"""Tests for the plugin system."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from mcp_server.plugin_base import IPlugin
from mcp_server.plugin_system import (
    PluginConfig,
    PluginInfo,
    PluginInitError,
    PluginInstance,
    PluginLoadError,
    PluginManager,
    PluginNotFoundError,
    PluginState,
    PluginSystemConfig,
    PluginType,
)
from mcp_server.plugin_system.plugin_discovery import PluginDiscovery
from mcp_server.plugin_system.plugin_loader import PluginLoader
from mcp_server.plugin_system.plugin_registry import PluginRegistry


class MockPlugin(IPlugin):
    """Mock plugin for testing."""

    lang = "mock"

    def __init__(self, **kwargs):
        self.initialized = True
        self.started = False
        self.stopped = False
        self.destroyed = False
        self.health_status = "healthy"
        self.metrics = {"operations_count": 0, "last_operation_time": None}

    def supports(self, path):
        return path.endswith(".mock")

    def indexFile(self, path, content):
        self.metrics["operations_count"] += 1
        import time

        self.metrics["last_operation_time"] = time.time()
        return {"file": path, "symbols": [], "language": "mock"}

    def getDefinition(self, symbol):
        self.metrics["operations_count"] += 1
        return None

    def findReferences(self, symbol):
        self.metrics["operations_count"] += 1
        return []

    def search(self, query, opts=None):
        self.metrics["operations_count"] += 1
        return []

    def start(self):
        self.started = True
        self.health_status = "healthy"

    def stop(self):
        self.stopped = True
        self.health_status = "stopped"

    def destroy(self):
        self.destroyed = True
        self.health_status = "destroyed"

    def get_health_status(self):
        """Get plugin health status."""
        return self.health_status

    def get_metrics(self):
        """Get plugin performance metrics."""
        return self.metrics.copy()


class TestPluginDiscovery:
    """Test plugin discovery functionality."""

    def test_discover_plugins_empty_dir(self, tmp_path):
        """Test discovering plugins in empty directory."""
        discovery = PluginDiscovery()
        plugins = discovery.discover_plugins([tmp_path])
        assert plugins == []

    def test_discover_plugins_safe(self, tmp_path):
        """Test safe plugin discovery with Result pattern."""
        discovery = PluginDiscovery()

        # Create a valid plugin
        plugin_dir = tmp_path / "test_plugin"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.py").write_text("class Plugin: pass")

        result = discovery.discover_plugins_safe([tmp_path])
        assert result.success
        assert len(result.value) == 1
        assert "discovered_count" in result.metadata
        assert result.metadata["discovered_count"] == 1

    def test_discover_plugin_with_manifest(self, tmp_path):
        """Test discovering plugin with plugin.json manifest."""
        # Create plugin directory
        plugin_dir = tmp_path / "test_plugin"
        plugin_dir.mkdir()

        # Create manifest
        manifest = {
            "name": "Test Plugin",
            "version": "1.0.0",
            "description": "A test plugin",
            "author": "Test Author",
            "type": "language",
            "language": "test",
            "file_extensions": [".test", ".tst"],
        }

        with open(plugin_dir / "plugin.json", "w") as f:
            json.dump(manifest, f)

        # Create plugin.py
        (plugin_dir / "plugin.py").write_text("class Plugin: pass")

        discovery = PluginDiscovery()
        plugins = discovery.discover_plugins([tmp_path])

        assert len(plugins) == 1
        assert plugins[0].name == "Test Plugin"
        assert plugins[0].version == "1.0.0"
        assert plugins[0].language == "test"
        assert ".test" in plugins[0].file_extensions

    def test_discover_plugin_from_module(self, tmp_path):
        """Test discovering plugin from Python module."""
        # Create plugin directory
        plugin_dir = tmp_path / "python_plugin"
        plugin_dir.mkdir()

        # Create plugin.py with __plugin_info__
        plugin_code = """
__plugin_info__ = {
    "name": "Python Test Plugin",
    "version": "2.0.0",
    "description": "Python plugin for testing",
    "author": "Test",
    "language": "python"
}

class Plugin:
    pass
