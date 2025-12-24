#!/usr/bin/env python3
"""Check languages in a test index."""

import sys
import sqlite3
from pathlib import Path

# Check first test index
test_db = Path(".indexes/056d6d37b1aa/current.db")

if not test_db.exists():
    print(f"Database not found: {test_db}")
    sys.exit(1)

conn = sqlite3.connect(str(test_db))
cursor = conn.cursor()

print(f"\nChecking languages in: {test_db}")
print("="*60)

# Check if files table exists
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall()]
print(f"Tables: {tables}")

if 'files' in tables:
    # Get language stats
    cursor.execute("""
        SELECT language, COUNT(*) as count 
        FROM files 
        WHERE language IS NOT NULL 
        GROUP BY language 
        ORDER BY count DESC
        LIMIT 20
    """)
    
    results = cursor.fetchall()
    if results:
        print("\nLanguages found:")
        for lang, count in results:
            print(f"  {lang}: {count} files")
    else:
        print("\nNo languages found in files table")
        
    # Check total files
    cursor.execute("SELECT COUNT(*) FROM files")
    total = cursor.fetchone()[0]
    print(f"\nTotal files: {total}")
    
    # Check sample files
    cursor.execute("SELECT path, language FROM files LIMIT 5")
    print("\nSample files:")
    for path, lang in cursor.fetchall():
        print(f"  {path} -> {lang}")

else:
    print("No 'files' table found")

conn.close()