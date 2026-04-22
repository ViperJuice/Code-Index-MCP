"""Tests for BM25 adapter plugin bind(ctx) refactor (SL-5)."""

import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mcp_server.plugins.bm25_adapter_plugin import BM25AdapterPlugin
from mcp_server.plugins.js_plugin.plugin import Plugin as JsPlugin

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ctx(db_path: str):
    """Build a minimal fake RepoContext with a sqlite_store pointing to db_path."""
    sqlite_store = MagicMock()
    sqlite_store.db_path = db_path
    ctx = MagicMock()
    ctx.sqlite_store = sqlite_store
    return ctx


def _init_fts5_db(db_path: str) -> None:
    """Create a minimal bm25_content FTS5 table for integration tests."""
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE VIRTUAL TABLE IF NOT EXISTS bm25_content "
        "USING fts5(filepath, filename, content, language)"
    )
    conn.execute(
        "INSERT INTO bm25_content VALUES (?, ?, ?, ?)",
        ("src/foo.py", "foo.py", "def MyFunc(): pass", "python"),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# SL-5 Test 1: BM25 FTS5 query routes through ctx.sqlite_store.db_path
# ---------------------------------------------------------------------------


class TestBM25AdapterBindCtx:
    def test_search_calls_sqlite_connect_with_ctx_db_path(self):
        """After bind(ctx), search() opens ctx.sqlite_store.db_path."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        _init_fts5_db(db_path)

        plugin = BM25AdapterPlugin()
        ctx = _make_ctx(db_path)
        plugin.bind(ctx)

        with patch("sqlite3.connect", wraps=sqlite3.connect) as mock_connect:
            results = list(plugin.search("MyFunc", None))

        # Must have connected to the path provided by ctx, not ctor arg
        called_paths = [call.args[0] for call in mock_connect.call_args_list]
        assert (
            db_path in called_paths
        ), f"Expected sqlite3.connect({db_path!r}), got {called_paths!r}"

    def test_getdefinition_calls_sqlite_connect_with_ctx_db_path(self):
        """After bind(ctx), getDefinition() opens ctx.sqlite_store.db_path."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        _init_fts5_db(db_path)

        plugin = BM25AdapterPlugin()
        ctx = _make_ctx(db_path)
        plugin.bind(ctx)

        with patch("sqlite3.connect", wraps=sqlite3.connect) as mock_connect:
            plugin.getDefinition("MyFunc")

        called_paths = [call.args[0] for call in mock_connect.call_args_list]
        assert db_path in called_paths

    def test_no_db_path_without_bind(self):
        """Without bind, plugin has no _db_path and returns None/empty gracefully."""
        plugin = BM25AdapterPlugin()
        assert plugin.getDefinition("anything") is None
        assert list(plugin.search("anything", None)) == []


# ---------------------------------------------------------------------------
# SL-5 Test 2: js_plugin has no _sqlite_store attribute after bind
# ---------------------------------------------------------------------------


class TestJsPluginBindCtx:
    def test_js_plugin_has_no_sqlite_store_attr(self, monkeypatch):
        """After bind(ctx), js_plugin should not carry _sqlite_store."""
        monkeypatch.setenv("MCP_SKIP_PLUGIN_PREINDEX", "true")
        plugin = JsPlugin()
        ctx = _make_ctx(":memory:")
        plugin.bind(ctx)
        assert not hasattr(
            plugin, "_sqlite_store"
        ), "js_plugin must not expose _sqlite_store after SL-5 refactor"

    def test_js_plugin_ctx_set_after_bind(self, monkeypatch):
        """bind(ctx) sets _ctx on the plugin."""
        monkeypatch.setenv("MCP_SKIP_PLUGIN_PREINDEX", "true")
        plugin = JsPlugin()
        ctx = _make_ctx(":memory:")
        plugin.bind(ctx)
        assert plugin._ctx is ctx


# ---------------------------------------------------------------------------
# SL-5 Test 3: rg returns zero _sqlite_store hits in owned files
# ---------------------------------------------------------------------------


class TestNoResidualSqliteStoreAttr:
    def test_rg_finds_no_sqlite_store_assignments(self):
        """rg -n '_sqlite_store' in the three plugin files returns zero matches."""
        repo_root = Path(__file__).parent.parent
        targets = [
            repo_root / "mcp_server/plugins/js_plugin/plugin.py",
            repo_root / "mcp_server/plugins/bm25_adapter_plugin.py",
            repo_root / "mcp_server/plugin_base_enhanced.py",
        ]
        result = subprocess.run(
            ["rg", "-n", "_sqlite_store"] + [str(t) for t in targets],
            capture_output=True,
            text=True,
        )
        assert (
            result.returncode != 0 or result.stdout.strip() == ""
        ), f"Found residual _sqlite_store references:\n{result.stdout}"
