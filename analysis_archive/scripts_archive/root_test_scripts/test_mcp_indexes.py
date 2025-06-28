#!/usr/bin/env python3
"""
Test script to verify MCP indexes work correctly.
"""

import asyncio
import json
import sys
from pathlib import Path
import sqlite3

# Add parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
from mcp_server.plugin_system import PluginManager
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.indexer.bm25_indexer import BM25Indexer


async def test_index(index_path: Path, query: str):
    """Test an index with a query."""
    print(f"\nTesting index: {index_path}")
    print(f"Query: '{query}'")
    
    # Open database directly to test BM25 search
    conn = sqlite3.connect(str(index_path))
    
    # Test direct BM25 search
    cursor = conn.execute("""
        SELECT path, 
               snippet(bm25_content, 1, '**', '**', '...', 50) as snippet,
               bm25(bm25_content) as score
        FROM bm25_content
        WHERE bm25_content MATCH ?
        ORDER BY score
        LIMIT 10
    """, (query,))
    
    results = cursor.fetchall()
    conn.close()
    
    print(f"\nFound {len(results)} results:")
    for i, (path, snippet, score) in enumerate(results, 1):
        print(f"{i}. {path}")
        print(f"   Score: {score:.4f}")
        print(f"   Snippet: {snippet}")
        print()


async def main():
    """Main test function."""
    # Test indexes directory
    test_indexes_base = Path("/workspaces/Code-Index-MCP/test_indexes")
    
    # Test different indexes with appropriate queries
    test_cases = [
        ("go_gin/code_index.db", "router"),
        ("python_django/code_index.db", "model view"),
        ("csharp_aspnetcore/code_index.db", "controller"),
        ("javascript_react/code_index.db", "component state"),
        ("rust_tokio/code_index.db", "async await"),
    ]
    
    for index_name, query in test_cases:
        index_path = test_indexes_base / index_name
        
        if index_path.exists():
            try:
                await test_index(index_path, query)
            except Exception as e:
                print(f"Error testing {index_name}: {e}")
        else:
            print(f"Index not found: {index_path}")
    
    # Now test with MCP tools
    print("\n" + "="*60)
    print("Testing with MCP tools")
    print("="*60)
    
    # The MCP server should be able to discover and use these indexes
    # when started from the test_indexes directory


if __name__ == "__main__":
    asyncio.run(main())