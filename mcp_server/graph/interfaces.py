"""Graph analysis interfaces and data structures."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class EdgeType(Enum):
    """Types of edges in the code graph."""

    CALLS = "calls"
    IMPORTS = "imports"
    INHERITS = "inherits"
    REFERENCES = "references"
    DEFINES = "defines"


@dataclass
class GraphNode:
    """Represents a node in the code graph."""

    id: str
    file_path: str
    language: str
    symbol: Optional[str] = None
    kind: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    attrs: Dict[str, Any] = field(default_factory=dict)
    score: float = 0.0


@dataclass
class GraphEdge:
    """Represents an edge in the code graph."""

    source_id: str
    target_id: str
    edge_type: EdgeType
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphCutResult:
    """Result of a graph cut operation."""

    selected_nodes: List[GraphNode]
    induced_edges: List[GraphEdge]
    seed_nodes: List[str]
    radius: int
    budget: int
    total_candidates: int
    execution_time_ms: float


class IGraphBuilder(ABC):
    """Interface for building code graphs."""

    @abstractmethod
    def build_graph(
        self, file_paths: List[str]
    ) -> tuple[List[GraphNode], List[GraphEdge]]:
        """
        Build a code graph from the given files.

        Args:
            file_paths: List of file paths to analyze

        Returns:
            Tuple of (nodes, edges)
        """
        pass


class IGraphAnalyzer(ABC):
    """Interface for analyzing code graphs."""

    @abstractmethod
    def find_dependencies(
        self, node_id: str, max_depth: int = 3
    ) -> List[GraphNode]:
        """
        Find all dependencies of a node.

        Args:
            node_id: ID of the node
            max_depth: Maximum depth to traverse

        Returns:
            List of dependent nodes
        """
        pass

    @abstractmethod
    def find_dependents(
        self, node_id: str, max_depth: int = 3
    ) -> List[GraphNode]:
        """
        Find all nodes that depend on this node.

        Args:
            node_id: ID of the node
            max_depth: Maximum depth to traverse

        Returns:
            List of nodes that depend on this node
        """
        pass

    @abstractmethod
    def find_path(
        self, source_id: str, target_id: str
    ) -> Optional[List[GraphNode]]:
        """
        Find shortest path between two nodes.

        Args:
            source_id: Source node ID
            target_id: Target node ID

        Returns:
            List of nodes forming the path, or None if no path exists
        """
        pass

    @abstractmethod
    def get_hotspots(self, top_n: int = 10) -> List[GraphNode]:
        """
        Get code hotspots (highly connected nodes).

        Args:
            top_n: Number of top hotspots to return

        Returns:
            List of hotspot nodes sorted by connectivity
        """
        pass


class IContextSelector(ABC):
    """Interface for selecting context using graph analysis."""

    @abstractmethod
    def select_context(
        self,
        seeds: List[str],
        radius: int = 2,
        budget: int = 200,
        weights: Optional[Dict[str, float]] = None,
    ) -> GraphCutResult:
        """
        Select optimal context around seed nodes.

        Args:
            seeds: Seed node IDs
            radius: Maximum distance from seeds
            budget: Maximum number of nodes to select
            weights: Scoring weights for graph cut

        Returns:
            GraphCutResult with selected nodes and edges
        """
        pass

    @abstractmethod
    def expand_search_results(
        self,
        search_results: List[Dict[str, Any]],
        expansion_radius: int = 1,
        max_context_nodes: int = 50,
    ) -> List[GraphNode]:
        """
        Expand search results with graph context.

        Args:
            search_results: Search results to expand
            expansion_radius: How far to expand
            max_context_nodes: Maximum context nodes to add

        Returns:
            List of context nodes
        """
        pass
