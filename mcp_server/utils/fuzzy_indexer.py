import logging
from typing import Any, Dict, List, Optional, Set, Tuple

# Import SQLiteStore only if it's available
try:
    from ..storage.sqlite_store import SQLiteStore
except ImportError:
    SQLiteStore = None

logger = logging.getLogger(__name__)


class FuzzyIndexer:
    """Index for fuzzy searching source files with optional SQLite persistence."""

    def __init__(self, sqlite_store: Optional["SQLiteStore"] = None) -> None:
        """Initialize fuzzy indexer.

        Args:
            sqlite_store: Optional SQLite store for persistence
        """
        self.index: Dict[str, List[Tuple[int, str]]] = {}
        self.sqlite_store = sqlite_store
        self._index_type = "fuzzy_file_index"
        self._symbol_metadata: Dict[str, Dict[str, Any]] = {}  # Track symbol metadata

        # Detect available schema type
        self._schema_type = "fts_code"  # Default expected schema
        if self.sqlite_store:
            self._schema_type = self._detect_schema_type()

        # Try to load existing index from SQLite if available
        if self.sqlite_store:
            self.load()

    def _detect_schema_type(self) -> str:
        """Detect which schema type is available in the database."""
        if not self.sqlite_store:
            return "fts_code"

        try:
            with self.sqlite_store._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('fts_code', 'bm25_content')"
                )
                tables = [row[0] for row in cursor.fetchall()]

                if "fts_code" in tables:
                    logger.debug("Detected fts_code schema")
                    return "fts_code"
                elif "bm25_content" in tables:
                    logger.info("Detected BM25 schema, adapting FuzzyIndexer")
                    return "bm25_content"
                else:
                    logger.warning("No compatible schema found, defaulting to fts_code")
                    return "fts_code"
        except Exception as e:
            logger.error(f"Schema detection failed: {e}")
            return "fts_code"

    # ------------------------------------------------------------------
    def add_file(self, path: str, content: str) -> None:
        """Add a file's contents to the index."""
        lines = [(i + 1, line.rstrip()) for i, line in enumerate(content.splitlines())]
        self.index[path] = lines

        # If using SQLite backend, also store in appropriate table
        if self.sqlite_store:
            try:
                with self.sqlite_store._get_connection() as conn:
                    if self._schema_type == "fts_code":
                        # Clear existing entries for this file
                        conn.execute("DELETE FROM fts_code WHERE file_id = ?", (path,))
                        # Insert new content (store full content for FTS5)
                        conn.execute(
                            "INSERT INTO fts_code (content, file_id) VALUES (?, ?)",
                            (content, path),
                        )
                    elif self._schema_type == "bm25_content":
                        # For BM25 schema, we don't modify the table - it's already populated
                        # Just log that we're adapting to existing BM25 content
                        logger.debug(f"Adapting to existing BM25 content for {path}")
            except Exception as e:
                logger.error(f"Failed to update search index for {path}: {e}")

    # ------------------------------------------------------------------
    def search(self, query: str, limit: int = 20) -> List[Dict]:
        """Return list of matches with basic substring matching or FTS5 if available."""
        # If SQLite backend with FTS5 is available, use it for better performance
        if self.sqlite_store and self._use_fts5_search(query):
            return self._search_fts5(query, limit)

        # Fall back to in-memory search
        return self._search_memory(query, limit)

    def _use_fts5_search(self, query: str) -> bool:
        """Determine if we should use FTS5 search."""
        # For now, use FTS5 for queries with multiple words or special operators
        return " " in query or any(op in query for op in ["AND", "OR", "NOT", '"'])

    def _search_fts5(self, query: str, limit: int) -> List[Dict]:
        """Search using SQLite FTS5 or BM25."""
        results: List[Dict] = []

        try:
            with self.sqlite_store._get_connection() as conn:
                if self._schema_type == "fts_code":
                    # Use FTS5 for search
                    cursor = conn.execute(
                        """
                        SELECT file_id, snippet(fts_code, 0, '**', '**', '...', 64) as snippet,
                               rank
                        FROM fts_code
                        WHERE fts_code MATCH ?
                        ORDER BY rank
                        LIMIT ?
                    """,
                        (query, limit),
                    )
                elif self._schema_type == "bm25_content":
                    # Use BM25 content table for search
                    cursor = conn.execute(
                        """
                        SELECT filepath, snippet(bm25_content, -1, '**', '**', '...', 64) as snippet,
                               rank
                        FROM bm25_content
                        WHERE bm25_content MATCH ?
                        ORDER BY rank
                        LIMIT ?
                    """,
                        (query, limit),
                    )

                for row in cursor:
                    # Extract line number from snippet if possible
                    # This is a simplified approach - in production, we'd store line info
                    results.append(
                        {
                            "file": row[0],
                            "line": 1,  # TODO: Extract actual line number
                            "snippet": row[1],
                        }
                    )

        except Exception as e:
            logger.error(f"FTS search failed, falling back to memory: {e}")
            return self._search_memory(query, limit)

        return results

    def _search_memory(self, query: str, limit: int) -> List[Dict]:
        """Original in-memory search implementation."""
        results: List[Dict] = []
        seen: Set[Tuple[str, int]] = set()
        q = query.lower()

        for file, lines in self.index.items():
            for line_no, text in lines:
                if q in text.lower():
                    key = (file, line_no)
                    if key in seen:
                        continue
                    seen.add(key)
                    results.append({"file": file, "line": line_no, "snippet": text.strip()})
                    if len(results) >= limit:
                        return results
        return results

    # ------------------------------------------------------------------
    def persist(self) -> bool:
        """Save index to SQLite database.

        Returns:
            True if successful, False otherwise
        """
        if not self.sqlite_store:
            logger.warning("No SQLite store configured for persistence")
            return False

        try:
            # Convert index to format suitable for SQLite storage
            # For each file in index, we'll store its content in FTS5
            # This is already done in add_file(), so this method just ensures
            # the data is committed

            # We could optionally store the pickled index as a backup
            # but the primary storage is in the FTS5 tables

            logger.info(f"Persisted fuzzy index with {len(self.index)} files")
            return True

        except Exception as e:
            logger.error(f"Failed to persist fuzzy index: {e}")
            return False

    # ------------------------------------------------------------------
    def load(self) -> bool:
        """Load index from SQLite database.

        Returns:
            True if successful, False otherwise
        """
        if not self.sqlite_store:
            logger.warning("No SQLite store configured for loading")
            return False

        try:
            # Since we're using FTS5 for storage, we don't need to load
            # the full index into memory. The search operations will query
            # the database directly. We could optionally load file metadata
            # for faster access.

            logger.info("SQLite backend ready for fuzzy search")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize SQLite backend: {e}")
            return False

    # ------------------------------------------------------------------
    def clear(self) -> None:
        """Clear the in-memory index."""
        self.index.clear()

        # Also clear search data if using SQLite
        if self.sqlite_store:
            try:
                with self.sqlite_store._get_connection() as conn:
                    if self._schema_type == "fts_code":
                        conn.execute("DELETE FROM fts_code")
                    elif self._schema_type == "bm25_content":
                        # For BM25, we don't clear the table as it's managed elsewhere
                        logger.debug("BM25 content table managed by indexer, not clearing")
            except Exception as e:
                logger.error(f"Failed to clear search index: {e}")

    # ------------------------------------------------------------------
    def add_symbol(
        self,
        symbol_name: str,
        file_path: str,
        line_number: int,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add a symbol to the fuzzy index.

        This is a higher-level method that works with symbols rather than raw file content.

        Args:
            symbol_name: Name of the symbol (function, class, etc.)
            file_path: Path to the file containing the symbol
            line_number: Line number where the symbol is defined
            metadata: Optional metadata about the symbol
        """
        # Store symbol metadata for later use
        key = f"{file_path}:{symbol_name}"
        self._symbol_metadata[key] = {
            "file_path": file_path,
            "line_number": line_number,
            "metadata": metadata or {},
        }

        # Add to trigram index if SQLite backend is available
        if self.sqlite_store and metadata and "symbol_id" in metadata:
            # The SQLiteStore already handles trigram generation when storing symbols
            # This method is mainly for tracking metadata
            pass

    # ------------------------------------------------------------------
    def search_symbols(self, query: str, limit: int = 20) -> List[Dict]:
        """Search for symbols using fuzzy matching.

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of matching symbols with metadata
        """
        if self.sqlite_store:
            # Use SQLite trigram search
            return self.sqlite_store.search_symbols_fuzzy(query, limit)
        else:
            # Fall back to simple in-memory search
            results = []
            query_lower = query.lower()

            for key, data in self._symbol_metadata.items():
                symbol_name = key.split(":", 1)[1]
                if query_lower in symbol_name.lower():
                    results.append(
                        {
                            "name": symbol_name,
                            "file_path": data["file_path"],
                            "line": data["line_number"],
                            **data["metadata"],
                        }
                    )
                    if len(results) >= limit:
                        break

            return results

    # ------------------------------------------------------------------
    def get_stats(self) -> Dict[str, int]:
        """Get index statistics."""
        total_lines = sum(len(lines) for lines in self.index.values())

        stats = {
            "files": len(self.index),
            "total_lines": total_lines,
            "symbols": len(self._symbol_metadata),
            "persisted": self.sqlite_store is not None,
        }

        # Add SQLite statistics if available
        if self.sqlite_store:
            db_stats = self.sqlite_store.get_statistics()
            stats.update(
                {
                    "db_files": db_stats.get("files", 0),
                    "db_symbols": db_stats.get("symbols", 0),
                    "db_references": db_stats.get("symbol_references", 0),
                }
            )

        return stats
