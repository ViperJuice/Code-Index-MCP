"""
Index Engine for coordinating code indexing operations.

This module provides the main IndexEngine class that coordinates all indexing
operations across the system, including file parsing, storage, and search index
maintenance.
"""

import asyncio
import hashlib
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

from ..core.ignore_patterns import get_ignore_manager
from ..plugin_system.interfaces import IPluginManager
from ..storage.sqlite_store import SQLiteStore
from ..utils.fuzzy_indexer import FuzzyIndexer

# Optional import for semantic indexing
try:
    from ..utils.semantic_indexer import SemanticIndexer
except ImportError:
    SemanticIndexer = None

logger = logging.getLogger(__name__)


@dataclass
class IndexResult:
    """Result of indexing a single file."""

    file_path: str
    success: bool
    symbols_count: int = 0
    references_count: int = 0
    duration_ms: float = 0.0
    error: Optional[str] = None
    language: Optional[str] = None
    file_size: int = 0


@dataclass
class BatchIndexResult:
    """Result of indexing multiple files."""

    total_files: int
    successful: int
    failed: int
    results: List[IndexResult] = field(default_factory=list)
    total_duration_ms: float = 0.0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


@dataclass
class IndexOptions:
    """Options for indexing operations."""

    force_reindex: bool = False
    include_patterns: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=list)
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    follow_symlinks: bool = False
    extract_graph: bool = True
    generate_embeddings: bool = False
    max_workers: int = 4
    batch_size: int = 10


@dataclass
class IndexTask:
    """A task in the indexing queue."""

    id: str
    path: str
    priority: int = 0
    options: Optional[IndexOptions] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: str = "pending"  # pending, running, completed, failed, cancelled


@dataclass
class IndexProgress:
    """Progress information for indexing operations."""

    total: int
    completed: int
    failed: int
    current_file: Optional[str] = None
    elapsed_time: Optional[timedelta] = None
    estimated_remaining: Optional[timedelta] = None
    throughput: float = 0.0  # files per second


