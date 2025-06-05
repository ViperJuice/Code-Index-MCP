"""Utility modules for the MCP server."""

# Import only what's needed to avoid circular imports
from .smart_parser import SmartParser
from .treesitter_wrapper import TreeSitterWrapper
from .treesitter_manager import TreeSitterManager, tree_sitter_manager
from .fuzzy_indexer import FuzzyIndexer

__all__ = [
    'SmartParser',
    'TreeSitterWrapper',
    'TreeSitterManager',
    'tree_sitter_manager',
    'FuzzyIndexer',
]