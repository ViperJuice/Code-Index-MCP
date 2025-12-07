"""
Path utilities for environment-agnostic path management.

This module provides centralized path operations that work across different
environments (Docker, native, CI/CD) without hardcoded paths.
"""

import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional, Union

logger = logging.getLogger(__name__)


class PathUtils:
    """Centralized path management utilities."""

    # Environment variable names
    ENV_WORKSPACE_ROOT = "MCP_WORKSPACE_ROOT"
    ENV_INDEX_STORAGE = "MCP_INDEX_STORAGE_PATH"
    ENV_REPO_REGISTRY = "MCP_REPO_REGISTRY"
    ENV_TEMP_PATH = "MCP_TEMP_PATH"
    ENV_LOG_PATH = "MCP_LOG_PATH"
    ENV_DATA_PATH = "MCP_DATA_PATH"
    ENV_PYTHON_PATH = "MCP_PYTHON_PATH"

    # Docker path mappings
    DOCKER_MAPPINGS = {
        "/app": "{workspace_root}",
        "/workspaces/Code-Index-MCP": "{workspace_root}",
        "/data": "{data_path}",
        "/tmp/mcp-indexes": "{temp_path}/mcp-indexes",
        "/var/log/mcp-server": "{log_path}",
        "/home/vscode/.claude": "{home}/.claude",
    }

    @classmethod
    def get_workspace_root(cls) -> Path:
        """
        Get workspace root with intelligent fallback logic.

        Returns:
            Path to workspace root directory
        """
        # Check environment variable first
        if env_root := os.environ.get(cls.ENV_WORKSPACE_ROOT):
            return Path(env_root).resolve()

        # Try to detect from git repository
        current = Path.cwd()
        while current != current.parent:
            if (current / ".git").exists():
                logger.debug(f"Detected workspace root from .git: {current}")
                return current
            current = current.parent

        # Fall back to current directory
        logger.debug(f"Using current directory as workspace root: {Path.cwd()}")
        return Path.cwd()

    @classmethod
    def get_index_storage_path(cls) -> Path:
        """
        Get index storage path based on environment.

        Returns:
            Path to index storage directory
        """
        if env_path := os.environ.get(cls.ENV_INDEX_STORAGE):
            path = Path(env_path)
            # Expand ~ to home directory
            if str(path).startswith("~"):
                path = path.expanduser()
            return path.resolve()

        # Default to .indexes in workspace
        return cls.get_workspace_root() / ".indexes"

    @classmethod
    def get_repo_registry_path(cls) -> Path:
        """
        Get repository registry path.

        Returns:
            Path to repository registry JSON file
        """
        if env_path := os.environ.get(cls.ENV_REPO_REGISTRY):
            path = Path(env_path)
            if str(path).startswith("~"):
                path = path.expanduser()
            return path.resolve()

        # Default to index storage location
        return cls.get_index_storage_path() / "repository_registry.json"

    @classmethod
    def get_temp_path(cls) -> Path:
        """
        Get temporary directory path.

        Returns:
            Path to temporary directory
        """
        if env_path := os.environ.get(cls.ENV_TEMP_PATH):
            return Path(env_path).resolve()

        return Path(tempfile.gettempdir())

    @classmethod
    def get_log_path(cls) -> Path:
        """
        Get log directory path.

        Returns:
            Path to log directory
        """
        if env_path := os.environ.get(cls.ENV_LOG_PATH):
            path = Path(env_path)
            if str(path).startswith("~"):
                path = path.expanduser()
            return path.resolve()

        # Default to ~/.mcp/logs
        return Path.home() / ".mcp" / "logs"

    @classmethod
    def get_data_path(cls) -> Path:
        """
        Get data directory path.

        Returns:
            Path to data directory
        """
        if env_path := os.environ.get(cls.ENV_DATA_PATH):
            return Path(env_path).resolve()

        # Default to workspace/data
        return cls.get_workspace_root() / "data"

    @classmethod
    def get_test_repos_path(cls) -> Path:
        """
        Get test repositories path.

        Returns:
            Path to test repositories directory
        """
        # Check for specific test repos environment variable
        if env_path := os.environ.get("MCP_TEST_REPOS_PATH"):
            return Path(env_path).resolve()

        # Default to workspace/test_repos
        return cls.get_workspace_root() / "test_repos"

    @classmethod
    def get_python_executable(cls) -> str:
        """
        Get Python executable path.

        Returns:
            Path to Python executable
        """
        if env_path := os.environ.get(cls.ENV_PYTHON_PATH):
            return env_path

        # Try common locations
        for python in ["python3", "python", "/usr/local/bin/python"]:
            if os.system(f"which {python} > /dev/null 2>&1") == 0:
                return python

        # Fall back to sys.executable
        import sys

        return sys.executable

    @classmethod
    def translate_docker_path(cls, path: Union[str, Path]) -> Path:
        """
        Translate Docker-specific paths to environment-agnostic paths.

        Args:
            path: Path that may contain Docker-specific components

        Returns:
            Translated path suitable for current environment
        """
        path_str = str(path)

        # Check each Docker mapping
        for docker_path, template in cls.DOCKER_MAPPINGS.items():
            if path_str.startswith(docker_path):
                # Replace Docker path with template
                remaining = path_str[len(docker_path) :]
                if remaining.startswith("/"):
                    remaining = remaining[1:]

                # Substitute template variables
                template = template.format(
                    workspace_root=cls.get_workspace_root(),
                    data_path=cls.get_data_path(),
                    temp_path=cls.get_temp_path(),
                    log_path=cls.get_log_path(),
                    home=Path.home(),
                )

                # Combine with remaining path
                result = Path(template) / remaining if remaining else Path(template)
                logger.debug(f"Translated {path} -> {result}")
                return result

        # Return original path if no translation needed
        return Path(path)

    @classmethod
    def ensure_directory(cls, path: Path) -> Path:
        """
        Ensure directory exists, creating if necessary.

        Args:
            path: Directory path to ensure

        Returns:
            Path object (created if necessary)
        """
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def get_relative_to_workspace(cls, path: Union[str, Path]) -> str:
        """
        Get path relative to workspace root.

        Args:
            path: Absolute or relative path

        Returns:
            Path relative to workspace root as string
        """
        path = Path(path).resolve()
        workspace = cls.get_workspace_root()

        try:
            return str(path.relative_to(workspace)).replace("\\", "/")
        except ValueError:
            # Path is outside workspace
            return str(path)

    @classmethod
    def resolve_path(cls, path: Union[str, Path], base: Optional[Path] = None) -> Path:
        """
        Resolve path with smart handling of relative/absolute paths.

        Args:
            path: Path to resolve
            base: Base directory for relative paths (default: workspace root)

        Returns:
            Resolved absolute path
        """
        path = Path(path)

        # Handle ~ expansion
        if str(path).startswith("~"):
            path = path.expanduser()

        # If absolute, translate Docker paths
        if path.is_absolute():
            return cls.translate_docker_path(path)

        # For relative paths, use base or workspace root
        base = base or cls.get_workspace_root()
        return (base / path).resolve()

    @classmethod
    def is_docker_environment(cls) -> bool:
        """
        Check if running in Docker container.

        Returns:
            True if in Docker environment
        """
        return (
            os.path.exists("/.dockerenv")
            or os.environ.get("DOCKER_CONTAINER") is not None
            or os.environ.get("CONTAINER") is not None
        )

    @classmethod
    def is_test_environment(cls) -> bool:
        """
        Check if running in test environment.

        Returns:
            True if in test environment
        """
        return (
            os.environ.get("PYTEST_CURRENT_TEST") is not None
            or "pytest" in os.environ.get("_", "")
            or "test" in str(Path.cwd())
        )

    @classmethod
    def get_environment_info(cls) -> Dict[str, Any]:
        """
        Get comprehensive environment information.

        Returns:
            Dictionary with environment details
        """
        return {
            "workspace_root": str(cls.get_workspace_root()),
            "index_storage": str(cls.get_index_storage_path()),
            "repo_registry": str(cls.get_repo_registry_path()),
            "temp_path": str(cls.get_temp_path()),
            "log_path": str(cls.get_log_path()),
            "data_path": str(cls.get_data_path()),
            "test_repos": str(cls.get_test_repos_path()),
            "python_exe": cls.get_python_executable(),
            "is_docker": cls.is_docker_environment(),
            "is_test": cls.is_test_environment(),
            "platform": os.name,
            "cwd": str(Path.cwd()),
        }


# Convenience functions for backward compatibility
def get_workspace_root() -> Path:
    """Get workspace root directory."""
    return PathUtils.get_workspace_root()


def get_index_storage_path() -> Path:
    """Get index storage path."""
    return PathUtils.get_index_storage_path()


def get_test_repos_path() -> Path:
    """Get test repositories path."""
    return PathUtils.get_test_repos_path()


def translate_docker_path(path: Union[str, Path]) -> Path:
    """Translate Docker paths to native paths."""
    return PathUtils.translate_docker_path(path)


def resolve_path(path: Union[str, Path], base: Optional[Path] = None) -> Path:
    """Resolve path with smart handling."""
    return PathUtils.resolve_path(path, base)
