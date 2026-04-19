"""Tests for atomic rename via two_phase_commit wrapper in dispatcher_enhanced.move_file."""

import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch, PropertyMock

import pytest

from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.core.repo_context import RepoContext
from mcp_server.core.errors import IndexingError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_store(tmp_path: Path) -> SQLiteStore:
    db_path = tmp_path / "idx.db"
    return SQLiteStore(str(db_path))


def _make_ctx(store: SQLiteStore, repo_id: str = "repo-1") -> RepoContext:
    info = Mock()
    info.tracked_branch = "main"
    return RepoContext(
        repo_id=repo_id,
        sqlite_store=store,
        workspace_root=Path("/repo"),
        tracked_branch="main",
        registry_entry=info,
    )


def _seed_file(store: SQLiteStore, relative_path: str, repo_int_id: int = 1) -> None:
    """Insert a file row into the store using create_repository + store_file."""
    store.store_file(
        path=f"/repo/{relative_path}",
        relative_path=relative_path,
        language="python",
        repository_id=repo_int_id,
    )


def _make_dispatcher(store: SQLiteStore):
    """Return a minimal EnhancedDispatcher with SQLite store and no semantic indexer."""
    from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
    dispatcher = EnhancedDispatcher.__new__(EnhancedDispatcher)
    # Minimal attribute init — only what move_file needs
    dispatcher._operation_stats = {}
    dispatcher._legacy_plugins = []
    dispatcher._lazy_load = False
    dispatcher._use_factory = False
    dispatcher._enable_advanced = False
    dispatcher._router = None
    dispatcher._semantic_registry = None
    dispatcher._semantic_indexer_fallback = None
    dispatcher._plugin_set_registry = Mock()
    dispatcher._plugin_set_registry.plugins_for.return_value = []
    return dispatcher


# ---------------------------------------------------------------------------
# test_rename_single_remove_single_add (acceptance #6)
# ---------------------------------------------------------------------------

class TestRenameSingleRemoveSingleAdd:
    """After move_file(foo.py → bar.py) SQLite shows only bar.py."""

    def test_rename_single_remove_single_add(self, tmp_path):
        store = _make_store(tmp_path)
        repo_id = store.create_repository(path="/repo", name="testrepo")
        _seed_file(store, "foo.py", repo_int_id=repo_id)

        ctx = _make_ctx(store)
        dispatcher = _make_dispatcher(store)

        old_path = Path("/repo/foo.py")
        new_path = Path("/repo/bar.py")

        dispatcher.move_file(ctx, old_path, new_path, content_hash="abc123")

        # Query SQLite directly
        with store._get_connection() as conn:
            rows = conn.execute(
                "SELECT relative_path FROM files "
                "WHERE repository_id = ? AND relative_path IN ('foo.py', 'bar.py') "
                "AND (is_deleted = 0 OR is_deleted IS NULL)",
                (repo_id,),
            ).fetchall()

        paths = [r[0] for r in rows]
        assert paths == ["bar.py"], f"Expected only bar.py but got {paths}"


# ---------------------------------------------------------------------------
# test_rename_rollback_on_semantic_failure (acceptance #6 + metric check)
# ---------------------------------------------------------------------------

class TestRenameRollbackOnSemanticFailure:
    """When semantic indexer raises, SQLite must be rolled back to old path."""

    def test_rename_rollback_on_semantic_failure(self, tmp_path):
        store = _make_store(tmp_path)
        repo_id = store.create_repository(path="/repo", name="testrepo")
        _seed_file(store, "foo.py", repo_int_id=repo_id)

        ctx = _make_ctx(store)
        dispatcher = _make_dispatcher(store)

        # Inject a failing plugin._indexer via _match_plugin
        failing_indexer = Mock()
        failing_indexer.move_file = Mock(side_effect=RuntimeError("semantic failure"))
        plugin_with_indexer = Mock()
        plugin_with_indexer._indexer = failing_indexer

        old_path = Path("/repo/foo.py")
        new_path = Path("/repo/bar.py")

        with patch.object(dispatcher, "_match_plugin", return_value=plugin_with_indexer):
            # Should raise (TwoPhaseCommitError wrapping IndexingError, or IndexingError)
            with pytest.raises(Exception):
                dispatcher.move_file(ctx, old_path, new_path, content_hash="abc123")

        # SQLite must still show OLD path, not new
        with store._get_connection() as conn:
            rows = conn.execute(
                "SELECT relative_path FROM files "
                "WHERE repository_id = ? AND relative_path IN ('foo.py', 'bar.py') "
                "AND (is_deleted = 0 OR is_deleted IS NULL)",
                (repo_id,),
            ).fetchall()

        paths = [r[0] for r in rows]
        assert paths == ["foo.py"], f"Expected rollback to foo.py but got {paths}"

    def test_rename_rollback_increments_error_metric(self, tmp_path):
        """IndexingError metric label increments on semantic failure."""
        store = _make_store(tmp_path)
        repo_id = store.create_repository(path="/repo", name="testrepo")
        _seed_file(store, "foo.py", repo_int_id=repo_id)

        ctx = _make_ctx(store)
        dispatcher = _make_dispatcher(store)

        failing_indexer = Mock()
        failing_indexer.move_file = Mock(side_effect=RuntimeError("boom"))
        plugin_with_indexer = Mock()
        plugin_with_indexer._indexer = failing_indexer

        old_path = Path("/repo/foo.py")
        new_path = Path("/repo/bar.py")

        call_count = []

        def fake_record_handled_error(module, exc):
            call_count.append((module, type(exc).__name__))

        with patch(
            "mcp_server.dispatcher.dispatcher_enhanced.record_handled_error",
            side_effect=fake_record_handled_error,
        ), patch.object(dispatcher, "_match_plugin", return_value=plugin_with_indexer):
            with pytest.raises(Exception):
                dispatcher.move_file(ctx, old_path, new_path, content_hash="abc123")

        assert len(call_count) >= 1
        modules = [c[0] for c in call_count]
        exc_names = [c[1] for c in call_count]
        assert "mcp_server.dispatcher.dispatcher_enhanced" in modules
        assert "IndexingError" in exc_names
