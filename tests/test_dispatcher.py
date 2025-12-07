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
from unittest.mock import Mock, patch

import pytest

from mcp_server.dispatcher import EnhancedDispatcher as Dispatcher
from mcp_server.plugin_base import IPlugin, SearchResult, SymbolDef


class TestDispatcherInitialization:
    """Test Dispatcher initialization and configuration."""

    def test_init_with_single_plugin(self, mock_plugin):
        """Test initialization with a single plugin."""
        dispatcher = Dispatcher([mock_plugin])

        assert len(dispatcher._plugins) == 1
        assert dispatcher._by_lang["mock"] == mock_plugin
        assert dispatcher._file_cache == {}

    def test_init_with_multiple_plugins(self):
        """Test initialization with multiple plugins."""
        plugin1 = Mock(spec=IPlugin, lang="python")
        plugin2 = Mock(spec=IPlugin, lang="javascript")
        plugin3 = Mock(spec=IPlugin, lang="java")

        dispatcher = Dispatcher([plugin1, plugin2, plugin3])

        assert len(dispatcher._plugins) == 3
        assert dispatcher._by_lang["python"] == plugin1
        assert dispatcher._by_lang["javascript"] == plugin2
        assert dispatcher._by_lang["java"] == plugin3

    def test_init_empty_plugins(self):
        """Test initialization with no plugins."""
        dispatcher = Dispatcher([])

        assert len(dispatcher._plugins) == 0
        assert dispatcher._by_lang == {}

    def test_plugins_property(self, mock_plugin):
        """Test the plugins property getter."""
        dispatcher = Dispatcher([mock_plugin])

        plugins = dispatcher.plugins
        assert plugins == {"mock": mock_plugin}


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
        py_plugin.supports.assert_called_once_with(Path("test.py"))
        js_plugin.supports.assert_called_once_with(Path("test.py"))

    def test_match_plugin_no_match(self, mock_plugin):
        """Test when no plugin matches the file."""
        mock_plugin.supports.return_value = False
        dispatcher = Dispatcher([mock_plugin])

        with pytest.raises(RuntimeError, match="No plugin for"):
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
    """Test symbol lookup functionality."""

    def test_lookup_found(self, mock_plugin):
        """Test successful symbol lookup."""
        expected_symbol = SymbolDef(name="test_func", kind="function", path="/test.py", line=10)
        mock_plugin.getDefinition.return_value = expected_symbol

        dispatcher = Dispatcher([mock_plugin])
        result = dispatcher.lookup("test_func")

        assert result == expected_symbol
        mock_plugin.getDefinition.assert_called_once_with("test_func")

    def test_lookup_not_found(self, mock_plugin):
        """Test symbol lookup when not found."""
        mock_plugin.getDefinition.return_value = None

        dispatcher = Dispatcher([mock_plugin])
        result = dispatcher.lookup("nonexistent")

        assert result is None
        mock_plugin.getDefinition.assert_called_once_with("nonexistent")

    def test_lookup_multiple_plugins(self):
        """Test lookup across multiple plugins."""
        plugin1 = Mock(spec=IPlugin, lang="python")
        plugin1.getDefinition.return_value = None

        expected_symbol = SymbolDef(name="found", kind="class", path="/found.js", line=5)
        plugin2 = Mock(spec=IPlugin, lang="javascript")
        plugin2.getDefinition.return_value = expected_symbol

        plugin3 = Mock(spec=IPlugin, lang="java")

        dispatcher = Dispatcher([plugin1, plugin2, plugin3])
        result = dispatcher.lookup("found")

        assert result == expected_symbol
        plugin1.getDefinition.assert_called_once_with("found")
        plugin2.getDefinition.assert_called_once_with("found")
        plugin3.getDefinition.assert_not_called()  # Stops after finding

    def test_lookup_plugin_error(self, mock_plugin):
        """Test lookup when plugin raises error."""
        mock_plugin.getDefinition.side_effect = Exception("Plugin error")

        dispatcher = Dispatcher([mock_plugin])

        # Should catch and continue (return None)
        with pytest.raises(Exception):
            dispatcher.lookup("test")


