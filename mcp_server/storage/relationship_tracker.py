"""
Relationship Tracker for Code Dependencies

This module provides lightweight graph relationship tracking to help coding agents
understand dependencies between functions, classes, and modules. Inspired by nglite's
graph patterns but optimized for SQLite storage.

Key Features:
- Track relationships: calls, inherits, imports, uses
- Query dependencies and dependents with depth
- Find paths between entities (BFS traversal)
- Batch operations for performance
- Confidence scores for relationship quality
"""

import json
import logging
from collections import deque
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from .sqlite_store import SQLiteStore

logger = logging.getLogger(__name__)


class RelationshipType:
    """Relationship types between code entities."""

    CALLS = "calls"  # Function calls another function
    INHERITS = "inherits"  # Class inherits from another class
    IMPORTS = "imports"  # Module imports another module
    USES = "uses"  # Generic usage relationship
    CONTAINS = "contains"  # File contains function/class

    ALL_TYPES = [CALLS, INHERITS, IMPORTS, USES, CONTAINS]


class Relationship:
    """Represents a relationship between two code entities."""

    def __init__(
        self,
        id: Optional[int],
        source_entity_id: int,
        target_entity_id: int,
        relationship_type: str,
        confidence_score: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
        created_at: Optional[str] = None,
    ):
        self.id = id
        self.source_entity_id = source_entity_id
        self.target_entity_id = target_entity_id
        self.relationship_type = relationship_type
        self.confidence_score = confidence_score
        self.metadata = metadata or {}
        self.created_at = created_at

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "source_entity_id": self.source_entity_id,
            "target_entity_id": self.target_entity_id,
            "relationship_type": self.relationship_type,
            "confidence_score": self.confidence_score,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }


