"""Resolves filesystem paths to RepoContext via the RepositoryRegistry."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from mcp_server.core.repo_context import RepoContext
from mcp_server.storage.repo_identity import compute_repo_id
from mcp_server.storage.repository_registry import RepositoryRegistry
from mcp_server.storage.store_registry import StoreRegistry

logger = logging.getLogger(__name__)


def _find_git_root(start: Path) -> Optional[Path]:
    """Walk up from `start` to find the nearest directory containing `.git`
    (file for worktrees, dir for main clones). Returns None if none found."""
    current = start.expanduser().resolve()
    if current.is_file():
        current = current.parent
    while True:
        if (current / ".git").exists():
            return current
        if current.parent == current:
            return None
        current = current.parent


class RepoResolver:
    """Resolves arbitrary filesystem paths to a RepoContext, or None when
    the path is outside any registered repository. Does NOT auto-register."""

    def __init__(self, registry: RepositoryRegistry, store_registry: StoreRegistry):
        self._registry = registry
        self._store_registry = store_registry

    def resolve(self, path: Path) -> Optional[RepoContext]:
        git_root = _find_git_root(path)
        if git_root is None:
            return None

        repo_id = self._registry.find_by_path(git_root)
        if repo_id is None:
            repo_id = compute_repo_id(git_root).repo_id

        info = self._registry.get(repo_id)
        if info is None:
            return None

        tracked_branch = info.tracked_branch or ""

        store = self._store_registry.get(repo_id)
        return RepoContext(
            repo_id=repo_id,
            sqlite_store=store,
            workspace_root=path,
            tracked_branch=tracked_branch,
            registry_entry=info,
        )
