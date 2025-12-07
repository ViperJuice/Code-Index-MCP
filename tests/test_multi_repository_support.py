"""Tests for multi-repository support and smart plugin loading."""

import asyncio
import os
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from mcp_server.plugins.memory_aware_manager import MemoryAwarePluginManager, PluginInfo
from mcp_server.plugins.repository_plugin_loader import RepositoryAwarePluginLoader
from mcp_server.storage.multi_repo_manager import MultiRepoIndexManager
from mcp_server.storage.sqlite_store import SQLiteStore


class TestMultiRepoManager:
    """Test multi-repository index management."""

    @pytest.fixture
    def temp_index_dir(self):
        """Create temporary index directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def mock_sqlite_store(self):
        """Create mock SQLite store."""
        store = Mock(spec=SQLiteStore)
        store.db_path = ":memory:"
        return store

    def test_repo_id_resolution(self):
        """Test repository ID resolution from various inputs."""
        # Test git URL
        git_url = "https://github.com/user/repo.git"
        repo_id = MultiRepoIndexManager.resolve_repo_id(git_url)
        assert len(repo_id) == 12
        assert all(c in "0123456789abcdef" for c in repo_id)

        # Test existing repo ID
        existing_id = "abcd1234efgh"
        assert MultiRepoIndexManager.resolve_repo_id(existing_id) == existing_id

        # Test path resolution
        with tempfile.TemporaryDirectory() as tmpdir:
            path_id = MultiRepoIndexManager.resolve_repo_id(tmpdir)
            assert len(path_id) == 12

    def test_authorization(self, temp_index_dir):
        """Test repository authorization."""
        os.environ["MCP_REFERENCE_REPOS"] = "repo1,repo2,repo3"

        manager = MultiRepoIndexManager("primary123", str(temp_index_dir))

        # Primary repo always authorized
        assert manager.is_repo_authorized("primary123")

        # Configured repos authorized
        assert manager.is_repo_authorized("repo1")
        assert manager.is_repo_authorized("repo2")
        assert manager.is_repo_authorized("repo3")

        # Unknown repo not authorized
        assert not manager.is_repo_authorized("unknown_repo")

    def test_index_loading(self, temp_index_dir):
        """Test loading repository indexes."""
        # Create test index
        repo_id = "test_repo_123"
        repo_dir = temp_index_dir / repo_id
        repo_dir.mkdir()

        # Create dummy database
        db_path = repo_dir / "current.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            """
            CREATE TABLE files (
                id INTEGER PRIMARY KEY,
                language TEXT,
                path TEXT
            )
        """
        )
        conn.execute("INSERT INTO files (language, path) VALUES ('python', 'test.py')")
        conn.commit()
        conn.close()

        # Create manager
        manager = MultiRepoIndexManager(repo_id, str(temp_index_dir))

        # Load index
        index = manager.get_index(repo_id)
        assert index is not None
        assert repo_id in manager.get_loaded_repos()

    def test_language_detection(self, temp_index_dir):
        """Test language detection from repository index."""
        # Create test index with multiple languages
        repo_id = "multilang_repo"
        repo_dir = temp_index_dir / repo_id
        repo_dir.mkdir()

        db_path = repo_dir / "current.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            """
            CREATE TABLE files (
                id INTEGER PRIMARY KEY,
                language TEXT,
                path TEXT
            )
        """
        )

        # Insert files with different languages
        languages = [
            ("python", "main.py"),
            ("python", "test.py"),
            ("javascript", "app.js"),
            ("typescript", "types.ts"),
            ("go", "server.go"),
        ]

        for lang, path in languages:
            conn.execute("INSERT INTO files (language, path) VALUES (?, ?)", (lang, path))
        conn.commit()
        conn.close()

        # Create manager and detect languages
        manager = MultiRepoIndexManager(repo_id, str(temp_index_dir))
        detected = manager.get_repo_languages(repo_id)

        assert "python" in detected
        assert "javascript" in detected
        assert "typescript" in detected
        assert "go" in detected


class TestRepositoryAwarePluginLoader:
    """Test repository-aware plugin loading."""

    @pytest.fixture
    def mock_sqlite_store(self):
        """Create mock SQLite store with test data."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmpfile:
            db_path = tmpfile.name

        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            CREATE TABLE files (
                id INTEGER PRIMARY KEY,
                language TEXT,
                path TEXT
            )
        """
        )

        # Add test files
        test_files = [
            ("python", "app.py"),
            ("python", "test.py"),
            ("python", "utils.py"),
            ("javascript", "index.js"),
            ("javascript", "config.js"),
            ("html", "index.html"),
            ("css", "styles.css"),
        ]

        for lang, path in test_files:
            conn.execute("INSERT INTO files (language, path) VALUES (?, ?)", (lang, path))
        conn.commit()
        conn.close()

        store = SQLiteStore(db_path)
        yield store

        # Cleanup
        os.unlink(db_path)

    def test_language_detection(self, mock_sqlite_store):
        """Test detecting languages from repository."""
        loader = RepositoryAwarePluginLoader(mock_sqlite_store)

        # Check detected languages
        assert "python" in loader.plugin_languages
        assert "javascript" in loader.plugin_languages
        assert "html" in loader.plugin_languages
        assert "css" in loader.plugin_languages

        # Check stats
        stats = loader.get_language_stats()
        assert stats["python"] == 3
        assert stats["javascript"] == 2
        assert stats["html"] == 1
        assert stats["css"] == 1

    def test_plugin_strategy(self, mock_sqlite_store):
        """Test different plugin loading strategies."""
        loader = RepositoryAwarePluginLoader(mock_sqlite_store)

        # Test auto strategy (default)
        os.environ["MCP_PLUGIN_STRATEGY"] = "auto"
        required = loader.get_required_plugins()
        assert len(required) == 4  # Only languages in repo

        # Test all strategy
        os.environ["MCP_PLUGIN_STRATEGY"] = "all"
        required = loader.get_required_plugins()
        assert len(required) > 4  # All available plugins

        # Test minimal strategy
        os.environ["MCP_PLUGIN_STRATEGY"] = "minimal"
        required = loader.get_required_plugins()
        assert len(required) == 0  # No plugins preloaded

    def test_priority_ordering(self, mock_sqlite_store):
        """Test language priority ordering."""
        os.environ["MCP_CACHE_HIGH_PRIORITY_LANGS"] = "python,typescript,rust"

        loader = RepositoryAwarePluginLoader(mock_sqlite_store)
        priority_order = loader.get_priority_languages()

        # Python should be first (in high priority and in repo)
        assert priority_order[0] == "python"

        # JavaScript should come after Python (not in priority list)
        python_idx = priority_order.index("python")
        js_idx = priority_order.index("javascript")
        assert python_idx < js_idx


class TestMemoryAwarePluginManager:
    """Test memory-aware plugin management."""

    @pytest.fixture
    def manager(self):
        """Create plugin manager with test configuration."""
        return MemoryAwarePluginManager(sqlite_store=None, max_memory_mb=100, min_free_mb=50)

    @pytest.fixture
    def mock_plugin(self):
        """Create mock plugin."""
        plugin = Mock()
        plugin.lang = "python"
        return plugin

    @pytest.mark.asyncio
    async def test_plugin_loading(self, manager, mock_plugin):
        """Test loading plugins with memory management."""
        # Mock the factory
        with patch.object(manager.plugin_factory, "create_plugin", return_value=mock_plugin):
            # Load plugin
            plugin = await manager.get_plugin("python", timeout=1.0)

            assert plugin == mock_plugin
            assert "python" in manager.get_loaded_plugins()

    def test_memory_tracking(self, manager):
        """Test memory usage tracking."""
        # Add some test plugins
        for lang in ["python", "javascript", "go"]:
            info = PluginInfo(lang)
            info.update_memory_usage(20.0)  # 20MB each
            info.is_loaded = True
            manager.plugins[lang] = info

        stats = manager.get_memory_usage()

        assert stats["loaded_plugins"] == 3
        assert stats["plugin_memory_mb"] == 60.0  # 3 * 20MB

    def test_lru_eviction(self, manager):
        """Test LRU eviction strategy."""
        # Add plugins with different access patterns
        languages = ["python", "javascript", "go", "rust", "java"]

        for i, lang in enumerate(languages):
            info = PluginInfo(lang)
            info.is_loaded = True
            info.update_memory_usage(10.0)
            manager.plugins[lang] = info

            # Simulate access patterns
            manager.access_counts[lang] = 5 - i  # Python most accessed
            manager.last_access[lang] = float(i)  # Python most recent

        # Get eviction candidates
        candidates = manager._get_eviction_candidates()

        # Java should be first candidate (least accessed, oldest)
        assert candidates[0] == "java"

        # Python should be last candidate (most accessed, newest)
        assert candidates[-1] == "python"

    def test_memory_pressure_detection(self, manager):
        """Test memory pressure detection."""
        # Mock memory stats
        with patch.object(manager.process, "memory_info") as mock_mem:
            mock_mem.return_value = Mock(rss=150 * 1024 * 1024)  # 150MB

            with patch("psutil.virtual_memory") as mock_vm:
                mock_vm.return_value = Mock(available=30 * 1024 * 1024)  # 30MB

                # Should detect high memory pressure
                pressure = manager._calculate_memory_pressure()
                assert pressure > 0.5  # High pressure

                # Should trigger eviction
                needs_eviction = asyncio.run(manager._needs_eviction())
                assert needs_eviction


class TestIntegration:
    """Integration tests for the complete system."""

    @pytest.mark.asyncio
    async def test_end_to_end_multi_repo_search(self):
        """Test complete multi-repo search flow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create two test repositories
            for repo_num in [1, 2]:
                repo_id = f"test_repo_{repo_num}"
                repo_dir = Path(tmpdir) / repo_id
                repo_dir.mkdir()

                # Create index
                db_path = repo_dir / "current.db"
                conn = sqlite3.connect(str(db_path))
                conn.execute(
                    """
                    CREATE TABLE files (
                        id INTEGER PRIMARY KEY,
                        language TEXT,
                        path TEXT
                    )
                """
                )
                conn.execute(
                    """
                    CREATE VIRTUAL TABLE bm25_content USING fts5(
                        filepath, content, language, tokenize='porter'
                    )
                """
                )

                # Add test content
                content = f"Repository {repo_num} test content with search term"
                conn.execute(
                    "INSERT INTO bm25_content (filepath, content, language) VALUES (?, ?, ?)",
                    (f"test{repo_num}.py", content, "python"),
                )
                conn.commit()
                conn.close()

            # Create multi-repo manager
            os.environ["MCP_REFERENCE_REPOS"] = "test_repo_1,test_repo_2"
            manager = MultiRepoIndexManager("test_repo_1", tmpdir)

            # Search across both repos
            results = await manager.search_across_repos("search term", None, limit=10)

            # Should find results from both repos
            assert len(results) >= 2
            repo_ids = {r.get("repo_id") for r in results}
            assert "test_repo_1" in repo_ids
            assert "test_repo_2" in repo_ids

    def test_memory_aware_loading_with_repo_detection(self):
        """Test memory-aware loading based on repository content."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmpfile:
            db_path = tmpfile.name

        try:
            # Create test database
            conn = sqlite3.connect(db_path)
            conn.execute(
                """
                CREATE TABLE files (
                    id INTEGER PRIMARY KEY,
                    language TEXT,
                    path TEXT
                )
            """
            )

            # Add files for only 3 languages
            for lang in ["python", "python", "javascript", "go"]:
                conn.execute(
                    "INSERT INTO files (language, path) VALUES (?, ?)", (lang, f"test.{lang}")
                )
            conn.commit()
            conn.close()

            # Create components
            store = SQLiteStore(db_path)
            loader = RepositoryAwarePluginLoader(store)

            # Should only need 3 plugins
            required = loader.get_required_plugins()
            assert len(required) == 3
            assert "python" in required
            assert "javascript" in required
            assert "go" in required

            # Should not include other languages
            assert "rust" not in required
            assert "java" not in required

        finally:
            os.unlink(db_path)