"""
        (plugin_dir / "plugin.py").write_text(plugin_code)

        discovery = PluginDiscovery()
        plugins = discovery.discover_plugins([tmp_path])

        assert len(plugins) == 1
        assert plugins[0].name == "Python Test Plugin"
        assert plugins[0].version == "2.0.0"

    def test_validate_plugin(self, tmp_path):
        """Test plugin validation."""
        discovery = PluginDiscovery()

        # Invalid - not a directory
        assert not discovery.validate_plugin(tmp_path / "nonexistent")

        # Invalid - empty directory
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        assert not discovery.validate_plugin(empty_dir)

        # Valid - has plugin.json
        valid_dir = tmp_path / "valid"
        valid_dir.mkdir()
        (valid_dir / "plugin.json").write_text("{}")
        assert discovery.validate_plugin(valid_dir)

        # Valid - has plugin.py
        valid_py_dir = tmp_path / "valid_py"
        valid_py_dir.mkdir()
        (valid_py_dir / "plugin.py").write_text("")
        assert discovery.validate_plugin(valid_py_dir)

    def test_validate_plugin_safe(self, tmp_path):
        """Test safe plugin validation."""
        discovery = PluginDiscovery()

        # Valid plugin
        plugin_dir = tmp_path / "valid_plugin"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.py").write_text("class Plugin: pass")

        result = discovery.validate_plugin_safe(plugin_dir)
        assert result.success
        assert result.value is True

        # Invalid plugin
        result = discovery.validate_plugin_safe(tmp_path / "nonexistent")
        assert result.success  # Validation succeeds, but result is False
        assert result.value is False


class TestPluginLoader:
    """Test plugin loader functionality."""

    def test_load_plugin_success(self):
        """Test successful plugin loading."""
        loader = PluginLoader()

        plugin_info = PluginInfo(
            name="Test Plugin",
            version="1.0.0",
            description="Test",
            author="Test",
            plugin_type=PluginType.LANGUAGE,
            language="python",
            file_extensions=[".py"],
            path=Path("mcp_server/plugins/python_plugin"),
            module_name="mcp_server.plugins.python_plugin",
        )

        # Should load the actual Python plugin
        plugin_class = loader.load_plugin(plugin_info)
        assert plugin_class is not None
        assert hasattr(plugin_class, "lang")

    def test_load_plugin_safe_success(self):
        """Test safe plugin loading with Result pattern."""
        loader = PluginLoader()

        plugin_info = PluginInfo(
            name="Test Plugin",
            version="1.0.0",
            description="Test",
            author="Test",
            plugin_type=PluginType.LANGUAGE,
            language="python",
            file_extensions=[".py"],
            path=Path("mcp_server/plugins/python_plugin"),
            module_name="mcp_server.plugins.python_plugin",
        )

        result = loader.load_plugin_safe(plugin_info)
        assert result.success
        assert result.value is not None
        assert hasattr(result.value, "lang")
        assert "plugin_name" in result.metadata

    def test_load_plugin_not_found(self, tmp_path):
        """Test loading non-existent plugin."""
        loader = PluginLoader()

        plugin_info = PluginInfo(
            name="Nonexistent",
            version="1.0.0",
            description="Test",
            author="Test",
            plugin_type=PluginType.LANGUAGE,
            language="none",
            file_extensions=[],
            path=tmp_path / "nonexistent",
            module_name="nonexistent.plugin",
        )

        with pytest.raises(PluginLoadError):
            loader.load_plugin(plugin_info)

        # Test safe version
        result = loader.load_plugin_safe(plugin_info)
        assert not result.success
        assert result.error.code == "PLUGIN_LOAD_ERROR"

    def test_unload_plugin_safe(self):
        """Test safe plugin unloading."""
        loader = PluginLoader()

        # Test unloading non-existent plugin (should succeed)
        result = loader.unload_plugin_safe("NonExistent")
        assert result.success

    def test_validate_plugin_class(self):
        """Test plugin class validation."""
        loader = PluginLoader()

        # Valid plugin
        assert loader._validate_plugin_class(MockPlugin)

        # Invalid plugin (missing method)
        class InvalidPlugin:
            lang = "invalid"

            def supports(self, path):
                pass

        assert not loader._validate_plugin_class(InvalidPlugin)


class TestPluginRegistry:
    """Test plugin registry functionality."""

    def test_register_plugin(self):
        """Test plugin registration."""
        registry = PluginRegistry()

        plugin_info = PluginInfo(
            name="Test Plugin",
            version="1.0.0",
            description="Test",
            author="Test",
            plugin_type=PluginType.LANGUAGE,
            language="test",
            file_extensions=[".test", ".tst"],
            path=Path("test"),
            module_name="test",
        )

        registry.register_plugin(plugin_info, MockPlugin)

        assert registry.get_plugin("Test Plugin") == MockPlugin
        assert registry.get_plugin_info("Test Plugin") == plugin_info
        assert "Test Plugin" in registry.get_plugins_by_language("test")
        assert "Test Plugin" in registry.get_plugins_by_extension(".test")

    def test_register_plugin_safe(self):
        """Test safe plugin registration."""
        registry = PluginRegistry()

        plugin_info = PluginInfo(
            name="Test Plugin",
            version="1.0.0",
            description="Test",
            author="Test",
            plugin_type=PluginType.LANGUAGE,
            language="test",
            file_extensions=[".test"],
            path=Path("test"),
            module_name="test",
        )

        result = registry.register_plugin_safe(plugin_info, MockPlugin)
        assert result.success
        assert "plugin_name" in result.metadata
        assert result.metadata["plugin_name"] == "Test Plugin"

    def test_unregister_plugin(self):
        """Test plugin unregistration."""
        registry = PluginRegistry()

        plugin_info = PluginInfo(
            name="Test Plugin",
            version="1.0.0",
            description="Test",
            author="Test",
            plugin_type=PluginType.LANGUAGE,
            language="test",
            file_extensions=[".test"],
            path=Path("test"),
            module_name="test",
        )

        registry.register_plugin(plugin_info, MockPlugin)
        registry.unregister_plugin("Test Plugin")

        assert registry.get_plugin("Test Plugin") is None
        assert registry.get_plugins_by_language("test") == []

    def test_unregister_plugin_safe(self):
        """Test safe plugin unregistration."""
        registry = PluginRegistry()

        # Test unregistering non-existent plugin
        result = registry.unregister_plugin_safe("NonExistent")
        assert not result.success
        assert result.error.code == "PLUGIN_UNREGISTER_ERROR"

    def test_plugin_status_tracking(self):
        """Test plugin status information."""
        registry = PluginRegistry()

        plugin_info = PluginInfo(
            name="Test Plugin",
            version="1.0.0",
            description="Test Plugin Description",
            author="Test Author",
            plugin_type=PluginType.LANGUAGE,
            language="test",
            file_extensions=[".test"],
            path=Path("test"),
            module_name="test",
        )

        registry.register_plugin(plugin_info, MockPlugin)

        status = registry.get_plugin_status("Test Plugin")
        assert status is not None
        assert status["symbol"] == "Test Plugin"
        assert status["version"] == "1.0.0"
        assert status["description"] == "Test Plugin Description"
        assert status["is_registered"] is True

        all_statuses = registry.get_all_plugin_statuses()
        assert "Test Plugin" in all_statuses

    def test_get_plugin_for_file(self):
        """Test getting plugin for file."""
        registry = PluginRegistry()

        plugin_info = PluginInfo(
            name="Python Plugin",
            version="1.0.0",
            description="Test",
            author="Test",
            plugin_type=PluginType.LANGUAGE,
            language="python",
            file_extensions=[".py"],
            path=Path("test"),
            module_name="test",
        )

        registry.register_plugin(plugin_info, MockPlugin)

        assert registry.get_plugin_for_file("test.py") == "Python Plugin"
        assert registry.get_plugin_for_file("test.txt") is None


class TestPluginManager:
    """Test plugin manager functionality."""

    def test_initialization(self):
        """Test plugin manager initialization."""
        manager = PluginManager()
        assert manager.config is not None
        assert len(manager.config.plugin_dirs) > 0

    def test_initialize_plugin(self):
        """Test plugin initialization."""
        manager = PluginManager()

        # Manually register a plugin
        plugin_info = PluginInfo(
            name="Test Plugin",
            version="1.0.0",
            description="Test",
            author="Test",
            plugin_type=PluginType.LANGUAGE,
            language="test",
            file_extensions=[".test"],
            path=Path("test"),
            module_name="test",
        )

        manager._registry.register_plugin(plugin_info, MockPlugin)
        manager._instances["Test Plugin"] = (
            manager._instances.get("Test Plugin")
            or type(
                "obj",
                (object,),
                {
                    "info": plugin_info,
                    "config": PluginConfig(),
                    "instance": None,
                    "state": PluginState.LOADED,
                    "error": None,
                    "is_active": property(
                        lambda self: self.state in (PluginState.INITIALIZED, PluginState.STARTED)
                    ),
                },
            )()
        )

        # Initialize plugin
        plugin = manager.initialize_plugin("Test Plugin", {})
        assert isinstance(plugin, MockPlugin)
        assert plugin.initialized

    def test_plugin_lifecycle(self):
        """Test full plugin lifecycle."""
        # Create manager with auto_load disabled
        config = PluginSystemConfig(auto_load=False)
        manager = PluginManager(config)

        # Register plugin
        plugin_info = PluginInfo(
            name="Test Plugin",
            version="1.0.0",
            description="Test",
            author="Test",
            plugin_type=PluginType.LANGUAGE,
            language="test",
            file_extensions=[".test"],
            path=Path("test"),
            module_name="test",
        )

        manager._registry.register_plugin(plugin_info, MockPlugin)
        manager._instances["Test Plugin"] = (
            manager._instances.get("Test Plugin")
            or type(
                "obj",
                (object,),
                {
                    "info": plugin_info,
                    "config": PluginConfig(),
                    "instance": None,
                    "state": PluginState.LOADED,
                    "error": None,
                    "is_active": property(
                        lambda self: self.state in (PluginState.INITIALIZED, PluginState.STARTED)
                    ),
                },
            )()
        )

        # Initialize
        plugin = manager.initialize_plugin("Test Plugin", {})
        assert manager._instances["Test Plugin"].state == PluginState.INITIALIZED

        # Start
        manager.start_plugin("Test Plugin")
        assert manager._instances["Test Plugin"].state == PluginState.STARTED
        assert plugin.started

        # Stop
        manager.stop_plugin("Test Plugin")
        assert manager._instances["Test Plugin"].state == PluginState.STOPPED
        assert plugin.stopped

        # Destroy
        manager.destroy_plugin("Test Plugin")
        assert manager._instances["Test Plugin"].state == PluginState.LOADED
        assert plugin.destroyed

    def test_get_plugin_by_language(self):
        """Test getting plugin by language."""
        manager = PluginManager()

        # Register and initialize a plugin
        plugin_info = PluginInfo(
            name="Python Plugin",
            version="1.0.0",
            description="Test",
            author="Test",
            plugin_type=PluginType.LANGUAGE,
            language="python",
            file_extensions=[".py"],
            path=Path("test"),
            module_name="test",
        )

        manager._registry.register_plugin(plugin_info, MockPlugin)
        manager._instances["Python Plugin"] = type(
            "obj",
            (object,),
            {
                "info": plugin_info,
                "config": PluginConfig(),
                "instance": MockPlugin(),
                "state": PluginState.STARTED,
                "error": None,
                "is_active": True,
            },
        )()

        plugin = manager.get_plugin_by_language("python")
        assert isinstance(plugin, MockPlugin)

        # Non-existent language
        assert manager.get_plugin_by_language("rust") is None

    def test_plugin_error_handling(self):
        """Test error handling in plugin operations."""
        manager = PluginManager()

        # Try to initialize non-existent plugin
        with pytest.raises(PluginNotFoundError):
            manager.initialize_plugin("Nonexistent", {})

        # Try to start uninitialized plugin
        plugin_info = PluginInfo(
            name="Test Plugin",
            version="1.0.0",
            description="Test",
            author="Test",
            plugin_type=PluginType.LANGUAGE,
            language="test",
            file_extensions=[".test"],
            path=Path("test"),
            module_name="test",
        )

        manager._instances["Test Plugin"] = type(
            "obj",
            (object,),
            {
                "info": plugin_info,
                "config": PluginConfig(),
                "instance": None,
                "state": PluginState.LOADED,
                "error": None,
                "is_active": False,
            },
        )()

        with pytest.raises(PluginInitError):
            manager.start_plugin("Test Plugin")

    def test_plugin_config_loading(self, tmp_path):
        """Test loading plugin configuration from YAML."""
        config_content = """
