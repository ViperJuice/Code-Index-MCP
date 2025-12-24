"""
Utility module for handling ignore patterns from .gitignore and .mcp-index-ignore files.
"""

import fnmatch
import logging
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


class IgnorePatternManager:
    """Manages ignore patterns from various sources."""

    def __init__(self, root_path: Path = None):
        """
        Initialize the ignore pattern manager.

        Args:
            root_path: Root directory to look for ignore files. Defaults to current directory.
        """
        self.root_path = root_path or Path.cwd()
        self._patterns: List[str] = []
        self._gitignore_patterns: List[str] = []
        self._mcp_ignore_patterns: List[str] = []
        self._load_patterns()

    def _load_patterns(self):
        """Load patterns from all ignore files."""
        # Load .gitignore patterns
        self._gitignore_patterns = self._load_gitignore_patterns()

        # Load .mcp-index-ignore patterns
        self._mcp_ignore_patterns = self._load_mcp_ignore_patterns()

        # Combine all patterns
        self._patterns = self._gitignore_patterns + self._mcp_ignore_patterns

        logger.info(f"Loaded {len(self._patterns)} ignore patterns total")

    def _load_gitignore_patterns(self) -> List[str]:
        """Load patterns from .gitignore file."""
        patterns = []
        gitignore_path = self.root_path / ".gitignore"

        if gitignore_path.exists():
            try:
                with open(gitignore_path, "r") as f:
                    for line in f:
                        line = line.strip()
                        # Skip comments and empty lines
                        if line and not line.startswith("#"):
                            # Skip negation patterns for now
                            if not line.startswith("!"):
                                patterns.append(line)
                logger.debug(f"Loaded {len(patterns)} patterns from .gitignore")
            except Exception as e:
                logger.error(f"Error reading .gitignore: {e}")

        return patterns

    def _load_mcp_ignore_patterns(self) -> List[str]:
        """Load patterns from .mcp-index-ignore file."""
        patterns = []
        ignore_path = self.root_path / ".mcp-index-ignore"

        # Default patterns if file doesn't exist
        default_patterns = [
            "*.env",
            ".env*",
            "*.key",
            "*.pem",
            "*.p12",
            "*secret*",
            "*password*",
            "*.credentials",
            "config/secrets/*",
            ".aws/*",
            ".ssh/*",
            "*.pyc",
            "__pycache__/*",
            "node_modules/*",
            ".git/*",
            "*.log",
            "*.tmp",
            "*.temp",
            "*.cache",
        ]

        if ignore_path.exists():
            try:
                with open(ignore_path, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            patterns.append(line)
                logger.debug(f"Loaded {len(patterns)} patterns from .mcp-index-ignore")
            except Exception as e:
                logger.error(f"Error reading .mcp-index-ignore: {e}")
        else:
            # Use default patterns if file doesn't exist
            patterns = default_patterns
            logger.debug(f"Using {len(patterns)} default security patterns")

        return patterns

    def should_ignore(self, file_path: Path) -> bool:
        """
        Check if a file should be ignored based on all patterns.

        Args:
            file_path: Path to check (can be absolute or relative)

        Returns:
            True if file should be ignored, False otherwise
        """
        # Convert to relative path for pattern matching
        try:
            if file_path.is_absolute():
                rel_path = file_path.relative_to(self.root_path)
            else:
                rel_path = file_path
        except ValueError:
            # Path is outside root, use as-is
            rel_path = file_path

        # Convert to string for pattern matching
        path_str = str(rel_path).replace("\\", "/")

        for pattern in self._patterns:
            # Handle directory patterns
            if pattern.endswith("/"):
                # Check if any parent directory matches
                for parent in rel_path.parents:
                    if fnmatch.fnmatch(parent.name, pattern[:-1]):
                        return True
                # Check if the path itself is a directory matching the pattern
                if rel_path.name == pattern[:-1]:
                    return True
            else:
                # Check file patterns
                if fnmatch.fnmatch(path_str, pattern):
                    return True
                # Also check just the filename
                if fnmatch.fnmatch(rel_path.name, pattern):
                    return True

        return False

    def get_patterns(self) -> List[str]:
        """Get all loaded patterns."""
        return self._patterns.copy()

    def get_gitignore_patterns(self) -> List[str]:
        """Get patterns from .gitignore."""
        return self._gitignore_patterns.copy()

    def get_mcp_ignore_patterns(self) -> List[str]:
        """Get patterns from .mcp-index-ignore."""
        return self._mcp_ignore_patterns.copy()

    def reload(self):
        """Reload patterns from files."""
        self._load_patterns()


# Singleton instance for easy access
_ignore_manager: Optional[IgnorePatternManager] = None


def get_ignore_manager(root_path: Path = None) -> IgnorePatternManager:
    """
    Get or create the ignore pattern manager.

    Args:
        root_path: Root directory for ignore files. Only used on first call.

    Returns:
        IgnorePatternManager instance
    """
    global _ignore_manager
    if _ignore_manager is None:
        _ignore_manager = IgnorePatternManager(root_path)
    return _ignore_manager


def should_ignore_file(file_path: Path, root_path: Path = None) -> bool:
    """
    Convenience function to check if a file should be ignored.

    Args:
        file_path: Path to check
        root_path: Root directory for ignore files (optional)

    Returns:
        True if file should be ignored
    """
    manager = get_ignore_manager(root_path)
    return manager.should_ignore(file_path)
