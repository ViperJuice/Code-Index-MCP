"""MCP Server - Local-first code indexer for LLMs."""

# Version information
__version__ = "1.0.0"

# Public API exports
__all__ = [
    "__version__",
    "SQLiteStore",
    "EnhancedDispatcher",
    "PluginFactory",
]


# Lazy imports to avoid circular dependencies
# Usage examples:
#   from mcp_server import __version__
#   from mcp_server import SQLiteStore
#   from mcp_server import EnhancedDispatcher, PluginFactory
def __getattr__(name):
    """Lazy import public API components to avoid circular import issues."""
    if name == "SQLiteStore":
        from .storage.sqlite_store import SQLiteStore

        return SQLiteStore
    if name == "EnhancedDispatcher":
        from .dispatcher.dispatcher_enhanced import EnhancedDispatcher

        return EnhancedDispatcher
    if name == "PluginFactory":
        from .plugins.plugin_factory import PluginFactory

        return PluginFactory
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