class RelationshipTracker:
    """
    Tracks relationships between code entities in SQLite.

    This class provides methods to:
    - Add relationships between entities
    - Query dependencies (what an entity depends on)
    - Query dependents (what depends on an entity)
    - Find paths between entities
    - Traverse relationship graphs with depth limits
    """

    def __init__(self, sqlite_store: SQLiteStore):
        """
        Initialize the relationship tracker.

        Args:
            sqlite_store: SQLiteStore instance for persistence
        """
        self.store = sqlite_store
        self._ensure_schema()

    def _ensure_schema(self):
        """Ensure the relationships table exists."""
        # The schema is created by SQLiteStore, but we verify it here
        with self.store._get_connection() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='relationships'"
            )
            if not cursor.fetchone():
                logger.warning("Relationships table not found - creating it now")
                self._create_schema(conn)

    def _create_schema(self, conn):
        """Create the relationships schema if it doesn't exist."""
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS relationships (
                id INTEGER PRIMARY KEY,
                source_entity_id INTEGER NOT NULL,
                target_entity_id INTEGER NOT NULL,
                relationship_type TEXT NOT NULL,
                confidence_score REAL DEFAULT 1.0,
                metadata JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_entity_id) REFERENCES symbols(id) ON DELETE CASCADE,
                FOREIGN KEY (target_entity_id) REFERENCES symbols(id) ON DELETE CASCADE
            );
            
            CREATE INDEX IF NOT EXISTS idx_rel_source ON relationships(source_entity_id);
            CREATE INDEX IF NOT EXISTS idx_rel_target ON relationships(target_entity_id);
            CREATE INDEX IF NOT EXISTS idx_rel_type ON relationships(relationship_type);
            CREATE INDEX IF NOT EXISTS idx_rel_source_type ON relationships(source_entity_id, relationship_type);
            CREATE INDEX IF NOT EXISTS idx_rel_target_type ON relationships(target_entity_id, relationship_type);
        """
        )
        logger.info("Created relationships table and indexes")

    def add_relationship(
        self,
        source_entity_id: int,
        target_entity_id: int,
        relationship_type: str,
        confidence_score: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Add a single relationship between two entities.

        Args:
            source_entity_id: ID of the source entity (e.g., caller)
            target_entity_id: ID of the target entity (e.g., callee)
            relationship_type: Type of relationship (calls, inherits, imports, uses)
            confidence_score: Confidence in the relationship (0.0-1.0)
            metadata: Optional metadata about the relationship

        Returns:
            ID of the created relationship

        Raises:
            ValueError: If relationship_type is invalid or confidence_score out of range
        """
        if relationship_type not in RelationshipType.ALL_TYPES:
            raise ValueError(
                f"Invalid relationship_type: {relationship_type}. "
                f"Must be one of {RelationshipType.ALL_TYPES}"
            )

        if not 0.0 <= confidence_score <= 1.0:
            raise ValueError(f"confidence_score must be between 0.0 and 1.0, got {confidence_score}")

        with self.store._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO relationships 
                (source_entity_id, target_entity_id, relationship_type, confidence_score, metadata)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    source_entity_id,
                    target_entity_id,
                    relationship_type,
                    confidence_score,
                    json.dumps(metadata or {}),
                ),
            )
            relationship_id = cursor.lastrowid
            logger.debug(
                f"Added relationship {relationship_id}: {source_entity_id} "
                f"-[{relationship_type}]-> {target_entity_id}"
            )
            return relationship_id

    def add_relationships_batch(self, relationships: List[Dict[str, Any]]) -> int:
        """
        Add multiple relationships in a batch for performance.

        Args:
            relationships: List of relationship dicts with keys:
                - source_entity_id (int)
                - target_entity_id (int)
                - relationship_type (str)
                - confidence_score (float, optional, default 1.0)
                - metadata (dict, optional)

        Returns:
            Number of relationships added

        Raises:
            ValueError: If any relationship is invalid
        """
        if not relationships:
            return 0

        # Validate all relationships first
        for rel in relationships:
            rel_type = rel.get("relationship_type")
            if rel_type not in RelationshipType.ALL_TYPES:
                raise ValueError(f"Invalid relationship_type: {rel_type}")

            confidence = rel.get("confidence_score", 1.0)
            if not 0.0 <= confidence <= 1.0:
                raise ValueError(f"confidence_score must be between 0.0 and 1.0, got {confidence}")

        with self.store._get_connection() as conn:
            cursor = conn.executemany(
                """
                INSERT INTO relationships 
                (source_entity_id, target_entity_id, relationship_type, confidence_score, metadata)
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (
                        rel["source_entity_id"],
                        rel["target_entity_id"],
                        rel["relationship_type"],
                        rel.get("confidence_score", 1.0),
                        json.dumps(rel.get("metadata", {})),
                    )
                    for rel in relationships
                ],
            )
            count = cursor.rowcount
            logger.info(f"Added {count} relationships in batch")
            return count

    def get_dependencies(
        self,
        entity_id: int,
        depth: int = 1,
        relationship_types: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get what an entity depends on (outgoing relationships).

        Args:
            entity_id: ID of the entity to query
            depth: How many levels deep to traverse (default 1)
            relationship_types: Optional list of relationship types to filter by

        Returns:
            List of dependency dictionaries with entity info and relationship details

        Example:
            # Get what a function calls
            deps = tracker.get_dependencies(func_id, depth=1, relationship_types=['calls'])
        """
        if depth < 1:
            return []

        rel_types = relationship_types or RelationshipType.ALL_TYPES
        visited: Set[int] = set()
        results: List[Dict[str, Any]] = []

        self._traverse_dependencies(entity_id, depth, rel_types, visited, results, is_forward=True)

        return results

    def get_dependents(
        self,
        entity_id: int,
        depth: int = 1,
        relationship_types: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get what depends on an entity (incoming relationships).

        Args:
            entity_id: ID of the entity to query
            depth: How many levels deep to traverse (default 1)
            relationship_types: Optional list of relationship types to filter by

        Returns:
            List of dependent dictionaries with entity info and relationship details

        Example:
            # Get what functions call this function
            dependents = tracker.get_dependents(func_id, depth=1, relationship_types=['calls'])
        """
        if depth < 1:
            return []

        rel_types = relationship_types or RelationshipType.ALL_TYPES
        visited: Set[int] = set()
        results: List[Dict[str, Any]] = []

        self._traverse_dependencies(entity_id, depth, rel_types, visited, results, is_forward=False)

        return results

    def _traverse_dependencies(
        self,
        entity_id: int,
        depth: int,
        rel_types: List[str],
        visited: Set[int],
        results: List[Dict[str, Any]],
        is_forward: bool,
    ):
        """
        Recursively traverse dependencies or dependents.

        Args:
            entity_id: Current entity ID
            depth: Remaining depth to traverse
            rel_types: Relationship types to consider
            visited: Set of already visited entity IDs
            results: List to accumulate results
            is_forward: True for dependencies (outgoing), False for dependents (incoming)
        """
        if depth == 0 or entity_id in visited:
            return

        visited.add(entity_id)

        # Build query based on direction
        placeholders = ",".join(["?"] * len(rel_types))

        if is_forward:
            # Dependencies: source -> target
            query = f"""
                SELECT r.*, s.name as target_name, s.kind as target_kind,
                       s.line_start, s.line_end, f.path as target_file
                FROM relationships r
                JOIN symbols s ON r.target_entity_id = s.id
                JOIN files f ON s.file_id = f.id
                WHERE r.source_entity_id = ? AND r.relationship_type IN ({placeholders})
            """
            params = [entity_id] + rel_types
        else:
            # Dependents: target <- source
            query = f"""
                SELECT r.*, s.name as source_name, s.kind as source_kind,
                       s.line_start, s.line_end, f.path as source_file
                FROM relationships r
                JOIN symbols s ON r.source_entity_id = s.id
                JOIN files f ON s.file_id = f.id
                WHERE r.target_entity_id = ? AND r.relationship_type IN ({placeholders})
            """
            params = [entity_id] + rel_types

        with self.store._get_connection() as conn:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()

            for row in rows:
                row_dict = dict(row)
                # Parse metadata
                if row_dict.get("metadata"):
                    try:
                        row_dict["metadata"] = json.loads(row_dict["metadata"])
                    except json.JSONDecodeError:
                        row_dict["metadata"] = {}

                results.append(row_dict)

                # Recurse if depth allows
                if depth > 1:
                    next_id = row["target_entity_id"] if is_forward else row["source_entity_id"]
                    self._traverse_dependencies(
                        next_id, depth - 1, rel_types, visited, results, is_forward
                    )

    def get_relationship_graph(
        self, entity_id: int, depth: int = 2
    ) -> Dict[str, Any]:
        """
        Get a graph of relationships around an entity.

        Args:
            entity_id: ID of the central entity
            depth: How many levels to include in the graph

        Returns:
            Dictionary with 'nodes' and 'edges' lists representing the graph

        Example:
            graph = tracker.get_relationship_graph(func_id, depth=2)
            # Returns: {'nodes': [...], 'edges': [...]}
        """
        nodes: Dict[int, Dict[str, Any]] = {}
        edges: List[Dict[str, Any]] = []

        # Get dependencies and dependents
        deps = self.get_dependencies(entity_id, depth)
        dependents = self.get_dependents(entity_id, depth)

        # Collect unique nodes and edges
        for dep in deps:
            source_id = dep["source_entity_id"]
            target_id = dep["target_entity_id"]

            if source_id not in nodes:
                nodes[source_id] = {"id": source_id, "type": "entity"}

            if target_id not in nodes:
                nodes[target_id] = {
                    "id": target_id,
                    "name": dep.get("target_name"),
                    "kind": dep.get("target_kind"),
                    "file": dep.get("target_file"),
                }

            edges.append(
                {
                    "source": source_id,
                    "target": target_id,
                    "type": dep["relationship_type"],
                    "confidence": dep["confidence_score"],
                }
            )

        for dependent in dependents:
            source_id = dependent["source_entity_id"]
            target_id = dependent["target_entity_id"]

            if source_id not in nodes:
                nodes[source_id] = {
                    "id": source_id,
                    "name": dependent.get("source_name"),
                    "kind": dependent.get("source_kind"),
                    "file": dependent.get("source_file"),
                }

            if target_id not in nodes:
                nodes[target_id] = {"id": target_id, "type": "entity"}

            edges.append(
                {
                    "source": source_id,
                    "target": target_id,
                    "type": dependent["relationship_type"],
                    "confidence": dependent["confidence_score"],
                }
            )

        return {"nodes": list(nodes.values()), "edges": edges}

    def find_paths(
        self,
        source_id: int,
        target_id: int,
        max_depth: int = 5,
        relationship_types: Optional[List[str]] = None,
    ) -> List[List[Dict[str, Any]]]:
        """
        Find paths from source entity to target entity using BFS.

        Args:
            source_id: Starting entity ID
            target_id: Target entity ID
            max_depth: Maximum path length to search
            relationship_types: Optional list of relationship types to traverse

        Returns:
            List of paths, where each path is a list of relationships

        Example:
            paths = tracker.find_paths(func1_id, func2_id, max_depth=5)
            for path in paths:
                print(" -> ".join([rel['relationship_type'] for rel in path]))
        """
        rel_types = relationship_types or RelationshipType.ALL_TYPES
        paths: List[List[Dict[str, Any]]] = []

        # BFS to find all paths
        queue: deque = deque([(source_id, [])])
        visited_paths: Set[Tuple[int, ...]] = set()

        while queue:
            current_id, path = queue.popleft()

            # Check if we've reached the target
            if current_id == target_id and path:
                paths.append(path)
                continue

            # Check depth limit
            if len(path) >= max_depth:
                continue

            # Get outgoing relationships
            placeholders = ",".join(["?"] * len(rel_types))
            query = f"""
                SELECT r.*, s.name as target_name, s.kind as target_kind
                FROM relationships r
                JOIN symbols s ON r.target_entity_id = s.id
                WHERE r.source_entity_id = ? AND r.relationship_type IN ({placeholders})
            """

            with self.store._get_connection() as conn:
                cursor = conn.execute(query, [current_id] + rel_types)
                rows = cursor.fetchall()

                for row in rows:
                    next_id = row["target_entity_id"]

                    # Avoid cycles in this path
                    path_ids = tuple([r["source_entity_id"] for r in path] + [current_id, next_id])
                    if path_ids in visited_paths:
                        continue

                    visited_paths.add(path_ids)

                    # Create relationship dict
                    rel = {
                        "id": row["id"],
                        "source_entity_id": row["source_entity_id"],
                        "target_entity_id": row["target_entity_id"],
                        "relationship_type": row["relationship_type"],
                        "confidence_score": row["confidence_score"],
                        "target_name": row["target_name"],
                        "target_kind": row["target_kind"],
                    }

                    # Add to queue
                    queue.append((next_id, path + [rel]))

        logger.info(f"Found {len(paths)} paths from {source_id} to {target_id}")
        return paths

    def get_relationship_count(self, relationship_type: Optional[str] = None) -> int:
        """
        Get count of relationships.

        Args:
            relationship_type: Optional type to filter by

        Returns:
            Count of relationships
        """
        with self.store._get_connection() as conn:
            if relationship_type:
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM relationships WHERE relationship_type = ?",
                    (relationship_type,),
                )
            else:
                cursor = conn.execute("SELECT COUNT(*) FROM relationships")

            return cursor.fetchone()[0]

    def clear_relationships(self, entity_id: Optional[int] = None):
        """
        Clear relationships for an entity or all relationships.

        Args:
            entity_id: Optional entity ID to clear relationships for.
                       If None, clears all relationships.
        """
        with self.store._get_connection() as conn:
            if entity_id:
                conn.execute(
                    "DELETE FROM relationships WHERE source_entity_id = ? OR target_entity_id = ?",
                    (entity_id, entity_id),
                )
                logger.info(f"Cleared relationships for entity {entity_id}")
            else:
                conn.execute("DELETE FROM relationships")
                logger.info("Cleared all relationships")
