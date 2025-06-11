# Data Model

## Overview
This document defines the data structures and storage schema for Code-Index-MCP's multi-language indexing system. The system uses SQLite for symbol storage with FTS5 for text search, and Qdrant for vector embeddings to support semantic search across 48 programming languages.

## Core Entities

### Repository
```sql
CREATE TABLE repositories (
    id INTEGER PRIMARY KEY,
    path TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSON
);
```

### File
```sql
CREATE TABLE files (
    id INTEGER PRIMARY KEY,
    repository_id INTEGER NOT NULL,
    path TEXT NOT NULL, -- Absolute path (for backward compatibility)
    relative_path TEXT NOT NULL, -- Primary identifier for portability
    language TEXT,
    size INTEGER,
    hash TEXT, -- File hash (for change detection)
    content_hash TEXT, -- Content hash (for move detection)
    last_modified TIMESTAMP,
    indexed_at TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE, -- Soft delete flag
    deleted_at TIMESTAMP,
    metadata JSON,
    FOREIGN KEY (repository_id) REFERENCES repositories(id),
    UNIQUE(repository_id, relative_path) -- Changed from path to relative_path
);

CREATE INDEX idx_files_language ON files(language);
CREATE INDEX idx_files_hash ON files(hash);
CREATE INDEX idx_files_content_hash ON files(content_hash);
CREATE INDEX idx_files_deleted ON files(is_deleted);
CREATE INDEX idx_files_relative_path ON files(relative_path);
```

### File Move Tracking
```sql
CREATE TABLE file_moves (
    id INTEGER PRIMARY KEY,
    repository_id INTEGER NOT NULL,
    old_relative_path TEXT NOT NULL,
    new_relative_path TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    moved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    move_type TEXT, -- 'rename', 'relocate', 'restructure'
    FOREIGN KEY (repository_id) REFERENCES repositories(id)
);

CREATE INDEX idx_moves_content_hash ON file_moves(content_hash);
CREATE INDEX idx_moves_timestamp ON file_moves(moved_at);
```

### Symbol
```sql
CREATE TABLE symbols (
    id INTEGER PRIMARY KEY,
    file_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    kind TEXT NOT NULL, -- function, class, variable, section, paragraph, etc.
    line_start INTEGER NOT NULL,
    line_end INTEGER NOT NULL,
    column_start INTEGER,
    column_end INTEGER,
    signature TEXT,
    documentation TEXT,
    metadata JSON,
    FOREIGN KEY (file_id) REFERENCES files(id)
);

CREATE INDEX idx_symbols_name ON symbols(name);
CREATE INDEX idx_symbols_kind ON symbols(kind);
CREATE INDEX idx_symbols_file ON symbols(file_id);
```

### Document Chunks
```sql
CREATE TABLE document_chunks (
    id INTEGER PRIMARY KEY,
    file_id INTEGER NOT NULL,
    symbol_id INTEGER,
    content TEXT NOT NULL,
    context_before TEXT,  -- Summary of previous chunk
    context_after TEXT,   -- Summary of next chunk
    section_path TEXT,    -- JSON array of section hierarchy
    chunk_index INTEGER NOT NULL,
    total_chunks INTEGER NOT NULL,
    chunk_size INTEGER NOT NULL,
    overlap_size INTEGER,
    metadata JSON,
    FOREIGN KEY (file_id) REFERENCES files(id),
    FOREIGN KEY (symbol_id) REFERENCES symbols(id)
);

CREATE INDEX idx_chunks_file ON document_chunks(file_id);
CREATE INDEX idx_chunks_symbol ON document_chunks(symbol_id);
CREATE INDEX idx_chunks_order ON document_chunks(file_id, chunk_index);
```

### Import/Include
```sql
CREATE TABLE imports (
    id INTEGER PRIMARY KEY,
    file_id INTEGER NOT NULL,
    imported_path TEXT NOT NULL,
    imported_name TEXT,
    alias TEXT,
    line_number INTEGER,
    is_relative BOOLEAN,
    metadata JSON,
    FOREIGN KEY (file_id) REFERENCES files(id)
);

CREATE INDEX idx_imports_file ON imports(file_id);
CREATE INDEX idx_imports_path ON imports(imported_path);
```

