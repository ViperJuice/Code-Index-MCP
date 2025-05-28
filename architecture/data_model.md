# Data Model

## Overview
This document defines the data structures and storage schema for the MCP Server's Local Index Store.

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
    path TEXT NOT NULL,
    relative_path TEXT NOT NULL,
    language TEXT,
    size INTEGER,
    hash TEXT,
    last_modified TIMESTAMP,
    indexed_at TIMESTAMP,
    metadata JSON,
    FOREIGN KEY (repository_id) REFERENCES repositories(id),
    UNIQUE(repository_id, path)
);

CREATE INDEX idx_files_language ON files(language);
CREATE INDEX idx_files_hash ON files(hash);
```

### Symbol
```sql
CREATE TABLE symbols (
    id INTEGER PRIMARY KEY,
    file_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    kind TEXT NOT NULL, -- function, class, variable, etc.
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

### Full-Text Search
```sql
CREATE VIRTUAL TABLE fts_symbols USING fts5(
    name,
    documentation,
    content=symbols,
    content_rowid=id
);

CREATE VIRTUAL TABLE fts_code USING fts5(
    content,
    file_id UNINDEXED,
    tokenize="trigram"
);
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

## Embedding Storage

### Code Embeddings
```sql
CREATE TABLE embeddings (
    id INTEGER PRIMARY KEY,
    file_id INTEGER,
    symbol_id INTEGER,
    chunk_start INTEGER,
    chunk_end INTEGER,
    embedding BLOB NOT NULL, -- Serialized vector
    model_version TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSON,
    FOREIGN KEY (file_id) REFERENCES files(id),
    FOREIGN KEY (symbol_id) REFERENCES symbols(id)
);

CREATE INDEX idx_embeddings_file ON embeddings(file_id);
CREATE INDEX idx_embeddings_symbol ON embeddings(symbol_id);
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