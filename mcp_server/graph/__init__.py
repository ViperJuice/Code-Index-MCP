"""Graph-based code analysis module."""

from .context_selector import ContextSelector
from .graph_analyzer import GraphAnalyzer
from .interfaces import (
    EdgeType,
    GraphCutResult,
    GraphEdge,
    GraphNode,
    IContextSelector,
    IGraphAnalyzer,
    IGraphBuilder,
)
from .xref_adapter import CHUNKER_AVAILABLE, XRefAdapter

__all__ = [
    # Interfaces
    "IGraphBuilder",
    "IGraphAnalyzer",
    "IContextSelector",
    # Data classes
    "EdgeType",
    "GraphNode",
    "GraphEdge",
    "GraphCutResult",
    # Implementations
    "XRefAdapter",
    "GraphAnalyzer",
    "ContextSelector",
    # Flags
    "CHUNKER_AVAILABLE",
]