class TestSearch:
    """Test search functionality."""

    def test_search_basic(self, mock_plugin):
        """Test basic search across plugins."""
        expected_results = [
            SearchResult(name="func1", kind="function", path="/f1.py", score=0.9),
            SearchResult(name="func2", kind="function", path="/f2.py", score=0.8),
        ]
        mock_plugin.search.return_value = expected_results

        dispatcher = Dispatcher([mock_plugin])
        results = list(dispatcher.search("func"))

        assert results == expected_results
        mock_plugin.search.assert_called_once_with("func", {"semantic": False, "limit": 20})

    def test_search_semantic(self, mock_plugin):
        """Test semantic search."""
        mock_plugin.search.return_value = []

        dispatcher = Dispatcher([mock_plugin])
        list(dispatcher.search("test", semantic=True, limit=10))

        mock_plugin.search.assert_called_once_with("test", {"semantic": True, "limit": 10})

    def test_search_multiple_plugins(self):
        """Test search results from multiple plugins are combined."""
        plugin1 = Mock(spec=IPlugin, lang="python")
        plugin1.search.return_value = [
            SearchResult(name="py_func", kind="function", path="/test.py", score=0.9)
        ]

        plugin2 = Mock(spec=IPlugin, lang="javascript")
        plugin2.search.return_value = [
            SearchResult(name="js_func", kind="function", path="/test.js", score=0.8),
            SearchResult(name="js_class", kind="class", path="/test2.js", score=0.7),
        ]

        dispatcher = Dispatcher([plugin1, plugin2])
        results = list(dispatcher.search("test"))

        assert len(results) == 3
        assert results[0].name == "py_func"
        assert results[1].name == "js_func"
        assert results[2].name == "js_class"

    def test_search_empty_query(self, mock_plugin):
        """Test search with empty query."""
        mock_plugin.search.return_value = []

        dispatcher = Dispatcher([mock_plugin])
        results = list(dispatcher.search(""))

        assert results == []
        mock_plugin.search.assert_called_once()

    def test_search_plugin_error(self, mock_plugin):
        """Test search when plugin raises error."""
        mock_plugin.search.side_effect = Exception("Search error")

        dispatcher = Dispatcher([mock_plugin])

        with pytest.raises(Exception):
            list(dispatcher.search("test"))


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
        dispatcher = Dispatcher([mock_plugin])

        # Create test file
        test_file = tmp_path / "test.py"
        test_file.write_text("def hello(): pass")

        mock_plugin.supports.return_value = True
        mock_plugin.indexFile.return_value = {"symbols": [{"name": "hello", "kind": "function"}]}

        dispatcher.index_file(test_file)

        mock_plugin.indexFile.assert_called_once()
        assert str(test_file) in dispatcher._file_cache

    def test_index_file_unicode_decode_error(self, mock_plugin, tmp_path):
        """Test indexing file with encoding issues."""
        dispatcher = Dispatcher([mock_plugin])

        test_file = tmp_path / "test.py"
        # Write binary data that's not valid UTF-8
        test_file.write_bytes(b"\xff\xfe invalid utf-8")

        mock_plugin.supports.return_value = True

        # Should try latin-1 encoding
        dispatcher.index_file(test_file)

        # Plugin should be called with latin-1 decoded content
        mock_plugin.indexFile.assert_called_once()

    def test_index_file_read_error(self, mock_plugin):
        """Test indexing when file read fails."""
        dispatcher = Dispatcher([mock_plugin])

        path = Path("/nonexistent/file.py")
        mock_plugin.supports.return_value = True

        # Should not raise, just log error
        dispatcher.index_file(path)

        mock_plugin.indexFile.assert_not_called()

    def test_index_file_no_plugin_match(self, mock_plugin, tmp_path):
        """Test indexing file with no matching plugin."""
        dispatcher = Dispatcher([mock_plugin])

        test_file = tmp_path / "test.unknown"
        test_file.write_text("unknown content")

        mock_plugin.supports.return_value = False

        # Should not raise, just log debug
        dispatcher.index_file(test_file)

        mock_plugin.indexFile.assert_not_called()

    def test_index_file_plugin_error(self, mock_plugin, tmp_path):
        """Test indexing when plugin raises error."""
        dispatcher = Dispatcher([mock_plugin])

        test_file = tmp_path / "test.py"
        test_file.write_text("def hello(): pass")

        mock_plugin.supports.return_value = True
        mock_plugin.indexFile.side_effect = Exception("Plugin error")

        # Should not raise, just log error
        dispatcher.index_file(test_file)

        # File should not be cached on error
        assert str(test_file) not in dispatcher._file_cache

    def test_index_file_skip_cached(self, mock_plugin, tmp_path):
        """Test that cached files are skipped."""
        dispatcher = Dispatcher([mock_plugin])

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

        dispatcher.index_file(test_file)

        # Should not call plugin for cached file
        mock_plugin.indexFile.assert_not_called()


