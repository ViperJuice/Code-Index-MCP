"""
Comprehensive tests for SQLite persistence layer.

Tests cover:
- Database initialization and schema creation
- Repository operations
- File operations
- Symbol storage and retrieval
- Import tracking
- Reference tracking
- Search functionality (FTS and fuzzy)
- Cache operations
- Transaction handling
- Performance benchmarks
"""

import json
import sqlite3
import time
from datetime import datetime, timedelta

import pytest

from mcp_server.storage.sqlite_store import SQLiteStore


class TestDatabaseInitialization:
    """Test database initialization and schema creation."""

    def test_init_creates_database(self, temp_db_path):
        """Test that initialization creates database file."""
        store = SQLiteStore(str(temp_db_path))

        assert temp_db_path.exists()

        # Verify schema version
        with store._get_connection() as conn:
            cursor = conn.execute("SELECT version FROM schema_version")
            version = cursor.fetchone()
            assert version["version"] == 2

    def test_init_existing_database(self, temp_db_path):
        """Test initialization with existing database."""
        # Create first instance
        store1 = SQLiteStore(str(temp_db_path))

        # Create some data
        repo_id = store1.create_repository("/test", "test-repo")

        # Create second instance
        store2 = SQLiteStore(str(temp_db_path))

        # Should be able to read existing data
        repo = store2.get_repository("/test")
        assert repo is not None
        assert repo["name"] == "test-repo"

    def test_schema_tables_created(self, sqlite_store):
        """Test that all required tables are created."""
        expected_tables = [
            "schema_version",
            "repositories",
            "files",
            "symbols",
            "imports",
            "symbol_references",
            "symbol_trigrams",
            "embeddings",
            "query_cache",
            "parse_cache",
            "migrations",
        ]

        with sqlite_store._get_connection() as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row["name"] for row in cursor]

            for table in expected_tables:
                assert table in tables

    def test_fts_tables_created(self, sqlite_store):
        """Test that FTS5 virtual tables are created."""
        with sqlite_store._get_connection() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'fts_%'"
            )
            fts_tables = [row["name"] for row in cursor]

            assert "fts_symbols" in fts_tables
            assert "fts_code" in fts_tables

    def test_indexes_created(self, sqlite_store):
        """Test that all indexes are created."""
        expected_indexes = [
            "idx_files_language",
            "idx_files_hash",
            "idx_files_content_hash",
            "idx_files_deleted",
            "idx_files_relative_path",
            "idx_symbols_name",
            "idx_symbols_kind",
            "idx_symbols_file",
            "idx_imports_file",
            "idx_imports_path",
            "idx_references_symbol",
            "idx_references_file",
            "idx_trigrams",
            "idx_embeddings_file",
            "idx_embeddings_symbol",
            "idx_cache_expires",
        ]

        with sqlite_store._get_connection() as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='index'")
            indexes = [row["name"] for row in cursor]

            for index in expected_indexes:
                assert index in indexes

    def test_foreign_keys_enabled(self, sqlite_store):
        """Test that foreign keys are enabled."""
        with sqlite_store._get_connection() as conn:
            cursor = conn.execute("PRAGMA foreign_keys")
            assert cursor.fetchone()[0] == 1


