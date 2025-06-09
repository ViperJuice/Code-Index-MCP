"""Plugin system for MCP Server.

This package provides dynamic plugin discovery, loading, and lifecycle management.
"""

from .plugin_manager import PluginManager
from .models import (
    PluginInfo,
    PluginConfig,
    PluginState,
    PluginType,
    PluginSystemConfig,
    PluginError,
    PluginNotFoundError,
    PluginLoadError,
    PluginInitError,
    PluginValidationError,
    PluginConfigError
)
from .interfaces import (
    IPluginDiscovery,
    IPluginLoader,
    IPluginRegistry,
    ILifecycleManager,
    IPluginManager
)
from .discovery import PluginDiscovery, get_plugin_discovery
from .loader import PluginLoader, get_plugin_loader
from .config import PluginConfigManager, get_config_manager

__all__ = [
    # Main class
    'PluginManager',
    
    # Models
    'PluginInfo',
    'PluginConfig',
    'PluginState',
    'PluginType',
    'PluginSystemConfig',
    
    # Exceptions
    'PluginError',
    'PluginNotFoundError',
    'PluginLoadError',
    'PluginInitError',
    'PluginValidationError',
    'PluginConfigError',
    
    # Interfaces
    'IPluginDiscovery',
    'IPluginLoader',
    'IPluginRegistry',
    'ILifecycleManager',
    'IPluginManager',
    
    # Dynamic plugin system
    'PluginDiscovery',
    'get_plugin_discovery',
    'PluginLoader',
    'get_plugin_loader',
    'PluginConfigManager',
    'get_config_manager'
]