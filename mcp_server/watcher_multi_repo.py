"""Multi-repository file watcher with git synchronization.

This module extends the basic file watcher to support multiple repositories
and synchronize with git commits.
"""

import logging
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, Optional

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from .artifacts.commit_artifacts import CommitArtifactManager
from .dispatcher.dispatcher_enhanced import EnhancedDispatcher
from .storage.git_index_manager import GitAwareIndexManager
from .storage.repository_registry import RepositoryRegistry
from .watcher import _Handler

logger = logging.getLogger(__name__)


class GitMonitor:
    """Monitors git state changes in repositories."""

    def __init__(self, registry: RepositoryRegistry, callback):
        self.registry = registry
        self.callback = callback
        self.running = False
        self.monitor_thread = None
        self.check_interval = 30  # seconds
        self.last_commits = {}  # repo_id -> commit

    def start(self):
        """Start monitoring git repositories."""
        if self.running:
            return

        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Git monitor started")

    def stop(self):
        """Stop monitoring."""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Git monitor stopped")

    def _monitor_loop(self):
        """Main monitoring loop."""
        while self.running:
            try:
                self._check_repositories()
            except Exception as e:
                logger.error(f"Error in git monitor: {e}")

            # Sleep with interruption support
            for _ in range(self.check_interval):
                if not self.running:
                    break
                threading.Event().wait(1)

    def _check_repositories(self):
        """Check all repositories for git state changes."""
        for repo_id, repo_info in self.registry.get_all_repositories().items():
            if not repo_info.auto_sync:
                continue

            try:
                current_commit = self._get_current_commit(repo_info.path)
                if not current_commit:
                    continue

                last_commit = self.last_commits.get(repo_id)

                if last_commit and current_commit != last_commit:
                    # Commit changed
                    logger.info(f"New commit detected in {repo_info.name}: {current_commit[:8]}")
                    self.callback(repo_id, current_commit)

                self.last_commits[repo_id] = current_commit

            except Exception as e:
                logger.error(f"Error checking repository {repo_id}: {e}")

    def _get_current_commit(self, repo_path: str) -> Optional[str]:
        """Get current git commit for a repository."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except Exception:
            return None


class MultiRepositoryHandler(FileSystemEventHandler):
    """File system event handler for a specific repository."""

    def __init__(self, repo_id: str, repo_path: Path, parent_watcher):
        self.repo_id = repo_id
        self.repo_path = repo_path
        self.parent_watcher = parent_watcher
        self.handler = _Handler(
            parent_watcher.dispatcher, parent_watcher.query_cache, parent_watcher.path_resolver
        )

    def on_any_event(self, event):
        """Handle file system events."""
        # Add repository context
        logger.debug(f"Event in {self.repo_id}: {event}")

        # Let the standard handler process it
        self.handler.on_any_event(event)

        # Mark repository as having changes
        self.parent_watcher.mark_repository_changed(self.repo_id)


class MultiRepositoryWatcher:
    """Watches multiple repositories and syncs with git."""

    def __init__(
        self,
        registry: RepositoryRegistry,
        dispatcher: EnhancedDispatcher,
        index_manager: GitAwareIndexManager,
        artifact_manager: Optional[CommitArtifactManager] = None,
    ):
        self.registry = registry
        self.dispatcher = dispatcher
        self.index_manager = index_manager
        self.artifact_manager = artifact_manager or CommitArtifactManager()

        self.watchers = {}  # repo_id -> Observer
        self.observers = {}  # repo_id -> Observer instance
        self.changed_repos = set()  # Repos with uncommitted changes
        self.git_monitor = GitMonitor(registry, self.on_git_commit)

        self.query_cache = None  # TODO: Add query cache support
        self.path_resolver = None  # TODO: Add path resolver

        self.executor = ThreadPoolExecutor(max_workers=4)
        self.running = False

    def start_watching_all(self):
        """Start watching all registered repositories."""
        self.running = True

        for repo_id, repo_info in self.registry.get_all_repositories().items():
            if repo_info.auto_sync:
                self._start_repo_watcher(repo_id, repo_info.path)

        # Start git monitor
        self.git_monitor.start()

        logger.info(f"Started watching {len(self.watchers)} repositories")

    def stop_watching_all(self):
        """Stop all watchers."""
        self.running = False

        # Stop git monitor
        self.git_monitor.stop()

        # Stop all file watchers
        for repo_id, observer in self.observers.items():
            observer.stop()
            observer.join(timeout=5)

        self.watchers.clear()
        self.observers.clear()

        logger.info("Stopped all repository watchers")

    def add_repository(self, repo_path: str) -> str:
        """Add a new repository to watch.

        Args:
            repo_path: Repository path

        Returns:
            Repository ID
        """
        repo_id = self.registry.register_repository(repo_path)

        if self.running:
            self._start_repo_watcher(repo_id, repo_path)

        return repo_id

    def remove_repository(self, repo_id: str):
        """Remove a repository from watching.

        Args:
            repo_id: Repository ID
        """
        if repo_id in self.observers:
            observer = self.observers[repo_id]
            observer.stop()
            observer.join(timeout=5)

            del self.observers[repo_id]
            del self.watchers[repo_id]

        self.registry.unregister_repository(repo_id)

    def _start_repo_watcher(self, repo_id: str, repo_path: str):
        """Start watching a specific repository.

        Args:
            repo_id: Repository ID
            repo_path: Repository path
        """
        if repo_id in self.observers:
            # Already watching
            return

        try:
            path = Path(repo_path)
            if not path.exists():
                logger.error(f"Repository path does not exist: {repo_path}")
                return

            # Create handler for this repository
            handler = MultiRepositoryHandler(repo_id, path, self)

            # Create and start observer
            observer = Observer()
            observer.schedule(handler, str(path), recursive=True)
            observer.start()

            self.observers[repo_id] = observer
            self.watchers[repo_id] = handler

            logger.info(f"Started watching repository: {repo_id} at {repo_path}")

        except Exception as e:
            logger.error(f"Failed to start watcher for {repo_id}: {e}")

    def mark_repository_changed(self, repo_id: str):
        """Mark a repository as having uncommitted changes.

        Args:
            repo_id: Repository ID
        """
        self.changed_repos.add(repo_id)

    def on_git_commit(self, repo_id: str, commit: str):
        """Handle new git commit in repository.

        Args:
            repo_id: Repository ID
            commit: New commit SHA
        """
        logger.info(f"Processing new commit in {repo_id}: {commit[:8]}")

        # Remove from changed set (changes are now committed)
        self.changed_repos.discard(repo_id)

        # Submit index sync task
        _ = self.executor.submit(self._sync_repository, repo_id, commit)

    def _sync_repository(self, repo_id: str, commit: str):
        """Sync repository index with new commit.

        Args:
            repo_id: Repository ID
            commit: Git commit SHA
        """
        try:
            # Sync the index
            result = self.index_manager.sync_repository_index(repo_id)

            if result.action == "indexed" and result.files_processed > 0:
                logger.info(
                    f"Repository {repo_id} synced: "
                    f"{result.files_processed} files in {result.duration_seconds:.2f}s"
                )

                # Create and upload artifact if enabled
                repo_info = self.registry.get_repository(repo_id)
                if repo_info and repo_info.artifact_enabled:
                    self._create_and_upload_artifact(repo_id, commit)

        except Exception as e:
            logger.error(f"Failed to sync repository {repo_id}: {e}")

    def _create_and_upload_artifact(self, repo_id: str, commit: str):
        """Create and upload artifact for commit.

        Args:
            repo_id: Repository ID
            commit: Git commit SHA
        """
        try:
            repo_info = self.registry.get_repository(repo_id)
            if not repo_info:
                return

            index_path = Path(repo_info.index_location)

            # Create artifact
            artifact_path = self.artifact_manager.create_commit_artifact(
                repo_id, commit, index_path
            )

            if artifact_path:
                logger.info(f"Created artifact for {repo_id} commit {commit[:8]}")

                # TODO: Upload to GitHub artifacts

                # Clean up old artifacts
                removed = self.artifact_manager.cleanup_old_artifacts(repo_id, keep_last=5)
                if removed > 0:
                    logger.info(f"Removed {removed} old artifacts for {repo_id}")

        except Exception as e:
            logger.error(f"Failed to create artifact for {repo_id}: {e}")

    def sync_all_repositories(self):
        """Manually trigger sync for all repositories."""
        futures = []

        for repo_id, repo_info in self.registry.get_all_repositories().items():
            if repo_info.auto_sync:
                future = self.executor.submit(self.index_manager.sync_repository_index, repo_id)
                futures.append((repo_id, future))

        # Wait for all to complete
        for repo_id, future in futures:
            try:
                result = future.result(timeout=300)  # 5 minute timeout
                logger.info(f"Synced {repo_id}: {result.action}")
            except Exception as e:
                logger.error(f"Failed to sync {repo_id}: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get status of all watched repositories.

        Returns:
            Status dictionary
        """
        status = {"watching": len(self.watchers), "repositories": {}}

        for repo_id in self.watchers:
            repo_info = self.registry.get_repository(repo_id)
            if repo_info:
                repo_status = self.index_manager.get_repository_status(repo_id)
                repo_status["has_uncommitted_changes"] = repo_id in self.changed_repos
                status["repositories"][repo_id] = repo_status

        return status
