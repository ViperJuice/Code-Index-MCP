"""Plugin registry implementation."""

import logging
from typing import Dict, List, Optional, Type

from ..plugin_base import IPlugin
from .interfaces import IPluginRegistry
from .models import PluginInfo, PluginNotFoundError

logger = logging.getLogger(__name__)


class PluginRegistry(IPluginRegistry):
    """Manages plugin registration and metadata."""
    
    def __init__(self):
        self._plugins: Dict[str, Type[IPlugin]] = {}
        self._plugin_info: Dict[str, PluginInfo] = {}
        self._language_map: Dict[str, List[str]] = {}  # language -> plugin names
        self._extension_map: Dict[str, List[str]] = {}  # extension -> plugin names
    
    def register_plugin(self, plugin_info: PluginInfo, plugin_class: Type[IPlugin]) -> None:
        """Register a plugin with its metadata."""
        plugin_name = plugin_info.name
        
        if plugin_name in self._plugins:
            logger.warning(f"Plugin {plugin_name} is already registered, overwriting")
        
        # Store plugin class and info
        self._plugins[plugin_name] = plugin_class
        self._plugin_info[plugin_name] = plugin_info
        
        # Update language mapping
        if plugin_info.language:
            if plugin_info.language not in self._language_map:
                self._language_map[plugin_info.language] = []
            if plugin_name not in self._language_map[plugin_info.language]:
                self._language_map[plugin_info.language].append(plugin_name)
        
        # Update extension mapping
        for ext in plugin_info.file_extensions:
            if ext not in self._extension_map:
                self._extension_map[ext] = []
            if plugin_name not in self._extension_map[ext]:
                self._extension_map[ext].append(plugin_name)
        
        logger.info(f"Registered plugin: {plugin_name} (language: {plugin_info.language}, "
                   f"extensions: {', '.join(plugin_info.file_extensions)})")
    
    def unregister_plugin(self, plugin_name: str) -> None:
        """Unregister a plugin."""
        if plugin_name not in self._plugins:
            raise PluginNotFoundError(f"Plugin {plugin_name} not found")
        
        # Get plugin info for cleanup
        plugin_info = self._plugin_info[plugin_name]
        
        # Remove from main registry
        del self._plugins[plugin_name]
        del self._plugin_info[plugin_name]
        
        # Remove from language mapping
        if plugin_info.language and plugin_info.language in self._language_map:
            self._language_map[plugin_info.language].remove(plugin_name)
            if not self._language_map[plugin_info.language]:
                del self._language_map[plugin_info.language]
        
        # Remove from extension mapping
        for ext in plugin_info.file_extensions:
            if ext in self._extension_map:
                self._extension_map[ext].remove(plugin_name)
                if not self._extension_map[ext]:
                    del self._extension_map[ext]
        
        logger.info(f"Unregistered plugin: {plugin_name}")
    
    def get_plugin(self, plugin_name: str) -> Optional[Type[IPlugin]]:
        """Get a registered plugin class by name."""
        return self._plugins.get(plugin_name)
    
    def get_all_plugins(self) -> Dict[str, Type[IPlugin]]:
        """Get all registered plugins."""
        return self._plugins.copy()
    
    def get_plugin_info(self, plugin_name: str) -> Optional[PluginInfo]:
        """Get metadata for a plugin."""
        return self._plugin_info.get(plugin_name)
    
    def list_plugins(self) -> List[PluginInfo]:
        """List all registered plugins with their metadata."""
        return list(self._plugin_info.values())
    
    def get_plugins_by_language(self, language: str) -> List[str]:
        """Get plugin names that support a specific language."""
        return self._language_map.get(language, []).copy()
    
    def get_plugins_by_extension(self, extension: str) -> List[str]:
        """Get plugin names that support a specific file extension."""
        # Normalize extension
        if not extension.startswith('.'):
            extension = f'.{extension}'
        return self._extension_map.get(extension, []).copy()
    
    def get_plugin_for_file(self, file_path: str) -> Optional[str]:
        """Get the best plugin name for a given file path."""
        from pathlib import Path
        path = Path(file_path)
        extension = path.suffix.lower()
        
        plugin_names = self.get_plugins_by_extension(extension)
        if plugin_names:
            # Return the first one (could be improved with priority)
            return plugin_names[0]
        
        return None
    
    def clear(self) -> None:
        """Clear all registered plugins."""
        self._plugins.clear()
        self._plugin_info.clear()
        self._language_map.clear()
        self._extension_map.clear()
        logger.info("Cleared plugin registry")