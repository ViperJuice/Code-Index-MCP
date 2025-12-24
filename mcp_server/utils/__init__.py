"""
Utility modules for MCP Server.

This package contains various utility functions and classes used throughout
the MCP server implementation.
"""

from .fuzzy_indexer import FuzzyIndexer
from .index_discovery import IndexDiscovery
from .token_counter import TokenCounter, compare_model_costs, quick_estimate

# SemanticIndexer requires optional dependencies (voyageai, qdrant-client)
# Use lazy import to avoid ImportError when semantic deps not installed
_SemanticIndexer = None


def get_semantic_indexer():
    """Get SemanticIndexer class if semantic dependencies are available.

    Returns:
        SemanticIndexer class or None if dependencies not installed.
    """
    global _SemanticIndexer
    if _SemanticIndexer is None:
        try:
            from .semantic_indexer import SemanticIndexer

            _SemanticIndexer = SemanticIndexer
        except ImportError:
            return None
    return _SemanticIndexer


__all__ = [
    "FuzzyIndexer",
    "IndexDiscovery",
    "get_semantic_indexer",
    "TokenCounter",
    "quick_estimate",
    "compare_model_costs",
]
