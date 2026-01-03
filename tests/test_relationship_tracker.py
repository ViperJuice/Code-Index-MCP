"""
Comprehensive tests for RelationshipTracker.

Tests cover:
- Basic relationship creation and retrieval
- Bidirectional dependency queries
- Multi-level graph traversal
- Path finding between entities
- Edge cases (circular dependencies, missing entities)
- Batch operations
- NetworkX graph validation
"""

import networkx as nx
import pytest

from mcp_server.storage.relationship_tracker import (
    Relationship,
    RelationshipTracker,
    RelationshipType,
)
from mcp_server.storage.sqlite_store import SQLiteStore


class TestRelationshipTrackerBasics:
    """Test basic relationship operations."""

    def test_add_single_relationship(self, sqlite_store):
        """Test adding a single relationship."""
        tracker = RelationshipTracker(sqlite_store)

        # Create test entities
        repo_id = sqlite_store.create_repository("/test", "test-repo")
        file_id = sqlite_store.store_file(repo_id, "/test/file.py", "file.py", "python")

        func1_id = sqlite_store.store_symbol(file_id, "func1", "function", 1, 10)
        func2_id = sqlite_store.store_symbol(file_id, "func2", "function", 12, 20)

        # Add relationship
        rel_id = tracker.add_relationship(
            func1_id, func2_id, RelationshipType.CALLS, confidence_score=1.0
        )

        assert rel_id > 0
        assert tracker.get_relationship_count(RelationshipType.CALLS) == 1

    def test_add_relationship_with_metadata(self, sqlite_store):
        """Test adding relationship with metadata."""
        tracker = RelationshipTracker(sqlite_store)

        repo_id = sqlite_store.create_repository("/test", "test-repo")
        file_id = sqlite_store.store_file(repo_id, "/test/file.py", "file.py", "python")

        func1_id = sqlite_store.store_symbol(file_id, "func1", "function", 1, 10)
        func2_id = sqlite_store.store_symbol(file_id, "func2", "function", 12, 20)

        metadata = {"line": 5, "call_type": "direct"}
        rel_id = tracker.add_relationship(
            func1_id, func2_id, RelationshipType.CALLS, metadata=metadata
        )

        assert rel_id > 0

    def test_invalid_relationship_type(self, sqlite_store):
        """Test that invalid relationship type raises error."""
        tracker = RelationshipTracker(sqlite_store)

        repo_id = sqlite_store.create_repository("/test", "test-repo")
        file_id = sqlite_store.store_file(repo_id, "/test/file.py", "file.py", "python")

        func1_id = sqlite_store.store_symbol(file_id, "func1", "function", 1, 10)
        func2_id = sqlite_store.store_symbol(file_id, "func2", "function", 12, 20)

        with pytest.raises(ValueError, match="Invalid relationship_type"):
            tracker.add_relationship(func1_id, func2_id, "invalid_type")

    def test_invalid_confidence_score(self, sqlite_store):
        """Test that invalid confidence score raises error."""
        tracker = RelationshipTracker(sqlite_store)

        repo_id = sqlite_store.create_repository("/test", "test-repo")
        file_id = sqlite_store.store_file(repo_id, "/test/file.py", "file.py", "python")

        func1_id = sqlite_store.store_symbol(file_id, "func1", "function", 1, 10)
        func2_id = sqlite_store.store_symbol(file_id, "func2", "function", 12, 20)

        with pytest.raises(ValueError, match="confidence_score must be between"):
            tracker.add_relationship(
                func1_id, func2_id, RelationshipType.CALLS, confidence_score=1.5
            )


