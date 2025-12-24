#!/usr/bin/env python3
"""
Test BM25 search directly on the database.
"""

import sys
import sqlite3
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from mcp_server.core.path_utils import PathUtils

def test_bm25_search():
    """Test BM25 search directly."""
    index_path = PathUtils.get_index_storage_path()
    db_file = list(index_path.glob("*/code_index.db"))[0]
    
    print(f"Testing BM25 search on: {db_file}")
    
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    # Test queries
    queries = ["def", "class", "import", "function", "Django"]
    
    for query in queries:
        print(f"\n[Searching for: {query}]")
        
        try:
            # Use correct column names
            cursor.execute("""
                SELECT filepath, filename, content, language 
                FROM bm25_content 
                WHERE bm25_content MATCH ? 
                LIMIT 5
            """, (query,))
            
            results = cursor.fetchall()
            print(f"Found {len(results)} results")
            
            for filepath, filename, content, language in results:
                print(f"\n  File: {filepath}")
                print(f"  Language: {language}")
                print(f"  Content preview: {content[:100]}...")
                
        except Exception as e:
            print(f"Error: {e}")
    
    # Check why MCP might be failing
    print("\n\n[Checking MCP compatibility]")
    
    # Check if SQLiteStore expects different table structure
    print("\nChecking for 'code_blocks' table (expected by SQLiteStore):")
    cursor.execute("SELECT name FROM sqlite_master WHERE name='code_blocks'")
    if cursor.fetchone():
        print("✓ code_blocks table exists")
    else:
        print("✗ code_blocks table NOT found - this is why MCP searches fail!")
        print("  The database uses 'bm25_content' table instead")
    
    conn.close()
    
    # Now check the current repository index
    print("\n\n[Checking current repository index]")
    current_db = index_path / "current" / "code_index.db"
    if not current_db.exists():
        # Try to find it by checking for this repo's files
        print("Looking for current repository index...")
        for db_path in index_path.glob("*/code_index.db"):
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT filepath FROM bm25_content WHERE filepath LIKE '%path_utils.py%' LIMIT 1")
            if cursor.fetchone():
                print(f"Found current repo index at: {db_path}")
                current_db = db_path
                break
            conn.close()
    
    if current_db.exists():
        print(f"Testing current repo: {current_db}")
        conn = sqlite3.connect(current_db)
        cursor = conn.cursor()
        
        # Search for PathUtils
        cursor.execute("""
            SELECT filepath, content 
            FROM bm25_content 
            WHERE bm25_content MATCH 'PathUtils' 
            LIMIT 3
        """, ())
        
        results = cursor.fetchall()
        print(f"\nSearching for 'PathUtils': Found {len(results)} results")
        for filepath, content in results:
            print(f"  {filepath}")
        
        conn.close()

if __name__ == "__main__":
    test_bm25_search()