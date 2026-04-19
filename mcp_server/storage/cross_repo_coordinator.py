"""
Compatibility shim for the deleted ``mcp_server.storage.cross_repo_coordinator``
module.  The canonical implementation lives at
``mcp_server.dispatcher.cross_repo_coordinator``; this module exists solely to
preserve two external affordances:

1. Re-export the ``AggregatedResult``/``SearchScope``/``CrossRepositorySearchCoordinator``
   public names under their legacy import path.
2. Expose ``ThreadPoolExecutor``, ``as_completed``, and ``SQLiteStore`` as module
   attributes so existing tests that ``@patch("mcp_server.storage.cross_repo_coordinator.X")``
   continue to function without requiring rewrites.

No production code should import from this module; it is intentionally
undocumented outside of the compatibility contract above.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed

from mcp_server.dispatcher.cross_repo_coordinator import (
    AggregatedResult,
    CrossRepositorySearchCoordinator,
    SearchScope,
    get_cross_repo_coordinator,
)
from mcp_server.storage.sqlite_store import SQLiteStore

__all__ = [
    "AggregatedResult",
    "CrossRepositorySearchCoordinator",
    "SearchScope",
    "SQLiteStore",
    "ThreadPoolExecutor",
    "as_completed",
    "get_cross_repo_coordinator",
]
