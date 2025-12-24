#!/usr/bin/env python3
"""
Create an MCP index for the current repository
"""

import os
import sys
import sqlite3
from pathlib import Path
import hashlib
from datetime import datetime
import json
from mcp_server.core.path_utils import PathUtils

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def create_repo_index():
    """Create an MCP index for the current repository."""
    repo_root = Path("PathUtils.get_workspace_root()")
    index_dir = repo_root / ".mcp-index"
    index_dir.mkdir(exist_ok=True)
    
    db_path = index_dir / "code_index.db"
    
    print(f"📦 Creating index for Code-Index-MCP repository...")
    print(f"   Repository: {repo_root}")
    print(f"   Database: {db_path}")
    
    # Create database
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Create schema
    cursor.executescript("""
        -- Repository table
        CREATE TABLE IF NOT EXISTS repositories (
            id INTEGER PRIMARY KEY,
            path TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            metadata TEXT DEFAULT '{}'
        );
        
        -- Files table
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY,
            repository_id INTEGER,
            path TEXT NOT NULL,
            relative_path TEXT NOT NULL,
            language TEXT,
            size INTEGER,
            content_hash TEXT,
            metadata TEXT DEFAULT '{}',
            UNIQUE(repository_id, relative_path),
            FOREIGN KEY (repository_id) REFERENCES repositories(id)
        );
        
        -- BM25 content table
        CREATE VIRTUAL TABLE IF NOT EXISTS bm25_content USING fts5(
            file_id UNINDEXED,
            filepath,
            filename,
            content,
            language,
            tokenize = 'porter unicode61',
            prefix = '2 3'
        );
        
        -- BM25 index status
        CREATE TABLE IF NOT EXISTS bm25_index_status (
            file_id INTEGER PRIMARY KEY,
            filepath TEXT NOT NULL,
            content_hash TEXT,
            indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    # Create repository
    cursor.execute(
        "INSERT OR REPLACE INTO repositories (path, name) VALUES (?, ?)",
        (".", "code-index-mcp")  # Use relative path
    )
    repo_id = cursor.lastrowid
    
    # Index Python files in mcp_server directory
    indexed_count = 0
    for py_file in (repo_root / "mcp_server").rglob("*.py"):
        # Skip test files and __pycache__
        if "__pycache__" in str(py_file) or "test" in py_file.name:
            continue
            
        try:
            with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Get relative path from repo root
            rel_path = py_file.relative_to(repo_root)
            
            # Calculate content hash
            content_hash = hashlib.md5(content.encode()).hexdigest()
            
            # Insert file record
            cursor.execute(
                """INSERT OR REPLACE INTO files 
                   (repository_id, path, relative_path, language, size, content_hash)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (repo_id, str(rel_path), str(rel_path), "py", len(content), content_hash)
            )
            file_id = cursor.lastrowid
            
            # Index in BM25
            cursor.execute(
                """INSERT INTO bm25_content 
                   (file_id, filepath, filename, content, language)
                   VALUES (?, ?, ?, ?, ?)""",
                (file_id, str(rel_path), py_file.name, content, "py")
            )
            
            # Update index status
            cursor.execute(
                """INSERT OR REPLACE INTO bm25_index_status 
                   (file_id, filepath, content_hash)
                   VALUES (?, ?, ?)""",
                (file_id, str(rel_path), content_hash)
            )
            
            indexed_count += 1
            
        except Exception as e:
            print(f"   Warning: Failed to index {py_file}: {e}")
            continue
    
    conn.commit()
    
    # Create metadata file
    metadata = {
        "version": "1.0",
        "created_at": datetime.now().isoformat(),
        "indexed_files": indexed_count,
        "repository": "code-index-mcp",
        "description": "MCP index for Code-Index-MCP repository"
    }
    
    with open(index_dir / ".index_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)
    
    # Test search
    cursor.execute(
        """SELECT filepath, snippet(bm25_content, 3, '<mark>', '</mark>', '...', 20) as snippet
           FROM bm25_content 
           WHERE bm25_content MATCH 'dispatcher'
           LIMIT 5"""
    )
    results = cursor.fetchall()
    
    print(f"\n✅ Index created successfully!")
    print(f"   Total files indexed: {indexed_count}")
    print(f"   Test search for 'dispatcher': {len(results)} results")
    if results:
        print(f"   Example: {results[0][0]}")
    
    conn.close()
    
    print(f"\n💡 To use this index:")
    print(f"   1. The MCP server will automatically detect it")
    print(f"   2. Or set DATABASE_URL=sqlite:///.mcp-index/code_index.db")


if __name__ == "__main__":
    create_repo_index()