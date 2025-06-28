#!/usr/bin/env python3
"""
Debug dispatcher lookup and search methods.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, "/workspaces/Code-Index-MCP")

from scripts.cli.mcp_server_cli import initialize_services, dispatcher


async def test_dispatcher():
    """Test dispatcher methods directly."""
    print("Testing Dispatcher Methods")
    print("=" * 60)
    
    # Initialize services
    await initialize_services()
    
    if dispatcher is None:
        print("ERROR: Dispatcher not initialized!")
        return
    
    print(f"Dispatcher type: {type(dispatcher)}")
    print(f"Dispatcher attributes: {[attr for attr in dir(dispatcher) if not attr.startswith('_')]}")
    
    # Test symbol lookup
    print("\n1. Testing symbol lookup")
    print("-" * 40)
    
    test_symbols = ["BM25Indexer", "SQLiteStore", "IndexManager"]
    
    for symbol in test_symbols:
        print(f"\nLooking up '{symbol}':")
        
        # Try different method names
        if hasattr(dispatcher, 'lookup'):
            result = dispatcher.lookup(symbol)
            print(f"  lookup() result: {result}")
        
        if hasattr(dispatcher, 'lookup_symbol'):
            result = dispatcher.lookup_symbol(symbol)
            print(f"  lookup_symbol() result: {result}")
        
        if hasattr(dispatcher, 'find_symbol'):
            result = dispatcher.find_symbol(symbol)
            print(f"  find_symbol() result: {result}")
    
    # Test search
    print("\n\n2. Testing search")
    print("-" * 40)
    
    test_queries = ["reranking", "centralized storage", "BM25"]
    
    for query in test_queries:
        print(f"\nSearching for '{query}':")
        
        if hasattr(dispatcher, 'search'):
            results = list(dispatcher.search(query, limit=5))
            print(f"  search() returned {len(results)} results")
            if results:
                print(f"  First result: {results[0]}")
        
        if hasattr(dispatcher, 'search_code'):
            results = list(dispatcher.search_code(query, limit=5))
            print(f"  search_code() returned {len(results)} results")
    
    # Check storage
    print("\n\n3. Checking storage")
    print("-" * 40)
    
    if hasattr(dispatcher, '_sqlite_store'):
        store = dispatcher._sqlite_store
        print(f"  SQLite store: {store}")
        print(f"  DB path: {store.db_path if hasattr(store, 'db_path') else 'unknown'}")
    
    # Try direct BM25 search
    print("\n\n4. Direct BM25 search test")
    print("-" * 40)
    
    import sqlite3
    db_path = Path.home() / ".mcp" / "indexes" / "f7b49f5d0ae0" / "main_f48abb0.db"
    
    if db_path.exists():
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT filepath, snippet(bm25_content, -1, '<<', '>>', '...', 10)
            FROM bm25_content
            WHERE bm25_content MATCH 'BM25Indexer'
            LIMIT 3
        """)
        
        results = cursor.fetchall()
        print(f"  Direct BM25 search found {len(results)} results")
        for filepath, snippet in results:
            print(f"    - {filepath}: {snippet}")
        
        conn.close()


if __name__ == "__main__":
    asyncio.run(test_dispatcher())