### Reference
```sql
CREATE TABLE references (
    id INTEGER PRIMARY KEY,
    symbol_id INTEGER NOT NULL,
    file_id INTEGER NOT NULL,
    line_number INTEGER NOT NULL,
    column_number INTEGER,
    reference_kind TEXT, -- call, read, write, etc.
    metadata JSON,
    FOREIGN KEY (symbol_id) REFERENCES symbols(id),
    FOREIGN KEY (file_id) REFERENCES files(id)
);

CREATE INDEX idx_references_symbol ON references(symbol_id);
CREATE INDEX idx_references_file ON references(file_id);
```

## Search Indices

### Full-Text Search with BM25
```sql
-- Symbol search with BM25 ranking
CREATE VIRTUAL TABLE fts_symbols USING fts5(
    name,
    documentation,
    content=symbols,
    content_rowid=id,
    tokenize='porter unicode61'
);

-- Code content search
CREATE VIRTUAL TABLE fts_code USING fts5(
    content,
    file_id UNINDEXED,
    tokenize="trigram"
);

-- Document chunk search with BM25
CREATE VIRTUAL TABLE fts_documents USING fts5(
    content,
    context_before,
    context_after,
    section_path,
    document_title UNINDEXED,
    content=document_chunks,
    content_rowid=id,
    tokenize='porter unicode61'
);

-- BM25 search query example
SELECT 
    dc.*,
    bm25(fts_documents) as rank,
    snippet(fts_documents, 0, '<mark>', '</mark>', '...', 20) as highlight
FROM document_chunks dc
JOIN fts_documents ON dc.id = fts_documents.rowid
WHERE fts_documents MATCH ?
ORDER BY rank DESC
LIMIT 20;
```

### Fuzzy Search
```sql
CREATE TABLE symbol_trigrams (
    symbol_id INTEGER NOT NULL,
    trigram TEXT NOT NULL,
    FOREIGN KEY (symbol_id) REFERENCES symbols(id)
);

CREATE INDEX idx_trigrams ON symbol_trigrams(trigram);
```

## Language Configuration

### Language Registry
```sql
CREATE TABLE languages (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    file_extensions JSON NOT NULL, -- [".py", ".pyw"]
    parser_type TEXT NOT NULL, -- "enhanced" or "generic"
    tree_sitter_grammar TEXT,
    query_patterns JSON, -- Language-specific queries
    metadata JSON
);

-- Insert 48 supported languages
INSERT INTO languages (name, file_extensions, parser_type) VALUES
    ('python', '["*.py", "*.pyw"]', 'enhanced'),
    ('javascript', '["*.js", "*.jsx", "*.mjs"]', 'enhanced'),
    ('c', '["*.c", "*.h"]', 'enhanced'),
    ('cpp', '["*.cpp", "*.hpp", "*.cc", "*.cxx"]', 'enhanced'),
    ('dart', '["*.dart"]', 'enhanced'),
    ('html', '["*.html", "*.htm"]', 'enhanced'),
    ('css', '["*.css", "*.scss", "*.sass"]', 'enhanced'),
    ('go', '["*.go"]', 'generic'),
    ('rust', '["*.rs"]', 'generic'),
    ('java', '["*.java"]', 'generic'),
    -- ... 38 more languages
;
```

## Vector Storage (Qdrant)

### Collection Schema (Updated for Path Management)
```json
{
    "collection_name": "code-embeddings-{language}",
    "vectors": {
        "size": 1024,
        "distance": "Cosine"
    },
    "payload_schema": {
        "file_path": "keyword",           // Legacy: absolute path
        "relative_path": "keyword",       // Primary: relative path
        "content_hash": "keyword",        // File content hash
        "chunk_hash": "keyword",          // Chunk-specific hash
        "repository_id": "integer",       // Link to SQLite
        "symbol_name": "keyword", 
        "symbol_kind": "keyword",
        "language": "keyword",
        "line": "integer",
        "signature": "text",
        "content": "text",
        "context_before": "text",
        "context_after": "text",
        "section_path": "keyword[]",
        "chunk_index": "integer",
        "document_type": "keyword",
        "indexed_at": "date",
        "is_deleted": "boolean"           // Soft delete flag
    }
}
```

