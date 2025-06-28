"""
Markdown plugin for the MCP Server.

This plugin provides comprehensive Markdown document processing capabilities including:
- Markdown AST parsing and structure extraction
- Hierarchical section extraction
- YAML/TOML frontmatter parsing
- Smart document chunking strategies
- Integration with semantic search
"""

from .plugin import MarkdownPlugin

__all__ = ["MarkdownPlugin"]
