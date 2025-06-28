#\!/usr/bin/env python3
"""
Helper script to test MCP tools via subprocess.
"""

import json
import sys
import argparse
import sqlite3
from pathlib import Path


def test_symbol_lookup(symbol: str) -> dict:
    """Test symbol lookup using BM25 index."""
    index_path = Path.home() / ".mcp/indexes/f7b49f5d0ae0/main_f48abb0.db"
    
    if not index_path.exists():
        return {"error": "Index not found"}
    
    conn = sqlite3.connect(str(index_path))
    cursor = conn.cursor()
    
    # Search for symbol patterns
    patterns = [
        f"class {symbol}",
        f"def {symbol}",
        f"function {symbol}",
        f"interface {symbol}",
        f"type {symbol}"
    ]
    
    for pattern in patterns:
        cursor.execute("""
            SELECT filepath, snippet(bm25_content, -1, '', '', '...', 20), language
            FROM bm25_content
            WHERE bm25_content MATCH ?
            ORDER BY rank
            LIMIT 1
        """, (pattern,))
        
        row = cursor.fetchone()
        if row:
            filepath, snippet, language = row
            
            # Determine kind from snippet
            snippet_lower = snippet.lower()
            kind = 'symbol'
            if 'class' in snippet_lower:
                kind = 'class'
            elif 'def' in snippet_lower or 'function' in snippet_lower:
                kind = 'function'
            
            conn.close()
            return {
                'symbol': symbol,
                'kind': kind,
                'language': language or 'unknown',
                'defined_in': filepath,
                'line': 1,  # Would need to parse for actual line
                'signature': snippet,
                'doc': ''
            }
    
    conn.close()
    return {"error": f"Symbol '{symbol}' not found"}


def test_search_code(query: str, limit: int = 10) -> list:
    """Test code search using BM25 index."""
    index_path = Path.home() / ".mcp/indexes/f7b49f5d0ae0/main_f48abb0.db"
    
    if not index_path.exists():
        return []
    
    conn = sqlite3.connect(str(index_path))
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            filepath,
            snippet(bm25_content, -1, '<<', '>>', '...', 20) as snippet,
            language,
            rank
        FROM bm25_content
        WHERE bm25_content MATCH ?
        ORDER BY rank
        LIMIT ?
    """, (query, limit))
    
    results = []
    for row in cursor.fetchall():
        filepath, snippet, language, rank = row
        results.append({
            'file': filepath,
            'line': 1,  # Would need to parse for actual line
            'snippet': snippet,
            'score': abs(rank),
            'language': language or 'unknown'
        })
    
    conn.close()
    return results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Test MCP tools')
    parser.add_argument('--tool', required=True, choices=['symbol_lookup', 'search_code'])
    parser.add_argument('--symbol', help='Symbol to look up')
    parser.add_argument('--query', help='Search query')
    parser.add_argument('--limit', type=int, default=10, help='Result limit')
    
    args = parser.parse_args()
    
    if args.tool == 'symbol_lookup':
        if not args.symbol:
            print(json.dumps({"error": "Symbol required for lookup"}))
            sys.exit(1)
        result = test_symbol_lookup(args.symbol)
        print(json.dumps(result))
    
    elif args.tool == 'search_code':
        if not args.query:
            print(json.dumps({"error": "Query required for search"}))
            sys.exit(1)
        results = test_search_code(args.query, args.limit)
        print(json.dumps(results))


if __name__ == "__main__":
    main()
