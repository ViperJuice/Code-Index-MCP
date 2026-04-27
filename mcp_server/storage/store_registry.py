"""
Thread-safe registry of SQLiteStore instances keyed by repo_id.
"""

import logging
import sqlite3
import threading
from pathlib import Path
from typing import Dict

from mcp_server.core.path_resolver import PathResolver
from mcp_server.storage.connection_pool import ConnectionPool
from mcp_server.storage.repository_registry import RepositoryRegistry
from mcp_server.storage.sqlite_store import SQLiteStore

logger = logging.getLogger(__name__)


class StoreRegistry:
    """Thread-safe registry of SQLiteStore instances keyed by repo_id.

    Idempotent: get(repo_id) returns the same instance for repeated calls.
    Cache dict is protected by threading.Lock (SQLite WAL handles per-
    connection thread-safety separately). Construction of a new SQLiteStore
    happens OUTSIDE the global lock to avoid serializing all cache misses.

    Per-key construction lock: a second dict of per-repo_id locks serializes
    concurrent construction for the SAME key (preventing SQLite migration
    races), while different keys can still construct in parallel.

    Double-check pattern: after acquiring the per-key lock, re-check the
    cache — the first thread inserts and the rest return the cached instance.

    Use for_registry() to construct. __init__ is treated as private.
    """

    def __init__(self, registry: RepositoryRegistry):
        self._registry = registry
        self._cache: Dict[str, SQLiteStore] = {}
        self._lock = threading.Lock()
        self._build_locks: Dict[str, threading.Lock] = {}

    @classmethod
    def for_registry(cls, registry: RepositoryRegistry) -> "StoreRegistry":
        return cls(registry)

    def _get_build_lock(self, repo_id: str) -> threading.Lock:
        """Return (creating if needed) a per-repo_id construction lock."""
        with self._lock:
            if repo_id not in self._build_locks:
                self._build_locks[repo_id] = threading.Lock()
            return self._build_locks[repo_id]

    def get(self, repo_id: str) -> SQLiteStore:
        """Return cached SQLiteStore (same instance on repeated calls).
        Raises KeyError if repo_id is not registered."""
        with self._lock:
            cached = self._cache.get(repo_id)
            if cached is not None:
                return cached
            info = self._registry.get(repo_id)
            if info is None:
                raise KeyError(f"repo_id {repo_id!r} is not registered")
            index_path = str(info.index_path)

        # Serialize construction for the same repo_id to prevent concurrent
        # SQLite migration races; different repo_ids still build in parallel.
        build_lock = self._get_build_lock(repo_id)
        with build_lock:
            # Double-check: another thread may have won while we waited.
            with self._lock:
                existing = self._cache.get(repo_id)
                if existing is not None:
                    return existing
            index_path_obj = Path(info.index_path)
            index_path_obj.parent.mkdir(parents=True, exist_ok=True)
            pool = ConnectionPool(
                factory=lambda p=index_path: sqlite3.connect(p, check_same_thread=False),
                size=4,
            )
            store = SQLiteStore(index_path, path_resolver=PathResolver(info.path), pool=pool)
            with self._lock:
                self._cache[repo_id] = store
            return store

    def close(self, repo_id: str) -> None:
        """Close and evict the cached store for repo_id. No-op if absent."""
        with self._lock:
            store = self._cache.pop(repo_id, None)
            self._build_locks.pop(repo_id, None)
        if store is not None:
            try:
                store.close()
            except Exception as exc:
                logger.warning("SQLiteStore.close failed for %s: %s", repo_id, exc)

    def shutdown(self) -> None:
        """Close all cached stores and clear the cache."""
        with self._lock:
            items = list(self._cache.items())
            self._cache.clear()
        for repo_id, store in items:
            try:
                store.close()
            except Exception as exc:
                logger.warning("SQLiteStore.close failed for %s: %s", repo_id, exc)
