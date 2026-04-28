"""
Comprehensive tests for the Dispatcher component.

Tests cover:
- Plugin registration and management
- Symbol lookup and caching
- Search functionality
- File indexing with caching
- Error handling and edge cases
"""

import hashlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

import pytest

from mcp_server.core.repo_context import RepoContext
from mcp_server.dispatcher import EnhancedDispatcher as Dispatcher

# ---------------------------------------------------------------------------
# SL-1.1 imports (new Protocol-conformance tests)
# ---------------------------------------------------------------------------
from mcp_server.dispatcher.dispatcher_enhanced import (
    IndexResult,
    IndexResultStatus,
    SemanticSearchFailure,
)
from mcp_server.dispatcher.protocol import DispatcherProtocol
from mcp_server.dispatcher.query_intent import QueryIntent, classify
from mcp_server.dispatcher.simple_dispatcher import SimpleDispatcher
from mcp_server.plugin_base import IPlugin, SearchResult, SymbolDef
from tests.conftest import measure_time


class TestDispatcherInitialization:
    """Test Dispatcher initialization and configuration."""

    def test_init_with_single_plugin(self, mock_plugin):
        """Test initialization with a single plugin."""
        dispatcher = Dispatcher([mock_plugin])

        assert len(dispatcher.plugins()) == 1
        assert mock_plugin in dispatcher.plugins()
        assert dispatcher._file_cache == {}

    def test_init_with_multiple_plugins(self):
        """Test initialization with multiple plugins."""
        plugin1 = Mock(spec=IPlugin, lang="python")
        plugin2 = Mock(spec=IPlugin, lang="javascript")
        plugin3 = Mock(spec=IPlugin, lang="java")

        dispatcher = Dispatcher([plugin1, plugin2, plugin3])

        assert len(dispatcher.plugins()) == 3
        assert plugin1 in dispatcher.plugins()
        assert plugin2 in dispatcher.plugins()
        assert plugin3 in dispatcher.plugins()

    def test_init_empty_plugins(self):
        """Test initialization with no plugins."""
        dispatcher = Dispatcher([])

        assert len(dispatcher.plugins()) == 0

    def test_plugins_method(self, mock_plugin):
        """Test the plugins() method returns list of plugins."""
        dispatcher = Dispatcher([mock_plugin])

        plugins = dispatcher.plugins()
        assert isinstance(plugins, list)
        assert mock_plugin in plugins

    @patch("mcp_server.dispatcher.dispatcher_enhanced.MultiRepositoryManager")
    @patch("mcp_server.dispatcher.dispatcher_enhanced.CrossRepositorySearchCoordinator")
    @patch("pathlib.Path.home")
    def test_multi_repo_default_registry_path_uses_home_directory(
        self, mock_home, mock_cross_repo, mock_multi_repo
    ):
        """Default multi-repo registry path should be user-writable under ~/.mcp."""
        mock_home.return_value = Path("/tmp/test-home")

        with patch.dict("os.environ", {"MCP_ENABLE_MULTI_REPO": "true"}, clear=False):
            Dispatcher([])

        registry_path = mock_multi_repo.call_args.kwargs["central_index_path"]
        assert (
            registry_path
            == Path("/tmp/test-home") / ".mcp" / "indexes" / "repository_registry.json"
        )


class TestPluginMatching:
    """Test plugin matching for files."""

    def test_match_plugin_success(self):
        """Test successful plugin matching."""
        py_plugin = Mock(spec=IPlugin, lang="python")
        py_plugin.supports.return_value = True

        js_plugin = Mock(spec=IPlugin, lang="javascript")
        js_plugin.supports.return_value = False

        dispatcher = Dispatcher([py_plugin, js_plugin])

        result = dispatcher._match_plugin(Path("test.py"))
        assert result == py_plugin
        py_plugin.supports.assert_called_with(Path("test.py"))

    def test_match_plugin_no_match(self, mock_plugin):
        """Test when no plugin matches the file."""
        mock_plugin.supports.return_value = False
        dispatcher = Dispatcher([mock_plugin])

        with pytest.raises(RuntimeError, match="No plugin"):
            dispatcher._match_plugin(Path("test.unknown"))

    def test_match_plugin_multiple_matches(self):
        """Test when multiple plugins match (first wins)."""
        plugin1 = Mock(spec=IPlugin, lang="plugin1")
        plugin1.supports.return_value = True

        plugin2 = Mock(spec=IPlugin, lang="plugin2")
        plugin2.supports.return_value = True

        dispatcher = Dispatcher([plugin1, plugin2])

        result = dispatcher._match_plugin(Path("test.file"))
        assert result == plugin1  # First matching plugin wins


class TestSymbolLookup:
    """Test symbol lookup functionality (first-hit semantics via run_gated_fallback)."""

    def test_lookup_found(self, mock_plugin):
        """Test successful symbol lookup — first-truthy-hit semantics (IF-0-P11-1)."""
        from mcp_server.dispatcher.fallback import run_gated_fallback

        expected_symbol = SymbolDef(name="test_func", kind="function", path="/test.py", line=10)
        mock_plugin.getDefinition.return_value = expected_symbol

        result = run_gated_fallback([mock_plugin], "test_func", source_ext=".py", timeout_ms=1000)

        assert result == expected_symbol
        mock_plugin.getDefinition.assert_called_once_with("test_func")

    def test_lookup_not_found(self, mock_plugin):
        """Test symbol lookup when not found — run_gated_fallback returns None."""
        from mcp_server.dispatcher.fallback import run_gated_fallback

        mock_plugin.getDefinition.return_value = None

        result = run_gated_fallback([mock_plugin], "nonexistent", source_ext=".py", timeout_ms=1000)

        assert result is None
        mock_plugin.getDefinition.assert_called_once_with("nonexistent")

    def test_lookup_multiple_plugins(self):
        """Test lookup across multiple plugins — stops at first truthy hit (IF-0-P11-1)."""
        from mcp_server.dispatcher.fallback import run_gated_fallback

        plugin1 = Mock(spec=IPlugin, lang="python")
        plugin1.getDefinition.return_value = None

        expected_symbol = SymbolDef(name="found", kind="class", path="/found.js", line=5)
        plugin2 = Mock(spec=IPlugin, lang="javascript")
        plugin2.getDefinition.return_value = expected_symbol

        plugin3 = Mock(spec=IPlugin, lang="java")
        plugin3.getDefinition.return_value = None

        result = run_gated_fallback(
            [plugin1, plugin2, plugin3], "found", source_ext=".py", timeout_ms=1000
        )

        assert result == expected_symbol
        plugin1.getDefinition.assert_called_once_with("found")
        plugin2.getDefinition.assert_called_once_with("found")
        # plugin3 is NOT called since plugin2 returned a truthy hit
        plugin3.getDefinition.assert_not_called()

    def test_lookup_plugin_error(self, mock_plugin):
        """Test lookup when plugin raises error."""
        mock_plugin.getDefinition.side_effect = Exception("Plugin error")

        ctx = _make_repo_ctx()
        dispatcher = Dispatcher([mock_plugin])

        # Dispatcher catches plugin errors and returns None
        result = dispatcher.lookup(ctx, "test")
        assert result is None


def _make_psr_with_plugins(repo_id: str, plugins: list):
    """Build a PluginSetRegistry pre-seeded with *plugins* for *repo_id*.

    This bypasses MemoryAwarePluginManager so mock plugins are visible to
    the dispatcher's plugin-fallback search path (first-hit semantics, SL-4).
    """
    from mcp_server.plugins.plugin_set_registry import PluginSetRegistry

    psr = PluginSetRegistry()
    psr._cache[repo_id] = list(plugins)
    return psr


