#!/usr/bin/env python3
"""
Check the schema of test indexes to understand their structure.
"""

import sqlite3
from pathlib import Path
from mcp_server.core.path_utils import PathUtils


def check_schema(db_path: Path):
    """Check the schema of a database."""
    print(f"\nChecking schema for: {db_path}")
    print("-" * 60)
    
    if not db_path.exists():
        print("Database does not exist!")
        return
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' 
            ORDER BY name
        """)
        tables = cursor.fetchall()
        
        print(f"Tables found: {[t[0] for t in tables]}")
        
        # For each table, get schema
        for table_name in [t[0] for t in tables]:
            print(f"\n{table_name}:")
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            for col in columns:
                print(f"  - {col[1]} ({col[2]})")
        
        # Check specifically for FTS tables
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name LIKE '%fts%'
        """)
        fts_tables = cursor.fetchall()
        
        if fts_tables:
            print(f"\nFTS tables: {[t[0] for t in fts_tables]}")
        
        # If bm25_content exists, show sample data
        if 'bm25_content' in [t[0] for t in tables]:
            print("\nSample from bm25_content:")
            cursor.execute("SELECT * FROM bm25_content LIMIT 1")
            row = cursor.fetchone()
            if row:
                # Get column names
                cursor.execute("PRAGMA table_info(bm25_content)")
                cols = [c[1] for c in cursor.fetchall()]
                print("Columns:", cols)
                print("Sample row:", row)
        
        # Check for documents table
        if 'documents' in [t[0] for t in tables]:
            print("\nSample from documents:")
            cursor.execute("SELECT * FROM documents LIMIT 1")
            row = cursor.fetchone()
            if row:
                cursor.execute("PRAGMA table_info(documents)")
                cols = [c[1] for c in cursor.fetchall()]
                print("Columns:", cols)
                for i, col in enumerate(cols):
                    print(f"  {col}: {row[i]}")
        
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")


def main():
    """Check schemas of test indexes."""
    
    print("Checking Test Index Schemas")
    print("=" * 80)
    
    # Check a few different test indexes
    test_indexes = [
        Path("PathUtils.get_workspace_root()/test_indexes/go_gin/code_index.db"),
        Path("PathUtils.get_workspace_root()/test_indexes/python_django/code_index.db"),
        Path("PathUtils.get_workspace_root()/test_indexes/c_redis/simple_bm25.db"),
        # Check main repo index for comparison
        Path.home() / ".mcp" / "indexes" / "f7b49f5d0ae0" / "current.db"
    ]
    
    for db_path in test_indexes:
        if db_path.exists():
            check_schema(db_path)
        else:
            print(f"\n{db_path} does not exist")


if __name__ == "__main__":
    main()