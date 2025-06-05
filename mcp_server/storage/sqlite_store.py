"""
SQLite-based persistence layer for the MCP Server.

This module provides a local storage implementation using SQLite with FTS5
for efficient full-text search capabilities.
"""

import sqlite3
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class SQLiteStore:
    """SQLite-based storage implementation with FTS5 support."""
    
    def __init__(self, db_path: str = "code_index.db"):
        """
        Initialize the SQLite store.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize database and create schema if needed."""
        with self._get_connection() as conn:
            # Enable foreign keys
            conn.execute("PRAGMA foreign_keys = ON")
            
            # Check if schema exists
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
            )
            if not cursor.fetchone():
                self._init_schema(conn)
                logger.info(f"Initialized database schema at {self.db_path}")
            else:
                logger.info(f"Using existing database at {self.db_path}")
    
    @contextmanager
    def _get_connection(self):
        """Get a database connection with proper error handling."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _init_schema(self, conn: sqlite3.Connection):
        """Initialize the database schema."""
        # Create core tables
        conn.executescript("""
            -- Schema Version
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                description TEXT
            );
            
            -- Repositories
            CREATE TABLE IF NOT EXISTS repositories (
                id INTEGER PRIMARY KEY,
                path TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata JSON
            );
            
            -- Files
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY,
                repository_id INTEGER NOT NULL,
                path TEXT NOT NULL,
                relative_path TEXT NOT NULL,
                language TEXT,
                size INTEGER,
                hash TEXT,
                last_modified TIMESTAMP,
                indexed_at TIMESTAMP,
                metadata JSON,
                FOREIGN KEY (repository_id) REFERENCES repositories(id),
                UNIQUE(repository_id, path)
            );
            
            CREATE INDEX IF NOT EXISTS idx_files_language ON files(language);
            CREATE INDEX IF NOT EXISTS idx_files_hash ON files(hash);
            
            -- Symbols
            CREATE TABLE IF NOT EXISTS symbols (
                id INTEGER PRIMARY KEY,
                file_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                kind TEXT NOT NULL,
                line_start INTEGER NOT NULL,
                line_end INTEGER NOT NULL,
                column_start INTEGER,
                column_end INTEGER,
                signature TEXT,
                documentation TEXT,
                metadata JSON,
                FOREIGN KEY (file_id) REFERENCES files(id)
            );
            
            CREATE INDEX IF NOT EXISTS idx_symbols_name ON symbols(name);
            CREATE INDEX IF NOT EXISTS idx_symbols_kind ON symbols(kind);
            CREATE INDEX IF NOT EXISTS idx_symbols_file ON symbols(file_id);
            
            -- Imports
            CREATE TABLE IF NOT EXISTS imports (
                id INTEGER PRIMARY KEY,
                file_id INTEGER NOT NULL,
                imported_path TEXT NOT NULL,
                imported_name TEXT,
                alias TEXT,
                line_number INTEGER,
                is_relative BOOLEAN,
                metadata JSON,
                FOREIGN KEY (file_id) REFERENCES files(id)
            );
            
            CREATE INDEX IF NOT EXISTS idx_imports_file ON imports(file_id);
            CREATE INDEX IF NOT EXISTS idx_imports_path ON imports(imported_path);
            
            -- References (using symbol_references to avoid keyword conflict)
            CREATE TABLE IF NOT EXISTS symbol_references (
                id INTEGER PRIMARY KEY,
                symbol_id INTEGER NOT NULL,
                file_id INTEGER NOT NULL,
                line_number INTEGER NOT NULL,
                column_number INTEGER,
                reference_kind TEXT,
                metadata JSON,
                FOREIGN KEY (symbol_id) REFERENCES symbols(id),
                FOREIGN KEY (file_id) REFERENCES files(id)
            );
            
            CREATE INDEX IF NOT EXISTS idx_references_symbol ON symbol_references(symbol_id);
            CREATE INDEX IF NOT EXISTS idx_references_file ON symbol_references(file_id);
            
            -- Full-Text Search tables
            CREATE VIRTUAL TABLE IF NOT EXISTS fts_symbols USING fts5(
                name,
                documentation,
                content=symbols,
                content_rowid=id
            );
            
            CREATE VIRTUAL TABLE IF NOT EXISTS fts_code USING fts5(
                content,
                file_id UNINDEXED
            );
            
            -- Fuzzy Search
            CREATE TABLE IF NOT EXISTS symbol_trigrams (
                symbol_id INTEGER NOT NULL,
                trigram TEXT NOT NULL,
                FOREIGN KEY (symbol_id) REFERENCES symbols(id)
            );
            
            CREATE INDEX IF NOT EXISTS idx_trigrams ON symbol_trigrams(trigram);
            
            -- Embeddings
            CREATE TABLE IF NOT EXISTS embeddings (
                id INTEGER PRIMARY KEY,
                file_id INTEGER,
                symbol_id INTEGER,
                chunk_start INTEGER,
                chunk_end INTEGER,
                embedding BLOB NOT NULL,
                model_version TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata JSON,
                FOREIGN KEY (file_id) REFERENCES files(id),
                FOREIGN KEY (symbol_id) REFERENCES symbols(id)
            );
            
            CREATE INDEX IF NOT EXISTS idx_embeddings_file ON embeddings(file_id);
            CREATE INDEX IF NOT EXISTS idx_embeddings_symbol ON embeddings(symbol_id);
            
            -- Cache Tables
            CREATE TABLE IF NOT EXISTS query_cache (
                query_hash TEXT PRIMARY KEY,
                query_text TEXT NOT NULL,
                result JSON NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                hit_count INTEGER DEFAULT 0
            );
            
            CREATE INDEX IF NOT EXISTS idx_cache_expires ON query_cache(expires_at);
            
            CREATE TABLE IF NOT EXISTS parse_cache (
                file_hash TEXT PRIMARY KEY,
                ast JSON NOT NULL,
                parser_version TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Migration Log
            CREATE TABLE IF NOT EXISTS migrations (
                id INTEGER PRIMARY KEY,
                version_from INTEGER,
                version_to INTEGER,
                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                duration_ms INTEGER,
                status TEXT
            );
            
            -- Insert initial schema version
            INSERT INTO schema_version (version, description) 
            VALUES (1, 'Initial schema creation');
        """)
        
        # Create triggers for FTS
        conn.executescript("""
            -- Triggers to keep FTS in sync with symbols table
            CREATE TRIGGER IF NOT EXISTS symbols_ai AFTER INSERT ON symbols
            BEGIN
                INSERT INTO fts_symbols(rowid, name, documentation)
                VALUES (new.id, new.name, new.documentation);
            END;
            
            CREATE TRIGGER IF NOT EXISTS symbols_ad AFTER DELETE ON symbols
            BEGIN
                DELETE FROM fts_symbols WHERE rowid = old.id;
            END;
            
            CREATE TRIGGER IF NOT EXISTS symbols_au AFTER UPDATE ON symbols
            BEGIN
                UPDATE fts_symbols 
                SET name = new.name, documentation = new.documentation
                WHERE rowid = new.id;
            END;
        """)
    
    # Repository operations
    def create_repository(self, path: str, name: str, metadata: Optional[Dict] = None) -> int:
        """Create a new repository entry with enhanced metadata support."""
        # Enhance metadata with defaults for better tracking
        enhanced_metadata = {
            "created_at": datetime.now().isoformat(),
            "type": "local",  # local, reference, temporary, external
            "language": None,
            "purpose": None,
            "temporary": False,
            "cleanup_after": None,
            "indexed_files_count": 0,
            "last_accessed": datetime.now().isoformat(),
            **(metadata or {})
        }
        
        with self._get_connection() as conn:
            cursor = conn.execute(
                """INSERT INTO repositories (path, name, metadata) 
                   VALUES (?, ?, ?)
                   ON CONFLICT(path) DO UPDATE SET 
                   name=excluded.name, 
                   metadata=excluded.metadata,
                   updated_at=CURRENT_TIMESTAMP""",
                (path, name, json.dumps(enhanced_metadata))
            )
            if cursor.lastrowid:
                return cursor.lastrowid
            else:
                # If lastrowid is None, it means we updated an existing row
                # Get the id of the existing repository
                cursor = conn.execute("SELECT id FROM repositories WHERE path = ?", (path,))
                return cursor.fetchone()[0]
    
    def get_repository(self, path: str) -> Optional[Dict]:
        """Get repository by path."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM repositories WHERE path = ?", (path,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def list_repositories(self, filter_metadata: Optional[Dict] = None) -> List[Dict]:
        """List all repositories with optional metadata filtering."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM repositories ORDER BY created_at DESC")
            repos = [dict(row) for row in cursor.fetchall()]
            
            # Parse metadata and apply filtering
            filtered_repos = []
            for repo in repos:
                try:
                    repo['metadata'] = json.loads(repo['metadata']) if repo['metadata'] else {}
                except json.JSONDecodeError:
                    repo['metadata'] = {}
                
                # Apply filtering if provided
                if filter_metadata:
                    match = True
                    for key, value in filter_metadata.items():
                        if key not in repo['metadata'] or repo['metadata'][key] != value:
                            match = False
                            break
                    if match:
                        filtered_repos.append(repo)
                else:
                    filtered_repos.append(repo)
            
            return filtered_repos

    def get_temporary_repositories(self) -> List[Dict]:
        """Get all temporary repositories that can be cleaned up."""
        return self.list_repositories(filter_metadata={"temporary": True})

    def get_repositories_by_type(self, repo_type: str) -> List[Dict]:
        """Get repositories by type (local, reference, temporary, external)."""
        return self.list_repositories(filter_metadata={"type": repo_type})

    def update_repository_metadata(self, repository_id: int, metadata_updates: Dict) -> bool:
        """Update repository metadata."""
        with self._get_connection() as conn:
            # Get current metadata
            cursor = conn.execute("SELECT metadata FROM repositories WHERE id = ?", (repository_id,))
            row = cursor.fetchone()
            if not row:
                return False
            
            try:
                current_metadata = json.loads(row[0]) if row[0] else {}
            except json.JSONDecodeError:
                current_metadata = {}
            
            # Merge updates
            current_metadata.update(metadata_updates)
            current_metadata["last_accessed"] = datetime.now().isoformat()
            
            # Update database
            cursor = conn.execute(
                "UPDATE repositories SET metadata = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (json.dumps(current_metadata), repository_id)
            )
            return cursor.rowcount > 0

    def delete_repository(self, repository_id: int, cascade: bool = True) -> Dict[str, int]:
        """
        Delete a repository and optionally cascade to related data.
        
        Returns:
            Dictionary with counts of deleted items
        """
        stats = {"repositories": 0, "files": 0, "symbols": 0, "references": 0, "embeddings": 0}
        
        with self._get_connection() as conn:
            if cascade:
                # Get file IDs for this repository
                cursor = conn.execute(
                    "SELECT id FROM files WHERE repository_id = ?", (repository_id,)
                )
                file_ids = [row[0] for row in cursor.fetchall()]
                
                if file_ids:
                    file_ids_str = ",".join(str(fid) for fid in file_ids)
                    
                    # Delete embeddings
                    cursor = conn.execute(f"DELETE FROM embeddings WHERE file_id IN ({file_ids_str})")
                    stats["embeddings"] = cursor.rowcount
                    
                    # Get symbol IDs for this repository
                    cursor = conn.execute(f"SELECT id FROM symbols WHERE file_id IN ({file_ids_str})")
                    symbol_ids = [row[0] for row in cursor.fetchall()]
                    
                    if symbol_ids:
                        symbol_ids_str = ",".join(str(sid) for sid in symbol_ids)
                        
                        # Delete symbol references
                        cursor = conn.execute(f"DELETE FROM symbol_references WHERE symbol_id IN ({symbol_ids_str})")
                        stats["references"] += cursor.rowcount
                        
                        # Delete file-based references  
                        cursor = conn.execute(f"DELETE FROM symbol_references WHERE file_id IN ({file_ids_str})")
                        stats["references"] += cursor.rowcount
                        
                        # Delete trigrams
                        cursor = conn.execute(f"DELETE FROM symbol_trigrams WHERE symbol_id IN ({symbol_ids_str})")
                        
                        # Delete symbols
                        cursor = conn.execute(f"DELETE FROM symbols WHERE file_id IN ({file_ids_str})")
                        stats["symbols"] = cursor.rowcount
                    
                    # Delete imports
                    cursor = conn.execute(f"DELETE FROM imports WHERE file_id IN ({file_ids_str})")
                    
                    # Delete files
                    cursor = conn.execute("DELETE FROM files WHERE repository_id = ?", (repository_id,))
                    stats["files"] = cursor.rowcount
            
            # Delete repository
            cursor = conn.execute("DELETE FROM repositories WHERE id = ?", (repository_id,))
            stats["repositories"] = cursor.rowcount
            
            return stats

    def cleanup_expired_repositories(self) -> Dict[str, Any]:
        """Clean up repositories that have expired."""
        cleanup_stats = {"cleaned_repos": [], "total_deleted": {"repositories": 0, "files": 0, "symbols": 0, "references": 0, "embeddings": 0}}
        
        # Get repositories that should be cleaned up
        temp_repos = self.get_temporary_repositories()
        current_time = datetime.now()
        
        for repo in temp_repos:
            metadata = repo.get('metadata', {})
            cleanup_after = metadata.get('cleanup_after')
            
            if cleanup_after:
                try:
                    cleanup_time = datetime.fromisoformat(cleanup_after)
                    if current_time > cleanup_time:
                        # Time to clean up this repository
                        delete_stats = self.delete_repository(repo['id'], cascade=True)
                        cleanup_stats["cleaned_repos"].append({
                            "repository": repo['name'],
                            "path": repo['path'],
                            "cleanup_time": cleanup_after,
                            "deleted": delete_stats
                        })
                        
                        # Add to totals
                        for key, value in delete_stats.items():
                            cleanup_stats["total_deleted"][key] += value
                            
                except ValueError:
                    # Invalid date format, skip
                    continue
        
        return cleanup_stats

    def get_repository_stats(self, repository_id: Optional[int] = None) -> Dict[str, Any]:
        """Get statistics for repositories."""
        with self._get_connection() as conn:
            if repository_id:
                # Stats for specific repository
                cursor = conn.execute("""
                    SELECT 
                        r.name, r.path, r.metadata,
                        COUNT(DISTINCT f.id) as file_count,
                        COUNT(DISTINCT s.id) as symbol_count,
                        COUNT(DISTINCT sr.id) as reference_count,
                        COUNT(DISTINCT e.id) as embedding_count,
                        SUM(f.size) as total_size
                    FROM repositories r
                    LEFT JOIN files f ON r.id = f.repository_id
                    LEFT JOIN symbols s ON f.id = s.file_id
                    LEFT JOIN symbol_references sr ON s.id = sr.symbol_id
                    LEFT JOIN embeddings e ON f.id = e.file_id
                    WHERE r.id = ?
                    GROUP BY r.id
                """, (repository_id,))
                
                row = cursor.fetchone()
                if row:
                    stats = dict(row)
                    try:
                        stats['metadata'] = json.loads(stats['metadata']) if stats['metadata'] else {}
                    except json.JSONDecodeError:
                        stats['metadata'] = {}
                    return stats
                return {}
            else:
                # Stats for all repositories
                cursor = conn.execute("""
                    SELECT 
                        r.id, r.name, r.path, r.metadata,
                        COUNT(DISTINCT f.id) as file_count,
                        COUNT(DISTINCT s.id) as symbol_count,
                        COUNT(DISTINCT sr.id) as reference_count,
                        COUNT(DISTINCT e.id) as embedding_count,
                        SUM(f.size) as total_size
                    FROM repositories r
                    LEFT JOIN files f ON r.id = f.repository_id
                    LEFT JOIN symbols s ON f.id = s.file_id
                    LEFT JOIN symbol_references sr ON s.id = sr.symbol_id
                    LEFT JOIN embeddings e ON f.id = e.file_id
                    GROUP BY r.id
                    ORDER BY r.created_at DESC
                """)
                
                stats = []
                for row in cursor.fetchall():
                    repo_stats = dict(row)
                    try:
                        repo_stats['metadata'] = json.loads(repo_stats['metadata']) if repo_stats['metadata'] else {}
                    except json.JSONDecodeError:
                        repo_stats['metadata'] = {}
                    stats.append(repo_stats)
                
                return {"repositories": stats}
    
    # File operations
    def store_file(self, repository_id: int, path: str, relative_path: str,
                   language: Optional[str] = None, size: Optional[int] = None,
                   hash: Optional[str] = None, metadata: Optional[Dict] = None) -> int:
        """Store file information."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """INSERT INTO files 
                   (repository_id, path, relative_path, language, size, hash, 
                    last_modified, indexed_at, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, ?)
                   ON CONFLICT(repository_id, path) DO UPDATE SET
                   relative_path=excluded.relative_path,
                   language=excluded.language,
                   size=excluded.size,
                   hash=excluded.hash,
                   last_modified=CURRENT_TIMESTAMP,
                   indexed_at=CURRENT_TIMESTAMP,
                   metadata=excluded.metadata""",
                (repository_id, path, relative_path, language, size, hash, 
                 json.dumps(metadata or {}))
            )
            if cursor.lastrowid:
                return cursor.lastrowid
            else:
                # If lastrowid is None, it means we updated an existing row
                # Get the id of the existing file
                cursor = conn.execute(
                    "SELECT id FROM files WHERE repository_id = ? AND path = ?", 
                    (repository_id, path)
                )
                return cursor.fetchone()[0]
    
    def get_file(self, file_path: str, repository_id: Optional[int] = None) -> Optional[Dict]:
        """Get file by path."""
        with self._get_connection() as conn:
            if repository_id:
                cursor = conn.execute(
                    "SELECT * FROM files WHERE path = ? AND repository_id = ?",
                    (file_path, repository_id)
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM files WHERE path = ?", (file_path,)
                )
            row = cursor.fetchone()
            return dict(row) if row else None
    
    # Symbol operations
    def store_symbol(self, file_id: int, name: str, kind: str,
                     line_start: int, line_end: int,
                     column_start: Optional[int] = None,
                     column_end: Optional[int] = None,
                     signature: Optional[str] = None,
                     documentation: Optional[str] = None,
                     metadata: Optional[Dict] = None) -> int:
        """Store a symbol definition."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """INSERT INTO symbols 
                   (file_id, name, kind, line_start, line_end, column_start, 
                    column_end, signature, documentation, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (file_id, name, kind, line_start, line_end, column_start,
                 column_end, signature, documentation, json.dumps(metadata or {}))
            )
            symbol_id = cursor.lastrowid
            
            # Generate and store trigrams for fuzzy search
            self._store_trigrams(conn, symbol_id, name)
            
            return symbol_id
    
    def _store_trigrams(self, conn: sqlite3.Connection, symbol_id: int, name: str):
        """Generate and store trigrams for a symbol name."""
        # Generate trigrams
        trigrams = set()
        padded_name = f"  {name}  "  # Pad with spaces for edge trigrams
        for i in range(len(padded_name) - 2):
            trigram = padded_name[i:i+3].lower()
            trigrams.add(trigram)
        
        # Store trigrams
        for trigram in trigrams:
            conn.execute(
                "INSERT INTO symbol_trigrams (symbol_id, trigram) VALUES (?, ?)",
                (symbol_id, trigram)
            )
    
    def get_symbol(self, name: str, kind: Optional[str] = None) -> List[Dict]:
        """Get symbols by name and optionally kind."""
        with self._get_connection() as conn:
            if kind:
                cursor = conn.execute(
                    """SELECT s.*, f.path as file_path 
                       FROM symbols s
                       JOIN files f ON s.file_id = f.id
                       WHERE s.name = ? AND s.kind = ?""",
                    (name, kind)
                )
            else:
                cursor = conn.execute(
                    """SELECT s.*, f.path as file_path 
                       FROM symbols s
                       JOIN files f ON s.file_id = f.id
                       WHERE s.name = ?""",
                    (name,)
                )
            return [dict(row) for row in cursor.fetchall()]
    
    # Reference operations
    def store_reference(self, symbol_id: int, file_id: int,
                       line_number: int, column_number: Optional[int] = None,
                       reference_kind: Optional[str] = None,
                       metadata: Optional[Dict] = None) -> int:
        """Store a symbol reference."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """INSERT INTO symbol_references 
                   (symbol_id, file_id, line_number, column_number, 
                    reference_kind, metadata)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (symbol_id, file_id, line_number, column_number,
                 reference_kind, json.dumps(metadata or {}))
            )
            return cursor.lastrowid
    
    def get_references(self, symbol_id: int) -> List[Dict]:
        """Get all references to a symbol."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """SELECT r.*, f.path as file_path
                   FROM symbol_references r
                   JOIN files f ON r.file_id = f.id
                   WHERE r.symbol_id = ?""",
                (symbol_id,)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    # Search operations
    def search_symbols_fuzzy(self, query: str, limit: int = 20) -> List[Dict]:
        """
        Fuzzy search for symbols using trigrams.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching symbols with relevance scores
        """
        with self._get_connection() as conn:
            # Generate trigrams for the query
            query_trigrams = set()
            padded_query = f"  {query}  "
            for i in range(len(padded_query) - 2):
                trigram = padded_query[i:i+3].lower()
                query_trigrams.add(trigram)
            
            if not query_trigrams:
                return []
            
            # Build query with trigram matching
            placeholders = ','.join(['?'] * len(query_trigrams))
            
            cursor = conn.execute(f"""
                SELECT s.*, f.path as file_path,
                       COUNT(DISTINCT st.trigram) as matches,
                       COUNT(DISTINCT st.trigram) * 1.0 / ? as score
                FROM symbols s
                JOIN files f ON s.file_id = f.id
                JOIN symbol_trigrams st ON s.id = st.symbol_id
                WHERE st.trigram IN ({placeholders})
                GROUP BY s.id
                ORDER BY score DESC, s.name
                LIMIT ?
            """, [len(query_trigrams)] + list(query_trigrams) + [limit])
            
            return [dict(row) for row in cursor.fetchall()]
    
    def search_symbols_fts(self, query: str, limit: int = 20) -> List[Dict]:
        """
        Full-text search for symbols.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching symbols
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """SELECT s.*, f.path as file_path
                   FROM symbols s
                   JOIN files f ON s.file_id = f.id
                   JOIN fts_symbols ON s.id = fts_symbols.rowid
                   WHERE fts_symbols MATCH ?
                   ORDER BY rank
                   LIMIT ?""",
                (query, limit)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def search_code_fts(self, query: str, limit: int = 20) -> List[Dict]:
        """
        Full-text search in code content.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching code snippets
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """SELECT fts.*, f.path as file_path
                   FROM fts_code fts
                   JOIN files f ON fts.file_id = f.id
                   WHERE fts_code MATCH ?
                   ORDER BY rank
                   LIMIT ?""",
                (query, limit)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    # Index operations for fuzzy_indexer.py integration
    def persist_fuzzy_index(self, index_data: Dict[str, List[Tuple[str, Any]]]):
        """
        Persist fuzzy index data to database.
        
        Args:
            index_data: Dictionary mapping trigrams to list of (item, metadata) tuples
        """
        with self._get_connection() as conn:
            # Clear existing fuzzy index (for simplicity; in production, use incremental updates)
            conn.execute("DELETE FROM symbol_trigrams")
            
            # Store all symbols and their trigrams
            for trigram, items in index_data.items():
                for item, metadata in items:
                    # For now, assume item is a symbol name and metadata contains file info
                    # This is a simplified implementation
                    if isinstance(metadata, dict) and 'file_id' in metadata:
                        conn.execute(
                            "INSERT INTO symbol_trigrams (symbol_id, trigram) VALUES (?, ?)",
                            (metadata.get('symbol_id', 0), trigram)
                        )
    
    def load_fuzzy_index(self) -> Dict[str, List[Tuple[str, Any]]]:
        """
        Load fuzzy index data from database.
        
        Returns:
            Dictionary mapping trigrams to list of (item, metadata) tuples
        """
        index_data = {}
        
        with self._get_connection() as conn:
            cursor = conn.execute(
                """SELECT st.trigram, s.name, s.id, s.file_id, f.path
                   FROM symbol_trigrams st
                   JOIN symbols s ON st.symbol_id = s.id
                   JOIN files f ON s.file_id = f.id"""
            )
            
            for row in cursor:
                trigram = row['trigram']
                if trigram not in index_data:
                    index_data[trigram] = []
                
                # Store symbol name with metadata
                metadata = {
                    'symbol_id': row['id'],
                    'file_id': row['file_id'],
                    'file_path': row['path']
                }
                index_data[trigram].append((row['name'], metadata))
        
        return index_data
    
    # Utility methods
    def clear_cache(self):
        """Clear expired cache entries."""
        with self._get_connection() as conn:
            conn.execute(
                "DELETE FROM query_cache WHERE expires_at < CURRENT_TIMESTAMP"
            )
    
    def get_statistics(self) -> Dict[str, int]:
        """Get database statistics."""
        stats = {}
        with self._get_connection() as conn:
            tables = ['repositories', 'files', 'symbols', 'symbol_references', 'imports']
            for table in tables:
                cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                stats[table] = cursor.fetchone()[0]
        return stats