### Contextual Embedding Metadata
```json
{
    "model": "voyage-code-3",
    "embedding_dimension": 1024,
    "indexed_at": "2025-06-07T00:00:00Z",
    "file_hash": "sha256:...",
    "language": "python",
    "symbol_type": "function",
    "embedding_type": "contextual",
    "context_window": {
        "before": 100,
        "after": 100
    },
    "section_hierarchy": ["API Reference", "Authentication", "JWT"],
    "chunk_metadata": {
        "index": 3,
        "total": 10,
        "size": 1500,
        "overlap": 200
    }
}
```

### Hybrid Search Index
```json
{
    "collection_name": "hybrid-search-{document_type}",
    "vectors": {
        "contextual": {
            "size": 1024,
            "distance": "Cosine"
        }
    },
    "sparse_vectors": {
        "bm25": {
            "modifier": "idf"
        }
    },
    "payload_schema": {
        "content": "text",
        "bm25_score": "float",
        "section_path": "keyword[]",
        "document_id": "keyword",
        "chunk_id": "keyword"
    }
}
```

## Cache Tables

### Query Cache
```sql
CREATE TABLE query_cache (
    query_hash TEXT PRIMARY KEY,
    query_text TEXT NOT NULL,
    result JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    hit_count INTEGER DEFAULT 0
);

CREATE INDEX idx_cache_expires ON query_cache(expires_at);
```

### Parse Cache
```sql
CREATE TABLE parse_cache (
    file_hash TEXT PRIMARY KEY,
    ast JSON NOT NULL,
    parser_version TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Metadata Schema

### Repository Metadata
```json
{
    "vcs": "git",
    "remote_url": "https://github.com/...",
    "default_branch": "main",
    "languages": ["python", "javascript"],
    "framework": "django",
    "index_config": {
        "ignore_patterns": ["*.test.js"],
        "max_file_size": 1048576
    }
}
```

### File Metadata
```json
{
    "encoding": "utf-8",
    "mime_type": "text/x-python",
    "complexity": 42,
    "test_file": false,
    "generated": false,
    "metrics": {
        "lines_of_code": 150,
        "cyclomatic_complexity": 10
    },
    "document_info": {
        "type": "markdown",
        "has_toc": true,
        "has_code_blocks": true,
        "sections_count": 12,
        "max_heading_level": 3,
        "estimated_reading_time": "5 min"
    }
}
```

### Document Chunk Metadata
```json
{
    "chunk_strategy": "hierarchical",
    "chunk_params": {
        "size": 1500,
        "overlap": 200,
        "boundary": "section"
    },
    "context_generation": {
        "method": "summarization",
        "window_size": 100
    },
    "section_info": {
        "title": "Installation Guide",
        "level": 2,
        "parent": "Getting Started",
        "path": ["Getting Started", "Installation Guide"],
        "has_subsections": true
    },
    "quality_metrics": {
        "coherence_score": 0.92,
        "completeness": 0.98,
        "has_complete_sentences": true
    }
}
```

### Symbol Metadata
```json
{
    "visibility": "public",
    "static": false,
    "async": true,
    "decorators": ["@property"],
    "type_hints": {
        "parameters": ["str", "int"],
        "return": "bool"
    },
    "references_count": 42
}
```

## Index Versioning

### Schema Version
```sql
CREATE TABLE schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);
```

### Migration Log
```sql
CREATE TABLE migrations (
    id INTEGER PRIMARY KEY,
    version_from INTEGER,
    version_to INTEGER,
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    duration_ms INTEGER,
    status TEXT
);
```

## Performance Optimizations

### Partitioning Strategy
- Partition by repository for large codebases
- Separate tables for different languages
- Archive old versions

### Index Strategy
- Covering indices for common queries
- Partial indices for filtered searches
- Expression indices for computed values

### Compression
- Compress AST data
- Compress embeddings
- Deduplicate common strings

## Data Lifecycle

### Retention Policy
- Keep parse cache for 7 days
- Keep query cache for 1 day
- Archive old symbol versions
- Purge orphaned records

### Backup Strategy
- Incremental backups daily
- Full backups weekly
- Test restoration monthly
- Encrypted off-site storage

## Query Examples

### Find Symbol Definition
```sql
SELECT s.*, f.path
FROM symbols s
JOIN files f ON s.file_id = f.id
WHERE s.name = ? AND s.kind = 'function';
```

### Find All References
```sql
SELECT r.*, f.path, s.name
FROM references r
JOIN files f ON r.file_id = f.id
JOIN symbols s ON r.symbol_id = s.id
WHERE s.name = ?;
```

### Semantic Search
```sql
WITH similar AS (
    SELECT file_id, symbol_id, 
           vector_distance(embedding, ?) as distance
    FROM embeddings
    WHERE model_version = ?
    ORDER BY distance
    LIMIT 20
)
SELECT s.*, f.path
FROM similar
JOIN symbols s ON similar.symbol_id = s.id
JOIN files f ON s.file_id = f.id;
```

## Graph Database Schema (Memgraph)

### Node Types

#### File Node
```cypher
CREATE (f:File {
    path: '/src/main.py',
    language: 'python',
    hash: 'abc123...',
    size: 1024,
    last_modified: timestamp()
})
```

#### Module Node
```cypher
CREATE (m:Module {
    name: 'app.core',
    path: '/src/app/core.py',
    package: 'app'
})
```

#### Symbol Nodes
```cypher
// Class
CREATE (c:Class:Symbol {
    name: 'UserService',
    file: '/src/services/user.py',
    line: 15,
    docstring: 'Handles user operations'
})