class TestBatchOperations:
    """Test batch relationship operations."""

    def test_add_relationships_batch(self, sqlite_store):
        """Test adding multiple relationships in batch."""
        tracker = RelationshipTracker(sqlite_store)

        # Create test entities
        repo_id = sqlite_store.create_repository("/test", "test-repo")
        file_id = sqlite_store.store_file(repo_id, "/test/file.py", "file.py", "python")

        func_ids = []
        for i in range(5):
            func_id = sqlite_store.store_symbol(file_id, f"func{i}", "function", i * 10, i * 10 + 5)
            func_ids.append(func_id)

        # Create batch relationships
        relationships = []
        for i in range(len(func_ids) - 1):
            relationships.append(
                {
                    "source_entity_id": func_ids[i],
                    "target_entity_id": func_ids[i + 1],
                    "relationship_type": RelationshipType.CALLS,
                    "confidence_score": 1.0,
                    "metadata": {"chain": i},
                }
            )

        count = tracker.add_relationships_batch(relationships)

        assert count == 4
        assert tracker.get_relationship_count(RelationshipType.CALLS) == 4

    def test_batch_empty_list(self, sqlite_store):
        """Test that batch with empty list returns 0."""
        tracker = RelationshipTracker(sqlite_store)
        count = tracker.add_relationships_batch([])
        assert count == 0


class TestDependencyQueries:
    """Test dependency and dependent queries."""

    def test_get_dependencies_single_level(self, sqlite_store):
        """Test getting dependencies at depth 1."""
        tracker = RelationshipTracker(sqlite_store)

        # Create test entities: func1 -> func2, func1 -> func3
        repo_id = sqlite_store.create_repository("/test", "test-repo")
        file_id = sqlite_store.store_file(repo_id, "/test/file.py", "file.py", "python")

        func1_id = sqlite_store.store_symbol(file_id, "func1", "function", 1, 10)
        func2_id = sqlite_store.store_symbol(file_id, "func2", "function", 12, 20)
        func3_id = sqlite_store.store_symbol(file_id, "func3", "function", 22, 30)

        tracker.add_relationship(func1_id, func2_id, RelationshipType.CALLS)
        tracker.add_relationship(func1_id, func3_id, RelationshipType.CALLS)

        deps = tracker.get_dependencies(func1_id, depth=1)

        assert len(deps) == 2
        target_ids = {dep["target_entity_id"] for dep in deps}
        assert target_ids == {func2_id, func3_id}

    def test_get_dependents_single_level(self, sqlite_store):
        """Test getting dependents at depth 1."""
        tracker = RelationshipTracker(sqlite_store)

        # Create test entities: func1 -> func3, func2 -> func3
        repo_id = sqlite_store.create_repository("/test", "test-repo")
        file_id = sqlite_store.store_file(repo_id, "/test/file.py", "file.py", "python")

        func1_id = sqlite_store.store_symbol(file_id, "func1", "function", 1, 10)
        func2_id = sqlite_store.store_symbol(file_id, "func2", "function", 12, 20)
        func3_id = sqlite_store.store_symbol(file_id, "func3", "function", 22, 30)

        tracker.add_relationship(func1_id, func3_id, RelationshipType.CALLS)
        tracker.add_relationship(func2_id, func3_id, RelationshipType.CALLS)

        dependents = tracker.get_dependents(func3_id, depth=1)

        assert len(dependents) == 2
        source_ids = {dep["source_entity_id"] for dep in dependents}
        assert source_ids == {func1_id, func2_id}

    def test_get_dependencies_multi_level(self, sqlite_store):
        """Test getting dependencies with depth > 1."""
        tracker = RelationshipTracker(sqlite_store)

        # Create chain: func1 -> func2 -> func3 -> func4
        repo_id = sqlite_store.create_repository("/test", "test-repo")
        file_id = sqlite_store.store_file(repo_id, "/test/file.py", "file.py", "python")

        func_ids = []
        for i in range(4):
            func_id = sqlite_store.store_symbol(
                file_id, f"func{i+1}", "function", i * 10, i * 10 + 5
            )
            func_ids.append(func_id)

        # Create chain
        for i in range(len(func_ids) - 1):
            tracker.add_relationship(func_ids[i], func_ids[i + 1], RelationshipType.CALLS)

        # Get dependencies with depth 3
        deps = tracker.get_dependencies(func_ids[0], depth=3)

        # Should get func2, func3, func4
        assert len(deps) == 3
        target_ids = {dep["target_entity_id"] for dep in deps}
        assert target_ids == {func_ids[1], func_ids[2], func_ids[3]}

    def test_get_dependencies_with_type_filter(self, sqlite_store):
        """Test filtering dependencies by relationship type."""
        tracker = RelationshipTracker(sqlite_store)

        repo_id = sqlite_store.create_repository("/test", "test-repo")
        file_id = sqlite_store.store_file(repo_id, "/test/file.py", "file.py", "python")

        class1_id = sqlite_store.store_symbol(file_id, "Class1", "class", 1, 10)
        class2_id = sqlite_store.store_symbol(file_id, "Class2", "class", 12, 20)
        func1_id = sqlite_store.store_symbol(file_id, "func1", "function", 22, 30)

        # Add different relationship types
        tracker.add_relationship(class1_id, class2_id, RelationshipType.INHERITS)
        tracker.add_relationship(class1_id, func1_id, RelationshipType.USES)

        # Filter by INHERITS only
        deps = tracker.get_dependencies(class1_id, relationship_types=[RelationshipType.INHERITS])

        assert len(deps) == 1
        assert deps[0]["target_entity_id"] == class2_id
        assert deps[0]["relationship_type"] == RelationshipType.INHERITS


