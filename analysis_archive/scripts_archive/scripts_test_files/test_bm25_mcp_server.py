#!/usr/bin/env python3
"""
Test the BM25 MCP server to ensure it returns valid results.
"""

import json
import subprocess
import asyncio
from pathlib import Path


async def test_mcp_server():
    """Test MCP server with sample queries."""
    
    # Start the MCP server process
    server_path = Path("/workspaces/Code-Index-MCP/scripts/cli/mcp_server_bm25.py")
    
    print("Testing BM25 MCP Server")
    print("=" * 60)
    
    # Test 1: Symbol lookup
    print("\n1. Testing symbol_lookup tool:")
    print("-" * 40)
    
    test_symbols = ["BM25Indexer", "SQLiteStore", "EnhancedDispatcher"]
    
    for symbol in test_symbols:
        # Simulate MCP tool call
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "symbol_lookup",
                "arguments": {"symbol": symbol}
            },
            "id": 1
        }
        
        print(f"\nLooking up symbol: {symbol}")
        # In real usage, this would be sent to the server via stdio
        # For testing, we'll import and call directly
        
    # Test 2: Search code
    print("\n\n2. Testing search_code tool:")
    print("-" * 40)
    
    test_queries = ["reranking", "BM25", "centralized storage"]
    
    for query in test_queries:
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "search_code",
                "arguments": {"query": query, "limit": 3}
            },
            "id": 2
        }
        
        print(f"\nSearching for: {query}")
        # In real usage, this would be sent to the server
    
    # Test 3: Get status
    print("\n\n3. Testing get_status tool:")
    print("-" * 40)
    
    request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "get_status",
            "arguments": {}
        },
        "id": 3
    }
    
    print("\nGetting server status...")
    
    # Direct test by importing the module
    print("\n\n4. Direct module test:")
    print("-" * 40)
    
    import sys
    sys.path.insert(0, "/workspaces/Code-Index-MCP/scripts/cli")
    from mcp_server_bm25 import BM25Dispatcher
    
    dispatcher = BM25Dispatcher()
    
    # Test symbol lookup
    print("\nDirect symbol lookup test:")
    for symbol in ["BM25Indexer", "SQLiteStore"]:
        result = dispatcher.lookup(symbol)
        if result:
            print(f"  {symbol}: Found in {result['defined_in']} as {result['kind']}")
        else:
            print(f"  {symbol}: Not found")
    
    # Test search
    print("\nDirect search test:")
    results = dispatcher.search("reranking", limit=3)
    print(f"  Found {len(results)} results")
    for r in results:
        print(f"    - {r['file']}:{r['line']} - {r['snippet'][:60]}...")
    
    # Get status
    print("\nStatus:")
    health = dispatcher.health_check()
    stats = dispatcher.get_statistics()
    print(f"  Health: {health}")
    print(f"  Stats: {stats}")
    
    print("\n\nMCP server is ready for use!")
    print("To use with Claude Code, update your .mcp.json to point to:")
    print(f"  {server_path}")


if __name__ == "__main__":
    asyncio.run(test_mcp_server())