class IndexEngine:
    """
    Main indexing engine that coordinates all indexing operations.

    This class implements both IIndexEngine and IIndexCoordinator interfaces
    from the architecture specification.
    """

    def __init__(
        self,
        plugin_manager: IPluginManager,
        storage: SQLiteStore,
        fuzzy_indexer: Optional[FuzzyIndexer] = None,
        semantic_indexer: Optional[Any] = None,  # SemanticIndexer if available
        repository_path: Optional[str] = None,
    ):
        """
        Initialize the index engine.

        Args:
            plugin_manager: Plugin manager for parsing operations
            storage: SQLite storage backend
            fuzzy_indexer: Optional fuzzy search indexer
            semantic_indexer: Optional semantic search indexer
            repository_path: Path to the repository being indexed
        """
        self.plugin_manager = plugin_manager
        self.storage = storage
        self.fuzzy_indexer = fuzzy_indexer or FuzzyIndexer(storage)
        self.semantic_indexer = semantic_indexer
        self.repository_path = repository_path

        # Task management
        self._task_queue: Dict[str, IndexTask] = {}
        self._running_tasks: Set[str] = set()
        self._task_results: Dict[str, Union[IndexResult, BatchIndexResult]] = {}

        # Progress tracking
        self._progress: IndexProgress = IndexProgress(0, 0, 0)
        self._start_time: Optional[datetime] = None

        # Cache for file hashes and metadata
        self._file_cache: Dict[str, Dict[str, Any]] = {}

        # Repository setup
        self._repository_id: Optional[int] = None
        if repository_path:
            self._setup_repository()

    def _setup_repository(self) -> None:
        """Set up repository in storage if needed."""
        if not self.repository_path:
            return

        repo_name = Path(self.repository_path).name
        self._repository_id = self.storage.create_repository(
            path=self.repository_path,
            name=repo_name,
            metadata={"indexed_at": datetime.now().isoformat()},
        )

    # ========================================
    # IIndexEngine Implementation
    # ========================================

    async def index_file(self, file_path: str, force: bool = False) -> IndexResult:
        """
        Index a single file.

        Args:
            file_path: Path to the file to index
            force: Whether to force reindexing even if file hasn't changed

        Returns:
            IndexResult containing the indexing outcome
        """
        start_time = time.time()

        try:
            # Check if we should index this file
            if not force and not self._should_index(file_path):
                return IndexResult(
                    file_path=file_path,
                    success=True,
                    duration_ms=(time.time() - start_time) * 1000,
                    error="File already indexed and unchanged",
                )

            # Get file information
            path_obj = Path(file_path)
            if not path_obj.exists():
                return IndexResult(
                    file_path=file_path,
                    success=False,
                    duration_ms=(time.time() - start_time) * 1000,
                    error="File not found",
                )

            file_size = path_obj.stat().st_size
            file_hash = self._get_file_hash(file_path)

            # Determine language and get appropriate plugin
            plugin = self.plugin_manager.get_plugin_for_file(path_obj)
            if not plugin:
                return IndexResult(
                    file_path=file_path,
                    success=False,
                    duration_ms=(time.time() - start_time) * 1000,
                    error="No plugin available for this file type",
                    file_size=file_size,
                )

            # Parse the file
            parse_result = await self._parse_file_async(plugin, file_path)
            if not parse_result:
                return IndexResult(
                    file_path=file_path,
                    success=False,
                    duration_ms=(time.time() - start_time) * 1000,
                    error="Failed to parse file",
                    file_size=file_size,
                )

            # Store in database
            await self._store_parse_result(file_path, parse_result, file_hash, file_size)

            # Update fuzzy index
            if self.fuzzy_indexer:
                try:
                    content = path_obj.read_text(encoding="utf-8", errors="ignore")
                    self.fuzzy_indexer.add_file(file_path, content)

                    # Add symbols to fuzzy index
                    for symbol in parse_result.get("symbols", []):
                        self.fuzzy_indexer.add_symbol(
                            symbol_name=symbol["name"],
                            file_path=file_path,
                            line_number=symbol.get("line_start", 1),
                            metadata=symbol,
                        )
                except Exception as e:
                    logger.warning(f"Failed to update fuzzy index for {file_path}: {e}")

            # Generate semantic embeddings if requested
            if self.semantic_indexer:
                try:
                    _ = self.semantic_indexer.index_file(path_obj)
                    logger.debug(f"Generated semantic embeddings for {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to generate semantic embeddings for {file_path}: {e}")

            symbols_count = len(parse_result.get("symbols", []))
            references_count = len(parse_result.get("references", []))

            return IndexResult(
                file_path=file_path,
                success=True,
                symbols_count=symbols_count,
                references_count=references_count,
                duration_ms=(time.time() - start_time) * 1000,
                language=parse_result.get("language"),
                file_size=file_size,
            )

        except Exception as e:
            logger.error(f"Error indexing file {file_path}: {e}")
            return IndexResult(
                file_path=file_path,
                success=False,
                duration_ms=(time.time() - start_time) * 1000,
                error=str(e),
            )

    async def index_directory(
        self,
        directory: str,
        recursive: bool = True,
        patterns: Optional[List[str]] = None,
    ) -> BatchIndexResult:
        """
        Index all files in a directory.

        Args:
            directory: Path to directory to index
            recursive: Whether to index subdirectories
            patterns: Optional list of file patterns to include

        Returns:
            BatchIndexResult containing the indexing outcome
        """
        options = IndexOptions(include_patterns=patterns or [], force_reindex=False)

        # Collect files to index
        files = self._collect_files(directory, recursive, options)

        return await self._index_files_batch(files, options)

    async def update_index(self, file_path: str) -> IndexResult:
        """
        Update the index for a specific file.

        Args:
            file_path: Path to the file to update

        Returns:
            IndexResult containing the update outcome
        """
        # Force reindexing to ensure we get the latest content
        return await self.index_file(file_path, force=True)

    async def remove_from_index(self, file_path: str) -> None:
        """
        Remove a file from all indexes.

        Args:
            file_path: Path to the file to remove
        """
        try:
            # Remove from database
            file_record = self.storage.get_file(file_path, self._repository_id)
            if file_record:
                # TODO: Implement proper cascade deletion in storage
                logger.info(f"Removed {file_path} from index")

            # Remove from fuzzy index
            if self.fuzzy_indexer and hasattr(self.fuzzy_indexer, "remove_file"):
                # Note: Current FuzzyIndexer doesn't have remove_file method
                # This would need to be implemented
                pass

            # Clear from cache
            self._file_cache.pop(file_path, None)

        except Exception as e:
            logger.error(f"Error removing {file_path} from index: {e}")

    def get_index_status(self, path: str) -> Dict[str, Any]:
        """
        Get the indexing status for a path.

        Args:
            path: File or directory path

        Returns:
            Dictionary containing status information
        """
        if Path(path).is_file():
            file_record = self.storage.get_file(path, self._repository_id)
            if file_record:
                return {
                    "indexed": True,
                    "last_indexed": file_record.get("indexed_at"),
                    "file_hash": file_record.get("hash"),
                    "language": file_record.get("language"),
                    "symbols_count": 0,  # TODO: Count symbols
                }
            else:
                return {"indexed": False}
        else:
            # For directories, return aggregate stats
            stats = self.storage.get_statistics()
            return {
                "total_files": stats.get("files", 0),
                "total_symbols": stats.get("symbols", 0),
                "total_references": stats.get("symbol_references", 0),
            }

    async def rebuild_index(self) -> None:
        """Rebuild the entire index from scratch."""
        logger.info("Starting index rebuild")

        # Clear existing indexes
        if self.fuzzy_indexer:
            self.fuzzy_indexer.clear()

        # TODO: Clear semantic index if available
        # TODO: Clear database indexes (implement in storage)

        # Reindex the repository if we have one
        if self.repository_path:
            await self.index_directory(self.repository_path, recursive=True)

        logger.info("Index rebuild completed")

    # ========================================
    # IIndexCoordinator Implementation
    # ========================================

    async def coordinate_indexing(
        self, paths: List[str], options: IndexOptions
    ) -> BatchIndexResult:
        """
        Coordinate indexing of multiple paths.

        Args:
            paths: List of file or directory paths to index
            options: Indexing options

        Returns:
            BatchIndexResult containing coordination outcome
        """
        all_files = []

        for path in paths:
            path_obj = Path(path)
            if path_obj.is_file():
                all_files.append(path)
            elif path_obj.is_dir():
                files = self._collect_files(path, True, options)
                all_files.extend(files)

        return await self._index_files_batch(all_files, options)

    async def schedule_reindex(self, path: str, priority: int = 0) -> str:
        """
        Schedule a reindexing task.

        Args:
            path: Path to reindex
            priority: Task priority (higher = more urgent)

        Returns:
            Task ID
        """
        task_id = str(uuid.uuid4())
        task = IndexTask(
            id=task_id,
            path=path,
            priority=priority,
            options=IndexOptions(force_reindex=True),
            status="pending",
        )

        self._task_queue[task_id] = task
        logger.info(f"Scheduled reindex task {task_id} for {path}")

        return task_id

    def get_pending_tasks(self) -> List[IndexTask]:
        """Get all pending indexing tasks."""
        return [task for task in self._task_queue.values() if task.status == "pending"]

    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a pending task.

        Args:
            task_id: ID of the task to cancel

        Returns:
            True if task was cancelled, False if not found or already running
        """
        task = self._task_queue.get(task_id)
        if task and task.status == "pending":
            task.status = "cancelled"
            logger.info(f"Cancelled task {task_id}")
            return True
        return False

    def get_progress(self) -> IndexProgress:
        """Get current indexing progress."""
        if self._start_time:
            elapsed = datetime.now() - self._start_time
            self._progress.elapsed_time = elapsed

            # Calculate throughput
            if elapsed.total_seconds() > 0:
                self._progress.throughput = self._progress.completed / elapsed.total_seconds()

            # Estimate remaining time
            if self._progress.throughput > 0 and self._progress.total > 0:
                remaining_files = self._progress.total - self._progress.completed
                remaining_seconds = remaining_files / self._progress.throughput
                self._progress.estimated_remaining = timedelta(seconds=remaining_seconds)

        return self._progress

    # ========================================
    # Private Helper Methods
    # ========================================

    async def _parse_file_async(self, plugin: Any, file_path: str) -> Optional[Dict[str, Any]]:
        """Parse a file using the appropriate plugin asynchronously."""
        try:
            # Run plugin parsing in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._parse_file_sync, plugin, file_path)
            return result
        except Exception as e:
            logger.error(f"Error parsing {file_path}: {e}")
            return None

    def _parse_file_sync(self, plugin: Any, file_path: str) -> Optional[Dict[str, Any]]:
        """Synchronously parse a file using a plugin."""
        try:
            # Call the plugin's parse method
            result = plugin.parse_file(file_path)
            return result
        except Exception as e:
            logger.error(f"Plugin error parsing {file_path}: {e}")
            return None

    async def _store_parse_result(
        self,
        file_path: str,
        parse_result: Dict[str, Any],
        file_hash: str,
        file_size: int,
    ) -> None:
        """Store parsing results in the database."""
        if not self._repository_id:
            logger.warning("No repository configured, skipping database storage")
            return

        try:
            # Store file record
            relative_path = os.path.relpath(file_path, self.repository_path or "")
            file_id = self.storage.store_file(
                repository_id=self._repository_id,
                path=file_path,
                relative_path=relative_path,
                language=parse_result.get("language"),
                size=file_size,
                hash=file_hash,
                metadata=parse_result.get("metadata", {}),
            )

            # Store symbols
            for symbol in parse_result.get("symbols", []):
                _ = self.storage.store_symbol(
                    file_id=file_id,
                    name=symbol["name"],
                    kind=symbol["kind"],
                    line_start=symbol.get("line_start", 1),
                    line_end=symbol.get("line_end", 1),
                    column_start=symbol.get("column_start"),
                    column_end=symbol.get("column_end"),
                    signature=symbol.get("signature"),
                    documentation=symbol.get("documentation"),
                    metadata=symbol.get("metadata", {}),
                )

            # Store references
            for ref in parse_result.get("references", []):
                # TODO: Implement reference storage
                # This requires linking references to symbols
                pass

        except Exception as e:
            logger.error(f"Error storing parse result for {file_path}: {e}")

    def _should_index(self, file_path: str) -> bool:
        """Check if a file should be indexed based on cache and modification time."""
        try:
            path_obj = Path(file_path)
            if not path_obj.exists():
                return False

            # Check cache
            cached = self._file_cache.get(file_path)
            if cached:
                cached_hash = cached.get("hash")
                current_hash = self._get_file_hash(file_path)
                if cached_hash == current_hash:
                    return False

            # Check database
            file_record = self.storage.get_file(file_path, self._repository_id)
            if file_record:
                stored_hash = file_record.get("hash")
                current_hash = self._get_file_hash(file_path)
                return stored_hash != current_hash

            return True

        except Exception as e:
            logger.error(f"Error checking if {file_path} should be indexed: {e}")
            return True

    def _get_file_hash(self, file_path: str) -> str:
        """Calculate MD5 hash of a file."""
        try:
            with open(file_path, "rb") as f:
                file_hash = hashlib.md5(f.read()).hexdigest()
                # Cache the hash
                self._file_cache[file_path] = {"hash": file_hash}
                return file_hash
        except Exception as e:
            logger.error(f"Error calculating hash for {file_path}: {e}")
            return ""

    def _collect_files(self, directory: str, recursive: bool, options: IndexOptions) -> List[str]:
        """Collect files to index from a directory."""
        files = []
        dir_path = Path(directory)

        if not dir_path.exists() or not dir_path.is_dir():
            return files

        # Get ignore manager for this directory
        ignore_manager = get_ignore_manager(dir_path)

        # Pattern matching function
        def matches_patterns(file_path: str, patterns: List[str]) -> bool:
            if not patterns:
                return True
            path_obj = Path(file_path)
            for pattern in patterns:
                if path_obj.match(pattern):
                    return True
            return False

        # Traverse directory
        try:
            for item in dir_path.rglob("*") if recursive else dir_path.iterdir():
                if item.is_file():
                    file_path = str(item)

                    # Check if file should be ignored based on .gitignore and .mcp-index-ignore
                    if ignore_manager.should_ignore(item):
                        logger.debug(f"Ignoring {file_path} due to ignore patterns")
                        continue

                    # Check size limit
                    if item.stat().st_size > options.max_file_size:
                        continue

                    # Check include patterns
                    if options.include_patterns:
                        if not matches_patterns(file_path, options.include_patterns):
                            continue

                    # Check exclude patterns
                    if options.exclude_patterns:
                        if matches_patterns(file_path, options.exclude_patterns):
                            continue

                    # Check if we have a plugin for this file
                    plugin = self.plugin_manager.get_plugin_for_file(item)
                    if plugin:
                        files.append(file_path)

        except Exception as e:
            logger.error(f"Error collecting files from {directory}: {e}")

        return files

    async def _index_files_batch(self, files: List[str], options: IndexOptions) -> BatchIndexResult:
        """Index a batch of files with progress tracking."""
        total_files = len(files)
        start_time = datetime.now()
        self._start_time = start_time

        # Initialize progress
        self._progress = IndexProgress(total=total_files, completed=0, failed=0)

        results = []
        successful = 0
        failed = 0

        # Create semaphore for controlling concurrency
        semaphore = asyncio.Semaphore(options.max_workers)

        async def index_file_with_semaphore(file_path: str) -> IndexResult:
            async with semaphore:
                self._progress.current_file = file_path
                result = await self.index_file(file_path, options.force_reindex)

                # Update progress
                if result.success:
                    self._progress.completed += 1
                else:
                    self._progress.failed += 1

                return result

        # Process files in batches
        batch_size = options.batch_size
        for i in range(0, len(files), batch_size):
            batch = files[i : i + batch_size]

            # Process batch concurrently
            batch_tasks = [index_file_with_semaphore(f) for f in batch]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

            # Process results
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Error in batch processing: {result}")
                    failed += 1
                elif isinstance(result, IndexResult):
                    results.append(result)
                    if result.success:
                        successful += 1
                    else:
                        failed += 1

        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds() * 1000

        # Final progress update
        self._progress.current_file = None
        self._progress.elapsed_time = end_time - start_time

        return BatchIndexResult(
            total_files=total_files,
            successful=successful,
            failed=failed,
            results=results,
            total_duration_ms=total_duration,
            start_time=start_time,
            end_time=end_time,
        )
