"""Per-repo reentrant lock registry (IF-0-P12-2)."""

import threading
from contextlib import AbstractContextManager
from typing import Dict


class IndexingLockRegistry:
    """Thread-safe registry of per-repo RLocks.

    acquire(repo_id) returns the repo's RLock as a context manager.
    RLocks are reentrant: the same thread may acquire the same repo's lock
    multiple times without deadlocking.
    """

    def __init__(self) -> None:
        self._locks: Dict[str, threading.RLock] = {}
        self._registry_lock = threading.Lock()

    def acquire(self, repo_id: str) -> AbstractContextManager[None]:
        with self._registry_lock:
            if repo_id not in self._locks:
                self._locks[repo_id] = threading.RLock()
        return self._locks[repo_id]


# Module-level singleton (IF-0-P12-2)
lock_registry: IndexingLockRegistry = IndexingLockRegistry()
