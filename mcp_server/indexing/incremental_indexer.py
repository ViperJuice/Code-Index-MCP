"""Incremental indexing based on file changes.

This module provides efficient incremental index updates by only processing
files that have changed between commits.
"""

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core.path_resolver import PathResolver
from ..core.repo_context import RepoContext
from ..dispatcher.dispatcher_enhanced import EnhancedDispatcher
from ..storage.sqlite_store import SQLiteStore
from ..storage.two_phase import two_phase_commit
from .change_detector import FileChange
from .checkpoint import (
    ReindexCheckpoint,
)
from .checkpoint import clear as _clear_ckpt
from .checkpoint import load as _load_ckpt
from .checkpoint import save as _save_ckpt
from .lock_registry import lock_registry

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
        semantic_indexer: Optional[Any] = None,
        ctx: Optional[RepoContext] = None,
    ):
        self.store = store
        self.dispatcher = dispatcher
        self.ctx = ctx
        self.repo_path = repo_path or Path.cwd()
        self.path_resolver = PathResolver(self.repo_path)
        self.semantic_indexer = semantic_indexer

    def _dispatcher_ctx(self) -> RepoContext:
        if self.ctx is None:
            raise ValueError("dispatcher-backed incremental indexing requires RepoContext")
        return self.ctx

    def _get_chunk_ids_for_path(
        self, path: str, limit: Optional[int] = None, offset: int = 0
    ) -> List[str]:
        """Get indexed chunk ids for a relative repository path."""
        relative_path = self.path_resolver.normalize_path(self.repo_path / path)
        repo_id = self._get_repository_id()

        with self.store._get_connection() as conn:
            cursor = conn.execute(
                "SELECT id FROM files WHERE relative_path = ? AND repository_id = ?",
                (relative_path, repo_id),
            )
            row = cursor.fetchone()
            if not row:
                return []

            file_id = row[0]
            if limit is not None:
                cursor = conn.execute(
                    "SELECT chunk_id FROM code_chunks WHERE file_id = ? LIMIT ? OFFSET ?",
                    (file_id, limit, offset),
                )
            else:
                cursor = conn.execute(
                    "SELECT chunk_id FROM code_chunks WHERE file_id = ?",
                    (file_id,),
                )
            chunk_ids = [record[0] for record in cursor.fetchall()]
            if not chunk_ids:
                return []

            like_clauses = " OR ".join(["chunk_id LIKE ?"] * len(chunk_ids))
            params = [f"{chunk_id}:part:%" for chunk_id in chunk_ids]
            cursor = conn.execute(
                f"SELECT chunk_id FROM semantic_points WHERE {like_clauses}",
                params,
            )
            derived_chunk_ids = [record[0] for record in cursor.fetchall()]

            file_summary_ids: List[str] = []
            if self.semantic_indexer is not None:
                file_summary_chunk_id = f"{relative_path}:file-summary"
                cursor = conn.execute(
                    "SELECT chunk_id FROM semantic_points WHERE profile_id = ? AND chunk_id = ?",
                    (
                        self.semantic_indexer.semantic_profile.profile_id,
                        file_summary_chunk_id,
                    ),
                )
                file_summary_ids = [record[0] for record in cursor.fetchall()]

            return chunk_ids + derived_chunk_ids + file_summary_ids

    def _cleanup_stale_vectors(self, chunk_ids: List[str]) -> None:
        """Delete stale semantic vectors for existing chunk ids.

        Raises on failure so callers using two_phase_commit can detect shadow failure.
        """
        if not self.semantic_indexer or not chunk_ids:
            return

        profile_id = self.semantic_indexer.semantic_profile.profile_id
        self.semantic_indexer.delete_stale_vectors(
            profile_id=profile_id,
            chunk_ids=chunk_ids,
            sqlite_store=self.store,
        )

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

        # Process additions and modifications with checkpoint-resume
        add_mod_changes = changes_by_type.get("added", []) + changes_by_type.get("modified", [])
        self._index_files_with_checkpoint(add_mod_changes, stats)

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

    def _index_files_with_checkpoint(
        self, changes: List[FileChange], stats: IncrementalStats
    ) -> None:
        """Index add/modified files with checkpoint-resume under per-repo lock."""
        repo_id = self._get_repository_id()

        with lock_registry.acquire(repo_id):
            # Determine resume point from existing checkpoint
            ckpt = _load_ckpt(self.repo_path)
            all_paths = [c.path for c in changes]

            if ckpt is not None and ckpt.repo_id == repo_id and ckpt.remaining_paths:
                resume_from = ckpt.remaining_paths[0]
                try:
                    start_idx = all_paths.index(resume_from)
                except ValueError:
                    start_idx = 0
                pending = all_paths[start_idx:]
                existing_errors = list(ckpt.errors)
                last_completed = ckpt.last_completed_path
            else:
                pending = list(all_paths)
                existing_errors = []
                last_completed = ""

            started_at = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            errors: list = list(existing_errors)
            first_error_idx: int = -1

            for idx, path in enumerate(pending):
                result = self._index_file(path)
                if result == "indexed":
                    stats.files_indexed += 1
                    last_completed = path
                elif result == "skipped":
                    stats.files_skipped += 1
                    last_completed = path
                else:
                    stats.errors += 1
                    errors.append({"path": path, "error": "indexing failed"})
                    if first_error_idx == -1:
                        first_error_idx = idx
                        # Freeze checkpoint at first failure; remaining = from this file onward
                        _save_ckpt(
                            ReindexCheckpoint(
                                repo_id=repo_id,
                                started_at=started_at,
                                last_completed_path=last_completed,
                                remaining_paths=pending[idx:],
                                errors=errors,
                            ),
                            self.repo_path,
                        )

            # Always clear on clean loop exit; errors list is for reporting, not state resumption.
            _clear_ckpt(self.repo_path)

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

        Uses two_phase_commit with SQLite as primary and Qdrant as shadow.
        SQLite remove_file is irreversible (cascades across many tables), so rollback
        logs a warning rather than restoring — both ops are destructive but SQLite is
        chosen as primary because it is the authoritative record of file existence.
        """
        try:
            chunk_ids = self._get_chunk_ids_for_path(path)

            if self.dispatcher:
                full_path = self.repo_path / path
                ctx = self._dispatcher_ctx()

                def primary_op():
                    self.dispatcher.remove_file(ctx, full_path)
                    return chunk_ids

                def shadow_op(captured_chunk_ids):
                    self._cleanup_stale_vectors(captured_chunk_ids)

                def rollback(captured_chunk_ids):
                    logger.warning(
                        f"Cannot roll back SQLite remove for {path}; "
                        "Qdrant vectors may be inconsistent."
                    )

                two_phase_commit(primary_op, shadow_op, rollback)
            else:
                relative_path = self.path_resolver.normalize_path(self.repo_path / path)
                repo_id = self._get_repository_id()

                def primary_op():
                    self.store.remove_file(relative_path, repo_id)
                    return chunk_ids

                def shadow_op(captured_chunk_ids):
                    self._cleanup_stale_vectors(captured_chunk_ids)

                def rollback(captured_chunk_ids):
                    logger.warning(
                        f"Cannot roll back SQLite remove for {path}; "
                        "Qdrant vectors may be inconsistent."
                    )

                two_phase_commit(primary_op, shadow_op, rollback)

            logger.debug(f"Removed file from index: {path}")
            return True

        except Exception as e:
            logger.error(f"Failed to remove file {path}: {e}")
            return False

    def _move_file(self, old_path: str, new_path: str) -> bool:
        """Move a file in the index (handle rename).

        Uses two_phase_commit: primary = SQLite move_file (durable, rollback via reverse
        move), shadow = Qdrant delete_stale_vectors for old_path vectors. Chunk IDs are
        captured before the primary op because SQLite no longer has the old row after move.
        """
        try:
            new_full_path = self.repo_path / new_path

            if not new_full_path.exists():
                return self._remove_file(old_path)

            content_hash = self._compute_file_hash(new_full_path)
            # Capture chunk IDs before primary op mutates the SQLite row.
            chunk_ids = self._get_chunk_ids_for_path(old_path)

            if self.dispatcher:
                old_full_path = self.repo_path / old_path
                ctx = self._dispatcher_ctx()

                def primary_op():
                    self.dispatcher.move_file(ctx, old_full_path, new_full_path, content_hash)
                    return chunk_ids

                def shadow_op(captured_chunk_ids):
                    self._cleanup_stale_vectors(captured_chunk_ids)

                def rollback(captured_chunk_ids):
                    try:
                        self.dispatcher.move_file(ctx, new_full_path, old_full_path, content_hash)
                    except Exception as rb_exc:
                        logger.warning(f"Rollback of dispatcher move {old_path} failed: {rb_exc}")

                two_phase_commit(primary_op, shadow_op, rollback)
            else:
                old_relative = self.path_resolver.normalize_path(self.repo_path / old_path)
                new_relative = self.path_resolver.normalize_path(new_full_path)
                repo_id = self._get_repository_id()

                def primary_op():
                    self.store.move_file(old_relative, new_relative, repo_id, content_hash)
                    return chunk_ids

                def shadow_op(captured_chunk_ids):
                    self._cleanup_stale_vectors(captured_chunk_ids)

                def rollback(captured_chunk_ids):
                    try:
                        self.store.move_file(new_relative, old_relative, repo_id, content_hash)
                    except Exception as rb_exc:
                        logger.warning(f"Rollback of SQLite move {old_path} failed: {rb_exc}")

                two_phase_commit(primary_op, shadow_op, rollback)

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

            self._cleanup_stale_vectors(self._get_chunk_ids_for_path(path))

            relative_path = self.path_resolver.normalize_path(full_path)
            repo_id = self._get_repository_id()
            stored_file = self.store.get_file_by_path(relative_path, repo_id)
            if stored_file is not None:
                self.store.remove_file(relative_path, repo_id)

            if self.dispatcher:
                # Use dispatcher if available
                ctx = self._dispatcher_ctx()
                self.dispatcher.index_file(ctx, full_path)
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
        stats = {
            "total_indexed": 0,
            "files_missing": 0,
            "files_changed": 0,
            "files_ok": 0,
        }

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
