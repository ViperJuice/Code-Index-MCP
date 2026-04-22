"""Core infrastructure for MCP Server."""

from .errors import ConfigError, IndexError, MCPError, PluginError
from .logging import get_logger, setup_logging

__all__ = [
    "setup_logging",
    "get_logger",
    "MCPError",
    "PluginError",
    "IndexError",
    "ConfigError",
    "RepoContext",
    "RepoResolver",
]


def __getattr__(name: str):
    # Lazy re-exports to avoid a circular import with mcp_server.storage
    # (repo_context.py imports SQLiteStore at runtime for get_type_hints()
    # resolution; eager import at package load time creates a cycle when
    # mcp_server.storage is imported before mcp_server.core).
    if name == "RepoContext":
        from .repo_context import RepoContext

        return RepoContext
    if name == "RepoResolver":
        from .repo_resolver import RepoResolver

        return RepoResolver
    raise AttributeError(f"module 'mcp_server.core' has no attribute {name!r}")
