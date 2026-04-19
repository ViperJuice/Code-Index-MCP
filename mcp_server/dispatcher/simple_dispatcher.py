"""Simple dispatcher that bypasses plugin system for direct BM25 search."""

import logging
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

from ..core.errors import record_handled_error
from ..core.repo_context import RepoContext
from ..graph import GraphCutResult
from ..plugin_base import IPlugin, SearchResult, SymbolDef

logger = logging.getLogger(__name__)


class SimpleDispatcher:
    """Simplified dispatcher using direct BM25 search.

    Conforms to the query subset of DispatcherProtocol: search, health_check,
    get_statistics, plugins, supported_languages. Graph, mutation, and cross-repo
    methods raise NotImplementedError.
    """

    def __init__(self) -> None:
        self._search_count = 0
        self._total_results = 0

    # ------------------------------------------------------------------
    # Process-global accessors (no ctx)
    # ------------------------------------------------------------------

    def plugins(self) -> List[IPlugin]:
        return []

    def supported_languages(self) -> List[str]:
        return []

    # ------------------------------------------------------------------
    # Per-repo query methods
    # ------------------------------------------------------------------

    def lookup(self, ctx: RepoContext, symbol: str, limit: int = 20) -> Optional[SymbolDef]:
        if not ctx.sqlite_store:
            return None
        try:
            rows = ctx.sqlite_store.get_symbol(symbol)
            if rows:
                row = rows[0]
                return {
                    "symbol": row.get("name", symbol),
                    "kind": row.get("kind", "symbol"),
                    "language": "unknown",
                    "signature": row.get("signature", ""),
                    "doc": row.get("documentation"),
                    "defined_in": row.get("file_path", ""),
                    "line": row.get("line_start", 1),
                    "span": (0, len(symbol)),
                }
        except Exception as e:
            logger.error(f"Symbol lookup failed for '{symbol}': {e}")
        return None

    def search(self, ctx: RepoContext, query: str, semantic: bool = False, fuzzy: bool = False, limit: int = 10) -> Iterable[SearchResult]:
        """Search using direct BM25 via ctx.sqlite_store."""
        if not ctx.sqlite_store:
            logger.warning("No SQLite store available for search")
            return

        self._search_count += 1
        tables_to_try = ["bm25_content", "fts_code"]

        for table in tables_to_try:
            try:
                results = ctx.sqlite_store.search_bm25(query, table=table, limit=limit)
                if results:
                    for result in results:
                        self._total_results += 1
                        file_path = result.get("filepath") or result.get("file_path", "")
                        yield SearchResult(
                            file_path=file_path,
                            start_line=result.get("line", 0),
                            end_line=result.get("line", 0),
                            column=result.get("column", 0),
                            snippet=result.get("snippet", ""),
                            score=result.get("score", 0.0),
                            metadata=result.get("metadata", {}),
                        )
                    return
            except Exception as e:
                logger.debug(f"Search in table '{table}' failed: {e}")
                continue

        logger.error(f"Search failed for query '{query}' in all tables")

    def search_documentation(
        self,
        ctx: RepoContext,
        topic: str,
        doc_types: Optional[List[str]] = None,
        limit: int = 20,
    ) -> Iterable[SearchResult]:
        yield from self.search(ctx, topic, limit=limit)

    def get_plugins_for_file(self, ctx: RepoContext, path: Path) -> List[Tuple[IPlugin, float]]:
        return []

    # ------------------------------------------------------------------
    # Per-repo mutation methods — not supported in SimpleDispatcher
    # ------------------------------------------------------------------

    def index_file(self, ctx: RepoContext, path: Path, do_semantic: bool = True) -> None:
        raise NotImplementedError("SimpleDispatcher does not support index_file")

    def index_directory(self, ctx: RepoContext, directory: Path, recursive: bool = True) -> Dict[str, int]:
        raise NotImplementedError("SimpleDispatcher does not support index_directory")

    def remove_file(self, ctx: RepoContext, path: Union[Path, str]) -> None:
        raise NotImplementedError("SimpleDispatcher does not support remove_file")

    def move_file(
        self,
        ctx: RepoContext,
        old_path: Union[Path, str],
        new_path: Union[Path, str],
        content_hash: Optional[str] = None,
    ) -> None:
        raise NotImplementedError("SimpleDispatcher does not support move_file")

    # ------------------------------------------------------------------
    # Per-repo graph methods — not supported in SimpleDispatcher
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
        raise NotImplementedError("SimpleDispatcher does not support graph_search")

    def get_context_for_symbols(
        self,
        ctx: RepoContext,
        symbols: List[str],
        radius: int = 2,
        budget: int = 200,
        weights: Optional[Dict[str, float]] = None,
    ) -> Optional[GraphCutResult]:
        raise NotImplementedError("SimpleDispatcher does not support get_context_for_symbols")

    def find_symbol_dependencies(self, ctx: RepoContext, symbol: str, max_depth: int = 3) -> List[Dict[str, Any]]:
        raise NotImplementedError("SimpleDispatcher does not support find_symbol_dependencies")

    def find_symbol_dependents(self, ctx: RepoContext, symbol: str, max_depth: int = 3) -> List[Dict[str, Any]]:
        raise NotImplementedError("SimpleDispatcher does not support find_symbol_dependents")

    def get_code_hotspots(self, ctx: RepoContext, top_n: int = 10) -> List[Dict[str, Any]]:
        raise NotImplementedError("SimpleDispatcher does not support get_code_hotspots")

    # ------------------------------------------------------------------
    # Per-repo meta
    # ------------------------------------------------------------------

    def get_statistics(self, ctx: RepoContext) -> Dict[str, Any]:
        return {
            "search_count": self._search_count,
            "total_results": self._total_results,
            "store_connected": ctx.sqlite_store is not None,
            "search_method": "BM25 (direct)",
        }

    def health_check(self, ctx: RepoContext) -> Dict[str, Any]:
        health: Dict[str, Any] = {"status": "healthy", "sqlite_store": False, "search_available": False}

        if ctx.sqlite_store:
            health["sqlite_store"] = True
            try:
                _ = list(self.search(ctx, "test", limit=1))
                health["search_available"] = True
            except Exception as exc:
                record_handled_error(__name__, exc)
                health["status"] = "degraded"
        else:
            health["status"] = "unhealthy"

        return health

    # ------------------------------------------------------------------
    # Cross-repo — not supported in SimpleDispatcher
    # ------------------------------------------------------------------

    async def cross_repo_symbol_search(
        self,
        contexts: List[RepoContext],
        symbol: str,
        languages: Optional[List[str]] = None,
        max_repositories: int = 10,
    ) -> Dict[str, Any]:
        raise NotImplementedError("SimpleDispatcher does not support cross_repo_symbol_search")

    async def cross_repo_code_search(
        self,
        contexts: List[RepoContext],
        query: str,
        languages: Optional[List[str]] = None,
        semantic: bool = False,
        max_repositories: int = 10,
    ) -> Dict[str, Any]:
        raise NotImplementedError("SimpleDispatcher does not support cross_repo_code_search")

    async def get_cross_repo_statistics(self, contexts: List[RepoContext]) -> Dict[str, Any]:
        raise NotImplementedError("SimpleDispatcher does not support get_cross_repo_statistics")


def create_simple_dispatcher(db_path: str) -> SimpleDispatcher:
    """Create a simple dispatcher (db_path is ignored; ctx passed per-call)."""
    return SimpleDispatcher()
