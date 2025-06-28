#!/usr/bin/env python3
"""
Create a simple MCP-compatible index directly
"""

import os
import sys
import sqlite3
from pathlib import Path
import hashlib
from datetime import datetime
import json

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def create_simple_mcp_index(repo_path: str, index_name: str):
    """Create a simple MCP index using direct SQLite."""
    # Create index directory
    index_dir = Path(".mcp-index") / index_name
    index_dir.mkdir(parents=True, exist_ok=True)
    
    db_path = index_dir / "code_index.db"
    
    print(f"\n📦 Creating simple MCP index for {index_name}...")
    print(f"   Repository: {repo_path}")
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
        (repo_path, index_name)
    )
    repo_id = cursor.lastrowid
    
    # Index files
    repo_path_obj = Path(repo_path)
    code_extensions = ['.py', '.js', '.java', '.go', '.rs', '.cpp', '.c', '.rb', '.php', '.swift', '.kt', '.ts', '.jsx', '.tsx']
    indexed_count = 0
    
    for ext in code_extensions:
        for file_path in repo_path_obj.rglob(f"*{ext}"):
            # Skip hidden and excluded directories
            if any(part.startswith('.') for part in file_path.parts):
                continue
            if any(exclude in str(file_path) for exclude in ['node_modules', '__pycache__', 'venv', '.git']):
                continue
            
            try:
                # Read file content
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Get relative path
                rel_path = file_path.relative_to(repo_path_obj)
                
                # Calculate content hash
                content_hash = hashlib.md5(content.encode()).hexdigest()
                
                # Insert file record
                cursor.execute(
                    """INSERT OR REPLACE INTO files 
                       (repository_id, path, relative_path, language, size, content_hash)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (repo_id, str(file_path), str(rel_path), ext[1:], len(content), content_hash)
                )
                file_id = cursor.lastrowid
                
                # Index in BM25
                cursor.execute(
                    """INSERT INTO bm25_content 
                       (file_id, filepath, filename, content, language)
                       VALUES (?, ?, ?, ?, ?)""",
                    (file_id, str(rel_path), file_path.name, content, ext[1:])
                )
                
                # Update index status
                cursor.execute(
                    """INSERT OR REPLACE INTO bm25_index_status 
                       (file_id, filepath, content_hash)
                       VALUES (?, ?, ?)""",
                    (file_id, str(rel_path), content_hash)
                )
                
                indexed_count += 1
                if indexed_count % 100 == 0:
                    print(f"   Indexed {indexed_count} files...")
                    conn.commit()
                    
            except Exception as e:
                print(f"   Warning: Failed to index {file_path}: {e}")
                continue
    
    conn.commit()
    
    # Get statistics
    cursor.execute("SELECT COUNT(*) FROM bm25_content")
    total_indexed = cursor.fetchone()[0]
    
    print(f"✅ Index created successfully!")
    print(f"   Total files indexed: {total_indexed}")
    
    # Test search
    cursor.execute(
        """SELECT filepath, snippet(bm25_content, 3, '<mark>', '</mark>', '...', 32) as snippet
           FROM bm25_content 
           WHERE bm25_content MATCH 'function'
           LIMIT 5"""
    )
    results = cursor.fetchall()
    print(f"   Test search for 'function': {len(results)} results")
    
    conn.close()
    return db_path, indexed_count


def main():
    """Create simple MCP indexes for test repositories."""
    test_repos = [
        {
            'path': '/workspaces/Code-Index-MCP/test_repos/web/javascript/react',
            'name': 'react'
        },
        {
            'path': '/workspaces/Code-Index-MCP/test_repos/modern/go/gin',
            'name': 'gin'
        },
        {
            'path': '/workspaces/Code-Index-MCP/test_repos/systems/c/redis',
            'name': 'redis'
        }
    ]
    
    created_indexes = []
    
    for repo in test_repos[:3]:  # Just do 3 for now
        if Path(repo['path']).exists():
            db_path, count = create_simple_mcp_index(repo['path'], repo['name'])
            created_indexes.append({
                'name': repo['name'],
                'db_path': str(db_path),
                'file_count': count
            })
        else:
            print(f"\n❌ Repository not found: {repo['path']}")
    
    # Save index information
    with open('.mcp-index/index_info.json', 'w') as f:
        json.dump({
            'created_at': datetime.now().isoformat(),
            'indexes': created_indexes
        }, f, indent=2)
    
    print(f"\n✅ Created {len(created_indexes)} simple MCP indexes")
    print(f"💾 Index information saved to .mcp-index/index_info.json")


if __name__ == "__main__":
    main()