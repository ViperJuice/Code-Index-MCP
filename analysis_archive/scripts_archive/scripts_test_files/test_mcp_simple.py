#!/usr/bin/env python3
"""
Simple test of MCP server BM25 functionality.
"""

import sqlite3
from pathlib import Path

# Test the BM25 index directly
index_path = Path.home() / ".mcp/indexes/f7b49f5d0ae0/main_f48abb0.db"

print("Testing BM25 Index Directly")
print("=" * 80)
print(f"Index path: {index_path}")
print(f"Index exists: {index_path.exists()}")

if index_path.exists():
    conn = sqlite3.connect(str(index_path))
    cursor = conn.cursor()
    
    # Check BM25 table
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bm25_content'")
    if cursor.fetchone():
        print("\n✓ BM25 table found!")
        
        # Get row count
        cursor.execute("SELECT COUNT(*) FROM bm25_content")
        count = cursor.fetchone()[0]
        print(f"  Total indexed files: {count}")
        
        # Test queries
        print("\nTesting BM25 searches:")
        
        test_queries = [
            "BM25Indexer",
            "class SQLiteStore",
            "def search",
            "reranking"
        ]
        
        for query in test_queries:
            cursor.execute("""
                SELECT 
                    filepath,
                    snippet(bm25_content, -1, '<<', '>>', '...', 20) as snippet,
                    language
                FROM bm25_content
                WHERE bm25_content MATCH ?
                ORDER BY rank
                LIMIT 3
            """, (query,))
            
            results = cursor.fetchall()
            print(f"\n  Query '{query}': {len(results)} results")
            for i, (filepath, snippet, language) in enumerate(results):
                print(f"    {i+1}. {filepath}")
                print(f"       Language: {language}")
                print(f"       Snippet: {snippet[:80]}...")
    else:
        print("\n✗ BM25 table not found!")
    
    conn.close()
else:
    print("\n✗ Index file not found!")

print("\n" + "=" * 80)