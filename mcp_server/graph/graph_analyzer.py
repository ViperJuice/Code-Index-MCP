"""Graph analyzer for code dependency analysis."""

import logging
from collections import defaultdict, deque
from typing import Dict, List, Optional, Set

from .interfaces import GraphEdge, GraphNode, IGraphAnalyzer

logger = logging.getLogger(__name__)


class GraphAnalyzer(IGraphAnalyzer):
    """Analyzes code graphs for dependencies and patterns."""

    def __init__(self, nodes: List[GraphNode], edges: List[GraphEdge]):
        """
        Initialize the graph analyzer.

        Args:
            nodes: Graph nodes
            edges: Graph edges
        """
        self.nodes = nodes
        self.edges = edges

        # Build lookup structures
        self._node_map: Dict[str, GraphNode] = {n.id: n for n in nodes}
        self._out_edges: Dict[str, List[GraphEdge]] = defaultdict(list)
        self._in_edges: Dict[str, List[GraphEdge]] = defaultdict(list)

        for edge in edges:
            self._out_edges[edge.source_id].append(edge)
            self._in_edges[edge.target_id].append(edge)

        logger.debug(
            f"GraphAnalyzer initialized: {len(nodes)} nodes, {len(edges)} edges"
        )

    def find_dependencies(
        self, node_id: str, max_depth: int = 3
    ) -> List[GraphNode]:
        """
        Find all dependencies of a node using BFS.

        Args:
            node_id: ID of the node
            max_depth: Maximum depth to traverse

        Returns:
            List of dependent nodes
        """
        if node_id not in self._node_map:
            logger.warning(f"Node not found: {node_id}")
            return []

        visited: Set[str] = set()
        queue: deque = deque([(node_id, 0)])
        dependencies: List[GraphNode] = []

        while queue:
            current_id, depth = queue.popleft()

            if current_id in visited:
                continue

            visited.add(current_id)

            # Don't include the seed node itself
            if current_id != node_id:
                node = self._node_map.get(current_id)
                if node:
                    dependencies.append(node)

            # Stop if we've reached max depth
            if depth >= max_depth:
                continue

            # Add outgoing edges (dependencies)
            for edge in self._out_edges.get(current_id, []):
                if edge.target_id not in visited:
                    queue.append((edge.target_id, depth + 1))

        logger.debug(
            f"Found {len(dependencies)} dependencies for {node_id} (max_depth={max_depth})"
        )
        return dependencies

    def find_dependents(
        self, node_id: str, max_depth: int = 3
    ) -> List[GraphNode]:
        """
        Find all nodes that depend on this node using BFS.

        Args:
            node_id: ID of the node
            max_depth: Maximum depth to traverse

        Returns:
            List of nodes that depend on this node
        """
        if node_id not in self._node_map:
            logger.warning(f"Node not found: {node_id}")
            return []

        visited: Set[str] = set()
        queue: deque = deque([(node_id, 0)])
        dependents: List[GraphNode] = []

        while queue:
            current_id, depth = queue.popleft()

            if current_id in visited:
                continue

            visited.add(current_id)

            # Don't include the seed node itself
            if current_id != node_id:
                node = self._node_map.get(current_id)
                if node:
                    dependents.append(node)

            # Stop if we've reached max depth
            if depth >= max_depth:
                continue

            # Add incoming edges (dependents)
            for edge in self._in_edges.get(current_id, []):
                if edge.source_id not in visited:
                    queue.append((edge.source_id, depth + 1))

        logger.debug(
            f"Found {len(dependents)} dependents for {node_id} (max_depth={max_depth})"
        )
        return dependents

    def find_path(
        self, source_id: str, target_id: str
    ) -> Optional[List[GraphNode]]:
        """
        Find shortest path between two nodes using BFS.

        Args:
            source_id: Source node ID
            target_id: Target node ID

        Returns:
            List of nodes forming the path, or None if no path exists
        """
        if source_id not in self._node_map or target_id not in self._node_map:
            logger.warning(f"Source or target node not found")
            return None

        if source_id == target_id:
            return [self._node_map[source_id]]

        visited: Set[str] = set()
        queue: deque = deque([(source_id, [source_id])])

        while queue:
            current_id, path = queue.popleft()

            if current_id in visited:
                continue

            visited.add(current_id)

            # Check if we reached the target
            if current_id == target_id:
                return [self._node_map[nid] for nid in path]

            # Explore neighbors
            for edge in self._out_edges.get(current_id, []):
                if edge.target_id not in visited:
                    queue.append((edge.target_id, path + [edge.target_id]))

        logger.debug(f"No path found between {source_id} and {target_id}")
        return None

    def get_hotspots(self, top_n: int = 10) -> List[GraphNode]:
        """
        Get code hotspots (highly connected nodes) based on degree centrality.

        Args:
            top_n: Number of top hotspots to return

        Returns:
            List of hotspot nodes sorted by connectivity
        """
        # Calculate degree centrality for each node
        node_degrees: Dict[str, int] = defaultdict(int)

        for node_id in self._node_map.keys():
            in_degree = len(self._in_edges.get(node_id, []))
            out_degree = len(self._out_edges.get(node_id, []))
            node_degrees[node_id] = in_degree + out_degree

        # Sort by degree
        sorted_nodes = sorted(
            node_degrees.items(), key=lambda x: x[1], reverse=True
        )

        # Get top N nodes
        hotspots = []
        for node_id, degree in sorted_nodes[:top_n]:
            node = self._node_map.get(node_id)
            if node:
                # Set score to degree for reference
                node.score = float(degree)
                hotspots.append(node)

        logger.debug(f"Found {len(hotspots)} hotspots (top_n={top_n})")
        return hotspots
