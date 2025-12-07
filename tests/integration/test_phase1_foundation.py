"""Integration tests for Phase 1 Foundation work."""

import sqlite3
import time
from pathlib import Path

import pytest

from mcp_server.storage.sqlite_store import SQLiteStore


class TestPhase1Foundation:
    """Integration tests for Phase 1 Foundation work."""

    def test_sqlite_fresh_database_has_all_tables(self, tmp_path):
        """Verify fresh database creates all required tables."""
        db_path = tmp_path / "test.db"
        store = SQLiteStore(str(db_path))

        health = store.health_check()

        assert health["status"] == "healthy"
        assert health["tables"]["file_moves"] == True
        assert health["tables"]["files"] == True
        assert health["tables"]["symbols"] == True
        assert health["fts5"] == True
        assert health["wal"] == True

    def test_bm25_fallback_multiple_schemas(self, tmp_path):
        """Verify BM25 works with different table schemas."""
        # Test with bm25_content table
        db1 = tmp_path / "bm25.db"
        conn = sqlite3.connect(str(db1))
        conn.execute(
            """
            CREATE VIRTUAL TABLE bm25_content USING fts5(
                filepath, content, language
            )
        """
        )
        conn.execute(
            "INSERT INTO bm25_content VALUES (?, ?, ?)", ("/test.py", "def hello(): pass", "python")
        )
        conn.commit()
        conn.close()

        store = SQLiteStore(str(db1))
        results = store.search_bm25("hello", table="bm25_content")

        assert len(results) >= 1

    def test_sqlite_store_initialization_is_fast(self, tmp_path):
        """Verify SQLiteStore initializes in under 2 seconds."""
        db_path = tmp_path / "test.db"

        start = time.time()
        store = SQLiteStore(str(db_path))
        elapsed = time.time() - start

        assert elapsed < 2.0, f"Initialization took {elapsed:.2f}s, should be under 2s"

    def test_file_moves_table_structure(self, tmp_path):
        """Verify file_moves table has correct structure."""
        db_path = tmp_path / "test.db"
        store = SQLiteStore(str(db_path))

        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute("PRAGMA table_info(file_moves)")
        columns = {row[1] for row in cursor.fetchall()}
        conn.close()

        expected_columns = {
            "id",
            "repository_id",
            "old_relative_path",
            "new_relative_path",
            "content_hash",
            "moved_at",
            "move_type",
        }
        assert expected_columns.issubset(columns)

    def test_file_moves_table_indexes(self, tmp_path):
        """Verify file_moves table has proper indexes."""
        db_path = tmp_path / "test.db"
        store = SQLiteStore(str(db_path))

        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='file_moves'"
        )
        indexes = {row[0] for row in cursor.fetchall()}
        conn.close()

        expected_indexes = {
            "idx_moves_content_hash",
            "idx_moves_timestamp",
            "idx_moves_old_path",
            "idx_moves_new_path",
        }
        assert expected_indexes.issubset(indexes)

    def test_health_check_comprehensive(self, tmp_path):
        """Comprehensive health check validation."""
        db_path = tmp_path / "test.db"
        store = SQLiteStore(str(db_path))

        health = store.health_check()

        # Verify structure
        assert "status" in health
        assert "tables" in health
        assert "fts5" in health
        assert "wal" in health
        assert "version" in health
        assert "error" in health

        # Verify healthy status
        assert health["status"] == "healthy"
        assert health["error"] is None

        # Verify version
        assert isinstance(health["version"], int)
        assert health["version"] >= 1

    def test_bm25_search_with_modern_schema(self, tmp_path):
        """Test BM25 search with modern fts_code schema."""
        db_path = tmp_path / "modern.db"
        store = SQLiteStore(str(db_path))

        # Create repository and file
        repo_id = store.create_repository("/test/repo", "test-repo")
        file_id = store.store_file(repo_id, "/test/repo/example.py", language="python", size=100)

        # Insert content into fts_code
        with store._get_connection() as conn:
            conn.execute(
                "INSERT INTO fts_code (content, file_id) VALUES (?, ?)",
                ("def example_function(): pass", file_id),
            )

        # Search should work
        results = store.search_bm25("example_function", table="fts_code")

        # Should find the content
        assert len(results) >= 1

    def test_concurrent_health_checks(self, tmp_path):
        """Verify health checks can be performed concurrently."""
        import concurrent.futures

        db_path = tmp_path / "test.db"
        store = SQLiteStore(str(db_path))

        def run_health_check():
            health = store.health_check()
            assert health["status"] == "healthy"
            return health

        # Run multiple health checks concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(run_health_check) for _ in range(10)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # All should succeed
        assert len(results) == 10
        assert all(r["status"] == "healthy" for r in results)

    def test_schema_migration_readiness(self, tmp_path):
        """Verify schema is ready for future migrations."""
        db_path = tmp_path / "test.db"
        store = SQLiteStore(str(db_path))

        with store._get_connection() as conn:
            # Check schema_version table exists and has correct structure
            cursor = conn.execute("PRAGMA table_info(schema_version)")
            columns = {row[1]: row[2] for row in cursor.fetchall()}

            assert "version" in columns
            assert "applied_at" in columns
            assert "description" in columns

            # Check migrations table exists
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='migrations'"
            )
            assert cursor.fetchone() is not None

    def test_fresh_database_no_migrations_run(self, tmp_path):
        """Verify fresh database doesn't run migrations."""
        db_path = tmp_path / "test.db"

        # Database doesn't exist yet
        assert not db_path.exists()

        # Create store
        store = SQLiteStore(str(db_path))

        # Check that migrations table is empty (no migrations run on fresh DB)
        with store._get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM migrations")
            count = cursor.fetchone()[0]

            # Fresh database should have no migration records
            assert count == 0

    def test_foreign_key_constraints_enabled(self, tmp_path):
        """Verify foreign key constraints are enabled."""
        db_path = tmp_path / "test.db"
        store = SQLiteStore(str(db_path))

        with store._get_connection() as conn:
            cursor = conn.execute("PRAGMA foreign_keys")
            fk_enabled = cursor.fetchone()[0]

            assert fk_enabled == 1

    def test_file_moves_foreign_key_constraint(self, tmp_path):
        """Verify file_moves table has foreign key to repositories."""
        db_path = tmp_path / "test.db"
        store = SQLiteStore(str(db_path))

        # Try to insert file_move with non-existent repository
        with pytest.raises(sqlite3.IntegrityError):
            with store._get_connection() as conn:
                conn.execute(
                    """INSERT INTO file_moves
                       (repository_id, old_relative_path, new_relative_path, content_hash, move_type)
                       VALUES (?, ?, ?, ?, ?)""",
                    (99999, "old.py", "new.py", "hash123", "rename"),
                )

    def test_bm25_search_empty_database(self, tmp_path):
        """Verify BM25 search handles empty database gracefully."""
        db_path = tmp_path / "empty.db"
        store = SQLiteStore(str(db_path))

        # Search on empty database should return empty results, not error
        results = store.search_bm25("test", table="fts_code")

        assert results == []

    def test_index_config_populated(self, tmp_path):
        """Verify index_config table is populated on initialization."""
        db_path = tmp_path / "test.db"
        store = SQLiteStore(str(db_path))

        with store._get_connection() as conn:
            cursor = conn.execute("SELECT config_key, config_value FROM index_config")
            config = {row[0]: row[1] for row in cursor.fetchall()}

            # Check expected config values
            assert "embedding_model" in config
            assert "model_dimension" in config
            assert "distance_metric" in config
            assert "index_version" in config

            # Verify values
            assert config["embedding_model"] == "voyage-code-3"
            assert config["model_dimension"] == "1024"
            assert config["distance_metric"] == "cosine"
