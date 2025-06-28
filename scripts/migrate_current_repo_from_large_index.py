#!/usr/bin/env python3
"""
Quick migration script to extract current repository from large index.
"""

import os
import sys
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from mcp_server.core.path_utils import PathUtils


def migrate_current_repo():
    """Migrate current repository from large index."""
    
    # Paths
    source_db = Path("/workspaces/Code-Index-MCP/.indexes/f7b49f5d0ae0/new_index.db")
    current_repo_path = str(PathUtils.get_workspace_root())
    repo_hash = hashlib.sha256(current_repo_path.encode()).hexdigest()[:12]
    
    # Output path
    output_dir = PathUtils.get_index_storage_path() / repo_hash
    output_dir.mkdir(exist_ok=True)
    output_db = output_dir / "code_index.db"
    
    print(f"Migrating current repository from large index...")
    print(f"Source: {source_db}")
    print(f"Target: {output_db}")
    print(f"Repository path: {current_repo_path}")
    print(f"Repository hash: {repo_hash}")
    
    # Remove existing if present
    if output_db.exists():
        output_db.unlink()
        print("Removed existing index")
    
    # Connect to databases
    source_conn = sqlite3.connect(str(source_db))
    target_conn = sqlite3.connect(str(output_db))
    
    try:
        # Create schema in target
        create_schema(target_conn)
        
        # Migrate data
        file_count = migrate_data(source_conn, target_conn, current_repo_path)
        
        print(f"\nMigrated {file_count} files successfully!")
        
        # Update registry
        update_registry(repo_hash, current_repo_path, output_db, file_count)
        
    finally:
        source_conn.close()
        target_conn.close()


def create_schema(conn):
    """Create necessary tables in target database."""
    cursor = conn.cursor()
    
    # Create repositories table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS repositories (
            id INTEGER PRIMARY KEY,
            path TEXT NOT NULL,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata JSON
        )
    """)
    
    # Create files table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS files (
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
        )
    """)
    
    # Create symbols table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS symbols (
            id INTEGER PRIMARY KEY,
            file_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            kind TEXT,
            line_start INTEGER,
            line_end INTEGER,
            column_start INTEGER,
            column_end INTEGER,
            signature TEXT,
            documentation TEXT,
            metadata JSON,
            FOREIGN KEY (file_id) REFERENCES files(id)
        )
    """)
    
    # Create indexes for symbols
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_symbols_name ON symbols(name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_symbols_file ON symbols(file_id)")
    
    # Create BM25 FTS5 table
    cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS bm25_content USING fts5(
            file_id UNINDEXED,
            filepath,
            filename,
            content,
            language,
            symbols,
            imports,
            comments,
            tokenize = 'porter unicode61',
            prefix = '2 3'
        )
    """)
    
    # Create indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_repo ON files(repository_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_path ON files(path)")
    
    conn.commit()


def migrate_data(source_conn, target_conn, repo_path):
    """Migrate data for the current repository."""
    source_cursor = source_conn.cursor()
    target_cursor = target_conn.cursor()
    
    # Insert repository
    target_cursor.execute("""
        INSERT INTO repositories (id, path, name, metadata)
        VALUES (1, ?, 'Code-Index-MCP', '{}')
    """, (repo_path,))
    
    # Get files from current repo (excluding test_repos)
    source_cursor.execute("""
        SELECT DISTINCT b.file_id, b.filepath, b.filename, b.content, 
               b.language, b.symbols, b.imports, b.comments
        FROM bm25_content b
        WHERE b.filepath LIKE ? || '%'
        AND b.filepath NOT LIKE '%/test_repos/%'
        ORDER BY b.file_id
    """, (repo_path,))
    
    file_count = 0
    new_file_id = 1
    file_id_mapping = {}  # old_file_id -> new_file_id
    
    for row in source_cursor.fetchall():
        old_file_id, filepath, filename, content, language, symbols, imports, comments = row
        
        # Store file ID mapping
        file_id_mapping[old_file_id] = new_file_id
        
        # Insert into files table
        relative_path = filepath[len(repo_path):].lstrip('/')
        
        target_cursor.execute("""
            INSERT INTO files (id, repository_id, path, relative_path, language,
                             size, hash, last_modified, indexed_at, metadata)
            VALUES (?, 1, ?, ?, ?, 0, '', datetime('now'), datetime('now'), '{}')
        """, (new_file_id, filepath, relative_path, language))
        
        # Insert into bm25_content
        target_cursor.execute("""
            INSERT INTO bm25_content 
            (file_id, filepath, filename, content, language, symbols, imports, comments)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (new_file_id, filepath, filename, content, language, symbols, imports, comments))
        
        new_file_id += 1
        file_count += 1
        
        if file_count % 100 == 0:
            print(f"  Migrated {file_count} files...")
            target_conn.commit()
    
    # Migrate symbols
    print("\n  Migrating symbols...")
    symbol_count = 0
    
    # Get unique file paths we migrated
    migrated_files = list(file_id_mapping.keys())
    
    if migrated_files:
        # Query symbols from files table join
        placeholders = ','.join(['?'] * len(migrated_files))
        source_cursor.execute(f"""
            SELECT s.file_id, s.name, s.kind, s.line_start, s.line_end,
                   s.column_start, s.column_end, s.signature, s.documentation, s.metadata
            FROM symbols s
            WHERE s.file_id IN ({placeholders})
        """, migrated_files)
        
        for row in source_cursor.fetchall():
            old_file_id = row[0]
            new_file_id = file_id_mapping.get(old_file_id)
            
            if new_file_id:
                target_cursor.execute("""
                    INSERT INTO symbols 
                    (file_id, name, kind, line_start, line_end, column_start, column_end,
                     signature, documentation, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (new_file_id,) + row[1:])
                
                symbol_count += 1
        
        print(f"  Migrated {symbol_count} symbols")
    
    target_conn.commit()
    return file_count


def update_registry(repo_hash, repo_path, index_path, file_count):
    """Update repository registry."""
    import json
    
    registry_path = PathUtils.get_index_storage_path() / "repository_registry.json"
    
    # Load existing registry
    if registry_path.exists():
        with open(registry_path, 'r') as f:
            registry = json.load(f)
    else:
        registry = {}
    
    # Add/update current repo
    registry[repo_hash] = {
        "repository_id": repo_hash,
        "name": "Code-Index-MCP",
        "path": repo_path,
        "index_path": str(index_path),
        "language_stats": {"python": file_count},  # Simplified
        "total_files": file_count,
        "total_symbols": 0,
        "indexed_at": datetime.now().isoformat(),
        "active": True,
        "priority": 10  # Higher priority for current repo
    }
    
    # Write back
    with open(registry_path, 'w') as f:
        json.dump(registry, f, indent=2)
    
    print(f"\nUpdated registry: {registry_path}")


if __name__ == "__main__":
    migrate_current_repo()