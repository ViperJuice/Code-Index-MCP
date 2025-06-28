#\!/usr/bin/env python3
"""
Test the MCP server directly to verify it returns results after the fix.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add to path
sys.path.insert(0, "/workspaces/Code-Index-MCP")

# Import MCP server components
from scripts.cli.mcp_server_cli import initialize_services, dispatcher


async def test_mcp_server():
    """Test the MCP server functionality."""
    
    print("Testing MCP Server After Fix")
    print("=" * 80)
    
    # Initialize services
    print("\n1. Initializing services...")
    try:
        await initialize_services()
        print("   ✓ Services initialized")
    except Exception as e:
        print(f"   ✗ Failed to initialize: {e}")
        return
    
    # Check dispatcher
    print(f"\n2. Dispatcher type: {type(dispatcher).__name__}")
    
    # Check health
    if hasattr(dispatcher, 'health_check'):
        health = dispatcher.health_check()
        print(f"   Health: {health.get('status', 'unknown')}")
        print(f"   Components: {health.get('components', {}).get('dispatcher', {})}")
    
    # Test symbol lookup
    print("\n3. Testing symbol lookup:")
    test_symbols = ["BM25Indexer", "SQLiteStore", "PathResolver", "dispatcher"]
    
    for symbol in test_symbols:
        try:
            result = dispatcher.lookup(symbol)
            if result:
                print(f"   ✓ {symbol}: Found in {result.get('defined_in', 'unknown')}:{result.get('line', 0)}")
                print(f"     Kind: {result.get('kind', 'unknown')}, Language: {result.get('language', 'unknown')}")
            else:
                print(f"   ✗ {symbol}: Not found")
        except Exception as e:
            print(f"   ✗ {symbol}: Error - {e}")
    
    # Test search
    print("\n4. Testing search:")
    test_queries = ["reranking", "BM25", "centralized storage", "semantic search"]
    
    for query in test_queries:
        try:
            results = list(dispatcher.search(query, limit=5))
            print(f"   Query '{query}': {len(results)} results")
            if results:
                for i, r in enumerate(results[:2]):
                    print(f"     {i+1}. {r.get('file', 'unknown')}:{r.get('line', 0)}")
                    print(f"        {r.get('snippet', '')[:80]}...")
        except Exception as e:
            print(f"   Query '{query}': Error - {e}")
    
    # Test natural language query
    print("\n5. Testing natural language queries:")
    nl_queries = ["how to index a repository", "what is reranking", "where is authentication handled"]
    
    for query in nl_queries:
        try:
            results = list(dispatcher.search(query, semantic=True, limit=3))
            print(f"   Query '{query}': {len(results)} results")
            if results and len(results) > 0:
                print(f"     First result: {results[0].get('file', 'unknown')}")
        except Exception as e:
            print(f"   Query '{query}': Error - {e}")
    
    # Get statistics
    print("\n6. Statistics:")
    if hasattr(dispatcher, 'get_statistics'):
        stats = dispatcher.get_statistics()
        print(f"   {json.dumps(stats, indent=2)}")
    
    print("\n\nMCP Server Test Complete\!")
    
    # Check if we're actually using BM25
    if hasattr(dispatcher, '_sqlite_store') and dispatcher._sqlite_store:
        print(f"\nUsing SQLite store at: {dispatcher._sqlite_store.db_path}")


if __name__ == "__main__":
    asyncio.run(test_mcp_server())
EOF < /dev/null