// Function
CREATE (f:Function:Symbol {
    name: 'process_data',
    file: '/src/utils.py',
    line: 42,
    signature: 'def process_data(data: List[Dict]) -> Dict',
    async: true
})

// Variable
CREATE (v:Variable:Symbol {
    name: 'CONFIG',
    file: '/src/config.py',
    line: 10,
    type: 'dict',
    scope: 'global'
})
```

### Relationship Types

#### Structural Relationships
```cypher
// File contains symbols
(file:File)-[:CONTAINS]->(symbol:Symbol)

// Module exports symbols
(module:Module)-[:EXPORTS]->(symbol:Symbol)

// Class inheritance
(child:Class)-[:INHERITS]->(parent:Class)

// Class implements interface
(class:Class)-[:IMPLEMENTS]->(interface:Interface)

// Nested definitions
(class:Class)-[:DEFINES]->(method:Function)
```

#### Dependency Relationships
```cypher
// Module imports
(module:Module)-[:IMPORTS {line: 1, alias: 'np'}]->(imported:Module)

// Function calls
(caller:Function)-[:CALLS {line: 45, column: 12}]->(callee:Function)

// Symbol references
(function:Function)-[:REFERENCES {line: 52}]->(symbol:Symbol)

// Variable usage
(function:Function)-[:USES]->(variable:Variable)

// Type dependencies
(class:Class)-[:DEPENDS_ON]->(type:Class)
```

#### Analysis Relationships
```cypher
// Possible calls (from static analysis)
(function:Function)-[:MAY_CALL {confidence: 0.85}]->(target:Function)

// Overrides
(method:Function)-[:OVERRIDES]->(parent_method:Function)

// Test coverage
(test:Function)-[:TESTS]->(function:Function)
```

### Graph Indexes
```cypher
// Create indexes for performance
CREATE INDEX ON :File(path);
CREATE INDEX ON :Module(name);
CREATE INDEX ON :Symbol(name);
CREATE INDEX ON :Function(name);
CREATE INDEX ON :Class(name);

