"""
File indexing tool implementation.

Provides comprehensive file and directory indexing with progress tracking.
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional, Set, Tuple
from pathlib import Path
import fnmatch
import os
from dataclasses import dataclass
from datetime import datetime

from ...dispatcher.dispatcher import Dispatcher
from ...plugin_base import IPlugin, IndexShard
from ..registry import ToolRegistry, ToolMetadata, ToolCapability
from ..schemas import INDEX_FILE_SCHEMA

logger = logging.getLogger(__name__)


@dataclass
class IndexingProgress:
    """Progress information for indexing operations."""
    total_files: int = 0
    processed_files: int = 0
    failed_files: int = 0
    current_file: Optional[str] = None
    start_time: Optional[datetime] = None
    estimated_remaining: Optional[float] = None
    
    @property
    def percentage(self) -> float:
        """Get completion percentage."""
        if self.total_files == 0:
            return 0.0
        return (self.processed_files / self.total_files) * 100.0
    
    @property
    def success_rate(self) -> float:
        """Get success rate percentage."""
        total_processed = self.processed_files + self.failed_files
        if total_processed == 0:
            return 100.0
        return (self.processed_files / total_processed) * 100.0


@dataclass
class IndexingResult:
    """Result of an indexing operation."""
    success: bool
    file_path: str
    symbols_found: int = 0
    processing_time: float = 0.0
    file_size: int = 0
    language: Optional[str] = None
    error: Optional[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


@dataclass
class IndexingStats:
    """Statistics from indexing operations."""
    total_files: int = 0
    successful_files: int = 0
    failed_files: int = 0
    skipped_files: int = 0
    total_symbols: int = 0
    total_size_bytes: int = 0
    total_time: float = 0.0
    languages: Dict[str, int] = None
    
    def __post_init__(self):
        if self.languages is None:
            self.languages = {}


class IndexFileHandler:
    """Handler for file and directory indexing operations with MCP integration."""
    
    def __init__(self):
        """Initialize the index file handler."""
        self._active_operations: Dict[str, IndexingProgress] = {}
        self._operation_counter = 0
        
        # Default exclusion patterns
        self._default_exclusions = [
            ".git/**",
            "node_modules/**",
            "__pycache__/**",
            "*.pyc",
            "*.pyo",
            "*.pyd",
            ".DS_Store",
            "Thumbs.db",
            "*.log",
            "*.tmp",
            "*.bak",
            "*.swp",
            "*.swo",
            ".idea/**",
            ".vscode/**",
            "*.class",
            "*.jar",
            "*.war",
            "*.ear",
            "target/**",
            "build/**",
            "dist/**",
            "*.egg-info/**",
            "venv/**",
            "env/**",
            ".env/**",
            "coverage/**",
            ".coverage",
            ".pytest_cache/**",
            ".tox/**",
            ".mypy_cache/**"
        ]
    
    async def handle(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle file indexing requests.
        
        Args:
            params: Validated parameters from the tool request
            context: Execution context including dispatcher
            
        Returns:
            Indexing results formatted for MCP clients
        """
        # Get dispatcher from context
        dispatcher = context.get("dispatcher")
        if not dispatcher:
            raise ValueError("Dispatcher not available in context")
        
        # Extract and validate parameters
        path = params["path"]
        recursive = params.get("recursive", True)
        force = params.get("force", False)
        file_pattern = params.get("file_pattern", "*")
        exclude_patterns = params.get("exclude_patterns", self._default_exclusions)
        
        # Validate path
        target_path = Path(path)
        if not target_path.exists():
            raise ValueError(f"Path does not exist: {path}")
        
        try:
            # Generate operation ID for progress tracking
            operation_id = self._generate_operation_id()
            
            # Initialize progress tracking
            progress = IndexingProgress(start_time=datetime.now())
            self._active_operations[operation_id] = progress
            
            try:
                if target_path.is_file():
                    # Index single file
                    result = await self._index_single_file(
                        dispatcher, target_path, force, progress
                    )
                    stats = IndexingStats(
                        total_files=1,
                        successful_files=1 if result.success else 0,
                        failed_files=0 if result.success else 1,
                        total_symbols=result.symbols_found,
                        total_size_bytes=result.file_size,
                        total_time=result.processing_time,
                        languages={result.language: 1} if result.language else {}
                    )
                    results = [result]
                else:
                    # Index directory
                    results, stats = await self._index_directory(
                        dispatcher, target_path, recursive, force, 
                        file_pattern, exclude_patterns, progress
                    )
                
                # Build response
                response = {
                    "operation_id": operation_id,
                    "path": str(target_path),
                    "recursive": recursive if target_path.is_dir() else False,
                    "force": force,
                    "file_pattern": file_pattern,
                    "exclude_patterns": exclude_patterns,
                    "statistics": {
                        "total_files": stats.total_files,
                        "successful_files": stats.successful_files,
                        "failed_files": stats.failed_files,
                        "skipped_files": stats.skipped_files,
                        "total_symbols": stats.total_symbols,
                        "total_size_mb": round(stats.total_size_bytes / (1024 * 1024), 2),
                        "total_time_seconds": round(stats.total_time, 2),
                        "avg_time_per_file": round(stats.total_time / max(stats.successful_files, 1), 2),
                        "languages": stats.languages,
                        "success_rate": round((stats.successful_files / max(stats.total_files, 1)) * 100, 1)
                    },
                    "progress": {
                        "percentage": round(progress.percentage, 1),
                        "processed_files": progress.processed_files,
                        "failed_files": progress.failed_files,
                        "success_rate": round(progress.success_rate, 1)
                    }
                }
                
                # Add detailed results if requested or for small operations
                if stats.total_files <= 20:  # Include details for small operations
                    response["results"] = [
                        {
                            "file_path": r.file_path,
                            "success": r.success,
                            "symbols_found": r.symbols_found,
                            "processing_time_ms": round(r.processing_time * 1000, 1),
                            "file_size_kb": round(r.file_size / 1024, 1),
                            "language": r.language,
                            "error": r.error,
                            "warnings": r.warnings
                        }
                        for r in results
                    ]
                else:
                    # For large operations, include only failed files
                    failed_results = [r for r in results if not r.success]
                    if failed_results:
                        response["failed_files"] = [
                            {
                                "file_path": r.file_path,
                                "error": r.error,
                                "warnings": r.warnings
                            }
                            for r in failed_results
                        ]
                
                # Add performance insights
                if stats.total_files > 1:
                    response["insights"] = self._generate_insights(stats, results)
                
                return response
                
            finally:
                # Clean up progress tracking
                if operation_id in self._active_operations:
                    del self._active_operations[operation_id]
                    
        except Exception as e:
            logger.error(f"Indexing failed for {path}: {e}", exc_info=True)
            raise


    async def _index_single_file(
        self,
        dispatcher: Dispatcher,
        file_path: Path,
        force: bool,
        progress: IndexingProgress
    ) -> IndexingResult:
        """Index a single file."""
        start_time = time.time()
        progress.total_files = 1
        progress.current_file = str(file_path)
        
        try:
            # Get file size
            file_size = file_path.stat().st_size
            
            # Check if dispatcher already has the file indexed and it's up to date
            if not force:
                # Here we would check if file needs re-indexing
                # For now, we'll always index unless forced to skip
                pass
            
            # Trigger indexing via dispatcher
            logger.info(f"Indexing file: {file_path}")
            dispatcher.index_file(file_path)
            
            # Get the plugin that handled the file to extract info
            plugin = dispatcher._match_plugin(file_path)
            language = getattr(plugin, 'lang', 'unknown')
            
            # Calculate symbols (this is an approximation since we don't have direct access)
            # In a real implementation, we'd get this from the dispatcher result
            symbols_count = self._estimate_symbols_count(file_path, language)
            
            processing_time = time.time() - start_time
            progress.processed_files = 1
            
            return IndexingResult(
                success=True,
                file_path=str(file_path),
                symbols_found=symbols_count,
                processing_time=processing_time,
                file_size=file_size,
                language=language
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            progress.failed_files = 1
            
            return IndexingResult(
                success=False,
                file_path=str(file_path),
                processing_time=processing_time,
                file_size=file_path.stat().st_size if file_path.exists() else 0,
                error=str(e)
            )



    async def _index_directory(
        self,
        dispatcher: Dispatcher,
        directory: Path,
        recursive: bool,
        force: bool,
        file_pattern: str,
        exclude_patterns: List[str],
        progress: IndexingProgress
    ) -> Tuple[List[IndexingResult], IndexingStats]:
        """Index all files in a directory."""
        
        # Discover files to index
        files_to_index = self._discover_files(
            directory, recursive, file_pattern, exclude_patterns
        )
        
        progress.total_files = len(files_to_index)
        
        if not files_to_index:
            return [], IndexingStats()
        
        logger.info(f"Indexing {len(files_to_index)} files in {directory}")
        
        # Index files with progress tracking
        results = []
        stats = IndexingStats(total_files=len(files_to_index))
        
        # Process files in batches to avoid overwhelming the system
        batch_size = min(10, len(files_to_index))
        
        for i in range(0, len(files_to_index), batch_size):
            batch = files_to_index[i:i + batch_size]
            
            # Process batch concurrently
            batch_tasks = [
                self._index_single_file(dispatcher, file_path, force, progress)
                for file_path in batch
            ]
            
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, Exception):
                    # Handle exception in batch processing
                    stats.failed_files += 1
                    results.append(IndexingResult(
                        success=False,
                        file_path="unknown",
                        error=str(result)
                    ))
                else:
                    results.append(result)
                    
                    # Update statistics
                    if result.success:
                        stats.successful_files += 1
                        stats.total_symbols += result.symbols_found
                        stats.total_size_bytes += result.file_size
                        
                        if result.language:
                            stats.languages[result.language] = stats.languages.get(result.language, 0) + 1
                    else:
                        stats.failed_files += 1
                    
                    stats.total_time += result.processing_time
            
            # Update progress
            progress.processed_files = min(progress.processed_files + len(batch), progress.total_files)
            
            # Add small delay between batches to prevent overwhelming
            if i + batch_size < len(files_to_index):
                await asyncio.sleep(0.1)
        
        logger.info(
            f"Indexing completed: {stats.successful_files} successful, "
            f"{stats.failed_files} failed, {stats.total_symbols} symbols found"
        )
        
        return results, stats


    def _discover_files(
        self,
        directory: Path,
        recursive: bool,
        file_pattern: str,
        exclude_patterns: List[str]
    ) -> List[Path]:
        """Discover files to index based on patterns and exclusions."""
        files = []
        
        def should_exclude(path: Path) -> bool:
            """Check if path should be excluded."""
            path_str = str(path.relative_to(directory))
            
            for pattern in exclude_patterns:
                if fnmatch.fnmatch(path_str, pattern) or fnmatch.fnmatch(str(path), pattern):
                    return True
                    
                # Check if any parent directory matches the pattern
                for parent in path.parents:
                    try:
                        parent_str = str(parent.relative_to(directory))
                        if fnmatch.fnmatch(parent_str, pattern):
                            return True
                    except ValueError:
                        # parent is not relative to directory
                        break
            
            return False
        
        def add_file(file_path: Path):
            """Add file if it matches criteria."""
            if should_exclude(file_path):
                return
                
            if fnmatch.fnmatch(file_path.name, file_pattern):
                files.append(file_path)
        
        if recursive:
            for root, dirs, filenames in os.walk(directory):
                root_path = Path(root)
                
                # Filter out excluded directories
                dirs[:] = [d for d in dirs if not should_exclude(root_path / d)]
                
                for filename in filenames:
                    file_path = root_path / filename
                    if file_path.is_file():  # Extra safety check
                        add_file(file_path)
        else:
            # Non-recursive: only direct children
            for item in directory.iterdir():
                if item.is_file():
                    add_file(item)
        
        return files


    def _estimate_symbols_count(self, file_path: Path, language: str) -> int:
        """Estimate number of symbols in a file based on heuristics."""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            lines = content.split('\n')
            
            # Simple heuristics based on language
            symbol_count = 0
            
            if language == 'python':
                for line in lines:
                    stripped = line.strip()
                    if (stripped.startswith('def ') or 
                        stripped.startswith('class ') or
                        stripped.startswith('async def ')):
                        symbol_count += 1
            elif language in ['javascript', 'typescript']:
                for line in lines:
                    stripped = line.strip()
                    if ('function ' in stripped or 
                        'class ' in stripped or
                        '=>' in stripped or
                        'const ' in stripped or
                        'let ' in stripped or
                        'var ' in stripped):
                        symbol_count += 1
            elif language in ['c', 'cpp']:
                for line in lines:
                    stripped = line.strip()
                    if (stripped.endswith('{') or
                        'struct ' in stripped or
                        'class ' in stripped or
                        'enum ' in stripped):
                        symbol_count += 1
            else:
                # Generic estimation: significant lines / 10
                non_empty_lines = len([l for l in lines if l.strip()])
                symbol_count = max(1, non_empty_lines // 10)
            
            return symbol_count
            
        except Exception:
            return 1  # Default estimate


    def _generate_insights(self, stats: IndexingStats, results: List[IndexingResult]) -> Dict[str, Any]:
        """Generate insights about the indexing operation."""
        insights = {}
        
        # Performance insights
        if stats.successful_files > 0:
            avg_time = stats.total_time / stats.successful_files
            avg_symbols = stats.total_symbols / stats.successful_files
            
            insights["performance"] = {
                "average_time_per_file": round(avg_time, 3),
                "average_symbols_per_file": round(avg_symbols, 1),
                "throughput_files_per_second": round(stats.successful_files / stats.total_time, 2)
            }
        
        # Language distribution
        if stats.languages:
            total_files = sum(stats.languages.values())
            insights["language_distribution"] = {
                lang: {
                    "count": count,
                    "percentage": round((count / total_files) * 100, 1)
                }
                for lang, count in sorted(stats.languages.items(), key=lambda x: x[1], reverse=True)
            }
        
        # Recommendations
        recommendations = []
        
        if stats.failed_files > stats.successful_files * 0.1:  # More than 10% failure rate
            recommendations.append("High failure rate detected. Consider excluding problematic file types.")
        
        if stats.total_time > 60:  # More than 1 minute
            recommendations.append("Large indexing operation. Consider using file patterns to limit scope.")
        
        if stats.languages.get('unknown', 0) > 0:
            recommendations.append("Some files have unknown language. Consider adding more plugins.")
        
        if recommendations:
            insights["recommendations"] = recommendations
        
        return insights


    def _generate_operation_id(self) -> str:
        """Generate a unique operation ID."""
        self._operation_counter += 1
        return f"index_op_{self._operation_counter}_{int(time.time())}"


    def get_active_operations(self) -> Dict[str, Dict[str, Any]]:
        """Get information about active indexing operations."""
        return {
            op_id: {
                "total_files": progress.total_files,
                "processed_files": progress.processed_files,
                "failed_files": progress.failed_files,
                "current_file": progress.current_file,
                "percentage": round(progress.percentage, 1),
                "success_rate": round(progress.success_rate, 1),
                "start_time": progress.start_time.isoformat() if progress.start_time else None
            }
            for op_id, progress in self._active_operations.items()
        }



async def index_file_handler(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle file indexing requests.
    
    This is the main entry point for the index_file tool.
    """
    handler = IndexFileHandler()
    return await handler.handle(params, context)


def register_tool(registry: ToolRegistry) -> None:
    """Register the index_file tool with the registry."""
    from .index_file_wrapper import wrap_index_handler
    
    metadata = ToolMetadata(
        name="index_file",
        description="Index specific files or directories with comprehensive progress tracking and statistics",
        version="1.0.0",
        capabilities=[ToolCapability.INDEX],
        tags=["index", "file", "directory", "symbols", "progress"],
        author="MCP Team"
    )
    
    # Wrap the handler with smart setup capabilities
    smart_handler = wrap_index_handler(index_file_handler)
    
    registry.register(
        name="index_file",
        handler=smart_handler,
        schema=INDEX_FILE_SCHEMA,
        metadata=metadata
    )
