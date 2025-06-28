#!/usr/bin/env python3
"""
Test the patched MCP server to verify it returns actual results.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add to path
sys.path.insert(0, "/workspaces/Code-Index-MCP")

# Import MCP server components
import scripts.cli.mcp_server_cli as mcp_cli


async def test_mcp_server():
    """Test the patched MCP server functionality."""
    
    print("Testing Patched MCP Server with BM25 Fallback")
    print("=" * 80)
    
    # Initialize services
    print("\n1. Initializing services...")
    try:
        await mcp_cli.initialize_services()
        print("   ✓ Services initialized")
    except Exception as e:
        print(f"   ✗ Failed to initialize: {e}")
        return
    
    # Get dispatcher reference
    dispatcher = mcp_cli.dispatcher
    
    # Check dispatcher
    print(f"\n2. Dispatcher type: {type(dispatcher).__name__}")
    print(f"   SQLite store: {dispatcher._sqlite_store is not None}")
    print(f"   Number of plugins: {len(dispatcher._plugins)}")
    
    # Test symbol lookup
    print("\n3. Testing symbol lookup with BM25 fallback:")
    test_symbols = ["BM25Indexer", "SQLiteStore", "PathResolver", "EnhancedDispatcher"]
    
    for symbol in test_symbols:
        try:
            result = dispatcher.lookup(symbol)
            if result:
                print(f"   ✓ {symbol}: Found!")
                print(f"     - File: {result.get('defined_in', 'unknown')}")
                print(f"     - Kind: {result.get('kind', 'unknown')}")
                print(f"     - Language: {result.get('language', 'unknown')}")
                print(f"     - Signature: {result.get('signature', '')[:60]}...")
            else:
                print(f"   ✗ {symbol}: Not found")
        except Exception as e:
            print(f"   ✗ {symbol}: Error - {e}")
    
    # Test search
    print("\n4. Testing search with BM25 fallback:")
    test_queries = ["reranking", "BM25", "centralized storage", "semantic search"]
    
    for query in test_queries:
        try:
            results = list(dispatcher.search(query, limit=5))
            print(f"\n   Query '{query}': {len(results)} results")
            if results:
                for i, r in enumerate(results[:3]):
                    print(f"     {i+1}. {r.get('file', 'unknown')}")
                    snippet = r.get('snippet', '').replace('\n', ' ')[:80]
                    print(f"        Snippet: {snippet}...")
                    print(f"        Score: {r.get('score', 0)}")
        except Exception as e:
            print(f"   Query '{query}': Error - {e}")
    
    # Test natural language query
    print("\n5. Testing natural language queries:")
    nl_queries = ["how to index a repository", "what is reranking"]
    
    for query in nl_queries:
        try:
            results = list(dispatcher.search(query, semantic=False, limit=3))
            print(f"\n   Query '{query}': {len(results)} results")
            if results:
                print(f"     First result: {results[0].get('file', 'unknown')}")
                print(f"     Snippet: {results[0].get('snippet', '')[:60]}...")
        except Exception as e:
            print(f"   Query '{query}': Error - {e}")
    
    print("\n\nMCP Server Test Complete!")
    print("=" * 80)
    
    # Summary
    if dispatcher._sqlite_store:
        print(f"\nUsing SQLite store at: {dispatcher._sqlite_store.db_path}")
        print(f"BM25 fallback is {'ACTIVE' if len(dispatcher._plugins) == 0 else 'not needed'}")


if __name__ == "__main__":
    asyncio.run(test_mcp_server())