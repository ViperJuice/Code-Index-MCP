"""
BM25 Adapter Plugin - Makes BM25 indexes work with the plugin system.

This adapter allows the existing plugin system to work with BM25 indexes
by implementing the IPlugin interface and querying the BM25 FTS5 tables.
"""

import logging
import sqlite3
from pathlib import Path
from typing import Iterable, Optional

from ..plugin_base import (
    IndexShard,
    IPlugin,
    Reference,
    SearchOpts,
    SearchResult,
    SymbolDef,
)

logger = logging.getLogger(__name__)


class BM25AdapterPlugin(IPlugin):
    """Adapter that makes BM25 indexes work with the plugin system."""

    # This adapter works for all languages
    lang = "all"

    def __init__(self, sqlite_store=None):
        """Initialize with SQLiteStore that points to BM25 index."""
        self._sqlite_store = sqlite_store
        self._db_path = sqlite_store.db_path if sqlite_store else None

    def supports(self, path: str | Path) -> bool:
        """Support all file types since BM25 is language agnostic."""
        return True

    def getSymbols(self, path: Path, content: str) -> IndexShard:
        """Not implemented - BM25 index is already built."""
        return {"file": str(path), "symbols": [], "language": "unknown"}

    def getDefinition(self, symbol: str) -> Optional[SymbolDef]:
        """Look up symbol definition in BM25 index."""
        if not self._db_path:
            return None

        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()

            # Try different patterns for symbol definitions
            patterns = [
                f"class {symbol}",
                f"def {symbol}",
                f"function {symbol}",
                f"interface {symbol}",
                f"type {symbol}",
                f"const {symbol}",
                f"var {symbol}",
                f"let {symbol}",
            ]

            for pattern in patterns:
                cursor.execute(
                    """
                    SELECT 
                        filepath,
                        snippet(bm25_content, -1, '', '', '...', 20) as snippet,
                        language
                    FROM bm25_content
                    WHERE bm25_content MATCH ?
                    ORDER BY rank
                    LIMIT 1
                """,
                    (pattern,),
                )

                row = cursor.fetchone()
                if row:
                    filepath, snippet, language = row

                    # Try to determine kind from snippet
                    snippet_lower = snippet.lower()
                    kind = "symbol"
                    if "class" in snippet_lower:
                        kind = "class"
                    elif "def" in snippet_lower or "function" in snippet_lower:
                        kind = "function"
                    elif "interface" in snippet_lower:
                        kind = "interface"
                    elif any(kw in snippet_lower for kw in ["const", "var", "let"]):
                        kind = "variable"

                    conn.close()

                    return {
                        "symbol": symbol,
                        "kind": kind,
                        "language": language or "unknown",
                        "defined_in": filepath,
                        "line": 1,  # BM25 doesn't store line numbers
                        "signature": snippet,
                        "doc": "",
                    }

            conn.close()

        except Exception as e:
            logger.error(f"Error in BM25 symbol lookup: {e}")

        return None

    def getReferences(self, symbol: str) -> list[Reference]:
        """Find references to a symbol - not implemented for BM25."""
        return []

    def search(self, query: str, opts: SearchOpts) -> Iterable[SearchResult]:
        """Search using BM25 FTS5."""
        if not self._db_path:
            return

        limit = opts.get("limit", 20) if opts else 20

        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT 
                    filepath,
                    filename,
                    snippet(bm25_content, -1, '<<', '>>', '...', 20) as snippet,
                    language,
                    rank
                FROM bm25_content
                WHERE bm25_content MATCH ?
                ORDER BY rank
                LIMIT ?
            """,
                (query, limit),
            )

            for row in cursor.fetchall():
                filepath, filename, snippet, language, rank = row

                yield {
                    "file": filepath,
                    "line": 1,  # Default since BM25 doesn't store line numbers
                    "snippet": snippet,
                    "score": abs(rank),  # FTS5 rank is negative
                    "language": language or "unknown",
                }

            conn.close()

        except Exception as e:
            logger.error(f"Error in BM25 search: {e}")
