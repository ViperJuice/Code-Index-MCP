#!/usr/bin/env python3
"""
Simple BM25 indexing for test repositories
"""

import os
import sys
import sqlite3
from pathlib import Path
from datetime import datetime
import hashlib

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def create_simple_index(repo_path, db_path):
    """Create a simple BM25 index directly."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create simple BM25 FTS table
    cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS bm25_simple USING fts5(
            filepath,
            content,
            tokenize = 'porter unicode61'
        )
    """)
    
    # Get all code files
    code_files = []
    extensions = ['.py', '.js', '.java', '.go', '.rs', '.cpp', '.c', '.rb', '.php', '.swift', '.kt', '.ts', '.jsx', '.tsx']
    
    for ext in extensions:
        code_files.extend(Path(repo_path).rglob(f"*{ext}"))
    
    # Index files
    indexed = 0
    for file_path in code_files[:500]:  # Limit to 500 files
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            rel_path = file_path.relative_to(repo_path)
            
            cursor.execute(
                "INSERT INTO bm25_simple (filepath, content) VALUES (?, ?)",
                (str(rel_path), content)
            )
            indexed += 1
            
        except Exception as e:
            pass
    
    conn.commit()
    conn.close()
    
    return indexed


def main():
    """Index a few test repositories."""
    test_repos = [
        "/workspaces/Code-Index-MCP/test_repos/web/javascript/react",
        "/workspaces/Code-Index-MCP/test_repos/systems/c/redis", 
        "/workspaces/Code-Index-MCP/test_repos/modern/go/gin",
        "/workspaces/Code-Index-MCP/test_repos/web/python/django",
        "/workspaces/Code-Index-MCP/test_repos/systems/rust/tokio"
    ]
    
    for repo_path in test_repos:
        if not Path(repo_path).exists():
            print(f"Skipping {repo_path} - not found")
            continue
            
        repo_name = f"{Path(repo_path).parent.name}_{Path(repo_path).name}"
        db_path = f"/workspaces/Code-Index-MCP/test_indexes/{repo_name}/simple_bm25.db"
        
        # Create directory
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        print(f"Indexing {repo_name}...")
        count = create_simple_index(repo_path, db_path)
        print(f"  Indexed {count} files")
        
        # Test search
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT filepath FROM bm25_simple WHERE bm25_simple MATCH 'TODO' LIMIT 5"
        )
        results = cursor.fetchall()
        print(f"  Test search found {len(results)} TODO matches")
        
        conn.close()


if __name__ == "__main__":
    main()