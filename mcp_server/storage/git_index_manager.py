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
from ..core.path_resolver import PathResolver
from ..core.repo_context import RepoContext
from ..core.repo_resolver import RepoResolver
from ..dispatcher.dispatcher_enhanced import (
    EnhancedDispatcher,
    IndexResult,
    IndexResultStatus,
)
from ..health.repository_readiness import RepositoryReadiness, RepositoryReadinessState
from ..indexing.change_detector import ChangeDetector
from .repository_registry import RepositoryRegistry
from .sqlite_store import SQLiteStore
from .store_registry import StoreRegistry


def should_reindex_for_branch(current: Optional[str], tracked: Optional[str]) -> bool:
    """True iff both branches are non-None and equal."""
    if not current or not tracked:
        return False
    return current == tracked


logger = logging.getLogger(__name__)

# Callback type: (repo_id, current_branch, tracked_branch) -> None
_DriftCallback = Optional[Any]


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

    action: str
    commit: str
    files_processed: int = 0
    error: Optional[str] = None
    duration_seconds: float = 0.0
    code: Optional[str] = None
    readiness: Optional[Dict[str, Any]] = None


@dataclass
class UpdateResult:
    """Result of incremental index update."""

    indexed: int = 0
    deleted: int = 0
    moved: int = 0
    failed: int = 0
    skipped: int = 0
    errors: List[str] = None
    duration_seconds: float = 0.0

    def __post_init__(self) -> None:
        if self.errors is None:
            self.errors = []

    @property
    def files_processed(self) -> int:
        return self.indexed + self.deleted + self.moved

    @property
    def clean(self) -> bool:
        return self.failed == 0 and self.skipped == 0 and not self.errors


