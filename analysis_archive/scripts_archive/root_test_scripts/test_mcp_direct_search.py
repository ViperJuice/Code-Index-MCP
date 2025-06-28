#!/usr/bin/env python3
"""Test MCP search directly without subprocess"""
import sys
import os
sys.path.insert(0, '/workspaces/Code-Index-MCP')

from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
from mcp_server.storage.sqlite_store import SQLiteStore
from pathlib import Path

def test_direct_search():
    """Test search functionality directly"""
    # Initialize store
    db_path = "/workspaces/Code-Index-MCP/.indexes/f7b49f5d0ae0/current.db"
    print(f"Using database: {db_path}")
    
    store = SQLiteStore(db_path)
    
    # Create dispatcher with minimal config
    dispatcher = EnhancedDispatcher(
        plugins=[],  # Start with no plugins
        sqlite_store=store,
        enable_advanced_features=True,
        use_plugin_factory=True,
        lazy_load=True,
        semantic_search_enabled=False  # Disable semantic search for now
    )
    
    # Test symbol lookup
    print("\n=== Testing symbol lookup ===")
    test_symbols = ["SQLiteStore", "EnhancedDispatcher", "test_", "main"]
    for symbol in test_symbols:
        result = dispatcher.lookup(symbol)
        if result:
            print(f"✓ Found {symbol}: {result.get('kind')} in {result.get('defined_in')}")
        else:
            print(f"✗ Not found: {symbol}")
    
    # Test code search
    print("\n=== Testing code search ===")
    test_queries = ["initialize", "plugin", "search", "MCP"]
    for query in test_queries:
        results = list(dispatcher.search(query, limit=3))
        if results:
            print(f"✓ Found {len(results)} results for '{query}':")
            for r in results[:2]:
                print(f"  - {r.get('file')}:{r.get('line')} - {r.get('snippet', '')[:60]}...")
        else:
            print(f"✗ No results for '{query}'")

if __name__ == "__main__":
    test_direct_search()