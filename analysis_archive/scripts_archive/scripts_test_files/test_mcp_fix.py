#!/usr/bin/env python3
"""
Test fix for MCP empty responses.
"""

import sqlite3
from pathlib import Path
import json


def search_bm25_directly(query: str, limit: int = 20):
    """Search BM25 index directly."""
    db_path = Path.home() / ".mcp" / "indexes" / "f7b49f5d0ae0" / "main_f48abb0.db"
    
    if not db_path.exists():
        return []
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # Search using FTS5
        cursor.execute("""
            SELECT 
                filepath,
                filename,
                snippet(bm25_content, -1, '<<', '>>', '...', 20) as snippet,
                rank
            FROM bm25_content
            WHERE bm25_content MATCH ?
            ORDER BY rank
            LIMIT ?
        """, (query, limit))
        
        results = []
        for row in cursor.fetchall():
            filepath, filename, snippet, rank = row
            
            # Try to extract line number from content
            # This is a simplified approach
            line_num = 1  # Default
            
            results.append({
                'file': filepath,
                'filename': filename,
                'line': line_num,
                'snippet': snippet,
                'score': abs(rank)  # rank is negative in FTS5
            })
        
        return results
        
    finally:
        conn.close()


def lookup_symbol_directly(symbol: str):
    """Lookup symbol in BM25 index."""
    # Search for symbol definitions
    results = search_bm25_directly(f'class {symbol} OR def {symbol} OR function {symbol}', limit=10)
    
    if results:
        # Return the best match
        best = results[0]
        return {
            'symbol': symbol,
            'kind': 'class' if 'class' in best['snippet'] else 'function',
            'language': 'python',  # Would need to detect from file extension
            'defined_in': best['file'],
            'line': best['line'],
            'signature': best['snippet']
        }
    
    return None


def test_direct_search():
    """Test direct BM25 search."""
    print("Testing Direct BM25 Search")
    print("=" * 60)
    
    test_queries = [
        "BM25Indexer",
        "centralized storage",
        "reranking",
        "IndexManager"
    ]
    
    for query in test_queries:
        print(f"\nSearching for: '{query}'")
        results = search_bm25_directly(query, limit=3)
        
        if results:
            print(f"Found {len(results)} results:")
            for r in results:
                print(f"  - {r['file']}:{r['line']}")
                print(f"    {r['snippet']}")
        else:
            print("  No results found")
    
    # Test symbol lookup
    print("\n\nTesting Symbol Lookup")
    print("-" * 40)
    
    symbols = ["BM25Indexer", "SQLiteStore", "IndexManager"]
    
    for symbol in symbols:
        print(f"\nLooking up: '{symbol}'")
        result = lookup_symbol_directly(symbol)
        
        if result:
            print(f"  Found in: {result['defined_in']}")
            print(f"  Kind: {result['kind']}")
            print(f"  Signature: {result['signature'][:100]}...")
        else:
            print("  Not found")


if __name__ == "__main__":
    test_direct_search()