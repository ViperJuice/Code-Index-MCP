"""Change detection for incremental index updates.

This module provides utilities for detecting file changes between git commits
and determining what needs to be reindexed.
"""

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Set

from ..plugins.language_registry import get_all_extensions

logger = logging.getLogger(__name__)


@dataclass
class FileChange:
    """Represents a single file change."""

    path: str
    change_type: str  # "added", "modified", "deleted", "renamed"
    old_path: Optional[str] = None  # For renames


class ChangeDetector:
    """Detects file changes between commits for incremental indexing."""

    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self.supported_extensions = get_all_extensions()

    def get_changes_since_commit(
        self, from_commit: str, to_commit: str = "HEAD"
    ) -> List[FileChange]:
        """Get all file changes between two commits.

        Args:
            from_commit: Starting commit SHA
            to_commit: Ending commit SHA (default: HEAD)

        Returns:
            List of FileChange objects
        """
        changes = []

        try:
            # Get diff between commits
            cmd = ["git", "diff", "--name-status", "--no-renames", from_commit, to_commit]
            result = subprocess.run(
                cmd, cwd=self.repo_path, capture_output=True, text=True, check=True
            )

            for line in result.stdout.strip().splitlines():
                if not line:
                    continue

                parts = line.split("\t")
                if len(parts) < 2:
                    continue

                status = parts[0]
                path = parts[1]

                # Filter by supported extensions
                if not self._is_supported_file(path):
                    continue

                if status == "A":
                    changes.append(FileChange(path, "added"))
                elif status == "M":
                    changes.append(FileChange(path, "modified"))
                elif status == "D":
                    changes.append(FileChange(path, "deleted"))

            # Also check for renames
            cmd_renames = ["git", "diff", "--name-status", "--find-renames", from_commit, to_commit]
            result = subprocess.run(
                cmd_renames, cwd=self.repo_path, capture_output=True, text=True, check=True
            )

            for line in result.stdout.strip().splitlines():
                if not line:
                    continue

                parts = line.split("\t")
                if len(parts) >= 2 and parts[0].startswith("R"):
                    if len(parts) >= 3:
                        old_path = parts[1]
                        new_path = parts[2]

                        # Only track if either path is supported
                        if self._is_supported_file(old_path) or self._is_supported_file(new_path):
                            changes.append(FileChange(new_path, "renamed", old_path))

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get git diff: {e}")

        return changes

    def get_uncommitted_changes(self) -> List[FileChange]:
        """Get uncommitted changes in the working directory.

        Returns:
            List of FileChange objects
        """
        changes = []

        try:
            # Get staged changes
            cmd = ["git", "diff", "--cached", "--name-status"]
            result = subprocess.run(
                cmd, cwd=self.repo_path, capture_output=True, text=True, check=True
            )

            for line in result.stdout.strip().splitlines():
                change = self._parse_status_line(line)
                if change:
                    changes.append(change)

            # Get unstaged changes
            cmd = ["git", "diff", "--name-status"]
            result = subprocess.run(
                cmd, cwd=self.repo_path, capture_output=True, text=True, check=True
            )

            for line in result.stdout.strip().splitlines():
                change = self._parse_status_line(line)
                if change:
                    changes.append(change)

            # Get untracked files
            cmd = ["git", "ls-files", "--others", "--exclude-standard"]
            result = subprocess.run(
                cmd, cwd=self.repo_path, capture_output=True, text=True, check=True
            )

            for path in result.stdout.strip().splitlines():
                if path and self._is_supported_file(path):
                    changes.append(FileChange(path, "added"))

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get uncommitted changes: {e}")

        return changes

    def _parse_status_line(self, line: str) -> Optional[FileChange]:
        """Parse a git status line into a FileChange.

        Args:
            line: Git status line

        Returns:
            FileChange or None
        """
        if not line:
            return None

        parts = line.split("\t")
        if len(parts) < 2:
            return None

        status = parts[0]
        path = parts[1]

        if not self._is_supported_file(path):
            return None

        if status == "A":
            return FileChange(path, "added")
        elif status == "M":
            return FileChange(path, "modified")
        elif status == "D":
            return FileChange(path, "deleted")
        elif status.startswith("R") and len(parts) >= 3:
            return FileChange(parts[2], "renamed", parts[1])

        return None

    def _is_supported_file(self, path: str) -> bool:
        """Check if a file path has a supported extension.

        Args:
            path: File path

        Returns:
            True if supported
        """
        file_path = Path(path)
        return file_path.suffix in self.supported_extensions

    def get_affected_directories(self, changes: List[FileChange]) -> Set[str]:
        """Get set of directories affected by changes.

        Args:
            changes: List of file changes

        Returns:
            Set of directory paths
        """
        directories = set()

        for change in changes:
            dir_path = str(Path(change.path).parent)
            if dir_path != ".":
                directories.add(dir_path)

            # For renames, include old directory too
            if change.old_path:
                old_dir = str(Path(change.old_path).parent)
                if old_dir != ".":
                    directories.add(old_dir)

        return directories

    def estimate_reindex_cost(self, changes: List[FileChange]) -> dict:
        """Estimate the cost of reindexing based on changes.

        Args:
            changes: List of file changes

        Returns:
            Dictionary with cost estimates
        """
        cost = {
            "files_to_index": 0,
            "files_to_remove": 0,
            "files_to_move": 0,
            "estimated_time_seconds": 0.0,
        }

        for change in changes:
            if change.change_type in ["added", "modified"]:
                cost["files_to_index"] += 1
            elif change.change_type == "deleted":
                cost["files_to_remove"] += 1
            elif change.change_type == "renamed":
                cost["files_to_move"] += 1

        # Rough time estimates
        cost["estimated_time_seconds"] = (
            cost["files_to_index"] * 0.1  # 100ms per file to index
            + cost["files_to_remove"] * 0.01  # 10ms per file to remove
            + cost["files_to_move"] * 0.02  # 20ms per file to move
        )

        return cost

    def should_use_incremental(self, changes: List[FileChange], threshold: int = 1000) -> bool:
        """Determine if incremental update is worthwhile.

        Args:
            changes: List of file changes
            threshold: Maximum changes for incremental (default: 1000)

        Returns:
            True if incremental update should be used
        """
        total_changes = len(changes)

        # If too many changes, full reindex might be faster
        if total_changes > threshold:
            logger.info(f"Too many changes ({total_changes}), recommending full reindex")
            return False

        # Check if core directories changed (might affect many files)
        affected_dirs = self.get_affected_directories(changes)
        if any(d in ["src", "lib", "core"] for d in affected_dirs):
            # Major structural changes, might be better to do full reindex
            cost = self.estimate_reindex_cost(changes)
            if cost["files_to_index"] > threshold / 2:
                logger.info("Major structural changes detected, recommending full reindex")
                return False

        return True
