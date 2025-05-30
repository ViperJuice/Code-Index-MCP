"""
Dart/Flutter plugin for the MCP server.

This plugin provides code intelligence for Dart and Flutter projects including:
- Symbol extraction (classes, functions, methods, variables, enums, mixins, extensions)
- Flutter-specific features (widgets, state classes, build methods)
- Import/export tracking
- Documentation extraction
- Search and reference finding

The plugin uses regex-based parsing since tree-sitter-dart is not currently
available in the tree-sitter-languages package, but is structured to easily
upgrade to tree-sitter parsing when available.
"""

from .plugin import Plugin

__all__ = ["Plugin"]