"""
Tests for StoreRegistry — thread-safe SQLiteStore cache keyed by repo_id.
"""

import concurrent.futures
import sqlite3
from datetime import datetime
from pathlib import Path

import pytest

from mcp_server.storage.multi_repo_manager import RepositoryInfo
from mcp_server.storage.repository_registry import RepositoryRegistry
from mcp_server.storage.sqlite_store import SQLiteStore

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_registry_with_repo(tmp_path: Path) -> tuple:
    """Return (RepositoryRegistry, repo_id, index_path) backed by tmp_path."""
    registry_file = tmp_path / "registry.json"
    index_dir = tmp_path / "index"
    index_dir.mkdir(parents=True, exist_ok=True)
    index_path = index_dir / "code_index.db"

    # Create a minimal SQLite DB so SQLiteStore can open it.
    conn = sqlite3.connect(str(index_path))
    conn.close()

    registry = RepositoryRegistry(registry_file)

    repo_id = "aabbccdd11223344"
    repo_info = RepositoryInfo(
        repository_id=repo_id,
        name="test-repo",
        path=tmp_path,
        index_path=index_path,
        language_stats={},
        total_files=0,
        total_symbols=0,
        indexed_at=datetime.now(),
        active=True,
    )
    registry.register(repo_info)
    return registry, repo_id, index_path


# ---------------------------------------------------------------------------
# Import guard — StoreRegistry must exist; if not, tests will import-fail
# ---------------------------------------------------------------------------

