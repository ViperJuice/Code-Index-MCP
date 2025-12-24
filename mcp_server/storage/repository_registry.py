"""
Repository Registry for Multi-Repository Management

This module handles persistent storage and management of repository
registration information for cross-repository search.
"""

import json
import logging
import os
import subprocess
import threading
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class RepositoryRegistry:
    """
    Manages persistent registry of repositories for multi-repository search.

    Features:
    - JSON-based persistent storage
    - Thread-safe operations
    - Repository metadata management
    - Active/inactive status tracking
    """

    def __init__(self, registry_path: Optional[Path] = None):
        """
        Initialize the repository registry.

        Args:
            registry_path: Path to registry JSON file. Defaults to ~/.mcp/repository_registry.json
        """
        self.registry_path = registry_path or self._get_default_registry_path()
        self._lock = threading.RLock()
        self._registry: Dict[str, Dict[str, Any]] = {}

        # Ensure parent directory exists
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing registry
        self._load()

        logger.info(f"Repository registry initialized at {registry_path}")

    def _get_default_registry_path(self) -> Path:
        """Return the default registry path under the user home directory."""
        env_path = os.environ.get("MCP_REPO_REGISTRY")
        if env_path:
            return Path(env_path)

        home = Path.home()
        return home / ".mcp" / "repository_registry.json"

    def _load(self):
        """Load registry from disk."""
        if not self.registry_path.exists():
            logger.info("No existing registry found, starting fresh")
            return

        try:
            with open(self.registry_path, "r") as f:
                data = json.load(f)

            # Convert back to proper types
            for repo_id, repo_data in data.items():
                # Convert paths
                repo_data["path"] = Path(repo_data["path"])
                repo_data["index_path"] = Path(repo_data["index_path"])

                # Convert datetime
                if "indexed_at" in repo_data:
                    repo_data["indexed_at"] = datetime.fromisoformat(repo_data["indexed_at"])
                if "last_indexed" in repo_data and repo_data["last_indexed"]:
                    repo_data["last_indexed"] = datetime.fromisoformat(repo_data["last_indexed"])

                self._registry[repo_id] = repo_data

            logger.info(f"Loaded {len(self._registry)} repositories from registry")

        except Exception as e:
            logger.error(f"Failed to load registry: {e}")
            self._registry = {}

    def save(self):
        """Save registry to disk."""
        with self._lock:
            try:
                # Convert to JSON-serializable format
                data = {}
                for repo_id, repo_info in self._registry.items():
                    # Create a copy to avoid modifying original
                    repo_data = repo_info.copy()

                    # Convert paths to strings
                    repo_data["path"] = str(repo_data["path"])
                    repo_data["index_path"] = str(repo_data["index_path"])

                    # Convert datetime to ISO format
                    if "indexed_at" in repo_data and hasattr(repo_data["indexed_at"], "isoformat"):
                        repo_data["indexed_at"] = repo_data["indexed_at"].isoformat()
                    if "last_indexed" in repo_data and hasattr(
                        repo_data["last_indexed"], "isoformat"
                    ):
                        repo_data["last_indexed"] = repo_data["last_indexed"].isoformat()

                    if "index_location" in repo_data:
                        repo_data["index_location"] = str(repo_data["index_location"])

                    data[repo_id] = repo_data

                # Write to temporary file first
                temp_path = self.registry_path.with_suffix(".tmp")
                with open(temp_path, "w") as f:
                    json.dump(data, f, indent=2)

                # Atomic rename
                temp_path.replace(self.registry_path)

                logger.debug(f"Saved {len(data)} repositories to registry")

            except Exception as e:
                logger.error(f"Failed to save registry: {e}")

    def register(self, repo_info):
        """
        Register a repository.

        Args:
            repo_info: RepositoryInfo dataclass instance
        """
        with self._lock:
            # Convert dataclass to dict
            repo_data = asdict(repo_info)

            # Store in registry
            self._registry[repo_info.repository_id] = repo_data

            # Save to disk
            self.save()

            logger.info(f"Registered repository: {repo_info.name} ({repo_info.repository_id})")

    def unregister(self, repository_id: str):
        """
        Unregister a repository.

        Args:
            repository_id: ID of repository to unregister
        """
        with self._lock:
            if repository_id in self._registry:
                repo_name = self._registry[repository_id].get("name", "Unknown")
                del self._registry[repository_id]
                self.save()
                logger.info(f"Unregistered repository: {repo_name} ({repository_id})")
            else:
                logger.warning(f"Repository {repository_id} not found in registry")

    def get(self, repository_id: str) -> Optional[Any]:
        """
        Get repository information.

        Args:
            repository_id: ID of repository

        Returns:
            RepositoryInfo-like dict or None if not found
        """
        with self._lock:
            repo_data = self._registry.get(repository_id)
            if repo_data:
                # Return a copy to prevent external modifications
                return self._dict_to_repo_info(repo_data.copy())
            return None

    def get_repository(self, repository_id: str) -> Optional[Any]:
        """
        Get repository information (alias for get).

        Args:
            repository_id: Repository identifier.

        Returns:
            RepositoryInfo or None.
        """
        return self.get(repository_id)

    def list_all(self) -> List[Any]:
        """
        List all registered repositories.

        Returns:
            List of RepositoryInfo-like objects
        """
        with self._lock:
            repos = []
            for repo_data in self._registry.values():
                repos.append(self._dict_to_repo_info(repo_data.copy()))
            return repos

    def _dict_to_repo_info(self, repo_dict: Dict[str, Any]) -> Any:
        """Convert dictionary back to RepositoryInfo-like object."""
        # Import here to avoid circular imports
        from mcp_server.storage.multi_repo_manager import RepositoryInfo

        # Ensure paths are Path objects
        if isinstance(repo_dict.get("path"), str):
            repo_dict["path"] = Path(repo_dict["path"])
        if isinstance(repo_dict.get("index_path"), str):
            repo_dict["index_path"] = Path(repo_dict["index_path"])

        # Ensure datetime is parsed
        if isinstance(repo_dict.get("indexed_at"), str):
            repo_dict["indexed_at"] = datetime.fromisoformat(repo_dict["indexed_at"])
        if isinstance(repo_dict.get("last_indexed"), str):
            repo_dict["last_indexed"] = datetime.fromisoformat(repo_dict["last_indexed"])

        return RepositoryInfo(**repo_dict)

    def update_status(self, repository_id: str, active: bool):
        """
        Update repository active status.

        Args:
            repository_id: ID of repository
            active: New active status
        """
        with self._lock:
            if repository_id in self._registry:
                self._registry[repository_id]["active"] = active
                self.save()
                status = "activated" if active else "deactivated"
                logger.info(f"Repository {repository_id} {status}")
            else:
                logger.warning(f"Repository {repository_id} not found in registry")

    def update_priority(self, repository_id: str, priority: int):
        """
        Update repository search priority.

        Args:
            repository_id: ID of repository
            priority: New priority (higher = searched first)
        """
        with self._lock:
            if repository_id in self._registry:
                self._registry[repository_id]["priority"] = priority
                self.save()
                logger.info(f"Repository {repository_id} priority set to {priority}")
            else:
                logger.warning(f"Repository {repository_id} not found in registry")

    def update_statistics(self, repository_id: str, stats: Dict[str, Any]):
        """
        Update repository statistics.

        Args:
            repository_id: ID of repository
            stats: New statistics (language_stats, total_files, total_symbols)
        """
        with self._lock:
            if repository_id in self._registry:
                repo = self._registry[repository_id]

                # Update statistics
                if "language_stats" in stats:
                    repo["language_stats"] = stats["language_stats"]
                if "total_files" in stats:
                    repo["total_files"] = stats["total_files"]
                if "total_symbols" in stats:
                    repo["total_symbols"] = stats["total_symbols"]

                # Update indexed timestamp
                repo["indexed_at"] = datetime.now()

                self.save()
                logger.info(f"Updated statistics for repository {repository_id}")
            else:
                logger.warning(f"Repository {repository_id} not found in registry")

    def update_current_commit(self, repository_id: str) -> Optional[str]:
        """
        Refresh the current commit for a repository by reading its git HEAD.

        Args:
            repository_id: Repository identifier.

        Returns:
            The commit SHA if updated, otherwise None.
        """
        with self._lock:
            repo = self._registry.get(repository_id)
            if not repo:
                logger.warning(f"Repository {repository_id} not found in registry")
                return None

            repo_path = Path(repo["path"])

        commit = self._get_git_commit(repo_path)
        if commit:
            with self._lock:
                self._registry[repository_id]["current_commit"] = commit
                self.save()
            return commit

        return None

    def update_indexed_commit(self, repository_id: str, commit: str) -> Optional[str]:
        """
        Persist the last indexed commit for a repository.

        Args:
            repository_id: Repository identifier.
            commit: Commit SHA that was indexed.

        Returns:
            The stored commit SHA, or None if the repository was not found.
        """
        with self._lock:
            repo = self._registry.get(repository_id)
            if not repo:
                logger.warning(f"Repository {repository_id} not found in registry")
                return None

            repo["last_indexed_commit"] = commit
            repo["last_indexed"] = datetime.now()
            self.save()
            return commit

    def get_repositories_needing_update(self) -> List[Tuple[str, Any]]:
        """
        Return repositories where the current commit differs from the last indexed commit.

        Returns:
            List of tuples containing repository ID and RepositoryInfo.
        """
        stale: List[Tuple[str, Any]] = []
        with self._lock:
            for repo_id, repo_data in self._registry.items():
                repo_info = self._dict_to_repo_info(repo_data.copy())
                if repo_info.needs_update():
                    stale.append((repo_id, repo_info))
        return stale

    def _get_git_commit(self, repo_path: Path) -> Optional[str]:
        """Return the HEAD commit SHA for a repository path."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as exc:
            logger.error(f"Failed to read git commit for {repo_path}: {exc}")
        except FileNotFoundError:
            logger.error("Git is not installed or not available in PATH")
        return None

    def find_by_path(self, path: Path) -> Optional[str]:
        """
        Find repository ID by path.

        Args:
            path: Repository path

        Returns:
            Repository ID or None if not found
        """
        with self._lock:
            path_str = str(path.absolute())

            for repo_id, repo_data in self._registry.items():
                repo_path = repo_data.get("path")
                if isinstance(repo_path, str):
                    repo_path = Path(repo_path)

                if str(repo_path.absolute()) == path_str:
                    return repo_id

            return None

    def get_statistics(self) -> Dict[str, Any]:
        """Get registry statistics."""
        with self._lock:
            total = len(self._registry)
            active = sum(1 for r in self._registry.values() if r.get("active", True))

            # Language distribution
            all_languages = {}
            total_files = 0
            total_symbols = 0

            for repo in self._registry.values():
                lang_stats = repo.get("language_stats", {})
                for lang, count in lang_stats.items():
                    all_languages[lang] = all_languages.get(lang, 0) + count

                total_files += repo.get("total_files", 0)
                total_symbols += repo.get("total_symbols", 0)

            return {
                "total_repositories": total,
                "active_repositories": active,
                "inactive_repositories": total - active,
                "total_files": total_files,
                "total_symbols": total_symbols,
                "languages": all_languages,
                "registry_size_bytes": (
                    self.registry_path.stat().st_size if self.registry_path.exists() else 0
                ),
            }

    def cleanup(self):
        """Clean up invalid or missing repositories."""
        with self._lock:
            to_remove = []

            for repo_id, repo_data in self._registry.items():
                # Check if paths still exist
                index_path = repo_data.get("index_path")
                if isinstance(index_path, str):
                    index_path = Path(index_path)

                if not index_path or not index_path.exists():
                    to_remove.append(repo_id)
                    logger.warning(f"Repository {repo_id} has missing index, marking for removal")

            # Remove invalid entries
            for repo_id in to_remove:
                del self._registry[repo_id]

            if to_remove:
                self.save()
                logger.info(f"Cleaned up {len(to_remove)} invalid repository entries")

            return len(to_remove)
