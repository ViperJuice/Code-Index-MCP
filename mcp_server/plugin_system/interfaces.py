"""Plugin system interfaces.

This module defines all the interfaces for the plugin system components,
following the architecture defined in level3_mcp_components.dsl.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type

from ..interfaces.shared_interfaces import Result
from ..plugin_base import IPlugin

if TYPE_CHECKING:
    from .models import PluginInfo


class IPluginDiscovery(ABC):
    """Interface for discovering plugins in the filesystem."""

    @abstractmethod
    def discover_plugins(self, plugin_dirs: List[Path]) -> List["PluginInfo"]:
        """Discover all plugins in the specified directories.

        Args:
            plugin_dirs: List of directories to search for plugins

        Returns:
            List of discovered plugin information
        """

    @abstractmethod
    def validate_plugin(self, plugin_path: Path) -> bool:
        """Validate if a path contains a valid plugin.

        Args:
            plugin_path: Path to the potential plugin

        Returns:
            True if valid plugin, False otherwise
        """

    def discover_plugins_safe(self, plugin_dirs: List[Path]) -> Result[List["PluginInfo"]]:
        """Discover plugins using Result pattern for error handling."""

    def validate_plugin_safe(self, plugin_path: Path) -> Result[bool]:
        """Validate a plugin using Result pattern for error handling."""


class IPluginLoader(ABC):
    """Interface for dynamically loading plugin modules."""

    @abstractmethod
    def load_plugin(self, plugin_info: "PluginInfo") -> Type[IPlugin]:
        """Load a plugin class from the given plugin information.

        Args:
            plugin_info: Information about the plugin to load

        Returns:
            The loaded plugin class

        Raises:
            PluginLoadError: If the plugin cannot be loaded
        """

    @abstractmethod
    def unload_plugin(self, plugin_name: str) -> None:
        """Unload a plugin module.

        Args:
            plugin_name: Name of the plugin to unload
        """

    def load_plugin_safe(self, plugin_info: "PluginInfo") -> Result[Type[IPlugin]]:
        """Load a plugin using Result pattern for error handling."""

    def unload_plugin_safe(self, plugin_name: str) -> Result[None]:
        """Unload a plugin using Result pattern for error handling."""


class IPluginRegistry(ABC):
    """Interface for managing plugin registration and metadata."""

    @abstractmethod
    def register_plugin(self, plugin_info: "PluginInfo", plugin_class: Type[IPlugin]) -> None:
        """Register a plugin with its metadata.

        Args:
            plugin_info: Plugin metadata
            plugin_class: The plugin class
        """

    @abstractmethod
    def unregister_plugin(self, plugin_name: str) -> None:
        """Unregister a plugin.

        Args:
            plugin_name: Name of the plugin to unregister
        """

    @abstractmethod
    def get_plugin(self, plugin_name: str) -> Optional[Type[IPlugin]]:
        """Get a registered plugin class by name.

        Args:
            plugin_name: Name of the plugin

        Returns:
            Plugin class if found, None otherwise
        """

    @abstractmethod
    def get_all_plugins(self) -> Dict[str, Type[IPlugin]]:
        """Get all registered plugins.

        Returns:
            Dictionary mapping plugin names to plugin classes
        """

    @abstractmethod
    def get_plugin_info(self, plugin_name: str) -> Optional["PluginInfo"]:
        """Get metadata for a plugin.

        Args:
            plugin_name: Name of the plugin

        Returns:
            Plugin metadata if found, None otherwise
        """

    @abstractmethod
    def list_plugins(self) -> List["PluginInfo"]:
        """List all registered plugins with their metadata.

        Returns:
            List of plugin information
        """

    def register_plugin_safe(
        self, plugin_info: "PluginInfo", plugin_class: Type[IPlugin]
    ) -> Result[None]:
        """Register a plugin using Result pattern for error handling."""

    def unregister_plugin_safe(self, plugin_name: str) -> Result[None]:
        """Unregister a plugin using Result pattern for error handling."""


class ILifecycleManager(ABC):
    """Interface for managing plugin lifecycle events."""

    @abstractmethod
    def initialize_plugin(self, plugin_name: str, config: Dict[str, Any]) -> IPlugin:
        """Initialize a plugin instance with configuration.

        Args:
            plugin_name: Name of the plugin to initialize
            config: Plugin-specific configuration

        Returns:
            Initialized plugin instance

        Raises:
            PluginNotFoundError: If plugin not found
            PluginInitError: If initialization fails
        """

    @abstractmethod
    def start_plugin(self, plugin_name: str) -> None:
        """Start a plugin (called after initialization).

        Args:
            plugin_name: Name of the plugin to start
        """

    @abstractmethod
    def stop_plugin(self, plugin_name: str) -> None:
        """Stop a running plugin.

        Args:
            plugin_name: Name of the plugin to stop
        """

    @abstractmethod
    def destroy_plugin(self, plugin_name: str) -> None:
        """Destroy a plugin instance and cleanup resources.

        Args:
            plugin_name: Name of the plugin to destroy
        """

    @abstractmethod
    def get_plugin_instance(self, plugin_name: str) -> Optional[IPlugin]:
        """Get an active plugin instance.

        Args:
            plugin_name: Name of the plugin

        Returns:
            Plugin instance if active, None otherwise
        """

    @abstractmethod
    def get_active_plugins(self) -> Dict[str, IPlugin]:
        """Get all active plugin instances.

        Returns:
            Dictionary mapping plugin names to instances
        """


class IPluginManager(ABC):
    """High-level interface for plugin management operations."""

    @abstractmethod
    def load_plugins(self, config_path: Optional[Path] = None) -> None:
        """Load and initialize all plugins based on configuration.

        Args:
            config_path: Optional path to plugin configuration file
        """

    @abstractmethod
    def reload_plugin(self, plugin_name: str) -> None:
        """Reload a specific plugin.

        Args:
            plugin_name: Name of the plugin to reload
        """

    @abstractmethod
    def enable_plugin(self, plugin_name: str) -> None:
        """Enable a disabled plugin.

        Args:
            plugin_name: Name of the plugin to enable
        """

    @abstractmethod
    def disable_plugin(self, plugin_name: str) -> None:
        """Disable an active plugin.

        Args:
            plugin_name: Name of the plugin to disable
        """

    @abstractmethod
    def get_plugin_by_language(self, language: str) -> Optional[IPlugin]:
        """Get a plugin instance that supports the given language.

        Args:
            language: Programming language

        Returns:
            Plugin instance if found, None otherwise
        """

    @abstractmethod
    def get_plugin_for_file(self, file_path: Path) -> Optional[IPlugin]:
        """Get a plugin instance that supports the given file.

        Args:
            file_path: Path to the file

        Returns:
            Plugin instance if found, None otherwise
        """

    @abstractmethod
    def shutdown(self) -> None:
        """Shutdown all plugins and cleanup resources."""


# Hook interfaces for extensibility
class IPluginHook(ABC):
    """Base interface for plugin hooks."""

    @abstractmethod
    def execute(self, *args, **kwargs) -> Any:
        """Execute the hook."""


class IPreLoadHook(IPluginHook):
    """Hook executed before a plugin is loaded."""

    @abstractmethod
    def execute(self, plugin_info: "PluginInfo") -> None:
        """Execute pre-load actions.

        Args:
            plugin_info: Information about the plugin to be loaded
        """


class IPostLoadHook(IPluginHook):
    """Hook executed after a plugin is loaded."""

    @abstractmethod
    def execute(self, plugin_info: "PluginInfo", plugin_class: Type[IPlugin]) -> None:
        """Execute post-load actions.

        Args:
            plugin_info: Information about the loaded plugin
            plugin_class: The loaded plugin class
        """


class IPluginValidator(ABC):
    """Interface for validating plugin implementations."""

    @abstractmethod
    def validate_interface(self, plugin_class: Type[IPlugin]) -> bool:
        """Validate that a plugin class properly implements IPlugin.

        Args:
            plugin_class: Plugin class to validate

        Returns:
            True if valid, False otherwise
        """

    @abstractmethod
    def validate_metadata(self, plugin_info: "PluginInfo") -> bool:
        """Validate plugin metadata.

        Args:
            plugin_info: Plugin metadata to validate

        Returns:
            True if valid, False otherwise
        """