class TestPathFinding:
    """Test path finding between entities."""

    def test_find_direct_path(self, sqlite_store):
        """Test finding direct path between two entities."""
        tracker = RelationshipTracker(sqlite_store)

        repo_id = sqlite_store.create_repository("/test", "test-repo")
        file_id = sqlite_store.store_file(repo_id, "/test/file.py", "file.py", "python")

        func1_id = sqlite_store.store_symbol(file_id, "func1", "function", 1, 10)
        func2_id = sqlite_store.store_symbol(file_id, "func2", "function", 12, 20)

        tracker.add_relationship(func1_id, func2_id, RelationshipType.CALLS)

        paths = tracker.find_paths(func1_id, func2_id, max_depth=5)

        assert len(paths) == 1
        assert len(paths[0]) == 1
        assert paths[0][0]["source_entity_id"] == func1_id
        assert paths[0][0]["target_entity_id"] == func2_id

    def test_find_multi_hop_path(self, sqlite_store):
        """Test finding path with multiple hops."""
        tracker = RelationshipTracker(sqlite_store)

        # Create chain: func1 -> func2 -> func3
        repo_id = sqlite_store.create_repository("/test", "test-repo")
        file_id = sqlite_store.store_file(repo_id, "/test/file.py", "file.py", "python")

        func1_id = sqlite_store.store_symbol(file_id, "func1", "function", 1, 10)
        func2_id = sqlite_store.store_symbol(file_id, "func2", "function", 12, 20)
        func3_id = sqlite_store.store_symbol(file_id, "func3", "function", 22, 30)

        tracker.add_relationship(func1_id, func2_id, RelationshipType.CALLS)
        tracker.add_relationship(func2_id, func3_id, RelationshipType.CALLS)

        paths = tracker.find_paths(func1_id, func3_id, max_depth=5)

        assert len(paths) == 1
        assert len(paths[0]) == 2

    def test_find_no_path(self, sqlite_store):
        """Test finding path when no path exists."""
        tracker = RelationshipTracker(sqlite_store)

        repo_id = sqlite_store.create_repository("/test", "test-repo")
        file_id = sqlite_store.store_file(repo_id, "/test/file.py", "file.py", "python")

        func1_id = sqlite_store.store_symbol(file_id, "func1", "function", 1, 10)
        func2_id = sqlite_store.store_symbol(file_id, "func2", "function", 12, 20)

        # No relationship between them
        paths = tracker.find_paths(func1_id, func2_id, max_depth=5)

        assert len(paths) == 0

    def test_find_multiple_paths(self, sqlite_store):
        """Test finding multiple paths between entities."""
        tracker = RelationshipTracker(sqlite_store)

        # Create diamond: func1 -> func2 -> func4
        #                 func1 -> func3 -> func4
        repo_id = sqlite_store.create_repository("/test", "test-repo")
        file_id = sqlite_store.store_file(repo_id, "/test/file.py", "file.py", "python")

        func1_id = sqlite_store.store_symbol(file_id, "func1", "function", 1, 10)
        func2_id = sqlite_store.store_symbol(file_id, "func2", "function", 12, 20)
        func3_id = sqlite_store.store_symbol(file_id, "func3", "function", 22, 30)
        func4_id = sqlite_store.store_symbol(file_id, "func4", "function", 32, 40)

        tracker.add_relationship(func1_id, func2_id, RelationshipType.CALLS)
        tracker.add_relationship(func1_id, func3_id, RelationshipType.CALLS)
        tracker.add_relationship(func2_id, func4_id, RelationshipType.CALLS)
        tracker.add_relationship(func3_id, func4_id, RelationshipType.CALLS)

        paths = tracker.find_paths(func1_id, func4_id, max_depth=5)

        assert len(paths) == 2


