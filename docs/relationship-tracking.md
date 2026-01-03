# Relationship Tracking System

## Overview

The Relationship Tracking system provides lightweight graph-based dependency tracking for code entities. It enables coding agents to understand relationships between functions, classes, and modules without requiring heavy graph database infrastructure.

## Features

- **Track Relationships**: calls, inherits, imports, uses
- **Query Dependencies**: What an entity depends on
- **Query Dependents**: What depends on an entity
- **Path Finding**: Find connection paths between entities
- **Multi-level Traversal**: Configurable depth for graph exploration
- **Confidence Scores**: Track relationship quality (0.0-1.0)
- **Batch Operations**: High-performance bulk inserts
- **NetworkX Compatible**: Validated with industry-standard graph library

## Architecture

Inspired by [nglite](https://github.com/netbrah/nglite)'s graph patterns, our implementation uses:
- SQLite for storage (no external dependencies)
- BFS for path finding
- Deterministic relationship tracking
- Confidence scores for relationship quality

## API Endpoints

### 1. Get Dependencies

Get what an entity depends on (outgoing relationships).

```http
GET /api/v1/dependencies?entity_id=123&depth=2&relationship_types=calls
```

**Parameters:**
- `entity_id` (int, required): ID of the entity to query
- `depth` (int, optional): How many levels deep to traverse (1-10, default: 1)
- `relationship_types` (string, optional): Comma-separated types to filter (e.g., "calls,inherits")

**Response:**
```json
{
  "entity_id": 123,
  "dependencies": [
    {
      "id": 456,
      "source_entity_id": 123,
      "target_entity_id": 456,
      "relationship_type": "calls",
      "confidence_score": 1.0,
      "target_name": "helper_function",
      "target_kind": "function",
      "target_file": "/path/to/file.py",
      "line_start": 10,
      "line_end": 20
    }
  ],
  "depth": 2,
  "count": 1
}
```

**Example Use Cases:**
- Find all functions called by a function
- Find all classes inherited by a class
- Discover transitive dependencies

### 2. Get Dependents

Get what depends on an entity (incoming relationships).

```http
GET /api/v1/dependents?entity_id=456&depth=1&relationship_types=calls
```

**Parameters:**
- `entity_id` (int, required): ID of the entity to query
- `depth` (int, optional): How many levels deep to traverse (1-10, default: 1)
- `relationship_types` (string, optional): Comma-separated types to filter

**Response:**
```json
{
  "entity_id": 456,
  "dependents": [
    {
      "id": 789,
      "source_entity_id": 123,
      "target_entity_id": 456,
      "relationship_type": "calls",
      "confidence_score": 1.0,
      "source_name": "caller_function",
      "source_kind": "function",
      "source_file": "/path/to/file.py"
    }
  ],
  "depth": 1,
  "count": 1
}
```

**Example Use Cases:**
- Find all callers of a function (impact analysis)
- Find all subclasses of a class
- Identify dependent modules

### 3. Find Dependency Path

Find paths connecting two entities through relationships.

```http
GET /api/v1/dependency-path?source_entity_id=123&target_entity_id=789&max_depth=5
```

**Parameters:**
- `source_entity_id` (int, required): Starting entity ID
- `target_entity_id` (int, required): Target entity ID
- `max_depth` (int, optional): Maximum path length (1-10, default: 5)
- `relationship_types` (string, optional): Types to traverse

**Response:**
```json
{
  "source_entity_id": 123,
  "target_entity_id": 789,
  "paths": [
    [
      {
        "source_entity_id": 123,
        "target_entity_id": 456,
        "relationship_type": "calls",
        "target_name": "intermediate_function"
      },
      {
        "source_entity_id": 456,
        "target_entity_id": 789,
        "relationship_type": "calls",
        "target_name": "final_function"
      }
    ]
  ],
  "path_count": 1,
  "max_depth": 5
}
```

**Example Use Cases:**
- Understand call chains between functions
- Trace inheritance hierarchies
- Find connection paths for refactoring

## Python API

### RelationshipTracker

```python
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.storage.relationship_tracker import (
    RelationshipTracker,
    RelationshipType,
)

# Initialize
store = SQLiteStore("code_index.db")
tracker = RelationshipTracker(store)

# Add a single relationship
tracker.add_relationship(
    source_entity_id=func1_id,
    target_entity_id=func2_id,
    relationship_type=RelationshipType.CALLS,
    confidence_score=1.0,
    metadata={"line": 42, "call_type": "direct"}
)

# Add relationships in batch (faster)
relationships = [
    {
        "source_entity_id": func1_id,
        "target_entity_id": func2_id,
        "relationship_type": RelationshipType.CALLS,
        "confidence_score": 1.0,
    },
    {
        "source_entity_id": class1_id,
        "target_entity_id": class2_id,
        "relationship_type": RelationshipType.INHERITS,
        "confidence_score": 1.0,
    },
]
tracker.add_relationships_batch(relationships)

# Query dependencies
deps = tracker.get_dependencies(
    entity_id=func1_id,
    depth=2,
    relationship_types=[RelationshipType.CALLS]
)

# Query dependents
dependents = tracker.get_dependents(
    entity_id=func2_id,
    depth=1
)

# Find paths
paths = tracker.find_paths(
    source_id=func1_id,
    target_id=func3_id,
    max_depth=5
)

# Get relationship graph
graph = tracker.get_relationship_graph(
    entity_id=func1_id,
    depth=2
)
```

## Relationship Types

- **`calls`**: Function/method calls another
- **`inherits`**: Class inherits from another
- **`imports`**: Module imports another
- **`uses`**: Generic usage relationship
- **`contains`**: File contains function/class

## Performance

Optimized for typical code graphs:

- **Query Performance**: <100ms for depth 10 on 50-node chains
- **Batch Insert**: 100 relationships in <1 second
- **Cycle Handling**: Gracefully handles circular dependencies
- **Indexes**: 5 indexes for fast lookups

## Database Schema

```sql
CREATE TABLE relationships (
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

CREATE INDEX idx_rel_source ON relationships(source_entity_id);
CREATE INDEX idx_rel_target ON relationships(target_entity_id);
CREATE INDEX idx_rel_type ON relationships(relationship_type);
CREATE INDEX idx_rel_source_type ON relationships(source_entity_id, relationship_type);
CREATE INDEX idx_rel_target_type ON relationships(target_entity_id, relationship_type);
```

## Python Plugin Integration

The Python plugin automatically extracts relationships during indexing:

```python
# Automatically extracts:
# - Function call relationships (Tree-sitter based)
# - Class inheritance relationships
# - Import dependencies (planned)

# Example:
class BaseClass:
    pass

class DerivedClass(BaseClass):  # Inherits relationship
    def method1(self):
        self.method2()  # Calls relationship
    
    def method2(self):
        pass
```

## Testing

Comprehensive test suite with NetworkX validation:

```bash
# Run relationship tracker tests
pytest tests/test_relationship_tracker.py -v

# 23 tests covering:
# - Basic operations
# - Batch operations
# - Dependency queries
# - Path finding
# - Edge cases (cycles, missing entities)
# - NetworkX graph validation
# - Performance benchmarks
```

## Future Enhancements

Planned features:
- Import relationship resolution
- Cross-file dependency tracking
- Visualization support
- Impact analysis tools
- Refactoring suggestions
- Support for more languages (C++, Java, etc.)

## References

- Inspired by [nglite](https://github.com/netbrah/nglite) - C++ code graph extraction
- Validated with [NetworkX](https://networkx.org/) - Industry-standard graph library
- Based on problem statement requirements for lightweight relationship tracking

## Support

For issues or questions:
- See test examples in `tests/test_relationship_tracker.py`
- Check implementation in `mcp_server/storage/relationship_tracker.py`
- Review API examples above
