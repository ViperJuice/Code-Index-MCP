"""Shared repository readiness contracts for query and status surfaces."""

from __future__ import annotations

import sqlite3
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from mcp_server.storage.repo_identity import compute_repo_id


class RepositoryReadinessState(str, Enum):
    READY = "ready"
    UNREGISTERED_REPOSITORY = "unregistered_repository"
    MISSING_INDEX = "missing_index"
    INDEX_EMPTY = "index_empty"
    STALE_COMMIT = "stale_commit"
    WRONG_BRANCH = "wrong_branch"
    INDEX_BUILDING = "index_building"
    UNSUPPORTED_WORKTREE = "unsupported_worktree"


@dataclass(frozen=True)
class RepositoryReadiness:
    state: RepositoryReadinessState
    repository_id: Optional[str] = None
    repository_name: Optional[str] = None
    registered_path: Optional[str] = None
    requested_path: Optional[str] = None
    tracked_branch: Optional[str] = None
    current_branch: Optional[str] = None
    current_commit: Optional[str] = None
    last_indexed_commit: Optional[str] = None
    index_path: Optional[str] = None
    remediation: Optional[str] = None

    @property
    def ready(self) -> bool:
        return self.state == RepositoryReadinessState.READY

    @property
    def code(self) -> Optional[str]:
        return None if self.ready else self.state.value

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "ready": self.ready,
            "code": self.code,
            "repository_id": self.repository_id,
            "repository_name": self.repository_name,
            "registered_path": self.registered_path,
            "requested_path": self.requested_path,
            "tracked_branch": self.tracked_branch,
            "current_branch": self.current_branch,
            "current_commit": self.current_commit,
            "last_indexed_commit": self.last_indexed_commit,
            "index_path": self.index_path,
            "remediation": self.remediation,
        }


