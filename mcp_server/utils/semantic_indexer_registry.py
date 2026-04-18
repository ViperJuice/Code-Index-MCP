"""Per-repo SemanticIndexer cache — replaces SL-0 stub."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Dict, Optional

if TYPE_CHECKING:
    from ..storage.repository_registry import RepositoryRegistry
    from .semantic_indexer import SemanticIndexer


class SemanticIndexerRegistry:
    """Thread-safe registry that constructs and caches per-repo SemanticIndexer instances."""

    def __init__(self, repository_registry: "RepositoryRegistry") -> None:
        self._repo_registry = repository_registry
        self._cache: Dict[str, "SemanticIndexer"] = {}
        self._lock = threading.Lock()

    def get(self, repo_id: str) -> "SemanticIndexer":
        """Return the SemanticIndexer for *repo_id*, constructing it on first access.

        Raises KeyError if repo_id is not registered.
        """
        with self._lock:
            if repo_id in self._cache:
                return self._cache[repo_id]

        repo_info = self._repo_registry.get(repo_id)
        if repo_info is None:
            raise KeyError(repo_id)

        from .semantic_indexer import SemanticIndexer

        indexer = SemanticIndexer(
            qdrant_path=":memory:",
            repo_identifier=repo_id,
            branch=repo_info.tracked_branch or repo_info.current_branch,
            commit=repo_info.current_commit,
        )

        with self._lock:
            # Double-checked locking: another thread may have inserted while we built.
            if repo_id not in self._cache:
                self._cache[repo_id] = indexer
            else:
                indexer = self._cache[repo_id]

        return indexer

    def shutdown(self) -> None:
        """Close all cached indexers."""
        with self._lock:
            indexers = list(self._cache.values())
            self._cache.clear()

        for indexer in indexers:
            try:
                indexer.qdrant.close()
            except Exception:
                pass