class TestGraphOperations:
    """Test graph structure operations."""

    def test_get_relationship_graph(self, sqlite_store):
        """Test getting relationship graph structure."""
        tracker = RelationshipTracker(sqlite_store)

        # Create small graph
        repo_id = sqlite_store.create_repository("/test", "test-repo")
        file_id = sqlite_store.store_file(repo_id, "/test/file.py", "file.py", "python")

        func1_id = sqlite_store.store_symbol(file_id, "func1", "function", 1, 10)
        func2_id = sqlite_store.store_symbol(file_id, "func2", "function", 12, 20)
        func3_id = sqlite_store.store_symbol(file_id, "func3", "function", 22, 30)

        tracker.add_relationship(func1_id, func2_id, RelationshipType.CALLS)
        tracker.add_relationship(func2_id, func3_id, RelationshipType.CALLS)
        tracker.add_relationship(func3_id, func1_id, RelationshipType.CALLS)  # cycle

        graph = tracker.get_relationship_graph(func1_id, depth=2)

        assert "nodes" in graph
        assert "edges" in graph
        assert len(graph["nodes"]) > 0
        assert len(graph["edges"]) > 0


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_circular_dependencies(self, sqlite_store):
        """Test handling circular dependencies."""
        tracker = RelationshipTracker(sqlite_store)

        # Create circular dependency: func1 -> func2 -> func3 -> func1
        repo_id = sqlite_store.create_repository("/test", "test-repo")
        file_id = sqlite_store.store_file(repo_id, "/test/file.py", "file.py", "python")

        func1_id = sqlite_store.store_symbol(file_id, "func1", "function", 1, 10)
        func2_id = sqlite_store.store_symbol(file_id, "func2", "function", 12, 20)
        func3_id = sqlite_store.store_symbol(file_id, "func3", "function", 22, 30)

        tracker.add_relationship(func1_id, func2_id, RelationshipType.CALLS)
        tracker.add_relationship(func2_id, func3_id, RelationshipType.CALLS)
        tracker.add_relationship(func3_id, func1_id, RelationshipType.CALLS)

        # Should not hang or crash
        deps = tracker.get_dependencies(func1_id, depth=5)
        assert len(deps) > 0

    def test_depth_zero(self, sqlite_store):
        """Test that depth=0 returns empty list."""
        tracker = RelationshipTracker(sqlite_store)

        repo_id = sqlite_store.create_repository("/test", "test-repo")
        file_id = sqlite_store.store_file(repo_id, "/test/file.py", "file.py", "python")
        func1_id = sqlite_store.store_symbol(file_id, "func1", "function", 1, 10)

        deps = tracker.get_dependencies(func1_id, depth=0)
        assert len(deps) == 0

    def test_clear_relationships(self, sqlite_store):
        """Test clearing relationships."""
        tracker = RelationshipTracker(sqlite_store)

        repo_id = sqlite_store.create_repository("/test", "test-repo")
        file_id = sqlite_store.store_file(repo_id, "/test/file.py", "file.py", "python")

        func1_id = sqlite_store.store_symbol(file_id, "func1", "function", 1, 10)
        func2_id = sqlite_store.store_symbol(file_id, "func2", "function", 12, 20)

        tracker.add_relationship(func1_id, func2_id, RelationshipType.CALLS)
        assert tracker.get_relationship_count() == 1

        tracker.clear_relationships()
        assert tracker.get_relationship_count() == 0