class TestSearch:
    """Test search functionality."""

    _REPO_ID = "test-repo"

    def _make_no_sqlite_ctx(self):
        """Build a RepoContext with no sqlite_store so dispatcher falls back to plugins."""
        from pathlib import Path
        from unittest.mock import MagicMock

        from mcp_server.core.repo_context import RepoContext
        from mcp_server.storage.multi_repo_manager import RepositoryInfo

        registry_entry = MagicMock(spec=RepositoryInfo)
        registry_entry.tracked_branch = "main"
        return RepoContext(
            repo_id=self._REPO_ID,
            sqlite_store=None,
            workspace_root=Path("/tmp/test"),
            tracked_branch="main",
            registry_entry=registry_entry,
        )

    def test_search_basic(self, mock_plugin):
        """Test basic search across plugins when no sqlite_store (plugin fallback path)."""
        expected_results = [
            SearchResult(name="func1", kind="function", path="/f1.py", score=0.9),
            SearchResult(name="func2", kind="function", path="/f2.py", score=0.8),
        ]
        mock_plugin.search.return_value = expected_results

        ctx = self._make_no_sqlite_ctx()
        psr = _make_psr_with_plugins(self._REPO_ID, [mock_plugin])
        dispatcher = Dispatcher([mock_plugin], plugin_set_registry=psr)
        results = list(dispatcher.search(ctx, "func"))

        assert results == expected_results
        mock_plugin.search.assert_called_once_with("func", {"semantic": False, "limit": 20})

    def test_search_semantic(self, mock_plugin):
        """Test semantic search falls back to plugins when no sqlite/semantic indexer."""
        mock_plugin.search.return_value = []

        ctx = self._make_no_sqlite_ctx()
        psr = _make_psr_with_plugins(self._REPO_ID, [mock_plugin])
        dispatcher = Dispatcher([mock_plugin], plugin_set_registry=psr)
        dispatcher._semantic_indexer_fallback = None
        list(dispatcher.search(ctx, "test", semantic=True, limit=10))

        mock_plugin.search.assert_called_once_with("test", {"semantic": True, "limit": 10})

    def test_search_registered_semantic_returns_semantic_metadata(self):
        store = MagicMock()
        ctx = _make_repo_ctx(store)
        semantic_indexer = MagicMock()
        semantic_indexer.search.return_value = [
            {
                "relative_path": "mcp_server/utils/semantic_indexer.py",
                "line": 42,
                "snippet": "class SemanticIndexer:",
                "score": 0.84,
                "semantic_source": "semantic",
                "semantic_profile_id": "oss_high",
                "semantic_collection_name": "code_index__oss_high__v1",
            }
        ]

        dispatcher = Dispatcher([])
        dispatcher._semantic_registry = MagicMock(get=MagicMock(return_value=semantic_indexer))

        results = list(dispatcher.search(ctx, "class SemanticIndexer", semantic=True, limit=5))

        assert results[0]["file"] == "mcp_server/utils/semantic_indexer.py"
        assert results[0]["semantic_source"] == "semantic"
        assert results[0]["semantic_profile_id"] == "oss_high"
        assert results[0]["semantic_collection_name"] == "code_index__oss_high__v1"
        store.search_bm25.assert_not_called()

    def test_search_registered_semantic_failure_does_not_fall_back_to_bm25(self):
        store = MagicMock()
        store.search_bm25.return_value = [
            {"filepath": "docs/guides/semantic-onboarding.md", "score": -1.0, "snippet": "docs"}
        ]
        ctx = _make_repo_ctx(store)
        semantic_indexer = MagicMock()
        semantic_indexer.search.side_effect = RuntimeError("qdrant offline")
        semantic_indexer.semantic_profile = SimpleNamespace(profile_id="oss_high")
        semantic_indexer.collection = "code_index__oss_high__v1"

        dispatcher = Dispatcher([])
        dispatcher._semantic_registry = MagicMock(get=MagicMock(return_value=semantic_indexer))

        with pytest.raises(SemanticSearchFailure, match="Semantic search failed"):
            list(dispatcher.search(ctx, "class SemanticIndexer", semantic=True, limit=5))

        store.search_bm25.assert_not_called()

    def test_search_lexical_false_path_remains_unchanged_when_semantic_available(self):
        store = MagicMock()
        store.search_bm25.return_value = [
            {
                "filepath": "mcp_server/utils/semantic_indexer.py",
                "score": -2.0,
                "snippet": "class SemanticIndexer",
                "language": "python",
            }
        ]
        store.find_best_chunk_for_file.return_value = None
        ctx = _make_repo_ctx(store)
        semantic_indexer = MagicMock()

        dispatcher = Dispatcher([])
        dispatcher._semantic_registry = MagicMock(get=MagicMock(return_value=semantic_indexer))

        results = list(dispatcher.search(ctx, "semantic preflight validation", semantic=False, limit=5))

        assert results[0]["file"] == "mcp_server/utils/semantic_indexer.py"
        semantic_indexer.search.assert_not_called()
        store.search_bm25.assert_called()

    def test_search_multiple_plugins(self):
        """Test search results from multiple plugins are combined (first-hit plugin path)."""
        plugin1 = Mock(spec=IPlugin, lang="python")
        plugin1.search.return_value = [
            SearchResult(name="py_func", kind="function", path="/test.py", score=0.9)
        ]

        plugin2 = Mock(spec=IPlugin, lang="javascript")
        plugin2.search.return_value = [
            SearchResult(name="js_func", kind="function", path="/test.js", score=0.8),
            SearchResult(name="js_class", kind="class", path="/test2.js", score=0.7),
        ]

        from pathlib import Path
        from unittest.mock import MagicMock

        from mcp_server.core.repo_context import RepoContext
        from mcp_server.storage.multi_repo_manager import RepositoryInfo

        registry_entry = MagicMock(spec=RepositoryInfo)
        registry_entry.tracked_branch = "main"
        ctx = RepoContext(
            repo_id=self._REPO_ID,
            sqlite_store=None,
            workspace_root=Path("/tmp/test"),
            tracked_branch="main",
            registry_entry=registry_entry,
        )

        psr = _make_psr_with_plugins(self._REPO_ID, [plugin1, plugin2])
        dispatcher = Dispatcher([plugin1, plugin2], plugin_set_registry=psr)
        results = list(dispatcher.search(ctx, "test"))

        assert len(results) == 3
        assert results[0]["name"] == "py_func"
        assert results[1]["name"] == "js_func"
        assert results[2]["name"] == "js_class"

    def test_search_empty_query(self, mock_plugin):
        """Test search with empty query."""
        mock_plugin.search.return_value = []

        ctx = self._make_no_sqlite_ctx()
        psr = _make_psr_with_plugins(self._REPO_ID, [mock_plugin])
        dispatcher = Dispatcher([mock_plugin], plugin_set_registry=psr)
        results = list(dispatcher.search(ctx, ""))

        assert results == []
        mock_plugin.search.assert_called_once()

    def test_search_plugin_error(self, mock_plugin):
        """Test search when plugin raises error."""
        mock_plugin.search.side_effect = Exception("Search error")

        ctx = self._make_no_sqlite_ctx()
        psr = _make_psr_with_plugins(self._REPO_ID, [mock_plugin])
        dispatcher = Dispatcher([mock_plugin], plugin_set_registry=psr)

        # Dispatcher catches plugin errors and returns empty results
        results = list(dispatcher.search(ctx, "test"))
        assert results == []


class TestFileHashing:
    """Test file content hashing functionality."""

    def test_get_file_hash(self, mock_plugin):
        """Test file hash calculation."""
        dispatcher = Dispatcher([mock_plugin])

        content = "def hello():\n    print('world')\n"
        expected_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        result = dispatcher._get_file_hash(content)
        assert result == expected_hash

    def test_get_file_hash_unicode(self, mock_plugin):
        """Test file hash with unicode content."""
        dispatcher = Dispatcher([mock_plugin])

        content = "def 你好():\n    print('世界')\n"
        expected_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        result = dispatcher._get_file_hash(content)
        assert result == expected_hash

    def test_get_file_hash_empty(self, mock_plugin):
        """Test file hash for empty content."""
        dispatcher = Dispatcher([mock_plugin])

        content = ""
        expected_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        result = dispatcher._get_file_hash(content)
        assert result == expected_hash


