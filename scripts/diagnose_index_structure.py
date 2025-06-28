#!/usr/bin/env python3
"""
Diagnose the actual structure of the index databases.
"""

import sys
import sqlite3
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from mcp_server.core.path_utils import PathUtils

def diagnose_structure():
    """Diagnose index database structure."""
    index_path = PathUtils.get_index_storage_path()
    db_file = list(index_path.glob("*/code_index.db"))[0]  # First DB
    
    print(f"Examining: {db_file}")
    
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    print("\nDatabase Tables and Structure:")
    print("="*60)
    
    for (table_name,) in tables:
        print(f"\n[Table: {table_name}]")
        
        # Get schema
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        for col in columns:
            print(f"  {col[1]} {col[2]}")
        
        # Get row count
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"  Rows: {count}")
            
            # Sample data for key tables
            if table_name in ['bm25_content', 'files'] and count > 0:
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 2")
                rows = cursor.fetchall()
                print(f"  Sample data:")
                for row in rows:
                    print(f"    {row}")
        except Exception as e:
            print(f"  Error reading table: {e}")
    
    # Check for the actual content storage
    print("\n\nChecking BM25 content storage:")
    print("="*60)
    
    # The bm25_content table is the FTS5 table
    cursor.execute("SELECT sql FROM sqlite_master WHERE name='bm25_content'")
    create_sql = cursor.fetchone()
    if create_sql:
        print(f"BM25 table definition: {create_sql[0]}")
    
    # Try to search
    print("\nTrying BM25 search:")
    try:
        cursor.execute("SELECT file_path, content FROM bm25_content WHERE bm25_content MATCH 'def' LIMIT 3")
        results = cursor.fetchall()
        print(f"Found {len(results)} results")
        for path, content in results:
            print(f"  {path}: {content[:50]}...")
    except Exception as e:
        print(f"Search error: {e}")
    
    conn.close()

if __name__ == "__main__":
    diagnose_structure()