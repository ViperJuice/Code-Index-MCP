"""SemanticIndexerRegistry — IF-0-P3-2 interface freeze.

Per-repo semantic-indexer lookup. Threads ``repo_id`` through
:class:`SemanticIndexer`'s constructor (which already accepts
``repo_identifier`` / ``branch`` / ``commit``) and into
``namespace_resolver.resolve_collection_name``, yielding one Qdrant collection
per repo.

SL-4 replaces the stub below with a real implementation. Consumed by the
dispatcher (SL-6) at search/index time.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from mcp_server.utils.semantic_indexer import SemanticIndexer


@runtime_checkable
class SemanticIndexerRegistryProtocol(Protocol):
    """Per-repo semantic-indexer lookup contract."""

    def get(self, repo_id: str) -> "SemanticIndexer":
        """Return the semantic indexer bound to ``repo_id``."""
        ...

    def shutdown(self) -> None:
        """Close all cached indexers."""
        ...


class SemanticIndexerRegistry:
    """SL-0 stub. SL-4 replaces with the real impl."""

    def get(self, repo_id: str) -> "SemanticIndexer":
        raise NotImplementedError(
            "SemanticIndexerRegistry is an SL-0 stub; SL-4 implements."
        )

    def shutdown(self) -> None:
        raise NotImplementedError(
            "SemanticIndexerRegistry is an SL-0 stub; SL-4 implements."
        )