plugin_dirs:
  - test_plugins
  
auto_discover: false
auto_load: false
max_concurrent_loads: 3
load_timeout_seconds: 15

defaults:
  max_file_size: 2097152
  cache_enabled: true

environments:
  testing:
    enable_hot_reload: true
    validate_interfaces: false

loading:
  strategy: "alphabetical"
  parallel_loading: false

plugins:
  "Test Plugin":
    enabled: true
    priority: 100
    settings:
      custom_setting: value
    dependencies: ["Base Plugin"]
    health_check:
      enabled: true
      interval_seconds: 30
"""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(config_content)

        config = PluginSystemConfig(config_file=config_file)
        manager = PluginManager(config)

        assert not manager.config.auto_discover
        assert not manager.config.auto_load
        assert manager.config.max_concurrent_loads == 3
        assert manager.config.load_timeout_seconds == 15
        assert "Test Plugin" in manager.config.plugin_configs
        plugin_config = manager.config.plugin_configs["Test Plugin"]
        assert plugin_config.priority == 100
        assert plugin_config.dependencies == ["Base Plugin"]
        assert plugin_config.health_check["interval_seconds"] == 30
        assert manager.config.loading["strategy"] == "alphabetical"
        assert manager.config.defaults["max_file_size"] == 2097152

    def test_environment_config_overrides(self, tmp_path):
        """Test environment-specific configuration overrides."""
        config_content = """
