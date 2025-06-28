#!/usr/bin/env python3
"""
Final working indexing script for Code-Index-MCP.
Uses the migration approach which we know works.
"""

import sys
import os
from pathlib import Path
import json
import sqlite3
from datetime import datetime
import hashlib

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_server.core.path_utils import PathUtils


def create_working_index():
    """Create a working index by migrating from the large index."""
    print("Creating Working Index for Code-Index-MCP")
    print("=" * 60)
    
    # Paths
    workspace_root = PathUtils.get_workspace_root()
    repo_hash = "844145265d7a"
    source_db = Path(".indexes/f7b49f5d0ae0/new_index.db")
    target_dir = PathUtils.get_index_storage_path() / repo_hash
    target_db = target_dir / "code_index.db"
    
    # Check if source exists
    if not source_db.exists():
        print(f"Error: Source database not found at {source_db}")
        return False
    
    print(f"Source: {source_db}")
    print(f"Target: {target_db}")
    
    # Archive existing
    if target_db.exists():
        archive_dir = target_dir / "archive"
        archive_dir.mkdir(exist_ok=True)
        archive_path = archive_dir / f"code_index_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        target_db.rename(archive_path)
        print(f"Archived existing to: {archive_path}")
    
    # Ensure target directory exists
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # Connect to both databases
    source_conn = sqlite3.connect(str(source_db))
    target_conn = sqlite3.connect(str(target_db))
    
    try:
        # Create schema in target
        create_schema(target_conn)
        
        # Migrate current repository data
        stats = migrate_current_repo(source_conn, target_conn, str(workspace_root))
        
        print(f"\nMigration complete!")
        print(f"  Files: {stats['files']}")
        print(f"  Symbols: {stats['symbols']}")
        print(f"  BM25 docs: {stats['bm25']}")
        
        # Update registry
        update_registry(repo_hash, workspace_root, target_db, stats)
        
        return True
        
    finally:
        source_conn.close()
        target_conn.close()


