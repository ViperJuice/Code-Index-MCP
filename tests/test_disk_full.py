"""Tests for SQLite ENOSPC → read-only mode behaviour (SL-3)."""

import sqlite3
from unittest.mock import MagicMock, patch

import pytest

from mcp_server.core.errors import TransientArtifactError
from mcp_server.metrics.prometheus_exporter import mcp_storage_readonly_total
from mcp_server.storage.sqlite_store import SQLiteStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_store(tmp_path):
    db = str(tmp_path / "test.db")
    return SQLiteStore(db_path=db)


def _counter_value() -> int:
    try:
        return int(mcp_storage_readonly_total._value.get())
    except Exception:
        return 0


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestEnospcReadonly:
    def test_commit_enospc_sets_readonly(self, tmp_path):
        """commit() raising ENOSPC-style error transitions store to read-only."""
        store = _make_store(tmp_path)
        assert store._readonly is False

        baseline = _counter_value()

        enospc = sqlite3.OperationalError("database or disk is full")

        # sqlite3.Connection.commit is a C-level attribute and cannot be replaced on
        # instances. Use a thin proxy that delegates all attribute access to the real
        # connection but overrides commit() to raise once.
        class _CommitFailProxy:
            def __init__(self, real):
                self._real = real
                self._failed = False

            def commit(self):
                if not self._failed:
                    self._failed = True
                    raise enospc
                self._real.commit()

            def __getattr__(self, name):
                return getattr(self._real, name)

        original_connect = sqlite3.connect

        def patched_connect(*args, **kwargs):
            return _CommitFailProxy(original_connect(*args, **kwargs))

        with patch("mcp_server.storage.sqlite_store.sqlite3.connect", side_effect=patched_connect):
            with pytest.raises((TransientArtifactError, sqlite3.OperationalError)):
                with store._get_connection() as conn:
                    conn.execute("SELECT 1")

        assert store._readonly is True
        assert _counter_value() == baseline + 1

    def test_reads_work_after_readonly(self, tmp_path):
        """Read queries succeed even when _readonly is True."""
        store = _make_store(tmp_path)
        store._readonly = True
        # _get_connection is used for reads and must NOT gate on _readonly.
        with store._get_connection() as conn:
            result = conn.execute("SELECT 1").fetchone()
        assert result[0] == 1

    def test_writes_raise_after_readonly(self, tmp_path):
        """Write methods raise TransientArtifactError when store is read-only."""
        store = _make_store(tmp_path)
        store._readonly = True
        with pytest.raises(TransientArtifactError, match="read-only"):
            store.store_file(
                repository_id=1,
                relative_path="foo/bar.py",
            )
