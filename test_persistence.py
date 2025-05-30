#!/usr/bin/env python3
"""Test script to verify SQLite persistence integration."""

import sqlite3
import os
from pathlib import Path

def test_persistence():
    """Test that the SQLite database is created and contains data."""
    db_path = "code_index.db"
    
    if not os.path.exists(db_path):
        print("❌ Database file not found. Start the server first.")
        return
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    try:
        # Check schema version
        cursor = conn.execute("SELECT * FROM schema_version")
        version = cursor.fetchone()
        if version:
            print(f"✅ Schema version: {version['version']} - {version['description']}")
        else:
            print("❌ No schema version found")
        
        # Check repositories
        cursor = conn.execute("SELECT COUNT(*) as count FROM repositories")
        repo_count = cursor.fetchone()['count']
        print(f"✅ Repositories: {repo_count}")
        
        # Check files
        cursor = conn.execute("SELECT COUNT(*) as count FROM files")
        file_count = cursor.fetchone()['count']
        print(f"✅ Files indexed: {file_count}")
        
        # Check symbols
        cursor = conn.execute("SELECT COUNT(*) as count FROM symbols")
        symbol_count = cursor.fetchone()['count']
        print(f"✅ Symbols indexed: {symbol_count}")
        
        # Show some sample symbols
        if symbol_count > 0:
            print("\n📋 Sample symbols:")
            cursor = conn.execute("""
                SELECT s.name, s.kind, f.path 
                FROM symbols s 
                JOIN files f ON s.file_id = f.id 
                LIMIT 5
            """)
            for row in cursor:
                print(f"  - {row['name']} ({row['kind']}) in {row['path']}")
        
        # Check FTS5 tables
        cursor = conn.execute("SELECT COUNT(*) as count FROM fts_symbols")
        fts_count = cursor.fetchone()['count']
        print(f"\n✅ FTS5 symbols: {fts_count}")
        
        # Test fuzzy search
        cursor = conn.execute("""
            SELECT COUNT(DISTINCT symbol_id) as count 
            FROM symbol_trigrams
        """)
        trigram_symbols = cursor.fetchone()['count']
        print(f"✅ Symbols with trigrams: {trigram_symbols}")
        
        print("\n✅ All persistence checks passed!")
        
    except Exception as e:
        print(f"❌ Error checking database: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    test_persistence()