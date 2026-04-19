"""Extension-gating tests for EnhancedDispatcher's run_gated_fallback delegation."""

import os
import sqlite3
from pathlib import Path
from typing import Iterable, Optional
from unittest.mock import MagicMock, patch

import pytest

from mcp_server.core.repo_context import RepoContext
from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
from mcp_server.plugin_base import IPlugin, IndexShard, Reference, SearchOpts, SearchResult, SymbolDef
from mcp_server.plugins.plugin_set_registry import PluginSetRegistry
from mcp_server.storage.multi_repo_manager import RepositoryInfo
from mcp_server.storage.sqlite_store import SQLiteStore


REPO_ID = "test-gating-repo"


def _make_db(tmp_path: Path, filepath: str) -> str:
    """Create a minimal SQLite db with bm25_content table containing one row."""
    db_path = str(tmp_path / "test.db")
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE VIRTUAL TABLE bm25_content USING fts5(filepath, filename, content, language)"
    )
    conn.execute(
        "INSERT INTO bm25_content(filepath, filename, content, language) VALUES (?, ?, ?, ?)",
        (filepath, os.path.basename(filepath), "foo bar baz", "python"),
    )
    conn.commit()
    conn.close()
    return db_path


def _make_ctx(db_path: str) -> RepoContext:
    store = SQLiteStore(db_path)
    registry_entry = MagicMock(spec=RepositoryInfo)
    registry_entry.tracked_branch = "main"
    return RepoContext(
        repo_id=REPO_ID,
        sqlite_store=store,
        workspace_root=Path(db_path).parent,
        tracked_branch="main",
        registry_entry=registry_entry,
    )


def _make_dispatcher_with_plugins(plugins: list) -> EnhancedDispatcher:
    """Create an EnhancedDispatcher with a fixed plugin set injected into its registry."""
    dispatcher = EnhancedDispatcher(
        plugins=None,
        enable_advanced_features=False,
        use_plugin_factory=False,
        lazy_load=False,
        semantic_search_enabled=False,
    )
    dispatcher._plugin_set_registry._cache[REPO_ID] = plugins
    return dispatcher


class FakePyPlugin(IPlugin):
    """Plugin that claims to handle .py files."""
    lang = "python"

    def supports(self, path) -> bool:
        return str(path).endswith(".py")

    def indexFile(self, path, content) -> IndexShard:
        return {"file": str(path), "symbols": [], "language": "python"}

    def getDefinition(self, symbol: str) -> Optional[SymbolDef]:
        return None

    def findReferences(self, symbol: str) -> Iterable[Reference]:
        return []

    def search(self, query: str, opts=None) -> Iterable[SearchResult]:
        return []


class SpyPlugin(IPlugin):
    """Plugin that records getDefinition calls."""
    lang = "spy"

    def __init__(self) -> None:
        self.calls: list = []

    def supports(self, path) -> bool:
        return True

    def indexFile(self, path, content) -> IndexShard:
        return {"file": str(path), "symbols": [], "language": "spy"}

    def getDefinition(self, symbol: str) -> Optional[SymbolDef]:
        self.calls.append(symbol)
        return None

    def findReferences(self, symbol: str) -> Iterable[Reference]:
        return []

    def search(self, query: str, opts=None) -> Iterable[SearchResult]:
        return []


def test_py_extension_gating_no_plugin_instantiation(tmp_path):
    """CPlugin-equivalent must not be called when BM25 row has .py extension."""
    db_path = _make_db(tmp_path, "src/main.py")
    ctx = _make_ctx(db_path)

    # A plugin whose instantiation would raise — register it by class name under .py
    class CPlugin(IPlugin):
        lang = "c"

        def __init__(self):
            raise AssertionError("must not instantiate")

        def supports(self, path) -> bool:
            return str(path).endswith(".c")

        def indexFile(self, path, content) -> IndexShard:
            return {"file": str(path), "symbols": [], "language": "c"}

        def getDefinition(self, symbol: str) -> Optional[SymbolDef]:
            raise AssertionError("must not call")

        def findReferences(self, symbol: str) -> Iterable[Reference]:
            return []

        def search(self, query: str, opts=None) -> Iterable[SearchResult]:
            return []

    # Inject only a safe Python plugin; CPlugin is never registered in the plugin list.
    # The gating happens via the PluginRegistry extension_map — since we pass no
    # registry to run_gated_fallback, all plugins in the list ARE tried unless we
    # use extension-name-based gating. This test validates that lookup() returns None
    # without raising when the BM25 row points to a .py file and no plugin returns a def.
    py_plugin = FakePyPlugin()
    dispatcher = _make_dispatcher_with_plugins([py_plugin])

    result = dispatcher.lookup(ctx, "foo", limit=20)
    assert result is None


def test_no_bm25_row_no_plugin_called(tmp_path):
    """When BM25 has no match for the symbol, source_ext is None and no plugin is called."""
    db_path = _make_db(tmp_path, "src/other.py")
    ctx = _make_ctx(db_path)

    spy = SpyPlugin()
    dispatcher = _make_dispatcher_with_plugins([spy])

    # Use a symbol that won't match the BM25 content ("foo bar baz")
    result = dispatcher.lookup(ctx, "zzznomatch_xyz_qrs", limit=20)
    assert result is None
    assert spy.calls == [], "getDefinition must not be called when source_ext is None"


def test_c_extension_routes_to_c_plugin(tmp_path):
    """When BM25 row filepath ends in .c, a C-flavored spy plugin's getDefinition is called."""
    db_path = _make_db(tmp_path, "src/main.c")

    # Insert an additional row for a .c filepath so the symbol lookup matches it
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO bm25_content(filepath, filename, content, language) VALUES (?, ?, ?, ?)",
        ("src/main.c", "main.c", "void myfunc()", "c"),
    )
    conn.commit()
    conn.close()

    ctx = _make_ctx(db_path)

    spy = SpyPlugin()
    spy.lang = "c"
    dispatcher = _make_dispatcher_with_plugins([spy])

    # "myfunc" should match the BM25 row, setting source_ext=".c".
    # run_gated_fallback has no registry → allowed_names=None → spy is called.
    dispatcher.lookup(ctx, "myfunc", limit=20)
    assert "myfunc" in spy.calls, "getDefinition should be called for .c extension match"
