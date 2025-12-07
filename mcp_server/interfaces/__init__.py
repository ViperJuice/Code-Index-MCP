"""
MCP Server Interface Definitions

This package contains all interface definitions for the MCP Server, organized by module.
These interfaces define the contracts that enable parallel development across multiple agents
while maintaining clean architecture and preventing conflicts.

Interface Organization:
- shared_interfaces.py: Cross-cutting interfaces used by multiple modules
- api_gateway_interfaces.py: All API gateway related interfaces
- dispatcher_interfaces.py: All dispatcher and routing interfaces
- plugin_interfaces.py: All plugin system interfaces
- indexing_interfaces.py: All indexing engine interfaces
- storage_interfaces.py: All storage and persistence interfaces
- security_interfaces.py: All security and authentication interfaces
- metrics_interfaces.py: All metrics and monitoring interfaces
- cache_interfaces.py: All caching interfaces

Usage:
    from mcp_server.interfaces.plugin_interfaces import IPlugin
    from mcp_server.interfaces.shared_interfaces import ILogger, Result
"""

from .plugin_interfaces import (
    ILanguageAnalyzer,
    IPlugin,
    IPluginDiscovery,
    IPluginLoader,
    IPluginManager,
    IPluginRegistry,
)

# Re-export key interfaces for convenience
from .shared_interfaces import (
    Error,
    Event,
    IAsyncRepository,
    IAsyncSupport,
    ICache,
    IConfig,
    IEventBus,
    IFactory,
    ILogger,
    IMetrics,
    IndexStatus,
    IObservable,
    IObserver,
    IRepository,
    ISecurityContext,
    IValidator,
    LogLevel,
    PluginStatus,
    Result,
)

__all__ = [
    # Shared interfaces
    "ILogger",
    "IMetrics",
    "IConfig",
    "ICache",
    "IEventBus",
    "Result",
    "Error",
    "Event",
    "LogLevel",
    "IndexStatus",
    "PluginStatus",
    "ISecurityContext",
    "IValidator",
    "IAsyncSupport",
    "IRepository",
    "IAsyncRepository",
    "IFactory",
    "IObserver",
    "IObservable",
    # Plugin interfaces
    "IPlugin",
    "ILanguageAnalyzer",
    "IPluginRegistry",
    "IPluginManager",
    "IPluginLoader",
    "IPluginDiscovery",
]