class TestRepositoryOperations:
    """Test repository CRUD operations."""

    def test_create_repository(self, sqlite_store):
        """Test creating a new repository."""
        repo_id = sqlite_store.create_repository(
            "/home/user/project",
            "my-project",
            {"vcs": "git", "remote": "github.com/user/project"},
        )

        assert isinstance(repo_id, int)
        assert repo_id > 0

        # Verify data
        repo = sqlite_store.get_repository("/home/user/project")
        assert repo["name"] == "my-project"
        assert json.loads(repo["metadata"])["vcs"] == "git"

    def test_create_repository_duplicate(self, sqlite_store):
        """Test creating repository with duplicate path (should update)."""
        # Create first
        repo_id1 = sqlite_store.create_repository("/test/path", "repo1")

        # Create with same path
        repo_id2 = sqlite_store.create_repository("/test/path", "repo2", {"updated": True})

        assert repo_id1 == repo_id2  # Same ID

        # Verify update
        repo = sqlite_store.get_repository("/test/path")
        assert repo["name"] == "repo2"
        assert json.loads(repo["metadata"])["updated"] is True

    def test_get_repository_not_found(self, sqlite_store):
        """Test getting non-existent repository."""
        repo = sqlite_store.get_repository("/nonexistent")
        assert repo is None

    def test_repository_timestamps(self, sqlite_store):
        """Test repository timestamp handling."""
        # Create repository
        repo_id = sqlite_store.create_repository("/test", "test")
        repo1 = sqlite_store.get_repository("/test")

        time.sleep(0.1)  # Ensure time difference

        # Update repository
        sqlite_store.create_repository("/test", "test-updated")
        repo2 = sqlite_store.get_repository("/test")

        # updated_at should be different
        assert repo2["updated_at"] > repo1["created_at"]


class TestFileOperations:
    """Test file storage and retrieval."""

    def test_store_file(self, sqlite_store):
        """Test storing file information."""
        repo_id = sqlite_store.create_repository("/repo", "test-repo")

        file_id = sqlite_store.store_file(
            repository_id=repo_id,
            file_path="/repo/src/main.py",
            language="python",
            size=1024,
            hash="abc123def456",
            metadata={"encoding": "utf-8"},
        )

        assert isinstance(file_id, int)
        assert file_id > 0

        # Verify data
        file_info = sqlite_store.get_file("/repo/src/main.py")
        assert file_info["relative_path"] == "src/main.py"
        assert file_info["language"] == "python"
        assert file_info["size"] == 1024
        assert file_info["hash"] == "abc123def456"

    def test_store_file_update(self, sqlite_store):
        """Test updating existing file."""
        repo_id = sqlite_store.create_repository("/repo", "test-repo")

        # Store initial version
        file_id1 = sqlite_store.store_file(
            repo_id, "/repo/file.py", "file.py", size=100, hash="hash1"
        )

        # Update file
        file_id2 = sqlite_store.store_file(
            repo_id, "/repo/file.py", "file.py", size=200, hash="hash2"
        )

        assert file_id1 == file_id2  # Same file ID

        # Verify update
        file_info = sqlite_store.get_file("/repo/file.py")
        assert file_info["size"] == 200
        assert file_info["hash"] == "hash2"

    def test_get_file_with_repository(self, sqlite_store):
        """Test getting file with specific repository."""
        repo1_id = sqlite_store.create_repository("/repo1", "repo1")
        repo2_id = sqlite_store.create_repository("/repo2", "repo2")

        # Same relative path in different repos
        sqlite_store.store_file(repo1_id, "/repo1/file.py", "file.py")
        sqlite_store.store_file(repo2_id, "/repo2/file.py", "file.py")

        # Get specific file
        file_info = sqlite_store.get_file("/repo1/file.py", repo1_id)
        assert file_info is not None
        assert file_info["repository_id"] == repo1_id

    def test_file_metadata_json(self, sqlite_store):
        """Test JSON metadata storage."""
        repo_id = sqlite_store.create_repository("/repo", "test")

        metadata = {
            "imports": ["os", "sys"],
            "exports": ["main", "helper"],
            "complexity": 5.2,
        }

        file_id = sqlite_store.store_file(repo_id, "/repo/file.py", "file.py", metadata=metadata)

        file_info = sqlite_store.get_file("/repo/file.py")
        stored_metadata = json.loads(file_info["metadata"])
        assert stored_metadata == metadata