// Unique constraints
CREATE CONSTRAINT ON (f:File) ASSERT f.path IS UNIQUE;
CREATE CONSTRAINT ON (m:Module) ASSERT m.name IS UNIQUE;
```

### Graph Queries

#### Find Symbol Context
```cypher
MATCH (s:Symbol {name: $symbol_name})
OPTIONAL MATCH (s)<-[:CONTAINS]-(file:File)
OPTIONAL MATCH (s)-[:CALLS]->(calls:Function)
OPTIONAL MATCH (s)<-[:CALLS]-(called_by:Function)
OPTIONAL MATCH (s)-[:USES]->(uses:Variable)
RETURN s, file, collect(DISTINCT calls) as calls, 
       collect(DISTINCT called_by) as called_by,
       collect(DISTINCT uses) as uses
```

#### Dependency Analysis
```cypher
// Find all dependencies of a module
MATCH path = (m:Module {name: $module_name})-[:IMPORTS*]->(dep:Module)
RETURN dep.name, length(path) as distance
ORDER BY distance

// Find circular dependencies
MATCH (m1:Module)-[:IMPORTS*]->(m2:Module)-[:IMPORTS*]->(m1)
WHERE m1.name < m2.name
RETURN DISTINCT m1.name, m2.name
```

#### Impact Analysis
```cypher
// What will be affected if we change a function?
MATCH (f:Function {name: $function_name})
OPTIONAL MATCH (f)<-[:CALLS*1..3]-(affected:Function)
OPTIONAL MATCH (f)<-[:REFERENCES*1..2]-(refs:Symbol)
RETURN f, 
       collect(DISTINCT affected) as affected_functions,
       collect(DISTINCT refs) as affected_symbols
```

#### Call Graph
```cypher
// Get call graph with depth limit
MATCH path = (start:Function {name: $start_function})-[:CALLS*..5]->(:Function)
RETURN path
```

### Graph Algorithms

#### PageRank for Important Functions
```cypher
CALL algo.pagerank({
    nodeProjection: 'Function',
    relationshipProjection: {
        CALLS: {
            type: 'CALLS',
            orientation: 'REVERSE'
        }
    }
}) YIELD nodeId, score
RETURN gds.util.asNode(nodeId).name AS function, score
ORDER BY score DESC
LIMIT 10
```

#### Community Detection for Modules
```cypher
CALL algo.louvain({
    nodeProjection: 'Module',
    relationshipProjection: 'IMPORTS'
}) YIELD nodeId, communityId
RETURN communityId, collect(gds.util.asNode(nodeId).name) as modules
ORDER BY size(modules) DESC
```

### Data Synchronization

#### SQLite to Memgraph Sync
```python
# Sync strategy
def sync_to_graph(file_data, symbols, relationships):
    # Create file node
    graph.execute("""
        MERGE (f:File {path: $path})
        SET f.language = $language,
            f.hash = $hash,
            f.last_modified = $last_modified
    """, file_data)
    
    # Create symbol nodes
    for symbol in symbols:
        graph.execute("""
            MERGE (s:Symbol:{type} {name: $name, file: $file})
            SET s.line = $line,
                s.docstring = $docstring
        """.format(type=symbol['type']), symbol)
    
    # Create relationships
    for rel in relationships:
        graph.execute("""
            MATCH (a:Symbol {name: $from_name, file: $from_file})
            MATCH (b:Symbol {name: $to_name, file: $to_file})
            MERGE (a)-[r:{type}]->(b)
            SET r.line = $line
        """.format(type=rel['type']), rel)
```

### Performance Considerations

#### Memory Usage
- Estimated 1KB per node (file/symbol)
- Estimated 100 bytes per relationship
- For 100K files with 10 symbols each: ~1GB RAM

#### Query Optimization
- Use node labels in all queries
- Limit traversal depth
- Use indexes for lookups
- Profile queries with EXPLAIN