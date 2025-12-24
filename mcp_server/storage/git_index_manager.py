"""Git-aware index manager for commit-synchronized indexing.

This module provides index management that's synchronized with git commits,
supporting incremental updates and artifact management.
"""

import logging
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..artifacts.commit_artifacts import CommitArtifactManager
from ..dispatcher.dispatcher_enhanced import EnhancedDispatcher
from .repository_registry import RepositoryRegistry

logger = logging.getLogger(__name__)


@dataclass
class ChangeSet:
    """Represents file changes between commits."""

    added: List[str]
    modified: List[str]
    deleted: List[str]
    renamed: List[Tuple[str, str]]  # List of (old_path, new_path)

    def is_empty(self) -> bool:
        """Check if there are no changes."""
        return not (self.added or self.modified or self.deleted or self.renamed)

    def total_changes(self) -> int:
        """Get total number of changed files."""
        return len(self.added) + len(self.modified) + len(self.deleted) + len(self.renamed)


@dataclass
class IndexSyncResult:
    """Result of index synchronization operation."""

    action: str  # "downloaded", "indexed", "up_to_date", "failed"
    commit: str
    files_processed: int = 0
    error: Optional[str] = None
    duration_seconds: float = 0.0


@dataclass
class UpdateResult:
    """Result of incremental index update."""

    indexed: int = 0
    deleted: int = 0
    moved: int = 0
    failed: int = 0
    duration_seconds: float = 0.0


