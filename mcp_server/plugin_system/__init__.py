"""Plugin system for MCP Server.

This package provides dynamic plugin discovery, loading, and lifecycle management.
"""

from .config import PluginConfigManager, get_config_manager
from .discovery import PluginDiscovery, get_plugin_discovery
from .interfaces import (
    ILifecycleManager,
    IPluginDiscovery,
    IPluginLoader,
    IPluginManager,
    IPluginRegistry,
)
from .loader import PluginLoader, get_plugin_loader
from .models import (
    PluginConfig,
    PluginConfigError,
    PluginError,
    PluginInfo,
    PluginInitError,
    PluginInstance,
    PluginLoadError,
    PluginNotFoundError,
    PluginState,
    PluginSystemConfig,
    PluginType,
    PluginValidationError,
)
from .plugin_manager import PluginManager

__all__ = [
    # Main class
    "PluginManager",
    # Models
    "PluginInfo",
    "PluginConfig",
    "PluginState",
    "PluginType",
    "PluginSystemConfig",
    "PluginInstance",
    # Exceptions
    "PluginError",
    "PluginNotFoundError",
    "PluginLoadError",
    "PluginInitError",
    "PluginValidationError",
    "PluginConfigError",
    # Interfaces
    "IPluginDiscovery",
    "IPluginLoader",
    "IPluginRegistry",
    "ILifecycleManager",
    "IPluginManager",
    # Dynamic plugin system
    "PluginDiscovery",
    "get_plugin_discovery",
    "PluginLoader",
    "get_plugin_loader",
    "PluginConfigManager",
    "get_config_manager",
]