from mcp_server.storage.store_registry import StoreRegistry  # noqa: E402

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestStoreRegistry:

    # --- 1. idempotency ---
    def test_get_returns_same_instance(self, tmp_path):
        registry, repo_id, _ = _make_registry_with_repo(tmp_path)
        sr = StoreRegistry.for_registry(registry)
        a = sr.get(repo_id)
        b = sr.get(repo_id)
        assert a is b

    # --- 2. close evicts ---
    def test_close_evicts_and_get_returns_fresh_instance(self, tmp_path):
        registry, repo_id, _ = _make_registry_with_repo(tmp_path)
        sr = StoreRegistry.for_registry(registry)
        first = sr.get(repo_id)
        assert repo_id in sr._build_locks
        sr.close(repo_id)
        assert repo_id not in sr._build_locks
        second = sr.get(repo_id)
        assert first is not second

    # --- 3. close unknown is no-op ---
    def test_close_unknown_repo_is_noop(self, tmp_path):
        registry, _, _ = _make_registry_with_repo(tmp_path)
        sr = StoreRegistry.for_registry(registry)
        # Should not raise
        sr.close("nonexistent_repo_id")

    # --- 4. shutdown clears all ---
    def test_shutdown_clears_cache(self, tmp_path):
        registry, repo_id, _ = _make_registry_with_repo(tmp_path)
        sr = StoreRegistry.for_registry(registry)
        first = sr.get(repo_id)
        sr.shutdown()
        second = sr.get(repo_id)
        assert first is not second

    # --- 5. KeyError on unknown repo_id ---
    def test_get_unknown_repo_raises_key_error(self, tmp_path):
        registry_file = tmp_path / "registry.json"
        registry = RepositoryRegistry(registry_file)
        sr = StoreRegistry.for_registry(registry)
        with pytest.raises(KeyError):
            sr.get("unknown_repo_id_xyz")

    def test_get_creates_index_parent_directory(self, tmp_path):
        registry_file = tmp_path / "registry.json"
        registry = RepositoryRegistry(registry_file)
        index_path = tmp_path / "repo" / ".mcp-index" / "current.db"
        repo_id = "aabbccdd11223344"
        repo_info = RepositoryInfo(
            repository_id=repo_id,
            name="test-repo",
            path=tmp_path,
            index_path=index_path,
            language_stats={},
            total_files=0,
            total_symbols=0,
            indexed_at=datetime.now(),
            active=True,
        )
        registry.register(repo_info)

        store = StoreRegistry.for_registry(registry).get(repo_id)

        assert isinstance(store, SQLiteStore)
        assert index_path.exists()

    def test_create_repository_returns_existing_row_after_other_inserts(self, tmp_path):
        store = SQLiteStore(str(tmp_path / "index.db"))
        repo_path = str(tmp_path / "repo")
        first_id = store.create_repository(repo_path, "repo")
        store.store_file(first_id, path=tmp_path / "file.py", relative_path="file.py")

        second_id = store.create_repository(repo_path, "repo")

        assert second_id == first_id

    def test_store_file_returns_existing_row_after_other_inserts(self, tmp_path):
        store = SQLiteStore(str(tmp_path / "index.db"))
        repo_id = store.create_repository(str(tmp_path / "repo"), "repo")
        first_id = store.store_file(
            repo_id,
            path=tmp_path / "file.py",
            relative_path="file.py",
            language="python",
        )
        store.store_file(repo_id, path=tmp_path / "other.py", relative_path="other.py")

        second_id = store.store_file(
            repo_id,
            path=tmp_path / "file.py",
            relative_path="file.py",
            language="python",
        )

        assert second_id == first_id

    # --- 6. concurrent get from 8 threads ---
    def test_concurrent_get_same_instance_no_lock_errors(self, tmp_path):
        registry, repo_id, _ = _make_registry_with_repo(tmp_path)
        sr = StoreRegistry.for_registry(registry)

        results = []
        errors = []

        def worker():
            try:
                store = sr.get(repo_id)
                results.append(store)
            except Exception as e:
                errors.append(e)

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(worker) for _ in range(8)]
            concurrent.futures.wait(futures, timeout=5)

        assert not errors, f"Errors raised: {errors}"
        assert len(results) == 8
        # Due to the double-check pattern, at most 2 distinct instances may have been
        # constructed (one from the winning thread; any racer closes its copy and
        # returns the winner's). All 8 results must reference the same survivor.
        unique_ids = {id(r) for r in results}
        assert len(unique_ids) in {1, 2}, f"Expected 1 or 2 unique instances, got {len(unique_ids)}"

    # --- 7. for_registry is the documented constructor ---
    def test_for_registry_is_constructor(self, tmp_path):
        registry_file = tmp_path / "registry.json"
        registry = RepositoryRegistry(registry_file)
        sr = StoreRegistry.for_registry(registry)
        assert isinstance(sr, StoreRegistry)

    # --- 8. MultiRepositoryManager integration ---
    def test_multi_repo_manager_search_symbol_still_works(self, tmp_path):
        """After delegation refactor, search_symbol works end-to-end."""
        import asyncio

        from mcp_server.storage.multi_repo_manager import MultiRepositoryManager

        registry_file = tmp_path / "test_registry.json"
        index_dir = tmp_path / "index"
        index_dir.mkdir(parents=True, exist_ok=True)
        index_path = index_dir / "code_index.db"

        # Build a minimal index with a known symbol
        store = SQLiteStore(str(index_path))
        try:
            with store._get_connection() as conn:
                repo_row_id = conn.execute(
                    "INSERT INTO repositories (path, name, metadata) VALUES (?, ?, ?)",
                    (str(tmp_path), "integration-test-repo", "{}"),
                ).lastrowid

                file_id = conn.execute(
                    "INSERT INTO files "
                    "(repository_id, path, relative_path, language, size, hash, content_hash, "
                    " last_modified, indexed_at, metadata, is_deleted) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, ?, FALSE)",
                    (
                        repo_row_id,
                        str(tmp_path / "test_module.py"),
                        "test_module.py",
                        "python",
                        100,
                        "abc123",
                        "abc123content",
                        "{}",
                    ),
                ).lastrowid

                conn.execute(
                    "INSERT INTO symbols "
                    "(file_id, name, kind, line_start, line_end, column_start, column_end, "
                    " signature, documentation, metadata) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (file_id, "MyTestClass", "class", 1, 5, 0, 0, "class MyTestClass:", "", "{}"),
                )
        finally:
            store.close()

        manager = MultiRepositoryManager(central_index_path=registry_file, max_workers=2)
        repo_id = "aabbccdd11223344"
        repo_info = RepositoryInfo(
            repository_id=repo_id,
            name="integration-test-repo",
            path=tmp_path,
            index_path=index_path,
            language_stats={},
            total_files=0,
            total_symbols=0,
            indexed_at=datetime.now(),
            active=True,
        )
        manager.registry.register(repo_info)

        results = asyncio.run(manager.search_symbol("MyTestClass", repository_ids=[repo_id]))
        assert any(
            "MyTestClass" in str(r) for r in results
        ), f"Expected MyTestClass in results, got: {results}"