class TestCacheLogic:
    """Test file caching logic."""

    def test_should_reindex_new_file(self, mock_plugin):
        """Test that new files should be indexed."""
        dispatcher = Dispatcher([mock_plugin])

        path = Path("/test/new_file.py")
        content = "print('hello')"

        assert dispatcher._should_reindex(path, content) is True

    def test_should_reindex_modified_file(self, mock_plugin):
        """Test that modified files should be reindexed."""
        dispatcher = Dispatcher([mock_plugin])

        path = Path("/test/file.py")
        old_content = "print('hello')"
        new_content = "print('hello world')"

        # First index
        with patch.object(Path, "stat") as mock_stat:
            mock_stat.return_value.st_mtime = 1000.0
            mock_stat.return_value.st_size = len(old_content)

            assert dispatcher._should_reindex(path, old_content) is True

            # Update cache manually
            dispatcher._file_cache[str(path)] = (
                1000.0,
                len(old_content),
                dispatcher._get_file_hash(old_content),
            )

        # Second index with different content
        with patch.object(Path, "stat") as mock_stat:
            mock_stat.return_value.st_mtime = 2000.0
            mock_stat.return_value.st_size = len(new_content)

            assert dispatcher._should_reindex(path, new_content) is True

    def test_should_not_reindex_unchanged_file(self, mock_plugin):
        """Test that unchanged files are not reindexed."""
        dispatcher = Dispatcher([mock_plugin])

        path = Path("/test/file.py")
        content = "print('hello')"
        content_hash = dispatcher._get_file_hash(content)

        # Set up cache
        dispatcher._file_cache[str(path)] = (1000.0, len(content), content_hash)

        # Same mtime and size
        with patch.object(Path, "stat") as mock_stat:
            mock_stat.return_value.st_mtime = 1000.0
            mock_stat.return_value.st_size = len(content)

            assert dispatcher._should_reindex(path, content) is False

    def test_should_reindex_size_changed_content_same(self, mock_plugin):
        """Test when size changes but content hash is same (rare edge case)."""
        dispatcher = Dispatcher([mock_plugin])

        path = Path("/test/file.py")
        content = "print('hello')"
        content_hash = dispatcher._get_file_hash(content)

        # Set up cache with different size
        dispatcher._file_cache[str(path)] = (1000.0, 999, content_hash)

        with patch.object(Path, "stat") as mock_stat:
            mock_stat.return_value.st_mtime = 2000.0
            mock_stat.return_value.st_size = len(content)

            # Should not reindex if hash is same
            assert dispatcher._should_reindex(path, content) is False

    def test_should_reindex_stat_error(self, mock_plugin):
        """Test when file stat fails."""
        dispatcher = Dispatcher([mock_plugin])

        path = Path("/test/file.py")
        content = "print('hello')"

        with patch.object(Path, "stat") as mock_stat:
            mock_stat.side_effect = OSError("File not found")

            assert dispatcher._should_reindex(path, content) is True


class TestIndexFile:
    """Test file indexing functionality."""

    def test_index_file_success(self, mock_plugin, tmp_path):
        """Test successful file indexing."""
        dispatcher = Dispatcher([mock_plugin], use_plugin_factory=False, lazy_load=False)

        # Create test file
        test_file = tmp_path / "test.py"
        test_file.write_text("def hello(): pass")

        mock_plugin.supports.return_value = True
        mock_plugin.indexFile.return_value = {"symbols": [{"name": "hello", "kind": "function"}]}

        ctx = _make_repo_ctx()
        dispatcher.index_file(ctx, test_file)

        mock_plugin.indexFile.assert_called_once()
        assert str(test_file) in dispatcher._file_cache

    def test_index_file_unicode_decode_error(self, mock_plugin, tmp_path):
        """Test indexing file with encoding issues."""
        dispatcher = Dispatcher([mock_plugin], use_plugin_factory=False, lazy_load=False)

        test_file = tmp_path / "test.py"
        # Write binary data that's not valid UTF-8
        test_file.write_bytes(b"\xff\xfe invalid utf-8")

        mock_plugin.supports.return_value = True

        # Should try latin-1 encoding
        ctx = _make_repo_ctx()
        dispatcher.index_file(ctx, test_file)

        # Plugin should be called with latin-1 decoded content
        mock_plugin.indexFile.assert_called_once()

    def test_index_file_read_error(self, mock_plugin):
        """Test indexing when file read fails."""
        dispatcher = Dispatcher([mock_plugin])

        path = Path("/nonexistent/file.py")
        mock_plugin.supports.return_value = True

        # Should not raise, just log error
        ctx = _make_repo_ctx()
        dispatcher.index_file(ctx, path)

        mock_plugin.indexFile.assert_not_called()

    def test_index_file_no_plugin_match(self, mock_plugin, tmp_path):
        """Test indexing file with no matching plugin."""
        dispatcher = Dispatcher([mock_plugin])

        test_file = tmp_path / "test.unknown"
        test_file.write_text("unknown content")

        mock_plugin.supports.return_value = False

        # Should not raise, just log debug
        ctx = _make_repo_ctx()
        dispatcher.index_file(ctx, test_file)

        mock_plugin.indexFile.assert_not_called()

    def test_index_file_plugin_error(self, mock_plugin, tmp_path):
        """Test indexing when plugin raises error."""
        dispatcher = Dispatcher([mock_plugin])

        test_file = tmp_path / "test.py"
        test_file.write_text("def hello(): pass")

        mock_plugin.supports.return_value = True
        mock_plugin.indexFile.side_effect = Exception("Plugin error")

        # Should not raise, just log error
        ctx = _make_repo_ctx()
        dispatcher.index_file(ctx, test_file)

        # File should not be cached on error
        assert str(test_file) not in dispatcher._file_cache

    def test_index_file_skip_cached(self, mock_plugin, tmp_path):
        """Test that cached files are skipped."""
        dispatcher = Dispatcher([mock_plugin], use_plugin_factory=False, lazy_load=False)

        test_file = tmp_path / "test.py"
        content = "def hello(): pass"
        test_file.write_text(content)

        # Pre-populate cache
        stat = test_file.stat()
        dispatcher._file_cache[str(test_file)] = (
            stat.st_mtime,
            stat.st_size,
            dispatcher._get_file_hash(content),
        )

        mock_plugin.supports.return_value = True

        ctx = _make_repo_ctx()
        dispatcher.index_file(ctx, test_file)

        # Should not call plugin for cached file
        mock_plugin.indexFile.assert_not_called()


class TestStatistics:
    """Test statistics gathering."""

    def test_get_statistics_empty(self, mock_plugin):
        """Test statistics with no indexed files."""
        ctx = _make_repo_ctx()
        dispatcher = Dispatcher([mock_plugin])

        stats = dispatcher.get_statistics(ctx)

        assert stats["total"] == 0
        assert stats["by_language"] == {}

    def test_get_statistics_with_files(self):
        """Test statistics with indexed files."""
        py_plugin = Mock(spec=IPlugin, lang="python")
        js_plugin = Mock(spec=IPlugin, lang="javascript")

        ctx = _make_repo_ctx()
        dispatcher = Dispatcher([py_plugin, js_plugin])

        # Simulate cached files
        dispatcher._file_cache = {
            "/test/file1.py": (1000, 100, "hash1"),
            "/test/file2.py": (1001, 200, "hash2"),
            "/test/app.js": (1002, 300, "hash3"),
        }

        # Configure plugin supports
        py_plugin.supports.side_effect = lambda p: p.suffix == ".py"
        js_plugin.supports.side_effect = lambda p: p.suffix == ".js"

        stats = dispatcher.get_statistics(ctx)

        assert stats["total"] == 3
        assert stats["by_language"]["python"] == 2
        assert stats["by_language"]["javascript"] == 1

    def test_get_statistics_plugin_error(self, mock_plugin):
        """Test statistics when plugin.supports raises error."""
        ctx = _make_repo_ctx()
        dispatcher = Dispatcher([mock_plugin])
        dispatcher._file_cache = {"/test/file.py": (1000, 100, "hash")}

        mock_plugin.supports.side_effect = Exception("Plugin error")

        stats = dispatcher.get_statistics(ctx)

        # Should handle error gracefully
        assert stats["total"] == 0
        assert stats["by_language"] == {}