class TestSymbolOperations:
    """Test symbol storage and retrieval."""

    def test_store_symbol(self, sqlite_store):
        """Test storing symbol definition."""
        repo_id = sqlite_store.create_repository("/repo", "test")
        file_id = sqlite_store.store_file(repo_id, "/repo/file.py", "file.py")

        symbol_id = sqlite_store.store_symbol(
            file_id,
            "calculate_total",
            "function",
            line_start=10,
            line_end=25,
            column_start=0,
            column_end=50,
            signature="def calculate_total(items: List[Item]) -> float",
            documentation="Calculate total price of items",
            metadata={"async": False, "decorator": ["cache"]},
        )

        assert isinstance(symbol_id, int)
        assert symbol_id > 0

        # Verify symbol stored
        symbols = sqlite_store.get_symbol("calculate_total")
        assert len(symbols) == 1
        assert symbols[0]["kind"] == "function"
        assert symbols[0]["line_start"] == 10

    def test_store_symbol_creates_trigrams(self, sqlite_store):
        """Test that storing symbol creates trigrams for fuzzy search."""
        repo_id = sqlite_store.create_repository("/repo", "test")
        file_id = sqlite_store.store_file(repo_id, "/repo/file.py", "file.py")

        symbol_id = sqlite_store.store_symbol(file_id, "TestClass", "class", 1, 100)

        # Check trigrams created
        with sqlite_store._get_connection() as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM symbol_trigrams WHERE symbol_id = ?", (symbol_id,)
            )
            count = cursor.fetchone()[0]

            # "TestClass" with padding should generate multiple trigrams
            assert count > 5

    def test_get_symbol_by_kind(self, sqlite_store):
        """Test getting symbols filtered by kind."""
        repo_id = sqlite_store.create_repository("/repo", "test")
        file_id = sqlite_store.store_file(repo_id, "/repo/file.py", "file.py")

        # Store different kinds
        sqlite_store.store_symbol(file_id, "MyClass", "class", 1, 50)
        sqlite_store.store_symbol(file_id, "my_func", "function", 60, 70)
        sqlite_store.store_symbol(file_id, "MY_CONST", "constant", 80, 80)

        # Get only functions
        functions = sqlite_store.get_symbol("my_func", kind="function")
        assert len(functions) == 1
        assert functions[0]["name"] == "my_func"

        # Get all with name
        all_my_func = sqlite_store.get_symbol("my_func")
        assert len(all_my_func) == 1

    def test_symbol_fts_triggers(self, sqlite_store):
        """Test FTS triggers maintain sync with symbols table."""
        repo_id = sqlite_store.create_repository("/repo", "test")
        file_id = sqlite_store.store_file(repo_id, "/repo/file.py", "file.py")

        # Store symbol
        symbol_id = sqlite_store.store_symbol(
            file_id,
            "search_me",
            "function",
            1,
            10,
            documentation="This function can be searched",
        )

        # Verify FTS entry created
        results = sqlite_store.search_symbols_fts("searched")
        assert len(results) == 1
        assert results[0]["name"] == "search_me"


class TestReferenceOperations:
    """Test symbol reference tracking."""

    def test_store_reference(self, sqlite_store):
        """Test storing symbol reference."""
        repo_id = sqlite_store.create_repository("/repo", "test")
        def_file_id = sqlite_store.store_file(repo_id, "/repo/defs.py", "defs.py")
        use_file_id = sqlite_store.store_file(repo_id, "/repo/uses.py", "uses.py")

        symbol_id = sqlite_store.store_symbol(def_file_id, "helper", "function", 1, 5)

        ref_id = sqlite_store.store_reference(
            symbol_id,
            use_file_id,
            line_number=20,
            column_number=15,
            reference_kind="call",
            metadata={"in_function": "main"},
        )

        assert isinstance(ref_id, int)
        assert ref_id > 0

    def test_get_references(self, sqlite_store):
        """Test getting all references to a symbol."""
        repo_id = sqlite_store.create_repository("/repo", "test")
        def_file_id = sqlite_store.store_file(repo_id, "/repo/module.py", "module.py")

        # Create files that use the symbol
        use1_id = sqlite_store.store_file(repo_id, "/repo/use1.py", "use1.py")
        use2_id = sqlite_store.store_file(repo_id, "/repo/use2.py", "use2.py")

        symbol_id = sqlite_store.store_symbol(def_file_id, "SharedClass", "class", 10, 50)

        # Store references
        sqlite_store.store_reference(symbol_id, use1_id, 15, 10, "import")
        sqlite_store.store_reference(symbol_id, use1_id, 25, 20, "instantiation")
        sqlite_store.store_reference(symbol_id, use2_id, 30, 5, "inheritance")

        # Get all references
        refs = sqlite_store.get_references(symbol_id)

        assert len(refs) == 3
        assert {r["reference_kind"] for r in refs} == {
            "import",
            "instantiation",
            "inheritance",
        }
        assert {r["file_path"] for r in refs} == {"/repo/use1.py", "/repo/use2.py"}


