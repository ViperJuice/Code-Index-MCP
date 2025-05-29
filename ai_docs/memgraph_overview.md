# Memgraph Overview for Code-Index-MCP

## What is Memgraph?

Memgraph is an open-source, in-memory graph database built for real-time streaming and high-performance graph analytics. It's designed for teams that need advanced analytical insights with Neo4j compatibility but up to 8x faster performance.

## Key Features

### Core Capabilities
- **In-Memory Architecture**: Stores data in RAM for near-instant access and processing
- **Cypher Query Language**: Uses the standardized Cypher query language over Bolt protocol
- **ACID Compliance**: Supports strongly consistent ACID transactions
- **Neo4j Compatibility**: Drop-in replacement for Neo4j with better performance

### Performance Characteristics
- **Speed**: Up to 8x faster than Neo4j for graph traversals
- **Throughput**: Handles over 1,000 transactions per second
- **Scale**: Supports graph sizes from 100 GB to 4 TB
- **Concurrency**: High performance in concurrent environments

### Developer Features
- **Multi-Language Support**: C#, C/C++, Go, Java, JavaScript, Node.js, PHP, Python, Ruby, Rust
- **Custom Query Modules**: Extend functionality with Python, C++, or Rust modules
- **Streaming Integration**: Direct connections to Kafka, SQL, CSV
- **Built-in Algorithms**: BFS, DFS, Weighted Shortest Path, All Shortest Paths

## Python Integration

### Client Libraries

1. **GQLAlchemy** (Recommended)
   ```python
   from gqlalchemy import Memgraph, Node, Relationship
   
   # Connect to Memgraph
   memgraph = Memgraph(host='127.0.0.1', port=7687)
   
   # Create nodes and relationships
   node1 = Node(labels="Function", name="parseFile")
   node2 = Node(labels="Function", name="processAST")
   rel = Relationship(type="CALLS", start_node=node1, end_node=node2)
   ```

2. **Neo4j Python Driver** (Compatible)
   ```python
   from neo4j import GraphDatabase
   
   driver = GraphDatabase.driver("bolt://localhost:7687")
   with driver.session() as session:
       result = session.run("MATCH (n) RETURN n LIMIT 10")
   ```

3. **pymgclient** (Low-level)
   ```python
   import mgclient
   
   conn = mgclient.connect(host='127.0.0.1', port=7687)
   cursor = conn.cursor()
   cursor.execute("MATCH (n) RETURN n")
   ```

### Custom Query Modules

Create custom Python procedures for specialized analysis:

```python
import mgp

@mgp.read_proc
def analyze_dependencies(ctx: mgp.ProcCtx,
                        start_node: mgp.Vertex) -> mgp.Record(dependencies=list):
    """Find all dependencies of a given code element."""
    visited = set()
    dependencies = []
    
    def traverse(node):
        if node.id in visited:
            return
        visited.add(node.id)
        
        for edge in node.out_edges:
            if edge.type == "DEPENDS_ON":
                dependencies.append({
                    "name": edge.to_vertex.properties.get("name"),
                    "type": edge.to_vertex.properties.get("type")
                })
                traverse(edge.to_vertex)
    
    traverse(start_node)
    return mgp.Record(dependencies=dependencies)
```

## Use Cases for Code Analysis

### 1. Dependency Graph
```cypher
// Create function nodes
CREATE (f1:Function {name: "main", file: "/src/main.py"})
CREATE (f2:Function {name: "parse", file: "/src/parser.py"})
CREATE (f1)-[:CALLS]->(f2)

// Find all dependencies
MATCH (f:Function {name: "main"})-[:CALLS*]->(dep)
RETURN dep.name, dep.file
```

### 2. Import Analysis
```cypher
// Model import relationships
CREATE (m1:Module {name: "app.main"})
CREATE (m2:Module {name: "utils.parser"})
CREATE (m1)-[:IMPORTS]->(m2)

// Find circular imports
MATCH (m1:Module)-[:IMPORTS*]->(m2:Module)-[:IMPORTS*]->(m1)
RETURN m1.name, m2.name
```

