"""Per-repo SemanticIndexer cache — replaces SL-0 stub."""

from __future__ import annotations

import hashlib
import re
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Dict

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

        branch = repo_info.tracked_branch or repo_info.current_branch or "unknown"
        qdrant_path = Path(repo_info.index_location or Path(repo_info.index_path).parent)
        qdrant_path = qdrant_path / "semantic_qdrant"

        indexer = SemanticIndexer(
            qdrant_path=str(qdrant_path),
            repo_identifier=repo_id,
            branch=branch,
            commit=repo_info.current_commit,
            collection=self._collection_name(repo_id, branch, repo_info.current_commit),
        )

        with self._lock:
            # Double-checked locking: another thread may have inserted while we built.
            if repo_id not in self._cache:
                self._cache[repo_id] = indexer
            else:
                indexer = self._cache[repo_id]

        return indexer

    @staticmethod
    def _collection_name(repo_id: str, branch: str, commit: str | None) -> str:
        repo_part = hashlib.sha256(repo_id.encode()).hexdigest()[:12]
        branch_part = re.sub(r"[^0-9a-zA-Z]+", "_", branch.lower()).strip("_") or "branch"
        commit_part = re.sub(r"[^0-9a-zA-Z]+", "_", (commit or "unknown").lower()).strip("_")
        return f"ci__{repo_part}__{branch_part}__{commit_part[:12] or 'unknown'}"

    def evict(self, repo_id: str) -> bool:
        """Close and remove one cached indexer. Returns True when one existed."""
        with self._lock:
            indexer = self._cache.pop(repo_id, None)
        if indexer is None:
            return False
        self._close_indexer(indexer)
        return True

    @staticmethod
    def _close_indexer(indexer: "SemanticIndexer") -> None:
        try:
            indexer.qdrant.close()
        except Exception:
            pass

    def shutdown(self) -> None:
        """Close all cached indexers."""
        with self._lock:
            indexers = list(self._cache.values())
            self._cache.clear()

        for indexer in indexers:
            self._close_indexer(indexer)
