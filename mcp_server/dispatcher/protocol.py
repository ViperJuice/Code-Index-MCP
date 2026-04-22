"""Dispatcher Protocol — IF-0-P2B-1 interface freeze.

Structural-typing contract for `EnhancedDispatcher` and `SimpleDispatcher` in
the post-P2B shape. Every per-repo method takes ``ctx: RepoContext`` as its
first positional argument; the dispatcher routes all storage access through
``ctx.sqlite_store``.

Two methods are intentionally process-global (no ``ctx``): :py:meth:`plugins`
and :py:meth:`supported_languages` — plugin sets remain dispatcher-global
during P2B per the spec non-goal ("No per-repo plugin map yet — P3 wraps that
in a repo-scoped registry").

Cross-repo methods take ``List[RepoContext]`` and fan out across repos.

This module is imported at runtime by test code (via ``typing.runtime_checkable``).
Consumers should import ``DispatcherProtocol`` from ``mcp_server.dispatcher``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Protocol, Tuple, Union, runtime_checkable

from mcp_server.core.repo_context import RepoContext
from mcp_server.graph import GraphCutResult
from mcp_server.plugin_base import IPlugin, SearchResult, SymbolDef


@runtime_checkable
class DispatcherProtocol(Protocol):
    """Post-P2B dispatcher interface.

    The concrete implementations are :class:`EnhancedDispatcher` (full) and
    :class:`SimpleDispatcher` (narrower BM25-only variant that conforms to
    the query subset). Both are rewritten in SL-1 to match this Protocol.
    """

    # ------------------------------------------------------------------
    # Process-global accessors (no ctx — deferred to P3 for per-repo scope)
    # ------------------------------------------------------------------

    def plugins(self) -> List[IPlugin]:
        """All plugins loaded into this dispatcher (process-global during P2B)."""
        ...

    def supported_languages(self) -> List[str]:
        """Union of file extensions all loaded plugins handle."""
        ...

    # ------------------------------------------------------------------
    # Per-repo query methods
    # ------------------------------------------------------------------

    def lookup(self, ctx: RepoContext, symbol: str, limit: int = 20) -> Optional[SymbolDef]:
        """Resolve a symbol definition within ``ctx.repo_id``."""
        ...

    def search(
        self,
        ctx: RepoContext,
        query: str,
        semantic: bool = False,
        fuzzy: bool = False,
        limit: int = 20,
    ) -> Iterable[SearchResult]:
        """Code search scoped to ``ctx.repo_id``."""
        ...

    def search_documentation(
        self,
        ctx: RepoContext,
        topic: str,
        doc_types: Optional[List[str]] = None,
        limit: int = 20,
    ) -> Iterable[SearchResult]:
        """Documentation-only search scoped to ``ctx.repo_id``."""
        ...

    def get_plugins_for_file(self, ctx: RepoContext, path: Path) -> List[Tuple[IPlugin, float]]:
        """Plugins capable of handling ``path``, with match scores."""
        ...

    # ------------------------------------------------------------------
    # Per-repo mutation methods
    # ------------------------------------------------------------------

    def index_file(self, ctx: RepoContext, path: Path, do_semantic: bool = True) -> None:
        """Index a single file into ``ctx.repo_id``'s store."""
        ...

    def index_directory(
        self, ctx: RepoContext, directory: Path, recursive: bool = True
    ) -> Dict[str, int]:
        """Batch-index a directory; returns per-language counts."""
        ...

    def remove_file(self, ctx: RepoContext, path: Union[Path, str]) -> None:
        """Remove a file from all per-repo indexes."""
        ...

    def move_file(
        self,
        ctx: RepoContext,
        old_path: Union[Path, str],
        new_path: Union[Path, str],
        content_hash: Optional[str] = None,
    ) -> None:
        """Relocate a file in the per-repo index; ``content_hash`` elides
        reindex when bytes are unchanged."""
        ...

    # ------------------------------------------------------------------
    # Per-repo graph / context methods
    # ------------------------------------------------------------------

    def graph_search(
        self,
        ctx: RepoContext,
        query: str,
        expansion_radius: int = 1,
        max_context_nodes: int = 50,
        semantic: bool = False,
        limit: int = 20,
    ) -> Iterable[SearchResult]:
        """Search + graph-context expansion within ``ctx.repo_id``."""
        ...

    def get_context_for_symbols(
        self,
        ctx: RepoContext,
        symbols: List[str],
        radius: int = 2,
        budget: int = 200,
        weights: Optional[Dict[str, float]] = None,
    ) -> Optional[GraphCutResult]:
        """Budgeted graph-cut over the symbols' neighborhood."""
        ...

    def find_symbol_dependencies(
        self, ctx: RepoContext, symbol: str, max_depth: int = 3
    ) -> List[Dict[str, Any]]:
        """Outgoing dependency walk from ``symbol``."""
        ...

    def find_symbol_dependents(
        self, ctx: RepoContext, symbol: str, max_depth: int = 3
    ) -> List[Dict[str, Any]]:
        """Incoming dependent walk into ``symbol``."""
        ...

    def get_code_hotspots(self, ctx: RepoContext, top_n: int = 10) -> List[Dict[str, Any]]:
        """Highest-centrality symbols in the per-repo call graph."""
        ...

    # ------------------------------------------------------------------
    # Per-repo meta
    # ------------------------------------------------------------------

    def get_statistics(self, ctx: RepoContext) -> Dict[str, Any]:
        """Per-repo statistics (index size, plugin load, cache hits)."""
        ...

    def health_check(self, ctx: RepoContext) -> Dict[str, Any]:
        """Per-repo health probe."""
        ...

    # ------------------------------------------------------------------
    # Cross-repo (fan-out) methods — take a list of contexts
    # ------------------------------------------------------------------

    async def cross_repo_symbol_search(
        self,
        contexts: List[RepoContext],
        symbol: str,
        languages: Optional[List[str]] = None,
        max_repositories: int = 10,
    ) -> Dict[str, Any]:
        """Fan symbol-lookup across the provided repo contexts."""
        ...

    async def cross_repo_code_search(
        self,
        contexts: List[RepoContext],
        query: str,
        languages: Optional[List[str]] = None,
        semantic: bool = False,
        max_repositories: int = 10,
    ) -> Dict[str, Any]:
        """Fan code-search across the provided repo contexts."""
        ...

    async def get_cross_repo_statistics(self, contexts: List[RepoContext]) -> Dict[str, Any]:
        """Aggregate statistics across the provided repo contexts."""
        ...
