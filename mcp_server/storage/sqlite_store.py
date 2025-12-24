"""
SQLite-based persistence layer for the MCP Server.

This module provides a local storage implementation using SQLite with FTS5
for efficient full-text search capabilities.
"""

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from ..core.path_resolver import PathResolver

logger = logging.getLogger(__name__)


class SQLiteStore:
    """SQLite-based storage implementation with FTS5 support."""

    def __init__(
        self,
        db_path: str = "code_index.db",
        path_resolver: Optional[PathResolver] = None,
    ):
        """
        Initialize the SQLite store.

        Args:
            db_path: Path to the SQLite database file
            path_resolver: PathResolver instance for path management
        """
        self.db_path = db_path
        self.path_resolver = path_resolver or PathResolver()

        self._init_database()
        self._run_migrations()

    def _init_database(self):
        """Initialize database and create schema if needed."""
        with self._get_connection() as conn:
            # Enable WAL mode for better concurrency
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA busy_timeout = 5000")  # 5 second timeout
            # Enable foreign keys
            conn.execute("PRAGMA foreign_keys = ON")

            # Enable FTS5 if available
            self._check_fts5_support(conn)

            # Check if this is a simple BM25 index (no schema_version table)
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='bm25_content'"
            )
            if cursor.fetchone():
                # This is a simple BM25 index, don't try to initialize schema
                logger.info(f"Using existing BM25 index at {self.db_path}")
                return

            # Check if schema exists
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
            )
            if not cursor.fetchone():
                self._init_schema(conn)
                logger.info(f"Initialized database schema at {self.db_path}")
            else:
                logger.info(f"Using existing database at {self.db_path}")

                # Check for missing columns that may need migration
                if not self._check_column_exists(conn, "files", "content_hash"):
                    logger.warning(
                        "Column 'content_hash' missing from 'files' table - migration may be needed"
                    )
                if not self._check_column_exists(conn, "files", "is_deleted"):
                    logger.warning(
                        "Column 'is_deleted' missing from 'files' table - migration may be needed"
                    )
                if not self._check_column_exists(conn, "files", "deleted_at"):
                    logger.warning(
                        "Column 'deleted_at' missing from 'files' table - migration may be needed"
                    )

    def _run_migrations(self):
        """Run any pending database migrations."""
        # Skip migrations for BM25-only databases
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='bm25_content'"
            )
            if (
                cursor.fetchone()
                and not conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
                ).fetchone()
            ):
                logger.debug("Skipping migrations for BM25-only database")
                return

        migrations_dir = Path(__file__).parent / "migrations"
        if not migrations_dir.exists():
            return

        with self._get_connection() as conn:
            # Get current schema version
            try:
                cursor = conn.execute("SELECT MAX(version) FROM schema_version")
                current_version = cursor.fetchone()[0] or 0
            except sqlite3.OperationalError:
                current_version = 0

            # Run migrations
            for migration_file in sorted(migrations_dir.glob("*.sql")):
                # Extract version from filename (e.g., "002_relative_paths.sql" -> 2)
                try:
                    version = int(migration_file.stem.split("_")[0])
                except (ValueError, IndexError):
                    continue

                if version > current_version:
                    logger.info(f"Running migration {migration_file.name}")
                    with open(migration_file, "r") as f:
                        conn.executescript(f.read())
                    logger.info(f"Completed migration to version {version}")

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

    def _check_fts5_support(self, conn: sqlite3.Connection) -> bool:
        """Check if FTS5 is supported in this SQLite build."""
        try:
            cursor = conn.execute("PRAGMA compile_options;")
            options = [row[0] for row in cursor]
            fts5_enabled = any("ENABLE_FTS5" in option for option in options)
            if fts5_enabled:
                logger.info("FTS5 support confirmed")
            else:
                logger.warning("FTS5 may not be available in this SQLite build")
            return fts5_enabled
        except Exception as e:
            logger.warning(f"Could not check FTS5 support: {e}")
            return False

    def _check_column_exists(self, conn: sqlite3.Connection, table: str, column: str) -> bool:
        """Check if a column exists in a table."""
        try:
            cursor = conn.execute(f"PRAGMA table_info({table})")
            columns = [row[1] for row in cursor.fetchall()]
            return column in columns
        except Exception as e:
            logger.warning(f"Could not check column {table}.{column}: {e}")
            return False

    def _init_schema(self, conn: sqlite3.Connection):
        """Initialize the database schema."""
        # Create core tables
        conn.executescript(
            """
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
                content_hash TEXT,
                last_modified TIMESTAMP,
                indexed_at TIMESTAMP,
                is_deleted BOOLEAN DEFAULT FALSE,
                deleted_at TIMESTAMP,
                metadata JSON,
                FOREIGN KEY (repository_id) REFERENCES repositories(id),
                UNIQUE(repository_id, relative_path)
            );
            
            CREATE INDEX IF NOT EXISTS idx_files_language ON files(language);
            CREATE INDEX IF NOT EXISTS idx_files_hash ON files(hash);
            CREATE INDEX IF NOT EXISTS idx_files_content_hash ON files(content_hash);
            CREATE INDEX IF NOT EXISTS idx_files_deleted ON files(is_deleted);
            CREATE INDEX IF NOT EXISTS idx_files_relative_path ON files(relative_path);
            
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
            
            -- Index Configuration
            CREATE TABLE IF NOT EXISTS index_config (
                id INTEGER PRIMARY KEY,
                config_key TEXT UNIQUE NOT NULL,
                config_value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                description TEXT
            );

            -- File Moves Tracking
            CREATE TABLE IF NOT EXISTS file_moves (
                id INTEGER PRIMARY KEY,
                repository_id INTEGER NOT NULL,
                old_relative_path TEXT NOT NULL,
                new_relative_path TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                moved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                move_type TEXT CHECK(move_type IN ('rename', 'relocate', 'restructure')),
                FOREIGN KEY (repository_id) REFERENCES repositories(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_moves_content_hash ON file_moves(content_hash);
            CREATE INDEX IF NOT EXISTS idx_moves_timestamp ON file_moves(moved_at);
            CREATE INDEX IF NOT EXISTS idx_moves_old_path ON file_moves(old_relative_path);
            CREATE INDEX IF NOT EXISTS idx_moves_new_path ON file_moves(new_relative_path);

            -- Insert initial index configuration
            INSERT OR IGNORE INTO index_config (config_key, config_value, description) VALUES
                ('embedding_model', 'voyage-code-3', 'Current embedding model used for vector search'),
                ('model_dimension', '1024', 'Embedding vector dimension'),
                ('distance_metric', 'cosine', 'Distance metric for vector similarity'),
                ('index_version', '1.0', 'Index schema version');

            -- Insert initial schema version
            INSERT INTO schema_version (version, description)
            VALUES (2, 'Initial schema creation with content tracking and soft delete support');
        """
        )

        # Create triggers for FTS
        conn.executescript(
            """
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
        """
        )

    # Repository operations
    def create_repository(self, path: str, name: str, metadata: Optional[Dict] = None) -> int:
        """Create a new repository entry."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """INSERT INTO repositories (path, name, metadata) 
                   VALUES (?, ?, ?)
                   ON CONFLICT(path) DO UPDATE SET 
                   name=excluded.name, 
                   metadata=excluded.metadata,
                   updated_at=CURRENT_TIMESTAMP""",
                (path, name, json.dumps(metadata or {})),
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
            cursor = conn.execute("SELECT * FROM repositories WHERE path = ?", (path,))
            row = cursor.fetchone()
            return dict(row) if row else None

    # File operations
    def store_file(
        self,
        repository_id: int,
        path: Optional[Union[str, Path]] = None,
        relative_path: Optional[Union[str, Path]] = None,
        language: Optional[str] = None,
        size: Optional[int] = None,
        hash: Optional[str] = None,
        content_hash: Optional[str] = None,
        metadata: Optional[Dict] = None,
        is_deleted: bool = False,
        deleted_at: Optional[Union[str, datetime]] = None,
        **kwargs: Any,
    ) -> int:
        """Store file information using relative paths and content hashes."""
        file_path_arg = kwargs.pop("file_path", None)
        resolved_path = Path(path or file_path_arg) if path or file_path_arg else None

        if not resolved_path and not relative_path:
            raise ValueError("Either 'path' or 'relative_path' must be provided to store_file")

        relative_path_str: Optional[str] = None
        if relative_path is not None:
            relative_path_str = str(relative_path).replace("\\", "/")
        elif resolved_path:
            try:
                relative_path_str = self.path_resolver.normalize_path(resolved_path)
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning(f"Could not normalize path {resolved_path}: {exc}")
                relative_path_str = str(resolved_path).replace("\\", "/")

        if not relative_path_str:
            raise ValueError("Relative path could not be determined for file storage")

        # Normalize stored path string
        stored_path = str(resolved_path) if resolved_path else relative_path_str

        # Determine filesystem metadata when available
        path_exists = resolved_path.exists() if resolved_path else False
        file_size = size
        if file_size is None and path_exists:
            try:
                file_size = resolved_path.stat().st_size
            except OSError as exc:  # pragma: no cover - defensive
                logger.warning(f"Could not read size for {resolved_path}: {exc}")

        file_hash = hash
        if file_hash is None and path_exists:
            try:
                file_hash = self.path_resolver.compute_file_hash(resolved_path)
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning(f"Failed to compute file hash for {resolved_path}: {exc}")

        content_hash_value = content_hash
        if content_hash_value is None and path_exists:
            try:
                content_hash_value = self.path_resolver.compute_content_hash(resolved_path)
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning(f"Failed to compute content hash for {resolved_path}: {exc}")

        last_modified_value = (
            datetime.fromtimestamp(resolved_path.stat().st_mtime, tz=timezone.utc)
            if path_exists
            else datetime.now(timezone.utc)
        )
        indexed_at_value = datetime.now(timezone.utc)

        with self._get_connection() as conn:
            # Check if file already exists with same content hash
            existing = (
                self.get_file_by_content_hash(content_hash_value, repository_id)
                if content_hash_value
                else None
            )
            if existing and existing["relative_path"] != relative_path_str:
                # File moved - record the move
                self.move_file(
                    existing["relative_path"],
                    relative_path_str,
                    repository_id,
                    content_hash_value or "",
                )
                return existing["id"]

            # Store using relative path as primary identifier
            cursor = conn.execute(
                """INSERT INTO files 
                   (repository_id, path, relative_path, language, size, hash, content_hash,
                    last_modified, indexed_at, metadata, is_deleted, deleted_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(repository_id, relative_path) DO UPDATE SET
                   path=excluded.path,
                   language=excluded.language,
                   size=excluded.size,
                   hash=excluded.hash,
                   content_hash=excluded.content_hash,
                   last_modified=excluded.last_modified,
                   indexed_at=excluded.indexed_at,
                   metadata=excluded.metadata,
                   is_deleted=excluded.is_deleted,
                   deleted_at=excluded.deleted_at""",
                (
                    repository_id,
                    stored_path,
                    relative_path_str,
                    language,
                    file_size,
                    file_hash,
                    content_hash_value,
                    last_modified_value,
                    indexed_at_value,
                    json.dumps(metadata or {}),
                    bool(is_deleted),
                    deleted_at,
                ),
            )
            if cursor.lastrowid:
                return cursor.lastrowid
            else:
                # Get the id of the existing file
                cursor = conn.execute(
                    "SELECT id FROM files WHERE repository_id = ? AND relative_path = ?",
                    (repository_id, relative_path),
                )
                return cursor.fetchone()[0]

    def get_file(
        self, file_path: Union[str, Path], repository_id: Optional[int] = None
    ) -> Optional[Dict]:
        """Get file by path (relative or absolute)."""
        # Try to normalize path if it's absolute
        try:
            relative_path = self.path_resolver.normalize_path(file_path)
        except ValueError:
            # Path might already be relative
            relative_path = str(file_path).replace("\\", "/")

        with self._get_connection() as conn:
            if repository_id:
                cursor = conn.execute(
                    "SELECT * FROM files WHERE relative_path = ? AND repository_id = ? AND is_deleted = FALSE",
                    (relative_path, repository_id),
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM files WHERE relative_path = ? AND is_deleted = FALSE",
                    (relative_path,),
                )
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_file_by_path(
        self, file_path: Union[str, Path], repository_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Get a file record by path, returning normalized paths and content hash."""
        try:
            relative_path = self.path_resolver.normalize_path(file_path)
        except ValueError:
            relative_path = str(file_path).replace("\\", "/")

        with self._get_connection() as conn:
            query = "SELECT * FROM files WHERE relative_path = ? AND is_deleted = FALSE"
            params: Tuple[Union[str, int], ...]

            if repository_id is not None:
                query += " AND repository_id = ?"
                params = (relative_path, repository_id)
            else:
                params = (relative_path,)

            cursor = conn.execute(query, params)
            row = cursor.fetchone()
            return self._normalize_file_record(row) if row else None

    def get_all_files(self, repository_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get all non-deleted files with normalized paths and content hashes."""
        with self._get_connection() as conn:
            query = "SELECT * FROM files WHERE is_deleted = FALSE"
            params: Tuple[Union[str, int], ...] = ()

            if repository_id is not None:
                query += " AND repository_id = ?"
                params = (repository_id,)

            cursor = conn.execute(query, params)
            return [self._normalize_file_record(row) for row in cursor.fetchall()]

    def _normalize_file_record(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Normalize file record paths and include content hash."""
        record = dict(row)
        original_path = record.get("path") or ""
        relative_path = record.get("relative_path")

        normalized_path: Optional[str] = None
        if relative_path:
            normalized_path = str(relative_path).replace("\\", "/")
        elif original_path:
            try:
                normalized_path = self.path_resolver.normalize_path(original_path)
            except Exception:
                normalized_path = str(original_path).replace("\\", "/")

        if normalized_path:
            record["path"] = normalized_path
            record["relative_path"] = normalized_path
            try:
                record["absolute_path"] = str(self.path_resolver.resolve_path(normalized_path))
            except Exception:
                record["absolute_path"] = original_path or normalized_path
        else:
            record["absolute_path"] = original_path

        record["content_hash"] = record.get("content_hash") or record.get("hash")
        return record

    # Symbol operations
    def store_symbol(
        self,
        file_id: int,
        name: str,
        kind: str,
        line_start: int,
        line_end: int,
        column_start: Optional[int] = None,
        column_end: Optional[int] = None,
        signature: Optional[str] = None,
        documentation: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> int:
        """Store a symbol definition."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """INSERT INTO symbols 
                   (file_id, name, kind, line_start, line_end, column_start, 
                    column_end, signature, documentation, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    file_id,
                    name,
                    kind,
                    line_start,
                    line_end,
                    column_start,
                    column_end,
                    signature,
                    documentation,
                    json.dumps(metadata or {}),
                ),
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
            trigram = padded_name[i : i + 3].lower()
            trigrams.add(trigram)

        # Store trigrams
        for trigram in trigrams:
            conn.execute(
                "INSERT INTO symbol_trigrams (symbol_id, trigram) VALUES (?, ?)",
                (symbol_id, trigram),
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
                    (name, kind),
                )
            else:
                cursor = conn.execute(
                    """SELECT s.*, f.path as file_path 
                       FROM symbols s
                       JOIN files f ON s.file_id = f.id
                       WHERE s.name = ?""",
                    (name,),
                )
            return [dict(row) for row in cursor.fetchall()]

    # Reference operations
    def store_reference(
        self,
        symbol_id: int,
        file_id: int,
        line_number: int,
        column_number: Optional[int] = None,
        reference_kind: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> int:
        """Store a symbol reference."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """INSERT INTO symbol_references 
                   (symbol_id, file_id, line_number, column_number, 
                    reference_kind, metadata)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    symbol_id,
                    file_id,
                    line_number,
                    column_number,
                    reference_kind,
                    json.dumps(metadata or {}),
                ),
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
                (symbol_id,),
            )
            return [dict(row) for row in cursor.fetchall()]

    # Search operations
    def search_symbols(
        self,
        query: Optional[str] = None,
        where_clause: Optional[str] = None,
        params: Optional[List[Any]] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Search for symbols with optional filtering.

        Args:
            query: Optional symbol name or pattern (uses LIKE)
            where_clause: Optional WHERE clause fragment (without the WHERE keyword)
            params: Parameters for the WHERE clause
            limit: Maximum number of results

        Returns:
            List of matching symbols with normalized fields
        """
        if not where_clause and query is not None:
            where_clause = "s.name LIKE ?"
            params = [f"%{query}%"]

        where_clause = where_clause or "1=1"
        parameters: List[Any] = list(params or [])

        sql = f"""
            SELECT
                s.name,
                s.kind AS type,
                f.language,
                COALESCE(f.relative_path, f.path) AS file_path,
                s.line_start AS line,
                s.line_end,
                s.column_start,
                s.column_end,
                s.signature,
                s.documentation
            FROM symbols s
            JOIN files f ON s.file_id = f.id
            WHERE {where_clause}
            ORDER BY s.name
            LIMIT ?
        """

        parameters.append(limit)

        with self._get_connection() as conn:
            cursor = conn.execute(sql, parameters)
            results = [dict(row) for row in cursor.fetchall()]

        for result in results:
            if "type" not in result and "kind" in result:
                result["type"] = result["kind"]
            if "file_path" not in result:
                result["file_path"] = result.get("path") or result.get("relative_path")
            if "line" not in result:
                result["line"] = result.get("line_start") or result.get("line_number")

        return results

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
                trigram = padded_query[i : i + 3].lower()
                query_trigrams.add(trigram)

            if not query_trigrams:
                return []

            # Build query with trigram matching
            placeholders = ",".join(["?"] * len(query_trigrams))

            cursor = conn.execute(
                f"""
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
            """,
                [len(query_trigrams)] + list(query_trigrams) + [limit],
            )

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
                (query, limit),
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
                (query, limit),
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
                    if isinstance(metadata, dict) and "file_id" in metadata:
                        conn.execute(
                            "INSERT INTO symbol_trigrams (symbol_id, trigram) VALUES (?, ?)",
                            (metadata.get("symbol_id", 0), trigram),
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
                trigram = row["trigram"]
                if trigram not in index_data:
                    index_data[trigram] = []

                # Store symbol name with metadata
                metadata = {
                    "symbol_id": row["id"],
                    "file_id": row["file_id"],
                    "file_path": row["path"],
                }
                index_data[trigram].append((row["name"], metadata))

        return index_data

    # Utility methods
    def clear_cache(self):
        """Clear expired cache entries."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM query_cache WHERE expires_at < CURRENT_TIMESTAMP")

    def get_statistics(self) -> Dict[str, int]:
        """Get database statistics."""
        stats = {}
        with self._get_connection() as conn:
            tables = [
                "repositories",
                "files",
                "symbols",
                "symbol_references",
                "imports",
            ]
            for table in tables:
                cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                stats[table] = cursor.fetchone()[0]
        return stats

    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on database.

        Returns:
            Dictionary containing:
            - status: "healthy" | "degraded" | "unhealthy"
            - tables: Dict[str, bool] - table existence check
            - fts5: bool - FTS5 availability
            - wal: bool - WAL mode status
            - version: int - schema version (0 if not available)
            - error: Optional[str] - error message if unhealthy
        """
        result = {
            "status": "healthy",
            "tables": {},
            "fts5": False,
            "wal": False,
            "version": 0,
            "error": None,
        }

        try:
            with self._get_connection() as conn:
                # Check required tables
                required_tables = [
                    "schema_version",
                    "repositories",
                    "files",
                    "symbols",
                    "symbol_references",
                    "imports",
                    "fts_symbols",
                    "fts_code",
                    "symbol_trigrams",
                    "embeddings",
                    "query_cache",
                    "parse_cache",
                    "migrations",
                    "index_config",
                    "file_moves",
                ]

                for table in required_tables:
                    cursor = conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
                    )
                    result["tables"][table] = cursor.fetchone() is not None

                # Check FTS5 support
                result["fts5"] = self._check_fts5_support(conn)

                # Check WAL mode
                cursor = conn.execute("PRAGMA journal_mode")
                journal_mode = cursor.fetchone()[0].upper()
                result["wal"] = journal_mode == "WAL"

                # Get schema version
                if result["tables"].get("schema_version", False):
                    try:
                        cursor = conn.execute("SELECT MAX(version) FROM schema_version")
                        version_row = cursor.fetchone()
                        result["version"] = version_row[0] if version_row and version_row[0] else 0
                    except sqlite3.OperationalError:
                        result["version"] = 0

                # Determine health status
                missing_tables = [table for table, exists in result["tables"].items() if not exists]
                if missing_tables:
                    if len(missing_tables) > 5:
                        result["status"] = "unhealthy"
                        result["error"] = (
                            f"Critical tables missing: {', '.join(missing_tables[:5])} and {len(missing_tables) - 5} more"
                        )
                    else:
                        result["status"] = "degraded"
                        result["error"] = f"Some tables missing: {', '.join(missing_tables)}"
                elif not result["fts5"]:
                    result["status"] = "degraded"
                    result["error"] = "FTS5 support not available - search functionality limited"
                elif not result["wal"]:
                    result["status"] = "degraded"
                    result["error"] = "WAL mode not enabled - concurrency may be affected"

        except Exception as e:
            result["status"] = "unhealthy"
            result["error"] = f"Database health check failed: {str(e)}"
            logger.error(f"Health check error: {e}")

        return result

    # Enhanced FTS5 search methods for BM25

    def search_bm25(
        self,
        query: str,
        table: str = "fts_code",
        limit: int = 20,
        offset: int = 0,
        columns: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Perform BM25 search using FTS5.

        Args:
            query: FTS5 query string
            table: FTS table to search
            limit: Maximum results
            offset: Result offset for pagination
            columns: Specific columns to return

        Returns:
            List of search results with BM25 scores
        """
        with self._get_connection() as conn:
            # Check if this is a simple BM25 table (like bm25_content) or structured FTS
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
            )
            if not cursor.fetchone():
                # Table doesn't exist
                return []

            # Check table structure
            cursor = conn.execute(f"PRAGMA table_info({table})")
            table_columns = {row[1] for row in cursor.fetchall()}

            if table == "fts_code" and "file_id" in table_columns:
                # Modern schema with file_id references - join with files table
                cursor = conn.execute(
                    """
                    SELECT 
                        fts.content,
                        fts.file_id,
                        f.path as filepath,
                        f.relative_path,
                        bm25(fts_code) as score,
                        snippet(fts_code, 0, '<mark>', '</mark>', '...', 32) as snippet
                    FROM fts_code fts
                    JOIN files f ON fts.file_id = f.id
                    WHERE fts_code MATCH ?
                    ORDER BY bm25(fts_code)
                    LIMIT ? OFFSET ?
                    """,
                    (query, limit, offset),
                )
            elif table == "bm25_content" and "filepath" in table_columns:
                # Legacy BM25 schema with direct filepath column
                if not columns:
                    columns = ["*", f"bm25({table}) as score"]
                else:
                    columns = columns + [f"bm25({table}) as score"]

                columns_str = ", ".join(columns)
                cursor = conn.execute(
                    f"""
                    SELECT {columns_str}
                    FROM {table}
                    WHERE {table} MATCH ?
                    ORDER BY bm25({table})
                    LIMIT ? OFFSET ?
                    """,
                    (query, limit, offset),
                )
            else:
                # Generic fallback
                if not columns:
                    columns = ["*", f"bm25({table}) as score"]
                else:
                    columns = columns + [f"bm25({table}) as score"]

                columns_str = ", ".join(columns)
                cursor = conn.execute(
                    f"""
                    SELECT {columns_str}
                    FROM {table}
                    WHERE {table} MATCH ?
                    ORDER BY bm25({table})
                    LIMIT ? OFFSET ?
                    """,
                    (query, limit, offset),
                )

            results = []
            for row in cursor:
                results.append(dict(row))

            return results

    def search_bm25_with_snippets(
        self,
        query: str,
        table: str = "fts_code",
        content_column: int = 0,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Search with BM25 and return snippets.

        Args:
            query: FTS5 query string
            table: FTS table to search
            content_column: Column index for snippet extraction
            limit: Maximum results

        Returns:
            List of results with snippets
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                f"""
                SELECT 
                    *,
                    snippet({table}, {content_column}, '<mark>', '</mark>', '...', 32) as snippet,
                    bm25({table}) as score
                FROM {table}
                WHERE {table} MATCH ?
                ORDER BY bm25({table})
                LIMIT ?
            """,
                (query, limit),
            )

            results = []
            for row in cursor:
                results.append(dict(row))

            return results

    def search_bm25_with_highlight(
        self,
        query: str,
        table: str = "fts_code",
        highlight_column: int = 0,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Search with BM25 and return highlighted content.

        Args:
            query: FTS5 query string
            table: FTS table to search
            highlight_column: Column index for highlighting
            limit: Maximum results

        Returns:
            List of results with highlighted content
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                f"""
                SELECT 
                    *,
                    highlight({table}, {highlight_column}, '<b>', '</b>') as highlighted,
                    bm25({table}) as score
                FROM {table}
                WHERE {table} MATCH ?
                ORDER BY bm25({table})
                LIMIT ?
            """,
                (query, limit),
            )

            results = []
            for row in cursor:
                results.append(dict(row))

            return results

    def get_bm25_term_statistics(self, term: str, table: str = "fts_code") -> Dict[str, Any]:
        """
        Get term statistics for BM25 tuning.

        Args:
            term: Term to analyze
            table: FTS table to search

        Returns:
            Dictionary with term statistics
        """
        with self._get_connection() as conn:
            # Get document frequency
            cursor = conn.execute(
                f"""
                SELECT COUNT(*) FROM {table}
                WHERE {table} MATCH ?
            """,
                (term,),
            )
            doc_freq = cursor.fetchone()[0]

            # Get total documents
            cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
            total_docs = cursor.fetchone()[0]

            # Get average document length (approximation)
            cursor = conn.execute(
                f"""
                SELECT AVG(LENGTH(content)) FROM {table}
            """
            )
            avg_doc_length = cursor.fetchone()[0] or 0

            return {
                "term": term,
                "document_frequency": doc_freq,
                "total_documents": total_docs,
                "idf": self._calculate_idf(doc_freq, total_docs),
                "average_document_length": avg_doc_length,
            }

    def _calculate_idf(self, doc_freq: int, total_docs: int) -> float:
        """Calculate Inverse Document Frequency."""
        import math

        if doc_freq == 0:
            return 0
        return math.log((total_docs - doc_freq + 0.5) / (doc_freq + 0.5))

    def optimize_fts_tables(self):
        """Optimize all FTS5 tables for better performance."""
        with self._get_connection() as conn:
            # Get all FTS5 tables
            cursor = conn.execute(
                """
                SELECT name FROM sqlite_master 
                WHERE type='table' AND sql LIKE '%USING fts5%'
            """
            )

            fts_tables = [row[0] for row in cursor]

            for table in fts_tables:
                try:
                    conn.execute(f"INSERT INTO {table}({table}) VALUES('optimize')")
                    logger.info(f"Optimized FTS5 table: {table}")
                except Exception as e:
                    logger.warning(f"Could not optimize {table}: {e}")

    def rebuild_fts_tables(self):
        """Rebuild all FTS5 tables."""
        with self._get_connection() as conn:
            # Get all FTS5 tables
            cursor = conn.execute(
                """
                SELECT name FROM sqlite_master 
                WHERE type='table' AND sql LIKE '%USING fts5%'
            """
            )

            fts_tables = [row[0] for row in cursor]

            for table in fts_tables:
                try:
                    conn.execute(f"INSERT INTO {table}({table}) VALUES('rebuild')")
                    logger.info(f"Rebuilt FTS5 table: {table}")
                except Exception as e:
                    logger.warning(f"Could not rebuild {table}: {e}")

    # New file operation methods for path management
    def get_file_by_content_hash(self, content_hash: str, repository_id: int) -> Optional[Dict]:
        """Get file by content hash."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """SELECT * FROM files 
                   WHERE content_hash = ? AND repository_id = ? AND is_deleted = FALSE
                   ORDER BY indexed_at DESC LIMIT 1""",
                (content_hash, repository_id),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def mark_file_deleted(self, relative_path: str, repository_id: int):
        """Mark a file as deleted (soft delete)."""
        with self._get_connection() as conn:
            conn.execute(
                """UPDATE files 
                   SET is_deleted = TRUE, deleted_at = CURRENT_TIMESTAMP
                   WHERE relative_path = ? AND repository_id = ?""",
                (relative_path, repository_id),
            )
            logger.info(f"Marked file as deleted: {relative_path}")

    def remove_file(self, relative_path: str, repository_id: int):
        """Remove file and all associated data (hard delete)."""
        with self._get_connection() as conn:
            # Get file ID first
            cursor = conn.execute(
                "SELECT id FROM files WHERE relative_path = ? AND repository_id = ?",
                (relative_path, repository_id),
            )
            row = cursor.fetchone()
            if not row:
                logger.warning(f"File not found for removal: {relative_path}")
                return

            file_id = row[0]

            # Delete all associated data (cascade should handle most)
            conn.execute("DELETE FROM symbol_references WHERE file_id = ?", (file_id,))
            conn.execute("DELETE FROM imports WHERE file_id = ?", (file_id,))
            conn.execute("DELETE FROM embeddings WHERE file_id = ?", (file_id,))
            conn.execute("DELETE FROM fts_code WHERE file_id = ?", (file_id,))
            conn.execute("DELETE FROM symbols WHERE file_id = ?", (file_id,))
            conn.execute("DELETE FROM files WHERE id = ?", (file_id,))

            logger.info(f"Removed file and all associated data: {relative_path}")

    def move_file(self, old_path: str, new_path: str, repository_id: int, content_hash: str):
        """Record a file move operation."""
        with self._get_connection() as conn:
            # Update the file path
            conn.execute(
                """UPDATE files 
                   SET relative_path = ?, path = ?
                   WHERE relative_path = ? AND repository_id = ?""",
                (new_path, new_path, old_path, repository_id),
            )

            # Record the move
            conn.execute(
                """INSERT INTO file_moves 
                   (repository_id, old_relative_path, new_relative_path, content_hash, move_type)
                   VALUES (?, ?, ?, ?, ?)""",
                (repository_id, old_path, new_path, content_hash, "rename"),
            )

            logger.info(f"Recorded file move: {old_path} -> {new_path}")

    def cleanup_deleted_files(self, days_old: int = 30):
        """Clean up files marked as deleted for more than specified days."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """SELECT COUNT(*) FROM files 
                   WHERE is_deleted = TRUE 
                   AND deleted_at < datetime('now', '-' || ? || ' days')""",
                (days_old,),
            )
            count = cursor.fetchone()[0]

            if count > 0:
                # Get file IDs for cleanup
                cursor = conn.execute(
                    """SELECT id, relative_path FROM files 
                       WHERE is_deleted = TRUE 
                       AND deleted_at < datetime('now', '-' || ? || ' days')""",
                    (days_old,),
                )

                for row in cursor:
                    file_id, path = row
                    # Use remove_file for thorough cleanup
                    self.remove_file(path, repository_id=None)

                logger.info(f"Cleaned up {count} deleted files older than {days_old} days")