class TestConcurrency:
    """Test concurrent operations."""

    def test_concurrent_indexing(self, mock_plugin, tmp_path):
        """Test concurrent file indexing."""
        import concurrent.futures

        dispatcher = Dispatcher([mock_plugin], use_plugin_factory=False, lazy_load=False)
        mock_plugin.supports.return_value = True
        mock_plugin.indexFile.return_value = {"symbols": []}

        # Create multiple test files
        files = []
        for i in range(10):
            test_file = tmp_path / f"test{i}.py"
            test_file.write_text(f"def func{i}(): pass")
            files.append(test_file)

        ctx = _make_repo_ctx()
        # Index files concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(dispatcher.index_file, ctx, f) for f in files]
            concurrent.futures.wait(futures)

        # All files should be cached
        assert len(dispatcher._file_cache) == 10
        assert mock_plugin.indexFile.call_count == 10

    def test_concurrent_search(self, mock_plugin):
        """Test concurrent search operations (plugin fallback path, no sqlite)."""
        import concurrent.futures
        from pathlib import Path
        from unittest.mock import MagicMock as _MM

        from mcp_server.core.repo_context import RepoContext
        from mcp_server.storage.multi_repo_manager import RepositoryInfo

        _REPO_ID = "test-repo"
        psr = _make_psr_with_plugins(_REPO_ID, [mock_plugin])
        dispatcher = Dispatcher([mock_plugin], plugin_set_registry=psr)
        mock_plugin.search.return_value = [
            SearchResult(name="result", kind="function", path="/test.py", score=1.0)
        ]

        reg = _MM(spec=RepositoryInfo)
        reg.tracked_branch = "main"
        ctx = RepoContext(
            repo_id=_REPO_ID,
            sqlite_store=None,
            workspace_root=Path("/tmp/test"),
            tracked_branch="main",
            registry_entry=reg,
        )

        def search_task(query):
            return list(dispatcher.search(ctx, query))

        # Perform concurrent searches
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(search_task, f"query{i}") for i in range(20)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # All searches should complete
        assert len(results) == 20
        assert all(len(r) == 1 for r in results)
        assert mock_plugin.search.call_count == 20


class TestPerformance:
    """Performance benchmarks for dispatcher operations."""

    @pytest.mark.benchmark
    def test_lookup_performance(self, benchmark_results):
        """Benchmark first-hit fallback lookup performance (IF-0-P11-1)."""
        from mcp_server.dispatcher.fallback import run_gated_fallback

        # Create five mock plugins; only the last returns the target symbol
        plugins = []
        for i in range(5):
            plugin = Mock(spec=IPlugin, lang=f"lang{i}")
            plugin.getDefinition.return_value = None
            plugins.append(plugin)

        # Last plugin has the symbol
        plugins[-1].getDefinition.return_value = SymbolDef(
            name="target", kind="function", path="/found.py", line=1
        )

        with measure_time("dispatcher_lookup", benchmark_results):
            for _ in range(1000):
                result = run_gated_fallback(plugins, "target", source_ext=".py", timeout_ms=1000)
                assert result is not None

    @pytest.mark.benchmark
    def test_cache_performance(self, benchmark_results, tmp_path):
        """Benchmark cache hit performance."""
        dispatcher = Dispatcher([])

        # Create test files with cached entries
        for i in range(100):
            path = tmp_path / f"file{i}.py"
            content = f"def func{i}(): pass"
            path.write_text(content)

            # Pre-populate cache
            stat = path.stat()
            dispatcher._file_cache[str(path)] = (
                stat.st_mtime,
                stat.st_size,
                dispatcher._get_file_hash(content),
            )

        # Benchmark cache lookups
        paths = list(tmp_path.glob("*.py"))

        with measure_time("dispatcher_cache_check", benchmark_results):
            for _ in range(10):
                for path in paths:
                    content = path.read_text()
                    should_index = dispatcher._should_reindex(path, content)
                    assert not should_index  # All should be cached


class TestQueryIntent:
    """Unit tests for the query intent classifier."""

    def test_class_prefix(self):
        intent, name, kind = classify("class SemanticIndexer")
        assert intent == QueryIntent.SYMBOL
        assert name == "SemanticIndexer"
        assert kind == "class"

    def test_def_prefix(self):
        intent, name, kind = classify("def rerank")
        assert intent == QueryIntent.SYMBOL
        assert name == "rerank"
        assert kind == "function"

    def test_function_prefix(self):
        intent, name, kind = classify("function myHandler")
        assert intent == QueryIntent.SYMBOL
        assert name == "myHandler"
        assert kind == "function"

    def test_camelcase_single_token(self):
        intent, name, kind = classify("EnhancedDispatcher")
        assert intent == QueryIntent.SYMBOL
        assert name == "EnhancedDispatcher"
        assert kind == "class"

    def test_snake_case_single_token(self):
        intent, name, kind = classify("search_symbols")
        assert intent == QueryIntent.SYMBOL
        assert name == "search_symbols"

    def test_dotted_name(self):
        intent, name, kind = classify("SQLiteStore.get_symbol")
        assert intent == QueryIntent.SYMBOL
        assert name == "get_symbol"

    def test_multiword_is_lexical(self):
        intent, name, kind = classify("semantic preflight")
        assert intent == QueryIntent.LEXICAL

    def test_natural_language_is_lexical(self):
        intent, _, _ = classify("where is qdrant autostart implemented")
        assert intent == QueryIntent.LEXICAL

    def test_qdrant_docker_is_lexical(self):
        intent, _, _ = classify("qdrant docker compose autostart")
        assert intent == QueryIntent.LEXICAL

    def test_empty_is_lexical(self):
        intent, _, _ = classify("")
        assert intent == QueryIntent.LEXICAL

    def test_case_insensitive_prefix(self):
        intent, name, kind = classify("Class MyModel")
        assert intent == QueryIntent.SYMBOL
        assert name == "MyModel"
        assert kind == "class"


class TestSymbolRouting:
    """Tests for _symbol_route and its integration into search()."""

    def setup_method(self):
        import os

        # .env.native has MCP_ENABLE_MULTI_REPO=true with stale /workspaces paths.
        # Force it off so dispatcher init doesn't try to create that directory.
        os.environ["MCP_ENABLE_MULTI_REPO"] = "false"

    def _make_store(self, symbol_rows):
        """Return a mock SQLiteStore whose get_symbol returns symbol_rows."""
        store = MagicMock()
        store.get_symbol.return_value = symbol_rows
        return store

    def _make_dispatcher_with_ctx(self, store):
        d = Dispatcher([])
        ctx = _make_repo_ctx(store)
        return d, ctx

    def test_symbol_route_returns_definition_file(self):
        store = self._make_store(
            [
                {
                    "name": "SemanticIndexer",
                    "kind": "class",
                    "line_start": 42,
                    "line_end": 120,
                    "signature": "class SemanticIndexer:",
                    "documentation": None,
                    "file_path": "mcp_server/utils/semantic_indexer.py",
                }
            ]
        )
        d, ctx = self._make_dispatcher_with_ctx(store)
        results = d._symbol_route(store, "SemanticIndexer", "class", 5)
        assert len(results) == 1
        assert results[0]["file"] == "mcp_server/utils/semantic_indexer.py"
        assert results[0]["line"] == 42
        assert results[0]["symbol"] == "SemanticIndexer"

    def test_symbol_route_prefers_non_init_file(self):
        """__init__.py re-export should sort after the definition file."""
        store = self._make_store(
            [
                {
                    "name": "SemanticIndexer",
                    "kind": "class",
                    "line_start": 1,
                    "line_end": 1,
                    "signature": "from .semantic_indexer import SemanticIndexer",
                    "documentation": None,
                    "file_path": "mcp_server/utils/__init__.py",
                },
                {
                    "name": "SemanticIndexer",
                    "kind": "class",
                    "line_start": 42,
                    "line_end": 120,
                    "signature": "class SemanticIndexer:",
                    "documentation": None,
                    "file_path": "mcp_server/utils/semantic_indexer.py",
                },
            ]
        )
        d, ctx = self._make_dispatcher_with_ctx(store)
        results = d._symbol_route(store, "SemanticIndexer", "class", 5)
        assert results[0]["file"] == "mcp_server/utils/semantic_indexer.py"
        assert results[1]["file"] == "mcp_server/utils/__init__.py"

    def test_symbol_route_empty_when_not_found(self):
        store = self._make_store([])
        # Both strict and relaxed calls return empty
        store.get_symbol.return_value = []
        d, ctx = self._make_dispatcher_with_ctx(store)
        results = d._symbol_route(store, "NonExistentSymbol", "class", 5)
        assert results == []

    def test_symbol_route_relaxes_kind_on_miss(self):
        """If kind-restricted lookup returns nothing, retry without kind."""
        store = MagicMock()
        store.get_symbol.side_effect = [
            [],  # first call (with kind) → empty
            [
                {
                    "name": "rerank",
                    "kind": "method",
                    "line_start": 10,
                    "line_end": 20,
                    "signature": "def rerank()",
                    "documentation": None,
                    "file_path": "mcp_server/indexer/reranker.py",
                }
            ],
        ]
        d, ctx = self._make_dispatcher_with_ctx(store)
        results = d._symbol_route(store, "rerank", "class", 5)
        assert len(results) == 1
        assert "reranker.py" in results[0]["file"]

    def test_search_routes_class_query_to_symbols(self):
        """search('class SemanticIndexer') should hit symbol table, not BM25."""
        store = MagicMock()
        store.get_symbol.return_value = [
            {
                "name": "SemanticIndexer",
                "kind": "class",
                "line_start": 42,
                "line_end": 120,
                "signature": "class SemanticIndexer:",
                "documentation": None,
                "file_path": "mcp_server/utils/semantic_indexer.py",
            }
        ]
        d, ctx = self._make_dispatcher_with_ctx(store)
        results = list(d.search(ctx, "class SemanticIndexer", limit=5))
        assert len(results) >= 1
        assert results[0]["file"] == "mcp_server/utils/semantic_indexer.py"
        # BM25 (search_bm25) should NOT have been called
        store.search_bm25.assert_not_called()

    def test_search_falls_back_to_bm25_when_symbol_not_found(self):
        """When symbols table has no match, BM25 path should still run."""
        store = MagicMock()
        store.get_symbol.return_value = []
        store.search_bm25.return_value = []  # BM25 also returns nothing
        d, ctx = self._make_dispatcher_with_ctx(store)
        list(d.search(ctx, "class SemanticIndexer", limit=5))
        # BM25 was attempted as fallback
        store.search_bm25.assert_called()

    def test_multiword_query_skips_symbol_route(self):
        """Multi-word lexical queries must NOT hit the symbol table."""
        store = MagicMock()
        store.search_bm25.return_value = []
        d, ctx = self._make_dispatcher_with_ctx(store)
        list(d.search(ctx, "qdrant docker compose autostart", limit=5))
        store.get_symbol.assert_not_called()


