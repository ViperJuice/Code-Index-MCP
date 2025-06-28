#!/usr/bin/env python3
"""Test MCP search_code tool to verify it doesn't hang."""
import sys
import os
import time
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.core.path_utils import PathUtils

def test_search():
    """Test search functionality directly."""
    print("Testing MCP search functionality...")
    
    # Find the index
    index_path = PathUtils.get_index_storage_path() / "844145265d7a" / "code_index.db"
    if not index_path.exists():
        print(f"Error: Index not found at {index_path}")
        return
    
    # Create SQLite store
    sqlite_store = SQLiteStore(str(index_path))
    
    # Create dispatcher
    print("Creating dispatcher...")
    dispatcher = EnhancedDispatcher(
        plugins=[],
        sqlite_store=sqlite_store,
        enable_advanced_features=True,
        use_plugin_factory=True,
        lazy_load=True,
        semantic_search_enabled=False,
        memory_aware=True,
        multi_repo_enabled=False
    )
    
    # Test search
    queries = ["EnhancedDispatcher", "multi_repo_manager", "def search"]
    
    for query in queries:
        print(f"\nSearching for: {query}")
        start_time = time.time()
        
        try:
            # Call search method directly
            results = list(dispatcher.search(query, semantic=False, limit=5))
            elapsed = time.time() - start_time
            
            print(f"Found {len(results)} results in {elapsed:.2f}s")
            
            # Show first result
            if results:
                first = results[0]
                # Check what type of result we got
                if hasattr(first, '__dict__'):
                    print(f"First result attrs: {first.__dict__}")
                else:
                    print(f"First result: {first}")
                    if isinstance(first, dict):
                        print(f"  File: {first.get('file', first.get('file_path', 'N/A'))}")
                        print(f"  Line: {first.get('line', 'N/A')}")
                        print(f"  Snippet: {first.get('snippet', 'N/A')[:100]}...")
                
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"Error after {elapsed:.2f}s: {e}")

if __name__ == "__main__":
    test_search()