-- MCP Server Initial Schema Migration
-- Version: 001
-- Description: Create initial database schema with core tables and indexes

-- Schema Version
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

-- Repositories
CREATE TABLE IF NOT EXISTS repositories (
    id INTEGER PRIMARY KEY,
    path TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSON
);

-- Files
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY,
    repository_id INTEGER NOT NULL,
    path TEXT NOT NULL,
    relative_path TEXT NOT NULL,
    language TEXT,
    size INTEGER,
    hash TEXT,
    content_hash TEXT,
    last_modified TIMESTAMP,
    indexed_at TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,
    deleted_at TIMESTAMP,
    metadata JSON,
    FOREIGN KEY (repository_id) REFERENCES repositories(id),
    UNIQUE(repository_id, relative_path)
);

CREATE INDEX IF NOT EXISTS idx_files_language ON files(language);
CREATE INDEX IF NOT EXISTS idx_files_hash ON files(hash);
CREATE INDEX IF NOT EXISTS idx_files_content_hash ON files(content_hash);
CREATE INDEX IF NOT EXISTS idx_files_deleted ON files(is_deleted);
CREATE INDEX IF NOT EXISTS idx_files_relative_path ON files(relative_path);

-- Symbols
CREATE TABLE IF NOT EXISTS symbols (
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

CREATE INDEX IF NOT EXISTS idx_symbols_name ON symbols(name);
CREATE INDEX IF NOT EXISTS idx_symbols_kind ON symbols(kind);
CREATE INDEX IF NOT EXISTS idx_symbols_file ON symbols(file_id);

-- Imports/Includes
CREATE TABLE IF NOT EXISTS imports (
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

CREATE INDEX IF NOT EXISTS idx_imports_file ON imports(file_id);
CREATE INDEX IF NOT EXISTS idx_imports_path ON imports(imported_path);

-- References (using symbol_references to avoid keyword conflict)
CREATE TABLE IF NOT EXISTS symbol_references (
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

CREATE INDEX IF NOT EXISTS idx_references_symbol ON symbol_references(symbol_id);
CREATE INDEX IF NOT EXISTS idx_references_file ON symbol_references(file_id);

-- Full-Text Search tables
CREATE VIRTUAL TABLE IF NOT EXISTS fts_symbols USING fts5(
    name,
    documentation,
    content=symbols,
    content_rowid=id
);

CREATE VIRTUAL TABLE IF NOT EXISTS fts_code USING fts5(
    content,
    file_id UNINDEXED
);

-- Fuzzy Search
CREATE TABLE IF NOT EXISTS symbol_trigrams (
    symbol_id INTEGER NOT NULL,
    trigram TEXT NOT NULL,
    FOREIGN KEY (symbol_id) REFERENCES symbols(id)
);

CREATE INDEX IF NOT EXISTS idx_trigrams ON symbol_trigrams(trigram);

-- Embeddings
CREATE TABLE IF NOT EXISTS embeddings (
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

CREATE INDEX IF NOT EXISTS idx_embeddings_file ON embeddings(file_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_symbol ON embeddings(symbol_id);

-- Cache Tables
CREATE TABLE IF NOT EXISTS query_cache (
    query_hash TEXT PRIMARY KEY,
    query_text TEXT NOT NULL,
    result JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    hit_count INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_cache_expires ON query_cache(expires_at);

CREATE TABLE IF NOT EXISTS parse_cache (
    file_hash TEXT PRIMARY KEY,
    ast JSON NOT NULL,
    parser_version TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Migration Log
CREATE TABLE IF NOT EXISTS migrations (
    id INTEGER PRIMARY KEY,
    version_from INTEGER,
    version_to INTEGER,
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    duration_ms INTEGER,
    status TEXT
);

-- Triggers to keep FTS in sync with symbols table
CREATE TRIGGER IF NOT EXISTS symbols_ai AFTER INSERT ON symbols
BEGIN
    INSERT INTO fts_symbols(rowid, name, documentation)
    VALUES (new.id, new.name, new.documentation);
END;

CREATE TRIGGER IF NOT EXISTS symbols_ad AFTER DELETE ON symbols
BEGIN
    DELETE FROM fts_symbols WHERE rowid = old.id;
END;

CREATE TRIGGER IF NOT EXISTS symbols_au AFTER UPDATE ON symbols
BEGIN
    UPDATE fts_symbols 
    SET name = new.name, documentation = new.documentation
    WHERE rowid = new.id;
END;

-- Insert initial schema version
INSERT INTO schema_version (version, description) 
VALUES (1, 'Initial schema creation');