# ---------------------------------------------------------------------------
# SL-1.1 — Protocol-conformance tests (initially RED; green after SL-1.2 impl)
# ---------------------------------------------------------------------------


def _make_repo_ctx(sqlite_store=None) -> RepoContext:
    """Build a minimal RepoContext for tests."""
    from pathlib import Path
    from unittest.mock import MagicMock

    from mcp_server.storage.multi_repo_manager import RepositoryInfo

    if sqlite_store is None:
        sqlite_store = MagicMock()

    registry_entry = MagicMock(spec=RepositoryInfo)
    registry_entry.tracked_branch = "main"
    registry_entry.path = Path("/tmp/test-repo")

    return RepoContext(
        repo_id="test-repo-id-0001",
        sqlite_store=sqlite_store,
        workspace_root=Path("/tmp/test-repo"),
        tracked_branch="main",
        registry_entry=registry_entry,
    )


class TestEnhancedDispatcherProtocolConformance:
    """EnhancedDispatcher must conform to DispatcherProtocol (SL-1.1)."""

    def test_isinstance_dispatcher_protocol(self):
        """runtime_checkable isinstance check must pass."""
        d = Dispatcher([])
        assert isinstance(d, DispatcherProtocol)

    def test_ctor_rejects_sqlite_store_kwarg(self):
        """EnhancedDispatcher() must raise TypeError when sqlite_store= is passed."""
        with pytest.raises(TypeError):
            Dispatcher(sqlite_store=MagicMock())

    def test_lookup_accepts_ctx_first_arg(self):
        """lookup(ctx, symbol) must route through ctx.sqlite_store."""
        store = MagicMock()
        store.get_symbol.return_value = []
        ctx = _make_repo_ctx(store)
        d = Dispatcher([])
        # Should not raise; returns None when nothing found
        result = d.lookup(ctx, "nonexistent_symbol_xyz")
        assert result is None

    def test_search_accepts_ctx_first_arg(self):
        """search(ctx, query) must not raise and must use ctx.sqlite_store."""
        store = MagicMock()
        store.search_bm25.return_value = []
        ctx = _make_repo_ctx(store)
        d = Dispatcher([])
        results = list(d.search(ctx, "test query"))
        assert isinstance(results, list)

    def test_search_uses_ctx_sqlite_store_not_instance_store(self):
        """search must consult ctx.sqlite_store, not a captured self._sqlite_store."""
        store_a = MagicMock()
        store_a.search_bm25.return_value = [
            {"filepath": "/repo_a/file.py", "snippet": "hello", "score": 1.0, "language": "python"}
        ]
        store_a.find_best_chunk_for_file = MagicMock(return_value=None)
        ctx_a = _make_repo_ctx(store_a)

        store_b = MagicMock()
        store_b.search_bm25.return_value = []
        ctx_b = _make_repo_ctx(store_b)

        d = Dispatcher([])
        # Search via ctx_a should use store_a
        list(d.search(ctx_a, "hello"))
        store_a.search_bm25.assert_called()
        # store_b was never accessed
        store_b.search_bm25.assert_not_called()

        # Search via ctx_b should use store_b (not store_a again)
        list(d.search(ctx_b, "hello"))
        store_b.search_bm25.assert_called()

    def test_health_check_accepts_ctx(self):
        """health_check(ctx) must accept ctx and return a dict."""
        ctx = _make_repo_ctx()
        d = Dispatcher([])
        result = d.health_check(ctx)
        assert isinstance(result, dict)
        assert "status" in result

    def test_get_statistics_accepts_ctx(self):
        """get_statistics(ctx) must accept ctx and return a dict."""
        ctx = _make_repo_ctx()
        d = Dispatcher([])
        result = d.get_statistics(ctx)
        assert isinstance(result, dict)

    def test_index_file_accepts_ctx(self, tmp_path):
        """index_file(ctx, path) must accept ctx as first positional arg."""
        ctx = _make_repo_ctx()
        d = Dispatcher([])
        f = tmp_path / "test.py"
        f.write_text("x = 1")
        result = d.index_file(ctx, f)
        assert result.status == IndexResultStatus.INDEXED

    def test_index_directory_accepts_ctx(self, tmp_path):
        """index_directory(ctx, path) must accept ctx and return a dict."""
        ctx = _make_repo_ctx()
        d = Dispatcher([])
        result = d.index_directory(ctx, tmp_path)
        assert isinstance(result, dict)

    def test_index_directory_treats_unsupported_plugin_files_as_ignored(self, tmp_path):
        ctx = _make_repo_ctx()
        target = tmp_path / "data.json"
        target.write_text('{"ok": true}\n')

        result = Dispatcher([]).index_directory(ctx, tmp_path)

        assert result["failed_files"] == 0
        assert result["ignored_files"] == 1

    def test_index_directory_runs_lexical_then_summaries_then_semantic(self, tmp_path, monkeypatch):
        events = []
        ctx = _make_repo_ctx(sqlite_store=MagicMock(db_path=str(tmp_path / "index.db")))
        target = tmp_path / "sample.py"
        target.write_text("x = 1\n")

        class FakeWriter:
            def __init__(self, *args, **kwargs):
                pass

            async def process_scope(self, **kwargs):
                events.append(("summary", sorted(str(path) for path in kwargs["target_paths"])))
                return SimpleNamespace(
                    summaries_written=1,
                    chunks_attempted=1,
                    authoritative_chunks=1,
                    missing_chunk_ids=[],
                    files_attempted=1,
                    files_summarized=1,
                )

        class FakeSemanticIndexer:
            def index_files_batch(self, paths, **kwargs):
                events.append(("semantic", [str(path) for path in paths], kwargs))
                return {"files_indexed": 1, "files_failed": 0, "files_skipped": 0}

        remaining_counts = [1, 0]

        monkeypatch.setattr(
            "mcp_server.indexing.summarization.ComprehensiveChunkWriter",
            FakeWriter,
        )
        monkeypatch.setattr(
            "mcp_server.setup.semantic_preflight.run_semantic_preflight",
            lambda **_kwargs: SimpleNamespace(
                to_dict=lambda: {"can_write_semantic_vectors": True, "blocker": None}
            ),
        )
        monkeypatch.setattr(
            Dispatcher,
            "_get_semantic_indexer",
            lambda self, _ctx: FakeSemanticIndexer(),
        )
        monkeypatch.setattr(
            Dispatcher,
            "_count_missing_summaries_for_paths",
            lambda self, _ctx, _paths: 0 if events and events[-1][0] == "summary" else 1,
        )

        def _fake_index_file(self, _ctx, path, do_semantic=False):
            events.append(("lexical", str(path), do_semantic))
            return IndexResult(
                status=IndexResultStatus.INDEXED,
                path=path,
                observed_hash=None,
                actual_hash=None,
            )

        monkeypatch.setattr(Dispatcher, "index_file", _fake_index_file)

        result = Dispatcher([]).index_directory(ctx, tmp_path)

        assert [event[0] for event in events] == ["lexical", "summary", "semantic"]
        assert result["semantic_stage"] == "indexed"

    def test_index_directory_blocks_semantic_stage_when_summaries_missing(
        self, tmp_path, monkeypatch
    ):
        ctx = _make_repo_ctx(sqlite_store=MagicMock(db_path=str(tmp_path / "index.db")))
        target = tmp_path / "sample.py"
        target.write_text("x = 1\n")

        class FakeWriter:
            def __init__(self, *args, **kwargs):
                pass

            async def process_scope(self, **kwargs):
                return SimpleNamespace(
                    summaries_written=0,
                    chunks_attempted=1,
                    authoritative_chunks=0,
                    missing_chunk_ids=["chunk-1"],
                    files_attempted=1,
                    files_summarized=0,
                )

        semantic_called = {"value": False}

        class FakeSemanticIndexer:
            def index_files_batch(self, paths, **kwargs):
                semantic_called["value"] = True
                return {"files_indexed": 0, "files_failed": 0, "files_skipped": 0}

        monkeypatch.setattr(
            "mcp_server.indexing.summarization.ComprehensiveChunkWriter",
            FakeWriter,
        )
        monkeypatch.setattr(
            "mcp_server.setup.semantic_preflight.run_semantic_preflight",
            lambda **_kwargs: SimpleNamespace(
                to_dict=lambda: {"can_write_semantic_vectors": True, "blocker": None}
            ),
        )
        monkeypatch.setattr(
            Dispatcher,
            "_get_semantic_indexer",
            lambda self, _ctx: FakeSemanticIndexer(),
        )
        monkeypatch.setattr(
            Dispatcher,
            "_count_missing_summaries_for_paths",
            lambda self, _ctx, _paths: 1,
        )
        monkeypatch.setattr(
            Dispatcher,
            "index_file",
            lambda self, _ctx, path, do_semantic=False: IndexResult(
                status=IndexResultStatus.INDEXED,
                path=path,
                observed_hash=None,
                actual_hash=None,
            ),
        )

        result = Dispatcher([]).index_directory(ctx, tmp_path)

        assert semantic_called["value"] is False
        assert result["semantic_stage"] == "blocked_missing_summaries"
        assert result["semantic_blocked"] == 1

    def test_index_directory_retries_summary_generation_until_scope_is_drained(
        self, tmp_path, monkeypatch
    ):
        summary_limits = []
        ctx = _make_repo_ctx(sqlite_store=MagicMock(db_path=str(tmp_path / "index.db")))
        target = tmp_path / "sample.py"
        target.write_text("x = 1\n")

        class FakeWriter:
            call_count = 0

            def __init__(self, *args, **kwargs):
                pass

            async def process_scope(self, **kwargs):
                FakeWriter.call_count += 1
                summary_limits.append(kwargs["limit"])
                if FakeWriter.call_count == 1:
                    return SimpleNamespace(
                        summaries_written=1,
                        chunks_attempted=1,
                        authoritative_chunks=1,
                        missing_chunk_ids=[],
                        files_attempted=1,
                        files_summarized=1,
                    )
                return SimpleNamespace(
                    summaries_written=1,
                    chunks_attempted=1,
                    authoritative_chunks=1,
                    missing_chunk_ids=[],
                    files_attempted=1,
                    files_summarized=1,
                )

        class FakeSemanticIndexer:
            def index_files_batch(self, paths, **kwargs):
                return {"files_indexed": 1, "files_failed": 0, "files_skipped": 0}

        unresolved = [{"remaining": 2}, {"remaining": 1}, {"remaining": 0}]

        monkeypatch.setattr(
            "mcp_server.indexing.summarization.ComprehensiveChunkWriter",
            FakeWriter,
        )
        monkeypatch.setattr(
            "mcp_server.setup.semantic_preflight.run_semantic_preflight",
            lambda **_kwargs: SimpleNamespace(
                to_dict=lambda: {"can_write_semantic_vectors": True, "blocker": None}
            ),
        )
        monkeypatch.setattr(
            Dispatcher,
            "_get_semantic_indexer",
            lambda self, _ctx: FakeSemanticIndexer(),
        )
        monkeypatch.setattr(
            Dispatcher,
            "_count_missing_summaries_for_paths",
            lambda self, _ctx, _paths: remaining_counts.pop(0),
        )
        monkeypatch.setattr(
            Dispatcher,
            "index_file",
            lambda self, _ctx, path, do_semantic=False: IndexResult(
                status=IndexResultStatus.INDEXED,
                path=path,
                observed_hash=None,
                actual_hash=None,
            ),
        )
        monkeypatch.setattr(
            Dispatcher,
            "_count_missing_summaries_for_paths",
            lambda self, _ctx, _paths: unresolved.pop(0)["remaining"],
        )

        result = Dispatcher([]).index_directory(ctx, tmp_path)

        assert result["semantic_stage"] == "indexed"
        assert result["summaries_written"] == 2
        assert result["summary_chunks_attempted"] == 2
        assert summary_limits == [10000, 10000]

    def test_index_directory_blocks_when_summary_progress_plateaus(
        self, tmp_path, monkeypatch
    ):
        ctx = _make_repo_ctx(sqlite_store=MagicMock(db_path=str(tmp_path / "index.db")))
        target = tmp_path / "sample.py"
        target.write_text("x = 1\n")

        class FakeWriter:
            def __init__(self, *args, **kwargs):
                pass

            async def process_scope(self, **kwargs):
                return SimpleNamespace(
                    summaries_written=1,
                    chunks_attempted=1,
                    authoritative_chunks=1,
                    missing_chunk_ids=["chunk-1"],
                    files_attempted=1,
                    files_summarized=1,
                )

        semantic_called = {"value": False}

        class FakeSemanticIndexer:
            def index_files_batch(self, paths, **kwargs):
                semantic_called["value"] = True
                return {"files_indexed": 1, "files_failed": 0, "files_skipped": 0}

        unresolved = [{"remaining": 2}, {"remaining": 2}, {"remaining": 2}]

        monkeypatch.setattr(
            "mcp_server.indexing.summarization.ComprehensiveChunkWriter",
            FakeWriter,
        )
        monkeypatch.setattr(
            "mcp_server.setup.semantic_preflight.run_semantic_preflight",
            lambda **_kwargs: SimpleNamespace(
                to_dict=lambda: {"can_write_semantic_vectors": True, "blocker": None}
            ),
        )
        monkeypatch.setattr(
            Dispatcher,
            "_get_semantic_indexer",
            lambda self, _ctx: FakeSemanticIndexer(),
        )
        monkeypatch.setattr(
            Dispatcher,
            "_count_missing_summaries_for_paths",
            lambda self, _ctx, _paths: unresolved.pop(0)["remaining"],
        )
        monkeypatch.setattr(
            Dispatcher,
            "index_file",
            lambda self, _ctx, path, do_semantic=False: IndexResult(
                status=IndexResultStatus.INDEXED,
                path=path,
                observed_hash=None,
                actual_hash=None,
            ),
        )

        result = Dispatcher([]).index_directory(ctx, tmp_path)

        assert semantic_called["value"] is False
        assert result["semantic_stage"] == "blocked_summary_plateau"
        assert result["semantic_blocked"] == 1
        assert result["summary_missing_chunks"] == 2
        assert result["summary_passes"] == 2

    def test_index_directory_bootstraps_missing_collection_before_semantic_writes(
        self, tmp_path, monkeypatch
    ):
        events = []
        ctx = _make_repo_ctx(sqlite_store=MagicMock(db_path=str(tmp_path / "index.db")))
        target = tmp_path / "sample.py"
        target.write_text("x = 1\n")

        class FakeWriter:
            def __init__(self, *args, **kwargs):
                pass

            async def process_scope(self, **kwargs):
                return SimpleNamespace(
                    summaries_written=1,
                    chunks_attempted=1,
                    authoritative_chunks=1,
                    missing_chunk_ids=[],
                    files_attempted=1,
                    files_summarized=1,
                )

        preflight_calls = {"count": 0}

        def _fake_preflight(**_kwargs):
            preflight_calls["count"] += 1
            if preflight_calls["count"] == 1:
                payload = {
                    "overall_ready": False,
                    "can_write_semantic_vectors": False,
                    "blocker": {
                        "code": "collection_missing",
                        "message": "Qdrant collection is missing for the active semantic profile",
                    },
                    "effective_config": {
                        "selected_profile": "oss_high",
                        "collection_name": "code_index__oss_high__v1",
                        "normalized_collection_name": "code_index__oss_high__v1",
                        "qdrant_url": "http://localhost:6333",
                        "vector_dimension": 4096,
                        "distance_metric": "cosine",
                    },
                }
            else:
                payload = {
                    "overall_ready": True,
                    "can_write_semantic_vectors": True,
                    "blocker": None,
                    "effective_config": {
                        "selected_profile": "oss_high",
                        "collection_name": "code_index__oss_high__v1",
                        "normalized_collection_name": "code_index__oss_high__v1",
                        "qdrant_url": "http://localhost:6333",
                        "vector_dimension": 4096,
                        "distance_metric": "cosine",
                    },
                }
            return SimpleNamespace(to_dict=lambda: payload)

        class FakeSemanticIndexer:
            def index_files_batch(self, paths, **kwargs):
                events.append(("semantic", [str(path) for path in paths], kwargs))
                return {"files_indexed": 1, "files_failed": 0, "files_skipped": 0}

        monkeypatch.setattr(
            "mcp_server.indexing.summarization.ComprehensiveChunkWriter",
            FakeWriter,
        )
        monkeypatch.setattr(
            "mcp_server.setup.semantic_preflight.run_semantic_preflight",
            _fake_preflight,
        )
        monkeypatch.setattr(
            "mcp_server.setup.semantic_preflight.bootstrap_active_profile_collection",
            lambda **_kwargs: SimpleNamespace(
                to_dict=lambda: {"status": "created", "message": "created"},
                status="created",
                message="created",
            ),
        )
        monkeypatch.setattr(
            Dispatcher,
            "_get_semantic_indexer",
            lambda self, _ctx: FakeSemanticIndexer(),
        )
        monkeypatch.setattr(
            Dispatcher,
            "_count_missing_summaries_for_paths",
            lambda self, _ctx, _paths: remaining.pop(0),
        )
        monkeypatch.setattr(
            Dispatcher,
            "index_file",
            lambda self, _ctx, path, do_semantic=False: IndexResult(
                status=IndexResultStatus.INDEXED,
                path=path,
                observed_hash=None,
                actual_hash=None,
            ),
        )

        remaining = [1, 0]

        result = Dispatcher([]).index_directory(ctx, tmp_path)

        assert preflight_calls["count"] == 2
        assert result["semantic_stage"] == "indexed"
        assert result["semantic_collection_bootstrap"]["status"] == "created"

    def test_index_directory_records_semantic_batch_blockers(
        self, tmp_path, monkeypatch
    ):
        ctx = _make_repo_ctx(sqlite_store=MagicMock(db_path=str(tmp_path / "index.db")))
        target = tmp_path / "sample.py"
        target.write_text("x = 1\n")

        class FakeWriter:
            def __init__(self, *args, **kwargs):
                pass

            async def process_scope(self, **kwargs):
                return SimpleNamespace(
                    summaries_written=1,
                    chunks_attempted=1,
                    authoritative_chunks=1,
                    missing_chunk_ids=[],
                    files_attempted=1,
                    files_summarized=1,
                )

        class FakeSemanticIndexer:
            def index_files_batch(self, paths, **kwargs):
                return {
                    "files_indexed": 0,
                    "files_failed": 0,
                    "files_skipped": 0,
                    "files_blocked": 1,
                    "semantic_blocker": {
                        "code": "semantic_batch_blocked",
                        "message": "Semantic batch writes were blocked after summaries were generated",
                    },
                    "semantic_error": "Semantic batch writes were blocked after summaries were generated",
                }

        monkeypatch.setattr(
            "mcp_server.indexing.summarization.ComprehensiveChunkWriter",
            FakeWriter,
        )
        monkeypatch.setattr(
            "mcp_server.setup.semantic_preflight.run_semantic_preflight",
            lambda **_kwargs: SimpleNamespace(
                to_dict=lambda: {"can_write_semantic_vectors": True, "blocker": None}
            ),
        )
        monkeypatch.setattr(
            Dispatcher,
            "_get_semantic_indexer",
            lambda self, _ctx: FakeSemanticIndexer(),
        )
        monkeypatch.setattr(
            Dispatcher,
            "_count_missing_summaries_for_paths",
            lambda self, _ctx, _paths: 0,
        )
        monkeypatch.setattr(
            Dispatcher,
            "index_file",
            lambda self, _ctx, path, do_semantic=False: IndexResult(
                status=IndexResultStatus.INDEXED,
                path=path,
                observed_hash=None,
                actual_hash=None,
            ),
        )

        result = Dispatcher([]).index_directory(ctx, tmp_path)

        assert result["semantic_stage"] == "blocked_semantic_batch"
        assert result["semantic_blocked"] == 1
        assert (
            result["semantic_error"]
            == "Semantic batch writes were blocked after summaries were generated"
        )

    def test_remove_file_accepts_ctx(self, tmp_path):
        """remove_file(ctx, path) must accept ctx as first positional arg."""
        ctx = _make_repo_ctx()
        d = Dispatcher([])
        f = tmp_path / "foo.py"
        f.write_text("x = 1")
        d.remove_file(ctx, f)  # must not raise

    def test_move_file_accepts_ctx(self, tmp_path):
        """move_file(ctx, old, new) must accept ctx as first positional arg."""
        ctx = _make_repo_ctx()
        d = Dispatcher([])
        d.move_file(ctx, tmp_path / "old.py", tmp_path / "new.py")  # must not raise

    def test_remove_file_uses_ctx_repository_row(self, tmp_path):
        """remove_file must delete from the repository row matching ctx root, not row 1."""
        from mcp_server.storage.sqlite_store import SQLiteStore

        repo_a = tmp_path / "repo-a"
        repo_b = tmp_path / "repo-b"
        repo_a.mkdir()
        repo_b.mkdir()
        target_a = repo_a / "same.py"
        target_b = repo_b / "same.py"
        target_a.write_text("a = 1\n")
        target_b.write_text("b = 1\n")

        store = SQLiteStore(str(tmp_path / "index.db"))
        row_a = store.ensure_repository_row(repo_a, name="a")
        row_b = store.ensure_repository_row(repo_b, name="b")
        store.store_file(repository_id=row_a, path=target_a, relative_path="same.py")
        store.store_file(repository_id=row_b, path=target_b, relative_path="same.py")

        ctx = _make_repo_ctx(store)
        ctx.registry_entry.path = repo_b
        ctx.registry_entry.name = "b"
        ctx = RepoContext(
            repo_id=ctx.repo_id,
            sqlite_store=store,
            workspace_root=repo_b,
            tracked_branch=ctx.tracked_branch,
            registry_entry=ctx.registry_entry,
        )

        result = Dispatcher([]).remove_file(ctx, target_b)

        assert result.status == IndexResultStatus.DELETED
        assert store.get_file_by_path("same.py", row_a) is not None
        assert store.get_file_by_path("same.py", row_b) is None

    def test_index_file_returns_not_found_for_missing_required_path(self, tmp_path):
        ctx = _make_repo_ctx()
        result = Dispatcher([]).index_file(ctx, tmp_path / "missing.py")

        assert result.status == IndexResultStatus.NOT_FOUND
        assert result.error == "file not found"

    def test_index_file_returns_explicit_plugin_failure(self, tmp_path):
        plugin = MagicMock(spec=IPlugin, lang="python")
        plugin.supports.return_value = True
        plugin.indexFile.side_effect = RuntimeError("plugin boom")
        dispatcher = Dispatcher([plugin])
        ctx = _make_repo_ctx()
        target = tmp_path / "test.py"
        target.write_text("x = 1\n")

        result = dispatcher.index_file(ctx, target)

        assert result.status == IndexResultStatus.ERROR
        assert result.error == "plugin boom"

    def test_index_file_persists_plugin_shard_to_ctx_sqlite_store(self, tmp_path):
        from mcp_server.storage.sqlite_store import SQLiteStore

        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        target = repo_root / "sample.py"
        target.write_text("def persisted():\n    return 1\n")
        store = SQLiteStore(str(tmp_path / "index.db"))

        plugin = MagicMock(spec=IPlugin, lang="python")
        plugin.language = "python"
        plugin.supports.return_value = True
        plugin.indexFile.return_value = {
            "file": str(target),
            "language": "python",
            "symbols": [
                {
                    "symbol": "persisted",
                    "kind": "function",
                    "line": 1,
                    "span": [1, 2],
                    "signature": "def persisted():",
                }
            ],
        }
        ctx = _make_repo_ctx(store)
        ctx.registry_entry.path = repo_root
        ctx.registry_entry.name = "repo"
        ctx = RepoContext(
            repo_id=ctx.repo_id,
            sqlite_store=store,
            workspace_root=repo_root,
            tracked_branch=ctx.tracked_branch,
            registry_entry=ctx.registry_entry,
        )

        result = Dispatcher([plugin]).index_file(ctx, target)

        repo_row = store.ensure_repository_row(repo_root, name="repo")
        file_row = store.get_file_by_path("sample.py", repo_row)
        assert result.status == IndexResultStatus.INDEXED
        assert file_row is not None
        assert store.get_symbol("persisted")[0]["file_id"] == file_row["id"]

    def test_index_file_returns_skipped_unchanged_when_cache_matches(self, tmp_path):
        plugin = MagicMock(spec=IPlugin, lang="python")
        plugin.supports.return_value = True
        plugin.indexFile.return_value = {"symbols": []}
        dispatcher = Dispatcher([plugin])
        ctx = _make_repo_ctx()
        target = tmp_path / "test.py"
        target.write_text("x = 1\n")

        first = dispatcher.index_file(ctx, target)
        second = dispatcher.index_file(ctx, target)

        assert first.status == IndexResultStatus.INDEXED
        assert second.status == IndexResultStatus.SKIPPED_UNCHANGED

    def test_remove_file_returns_not_found_when_repo_row_missing(self, tmp_path):
        from mcp_server.storage.sqlite_store import SQLiteStore

        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        target = repo_root / "missing.py"
        target.write_text("x = 1\n")
        store = SQLiteStore(str(tmp_path / "index.db"))
        store.ensure_repository_row(repo_root, name="repo")
        ctx = _make_repo_ctx(store)
        ctx.registry_entry.path = repo_root
        ctx.registry_entry.name = "repo"
        ctx = RepoContext(
            repo_id=ctx.repo_id,
            sqlite_store=store,
            workspace_root=repo_root,
            tracked_branch=ctx.tracked_branch,
            registry_entry=ctx.registry_entry,
        )

        result = Dispatcher([]).remove_file(ctx, target)

        assert result.status == IndexResultStatus.NOT_FOUND

    def test_runtime_feature_status_registered_semantic_unavailable_without_fallback(self):
        ctx = _make_repo_ctx(MagicMock())
        ctx.registry_entry.path = ctx.workspace_root
        d = Dispatcher([])
        d._semantic_registry = None
        d._semantic_indexer_fallback = object()

        status = d.get_runtime_feature_status(ctx)

        assert status["semantic"]["status"] == "unavailable"
        assert status["semantic"]["reason"] == "semantic_registry_unavailable"

    def test_plugins_takes_no_ctx(self):
        """plugins() is process-global; must accept no ctx arg."""
        d = Dispatcher([])
        result = d.plugins()
        assert isinstance(result, list)

    def test_supported_languages_takes_no_ctx(self):
        """supported_languages() is process-global; must accept no ctx arg."""
        d = Dispatcher([])
        result = d.supported_languages()
        assert isinstance(result, list)

    def test_get_plugins_for_file_accepts_ctx(self, tmp_path):
        """get_plugins_for_file(ctx, path) must accept ctx as first arg."""
        ctx = _make_repo_ctx()
        d = Dispatcher([])
        f = tmp_path / "test.py"
        result = d.get_plugins_for_file(ctx, f)
        assert isinstance(result, list)

    def test_search_scoped_to_ctx_repo_id(self):
        """Results from search(ctx_a, q) must not bleed store_b data."""
        store_a = MagicMock()
        store_a.search_bm25.return_value = [
            {"filepath": "/repo_a/x.py", "snippet": "foo", "score": 1.0, "language": "python"}
        ]
        store_a.find_best_chunk_for_file = MagicMock(return_value=None)

        store_b = MagicMock()
        store_b.search_bm25.return_value = [
            {"filepath": "/repo_b/y.py", "snippet": "foo", "score": 1.0, "language": "python"}
        ]

        ctx_a = _make_repo_ctx(store_a)
        d = Dispatcher([])
        list(d.search(ctx_a, "foo"))
        # store_b must never be touched
        store_b.search_bm25.assert_not_called()