class TestNetworkXIntegration:
    """Test integration with NetworkX for graph validation."""

    def test_graph_structure_matches_networkx(self, sqlite_store):
        """Test that our graph structure matches NetworkX representation."""
        tracker = RelationshipTracker(sqlite_store)

        # Create test graph
        repo_id = sqlite_store.create_repository("/test", "test-repo")
        file_id = sqlite_store.store_file(repo_id, "/test/file.py", "file.py", "python")

        func_ids = []
        for i in range(5):
            func_id = sqlite_store.store_symbol(file_id, f"func{i}", "function", i * 10, i * 10 + 5)
            func_ids.append(func_id)

        # Create relationships
        tracker.add_relationship(func_ids[0], func_ids[1], RelationshipType.CALLS)
        tracker.add_relationship(func_ids[0], func_ids[2], RelationshipType.CALLS)
        tracker.add_relationship(func_ids[1], func_ids[3], RelationshipType.CALLS)
        tracker.add_relationship(func_ids[2], func_ids[3], RelationshipType.CALLS)
        tracker.add_relationship(func_ids[3], func_ids[4], RelationshipType.CALLS)

        # Build NetworkX graph from our data
        G = nx.DiGraph()
        for func_id in func_ids:
            G.add_node(func_id)

        deps = tracker.get_dependencies(func_ids[0], depth=5)
        for dep in deps:
            G.add_edge(dep["source_entity_id"], dep["target_entity_id"])

        # Verify graph properties
        assert G.number_of_nodes() == len(func_ids)
        assert nx.is_directed_acyclic_graph(G)

        # Test path finding matches NetworkX
        our_paths = tracker.find_paths(func_ids[0], func_ids[4], max_depth=5)
        nx_paths = list(nx.all_simple_paths(G, func_ids[0], func_ids[4]))

        assert len(our_paths) == len(nx_paths)

    def test_shortest_path_matches_networkx(self, sqlite_store):
        """Test that shortest path matches NetworkX."""
        tracker = RelationshipTracker(sqlite_store)

        # Create test graph with multiple paths
        repo_id = sqlite_store.create_repository("/test", "test-repo")
        file_id = sqlite_store.store_file(repo_id, "/test/file.py", "file.py", "python")

        func_ids = []
        for i in range(6):
            func_id = sqlite_store.store_symbol(file_id, f"func{i}", "function", i * 10, i * 10 + 5)
            func_ids.append(func_id)

        # Create graph with long and short paths
        # Short: 0 -> 1 -> 5
        # Long:  0 -> 2 -> 3 -> 4 -> 5
        tracker.add_relationship(func_ids[0], func_ids[1], RelationshipType.CALLS)
        tracker.add_relationship(func_ids[1], func_ids[5], RelationshipType.CALLS)
        tracker.add_relationship(func_ids[0], func_ids[2], RelationshipType.CALLS)
        tracker.add_relationship(func_ids[2], func_ids[3], RelationshipType.CALLS)
        tracker.add_relationship(func_ids[3], func_ids[4], RelationshipType.CALLS)
        tracker.add_relationship(func_ids[4], func_ids[5], RelationshipType.CALLS)

        # Build NetworkX graph
        G = nx.DiGraph()
        for i in range(len(func_ids) - 1):
            deps = tracker.get_dependencies(func_ids[i], depth=1)
            for dep in deps:
                G.add_edge(dep["source_entity_id"], dep["target_entity_id"])

        # Find shortest path with NetworkX
        nx_shortest = nx.shortest_path(G, func_ids[0], func_ids[5])
        nx_shortest_len = len(nx_shortest) - 1  # Number of edges

        # Find paths with our tracker
        our_paths = tracker.find_paths(func_ids[0], func_ids[5], max_depth=10)
        our_shortest_len = min(len(path) for path in our_paths)

        assert our_shortest_len == nx_shortest_len

    def test_cycle_detection_with_networkx(self, sqlite_store):
        """Test cycle detection matches NetworkX."""
        tracker = RelationshipTracker(sqlite_store)

        repo_id = sqlite_store.create_repository("/test", "test-repo")
        file_id = sqlite_store.store_file(repo_id, "/test/file.py", "file.py", "python")

        func_ids = []
        for i in range(3):
            func_id = sqlite_store.store_symbol(file_id, f"func{i}", "function", i * 10, i * 10 + 5)
            func_ids.append(func_id)

        # Create cycle: 0 -> 1 -> 2 -> 0
        tracker.add_relationship(func_ids[0], func_ids[1], RelationshipType.CALLS)
        tracker.add_relationship(func_ids[1], func_ids[2], RelationshipType.CALLS)
        tracker.add_relationship(func_ids[2], func_ids[0], RelationshipType.CALLS)

        # Build NetworkX graph
        G = nx.DiGraph()
        for func_id in func_ids:
            deps = tracker.get_dependencies(func_id, depth=1)
            for dep in deps:
                G.add_edge(dep["source_entity_id"], dep["target_entity_id"])

        # Check for cycles
        has_cycle = not nx.is_directed_acyclic_graph(G)
        assert has_cycle

        # Our tracker should handle cycles gracefully
        deps = tracker.get_dependencies(func_ids[0], depth=10)
        assert len(deps) > 0  # Should not hang


