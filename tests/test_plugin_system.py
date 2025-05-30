"""Tests for the plugin system."""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from mcp_server.plugin_base import IPlugin
from mcp_server.plugin_system import (
    PluginManager,
    PluginInfo,
    PluginConfig,
    PluginState,
    PluginType,
    PluginSystemConfig,
    PluginNotFoundError,
    PluginLoadError,
    PluginInitError
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
    
    def supports(self, path):
        return path.endswith('.mock')
    
    def indexFile(self, path, content):
        return {'file': path, 'symbols': [], 'language': 'mock'}
    
    def getDefinition(self, symbol):
        return None
    
    def findReferences(self, symbol):
        return []
    
    def search(self, query, opts=None):
        return []
    
    def start(self):
        self.started = True
    
    def stop(self):
        self.stopped = True
    
    def destroy(self):
        self.destroyed = True


class TestPluginDiscovery:
    """Test plugin discovery functionality."""
    
    def test_discover_plugins_empty_dir(self, tmp_path):
        """Test discovering plugins in empty directory."""
        discovery = PluginDiscovery()
        plugins = discovery.discover_plugins([tmp_path])
        assert plugins == []
    
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
            "file_extensions": [".test", ".tst"]
        }
        
        with open(plugin_dir / "plugin.json", 'w') as f:
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
        plugin_code = '''
__plugin_info__ = {
    "name": "Python Test Plugin",
    "version": "2.0.0",
    "description": "Python plugin for testing",
    "author": "Test",
    "language": "python"
}

class Plugin:
    pass
'''
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
        (valid_dir / "plugin.json").write_text('{}')
        assert discovery.validate_plugin(valid_dir)
        
        # Valid - has plugin.py
        valid_py_dir = tmp_path / "valid_py"
        valid_py_dir.mkdir()
        (valid_py_dir / "plugin.py").write_text('')
        assert discovery.validate_plugin(valid_py_dir)


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
            module_name="mcp_server.plugins.python_plugin"
        )
        
        # Should load the actual Python plugin
        plugin_class = loader.load_plugin(plugin_info)
        assert plugin_class is not None
        assert hasattr(plugin_class, 'lang')
    
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
            module_name="nonexistent.plugin"
        )
        
        with pytest.raises(PluginLoadError):
            loader.load_plugin(plugin_info)
    
    def test_validate_plugin_class(self):
        """Test plugin class validation."""
        loader = PluginLoader()
        
        # Valid plugin
        assert loader._validate_plugin_class(MockPlugin)
        
        # Invalid plugin (missing method)
        class InvalidPlugin:
            lang = "invalid"
            def supports(self, path): pass
        
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
            module_name="test"
        )
        
        registry.register_plugin(plugin_info, MockPlugin)
        
        assert registry.get_plugin("Test Plugin") == MockPlugin
        assert registry.get_plugin_info("Test Plugin") == plugin_info
        assert "Test Plugin" in registry.get_plugins_by_language("test")
        assert "Test Plugin" in registry.get_plugins_by_extension(".test")
    
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
            module_name="test"
        )
        
        registry.register_plugin(plugin_info, MockPlugin)
        registry.unregister_plugin("Test Plugin")
        
        assert registry.get_plugin("Test Plugin") is None
        assert registry.get_plugins_by_language("test") == []
    
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
            module_name="test"
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
            module_name="test"
        )
        
        manager._registry.register_plugin(plugin_info, MockPlugin)
        manager._instances["Test Plugin"] = manager._instances.get("Test Plugin") or type('obj', (object,), {
            'info': plugin_info,
            'config': PluginConfig(),
            'instance': None,
            'state': PluginState.LOADED,
            'error': None,
            'is_active': property(lambda self: self.state in (PluginState.INITIALIZED, PluginState.STARTED))
        })()
        
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
            module_name="test"
        )
        
        manager._registry.register_plugin(plugin_info, MockPlugin)
        manager._instances["Test Plugin"] = manager._instances.get("Test Plugin") or type('obj', (object,), {
            'info': plugin_info,
            'config': PluginConfig(),
            'instance': None,
            'state': PluginState.LOADED,
            'error': None,
            'is_active': property(lambda self: self.state in (PluginState.INITIALIZED, PluginState.STARTED))
        })()
        
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
            module_name="test"
        )
        
        manager._registry.register_plugin(plugin_info, MockPlugin)
        manager._instances["Python Plugin"] = type('obj', (object,), {
            'info': plugin_info,
            'config': PluginConfig(),
            'instance': MockPlugin(),
            'state': PluginState.STARTED,
            'error': None,
            'is_active': True
        })()
        
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
            module_name="test"
        )
        
        manager._instances["Test Plugin"] = type('obj', (object,), {
            'info': plugin_info,
            'config': PluginConfig(),
            'instance': None,
            'state': PluginState.LOADED,
            'error': None,
            'is_active': False
        })()
        
        with pytest.raises(PluginInitError):
            manager.start_plugin("Test Plugin")
    
    def test_plugin_config_loading(self, tmp_path):
        """Test loading plugin configuration from YAML."""
        config_content = """
plugin_dirs:
  - test_plugins
  
auto_discover: false
auto_load: false

plugins:
  "Test Plugin":
    enabled: true
    priority: 100
    settings:
      custom_setting: value
"""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(config_content)
        
        config = PluginSystemConfig(config_file=config_file)
        manager = PluginManager(config)
        
        assert not manager.config.auto_discover
        assert not manager.config.auto_load
        assert "Test Plugin" in manager.config.plugin_configs
        assert manager.config.plugin_configs["Test Plugin"].priority == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])