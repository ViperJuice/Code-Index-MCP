#!/usr/bin/env python3
"""Check the created index database."""

import sqlite3
from pathlib import Path

db_path = Path(__file__).parent / "code_index.db"

if db_path.exists():
    print(f"✅ Database exists: {db_path}")
    print(f"📊 Size: {db_path.stat().st_size / 1024 / 1024:.2f} MB")
    
    # Connect to database
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Get table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f"\n📋 Tables: {[t[0] for t in tables]}")
    
    # Count files
    try:
        cursor.execute("SELECT COUNT(*) FROM files;")
        file_count = cursor.fetchone()[0]
        print(f"\n📁 Files indexed: {file_count}")
        
        # Sample some files
        cursor.execute("SELECT file_path FROM files LIMIT 10;")
        sample_files = cursor.fetchall()
        print("\n📄 Sample files:")
        for f in sample_files:
            print(f"  • {f[0]}")
    except Exception as e:
        print(f"Error querying files: {e}")
    
    # Count symbols
    try:
        cursor.execute("SELECT COUNT(*) FROM symbols;")
        symbol_count = cursor.fetchone()[0]
        print(f"\n🔤 Symbols indexed: {symbol_count}")
        
        # Sample some symbols
        cursor.execute("SELECT name, kind, file_path FROM symbols LIMIT 10;")
        sample_symbols = cursor.fetchall()
        print("\n🔍 Sample symbols:")
        for s in sample_symbols:
            print(f"  • {s[0]} ({s[1]}) in {Path(s[2]).name}")
    except Exception as e:
        print(f"Error querying symbols: {e}")
    
    conn.close()
else:
    print(f"❌ Database not found: {db_path}")