def create_schema(conn):
    """Create the schema we know works."""
    cursor = conn.cursor()
    
    # Create tables that MCP expects
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS repositories (
            id INTEGER PRIMARY KEY,
            path TEXT NOT NULL,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata JSON
        );
        
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY,
            repository_id INTEGER,
            path TEXT NOT NULL,
            relative_path TEXT NOT NULL,
            language TEXT,
            size INTEGER,
            hash TEXT,
            last_modified TIMESTAMP,
            indexed_at TIMESTAMP,
            metadata JSON,
            FOREIGN KEY (repository_id) REFERENCES repositories(id)
        );
        
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
        );
        
        -- Create FTS5 tables for search
        CREATE VIRTUAL TABLE IF NOT EXISTS fts_code USING fts5(
            file_id UNINDEXED,
            content,
            tokenize = 'porter unicode61'
        );
        
        CREATE VIRTUAL TABLE IF NOT EXISTS fts_symbols USING fts5(
            symbol_id UNINDEXED,
            name,
            signature,
            documentation,
            tokenize = 'porter unicode61'
        );
        
        -- Also create BM25 content for compatibility
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
        );
        
        -- Create indexes
        CREATE INDEX IF NOT EXISTS idx_files_path ON files(path);
        CREATE INDEX IF NOT EXISTS idx_files_repo ON files(repository_id);
        CREATE INDEX IF NOT EXISTS idx_symbols_name ON symbols(name);
        CREATE INDEX IF NOT EXISTS idx_symbols_file ON symbols(file_id);
    """)
    
    conn.commit()


def migrate_current_repo(source_conn, target_conn, repo_path):
    """Migrate data for current repository."""
    source_cursor = source_conn.cursor()
    target_cursor = target_conn.cursor()
    
    stats = {"files": 0, "symbols": 0, "bm25": 0}
    
    # Insert repository
    target_cursor.execute("""
        INSERT INTO repositories (id, path, name, metadata)
        VALUES (1, ?, 'Code-Index-MCP', '{}')
    """, (repo_path,))
    
    # Migrate files and content from bm25_content
    print("\nMigrating files...")
    source_cursor.execute("""
        SELECT DISTINCT file_id, filepath, filename, content, language, symbols, imports, comments
        FROM bm25_content
        WHERE filepath LIKE ? || '%'
        AND filepath NOT LIKE '%/test_repos/%' 
        ORDER BY file_id
    """, (repo_path,))
    
    file_id_mapping = {}
    new_file_id = 1
    
    for row in source_cursor.fetchall():
        old_file_id, filepath, filename, content, language, symbols, imports, comments = row
        
        # Skip if not actually our repo file
        if not filepath.startswith(repo_path):
            continue
            
        file_id_mapping[old_file_id] = new_file_id
        relative_path = filepath[len(repo_path):].lstrip('/')
        
        # Insert into files
        target_cursor.execute("""
            INSERT INTO files (id, repository_id, path, relative_path, language,
                             size, hash, last_modified, indexed_at, metadata)
            VALUES (?, 1, ?, ?, ?, ?, '', datetime('now'), datetime('now'), '{}')
        """, (new_file_id, filepath, relative_path, language, len(content) if content else 0))
        
        # Insert into bm25_content
        target_cursor.execute("""
            INSERT INTO bm25_content 
            (file_id, filepath, filename, content, language, symbols, imports, comments)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (new_file_id, filepath, filename, content, language, symbols, imports, comments))
        
        # Also insert into fts_code
        if content:
            target_cursor.execute("""
                INSERT INTO fts_code (file_id, content)
                VALUES (?, ?)
            """, (new_file_id, content))
        
        new_file_id += 1
        stats["files"] += 1
        stats["bm25"] += 1
        
        if stats["files"] % 100 == 0:
            print(f"  Migrated {stats['files']} files...")
            target_conn.commit()
    
    # Try to migrate symbols if they exist
    print("\nMigrating symbols...")
    if file_id_mapping:
        try:
            placeholders = ','.join(['?'] * len(file_id_mapping))
            source_cursor.execute(f"""
                SELECT s.* FROM symbols s
                WHERE s.file_id IN ({placeholders})
            """, list(file_id_mapping.keys()))
            
            for row in source_cursor.fetchall():
                old_file_id = row[1]  # file_id is second column
                new_file_id = file_id_mapping.get(old_file_id)
                
                if new_file_id:
                    # Insert symbol with new file_id
                    target_cursor.execute("""
                        INSERT INTO symbols 
                        (file_id, name, kind, line_start, line_end, column_start, column_end,
                         signature, documentation, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (new_file_id,) + row[2:])  # Skip id and old file_id
                    
                    stats["symbols"] += 1
        except Exception as e:
            print(f"  Symbol migration skipped: {e}")
    
    target_conn.commit()
    print(f"\nMigrated {stats['files']} files successfully!")
    
    return stats


def update_registry(repo_hash, repo_path, index_path, stats):
    """Update repository registry."""
    registry_path = PathUtils.get_index_storage_path() / "repository_registry.json"
    
    if registry_path.exists():
        with open(registry_path, 'r') as f:
            registry = json.load(f)
    else:
        registry = {}
    
    registry[repo_hash] = {
        "repository_id": repo_hash,
        "name": "Code-Index-MCP",
        "path": str(repo_path),
        "index_path": str(index_path),
        "language_stats": {"python": stats["files"]},  # Simplified
        "total_files": stats["files"],
        "total_symbols": stats["symbols"],
        "indexed_at": datetime.now().isoformat(),
        "active": True,
        "priority": 10
    }
    
    with open(registry_path, 'w') as f:
        json.dump(registry, f, indent=2)
    
    print(f"\n✓ Registry updated")


if __name__ == "__main__":
    success = create_working_index()
    if success:
        print("\n✅ Working index created successfully!")
        print("You can now test MCP queries.")
    else:
        print("\n❌ Failed to create index")