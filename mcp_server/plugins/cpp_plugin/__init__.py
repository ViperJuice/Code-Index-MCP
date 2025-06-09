"""C++ plugin for Code-Index-MCP."""

import os

# Use semantic plugin if enabled, otherwise fallback to basic plugin
if os.getenv("SEMANTIC_SEARCH_ENABLED", "false").lower() == "true":
    try:
        from .plugin_semantic import CppPluginSemantic as Plugin
    except ImportError:
        from .plugin import Plugin
else:
    from .plugin import Plugin

__all__ = ["Plugin"]