class TestSearchOperations:
    """Test search functionality."""

    def test_fuzzy_search_basic(self, sqlite_store):
        """Test basic fuzzy search with trigrams."""
        repo_id = sqlite_store.create_repository("/repo", "test")
        file_id = sqlite_store.store_file(repo_id, "/repo/file.py", "file.py")

        # Store symbols with similar names
        sqlite_store.store_symbol(file_id, "calculate_total", "function", 1, 10)
        sqlite_store.store_symbol(file_id, "calc_subtotal", "function", 20, 30)
        sqlite_store.store_symbol(file_id, "get_calculation", "function", 40, 50)
        sqlite_store.store_symbol(file_id, "unrelated_func", "function", 60, 70)

        # Search for "calc"
        results = sqlite_store.search_symbols_fuzzy("calc", limit=10)

        assert len(results) >= 3
        # Results should include symbols containing "calc"
        result_names = {r["name"] for r in results}
        assert "calculate_total" in result_names
        assert "calc_subtotal" in result_names

    def test_fuzzy_search_scoring(self, sqlite_store):
        """Test fuzzy search result scoring."""
        repo_id = sqlite_store.create_repository("/repo", "test")
        file_id = sqlite_store.store_file(repo_id, "/repo/file.py", "file.py")

        # Store symbols
        sqlite_store.store_symbol(file_id, "exact_match", "function", 1, 10)
        sqlite_store.store_symbol(file_id, "partial_exact", "function", 20, 30)
        sqlite_store.store_symbol(file_id, "somewhat_related", "function", 40, 50)

        # Search for "exact"
        results = sqlite_store.search_symbols_fuzzy("exact", limit=10)

        # Should be ordered by relevance (score)
        assert len(results) >= 2
        assert results[0]["score"] > results[1]["score"]

    def test_fuzzy_search_empty_query(self, sqlite_store):
        """Test fuzzy search with empty query."""
        results = sqlite_store.search_symbols_fuzzy("", limit=10)
        assert results == []

    def test_fts_search_basic(self, sqlite_store):
        """Test full-text search."""
        repo_id = sqlite_store.create_repository("/repo", "test")
        file_id = sqlite_store.store_file(repo_id, "/repo/file.py", "file.py")

        # Store symbols with documentation
        sqlite_store.store_symbol(
            file_id,
            "process_data",
            "function",
            1,
            10,
            documentation="Process incoming data from the API",
        )
        sqlite_store.store_symbol(
            file_id,
            "DataProcessor",
            "class",
            20,
            100,
            documentation="Main class for data processing operations",
        )
        sqlite_store.store_symbol(
            file_id,
            "validate_input",
            "function",
            110,
            120,
            documentation="Validate user input before processing",
        )

        # Search documentation
        results = sqlite_store.search_symbols_fts("processing")

        assert len(results) == 2
        result_names = {r["name"] for r in results}
        assert "DataProcessor" in result_names

    def test_fts_search_name_and_docs(self, sqlite_store):
        """Test FTS searches both name and documentation."""
        repo_id = sqlite_store.create_repository("/repo", "test")
        file_id = sqlite_store.store_file(repo_id, "/repo/file.py", "file.py")

        sqlite_store.store_symbol(
            file_id,
            "helper",
            "function",
            1,
            10,
            documentation="This is a utility function",
        )

        # Search by name
        results1 = sqlite_store.search_symbols_fts("helper")
        assert len(results1) == 1

        # Search by documentation
        results2 = sqlite_store.search_symbols_fts("utility")
        assert len(results2) == 1
        assert results2[0]["name"] == "helper"

    def test_search_code_fts(self, sqlite_store):
        """Test full-text search in code content."""
        # Note: This requires actual code content to be stored in fts_code
        # which is typically done by the indexing process
        results = sqlite_store.search_code_fts("import os")

        # Should return empty for now as we haven't populated fts_code
        assert isinstance(results, list)


