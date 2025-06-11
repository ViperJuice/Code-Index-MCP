#!/usr/bin/env python3
"""
Demo script showing how to populate and use the BM25 index.
"""

import subprocess
import sys
from pathlib import Path
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.indexer.bm25_indexer import BM25Indexer


def run_indexing():
    """Run the BM25 population script."""
    print("=== Populating BM25 Index ===")
    
    # Run with verbose output and small batch size for demo
    cmd = [
        sys.executable,
        "scripts/populate_bm25_index.py",
        "--verbose",
        "--batch-size", "10",
        "--workers", "2"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("Indexing completed successfully!")
        print("\nOutput:")
        print(result.stdout)
    else:
        print("Indexing failed!")
        print("\nError:")
        print(result.stderr)
        return False
        
    return True


def demo_search():
    """Demonstrate searching the BM25 index."""
    print("\n=== BM25 Search Demo ===")
    
    # Initialize storage and indexer
    storage = SQLiteStore("code_index.db")
    indexer = BM25Indexer(storage)
    
    # Get statistics
    stats = indexer.get_statistics()
    print(f"\nIndex Statistics:")
    print(f"  Total documents: {stats['total_documents']}")
    print(f"  Total symbols: {stats['total_symbols']}")
    print(f"  Languages: {list(stats['language_distribution'].keys())}")
    
    # Demo searches
    queries = [
        ("class", "Search for class definitions"),
        ("def search", "Search for search functions"),
        ("import sqlite3", "Search for sqlite imports"),
        ("TODO", "Search for TODO comments")
    ]
    
    for query, description in queries:
        print(f"\n{description}: '{query}'")
        results = indexer.search(query, limit=3)
        
        if results:
            for i, result in enumerate(results, 1):
                print(f"\n  Result {i}:")
                print(f"    File: {result['filepath']}")
                print(f"    Score: {result['score']:.2f}")
                print(f"    Snippet: {result['snippet']}")
        else:
            print("  No results found")
    
    # Demo symbol search
    print("\n=== Symbol Search ===")
    symbol_results = indexer.search("indexer", limit=3, search_type='symbols')
    
    if symbol_results:
        for i, result in enumerate(symbol_results, 1):
            print(f"\n  Symbol {i}:")
            print(f"    Name: {result['name']}")
            print(f"    Kind: {result['kind']}")
            print(f"    File: {result['filepath']}")
            print(f"    Score: {result['score']:.2f}")
    
    # Demo phrase search
    print("\n=== Phrase Search ===")
    phrase_results = indexer.search_phrase("bm25 index", limit=3)
    
    if phrase_results:
        print(f"Found {len(phrase_results)} results for exact phrase 'bm25 index'")
        for result in phrase_results[:2]:
            print(f"  - {result['filepath']} (score: {result['score']:.2f})")


def main():
    """Run the demo."""
    print("BM25 Index Population Demo")
    print("=" * 50)
    
    # Check if database exists
    if not Path("code_index.db").exists():
        print("Error: code_index.db not found!")
        print("Please run indexing first to create the database.")
        return 1
    
    # Run indexing
    if run_indexing():
        # Demo search capabilities
        demo_search()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())