class TestStatistics:
    """Test statistics gathering."""

    def test_get_statistics_empty(self, mock_plugin):
        """Test statistics with no indexed files."""
        dispatcher = Dispatcher([mock_plugin])

        stats = dispatcher.get_statistics()

        assert stats["total"] == 0
        assert stats["by_language"] == {}

    def test_get_statistics_with_files(self):
        """Test statistics with indexed files."""
        py_plugin = Mock(spec=IPlugin, lang="python")
        js_plugin = Mock(spec=IPlugin, lang="javascript")

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

        stats = dispatcher.get_statistics()

        assert stats["total"] == 3
        assert stats["by_language"]["python"] == 2
        assert stats["by_language"]["javascript"] == 1

    def test_get_statistics_plugin_error(self, mock_plugin):
        """Test statistics when plugin.supports raises error."""
        dispatcher = Dispatcher([mock_plugin])
        dispatcher._file_cache = {"/test/file.py": (1000, 100, "hash")}

        mock_plugin.supports.side_effect = Exception("Plugin error")

        stats = dispatcher.get_statistics()

        # Should handle error gracefully
        assert stats["total"] == 0
        assert stats["by_language"] == {}


class TestConcurrency:
    """Test concurrent operations."""

    def test_concurrent_indexing(self, mock_plugin, tmp_path):
        """Test concurrent file indexing."""
        import concurrent.futures

        dispatcher = Dispatcher([mock_plugin])
        mock_plugin.supports.return_value = True
        mock_plugin.indexFile.return_value = {"symbols": []}

        # Create multiple test files
        files = []
        for i in range(10):
            test_file = tmp_path / f"test{i}.py"
            test_file.write_text(f"def func{i}(): pass")
            files.append(test_file)

        # Index files concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(dispatcher.index_file, f) for f in files]
            concurrent.futures.wait(futures)

        # All files should be cached
        assert len(dispatcher._file_cache) == 10
        assert mock_plugin.indexFile.call_count == 10

    def test_concurrent_search(self, mock_plugin):
        """Test concurrent search operations."""
        import concurrent.futures

        dispatcher = Dispatcher([mock_plugin])
        mock_plugin.search.return_value = [
            SearchResult(name="result", kind="function", path="/test.py", score=1.0)
        ]

        def search_task(query):
            return list(dispatcher.search(query))

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
        """Benchmark symbol lookup performance."""
        # Create dispatcher with multiple plugins
        plugins = []
        for i in range(5):
            plugin = Mock(spec=IPlugin, lang=f"lang{i}")
            plugin.getDefinition.return_value = None
            plugins.append(plugin)

        # Last plugin has the symbol
        plugins[-1].getDefinition.return_value = SymbolDef(
            name="target", kind="function", path="/found.py", line=1
        )

        dispatcher = Dispatcher(plugins)

        with measure_time("dispatcher_lookup", benchmark_results):
            for _ in range(1000):
                result = dispatcher.lookup("target")
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
