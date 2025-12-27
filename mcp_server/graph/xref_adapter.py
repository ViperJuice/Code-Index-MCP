"""Adapter for TreeSitter Chunker's cross-reference graph builder."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .interfaces import EdgeType, GraphEdge, GraphNode, IGraphBuilder

logger = logging.getLogger(__name__)

# Check if TreeSitter Chunker is available
CHUNKER_AVAILABLE = False
try:
    from chunker.graph.xref import build_xref
    from chunker.chunker import chunk_file

    CHUNKER_AVAILABLE = True
    logger.info("TreeSitter Chunker graph module available")
except ImportError:
    logger.warning(
        "TreeSitter Chunker not available. Install with: pip install treesitter-chunker"
    )


class XRefAdapter(IGraphBuilder):
    """Adapter for TreeSitter Chunker's build_xref function."""

    def __init__(self):
        """Initialize the XRef adapter."""
        if not CHUNKER_AVAILABLE:
            logger.warning(
                "XRefAdapter initialized but TreeSitter Chunker is not available"
            )

    def build_graph(
        self, file_paths: List[str]
    ) -> Tuple[List[GraphNode], List[GraphEdge]]:
        """
        Build a code graph from the given files using TreeSitter Chunker.

        Args:
            file_paths: List of file paths to analyze

        Returns:
            Tuple of (nodes, edges)
        """
        if not CHUNKER_AVAILABLE:
            logger.error("Cannot build graph: TreeSitter Chunker not available")
            return [], []

        try:
            # Collect chunks from all files
            all_chunks = []
            for file_path in file_paths:
                try:
                    path = Path(file_path)
                    if not path.exists():
                        logger.warning(f"File not found: {file_path}")
                        continue

                    # Read file content
                    content = path.read_text(encoding="utf-8")

                    # Chunk the file
                    chunks = chunk_file(str(path), content)
                    all_chunks.extend(chunks)

                    logger.debug(f"Chunked {file_path}: {len(chunks)} chunks")
                except Exception as e:
                    logger.error(f"Error chunking file {file_path}: {e}")
                    continue

            if not all_chunks:
                logger.warning("No chunks generated from files")
                return [], []

            # Build cross-reference graph
            raw_nodes, raw_edges = build_xref(all_chunks)

            # Convert to our format
            nodes = self._convert_nodes(raw_nodes)
            edges = self._convert_edges(raw_edges)

            logger.info(
                f"Built graph: {len(nodes)} nodes, {len(edges)} edges from {len(file_paths)} files"
            )

            return nodes, edges

        except Exception as e:
            logger.error(f"Error building graph: {e}", exc_info=True)
            return [], []

    def _convert_nodes(self, raw_nodes: List[Dict[str, Any]]) -> List[GraphNode]:
        """
        Convert chunker nodes to GraphNode format.

        Args:
            raw_nodes: Nodes from build_xref

        Returns:
            List of GraphNode objects
        """
        nodes = []
        for raw in raw_nodes:
            node = GraphNode(
                id=raw.get("id", ""),
                file_path=raw.get("file", ""),
                language=raw.get("lang", "unknown"),
                symbol=raw.get("symbol"),
                kind=raw.get("kind"),
                attrs=raw.get("attrs", {}),
                score=0.0,
            )
            nodes.append(node)

        return nodes

    def _convert_edges(self, raw_edges: List[Dict[str, Any]]) -> List[GraphEdge]:
        """
        Convert chunker edges to GraphEdge format.

        Args:
            raw_edges: Edges from build_xref

        Returns:
            List of GraphEdge objects
        """
        edges = []
        for raw in raw_edges:
            # Map edge type string to EdgeType enum
            edge_type_str = raw.get("type", "REFERENCES").upper()
            try:
                edge_type = EdgeType[edge_type_str]
            except KeyError:
                logger.warning(
                    f"Unknown edge type: {edge_type_str}, defaulting to REFERENCES"
                )
                edge_type = EdgeType.REFERENCES

            edge = GraphEdge(
                source_id=raw.get("src", ""),
                target_id=raw.get("dst", ""),
                edge_type=edge_type,
                weight=raw.get("weight", 1.0),
                metadata={},
            )
            edges.append(edge)

        return edges