auto_discover: true
enable_hot_reload: false

environments:
  testing:
    auto_discover: false
    enable_hot_reload: true
  production:
    validate_interfaces: false
"""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(config_content)

        with patch.dict("os.environ", {"ENVIRONMENT": "testing"}):
            config = PluginSystemConfig(config_file=config_file)
            config.apply_environment_overrides()
            assert not config.auto_discover  # Overridden by testing environment
            assert config.enable_hot_reload  # Overridden by testing environment

    def test_safe_plugin_operations(self):
        """Test Result[T] pattern methods."""
        manager = PluginManager()

        # Test safe plugin loading
        with patch.object(manager, "load_plugins") as mock_load:
            mock_load.side_effect = Exception("Load failed")
            result = manager.load_plugins_safe()
            assert not result.success
            assert result.error.code == "PLUGIN_LOAD_BATCH_ERROR"
            assert "Load failed" in result.error.message

        # Test safe plugin reload
        result = manager.reload_plugin_safe("NonExistent")
        assert not result.success
        assert result.error.code == "PLUGIN_RELOAD_ERROR"

        # Test safe plugin enable/disable
        result = manager.enable_plugin_safe("NonExistent")
        assert not result.success
        assert result.error.code == "PLUGIN_ENABLE_ERROR"

        result = manager.disable_plugin_safe("NonExistent")
        assert not result.success
        assert result.error.code == "PLUGIN_DISABLE_ERROR"

        # Test safe shutdown
        result = manager.shutdown_safe()
        assert result.success  # Should succeed even with no plugins

    def test_detailed_plugin_status(self):
        """Test detailed plugin status reporting."""
        manager = PluginManager()

        # Create a mock plugin instance
        plugin_info = PluginInfo(
            name="Test Plugin",
            version="1.0.0",
            description="Test",
            author="Test",
            plugin_type=PluginType.LANGUAGE,
            language="test",
            file_extensions=[".test"],
            path=Path("test"),
            module_name="test",
        )

        plugin_config = PluginConfig(
            enabled=True,
            priority=10,
            settings={"test_setting": "value"},
            dependencies=["dep1"],
            health_check={"enabled": True, "interval_seconds": 60},
        )

        instance = PluginInstance(
            info=plugin_info,
            config=plugin_config,
            instance=MockPlugin(),
            state=PluginState.STARTED,
            load_time=0.5,
            health_status="healthy",
        )

        manager._instances["Test Plugin"] = instance

        status = manager.get_detailed_plugin_status()
        assert "Test Plugin" in status
        plugin_status = status["Test Plugin"]

        assert plugin_status["basic_info"]["name"] == "Test Plugin"
        assert plugin_status["runtime_info"]["state"] == "started"
        assert plugin_status["runtime_info"]["is_healthy"] is True
        assert plugin_status["runtime_info"]["load_time"] == 0.5
        assert plugin_status["config"]["dependencies"] == ["dep1"]
        assert plugin_status["config"]["health_check"]["enabled"] is True

    def test_plugin_queries_by_attributes(self):
        """Test querying plugins by various attributes."""
        manager = PluginManager()

        # Setup test plugins
        plugin_info1 = PluginInfo(
            name="Python Plugin",
            version="1.0.0",
            description="Test",
            author="Test",
            plugin_type=PluginType.LANGUAGE,
            language="python",
            file_extensions=[".py"],
            path=Path("test"),
            module_name="test",
        )
        plugin_info2 = PluginInfo(
            name="JS Plugin",
            version="1.0.0",
            description="Test",
            author="Test",
            plugin_type=PluginType.LANGUAGE,
            language="javascript",
            file_extensions=[".js"],
            path=Path("test"),
            module_name="test",
        )

        manager._registry.register_plugin(plugin_info1, MockPlugin)
        manager._registry.register_plugin(plugin_info2, MockPlugin)

        # Create active instances
        instance1 = PluginInstance(
            info=plugin_info1,
            config=PluginConfig(enabled=True),
            instance=MockPlugin(),
            state=PluginState.STARTED,
        )
        instance2 = PluginInstance(
            info=plugin_info2,
            config=PluginConfig(enabled=False),
            instance=None,
            state=PluginState.LOADED,
        )

        manager._instances["Python Plugin"] = instance1
        manager._instances["JS Plugin"] = instance2

        # Test queries
        enabled_plugins = manager.get_enabled_plugins()
        assert "Python Plugin" in enabled_plugins
        assert "JS Plugin" not in enabled_plugins

        active_plugins = manager.get_plugins_by_status(PluginState.STARTED)
        assert "Python Plugin" in active_plugins
        assert "JS Plugin" not in active_plugins

        python_plugins = manager.get_plugins_by_language("python")
        assert "Python Plugin" in python_plugins

        js_plugins = manager.get_plugins_by_extension(".js")
        assert "JS Plugin" in js_plugins


class TestPluginInstance:
    """Test plugin instance functionality."""

    def test_plugin_instance_properties(self):
        """Test plugin instance property methods."""
        plugin_info = PluginInfo(
            name="Test Plugin",
            version="1.0.0",
            description="Test",
            author="Test",
            plugin_type=PluginType.LANGUAGE,
            language="test",
            file_extensions=[".test"],
            path=Path("test"),
            module_name="test",
        )

        plugin_config = PluginConfig(enabled=True)

        # Test active instance
        instance = PluginInstance(
            info=plugin_info,
            config=plugin_config,
            instance=MockPlugin(),
            state=PluginState.STARTED,
            health_status="healthy",
        )

        assert instance.is_active
        assert not instance.is_error
        assert instance.is_healthy

        # Test error instance
        error_instance = PluginInstance(
            info=plugin_info,
            config=plugin_config,
            instance=None,
            state=PluginState.ERROR,
            error="Test error",
            health_status="unhealthy",
        )

        assert not error_instance.is_active
        assert error_instance.is_error
        assert not error_instance.is_healthy

    def test_plugin_metrics_update(self):
        """Test plugin metrics updating."""
        plugin_info = PluginInfo(
            name="Test Plugin",
            version="1.0.0",
            description="Test",
            author="Test",
            plugin_type=PluginType.LANGUAGE,
            language="test",
            file_extensions=[".test"],
            path=Path("test"),
            module_name="test",
        )

        instance = PluginInstance(
            info=plugin_info,
            config=PluginConfig(),
            instance=MockPlugin(),
            state=PluginState.STARTED,
        )

        # Update metrics
        test_metrics = {"cpu_usage": 15.5, "memory_usage": 128.0, "request_count": 42}

        instance.update_metrics(test_metrics)

        assert instance.metrics["cpu_usage"] == 15.5
        assert instance.metrics["memory_usage"] == 128.0
        assert instance.metrics["request_count"] == 42
        assert "last_updated" in instance.metrics


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
