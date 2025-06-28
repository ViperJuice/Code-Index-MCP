#!/usr/bin/env python3
"""
Test searching the BM25 index directly.
"""

import sqlite3
from pathlib import Path

def test_search():
    index_path = Path.home() / ".mcp" / "indexes" / "f7b49f5d0ae0" / "main_f48abb0.db"
    conn = sqlite3.connect(str(index_path))
    cursor = conn.cursor()
    
    # Test queries
    queries = [
        "IndexManager",
        "BM25Indexer", 
        "centralized storage",
        "reranking"
    ]
    
    for query in queries:
        print(f"\nSearching for: '{query}'")
        print("-" * 40)
        
        try:
            # Search using FTS5 MATCH
            cursor.execute("""
                SELECT filepath, filename, snippet(bm25_content, -1, '<<', '>>', '...', 10)
                FROM bm25_content
                WHERE bm25_content MATCH ?
                LIMIT 5
            """, (query,))
            
            results = cursor.fetchall()
            print(f"Found {len(results)} results:")
            
            for filepath, filename, snippet in results:
                print(f"\n  {filepath}")
                print(f"  Snippet: {snippet}")
                
        except Exception as e:
            print(f"  Error: {e}")
    
    # Test getting file content
    print("\n\nTesting file retrieval:")
    print("-" * 40)
    
    cursor.execute("""
        SELECT filepath, substr(content, 1, 200)
        FROM bm25_content
        WHERE filepath LIKE '%index_manager%'
        LIMIT 1
    """)
    
    result = cursor.fetchone()
    if result:
        filepath, content = result
        print(f"File: {filepath}")
        print(f"Content preview: {content}...")
    
    conn.close()

if __name__ == "__main__":
    print("BM25 Search Test")
    print("=" * 60)
    test_search()