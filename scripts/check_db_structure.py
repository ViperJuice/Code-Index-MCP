#!/usr/bin/env python3
"""Check database structure for symbols table"""

import sqlite3
from pathlib import Path

db_path = Path("/workspaces/Code-Index-MCP/.indexes/844145265d7a/code_index.db")

if db_path.exists():
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Check if symbols table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='symbols'")
    if cursor.fetchone():
        print("Symbols table exists!")
        
        # Get table schema
        cursor.execute("PRAGMA table_info(symbols)")
        columns = cursor.fetchall()
        
        print("\nSymbols table columns:")
        for col in columns:
            print(f"  {col[1]} ({col[2]})")
            
        # Try a sample query
        print("\nSample query test:")
        try:
            cursor.execute("SELECT * FROM symbols LIMIT 1")
            result = cursor.fetchone()
            if result:
                print(f"  Found {len(result)} columns in result")
                for i, col in enumerate(columns):
                    print(f"  {col[1]}: {result[i]}")
        except Exception as e:
            print(f"  Query error: {e}")
    else:
        print("Symbols table does NOT exist!")
        
        # List all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print("\nAvailable tables:")
        for table in tables:
            print(f"  - {table[0]}")
    
    conn.close()
else:
    print(f"Database not found at {db_path}")
    
    # Look for other databases
    indexes_dir = Path("/workspaces/Code-Index-MCP/.indexes")
    if indexes_dir.exists():
        print("\nAvailable databases:")
        for db_dir in indexes_dir.iterdir():
            db_file = db_dir / "code_index.db"
            if db_file.exists():
                print(f"  - {db_file}")