class ReadinessClassifier:
    """Classify registered and arbitrary repository paths without mutating state."""

    @classmethod
    def classify_registered(
        cls,
        repo_info: Any,
        requested_path: Optional[Path] = None,
        indexing_active: bool = False,
    ) -> RepositoryReadiness:
        registered_path = Path(repo_info.path).resolve(strict=False)
        index_path = (
            Path(repo_info.index_path).resolve(strict=False) if repo_info.index_path else None
        )
        current_branch = getattr(repo_info, "current_branch", None) or _git_branch(registered_path)
        current_commit = getattr(repo_info, "current_commit", None) or _git_commit(registered_path)
        tracked_branch = getattr(repo_info, "tracked_branch", None)
        last_indexed_commit = getattr(repo_info, "last_indexed_commit", None)

        state = RepositoryReadinessState.READY
        remediation = None
        if indexing_active:
            state = RepositoryReadinessState.INDEX_BUILDING
            remediation = "Wait for indexing to finish, then retry the request."
        elif index_path is None or not index_path.exists():
            state = RepositoryReadinessState.MISSING_INDEX
            remediation = "Run reindex or pull the latest artifact for this repository."
        elif cls._index_is_empty(index_path):
            state = RepositoryReadinessState.INDEX_EMPTY
            remediation = "Run reindex to populate the repository index."
        elif tracked_branch and current_branch and tracked_branch != current_branch:
            state = RepositoryReadinessState.WRONG_BRANCH
            remediation = f"Switch to the tracked branch '{tracked_branch}' or register the intended repository path."
        elif current_commit and last_indexed_commit and current_commit != last_indexed_commit:
            state = RepositoryReadinessState.STALE_COMMIT
            remediation = "Run reindex to update the repository index to the current commit."

        return RepositoryReadiness(
            state=state,
            repository_id=getattr(repo_info, "repository_id", None),
            repository_name=getattr(repo_info, "name", None),
            registered_path=str(registered_path),
            requested_path=(
                str(Path(requested_path).resolve(strict=False)) if requested_path else None
            ),
            tracked_branch=tracked_branch,
            current_branch=current_branch,
            current_commit=current_commit,
            last_indexed_commit=last_indexed_commit,
            index_path=str(index_path) if index_path else None,
            remediation=remediation,
        )

    @classmethod
    def classify_path(
        cls,
        registry: Any,
        path: Path,
        indexing_active: bool = False,
    ) -> RepositoryReadiness:
        requested_path = Path(path).expanduser().resolve(strict=False)
        git_root = _find_git_root(requested_path)
        if git_root is None:
            return cls._unregistered(requested_path)

        repo_id = registry.find_by_path(git_root)
        if repo_id:
            repo_info = registry.get(repo_id)
            if repo_info is not None:
                return cls.classify_registered(
                    repo_info,
                    requested_path=requested_path,
                    indexing_active=indexing_active,
                )

        if hasattr(registry, "find_unsupported_worktree"):
            repo_info = registry.find_unsupported_worktree(git_root)
            if repo_info is not None:
                return cls._unsupported_worktree(repo_info, requested_path)

        try:
            repo_id = compute_repo_id(git_root).repo_id
        except Exception:
            return cls._unregistered(requested_path)
        repo_info = registry.get(repo_id)
        if repo_info is None:
            return cls._unregistered(requested_path)
        return cls.classify_registered(
            repo_info,
            requested_path=requested_path,
            indexing_active=indexing_active,
        )

    @classmethod
    def _unsupported_worktree(cls, repo_info: Any, requested_path: Path) -> RepositoryReadiness:
        return RepositoryReadiness(
            state=RepositoryReadinessState.UNSUPPORTED_WORKTREE,
            repository_id=getattr(repo_info, "repository_id", None),
            repository_name=getattr(repo_info, "name", None),
            registered_path=str(Path(repo_info.path).resolve(strict=False)),
            requested_path=str(requested_path),
            tracked_branch=getattr(repo_info, "tracked_branch", None),
            current_branch=getattr(repo_info, "current_branch", None),
            current_commit=getattr(repo_info, "current_commit", None),
            last_indexed_commit=getattr(repo_info, "last_indexed_commit", None),
            index_path=str(Path(repo_info.index_path).resolve(strict=False)),
            remediation=_worktree_remediation(),
        )

    @staticmethod
    def _unregistered(requested_path: Path) -> RepositoryReadiness:
        return RepositoryReadiness(
            state=RepositoryReadinessState.UNREGISTERED_REPOSITORY,
            requested_path=str(requested_path),
            remediation="Register this repository path before querying it.",
        )

    @staticmethod
    def _index_is_empty(index_path: Path) -> bool:
        if index_path.stat().st_size == 0:
            return True
        try:
            conn = sqlite3.connect(str(index_path))
            try:
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='files'"
                )
                if cursor.fetchone() is None:
                    return True
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM files WHERE is_deleted = 0 OR is_deleted IS NULL"
                )
                return int(cursor.fetchone()[0]) == 0
            finally:
                conn.close()
        except sqlite3.OperationalError:
            try:
                conn = sqlite3.connect(str(index_path))
                try:
                    cursor = conn.execute("SELECT COUNT(*) FROM files")
                    return int(cursor.fetchone()[0]) == 0
                finally:
                    conn.close()
            except Exception:
                return False
        except Exception:
            return False


def _worktree_remediation() -> str:
    return "Use the registered path or unregister it before registering another worktree."


def _find_git_root(start: Path) -> Optional[Path]:
    current = start.expanduser().resolve(strict=False)
    if current.is_file():
        current = current.parent
    top_level = _run_git(["rev-parse", "--show-toplevel"], current)
    if top_level:
        return Path(top_level).resolve(strict=False)
    is_bare = _run_git(["rev-parse", "--is-bare-repository"], current)
    if is_bare == "true":
        return current
    while True:
        if (current / ".git").exists():
            return current
        if current.parent == current:
            return None
        current = current.parent


def _git_branch(path: Path) -> Optional[str]:
    return _run_git(["rev-parse", "--abbrev-ref", "HEAD"], path)


def _git_commit(path: Path) -> Optional[str]:
    return _run_git(["rev-parse", "HEAD"], path)


def _run_git(args: list[str], cwd: Path) -> Optional[str]:
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
        value = result.stdout.strip()
        return value if value and value != "HEAD" else None
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
