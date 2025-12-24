"""
Index Path Configuration for Multi-Path Discovery

This module defines the search paths and priorities for finding MCP indexes
across different environments (Docker, native, test, etc.).
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from mcp_server.core.path_utils import PathUtils

if TYPE_CHECKING:
    from mcp_server.storage.artifact_registry import ArtifactRecord, ArtifactRegistry

logger = logging.getLogger(__name__)


class IndexPathConfig:
    """Configuration for index path discovery with multi-environment support."""

    # Default search paths in priority order
    DEFAULT_SEARCH_PATHS = [
        ".indexes/{repo_hash}",  # Centralized location (primary)
        ".mcp-index",  # Legacy location
        "/workspaces/{project}/.indexes",  # Docker/Dev container absolute
        "test_indexes/{repo}",  # Test repository indexes
        "~/.mcp/indexes/{repo_hash}",  # User-level indexes
        "/tmp/mcp-indexes/{repo_hash}",  # Temporary indexes
    ]

    def __init__(
        self,
        custom_paths: Optional[List[str]] = None,
        artifact_registry: Optional["ArtifactRegistry"] = None,
        cache_path: Optional[Path] = None,
    ):
        """
        Initialize index path configuration.

        Args:
            custom_paths: Optional list of custom search paths to use instead of defaults
        """
        self.search_paths = self._parse_search_paths(custom_paths)
        self.environment = self._detect_environment()
        self.cache_path = cache_path or PathUtils.get_index_storage_path() / "artifact_discovery_cache.json"
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.artifact_registry = artifact_registry or self._create_artifact_registry()

    def _parse_search_paths(self, custom_paths: Optional[List[str]] = None) -> List[str]:
        """Parse search paths from environment or use defaults."""
        if custom_paths:
            return custom_paths

        # Check environment variable for custom paths
        env_paths = os.environ.get("MCP_INDEX_PATHS")
        if env_paths:
            return env_paths.split(":")

        return self.DEFAULT_SEARCH_PATHS.copy()

    def _detect_environment(self) -> Dict[str, Any]:
        """Detect the current environment (Docker, native, test, etc.)."""
        env_info = {
            "is_docker": False,
            "is_test": False,
            "is_ci": False,
            "project_name": None,
            "workspace_root": None,
        }

        # Check if running in Docker
        if os.path.exists("/.dockerenv") or os.environ.get("DOCKER_CONTAINER"):
            env_info["is_docker"] = True

        # Check if in test environment
        if os.environ.get("PYTEST_CURRENT_TEST") or "test" in str(Path.cwd()):
            env_info["is_test"] = True

        # Check if in CI environment
        if os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"):
            env_info["is_ci"] = True

        # Detect workspace root
        workspace = os.environ.get("GITHUB_WORKSPACE") or os.environ.get("WORKSPACE_ROOT")
        if workspace:
            env_info["workspace_root"] = Path(workspace)
        elif Path("/workspaces").exists():
            # Dev container environment
            workspaces = list(Path("/workspaces").iterdir())
            if workspaces:
                env_info["workspace_root"] = workspaces[0]
                env_info["project_name"] = workspaces[0].name

        logger.debug(f"Detected environment: {env_info}")
        return env_info

    def get_search_paths(self, repo_identifier: Optional[str] = None) -> List[Path]:
        """
        Get concrete search paths for a specific repository.

        Args:
            repo_identifier: Repository name, hash, or identifier

        Returns:
            List of Path objects to search for indexes
        """
        paths = []

        # Get repository hash if possible
        repo_hash = self._get_repo_hash(repo_identifier)
        repo_name = self._get_repo_name(repo_identifier)

        for template in self.search_paths:
            # Substitute variables in path templates
            path = template

            # Replace {repo_hash}
            if "{repo_hash}" in path and repo_hash:
                path = path.replace("{repo_hash}", repo_hash)
            elif "{repo_hash}" in path:
                continue  # Skip if we need hash but don't have it

            # Replace {repo}
            if "{repo}" in path and repo_name:
                path = path.replace("{repo}", repo_name)
            elif "{repo}" in path:
                continue  # Skip if we need name but don't have it

            # Replace {project}
            if "{project}" in path:
                if self.environment["project_name"]:
                    path = path.replace("{project}", self.environment["project_name"])
                else:
                    continue  # Skip if we need project but don't have it

            # Expand user home directory
            if path.startswith("~"):
                path = os.path.expanduser(path)

            # Convert to Path object
            path_obj = Path(path)

            # Make absolute if relative
            if not path_obj.is_absolute():
                path_obj = Path.cwd() / path_obj

            paths.append(path_obj)

        # Add any workspace-specific paths
        if self.environment["workspace_root"]:
            workspace_indexes = self.environment["workspace_root"] / ".indexes"
            if workspace_indexes not in paths:
                paths.insert(0, workspace_indexes)

        # Remove duplicates while preserving order
        seen = set()
        unique_paths = []
        for path in paths:
            if path not in seen:
                seen.add(path)
                unique_paths.append(path)

        logger.debug(f"Search paths for {repo_identifier}: {unique_paths}")
        return unique_paths

    def _get_repo_hash(self, repo_identifier: Optional[str]) -> Optional[str]:
        """Get repository hash from identifier."""
        if not repo_identifier:
            return None

        # If already a hash (12-16 hex chars), return it
        if len(repo_identifier) in range(12, 17) and all(
            c in "0123456789abcdef" for c in repo_identifier
        ):
            return repo_identifier

        # Try to compute hash from repo name/URL
        try:
            import hashlib

            # Simple hash for demo - in production, this would match the actual repo hash logic
            return hashlib.sha256(repo_identifier.encode()).hexdigest()[:12]
        except Exception:
            return None

    def _get_repo_name(self, repo_identifier: Optional[str]) -> Optional[str]:
        """Extract repository name from identifier."""
        if not repo_identifier:
            return None

        # If it's a path, get the last component
        if "/" in repo_identifier:
            return repo_identifier.split("/")[-1]

        # If it's a URL, extract repo name
        if repo_identifier.startswith(("http://", "https://", "git@")):
            # Simple extraction - in production would be more robust
            parts = repo_identifier.rstrip("/").split("/")
            if len(parts) >= 2:
                repo_name = parts[-1]
                if repo_name.endswith(".git"):
                    repo_name = repo_name[:-4]
                return repo_name

        # Otherwise assume it's already a name
        return repo_identifier

    def add_search_path(self, path: str, priority: int = -1):
        """
        Add a custom search path.

        Args:
            path: Path template to add
            priority: Position in search order (-1 for end, 0 for beginning)
        """
        if priority == -1:
            self.search_paths.append(path)
        else:
            self.search_paths.insert(priority, path)

    def remove_search_path(self, path: str):
        """Remove a search path from the configuration."""
        if path in self.search_paths:
            self.search_paths.remove(path)

    def validate_paths(self, repo_identifier: Optional[str] = None) -> Dict[Path, bool]:
        """
        Validate which search paths exist.

        Returns:
            Dictionary mapping paths to existence status
        """
        results = {}
        for path in self.get_search_paths(repo_identifier):
            results[path] = path.exists()
        return results

    def cache_discovery(
        self,
        repo_identifier: str,
        path: Path,
        commit: Optional[str] = None,
        model: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Persist details about a discovered artifact for quick reuse."""
        if not repo_identifier:
            return

        model_name = model or "default"
        version = commit or "unknown"
        try:
            if self.artifact_registry:
                self.artifact_registry.add_or_update(
                    repo_identifier,
                    model_name,
                    version,
                    path,
                    commit=commit,
                    metadata=metadata or {},
                    source="discovery",
                )
        except Exception as e:
            logger.debug(f"Failed to cache discovery for {repo_identifier}: {e}")

        cache = self._load_cache()
        cache[repo_identifier] = {
            "path": str(path),
            "commit": commit,
            "model": model,
            "version": version,
            "cached_at": self._utcnow_iso(),
        }
        self._save_cache(cache)

    def get_cached_artifact(
        self, repo_identifier: str, model: Optional[str] = None
    ) -> Optional[Tuple[Path, Optional[str], Optional[str]]]:
        """Return cached artifact info if available."""
        if not repo_identifier:
            return None

        if self.artifact_registry:
            try:
                record = self.artifact_registry.find_best_match(repo_identifier, model=model)
                if record:
                    return record.path, record.commit, record.model
            except Exception as e:
                logger.debug(f"Artifact registry lookup failed: {e}")

        cache = self._load_cache()
        cached = cache.get(repo_identifier)
        if cached:
            path = Path(cached["path"])
            if path.exists():
                if model and cached.get("model") and cached["model"] != model:
                    return None
                return path, cached.get("commit"), cached.get("model")
        return None

    def _load_cache(self) -> Dict[str, Dict[str, Any]]:
        """Load discovery cache from disk."""
        if self.cache_path.exists():
            try:
                with open(self.cache_path, "r") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_cache(self, cache: Dict[str, Dict[str, Any]]) -> None:
        """Persist discovery cache to disk."""
        try:
            temp_path = self.cache_path.with_suffix(".tmp")
            with open(temp_path, "w") as f:
                json.dump(cache, f, indent=2)
            temp_path.replace(self.cache_path)
        except Exception as e:
            logger.debug(f"Failed to write discovery cache: {e}")

    def _create_artifact_registry(self) -> Optional["ArtifactRegistry"]:
        """Lazy-create the artifact registry without introducing hard dependency failures."""
        from mcp_server.storage.artifact_registry import ArtifactRegistry

        try:
            return ArtifactRegistry()
        except Exception as e:
            logger.debug(f"Artifact registry unavailable: {e}")
            return None

    @staticmethod
    def _utcnow_iso() -> str:
        """Get current UTC time in ISO format."""
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).isoformat()