class TestSimpleDispatcherProtocolConformance:
    """SimpleDispatcher must conform to the query subset of DispatcherProtocol (SL-1.1)."""

    def test_isinstance_dispatcher_protocol(self):
        """runtime_checkable isinstance check must pass for SimpleDispatcher."""
        d = SimpleDispatcher()
        assert isinstance(d, DispatcherProtocol)

    def test_ctor_rejects_sqlite_store_kwarg(self):
        """SimpleDispatcher() must raise TypeError when sqlite_store= is passed."""
        with pytest.raises(TypeError):
            SimpleDispatcher(sqlite_store=MagicMock())

    def test_search_accepts_ctx(self):
        """SimpleDispatcher.search(ctx, query) must accept ctx first positional arg."""
        store = MagicMock()
        store.search_bm25.return_value = []
        ctx = _make_repo_ctx(store)
        d = SimpleDispatcher()
        results = list(d.search(ctx, "hello"))
        assert isinstance(results, list)

    def test_health_check_accepts_ctx(self):
        """SimpleDispatcher.health_check(ctx) must accept ctx."""
        ctx = _make_repo_ctx()
        d = SimpleDispatcher()
        result = d.health_check(ctx)
        assert isinstance(result, dict)

    def test_get_statistics_accepts_ctx(self):
        """SimpleDispatcher.get_statistics(ctx) must accept ctx."""
        ctx = _make_repo_ctx()
        d = SimpleDispatcher()
        result = d.get_statistics(ctx)
        assert isinstance(result, dict)


class TestStorageCrossRepoCoordinatorDeleted:
    """mcp_server.storage.cross_repo_coordinator must be deleted (SL-1.1)."""

    def test_storage_cross_repo_import_raises(self):
        """Importing from mcp_server.storage.cross_repo_coordinator must raise ModuleNotFoundError."""
        import importlib
        import sys

        # Remove from sys.modules cache if already imported (pre-deletion)
        sys.modules.pop("mcp_server.storage.cross_repo_coordinator", None)
        with pytest.raises((ModuleNotFoundError, ImportError)):
            importlib.import_module("mcp_server.storage.cross_repo_coordinator")
