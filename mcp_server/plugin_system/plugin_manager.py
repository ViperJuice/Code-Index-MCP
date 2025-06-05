"""Plugin manager implementation."""

import logging
import os
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any, Type
from datetime import datetime

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
from ..interfaces.shared_interfaces import Result, Error

logger = logging.getLogger(__name__)


class PluginManager(IPluginManager, ILifecycleManager):
    """High-level plugin management and lifecycle operations."""
    
    def __init__(self, config: Optional[PluginSystemConfig] = None, sqlite_store: Optional[SQLiteStore] = None, tool_manager=None):
        self.config = config or self._get_default_config()
        self.sqlite_store = sqlite_store
        self.tool_manager = tool_manager  # MCP tool manager
        
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
        # Check if lazy loading is enabled
        lazy_loading = os.getenv("CODEX_LAZY_PLUGIN_LOADING", "false").lower() in ("true", "1", "yes")
        
        return PluginSystemConfig(
            plugin_dirs=[
                Path(__file__).parent.parent / "plugins"  # Default plugins directory
            ],
            auto_discover=True,
            auto_load=not lazy_loading,  # Disable auto_load if lazy loading is enabled
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
                # Apply environment-specific overrides
                self.config.apply_environment_overrides()
                logger.info(f"Loaded plugin configuration from {config_path}")
                logger.debug(f"Configuration: auto_discover={self.config.auto_discover}, "
                           f"auto_load={self.config.auto_load}, hot_reload={self.config.enable_hot_reload}")
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
                    
                    # Create instance record with timing
                    import time
                    start_time = time.time()
                    
                    instance = PluginInstance(
                        info=plugin_info,
                        config=plugin_config,
                        instance=None,
                        state=PluginState.LOADED,
                        load_time=time.time() - start_time
                    )
                    self._instances[plugin_info.name] = instance
                    
                    # Auto-initialize if configured
                    if self.config.auto_load and plugin_config.enabled:
                        self.initialize_plugin(plugin_info.name, plugin_config.settings)
                        
                except Exception as e:
                    logger.error(f"Failed to load plugin {plugin_info.name}: {e}")

    def prepare_plugins_for_lazy_loading(self, config_path: Optional[Path] = None) -> None:
        """Prepare plugins for lazy loading - discover and register but don't initialize."""
        if config_path:
            self._load_config_file(config_path)
        
        if self.config.auto_discover:
            # Discover plugins
            discovered = self._discovery.discover_plugins(self.config.plugin_dirs)
            logger.info(f"Discovered {len(discovered)} plugins for lazy loading")
            
            # Register each discovered plugin without initializing
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
                    
                    # Create instance record without initialization
                    instance = PluginInstance(
                        info=plugin_info,
                        config=plugin_config,
                        instance=None,
                        state=PluginState.DISCOVERED,  # New state for discovered but not loaded
                        load_time=0
                    )
                    self._instances[plugin_info.name] = instance
                    
                    logger.debug(f"Prepared plugin {plugin_info.name} for lazy loading")
                        
                except Exception as e:
                    logger.error(f"Failed to prepare plugin {plugin_info.name} for lazy loading: {e}")
    
    def load_plugins_safe(self, config_path: Optional[Path] = None) -> Result[List[PluginLoadResult]]:
        """Load plugins using Result pattern for error handling."""
        try:
            results = []
            if config_path:
                self._load_config_file(config_path)
            
            if self.config.auto_discover:
                discovered = self._discovery.discover_plugins(self.config.plugin_dirs)
                logger.info(f"Discovered {len(discovered)} plugins")
                
                for plugin_info in discovered:
                    if plugin_info.name in self.config.disabled_plugins:
                        results.append(PluginLoadResult(
                            success=False,
                            plugin_name=plugin_info.name,
                            message="Plugin is disabled"
                        ))
                        continue
                    
                    try:
                        plugin_class = self._loader.load_plugin(plugin_info)
                        self._registry.register_plugin(plugin_info, plugin_class)
                        
                        plugin_config = self.config.plugin_configs.get(
                            plugin_info.name,
                            PluginConfig()
                        )
                        
                        instance = PluginInstance(
                            info=plugin_info,
                            config=plugin_config,
                            instance=None,
                            state=PluginState.LOADED
                        )
                        self._instances[plugin_info.name] = instance
                        
                        if self.config.auto_load and plugin_config.enabled:
                            self.initialize_plugin(plugin_info.name, plugin_config.settings)
                        
                        results.append(PluginLoadResult(
                            success=True,
                            plugin_name=plugin_info.name,
                            message="Plugin loaded successfully"
                        ))
                        
                    except Exception as e:
                        results.append(PluginLoadResult(
                            success=False,
                            plugin_name=plugin_info.name,
                            message=f"Failed to load: {str(e)}",
                            error=e
                        ))
            
            successful_loads = sum(1 for r in results if r.success)
            return Result.success_result(
                results,
                metadata={
                    'total_discovered': len(results),
                    'successful_loads': successful_loads,
                    'failed_loads': len(results) - successful_loads,
                    'load_time': datetime.now().isoformat()
                }
            )
        except Exception as e:
            error = Error(
                code="PLUGIN_LOAD_BATCH_ERROR",
                message="Failed to load plugins",
                details={
                    'config_path': str(config_path) if config_path else None,
                    'error_type': type(e).__name__,
                    'error_message': str(e)
                },
                timestamp=datetime.now()
            )
            return Result.error_result(error)
    
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
    
    def reload_plugin_safe(self, plugin_name: str) -> Result[None]:
        """Reload a plugin using Result pattern for error handling."""
        try:
            self.reload_plugin(plugin_name)
            return Result.success_result(
                None,
                metadata={
                    'plugin_name': plugin_name,
                    'reloaded_at': datetime.now().isoformat()
                }
            )
        except Exception as e:
            error = Error(
                code="PLUGIN_RELOAD_ERROR",
                message=f"Failed to reload plugin {plugin_name}",
                details={
                    'plugin_name': plugin_name,
                    'error_type': type(e).__name__,
                    'error_message': str(e)
                },
                timestamp=datetime.now()
            )
            return Result.error_result(error)
    
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
    
    def enable_plugin_safe(self, plugin_name: str) -> Result[None]:
        """Enable a plugin using Result pattern for error handling."""
        try:
            self.enable_plugin(plugin_name)
            return Result.success_result(
                None,
                metadata={
                    'plugin_name': plugin_name,
                    'enabled_at': datetime.now().isoformat()
                }
            )
        except Exception as e:
            error = Error(
                code="PLUGIN_ENABLE_ERROR",
                message=f"Failed to enable plugin {plugin_name}",
                details={
                    'plugin_name': plugin_name,
                    'error_type': type(e).__name__,
                    'error_message': str(e)
                },
                timestamp=datetime.now()
            )
            return Result.error_result(error)
    
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
    
    def disable_plugin_safe(self, plugin_name: str) -> Result[None]:
        """Disable a plugin using Result pattern for error handling."""
        try:
            self.disable_plugin(plugin_name)
            return Result.success_result(
                None,
                metadata={
                    'plugin_name': plugin_name,
                    'disabled_at': datetime.now().isoformat()
                }
            )
        except Exception as e:
            error = Error(
                code="PLUGIN_DISABLE_ERROR",
                message=f"Failed to disable plugin {plugin_name}",
                details={
                    'plugin_name': plugin_name,
                    'error_type': type(e).__name__,
                    'error_message': str(e)
                },
                timestamp=datetime.now()
            )
            return Result.error_result(error)
    
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
    
    def shutdown_safe(self) -> Result[None]:
        """Shutdown all plugins using Result pattern for error handling."""
        try:
            self.shutdown()
            return Result.success_result(
                None,
                metadata={
                    'shutdown_at': datetime.now().isoformat()
                }
            )
        except Exception as e:
            error = Error(
                code="PLUGIN_SHUTDOWN_ERROR",
                message="Failed to shutdown plugin manager",
                details={
                    'error_type': type(e).__name__,
                    'error_message': str(e)
                },
                timestamp=datetime.now()
            )
            return Result.error_result(error)
    
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
            
            # Register MCP tools if available
            self._register_plugin_tools(plugin_name, plugin_instance)
            
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
    
    def get_detailed_plugin_status(self) -> Dict[str, Dict[str, Any]]:
        """Get detailed status information for all plugins."""
        status = {}
        for name, instance_info in self._instances.items():
            status[name] = {
                'basic_info': {
                    'name': instance_info.info.name,
                    'version': instance_info.info.version,
                    'description': instance_info.info.description,
                    'author': instance_info.info.author,
                    'language': instance_info.info.language,
                    'file_extensions': instance_info.info.file_extensions,
                    'plugin_type': instance_info.info.plugin_type.value
                },
                'runtime_info': {
                    'state': instance_info.state.value,
                    'enabled': instance_info.config.enabled,
                    'priority': instance_info.config.priority,
                    'is_active': instance_info.is_active,
                    'is_healthy': instance_info.is_healthy,
                    'error': instance_info.error,
                    'load_time': instance_info.load_time,
                    'last_health_check': instance_info.last_health_check,
                    'health_status': instance_info.health_status
                },
                'config': {
                    'settings': instance_info.config.settings,
                    'dependencies': instance_info.config.dependencies,
                    'health_check': instance_info.config.health_check
                },
                'metrics': instance_info.metrics
            }
        return status
    
    def get_plugins_by_status(self, state: PluginState) -> List[str]:
        """Get list of plugin names by their state."""
        return [
            name for name, instance in self._instances.items()
            if instance.state == state
        ]
    
    def get_enabled_plugins(self) -> List[str]:
        """Get list of enabled plugin names."""
        return [
            name for name, instance in self._instances.items()
            if instance.config.enabled
        ]
    
    def get_plugins_by_language(self, language: str) -> List[str]:
        """Get plugin names that support a specific language."""
        plugin_names = self._registry.get_plugins_by_language(language)
        
        # Filter to only return active plugins
        active_plugins = []
        for name in plugin_names:
            instance = self.get_plugin_instance(name)
            if instance:
                active_plugins.append(name)
        
        return active_plugins
    
    def get_plugins_by_extension(self, extension: str) -> List[str]:
        """Get plugin names that support a specific file extension."""
        plugin_names = self._registry.get_plugins_by_extension(extension)
        
        # Filter to only return active plugins
        active_plugins = []
        for name in plugin_names:
            instance = self.get_plugin_instance(name)
            if instance:
                active_plugins.append(name)
        
        return active_plugins
    
    def _register_plugin_tools(self, plugin_name: str, plugin_instance: IPlugin):
        """Register MCP tools provided by a plugin."""
        if not self.tool_manager:
            return
        
        # Check if plugin provides MCP tools
        if hasattr(plugin_instance, 'get_mcp_tools'):
            try:
                tools = plugin_instance.get_mcp_tools()
                if tools:
                    # Import the required classes
                    from ..tools.base import MCPTool, ToolHandler
                    
                    # Register each tool
                    for tool_def in tools:
                        if isinstance(tool_def, dict):
                            # Create MCPTool from dict
                            tool = MCPTool(
                                name=f"{plugin_name}_{tool_def['name']}",
                                description=tool_def.get('description', ''),
                                inputSchema=tool_def.get('inputSchema', {}),
                                metadata={'plugin': plugin_name}
                            )
                            
                            # Create handler wrapper
                            handler_func = tool_def.get('handler')
                            if handler_func:
                                class PluginToolHandler(ToolHandler):
                                    def __init__(self, func):
                                        self.func = func
                                    
                                    async def execute(self, params):
                                        return await self.func(params)
                                
                                handler = PluginToolHandler(handler_func)
                                self.tool_manager.register_tool(tool, handler)
                                logger.info(f"Registered MCP tool '{tool.name}' from plugin {plugin_name}")
                        
            except Exception as e:
                logger.error(f"Failed to register MCP tools for plugin {plugin_name}: {e}")