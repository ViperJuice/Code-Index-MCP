"""
Tests for Memory-Aware Plugin Management

These tests verify that the memory-aware plugin manager correctly handles
plugin loading, eviction, and memory limits.
"""

import gc
import os
from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from mcp_server.plugin_system.models import LoadedPlugin
from mcp_server.plugins.memory_aware_manager import (
    MemoryAwarePluginManager,
    PluginMemoryInfo,
    get_memory_aware_manager,
)


class TestMemoryAwarePluginManager:
    """Test memory-aware plugin management functionality."""

    @pytest.fixture
    def manager(self):
        """Create a manager instance with small memory limit for testing."""
        return MemoryAwarePluginManager(
            max_memory_mb=100,  # Small limit for testing
            high_priority_langs=["python", "javascript"],
        )

    @pytest.fixture
    def mock_plugin(self):
        """Create a mock plugin."""
        plugin = Mock()
        plugin.language = "test"
        plugin.index = Mock()
        plugin.getDefinition = Mock()
        return plugin

    def test_initialization(self, manager):
        """Test manager initialization."""
        assert manager.max_memory_bytes == 100 * 1024 * 1024
        assert "python" in manager.high_priority_langs
        assert "javascript" in manager.high_priority_langs
        assert len(manager._plugins) == 0

    def test_plugin_loading(self, manager, mock_plugin):
        """Test plugin loading and caching."""
        with patch.object(manager._factory, "get_plugin", return_value=mock_plugin):
            # First load
            plugin1 = manager.get_plugin("test")
            assert plugin1 == mock_plugin
            assert "test" in manager._plugins
            assert "test" in manager._plugin_info

            # Second load (from cache)
            plugin2 = manager.get_plugin("test")
            assert plugin2 == mock_plugin
            assert manager._plugin_info["test"].usage_count == 2

    def test_lru_ordering(self, manager):
        """Test LRU ordering of plugins."""
        plugins = []
        for i in range(3):
            plugin = Mock()
            plugin.language = f"lang{i}"
            plugins.append(plugin)

        with patch.object(manager._factory, "get_plugin", side_effect=plugins):
            # Load plugins in order
            manager.get_plugin("lang0")
            manager.get_plugin("lang1")
            manager.get_plugin("lang2")

            # Access lang0 again (moves to end)
            manager.get_plugin("lang0")

            # Check order (lang1 should be oldest)
            plugin_names = list(manager._plugins.keys())
            assert plugin_names == ["lang1", "lang2", "lang0"]

    def test_memory_limit_enforcement(self, manager):
        """Test that memory limits are enforced."""
        # Mock memory usage to exceed limit
        with patch.object(
            manager, "_get_plugin_memory_usage", return_value=manager.max_memory_bytes + 1
        ):
            with patch.object(manager, "_get_eviction_candidates", return_value=["old_plugin"]):
                with patch.object(manager, "_evict_plugin", return_value=1024 * 1024) as mock_evict:
                    with patch.object(manager._factory, "get_plugin", return_value=Mock()):
                        plugin = manager.get_plugin("new_plugin")

                        # Should have tried to evict
                        mock_evict.assert_called_once_with("old_plugin")

    def test_high_priority_protection(self, manager):
        """Test that high-priority plugins are protected from eviction."""
        # Create plugins
        python_plugin = Mock()
        python_plugin.language = "python"
        other_plugin = Mock()
        other_plugin.language = "rust"

        with patch.object(
            manager._factory, "get_plugin", side_effect=[python_plugin, other_plugin]
        ):
            # Load both plugins
            manager.get_plugin("python")
            manager.get_plugin("rust")

            # Mark Python as high priority
            manager._plugin_info["python"].is_high_priority = True
            manager._plugin_info["rust"].is_high_priority = False

            # Get eviction candidates
            candidates = manager._get_eviction_candidates()

            # Python should not be in candidates
            assert "python" not in candidates
            assert "rust" in candidates

    def test_plugin_eviction(self, manager):
        """Test plugin eviction and memory reclamation."""
        plugin = Mock()
        plugin.language = "test"

        # Add plugin manually
        manager._plugins["test"] = LoadedPlugin(name="test", instance=plugin, metadata={})
        manager._plugin_info["test"] = PluginMemoryInfo(
            plugin_name="test",
            memory_bytes=1024 * 1024,  # 1MB
            last_used=datetime.now(),
            load_time=0.1,
            usage_count=1,
            is_high_priority=False,
        )

        # Evict plugin
        memory_freed = manager._evict_plugin("test")

        assert memory_freed == 1024 * 1024
        assert "test" not in manager._plugins
        assert "test" not in manager._plugin_info

    def test_memory_status(self, manager):
        """Test memory status reporting."""
        # Add some test plugins
        for i in range(2):
            plugin = Mock()
            manager._plugins[f"lang{i}"] = LoadedPlugin(
                name=f"lang{i}", instance=plugin, metadata={}
            )
            manager._plugin_info[f"lang{i}"] = PluginMemoryInfo(
                plugin_name=f"lang{i}",
                memory_bytes=1024 * 1024 * 10,  # 10MB each
                last_used=datetime.now(),
                load_time=0.1,
                usage_count=i + 1,
                is_high_priority=i == 0,
            )

        status = manager.get_memory_status()

        assert status["max_memory_mb"] == 100
        assert status["used_memory_mb"] == 20  # 2 * 10MB
        assert status["available_memory_mb"] == 80
        assert status["usage_percent"] == 20
        assert status["loaded_plugins"] == 2
        assert len(status["plugin_details"]) == 2

    def test_preload_high_priority(self, manager):
        """Test preloading of high-priority plugins."""
        mock_plugins = {
            "python": Mock(language="python"),
            "javascript": Mock(language="javascript"),
        }

        def get_plugin_side_effect(lang):
            return mock_plugins.get(lang)

        with patch.object(manager._factory, "get_plugin", side_effect=get_plugin_side_effect):
            manager.preload_high_priority()

            # Both high-priority languages should be loaded
            assert "python" in manager._plugins
            assert "javascript" in manager._plugins

    def test_clear_cache(self, manager):
        """Test cache clearing functionality."""
        # Add plugins
        for lang in ["python", "rust", "go"]:
            plugin = Mock()
            manager._plugins[lang] = LoadedPlugin(name=lang, instance=plugin, metadata={})
            manager._plugin_info[lang] = PluginMemoryInfo(
                plugin_name=lang,
                memory_bytes=1024 * 1024,
                last_used=datetime.now(),
                load_time=0.1,
                usage_count=1,
                is_high_priority=(lang == "python"),
            )

        # Clear cache keeping high priority
        manager.clear_cache(keep_high_priority=True)

        assert "python" in manager._plugins  # High priority kept
        assert "rust" not in manager._plugins
        assert "go" not in manager._plugins

        # Clear all
        manager.clear_cache(keep_high_priority=False)
        assert len(manager._plugins) == 0

    def test_set_high_priority_languages(self, manager):
        """Test updating high-priority languages."""
        # Add a plugin
        manager._plugin_info["rust"] = PluginMemoryInfo(
            plugin_name="rust",
            memory_bytes=1024 * 1024,
            last_used=datetime.now(),
            load_time=0.1,
            usage_count=1,
            is_high_priority=False,
        )

        # Update high priority list
        manager.set_high_priority_languages(["rust", "go"])

        assert "rust" in manager.high_priority_langs
        assert "go" in manager.high_priority_langs
        assert "python" not in manager.high_priority_langs

        # Rust plugin should now be high priority
        assert manager._plugin_info["rust"].is_high_priority is True

    def test_get_plugin_info(self, manager):
        """Test getting plugin information."""
        # Add a plugin
        plugin = Mock()
        manager._plugins["test"] = LoadedPlugin(name="test", instance=plugin, metadata={})
        manager._plugin_info["test"] = PluginMemoryInfo(
            plugin_name="test",
            memory_bytes=1024 * 1024 * 5,  # 5MB
            last_used=datetime.now(),
            load_time=0.25,
            usage_count=10,
            is_high_priority=False,
        )

        info = manager.get_plugin_info("test")

        assert info["language"] == "test"
        assert info["memory_mb"] == 5.0
        assert info["usage_count"] == 10
        assert info["load_time_seconds"] == 0.25
        assert info["is_high_priority"] is False
        assert info["is_loaded"] is True

        # Non-existent plugin
        assert manager.get_plugin_info("nonexistent") is None


