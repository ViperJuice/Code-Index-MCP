#!/usr/bin/env python3
"""Check index content."""

import sqlite3
from pathlib import Path
from mcp_server.core.path_utils import PathUtils

def check_index(index_path):
    """Check index content."""
    conn = sqlite3.connect(index_path)
    cursor = conn.cursor()
    
    # Check tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f"Tables: {[t[0] for t in tables]}")
    
    # Check files
    cursor.execute("SELECT COUNT(*) FROM files")
    file_count = cursor.fetchone()[0]
    print(f"Files: {file_count}")
    
    # Check BM25 content
    try:
        cursor.execute("SELECT COUNT(*) FROM bm25_content")
        bm25_count = cursor.fetchone()[0]
        print(f"BM25 documents: {bm25_count}")
        
        # Sample BM25 content
        cursor.execute("SELECT content FROM bm25_content LIMIT 1")
        sample = cursor.fetchone()
        if sample:
            print(f"Sample content: {sample[0][:100]}...")
    except:
        print("No BM25 content table")
    
    # Check FTS
    try:
        cursor.execute("SELECT COUNT(*) FROM code_search")
        fts_count = cursor.fetchone()[0]
        print(f"FTS documents: {fts_count}")
    except:
        print("No FTS table")
    
    conn.close()

# Check Django index
print("Django index:")
check_index("PathUtils.get_workspace_root()/.indexes/d8df70cdcd6e/code_index.db")