class GitAwareIndexManager:
    """Manages indexes synchronized with git commits."""

    def __init__(
        self,
        registry: RepositoryRegistry,
        dispatcher: Optional[EnhancedDispatcher] = None,
        repo_resolver: Optional[RepoResolver] = None,
        store_registry: Optional[StoreRegistry] = None,
    ):
        self.registry = registry
        self.dispatcher = dispatcher
        self.repo_resolver = repo_resolver
        self.store_registry = store_registry
        self.artifact_manager = CommitArtifactManager()
        # Wired post-construction by MultiRepositoryWatcher to avoid circular import.
        # Signature: (repo_id: str, current_branch: str, tracked_branch: str) -> None
        self.on_branch_drift: _DriftCallback = None

    def sync_repository_index(
        self, repo_id: str, force_full: bool = False, bypass_branch_guard: bool = False
    ) -> IndexSyncResult:
        """Sync index with repository's current git state.

        Args:
            repo_id: Repository ID
            force_full: Force full reindex instead of incremental
            bypass_branch_guard: Compatibility parameter; production sync paths always
                respect the tracked-branch guard.

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
        index_exists_before_mutation = self._index_exists(repo_info)

        # Update current git state
        git_state = self.registry.update_git_state(repo_id)
        current_commit = git_state.get("commit") if git_state else None
        if not current_commit:
            return IndexSyncResult(action="failed", commit="", error="Failed to get current commit")

        repo_info.current_commit = current_commit
        if git_state and git_state.get("branch"):
            repo_info.current_branch = git_state["branch"]
        last_indexed_commit = repo_info.last_indexed_commit
        current_branch = getattr(repo_info, "current_branch", None)

        if not should_reindex_for_branch(current_branch, repo_info.tracked_branch):
            # Distinguish true drift (both non-None, different) from unconfigured (tracked is None)
            if (
                current_branch
                and repo_info.tracked_branch
                and current_branch != repo_info.tracked_branch
            ):
                logger.warning(
                    "branch.drift.detected",
                    extra={
                        "repo_id": repo_id,
                        "current_branch": current_branch,
                        "tracked_branch": repo_info.tracked_branch,
                    },
                )
                readiness = RepositoryReadiness(
                    state=RepositoryReadinessState.WRONG_BRANCH,
                    repository_id=repo_id,
                    repository_name=getattr(repo_info, "name", None),
                    registered_path=str(Path(repo_info.path).resolve(strict=False)),
                    tracked_branch=repo_info.tracked_branch,
                    current_branch=current_branch,
                    current_commit=current_commit,
                    last_indexed_commit=last_indexed_commit,
                    index_path=(
                        str(Path(repo_info.index_path).resolve(strict=False))
                        if getattr(repo_info, "index_path", None)
                        else None
                    ),
                    remediation=(
                        f"Switch to the tracked branch '{repo_info.tracked_branch}' "
                        "or register the intended repository path."
                    ),
                )
                return IndexSyncResult(
                    action="wrong_branch",
                    commit=current_commit,
                    duration_seconds=(datetime.now() - start_time).total_seconds(),
                    code=RepositoryReadinessState.WRONG_BRANCH.value,
                    readiness=readiness.to_dict(),
                )
            else:
                logger.info(
                    "Skipping reindex for %s: current branch %r != tracked branch %r",
                    repo_id,
                    current_branch,
                    repo_info.tracked_branch,
                )
            return IndexSyncResult(
                action="up_to_date",
                commit=current_commit,
                duration_seconds=(datetime.now() - start_time).total_seconds(),
            )

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
                    if self._index_exists(repo_info) and self.registry.update_indexed_commit(
                        repo_id, current_commit, branch=current_branch
                    ):
                        repo_info.last_indexed_commit = current_commit
                        return IndexSyncResult(
                            action="downloaded",
                            commit=current_commit,
                            duration_seconds=(datetime.now() - start_time).total_seconds(),
                        )

        ctx = self._resolve_ctx(repo_id)
        if ctx is None:
            return IndexSyncResult(
                action="failed",
                commit=current_commit,
                error=f"Failed to resolve repository context: {repo_id}",
                duration_seconds=(datetime.now() - start_time).total_seconds(),
            )

        # Determine what changed since last index
        if last_indexed_commit and not force_full:
            try:
                changed_files = self._get_changed_files(
                    repo_path, last_indexed_commit, current_commit
                )
                if not changed_files.is_empty():
                    if self._should_full_reindex(repo_path, changed_files):
                        logger.info(
                            "Large change set detected for %s (%d files), using full reindex",
                            repo_id,
                            changed_files.total_changes(),
                        )
                    elif not index_exists_before_mutation:
                        logger.warning(
                            "No existing durable index for %s; using full reindex",
                            repo_id,
                        )
                    else:
                        # Incremental update - only reindex changed files
                        result = self._incremental_index_update(repo_id, ctx, changed_files)
                        if not result.clean:
                            return IndexSyncResult(
                                action="failed",
                                commit=current_commit,
                                files_processed=result.files_processed,
                                error="; ".join(result.errors) or "Incremental index update failed",
                                duration_seconds=(datetime.now() - start_time).total_seconds(),
                            )
                        if self._index_exists(repo_info) and self.registry.update_indexed_commit(
                            repo_id, current_commit, branch=current_branch
                        ):
                            repo_info.last_indexed_commit = current_commit
                            return IndexSyncResult(
                                action="incremental_update",
                                commit=current_commit,
                                files_processed=result.files_processed,
                                duration_seconds=(datetime.now() - start_time).total_seconds(),
                            )
            except Exception as e:
                logger.warning(f"Incremental update failed, falling back to full index: {e}")

        # Full index needed
        result = self._normalize_update_result(self._full_index(repo_id, ctx))
        if not result.clean:
            return IndexSyncResult(
                action="failed",
                commit=current_commit,
                files_processed=result.files_processed,
                error="; ".join(result.errors) or "Full index failed",
                duration_seconds=(datetime.now() - start_time).total_seconds(),
            )
        if self._index_exists(repo_info) and self.registry.update_indexed_commit(
            repo_id, current_commit, branch=current_branch
        ):
            repo_info.last_indexed_commit = current_commit
        elif not self._index_exists(repo_info):
            return IndexSyncResult(
                action="failed",
                commit=current_commit,
                files_processed=result.files_processed,
                error="Full index did not create a durable SQLite index",
                duration_seconds=(datetime.now() - start_time).total_seconds(),
            )

        return IndexSyncResult(
            action="full_index",
            commit=current_commit,
            files_processed=result.indexed,
            duration_seconds=(datetime.now() - start_time).total_seconds(),
        )

    def _resolve_ctx(self, repo_id: str) -> Optional[RepoContext]:
        """Resolve a RepoContext for the registered repository before mutation."""
        repo_info = self.registry.get_repository(repo_id)
        if not repo_info:
            return None

        repo_path = Path(repo_info.path)
        if self.repo_resolver is not None:
            ctx = self.repo_resolver.resolve(repo_path)
            if ctx is not None and ctx.repo_id == repo_id:
                return ctx
            return None

        try:
            if self.store_registry is not None:
                store = self.store_registry.get(repo_id)
            else:
                registry_get = getattr(self.registry, "get", None)
                registered_info = registry_get(repo_id) if callable(registry_get) else None
                if registered_info is repo_info:
                    self.store_registry = StoreRegistry.for_registry(self.registry)
                    store = self.store_registry.get(repo_id)
                else:
                    if not isinstance(repo_info.index_path, (str, Path)):
                        return None
                    store = SQLiteStore(
                        str(repo_info.index_path),
                        path_resolver=PathResolver(repo_path),
                    )
        except Exception as exc:
            logger.error("Failed to resolve store for %s: %s", repo_id, exc)
            return None

        return RepoContext(
            repo_id=repo_id,
            sqlite_store=store,
            workspace_root=repo_path,
            tracked_branch=getattr(repo_info, "tracked_branch", "") or "",
            registry_entry=repo_info,
        )

    def _index_exists(self, repo_info: Any) -> bool:
        index_path = getattr(repo_info, "index_path", None)
        if index_path is not None:
            return Path(index_path).exists()
        index_location = getattr(repo_info, "index_location", None)
        if index_location is None:
            return False
        return (Path(index_location) / "current.db").exists()

    def _normalize_update_result(self, value: Any) -> UpdateResult:
        if isinstance(value, UpdateResult):
            return value
        if isinstance(value, int):
            return UpdateResult(indexed=value)
        return UpdateResult(failed=1, errors=[f"Unexpected update result: {value!r}"])

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
        for change in ChangeDetector(repo_path).get_changes_since_commit(from_commit, to_commit):
            if change.change_type == "added":
                changes.added.append(change.path)
            elif change.change_type == "modified":
                changes.modified.append(change.path)
            elif change.change_type == "deleted":
                changes.deleted.append(change.path)
            elif change.change_type == "renamed" and change.old_path:
                changes.renamed.append((change.old_path, change.path))

        return changes

    def _incremental_index_update(
        self, repo_id: str, ctx: RepoContext, changes: ChangeSet
    ) -> UpdateResult:
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
            result.failed += 1
            result.errors.append(f"Repository not found: {repo_id}")
            return result

        if not self._index_exists(repo_info):
            result.failed += 1
            result.errors.append(f"Missing durable index for incremental update: {repo_id}")
            result.duration_seconds = (datetime.now() - start_time).total_seconds()
            return result

        # Use dispatcher if available, otherwise direct SQLite operations
        if self.dispatcher:
            repo_path = Path(repo_info.path)

            # Handle deletions first
            for path in changes.deleted:
                try:
                    mutation = self._coerce_index_result(
                        self.dispatcher.remove_file(ctx, repo_path / path),
                        path=repo_path / path,
                    )
                    self._record_required_mutation_result(
                        result,
                        mutation,
                        success_status=IndexResultStatus.DELETED,
                        success_counter="deleted",
                        action_label=f"Failed to remove {path}",
                    )
                except Exception as e:
                    logger.error(f"Failed to remove {path}: {e}")
                    result.failed += 1
                    result.errors.append(f"Failed to remove {path}: {e}")

            # Handle renames
            for old_path, new_path in changes.renamed:
                try:
                    old_full = repo_path / old_path
                    new_full = repo_path / new_path
                    if new_full.exists():
                        mutation = self._coerce_index_result(
                            self.dispatcher.move_file(ctx, old_full, new_full),
                            path=new_full,
                        )
                        self._record_required_mutation_result(
                            result,
                            mutation,
                            success_status=IndexResultStatus.MOVED,
                            success_counter="moved",
                            action_label=f"Failed to move {old_path} -> {new_path}",
                        )
                    else:
                        # New path doesn't exist, just remove old
                        mutation = self._coerce_index_result(
                            self.dispatcher.remove_file(ctx, old_full),
                            path=old_full,
                        )
                        self._record_required_mutation_result(
                            result,
                            mutation,
                            success_status=IndexResultStatus.DELETED,
                            success_counter="deleted",
                            action_label=f"Failed to remove stale rename source {old_path}",
                        )
                except Exception as e:
                    logger.error(f"Failed to move {old_path} -> {new_path}: {e}")
                    result.failed += 1
                    result.errors.append(f"Failed to move {old_path} -> {new_path}: {e}")

            # Handle modifications and additions
            for path in changes.modified + changes.added:
                try:
                    full_path = repo_path / path
                    if full_path.exists() and full_path.is_file():
                        mutation = self._coerce_index_result(
                            self.dispatcher.index_file(ctx, full_path),
                            path=full_path,
                        )
                        self._record_required_mutation_result(
                            result,
                            mutation,
                            success_status=IndexResultStatus.INDEXED,
                            success_counter="indexed",
                            action_label=f"Failed to index {path}",
                        )
                    else:
                        result.skipped += 1
                        result.errors.append(f"Failed to index {path}: file missing at dispatch")
                except Exception as e:
                    logger.error(f"Failed to index {path}: {e}")
                    result.failed += 1
                    result.errors.append(f"Failed to index {path}: {e}")
        else:
            result.failed += 1
            result.errors.append("No dispatcher available for incremental update")

        result.duration_seconds = (datetime.now() - start_time).total_seconds()
        return result

    def _coerce_index_result(self, value: object, *, path: Path) -> IndexResult:
        if isinstance(value, IndexResult):
            return value
        return IndexResult(
            status=IndexResultStatus.ERROR,
            path=path,
            observed_hash=None,
            actual_hash=None,
            error=f"Unexpected mutation result: {value!r}",
        )

    def _record_required_mutation_result(
        self,
        result: UpdateResult,
        mutation: IndexResult,
        *,
        success_status: IndexResultStatus,
        success_counter: str,
        action_label: str,
    ) -> None:
        if mutation.status == success_status:
            setattr(result, success_counter, getattr(result, success_counter) + 1)
            return

        detail = mutation.error or mutation.status.value
        if mutation.status in {
            IndexResultStatus.SKIPPED_UNCHANGED,
            IndexResultStatus.SKIPPED_TOCTOU,
        }:
            result.skipped += 1
            result.errors.append(f"{action_label}: skipped required mutation ({detail})")
            return

        result.failed += 1
        result.errors.append(f"{action_label}: {detail}")

    def _should_full_reindex(self, repo_path: Path, changes: ChangeSet) -> bool:
        """Decide whether change volume warrants a full reindex."""
        try:
            result = subprocess.run(
                ["git", "ls-files"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            tracked_files = [line for line in result.stdout.splitlines() if line.strip()]
            total = len(tracked_files)
            if total == 0:
                return False

            ratio = changes.total_changes() / total
            return ratio >= 0.5
        except subprocess.CalledProcessError:
            return False

    def _full_index(self, repo_id: str, ctx: RepoContext) -> UpdateResult:
        """Perform full repository indexing.

        Args:
            repo_id: Repository ID

        Returns:
            UpdateResult with durability/failure details
        """
        start_time = datetime.now()
        result = UpdateResult()
        repo_info = self.registry.get_repository(repo_id)
        if not repo_info:
            result.failed += 1
            result.errors.append(f"Repository not found: {repo_id}")
            return result

        if not self.dispatcher:
            logger.error("No dispatcher available for indexing")
            result.failed += 1
            result.errors.append("No dispatcher available for indexing")
            return result

        repo_path = Path(repo_info.path)

        # Ensure index directory exists
        index_dir = Path(repo_info.index_location)
        index_dir.mkdir(parents=True, exist_ok=True)

        # Index the directory
        logger.info(f"Starting full index of {repo_info.name}")
        try:
            stats = self.dispatcher.index_directory(ctx, repo_path, recursive=True)
        except Exception as exc:
            result.failed += 1
            result.errors.append(f"Full index failed: {exc}")
            result.duration_seconds = (datetime.now() - start_time).total_seconds()
            return result

        total_indexed = stats.get("indexed_files", 0) if isinstance(stats, dict) else 0
        failed_files = stats.get("failed_files", 0) if isinstance(stats, dict) else 0
        errors = stats.get("errors", []) if isinstance(stats, dict) else []
        result.indexed = total_indexed
        result.failed = failed_files
        result.errors.extend(str(error) for error in errors)
        result.duration_seconds = (datetime.now() - start_time).total_seconds()
        logger.info(f"Indexed {total_indexed} files in {repo_info.name}")

        return result

    def _has_remote_artifact(self, repo_id: str, commit: str) -> bool:
        """Check if remote artifact exists for commit.

        Args:
            repo_id: Repository ID
            commit: Git commit SHA

        Returns:
            True if artifact exists
        """
        # Local artifact store fallback (can be extended to GitHub/cloud providers).
        return self.artifact_manager.has_artifact(repo_id, commit)

    def _download_commit_index(self, repo_id: str, commit: str) -> bool:
        """Download index artifact for specific commit.

        Args:
            repo_id: Repository ID
            commit: Git commit SHA

        Returns:
            True if successful
        """
        repo_info = self.registry.get_repository(repo_id)
        if not repo_info:
            return False

        target = Path(repo_info.index_location)
        target.mkdir(parents=True, exist_ok=True)
        return self.artifact_manager.extract_commit_artifact(repo_id, commit, target)

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

        index_path = Path(repo_info.index_location)
        return self.artifact_manager.create_commit_artifact(repo_id, commit, index_path)

    def enqueue_full_rescan(self, repo_id: str) -> IndexSyncResult:
        """Trigger a guarded full rescan without bypassing the tracked-branch check."""
        return self.sync_repository_index(repo_id, force_full=True)

    def sync_all_repositories(self) -> Dict[str, IndexSyncResult]:
        """Sync all repositories that need updates sequentially."""
        results = {}

        # Get repositories needing update
        stale_repos = self.registry.get_repositories_needing_update()

        if not stale_repos:
            logger.info("All repositories are up to date")
            return results

        logger.info(f"Found {len(stale_repos)} repositories needing update")

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
