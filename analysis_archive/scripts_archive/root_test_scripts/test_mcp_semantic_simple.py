#!/usr/bin/env python3
"""Simple test of MCP semantic search."""

import json
import sys
import os
import asyncio

# Add project root to path
sys.path.insert(0, '/workspaces/Code-Index-MCP')

from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
from mcp_server.storage.sqlite_store import SQLiteStore

# Set API key
os.environ['VOYAGE_AI_API_KEY'] = 'pa-Fdhj97wixjABvuP4oGuOgNTgjoPM3-ovbmg-4VktTnL'

def test_search():
    """Test semantic and BM25 search."""
    # Use the current project's index
    db_path = "/workspaces/Code-Index-MCP/.indexes/f7b49f5d0ae0/new_index.db"
    
    print(f"Using index: {db_path}")
    
    # Initialize storage
    sqlite_store = SQLiteStore(db_path)
    
    # Create dispatcher
    dispatcher = EnhancedDispatcher(
        plugins=[],  # No plugins to force direct search
        sqlite_store=sqlite_store,
        enable_advanced_features=True,
        use_plugin_factory=False,
        lazy_load=False,
        semantic_search_enabled=True
    )
    
    # Test queries
    test_cases = [
        ("BM25: 'def search'", "def search", False, 5),
        ("Semantic: 'how to initialize a class'", "how to initialize a class", True, 5),
        ("Semantic: 'error handling'", "error handling in main function", True, 5),
        ("BM25: 'EnhancedDispatcher'", "EnhancedDispatcher", False, 5),
    ]
    
    for name, query, semantic, limit in test_cases:
        print(f"\n=== {name} ===")
        print(f"Query: '{query}' (semantic={semantic})")
        
        try:
            results = list(dispatcher.search(query, semantic=semantic, limit=limit))
            
            if results:
                print(f"Found {len(results)} results:")
                for i, result in enumerate(results[:3], 1):
                    print(f"\n  {i}. {result.get('file', 'unknown')}")
                    print(f"     Score: {result.get('score', 0):.3f}")
                    snippet = result.get('snippet', '').replace('\n', ' ')[:100]
                    if snippet:
                        print(f"     Snippet: {snippet}...")
            else:
                print("No results found")
                
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_search()