class TestPerformance:
    """Test performance characteristics."""

    def test_batch_performance(self, sqlite_store, benchmark_results):
        """Test batch operation performance."""
        import time

        tracker = RelationshipTracker(sqlite_store)

        repo_id = sqlite_store.create_repository("/test", "test-repo")
        file_id = sqlite_store.store_file(repo_id, "/test/file.py", "file.py", "python")

        # Create 100 entities
        func_ids = []
        for i in range(100):
            func_id = sqlite_store.store_symbol(file_id, f"func{i}", "function", i * 10, i * 10 + 5)
            func_ids.append(func_id)

        # Create relationships
        relationships = []
        for i in range(len(func_ids) - 1):
            relationships.append(
                {
                    "source_entity_id": func_ids[i],
                    "target_entity_id": func_ids[i + 1],
                    "relationship_type": RelationshipType.CALLS,
                }
            )

        start = time.time()
        tracker.add_relationships_batch(relationships)
        elapsed = time.time() - start

        benchmark_results["batch_insert_100_relationships"] = [elapsed]

        # Should be fast (< 1 second for 100 relationships)
        assert elapsed < 1.0

    def test_query_performance(self, sqlite_store, benchmark_results):
        """Test query performance."""
        import time

        tracker = RelationshipTracker(sqlite_store)

        repo_id = sqlite_store.create_repository("/test", "test-repo")
        file_id = sqlite_store.store_file(repo_id, "/test/file.py", "file.py", "python")

        # Create 50 entities in a chain
        func_ids = []
        for i in range(50):
            func_id = sqlite_store.store_symbol(file_id, f"func{i}", "function", i * 10, i * 10 + 5)
            func_ids.append(func_id)

        # Create chain
        for i in range(len(func_ids) - 1):
            tracker.add_relationship(func_ids[i], func_ids[i + 1], RelationshipType.CALLS)

        start = time.time()
        deps = tracker.get_dependencies(func_ids[0], depth=10)
        elapsed = time.time() - start

        benchmark_results["query_depth_10_chain_50"] = [elapsed]

        # Should be fast (< 100ms target)
        assert elapsed < 0.1
        assert len(deps) > 0