class TestFuzzyIndexPersistence:
    """Test fuzzy index persistence integration."""

    def test_persist_fuzzy_index(self, sqlite_store):
        """Test persisting fuzzy index data."""
        repo_id = sqlite_store.create_repository("/repo", "test")
        file_id = sqlite_store.store_file(repo_id, "/repo/file.py", "file.py")

        # Create some symbols first
        symbol1_id = sqlite_store.store_symbol(file_id, "test_one", "function", 1, 10)
        symbol2_id = sqlite_store.store_symbol(file_id, "test_two", "function", 20, 30)

        # Simulate fuzzy index data
        index_data = {
            "tes": [
                ("test_one", {"symbol_id": symbol1_id, "file_id": file_id}),
                ("test_two", {"symbol_id": symbol2_id, "file_id": file_id}),
            ],
            "est": [
                ("test_one", {"symbol_id": symbol1_id, "file_id": file_id}),
            ],
        }

        sqlite_store.persist_fuzzy_index(index_data)

        # Verify trigrams stored
        with sqlite_store._get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM symbol_trigrams")
            # Should have some trigrams (exact count depends on implementation)
            assert cursor.fetchone()[0] > 0

    def test_load_fuzzy_index(self, sqlite_store):
        """Test loading fuzzy index data."""
        repo_id = sqlite_store.create_repository("/repo", "test")
        file_id = sqlite_store.store_file(repo_id, "/repo/file.py", "file.py")

        # Store symbol with trigrams
        symbol_id = sqlite_store.store_symbol(file_id, "example_func", "function", 1, 10)

        # Load fuzzy index
        index_data = sqlite_store.load_fuzzy_index()

        # Should contain trigrams for "example_func"
        assert len(index_data) > 0

        # Check that some expected trigrams exist
        has_example_trigram = any("exa" in trigram for trigram in index_data.keys())
        assert has_example_trigram


class TestCacheOperations:
    """Test caching functionality."""

    def test_clear_expired_cache(self, sqlite_store):
        """Test clearing expired cache entries."""
        with sqlite_store._get_connection() as conn:
            # Insert expired entry
            past = datetime.now() - timedelta(hours=1)
            conn.execute(
                """INSERT INTO query_cache 
                   (query_hash, query_text, result, expires_at)
                   VALUES (?, ?, ?, ?)""",
                ("hash1", "old query", '{"results": []}', past),
            )

            # Insert valid entry
            future = datetime.now() + timedelta(hours=1)
            conn.execute(
                """INSERT INTO query_cache 
                   (query_hash, query_text, result, expires_at)
                   VALUES (?, ?, ?, ?)""",
                ("hash2", "new query", '{"results": []}', future),
            )

        # Clear expired
        sqlite_store.clear_cache()

        # Check results
        with sqlite_store._get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM query_cache")
            count = cursor.fetchone()[0]
            assert count == 1  # Only future entry remains

            cursor = conn.execute("SELECT query_hash FROM query_cache")
            remaining = cursor.fetchone()
            assert remaining["query_hash"] == "hash2"


class TestStatistics:
    """Test statistics gathering."""

    def test_get_statistics_empty(self, sqlite_store):
        """Test statistics on empty database."""
        stats = sqlite_store.get_statistics()

        assert stats["repositories"] == 0
        assert stats["files"] == 0
        assert stats["symbols"] == 0
        assert stats["symbol_references"] == 0
        assert stats["imports"] == 0

    def test_get_statistics_populated(self, populated_sqlite_store):
        """Test statistics on populated database."""
        stats = populated_sqlite_store.get_statistics()

        assert stats["repositories"] == 1
        assert stats["files"] == 2
        assert stats["symbols"] == 3
        assert stats["symbol_references"] == 0  # No references added in fixture
        assert stats["imports"] == 0  # No imports added in fixture


