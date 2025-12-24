#!/usr/bin/env python3
"""
Create MCP-compatible indexes for test repositories
"""

import os
import sys
import sqlite3
from pathlib import Path
import time
import hashlib
from datetime import datetime
from mcp_server.core.path_utils import PathUtils

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.indexer.bm25_indexer import BM25Indexer


def create_mcp_index(repo_path: str, index_name: str):
    """Create an MCP-compatible index for a repository."""
    # Create index directory
    index_dir = Path(".mcp-index") / index_name
    index_dir.mkdir(parents=True, exist_ok=True)
    
    db_path = index_dir / "code_index.db"
    
    print(f"\n📦 Creating MCP index for {index_name}...")
    print(f"   Repository: {repo_path}")
    print(f"   Database: {db_path}")
    
    # Initialize storage
    storage = SQLiteStore(str(db_path))
    
    # Initialize BM25 indexer
    bm25_indexer = BM25Indexer(storage)
    
    # Get all code files
    code_extensions = ['.py', '.js', '.java', '.go', '.rs', '.cpp', '.c', '.rb', '.php', '.swift', '.kt', '.ts', '.jsx', '.tsx']
    indexed_count = 0
    
    repo_path_obj = Path(repo_path)
    
    for ext in code_extensions:
        for file_path in repo_path_obj.rglob(f"*{ext}"):
            # Skip hidden directories and common excludes
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
                
                # Create repository if needed
                repo = storage.get_repository(str(repo_path_obj))
                if not repo:
                    repo_id = storage.create_repository(str(repo_path_obj), index_name)
                else:
                    repo_id = repo['id']
                
                # Store file
                file_id = storage.store_file(
                    repo_id,
                    str(file_path),
                    language=ext[1:],
                    size=len(content),
                    metadata={
                        'last_modified': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                    }
                )
                
                # Index with BM25
                bm25_indexer.add_document(
                    str(rel_path),
                    content,
                    {
                        'language': ext[1:],
                        'file_id': file_id
                    }
                )
                
                indexed_count += 1
                
                if indexed_count % 100 == 0:
                    print(f"   Indexed {indexed_count} files...")
                    
            except Exception as e:
                print(f"   Warning: Failed to index {file_path}: {e}")
                continue
    
    # Get statistics
    stats = bm25_indexer.get_statistics()
    
    print(f"✅ Index created successfully!")
    print(f"   Total files indexed: {indexed_count}")
    print(f"   Index statistics: {stats}")
    
    return db_path, indexed_count


def test_mcp_search(db_path: str, query: str):
    """Test search on the created index."""
    storage = SQLiteStore(str(db_path))
    bm25_indexer = BM25Indexer(storage)
    
    results = bm25_indexer.search(query, limit=5)
    return results


def main():
    """Create MCP indexes for test repositories."""
    
    # Test repositories to index
    test_repos = [
        {
            'path': 'PathUtils.get_workspace_root()/test_repos/web/javascript/react',
            'name': 'react'
        },
        {
            'path': 'PathUtils.get_workspace_root()/test_repos/modern/go/gin',
            'name': 'gin'
        },
        {
            'path': 'PathUtils.get_workspace_root()/test_repos/systems/c/redis',
            'name': 'redis'
        },
        {
            'path': 'PathUtils.get_workspace_root()/test_repos/web/python/django',
            'name': 'django'
        },
        {
            'path': 'PathUtils.get_workspace_root()/test_repos/systems/rust/tokio',
            'name': 'tokio'
        }
    ]
    
    created_indexes = []
    
    for repo in test_repos:
        if Path(repo['path']).exists():
            db_path, count = create_mcp_index(repo['path'], repo['name'])
            created_indexes.append({
                'name': repo['name'],
                'db_path': str(db_path),
                'file_count': count
            })
            
            # Test the index
            print(f"\n🔍 Testing search on {repo['name']} index...")
            test_queries = ['function', 'error', 'TODO']
            
            for query in test_queries:
                results = test_mcp_search(db_path, query)
                print(f"   Query '{query}': {len(results)} results")
                if results:
                    print(f"     Example: {results[0]['filepath']}")
        else:
            print(f"\n❌ Repository not found: {repo['path']}")
    
    # Save index information
    import json
    with open('.mcp-index/index_info.json', 'w') as f:
        json.dump({
            'created_at': datetime.now().isoformat(),
            'indexes': created_indexes
        }, f, indent=2)
    
    print(f"\n✅ Created {len(created_indexes)} MCP-compatible indexes")
    print(f"💾 Index information saved to .mcp-index/index_info.json")


if __name__ == "__main__":
    main()