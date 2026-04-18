"""
Tests for ConnectionPool and its integration with SQLiteStore.

Covers:
- 16 concurrent readers against a pool-backed SQLiteStore (pool size 4)
- close_all() is idempotent
- close_all() closes every connection; post-call acquire raises RuntimeError
- Write path round trip works with a pool-backed store
"""

import concurrent.futures
import queue
import sqlite3
import threading

import pytest

from mcp_server.storage.connection_pool import ConnectionPool
from mcp_server.storage.sqlite_store import SQLiteStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pool(db_path: str, size: int = 4) -> ConnectionPool:
    return ConnectionPool(
        factory=lambda: sqlite3.connect(db_path, check_same_thread=False),
        size=size,
    )


def _make_pool_store(tmp_path, size: int = 4):
    """Return (store, pool) backed by a temp DB with a pool attached."""
    db_path = str(tmp_path / "pool_test.db")
    # Build store without pool first so schema initialises.
    store_init = SQLiteStore(db_path)
    del store_init
    pool = _make_pool(db_path, size=size)
    store = SQLiteStore(db_path, pool=pool)
    return store, pool


# ---------------------------------------------------------------------------
# Concurrency test
# ---------------------------------------------------------------------------

class TestConcurrentReaders:
    def test_16_readers_no_locked_error(self, tmp_path):
        """16 concurrent reader threads against pool-size-4 store — no OperationalError."""
        store, pool = _make_pool_store(tmp_path, size=4)
        repo_id = store.create_repository(str(tmp_path), "test-repo")
        store.store_file(
            repository_id=repo_id,
            relative_path="hello.py",
            language="python",
        )

        errors = []
        results = []

        def read_task():
            try:
                with store._get_connection() as conn:
                    rows = conn.execute("SELECT * FROM files").fetchall()
                    results.append(len(rows))
            except sqlite3.OperationalError as e:
                errors.append(str(e))

        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
            futures = [executor.submit(read_task) for _ in range(16)]
            concurrent.futures.wait(futures)

        assert errors == [], f"OperationalError(s) encountered: {errors}"
        assert len(results) == 16
        assert all(r >= 1 for r in results), "Each reader should see at least 1 file"

        pool.close_all()


# ---------------------------------------------------------------------------
# close_all() behaviour
# ---------------------------------------------------------------------------

class TestCloseAll:
    def test_close_all_idempotent(self, tmp_path):
        """close_all() called twice must not raise."""
        pool = _make_pool(str(tmp_path / "idem.db"))
        pool.close_all()
        pool.close_all()  # second call must be a no-op

    def test_close_all_raises_on_acquire(self, tmp_path):
        """After close_all(), acquire() raises RuntimeError immediately."""
        pool = _make_pool(str(tmp_path / "closed.db"))
        pool.close_all()
        with pytest.raises(RuntimeError):
            with pool.acquire():
                pass


# ---------------------------------------------------------------------------
# Write path round trip
# ---------------------------------------------------------------------------

class TestWritePathWithPool:
    def test_store_file_get_file_round_trip(self, tmp_path):
        """store_file + get_file works correctly with a pool-backed store."""
        store, pool = _make_pool_store(tmp_path)
        repo_id = store.create_repository(str(tmp_path), "write-test-repo")

        file_id = store.store_file(
            repository_id=repo_id,
            relative_path="src/main.py",
            language="python",
        )
        assert isinstance(file_id, int)

        row = store.get_file("src/main.py", repository_id=repo_id)
        assert row is not None
        assert row["language"] == "python"

        pool.close_all()