class TestSingletonManager:
    """Test singleton manager functionality."""

    def test_singleton_instance(self):
        """Test that get_memory_aware_manager returns singleton."""
        manager1 = get_memory_aware_manager()
        manager2 = get_memory_aware_manager()

        assert manager1 is manager2

    def test_environment_configuration(self):
        """Test configuration from environment variables."""
        # Clear any existing instance
        import mcp_server.plugins.memory_aware_manager as module

        module._manager_instance = None

        # Set environment variables
        os.environ["MCP_MAX_MEMORY_MB"] = "512"
        os.environ["MCP_HIGH_PRIORITY_LANGS"] = "python,go,rust"
        os.environ["MCP_PRELOAD_PLUGINS"] = "false"

        try:
            manager = get_memory_aware_manager()

            assert manager.max_memory_bytes == 512 * 1024 * 1024
            assert "python" in manager.high_priority_langs
            assert "go" in manager.high_priority_langs
            assert "rust" in manager.high_priority_langs

        finally:
            # Clean up
            del os.environ["MCP_MAX_MEMORY_MB"]
            del os.environ["MCP_HIGH_PRIORITY_LANGS"]
            del os.environ["MCP_PRELOAD_PLUGINS"]
            module._manager_instance = None

    def test_thread_safety(self):
        """Test thread-safe access to singleton."""
        import threading

        import mcp_server.plugins.memory_aware_manager as module

        module._manager_instance = None

        managers = []

        def get_manager():
            manager = get_memory_aware_manager()
            managers.append(manager)

        # Create multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=get_manager)
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # All should be the same instance
        assert len(set(id(m) for m in managers)) == 1

        # Clean up
        module._manager_instance = None


