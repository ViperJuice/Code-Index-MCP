#!/usr/bin/env python3
"""
Check the schema of the existing index database.
"""

import sqlite3
from pathlib import Path

def check_schema():
    # Path to current index
    index_path = Path.home() / ".mcp" / "indexes" / "f7b49f5d0ae0" / "main_f48abb0.db"
    
    print(f"Checking index: {index_path}")
    print("=" * 60)
    
    if not index_path.exists():
        print("Index file not found!")
        return
    
    conn = sqlite3.connect(str(index_path))
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    print(f"Tables found: {len(tables)}")
    for table in tables:
        table_name = table[0]
        print(f"\n{table_name}:")
        
        # Get table schema
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")
        
        # Get row count
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"  Rows: {count}")
        except:
            print(f"  Rows: Unable to count")
    
    # Check for FTS tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%fts%'")
    fts_tables = cursor.fetchall()
    
    if fts_tables:
        print(f"\nFTS Tables: {[t[0] for t in fts_tables]}")
    
    conn.close()

if __name__ == "__main__":
    check_schema()