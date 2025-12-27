"""Context selector using graph-based analysis."""

import logging
import time
from collections import defaultdict, deque
from typing import Any, Dict, List, Optional, Set

from .interfaces import (
    EdgeType,
    GraphCutResult,
    GraphEdge,
    GraphNode,
    IContextSelector,
)

logger = logging.getLogger(__name__)

# Check if TreeSitter Chunker graph cut is available
GRAPH_CUT_AVAILABLE = False
try:
    from chunker.graph.cut import graph_cut

    GRAPH_CUT_AVAILABLE = True
    logger.info("TreeSitter Chunker graph_cut available")
except ImportError:
    logger.warning("TreeSitter Chunker graph_cut not available, using fallback")


class ContextSelector(IContextSelector):
    """Selects optimal context using graph analysis."""

    def __init__(self, nodes: List[GraphNode], edges: List[GraphEdge]):
        """
        Initialize the context selector.

        Args:
            nodes: Graph nodes
            edges: Graph edges
        """
        self.nodes = nodes
        self.edges = edges
        self._node_map: Dict[str, GraphNode] = {n.id: n for n in nodes}

        logger.debug(
            f"ContextSelector initialized: {len(nodes)} nodes, {len(edges)} edges"
        )

    def select_context(
        self,
        seeds: List[str],
        radius: int = 2,
        budget: int = 200,
        weights: Optional[Dict[str, float]] = None,
    ) -> GraphCutResult:
        """
        Select optimal context around seed nodes.

        Uses TreeSitter Chunker's graph_cut if available, otherwise falls back to BFS.

        Args:
            seeds: Seed node IDs
            radius: Maximum distance from seeds
            budget: Maximum number of nodes to select
            weights: Scoring weights for graph cut

        Returns:
            GraphCutResult with selected nodes and edges
        """
        start_time = time.time()

        if GRAPH_CUT_AVAILABLE:
            result = self._select_with_graph_cut(seeds, radius, budget, weights)
        else:
            result = self._select_with_bfs(seeds, radius, budget)

        execution_time = (time.time() - start_time) * 1000  # Convert to ms
        result.execution_time_ms = execution_time

        logger.info(
            f"Selected {len(result.selected_nodes)} nodes in {execution_time:.2f}ms "
            f"(seeds={len(seeds)}, radius={radius}, budget={budget})"
        )

        return result

    def _select_with_graph_cut(
        self,
        seeds: List[str],
        radius: int,
        budget: int,
        weights: Optional[Dict[str, float]],
    ) -> GraphCutResult:
        """
        Select context using TreeSitter Chunker's graph_cut.

        Args:
            seeds: Seed node IDs
            radius: Maximum distance from seeds
            budget: Maximum number of nodes to select
            weights: Scoring weights

        Returns:
            GraphCutResult
        """
        # Convert nodes and edges to chunker format
        raw_nodes = []
        for node in self.nodes:
            raw_nodes.append(
                {
                    "id": node.id,
                    "file": node.file_path,
                    "lang": node.language,
                    "symbol": node.symbol,
                    "kind": node.kind,
                    "attrs": node.attrs,
                }
            )

        raw_edges = []
        for edge in self.edges:
            raw_edges.append(
                {
                    "src": edge.source_id,
                    "dst": edge.target_id,
                    "type": edge.edge_type.value,
                    "weight": edge.weight,
                }
            )

        # Call graph_cut
        selected_ids, induced_edges_raw = graph_cut(
            seeds=seeds,
            nodes=raw_nodes,
            edges=raw_edges,
            radius=radius,
            budget=budget,
            weights=weights or {},
        )

        # Convert results back to our format
        selected_nodes = [
            self._node_map[nid] for nid in selected_ids if nid in self._node_map
        ]

        induced_edges = []
        for raw_edge in induced_edges_raw:
            edge_type_str = raw_edge.get("type", "REFERENCES").upper()
            try:
                edge_type = EdgeType[edge_type_str]
            except KeyError:
                edge_type = EdgeType.REFERENCES

            induced_edges.append(
                GraphEdge(
                    source_id=raw_edge.get("src", ""),
                    target_id=raw_edge.get("dst", ""),
                    edge_type=edge_type,
                    weight=raw_edge.get("weight", 1.0),
                )
            )

        return GraphCutResult(
            selected_nodes=selected_nodes,
            induced_edges=induced_edges,
            seed_nodes=seeds,
            radius=radius,
            budget=budget,
            total_candidates=len(raw_nodes),
            execution_time_ms=0.0,  # Will be set by caller
        )

    def _select_with_bfs(
        self, seeds: List[str], radius: int, budget: int
    ) -> GraphCutResult:
        """
        Fallback BFS-based context selection.

        Args:
            seeds: Seed node IDs
            radius: Maximum distance from seeds
            budget: Maximum number of nodes to select

        Returns:
            GraphCutResult
        """
        # Build adjacency lists
        out_adj: Dict[str, Set[str]] = defaultdict(set)
        out_degree: Dict[str, int] = defaultdict(int)

        for edge in self.edges:
            out_adj[edge.source_id].add(edge.target_id)
            out_degree[edge.source_id] += 1

        # BFS from seeds to collect candidates within radius
        distance: Dict[str, int] = {}
        queue: deque = deque()

        for seed in seeds:
            if seed in self._node_map:
                distance[seed] = 0
                queue.append(seed)

        visited: Set[str] = set(distance.keys())

        while queue:
            current = queue.popleft()
            current_dist = distance[current]

            if current_dist >= radius:
                continue

            for neighbor in out_adj.get(current, set()):
                if neighbor not in visited:
                    visited.add(neighbor)
                    distance[neighbor] = current_dist + 1
                    queue.append(neighbor)

        # Score candidates by distance and degree
        def score(node_id: str) -> float:
            dist = distance.get(node_id, 1000000)
            if dist <= 0:
                dist = 1
            degree = out_degree.get(node_id, 0)
            # Simple scoring: closer nodes and higher degree are better
            return (1.0 / float(dist)) + (degree * 0.1)

        candidates = [nid for nid in visited if nid in self._node_map]
        candidates.sort(key=score, reverse=True)

        # Select top budget nodes
        selected_ids = candidates[:budget]
        selected_set = set(selected_ids)

        selected_nodes = [self._node_map[nid] for nid in selected_ids]

        # Induced edges
        induced_edges = [
            edge
            for edge in self.edges
            if edge.source_id in selected_set and edge.target_id in selected_set
        ]

        return GraphCutResult(
            selected_nodes=selected_nodes,
            induced_edges=induced_edges,
            seed_nodes=seeds,
            radius=radius,
            budget=budget,
            total_candidates=len(candidates),
            execution_time_ms=0.0,  # Will be set by caller
        )

    def expand_search_results(
        self,
        search_results: List[Dict[str, Any]],
        expansion_radius: int = 1,
        max_context_nodes: int = 50,
    ) -> List[GraphNode]:
        """
        Expand search results with graph context.

        Args:
            search_results: Search results to expand (must have 'file' key)
            expansion_radius: How far to expand
            max_context_nodes: Maximum context nodes to add

        Returns:
            List of context nodes
        """
        # Extract file paths from search results
        result_files = set()
        for result in search_results:
            file_path = result.get("file") or result.get("file_path")
            if file_path:
                result_files.add(file_path)

        if not result_files:
            logger.warning("No file paths in search results")
            return []

        # Find nodes matching these files
        seed_nodes = []
        for node in self.nodes:
            if node.file_path in result_files:
                seed_nodes.append(node.id)

        if not seed_nodes:
            logger.warning(
                f"No graph nodes found for {len(result_files)} result files"
            )
            return []

        # Use graph cut to select context
        result = self.select_context(
            seeds=seed_nodes,
            radius=expansion_radius,
            budget=max_context_nodes,
        )

        logger.debug(
            f"Expanded {len(search_results)} search results to {len(result.selected_nodes)} context nodes"
        )

        return result.selected_nodes