class TestTransactionHandling:
    """Test transaction and error handling."""

    def test_rollback_on_error(self, sqlite_store):
        """Test that transactions rollback on error."""
        repo_id = sqlite_store.create_repository("/repo", "test")

        with pytest.raises(Exception):
            with sqlite_store._get_connection() as conn:
                # This should succeed
                conn.execute(
                    "INSERT INTO files (repository_id, path, relative_path) VALUES (?, ?, ?)",
                    (repo_id, "/test.py", "test.py"),
                )

                # This should fail (invalid repository_id)
                conn.execute(
                    "INSERT INTO files (repository_id, path, relative_path) VALUES (?, ?, ?)",
                    (99999, "/fail.py", "fail.py"),
                )

        # First insert should have been rolled back
        assert sqlite_store.get_file("/test.py") is None

    def test_foreign_key_constraints(self, sqlite_store):
        """Test foreign key constraints are enforced."""
        with pytest.raises(sqlite3.IntegrityError):
            with sqlite_store._get_connection() as conn:
                # Try to insert file with non-existent repository
                conn.execute(
                    """INSERT INTO files 
                       (repository_id, path, relative_path)
                       VALUES (?, ?, ?)""",
                    (99999, "/test.py", "test.py"),
                )


class TestConcurrency:
    """Test concurrent database operations."""

    def test_concurrent_writes(self, sqlite_store):
        """Test concurrent write operations."""
        import concurrent.futures

        repo_id = sqlite_store.create_repository("/repo", "test")

        def write_file(i):
            file_id = sqlite_store.store_file(
                repo_id, f"/repo/file{i}.py", f"file{i}.py", size=i * 100
            )
            return file_id

        # Perform concurrent writes
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(write_file, i) for i in range(20)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # All writes should succeed
        assert len(results) == 20
        assert all(isinstance(r, int) for r in results)

        # Verify all files stored
        stats = sqlite_store.get_statistics()
        assert stats["files"] == 20

    def test_read_write_concurrency(self, populated_sqlite_store):
        """Test concurrent reads and writes."""
        import concurrent.futures

        def read_symbols():
            return populated_sqlite_store.get_symbol("main")

        def write_symbol(i):
            repo_id = 1  # From populated store
            file_id = 1
            return populated_sqlite_store.store_symbol(
                file_id, f"func_{i}", "function", i * 10, i * 10 + 5
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            # Mix reads and writes
            futures = []
            for i in range(10):
                futures.append(executor.submit(read_symbols))
                futures.append(executor.submit(write_symbol, i))

            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # All operations should complete
        assert len(results) == 20


class TestSQLiteStoreHealthCheck:
    """Tests for SQLiteStore.health_check() method."""

    def test_health_check_fresh_database(self, tmp_path):
        """Verify health check returns healthy for fresh database."""
        db_path = tmp_path / "test.db"
        store = SQLiteStore(str(db_path))

        health = store.health_check()

        assert health["status"] == "healthy"
        assert health["fts5"] is True
        assert health["wal"] is True
        assert health["version"] >= 1
        assert health["error"] is None
        # Check all required tables exist
        assert health["tables"]["file_moves"] is True
        assert health["tables"]["files"] is True
        assert health["tables"]["symbols"] is True
        assert health["tables"]["repositories"] is True
        assert health["tables"]["schema_version"] is True

    def test_health_check_missing_tables(self, tmp_path):
        """Verify health check detects missing tables."""
        # Create database with missing tables
        db_path = tmp_path / "incomplete.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE schema_version (version INTEGER PRIMARY KEY)")
        conn.execute("INSERT INTO schema_version VALUES (1)")
        conn.close()

        store = SQLiteStore(str(db_path))
        health = store.health_check()

        assert health["status"] in ["degraded", "unhealthy"]
        assert health["error"] is not None
        assert "missing" in health["error"].lower()

    def test_health_check_file_moves_table_exists(self, tmp_path):
        """Verify file_moves table is created in fresh database."""
        db_path = tmp_path / "test.db"
        store = SQLiteStore(str(db_path))

        health = store.health_check()

        assert health["tables"]["file_moves"] is True

    def test_check_column_exists(self, tmp_path):
        """Test _check_column_exists helper."""
        db_path = tmp_path / "test.db"
        store = SQLiteStore(str(db_path))

        # Use a connection to test
        conn = sqlite3.connect(str(db_path))

        # Should return True for existing columns
        assert store._check_column_exists(conn, "files", "path") is True
        assert store._check_column_exists(conn, "files", "language") is True
        assert store._check_column_exists(conn, "files", "relative_path") is True

        # Should return False for non-existing columns
        assert store._check_column_exists(conn, "files", "nonexistent_column") is False

        conn.close()

    def test_health_check_all_core_tables(self, tmp_path):
        """Verify all core tables are checked by health_check."""
        db_path = tmp_path / "test.db"
        store = SQLiteStore(str(db_path))

        health = store.health_check()

        # Verify all core tables are present in the check
        core_tables = [
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

        for table in core_tables:
            assert table in health["tables"], f"Table {table} not checked in health_check"
            assert health["tables"][table] is True, f"Table {table} should exist in fresh database"

    def test_health_check_fts5_support(self, tmp_path):
        """Verify health check reports FTS5 support."""
        db_path = tmp_path / "test.db"
        store = SQLiteStore(str(db_path))

        health = store.health_check()

        # FTS5 should be available in modern SQLite
        assert health["fts5"] is True

    def test_health_check_wal_mode(self, tmp_path):
        """Verify health check reports WAL mode."""
        db_path = tmp_path / "test.db"
        store = SQLiteStore(str(db_path))

        health = store.health_check()

        # WAL mode should be enabled by _init_database
        assert health["wal"] is True

    def test_health_check_schema_version(self, tmp_path):
        """Verify health check returns schema version."""
        db_path = tmp_path / "test.db"
        store = SQLiteStore(str(db_path))

        health = store.health_check()

        # Fresh database should have version 1
        assert health["version"] == 2


class TestPerformance:
    """Performance benchmarks for database operations."""

    @pytest.mark.benchmark
    def test_symbol_insertion_performance(self, sqlite_store, benchmark_results):
        """Benchmark symbol insertion performance."""
        repo_id = sqlite_store.create_repository("/repo", "test")
        file_id = sqlite_store.store_file(repo_id, "/repo/file.py", "file.py")

        with measure_time("sqlite_symbol_insert", benchmark_results):
            for i in range(100):
                sqlite_store.store_symbol(
                    file_id,
                    f"symbol_{i}",
                    "function",
                    i * 10,
                    i * 10 + 5,
                    documentation=f"Function {i} documentation",
                )

    @pytest.mark.benchmark
    def test_fuzzy_search_performance(self, populated_sqlite_store, benchmark_results):
        """Benchmark fuzzy search performance."""
        # Add more symbols for realistic benchmark
        file_id = 1  # From populated store
        for i in range(50):
            populated_sqlite_store.store_symbol(
                file_id, f"search_func_{i}", "function", i * 10, i * 10 + 5
            )

        with measure_time("sqlite_fuzzy_search", benchmark_results):
            for _ in range(50):
                results = populated_sqlite_store.search_symbols_fuzzy("func", limit=20)
                assert len(results) > 0

    @pytest.mark.benchmark
    def test_fts_search_performance(self, populated_sqlite_store, benchmark_results):
        """Benchmark FTS search performance."""
        # Add symbols with documentation
        file_id = 1
        for i in range(50):
            populated_sqlite_store.store_symbol(
                file_id,
                f"documented_{i}",
                "function",
                i * 10,
                i * 10 + 5,
                documentation=f"This function processes data type {i}",
            )

        with measure_time("sqlite_fts_search", benchmark_results):
            for _ in range(50):
                results = populated_sqlite_store.search_symbols_fts("process")
                assert isinstance(results, list)