class GitAwareIndexManager:
    """Manages indexes synchronized with git commits."""

    def __init__(
        self, registry: RepositoryRegistry, dispatcher: Optional[EnhancedDispatcher] = None
    ):
        self.registry = registry
        self.dispatcher = dispatcher
        self.artifact_manager = CommitArtifactManager()

    def sync_repository_index(self, repo_id: str, force_full: bool = False) -> IndexSyncResult:
        """Sync index with repository's current git state.

        Args:
            repo_id: Repository ID
            force_full: Force full reindex instead of incremental

        Returns:
            IndexSyncResult
        """
        start_time = datetime.now()

        repo_info = self.registry.get_repository(repo_id)
        if not repo_info:
            return IndexSyncResult(
                action="failed", commit="", error=f"Repository not found: {repo_id}"
            )

        repo_path = Path(repo_info.path)

        # Update current commit
        current_commit = self.registry.update_current_commit(repo_id)
        if not current_commit:
            return IndexSyncResult(action="failed", commit="", error="Failed to get current commit")

        repo_info.current_commit = current_commit
        last_indexed_commit = repo_info.last_indexed_commit

        # Check if already up to date
        if current_commit == last_indexed_commit and not force_full:
            return IndexSyncResult(
                action="up_to_date",
                commit=current_commit,
                duration_seconds=(datetime.now() - start_time).total_seconds(),
            )

        # Check for remote index artifact
        if repo_info.artifact_enabled and not force_full:
            if self._has_remote_artifact(repo_id, current_commit):
                # Download existing index for this commit
                if self._download_commit_index(repo_id, current_commit):
                    if self.registry.update_indexed_commit(repo_id, current_commit):
                        repo_info.last_indexed_commit = current_commit
                        return IndexSyncResult(
                            action="downloaded",
                            commit=current_commit,
                            duration_seconds=(datetime.now() - start_time).total_seconds(),
                        )

        # Determine what changed since last index
        if last_indexed_commit and not force_full:
            try:
                changed_files = self._get_changed_files(
                    repo_path, last_indexed_commit, current_commit
                )
                if not changed_files.is_empty():
                    # Incremental update - only reindex changed files
                    result = self._incremental_index_update(repo_id, changed_files)
                    if self.registry.update_indexed_commit(repo_id, current_commit):
                        repo_info.last_indexed_commit = current_commit
                        return IndexSyncResult(
                            action="indexed",
                            commit=current_commit,
                            files_processed=result.indexed + result.deleted + result.moved,
                            duration_seconds=(datetime.now() - start_time).total_seconds(),
                        )
            except Exception as e:
                logger.warning(f"Incremental update failed, falling back to full index: {e}")

        # Full index needed
        files_indexed = self._full_index(repo_id)
        if self.registry.update_indexed_commit(repo_id, current_commit):
            repo_info.last_indexed_commit = current_commit

        return IndexSyncResult(
            action="indexed",
            commit=current_commit,
            files_processed=files_indexed,
            duration_seconds=(datetime.now() - start_time).total_seconds(),
        )

    def _get_changed_files(self, repo_path: Path, from_commit: str, to_commit: str) -> ChangeSet:
        """Get files changed between two commits.

        Args:
            repo_path: Repository path
            from_commit: Starting commit
            to_commit: Ending commit

        Returns:
            ChangeSet
        """
        changes = ChangeSet(added=[], modified=[], deleted=[], renamed=[])

        try:
            # Get diff between commits
            cmd = ["git", "diff", "--name-status", from_commit, to_commit]
            result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True, check=True)

            for line in result.stdout.strip().splitlines():
                if not line:
                    continue

                parts = line.split("\t")
                if len(parts) < 2:
                    continue

                status = parts[0]

                if status == "A":  # Added
                    changes.added.append(parts[1])
                elif status == "M":  # Modified
                    changes.modified.append(parts[1])
                elif status == "D":  # Deleted
                    changes.deleted.append(parts[1])
                elif status.startswith("R"):  # Renamed
                    if len(parts) >= 3:
                        changes.renamed.append((parts[1], parts[2]))

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get git diff: {e}")
            raise

        return changes

    def _incremental_index_update(self, repo_id: str, changes: ChangeSet) -> UpdateResult:
        """Update index incrementally based on file changes.

        Args:
            repo_id: Repository ID
            changes: Set of file changes

        Returns:
            UpdateResult
        """
        start_time = datetime.now()
        result = UpdateResult()

        repo_info = self.registry.get_repository(repo_id)
        if not repo_info:
            return result

        index_path = Path(repo_info.index_location) / "current.db"
        if not index_path.exists():
            # No existing index, need full index
            logger.warning(f"No existing index for {repo_id}, full index required")
            return result

        # Use dispatcher if available, otherwise direct SQLite operations
        if self.dispatcher:
            repo_path = Path(repo_info.path)

            # Handle deletions first
            for path in changes.deleted:
                try:
                    self.dispatcher.remove_file(repo_path / path)
                    result.deleted += 1
                except Exception as e:
                    logger.error(f"Failed to remove {path}: {e}")
                    result.failed += 1

            # Handle renames
            for old_path, new_path in changes.renamed:
                try:
                    old_full = repo_path / old_path
                    new_full = repo_path / new_path
                    if new_full.exists():
                        content_hash = self.dispatcher._path_resolver.compute_content_hash(new_full)
                        self.dispatcher.move_file(old_full, new_full, content_hash)
                        result.moved += 1
                    else:
                        # New path doesn't exist, just remove old
                        self.dispatcher.remove_file(old_full)
                        result.deleted += 1
                except Exception as e:
                    logger.error(f"Failed to move {old_path} -> {new_path}: {e}")
                    result.failed += 1

            # Handle modifications and additions
            for path in changes.modified + changes.added:
                try:
                    full_path = repo_path / path
                    if full_path.exists() and full_path.is_file():
                        self.dispatcher.index_file(full_path)
                        result.indexed += 1
                except Exception as e:
                    logger.error(f"Failed to index {path}: {e}")
                    result.failed += 1
        else:
            logger.warning("No dispatcher available for incremental update")

        result.duration_seconds = (datetime.now() - start_time).total_seconds()
        return result

    def _full_index(self, repo_id: str) -> int:
        """Perform full repository indexing.

        Args:
            repo_id: Repository ID

        Returns:
            Number of files indexed
        """
        repo_info = self.registry.get_repository(repo_id)
        if not repo_info:
            return 0

        if not self.dispatcher:
            logger.error("No dispatcher available for indexing")
            return 0

        repo_path = Path(repo_info.path)

        # Ensure index directory exists
        index_dir = Path(repo_info.index_location)
        index_dir.mkdir(parents=True, exist_ok=True)

        # Index the directory
        logger.info(f"Starting full index of {repo_info.name}")
        stats = self.dispatcher.index_directory(repo_path, recursive=True)

        total_indexed = stats.get("indexed_files", 0)
        logger.info(f"Indexed {total_indexed} files in {repo_info.name}")

        return total_indexed

    def _has_remote_artifact(self, repo_id: str, commit: str) -> bool:
        """Check if remote artifact exists for commit.

        Args:
            repo_id: Repository ID
            commit: Git commit SHA

        Returns:
            True if artifact exists
        """
        # This would check GitHub artifacts or other remote storage
        # For now, return False
        return False

    def _download_commit_index(self, repo_id: str, commit: str) -> bool:
        """Download index artifact for specific commit.

        Args:
            repo_id: Repository ID
            commit: Git commit SHA

        Returns:
            True if successful
        """
        # This would download from GitHub artifacts
        # For now, return False
        return False

    def create_commit_artifact(self, repo_id: str) -> Optional[Path]:
        """Create index artifact for current commit.

        Args:
            repo_id: Repository ID

        Returns:
            Path to created artifact or None
        """
        repo_info = self.registry.get_repository(repo_id)
        if not repo_info:
            return None

        commit = repo_info.current_commit
        if not commit:
            return None

        # Create artifact with commit in name
        _ = f"{repo_id}-{commit[:8]}-index.tar.gz"

        # This would create the actual artifact
        # For now, return None
        return None

    def sync_all_repositories(self, parallel: bool = True) -> Dict[str, IndexSyncResult]:
        """Sync all repositories that need updates.

        Args:
            parallel: Whether to sync in parallel

        Returns:
            Dictionary of repo_id -> IndexSyncResult
        """
        results = {}

        # Get repositories needing update
        stale_repos = self.registry.get_repositories_needing_update()

        if not stale_repos:
            logger.info("All repositories are up to date")
            return results

        logger.info(f"Found {len(stale_repos)} repositories needing update")

        # For now, process sequentially
        # TODO: Add parallel processing support
        for repo_id, repo_info in stale_repos:
            if repo_info.auto_sync:
                logger.info(f"Syncing {repo_info.name}...")
                results[repo_id] = self.sync_repository_index(repo_id)
            else:
                logger.info(f"Skipping {repo_info.name} (auto-sync disabled)")

        return results

    def get_repository_status(self, repo_id: str) -> Dict[str, Any]:
        """Get detailed status of a repository's index.

        Args:
            repo_id: Repository ID

        Returns:
            Status dictionary
        """
        repo_info = self.registry.get_repository(repo_id)
        if not repo_info:
            return {"error": "Repository not found"}

        status = {
            "repo_id": repo_id,
            "name": repo_info.name,
            "path": repo_info.path,
            "current_commit": repo_info.current_commit,
            "last_indexed_commit": repo_info.last_indexed_commit,
            "last_indexed": repo_info.last_indexed,
            "needs_update": repo_info.needs_update(),
            "auto_sync": repo_info.auto_sync,
            "artifact_enabled": repo_info.artifact_enabled,
        }

        # Check index file
        index_path = Path(repo_info.index_location) / "current.db"
        if index_path.exists():
            status["index_exists"] = True
            status["index_size_mb"] = index_path.stat().st_size / (1024 * 1024)
        else:
            status["index_exists"] = False
            status["index_size_mb"] = 0

        return status
