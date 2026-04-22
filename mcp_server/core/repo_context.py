"""Per-tool-call repository context (frozen outer, mutable inner reference)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from mcp_server.storage.multi_repo_manager import RepositoryInfo

# Real imports so get_type_hints() resolves forward references at runtime.
# Neither class imports repo_context, so there is no circular dependency.
from mcp_server.storage.sqlite_store import SQLiteStore


@dataclass(frozen=True)
class RepoContext:
    """Per-tool-call repository context. Immutable outer; registry_entry
    is a LIVE mutable reference into RepositoryRegistry, not a snapshot.

    Fields:
      repo_id:         canonical 16-hex sha256 from compute_repo_id
      sqlite_store:    hydrated from StoreRegistry; non-Optional by contract
      workspace_root:  the path the caller resolved this from (pre-walk-up)
      tracked_branch:  pinned default branch from RepositoryInfo.tracked_branch
      registry_entry:  live RepositoryInfo reference for read-through access
                       to mutable fields (priority, current_commit, etc.)
    """

    repo_id: str
    sqlite_store: SQLiteStore
    workspace_root: Path
    tracked_branch: str
    registry_entry: RepositoryInfo
