"""Simple dispatcher that bypasses plugin system for direct BM25 search."""

import logging
from typing import Any, Dict, Iterable, Optional

from ..plugin_base import SearchResult
from ..storage.sqlite_store import SQLiteStore

logger = logging.getLogger(__name__)


class SimpleDispatcher:
    """Simplified dispatcher that uses direct BM25 search only."""

    def __init__(self, sqlite_store: Optional[SQLiteStore] = None):
        """Initialize with SQLite store."""
        self.sqlite_store = sqlite_store
        self._search_count = 0
        self._total_results = 0

    def search(self, query: str, limit: int = 10, **kwargs) -> Iterable[SearchResult]:
        """Search using direct BM25 only."""
        if not self.sqlite_store:
            logger.warning("No SQLite store available for search")
            return

        self._search_count += 1

        # Try different table names based on index schema
        tables_to_try = ["bm25_content", "fts_code"]

        for table in tables_to_try:
            try:
                # Direct BM25 search with specific table
                results = self.sqlite_store.search_bm25(query, table=table, limit=limit)

                # If we got results, convert to SearchResult format
                if results:
                    for result in results:
                        self._total_results += 1
                        # Handle different result formats
                        if "filepath" in result:
                            file_path = result["filepath"]
                        else:
                            file_path = result.get("file_path", "")

                        yield SearchResult(
                            file_path=file_path,
                            line=result.get("line", 0),
                            column=result.get("column", 0),
                            snippet=result.get("snippet", ""),
                            score=result.get("score", 0.0),
                            metadata=result.get("metadata", {}),
                        )
                    return  # Success, don't try other tables

            except Exception as e:
                logger.debug(f"Search in table '{table}' failed: {e}")
                continue

        # If all tables failed, log error
        logger.error(f"Search failed for query '{query}' in all tables")

    def search_symbol(self, symbol_name: str, limit: int = 10) -> Iterable[Dict[str, Any]]:
        """Search for symbols by name."""
        if not self.sqlite_store:
            return

        try:
            # Use get_symbol if available
            if hasattr(self.sqlite_store, "get_symbol"):
                symbols = self.sqlite_store.get_symbol(symbol_name)
                for symbol in symbols[:limit]:
                    yield symbol
            else:
                # Fallback to BM25 search
                for result in self.search(symbol_name, limit=limit):
                    yield {
                        "name": symbol_name,
                        "file_path": result.file_path,
                        "line": result.line,
                        "snippet": result.snippet,
                    }
        except Exception as e:
            logger.error(f"Symbol search failed for '{symbol_name}': {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get search statistics."""
        return {
            "search_count": self._search_count,
            "total_results": self._total_results,
            "store_connected": self.sqlite_store is not None,
            "search_method": "BM25 (direct)",
        }

    def health_check(self) -> Dict[str, Any]:
        """Check dispatcher health."""
        health = {"status": "healthy", "sqlite_store": False, "search_available": False}

        if self.sqlite_store:
            health["sqlite_store"] = True
            try:
                # Test search
                _ = list(self.search("test", limit=1))
                health["search_available"] = True
            except Exception:
                health["status"] = "degraded"
        else:
            health["status"] = "unhealthy"

        return health


# Convenience function for MCP server
def create_simple_dispatcher(db_path: str) -> SimpleDispatcher:
    """Create a simple dispatcher for the given database."""
    try:
        store = SQLiteStore(db_path)
        return SimpleDispatcher(store)
    except Exception as e:
        logger.error(f"Failed to create dispatcher for {db_path}: {e}")
        return SimpleDispatcher()  # Return empty dispatcher
