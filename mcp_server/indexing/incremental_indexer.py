"""Incremental indexing based on file changes.

This module provides efficient incremental index updates by only processing
files that have changed between commits.
"""

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from ..core.path_resolver import PathResolver
from ..dispatcher.dispatcher_enhanced import EnhancedDispatcher
from ..storage.sqlite_store import SQLiteStore
from .change_detector import FileChange

logger = logging.getLogger(__name__)


@dataclass
class IncrementalStats:
    """Statistics for incremental update operation."""

    files_indexed: int = 0
    files_removed: int = 0
    files_moved: int = 0
    files_skipped: int = 0
    errors: int = 0
    start_time: datetime = None
    end_time: datetime = None

    def duration_seconds(self) -> float:
        """Get operation duration in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0

    def total_operations(self) -> int:
        """Get total number of operations performed."""
        return self.files_indexed + self.files_removed + self.files_moved + self.files_skipped


class IncrementalIndexer:
    """Updates indexes incrementally based on file changes."""

    def __init__(
        self,
        store: SQLiteStore,
        dispatcher: Optional[EnhancedDispatcher] = None,
        repo_path: Optional[Path] = None,
    ):
        self.store = store
        self.dispatcher = dispatcher
        self.repo_path = repo_path or Path.cwd()
        self.path_resolver = PathResolver(self.repo_path)

    def update_from_changes(self, changes: List[FileChange]) -> IncrementalStats:
        """Update index based on file changes.

        Args:
            changes: List of file changes

        Returns:
            IncrementalStats with operation results
        """
        stats = IncrementalStats(start_time=datetime.now())

        # Group changes by type for efficient processing
        changes_by_type = self._group_changes_by_type(changes)

        # Process deletions first (to free up space)
        for change in changes_by_type.get("deleted", []):
            if self._remove_file(change.path):
                stats.files_removed += 1
            else:
                stats.errors += 1

        # Process renames
        for change in changes_by_type.get("renamed", []):
            if self._move_file(change.old_path, change.path):
                stats.files_moved += 1
            else:
                stats.errors += 1

        # Process additions and modifications
        for change in changes_by_type.get("added", []) + changes_by_type.get("modified", []):
            result = self._index_file(change.path)
            if result == "indexed":
                stats.files_indexed += 1
            elif result == "skipped":
                stats.files_skipped += 1
            else:
                stats.errors += 1

        stats.end_time = datetime.now()

        logger.info(
            f"Incremental update complete: "
            f"{stats.files_indexed} indexed, "
            f"{stats.files_removed} removed, "
            f"{stats.files_moved} moved, "
            f"{stats.files_skipped} skipped, "
            f"{stats.errors} errors "
            f"in {stats.duration_seconds():.2f}s"
        )

        return stats

    def _group_changes_by_type(self, changes: List[FileChange]) -> Dict[str, List[FileChange]]:
        """Group changes by their type.

        Args:
            changes: List of file changes

        Returns:
            Dictionary mapping change type to list of changes
        """
        grouped = {"added": [], "modified": [], "deleted": [], "renamed": []}

        for change in changes:
            grouped[change.change_type].append(change)

        return grouped

    def _remove_file(self, path: str) -> bool:
        """Remove a file from the index.

        Args:
            path: File path relative to repository

        Returns:
            True if successful
        """
        try:
            if self.dispatcher:
                # Use dispatcher if available
                full_path = self.repo_path / path
                self.dispatcher.remove_file(full_path)
            else:
                # Direct database operation
                relative_path = self.path_resolver.normalize_path(self.repo_path / path)

                # Get repository ID
                repo_id = self._get_repository_id()

                # Remove from SQLite
                self.store.remove_file(relative_path, repo_id)

                # TODO: Also remove from vector store if available

            logger.debug(f"Removed file from index: {path}")
            return True

        except Exception as e:
            logger.error(f"Failed to remove file {path}: {e}")
            return False

    def _move_file(self, old_path: str, new_path: str) -> bool:
        """Move a file in the index (handle rename).

        Args:
            old_path: Old file path
            new_path: New file path

        Returns:
            True if successful
        """
        try:
            new_full_path = self.repo_path / new_path

            # Check if new file exists and compute hash
            if not new_full_path.exists():
                # File was moved and deleted, just remove old entry
                return self._remove_file(old_path)

            content_hash = self._compute_file_hash(new_full_path)

            if self.dispatcher:
                # Use dispatcher if available
                old_full_path = self.repo_path / old_path
                self.dispatcher.move_file(old_full_path, new_full_path, content_hash)
            else:
                # Direct database operation
                old_relative = self.path_resolver.normalize_path(self.repo_path / old_path)
                new_relative = self.path_resolver.normalize_path(new_full_path)
                repo_id = self._get_repository_id()

                # Move in SQLite
                self.store.move_file(old_relative, new_relative, repo_id, content_hash)

                # TODO: Also update vector store if available

            logger.debug(f"Moved file in index: {old_path} -> {new_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to move file {old_path} -> {new_path}: {e}")
            return False

    def _index_file(self, path: str) -> str:
        """Index or reindex a file.

        Args:
            path: File path relative to repository

        Returns:
            "indexed", "skipped", or "error"
        """
        try:
            full_path = self.repo_path / path

            if not full_path.exists():
                logger.warning(f"File not found: {path}")
                return "error"

            if not full_path.is_file():
                logger.debug(f"Skipping non-file: {path}")
                return "skipped"

            # Check if file needs reindexing
            if not self._needs_reindex(full_path):
                logger.debug(f"File unchanged, skipping: {path}")
                return "skipped"

            if self.dispatcher:
                # Use dispatcher if available
                self.dispatcher.index_file(full_path)
            else:
                # Direct indexing would go here
                logger.warning(f"No dispatcher available to index {path}")
                return "error"

            logger.debug(f"Indexed file: {path}")
            return "indexed"

        except Exception as e:
            logger.error(f"Failed to index file {path}: {e}")
            return "error"

    def _needs_reindex(self, file_path: Path, stored_file: Optional[Dict] = None) -> bool:
        """Check if a file needs to be reindexed.

        Args:
            file_path: Absolute file path
            stored_file: Optional cached file record

        Returns:
            True if file needs reindexing
        """
        try:
            # Compute current file hash
            current_hash = self._compute_file_hash(file_path)

            # Get stored hash from database
            relative_path = self.path_resolver.normalize_path(file_path)
            repo_id = self._get_repository_id()

            stored_file = stored_file or self.store.get_file_by_path(relative_path, repo_id)
            if not stored_file:
                # File not in index
                return True

            stored_hash = stored_file.get("content_hash") or stored_file.get("hash")
            if not stored_hash:
                # No hash stored, reindex
                return True

            # Compare hashes
            return current_hash != stored_hash

        except Exception as e:
            logger.error(f"Error checking if file needs reindex: {e}")
            # On error, assume it needs reindexing
            return True

    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA-256 hash of file content.

        Args:
            file_path: File path

        Returns:
            Hex digest of file hash
        """
        sha256_hash = hashlib.sha256()

        try:
            with open(file_path, "rb") as f:
                # Read in chunks to handle large files
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)

            return sha256_hash.hexdigest()

        except Exception as e:
            logger.error(f"Failed to compute hash for {file_path}: {e}")
            # Return a unique value that will force reindexing
            return f"error_{datetime.now().timestamp()}"

    def _get_repository_id(self) -> str:
        """Get repository ID for current repository.

        Returns:
            Repository ID
        """
        # This is a simplified version - in practice would use the registry
        try:
            import subprocess

            result = subprocess.run(
                ["git", "config", "--get", "remote.origin.url"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            remote_url = result.stdout.strip()
            return hashlib.sha256(remote_url.encode()).hexdigest()[:12]
        except Exception:
            # Fallback to path-based ID
            return hashlib.sha256(str(self.repo_path).encode()).hexdigest()[:12]

    def validate_index_integrity(self) -> Dict[str, int]:
        """Validate that index matches current file system state.

        Returns:
            Dictionary with validation statistics
        """
        stats = {"total_indexed": 0, "files_missing": 0, "files_changed": 0, "files_ok": 0}

        repo_id = self._get_repository_id()

        # Get all indexed files
        indexed_files = self.store.get_all_files(repo_id)
        stats["total_indexed"] = len(indexed_files)

        for file_info in indexed_files:
            relative_path = file_info.get("path")
            if not relative_path:
                continue

            full_path = self.repo_path / relative_path

            if not full_path.exists():
                stats["files_missing"] += 1
            elif self._needs_reindex(full_path, stored_file=file_info):
                stats["files_changed"] += 1
            else:
                stats["files_ok"] += 1

        return stats