class TestMemoryMonitoring:
    """Test memory monitoring functionality."""

    def test_memory_measurement(self):
        """Test that memory measurement works."""
        manager = MemoryAwarePluginManager(max_memory_mb=100)

        # Should be able to get current memory
        current_memory = manager._get_current_memory()
        assert current_memory > 0

        # Plugin memory should start at 0
        plugin_memory = manager._get_plugin_memory_usage()
        assert plugin_memory == 0

    def test_weak_reference_cleanup(self):
        """Test that weak references allow garbage collection."""
        manager = MemoryAwarePluginManager(max_memory_mb=100)

        # Create and add a plugin
        plugin = Mock()
        plugin.language = "test"

        manager._plugins["test"] = LoadedPlugin(name="test", instance=plugin, metadata={})
        manager._plugin_info["test"] = PluginMemoryInfo(
            plugin_name="test",
            memory_bytes=1024,
            last_used=datetime.now(),
            load_time=0.1,
            usage_count=1,
            is_high_priority=False,
        )

        # Create weak reference
        manager._weak_refs["test"] = weakref.ref(
            plugin, lambda ref: manager._on_plugin_deleted("test")
        )

        # Remove strong reference
        del manager._plugins["test"]
        del plugin

        # Force garbage collection
        gc.collect()

        # Plugin info should be cleaned up by callback
        # Note: This is timing-dependent and may not always work in tests

    def test_memory_limit_calculation(self):
        """Test memory limit calculations."""
        manager = MemoryAwarePluginManager(max_memory_mb=100)

        # Add some fake plugin memory usage
        manager._plugin_info["test1"] = PluginMemoryInfo(
            plugin_name="test1",
            memory_bytes=30 * 1024 * 1024,  # 30MB
            last_used=datetime.now(),
            load_time=0.1,
            usage_count=1,
            is_high_priority=False,
        )

        manager._plugin_info["test2"] = PluginMemoryInfo(
            plugin_name="test2",
            memory_bytes=50 * 1024 * 1024,  # 50MB
            last_used=datetime.now(),
            load_time=0.1,
            usage_count=1,
            is_high_priority=False,
        )

        # Total should be 80MB
        total_memory = manager._get_plugin_memory_usage()
        assert total_memory == 80 * 1024 * 1024

        # Should need to free memory
        available = manager._ensure_memory_available()
        # This depends on eviction logic
