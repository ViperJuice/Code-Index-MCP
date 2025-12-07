"""
BM25 Indexer using SQLite FTS5 for full-text search.

This module provides BM25-based full-text search indexing using SQLite's FTS5
extension, which includes built-in BM25 ranking algorithms.
"""

import hashlib
import logging
import sqlite3

# Interface definition inline for now
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..storage.sqlite_store import SQLiteStore

logger = logging.getLogger(__name__)


# Define IIndexer interface inline
class IIndexer(ABC):
    @abstractmethod
    def index_documents(self, documents: List[Dict[str, Any]]) -> bool:
        pass

    @abstractmethod
    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        pass


class BM25Indexer(IIndexer):
    """
    BM25-based full-text search indexer using SQLite FTS5.

    This indexer provides:
    - Efficient full-text search using inverted indexes
    - Built-in BM25 ranking algorithm
    - Support for phrase searches, prefix searches, and boolean operators
    - Integration with existing SQLite storage
    """

    def __init__(self, storage: SQLiteStore, table_name: str = "bm25_content"):
        """
        Initialize the BM25 indexer.

        Args:
            storage: SQLite storage instance
            table_name: Name for the FTS5 virtual table
        """
        self.storage = storage
        self.table_name = table_name
        self.db_path = storage.db_path
        self._initialize_fts_tables()

    def _initialize_fts_tables(self):
        """Initialize FTS5 tables for BM25 search."""
        with self.storage._get_connection() as conn:
            # Create main BM25 content table
            conn.execute(
                f"""
                CREATE VIRTUAL TABLE IF NOT EXISTS {self.table_name} USING fts5(
                    file_id UNINDEXED,
                    filepath,
                    filename,
                    content,
                    language,
                    symbols,
                    imports,
                    comments,
                    tokenize = 'porter unicode61',
                    prefix = '2 3'
                )
            """
            )

            # Create specialized tables for different content types
            conn.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS bm25_symbols USING fts5(
                    symbol_id UNINDEXED,
                    name,
                    kind,
                    signature,
                    documentation,
                    filepath,
                    tokenize = 'unicode61'
                )
            """
            )

            conn.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS bm25_documents USING fts5(
                    file_id UNINDEXED,
                    filepath,
                    title,
                    content,
                    sections,
                    metadata,
                    tokenize = 'porter unicode61'
                )
            """
            )

            # Create tracking table for indexed files
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS bm25_index_status (
                    file_id INTEGER PRIMARY KEY,
                    filepath TEXT NOT NULL,
                    content_hash TEXT,
                    indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    index_version TEXT DEFAULT '1.0',
                    FOREIGN KEY (file_id) REFERENCES files(id)
                )
            """
            )

            # Create index on filepath for fast lookups
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_bm25_status_filepath 
                ON bm25_index_status(filepath)
            """
            )

            logger.info("BM25 FTS5 tables initialized successfully")

    # IIndexer Implementation

    def index_documents(self, documents: List[Dict[str, Any]]) -> bool:
        """Index multiple documents in batch.

        Args:
            documents: List of documents with 'id', 'content', and optional 'metadata'

        Returns:
            bool: True if successful
        """
        try:
            for doc in documents:
                self.add_document(doc["id"], doc["content"], doc.get("metadata"))
            return True
        except Exception as e:
            logger.error(f"Failed to index documents: {e}")
            return False

    def add_document(self, doc_id: str, content: str, metadata: Optional[Dict] = None) -> None:
        """
        Add a document to the BM25 index.

        Args:
            doc_id: Unique document identifier (file path)
            content: Document content to index
            metadata: Optional metadata including language, symbols, etc.
        """
        with self.storage._get_connection() as conn:
            # Get or create file record
            file_record = self.storage.get_file(doc_id)
            if not file_record:
                logger.warning(f"File record not found for {doc_id}, skipping BM25 indexing")
                return

            file_id = file_record["id"]
            filepath = doc_id
            filename = Path(filepath).name

            # Extract metadata
            language = metadata.get("language", "") if metadata else ""
            symbols = " ".join(metadata.get("symbols", [])) if metadata else ""
            imports = " ".join(metadata.get("imports", [])) if metadata else ""
            comments = " ".join(metadata.get("comments", [])) if metadata else ""

            # Calculate content hash
            content_hash = hashlib.md5(content.encode()).hexdigest()

            # Check if already indexed with same content
            cursor = conn.execute(
                """
                SELECT content_hash FROM bm25_index_status 
                WHERE file_id = ?
            """,
                (file_id,),
            )
            existing = cursor.fetchone()

            if existing and existing[0] == content_hash:
                logger.debug(f"Content unchanged for {filepath}, skipping reindex")
                return

            # Remove old entries
            conn.execute(
                f"""
                DELETE FROM {self.table_name} WHERE file_id = ?
            """,
                (file_id,),
            )

            # Insert new content
            conn.execute(
                f"""
                INSERT INTO {self.table_name} 
                (file_id, filepath, filename, content, language, symbols, imports, comments)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    file_id,
                    filepath,
                    filename,
                    content,
                    language,
                    symbols,
                    imports,
                    comments,
                ),
            )

            # Update index status
            conn.execute(
                """
                INSERT OR REPLACE INTO bm25_index_status 
                (file_id, filepath, content_hash, indexed_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """,
                (file_id, filepath, content_hash),
            )

            # If we have symbols, index them separately
            if metadata and "symbol_list" in metadata:
                self._index_symbols(conn, file_id, filepath, metadata["symbol_list"])

            logger.debug(f"Successfully indexed {filepath} in BM25")

    def _index_symbols(
        self,
        conn: sqlite3.Connection,
        file_id: int,
        filepath: str,
        symbols: List[Dict[str, Any]],
    ) -> None:
        """Index symbols separately for more precise symbol search."""
        # Remove old symbol entries
        conn.execute(
            """
            DELETE FROM bm25_symbols 
            WHERE symbol_id IN (SELECT id FROM symbols WHERE file_id = ?)
        """,
            (file_id,),
        )

        for symbol in symbols:
            symbol_id = symbol.get("id")
            if not symbol_id:
                continue

            conn.execute(
                """
                INSERT INTO bm25_symbols 
                (symbol_id, name, kind, signature, documentation, filepath)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    symbol_id,
                    symbol.get("name", ""),
                    symbol.get("kind", ""),
                    symbol.get("signature", ""),
                    symbol.get("documentation", ""),
                    filepath,
                ),
            )

    def search(self, query: str, limit: int = 20, **kwargs) -> List[Dict[str, Any]]:
        """
        Search using BM25 ranking.

        Args:
            query: Search query with FTS5 syntax support
            limit: Maximum number of results
            **kwargs: Additional search parameters (filters, etc.)

        Returns:
            List of search results with BM25 scores
        """
        search_type = kwargs.get("search_type", "content")
        language = kwargs.get("language")
        file_filter = kwargs.get("file_filter")

        with self.storage._get_connection() as conn:
            if search_type == "symbols":
                return self._search_symbols(conn, query, limit, **kwargs)
            elif search_type == "documents":
                return self._search_documents(conn, query, limit, **kwargs)
            else:
                return self._search_content(conn, query, limit, language, file_filter)

    def _search_content(
        self,
        conn: sqlite3.Connection,
        query: str,
        limit: int,
        language: Optional[str] = None,
        file_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search in file content with BM25 ranking."""
        # Build WHERE clause
        where_clauses = [f"{self.table_name} MATCH ?"]
        params = [query]

        if language:
            where_clauses.append("language = ?")
            params.append(language)

        if file_filter:
            where_clauses.append("filepath LIKE ?")
            params.append(f"%{file_filter}%")

        where_clause = " AND ".join(where_clauses)
        params.append(limit)

        # Execute search with BM25 ranking
        cursor = conn.execute(
            f"""
            SELECT 
                file_id,
                filepath,
                filename,
                language,
                snippet({self.table_name}, 3, '<mark>', '</mark>', '...', 32) as snippet,
                bm25({self.table_name}) as score
            FROM {self.table_name}
            WHERE {where_clause}
            ORDER BY score
            LIMIT ?
        """,
            params,
        )

        results = []
        for row in cursor:
            results.append(
                {
                    "file_id": row[0],
                    "filepath": row[1],
                    "filename": row[2],
                    "language": row[3],
                    "snippet": row[4],
                    "score": row[5],
                    "type": "content",
                }
            )

        return results

    def _search_symbols(
        self, conn: sqlite3.Connection, query: str, limit: int, **kwargs
    ) -> List[Dict[str, Any]]:
        """Search in symbols with BM25 ranking."""
        kind_filter = kwargs.get("kind")

        # Build WHERE clause
        where_clauses = ["bm25_symbols MATCH ?"]
        params = [query]

        if kind_filter:
            where_clauses.append("kind = ?")
            params.append(kind_filter)

        where_clause = " AND ".join(where_clauses)
        params.append(limit)

        cursor = conn.execute(
            """
            SELECT 
                symbol_id,
                name,
                kind,
                signature,
                filepath,
                highlight(bm25_symbols, 1, '<mark>', '</mark>') as highlighted_name,
                bm25(bm25_symbols) as score
            FROM bm25_symbols
            WHERE {}
            ORDER BY score
            LIMIT ?
        """.format(
                where_clause
            ),
            params,
        )

        results = []
        for row in cursor:
            results.append(
                {
                    "symbol_id": row[0],
                    "name": row[1],
                    "kind": row[2],
                    "signature": row[3],
                    "filepath": row[4],
                    "highlighted_name": row[5],
                    "score": row[6],
                    "type": "symbol",
                }
            )

        return results

    def _search_documents(
        self, conn: sqlite3.Connection, query: str, limit: int, **kwargs
    ) -> List[Dict[str, Any]]:
        """Search in documents with BM25 ranking."""
        cursor = conn.execute(
            """
            SELECT 
                file_id,
                filepath,
                title,
                snippet(bm25_documents, 3, '<mark>', '</mark>', '...', 50) as snippet,
                bm25(bm25_documents) as score
            FROM bm25_documents
            WHERE bm25_documents MATCH ?
            ORDER BY score
            LIMIT ?
        """,
            (query, limit),
        )

        results = []
        for row in cursor:
            results.append(
                {
                    "file_id": row[0],
                    "filepath": row[1],
                    "title": row[2],
                    "snippet": row[3],
                    "score": row[4],
                    "type": "document",
                }
            )

        return results

    def remove_document(self, doc_id: str) -> None:
        """
        Remove a document from the BM25 index.

        Args:
            doc_id: Document identifier (file path)
        """
        with self.storage._get_connection() as conn:
            # Get file record
            file_record = self.storage.get_file(doc_id)
            if not file_record:
                return

            file_id = file_record["id"]

            # Remove from all BM25 tables
            conn.execute(
                f"""
                DELETE FROM {self.table_name} WHERE file_id = ?
            """,
                (file_id,),
            )

            conn.execute(
                """
                DELETE FROM bm25_symbols 
                WHERE symbol_id IN (SELECT id FROM symbols WHERE file_id = ?)
            """,
                (file_id,),
            )

            conn.execute(
                """
                DELETE FROM bm25_documents WHERE file_id = ?
            """,
                (file_id,),
            )

            conn.execute(
                """
                DELETE FROM bm25_index_status WHERE file_id = ?
            """,
                (file_id,),
            )

            logger.debug(f"Removed {doc_id} from BM25 index")

    def update_document(self, doc_id: str, content: str, metadata: Optional[Dict] = None) -> None:
        """
        Update a document in the BM25 index.

        Args:
            doc_id: Document identifier
            content: New content
            metadata: Optional updated metadata
        """
        # For BM25, update is implemented as remove + add
        self.remove_document(doc_id)
        self.add_document(doc_id, content, metadata)

    def clear(self) -> None:
        """Clear all documents from the BM25 index."""
        with self.storage._get_connection() as conn:
            conn.execute(f"DELETE FROM {self.table_name}")
            conn.execute("DELETE FROM bm25_symbols")
            conn.execute("DELETE FROM bm25_documents")
            conn.execute("DELETE FROM bm25_index_status")
            logger.info("BM25 index cleared")

    def get_statistics(self) -> Dict[str, Any]:
        """Get index statistics."""
        with self.storage._get_connection() as conn:
            # Get document count
            cursor = conn.execute(f"SELECT COUNT(*) FROM {self.table_name}")
            doc_count = cursor.fetchone()[0]

            # Get symbol count
            cursor = conn.execute("SELECT COUNT(*) FROM bm25_symbols")
            symbol_count = cursor.fetchone()[0]

            # Get indexed files count
            cursor = conn.execute("SELECT COUNT(*) FROM bm25_index_status")
            indexed_files = cursor.fetchone()[0]

            # Get language distribution
            cursor = conn.execute(
                f"""
                SELECT language, COUNT(*) as count 
                FROM {self.table_name} 
                WHERE language != ''
                GROUP BY language 
                ORDER BY count DESC
            """
            )
            language_dist = {row[0]: row[1] for row in cursor}

            return {
                "total_documents": doc_count,
                "total_symbols": symbol_count,
                "indexed_files": indexed_files,
                "language_distribution": language_dist,
                "index_type": "BM25 (FTS5)",
                "features": [
                    "phrase_search",
                    "prefix_search",
                    "boolean_operators",
                    "ranking",
                ],
            }

    def optimize(self) -> None:
        """Optimize the FTS5 index for better performance."""
        with self.storage._get_connection() as conn:
            # Optimize main content table
            conn.execute(f"INSERT INTO {self.table_name}({self.table_name}) VALUES('optimize')")

            # Optimize symbol table
            conn.execute("INSERT INTO bm25_symbols(bm25_symbols) VALUES('optimize')")

            # Optimize document table
            conn.execute("INSERT INTO bm25_documents(bm25_documents) VALUES('optimize')")

            logger.info("BM25 index optimized")

    def rebuild(self) -> None:
        """Rebuild the entire FTS5 index."""
        with self.storage._get_connection() as conn:
            # Rebuild main content table
            conn.execute(f"INSERT INTO {self.table_name}({self.table_name}) VALUES('rebuild')")

            # Rebuild symbol table
            conn.execute("INSERT INTO bm25_symbols(bm25_symbols) VALUES('rebuild')")

            # Rebuild document table
            conn.execute("INSERT INTO bm25_documents(bm25_documents) VALUES('rebuild')")

            logger.info("BM25 index rebuilt")

    # Additional BM25-specific methods

    def search_phrase(self, phrase: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search for an exact phrase.

        Args:
            phrase: Exact phrase to search for
            limit: Maximum number of results

        Returns:
            List of results containing the exact phrase
        """
        # Wrap phrase in quotes for exact match
        query = f'"{phrase}"'
        return self.search(query, limit)

    def search_near(
        self, terms: List[str], distance: int = 10, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search for terms near each other.

        Args:
            terms: List of terms that should be near each other
            distance: Maximum distance between terms
            limit: Maximum number of results

        Returns:
            List of results with terms within specified distance
        """
        # Build NEAR query
        terms_str = " ".join(terms)
        query = f"NEAR({terms_str}, {distance})"
        return self.search(query, limit)

    def search_prefix(self, prefix: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search for words starting with a prefix.

        Args:
            prefix: Prefix to search for
            limit: Maximum number of results

        Returns:
            List of results with words starting with prefix
        """
        query = f"{prefix}*"
        return self.search(query, limit)

    def get_document_frequency(self, term: str) -> int:
        """
        Get the number of documents containing a term.

        Args:
            term: Term to count

        Returns:
            Number of documents containing the term
        """
        with self.storage._get_connection() as conn:
            cursor = conn.execute(
                f"""
                SELECT COUNT(*) FROM {self.table_name}
                WHERE {self.table_name} MATCH ?
            """,
                (term,),
            )
            return cursor.fetchone()[0]

    def get_term_statistics(self, term: str) -> Dict[str, Any]:
        """
        Get detailed statistics for a term.

        Args:
            term: Term to analyze

        Returns:
            Dictionary with term statistics
        """
        with self.storage._get_connection() as conn:
            # Get document frequency
            doc_freq = self.get_document_frequency(term)

            # Get total documents
            cursor = conn.execute(f"SELECT COUNT(*) FROM {self.table_name}")
            total_docs = cursor.fetchone()[0]

            # Calculate IDF
            import math

            idf = math.log((total_docs + 1) / (doc_freq + 1)) if doc_freq > 0 else 0

            return {
                "term": term,
                "document_frequency": doc_freq,
                "total_documents": total_docs,
                "idf": idf,
                "percentage": (doc_freq / total_docs * 100) if total_docs > 0 else 0,
            }
