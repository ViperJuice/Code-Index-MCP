#!/usr/bin/env python3
"""Check if PathUtils is in the index."""

import sqlite3
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Check new index
new_index = Path(".indexes/844145265d7a/code_index.db")
if new_index.exists():
    conn = sqlite3.connect(str(new_index))
    cursor = conn.cursor()
    
    # Check files
    cursor.execute("""
        SELECT path, relative_path 
        FROM files 
        WHERE path LIKE '%path_utils.py%' 
        OR relative_path LIKE '%path_utils.py%'
    """)
    files = cursor.fetchall()
    print(f"Files containing path_utils.py: {len(files)}")
    for f in files[:3]:
        print(f"  - {f[0]}")
    
    # Check BM25 content
    cursor.execute("""
        SELECT filepath, content 
        FROM bm25_content 
        WHERE filepath LIKE '%path_utils.py%'
        LIMIT 1
    """)
    bm25 = cursor.fetchone()
    if bm25:
        print(f"\nBM25 content found for: {bm25[0]}")
        print(f"Content preview: {bm25[1][:200]}...")
    
    # Check for PathUtils class
    cursor.execute("""
        SELECT filepath 
        FROM bm25_content 
        WHERE content LIKE '%class PathUtils%'
        LIMIT 5
    """)
    pathutils_class = cursor.fetchall()
    print(f"\nFiles with 'class PathUtils': {len(pathutils_class)}")
    for f in pathutils_class:
        print(f"  - {f[0]}")
    
    conn.close()

# Check source index
source_index = Path(".indexes/f7b49f5d0ae0/new_index.db")
if source_index.exists():
    print("\n--- SOURCE INDEX ---")
    conn = sqlite3.connect(str(source_index))
    cursor = conn.cursor()
    
    # Check for path_utils.py
    cursor.execute("""
        SELECT filepath 
        FROM bm25_content 
        WHERE filepath LIKE '%path_utils.py%'
        LIMIT 5
    """)
    files = cursor.fetchall()
    print(f"Files containing path_utils.py: {len(files)}")
    for f in files[:3]:
        print(f"  - {f[0]}")
    
    conn.close()