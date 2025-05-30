"""Plugin manager implementation."""

import logging
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any, Type

from ..plugin_base import IPlugin
from ..storage.sqlite_store import SQLiteStore
from .interfaces import IPluginManager, ILifecycleManager
from .plugin_discovery import PluginDiscovery
from .plugin_loader import PluginLoader
from .plugin_registry import PluginRegistry
from .models import (
    PluginInfo, PluginConfig, PluginInstance, PluginState,
    PluginSystemConfig, PluginNotFoundError, PluginInitError,
    PluginLoadResult
)

logger = logging.getLogger(__name__)


class PluginManager(IPluginManager, ILifecycleManager):
    """High-level plugin management and lifecycle operations."""
    
    def __init__(self, config: Optional[PluginSystemConfig] = None, sqlite_store: Optional[SQLiteStore] = None):
        self.config = config or self._get_default_config()
        self.sqlite_store = sqlite_store
        
        # Initialize components
        self._discovery = PluginDiscovery()
        self._loader = PluginLoader()
        self._registry = PluginRegistry()
        
        # Plugin instances
        self._instances: Dict[str, PluginInstance] = {}
        
        # Load configuration if specified
        if self.config.config_file and self.config.config_file.exists():
            self._load_config_file(self.config.config_file)
    
    def _get_default_config(self) -> PluginSystemConfig:
        """Get default plugin system configuration."""
        return PluginSystemConfig(
            plugin_dirs=[
                Path(__file__).parent.parent / "plugins"  # Default plugins directory
            ],
            auto_discover=True,
            auto_load=True,
            validate_interfaces=True
        )
    
    def _load_config_file(self, config_path: Path) -> None:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                data = yaml.safe_load(f)
            
            if data:
                # Update config with loaded data
                self.config = PluginSystemConfig.from_dict(data)
                logger.info(f"Loaded plugin configuration from {config_path}")
        except Exception as e:
            logger.error(f"Failed to load config file {config_path}: {e}")
    
    def load_plugins(self, config_path: Optional[Path] = None) -> None:
        """Load and initialize all plugins based on configuration."""
        if config_path:
            self._load_config_file(config_path)
        
        if self.config.auto_discover:
            # Discover plugins
            discovered = self._discovery.discover_plugins(self.config.plugin_dirs)
            logger.info(f"Discovered {len(discovered)} plugins")
            
            # Load each discovered plugin
            for plugin_info in discovered:
                if plugin_info.name in self.config.disabled_plugins:
                    logger.info(f"Skipping disabled plugin: {plugin_info.name}")
                    continue
                
                try:
                    # Load the plugin class
                    plugin_class = self._loader.load_plugin(plugin_info)
                    
                    # Register the plugin
                    self._registry.register_plugin(plugin_info, plugin_class)
                    
                    # Get plugin config
                    plugin_config = self.config.plugin_configs.get(
                        plugin_info.name,
                        PluginConfig()
                    )
                    
                    # Create instance record
                    instance = PluginInstance(
                        info=plugin_info,
                        config=plugin_config,
                        instance=None,
                        state=PluginState.LOADED
                    )
                    self._instances[plugin_info.name] = instance
                    
                    # Auto-initialize if configured
                    if self.config.auto_load and plugin_config.enabled:
                        self.initialize_plugin(plugin_info.name, plugin_config.settings)
                        
                except Exception as e:
                    logger.error(f"Failed to load plugin {plugin_info.name}: {e}")
    
    def reload_plugin(self, plugin_name: str) -> None:
        """Reload a specific plugin."""
        if plugin_name not in self._instances:
            raise PluginNotFoundError(f"Plugin {plugin_name} not found")
        
        # Stop and destroy if running
        if self._instances[plugin_name].is_active:
            self.stop_plugin(plugin_name)
            self.destroy_plugin(plugin_name)
        
        # Unload the module
        self._loader.unload_plugin(plugin_name)
        
        # Unregister from registry
        self._registry.unregister_plugin(plugin_name)
        
        # Get plugin info
        plugin_info = self._instances[plugin_name].info
        
        # Reload
        try:
            plugin_class = self._loader.load_plugin(plugin_info)
            self._registry.register_plugin(plugin_info, plugin_class)
            
            # Update state
            self._instances[plugin_name].state = PluginState.LOADED
            self._instances[plugin_name].error = None
            
            # Re-initialize if it was active
            if self._instances[plugin_name].config.enabled:
                self.initialize_plugin(plugin_name, self._instances[plugin_name].config.settings)
            
            logger.info(f"Successfully reloaded plugin: {plugin_name}")
            
        except Exception as e:
            self._instances[plugin_name].state = PluginState.ERROR
            self._instances[plugin_name].error = str(e)
            raise
    
    def enable_plugin(self, plugin_name: str) -> None:
        """Enable a disabled plugin."""
        if plugin_name not in self._instances:
            raise PluginNotFoundError(f"Plugin {plugin_name} not found")
        
        instance = self._instances[plugin_name]
        instance.config.enabled = True
        
        # Remove from disabled set
        self.config.disabled_plugins.discard(plugin_name)
        
        # Initialize if not already
        if not instance.is_active:
            self.initialize_plugin(plugin_name, instance.config.settings)
    
    def disable_plugin(self, plugin_name: str) -> None:
        """Disable an active plugin."""
        if plugin_name not in self._instances:
            raise PluginNotFoundError(f"Plugin {plugin_name} not found")
        
        instance = self._instances[plugin_name]
        instance.config.enabled = False
        
        # Add to disabled set
        self.config.disabled_plugins.add(plugin_name)
        
        # Stop if running
        if instance.is_active:
            self.stop_plugin(plugin_name)
            self.destroy_plugin(plugin_name)
    
    def get_plugin_by_language(self, language: str) -> Optional[IPlugin]:
        """Get a plugin instance that supports the given language."""
        plugin_names = self._registry.get_plugins_by_language(language)
        
        # Find the first active plugin
        for name in plugin_names:
            instance = self.get_plugin_instance(name)
            if instance:
                return instance
        
        return None
    
    def get_plugin_for_file(self, file_path: Path) -> Optional[IPlugin]:
        """Get a plugin instance that supports the given file."""
        # Check each active plugin
        for name, instance in self._instances.items():
            if instance.is_active and instance.instance:
                if instance.instance.supports(str(file_path)):
                    return instance.instance
        
        # Fallback to extension-based lookup
        plugin_name = self._registry.get_plugin_for_file(str(file_path))
        if plugin_name:
            return self.get_plugin_instance(plugin_name)
        
        return None
    
    def shutdown(self) -> None:
        """Shutdown all plugins and cleanup resources."""
        logger.info("Shutting down plugin manager")
        
        # Stop all active plugins
        for plugin_name in list(self._instances.keys()):
            if self._instances[plugin_name].is_active:
                try:
                    self.stop_plugin(plugin_name)
                    self.destroy_plugin(plugin_name)
                except Exception as e:
                    logger.error(f"Error shutting down plugin {plugin_name}: {e}")
        
        # Clear registry
        self._registry.clear()
        
        # Clear instances
        self._instances.clear()
    
    # ILifecycleManager implementation
    
    def initialize_plugin(self, plugin_name: str, config: Dict[str, Any]) -> IPlugin:
        """Initialize a plugin instance with configuration."""
        if plugin_name not in self._instances:
            raise PluginNotFoundError(f"Plugin {plugin_name} not found")
        
        instance_info = self._instances[plugin_name]
        if instance_info.state == PluginState.ERROR:
            raise PluginInitError(f"Plugin {plugin_name} is in error state: {instance_info.error}")
        
        try:
            # Get plugin class
            plugin_class = self._registry.get_plugin(plugin_name)
            if not plugin_class:
                raise PluginInitError(f"Plugin class not found for {plugin_name}")
            
            # Create instance with sqlite_store if available
            if self.sqlite_store:
                # Try to pass sqlite_store to constructor
                try:
                    plugin_instance = plugin_class(sqlite_store=self.sqlite_store)
                except TypeError:
                    # Fallback to no-args constructor
                    plugin_instance = plugin_class()
            else:
                plugin_instance = plugin_class()
            
            # Store instance
            instance_info.instance = plugin_instance
            instance_info.state = PluginState.INITIALIZED
            
            logger.info(f"Initialized plugin: {plugin_name}")
            
            # Auto-start if configured
            if self.config.auto_load:
                self.start_plugin(plugin_name)
            
            return plugin_instance
            
        except Exception as e:
            instance_info.state = PluginState.ERROR
            instance_info.error = str(e)
            logger.error(f"Failed to initialize plugin {plugin_name}: {e}")
            raise PluginInitError(f"Failed to initialize plugin {plugin_name}: {str(e)}") from e
    
    def start_plugin(self, plugin_name: str) -> None:
        """Start a plugin (called after initialization)."""
        if plugin_name not in self._instances:
            raise PluginNotFoundError(f"Plugin {plugin_name} not found")
        
        instance_info = self._instances[plugin_name]
        if instance_info.state != PluginState.INITIALIZED:
            raise PluginInitError(f"Plugin {plugin_name} must be initialized before starting")
        
        try:
            # Call start method if it exists
            if hasattr(instance_info.instance, 'start'):
                instance_info.instance.start()
            
            instance_info.state = PluginState.STARTED
            logger.info(f"Started plugin: {plugin_name}")
            
        except Exception as e:
            instance_info.state = PluginState.ERROR
            instance_info.error = str(e)
            logger.error(f"Failed to start plugin {plugin_name}: {e}")
            raise
    
    def stop_plugin(self, plugin_name: str) -> None:
        """Stop a running plugin."""
        if plugin_name not in self._instances:
            raise PluginNotFoundError(f"Plugin {plugin_name} not found")
        
        instance_info = self._instances[plugin_name]
        if instance_info.state != PluginState.STARTED:
            logger.warning(f"Plugin {plugin_name} is not running")
            return
        
        try:
            # Call stop method if it exists
            if hasattr(instance_info.instance, 'stop'):
                instance_info.instance.stop()
            
            instance_info.state = PluginState.STOPPED
            logger.info(f"Stopped plugin: {plugin_name}")
            
        except Exception as e:
            logger.error(f"Error stopping plugin {plugin_name}: {e}")
            # Set to stopped anyway
            instance_info.state = PluginState.STOPPED
    
    def destroy_plugin(self, plugin_name: str) -> None:
        """Destroy a plugin instance and cleanup resources."""
        if plugin_name not in self._instances:
            raise PluginNotFoundError(f"Plugin {plugin_name} not found")
        
        instance_info = self._instances[plugin_name]
        
        try:
            # Call destroy method if it exists
            if instance_info.instance and hasattr(instance_info.instance, 'destroy'):
                instance_info.instance.destroy()
            
            # Clear instance
            instance_info.instance = None
            instance_info.state = PluginState.LOADED
            logger.info(f"Destroyed plugin instance: {plugin_name}")
            
        except Exception as e:
            logger.error(f"Error destroying plugin {plugin_name}: {e}")
    
    def get_plugin_instance(self, plugin_name: str) -> Optional[IPlugin]:
        """Get an active plugin instance."""
        if plugin_name not in self._instances:
            return None
        
        instance_info = self._instances[plugin_name]
        if instance_info.is_active:
            return instance_info.instance
        
        return None
    
    def get_active_plugins(self) -> Dict[str, IPlugin]:
        """Get all active plugin instances."""
        active = {}
        for name, instance_info in self._instances.items():
            if instance_info.is_active and instance_info.instance:
                active[name] = instance_info.instance
        return active
    
    def get_plugin_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status information for all plugins."""
        status = {}
        for name, instance_info in self._instances.items():
            status[name] = {
                'state': instance_info.state.value,
                'enabled': instance_info.config.enabled,
                'version': instance_info.info.version,
                'language': instance_info.info.language,
                'error': instance_info.error
            }
        return status