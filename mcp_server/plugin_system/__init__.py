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
    'IPluginManager'
]