### 3. Call Graph
```cypher
// Create call relationships
CREATE (f1:Function {name: "process_data"})
CREATE (f2:Function {name: "validate"})
CREATE (f3:Function {name: "transform"})
CREATE (f1)-[:CALLS {line: 45}]->(f2)
CREATE (f1)-[:CALLS {line: 52}]->(f3)

// Find call paths
MATCH path = (start:Function {name: "main"})-[:CALLS*]->(:Function)
RETURN path
```

### 4. Symbol Resolution
```cypher
// Model symbol definitions and references
CREATE (s:Symbol {name: "CONFIG", type: "variable", scope: "global"})
CREATE (d:Definition {file: "/config.py", line: 10})-[:DEFINES]->(s)
CREATE (r1:Reference {file: "/main.py", line: 25})-[:REFERENCES]->(s)
CREATE (r2:Reference {file: "/utils.py", line: 40})-[:REFERENCES]->(s)

// Find all references to a symbol
MATCH (s:Symbol {name: "CONFIG"})<-[:REFERENCES]-(ref)
RETURN ref.file, ref.line
```

## Integration with Code-Index-MCP

### Architecture Integration

Memgraph can be integrated as a new container in the Level 2 architecture:

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────┐
│   API Gateway   │────▶│  Dispatcher  │────▶│   Plugins   │
│   (FastAPI)     │     │              │     │ (Language)  │
└─────────────────┘     └──────────────┘     └─────────────┘
         │                      │                     │
         ▼                      ▼                     ▼
┌─────────────────┐     ┌──────────────┐     ┌─────────────┐
│  Local Index    │     │   Memgraph   │     │  Embedding  │
│  (SQLite+FTS5)  │     │ (Graph Store)│     │   Service   │
└─────────────────┘     └──────────────┘     └─────────────┘
```

### Data Flow

1. **During Indexing**:
   - Plugins parse code and extract symbols
   - Basic data stored in SQLite for fast lookup
   - Relationships stored in Memgraph for context analysis

2. **During Querying**:
   - Simple searches use SQLite FTS5
   - Context queries use Memgraph traversals
   - Complex analysis combines both stores

### Benefits for Code Analysis

1. **Performance**: In-memory processing for fast graph traversals
2. **Flexibility**: Cypher queries for complex relationship analysis
3. **Scalability**: Handles large codebases with millions of relationships
4. **Real-time**: Updates relationships as code changes
5. **Algorithms**: Built-in algorithms for common analysis patterns

## Configuration

### Docker Deployment
```yaml
version: '3.8'
services:
  memgraph:
    image: memgraph/memgraph:latest
    ports:
      - "7687:7687"
      - "3000:3000"
    volumes:
      - memgraph_data:/var/lib/memgraph
    environment:
      - MEMGRAPH_TELEMETRY_ENABLED=false
```

### Connection Configuration
```python
# In config.py
MEMGRAPH_CONFIG = {
    'host': os.getenv('MEMGRAPH_HOST', 'localhost'),
    'port': int(os.getenv('MEMGRAPH_PORT', 7687)),
    'username': os.getenv('MEMGRAPH_USER', ''),
    'password': os.getenv('MEMGRAPH_PASS', ''),
    'encrypted': False
}
```

## Performance Tuning

### Memory Configuration
```
--memory-limit=4096MB
--storage-gc-cycle-sec=300
--storage-snapshot-interval-sec=300
```

### Query Optimization
- Use indexes on frequently queried properties
- Limit traversal depth for exploratory queries
- Use `PROFILE` to analyze query performance
- Leverage built-in algorithms for common patterns

## Security Considerations

1. **Authentication**: Configure username/password authentication
2. **SSL/TLS**: Enable encryption for production
3. **Access Control**: Use role-based access control
4. **Audit Logging**: Enable query logging for compliance

## References

- [Memgraph Documentation](https://memgraph.com/docs)
- [GQLAlchemy Python ORM](https://github.com/memgraph/gqlalchemy)
- [MAGE Algorithm Library](https://github.com/memgraph/mage)
- [Cypher Query Language](https://memgraph.com/docs/cypher)