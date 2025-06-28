#!/usr/bin/env python3
"""Test semantic search functionality with centralized indexes."""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_server.utils.semantic_indexer import SemanticIndexer
from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
from mcp_server.storage.sqlite_store import SQLiteStore


def test_semantic_search():
    """Test semantic search with a real query."""
    # Setup paths
    indexes_dir = Path(".indexes")
    qdrant_path = indexes_dir / "qdrant" / "main.qdrant"
    
    # Find a test repository index
    test_repo = None
    for item in indexes_dir.iterdir():
        if item.is_dir() and item.name != "qdrant":
            db_path = item / "current.db"
            if db_path.exists():
                test_repo = item
                break
    
    if not test_repo:
        print("No test repository found")
        return
    
    print(f"Using test repository: {test_repo}")
    db_path = test_repo / "current.db"
    
    # Initialize SQLite store
    sqlite_store = SQLiteStore(str(db_path))
    
    # Initialize semantic indexer
    print(f"Initializing semantic indexer with Qdrant at: {qdrant_path}")
    semantic_indexer = SemanticIndexer(
        qdrant_path=str(qdrant_path),
        collection="code-embeddings"
    )
    
    # Test queries
    test_queries = [
        "how to initialize a class",
        "error handling in main function",
        "database connection setup",
        "parse JSON data",
        "authentication middleware"
    ]
    
    print("\n=== Testing Semantic Search ===")
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        
        try:
            # Search using semantic indexer
            results = semantic_indexer.search(
                query=query,
                limit=5,
                hybrid=True  # Use hybrid search
            )
            
            if results:
                print(f"Found {len(results)} results:")
                for i, result in enumerate(results[:3], 1):
                    print(f"  {i}. {result['file_path']} (score: {result.get('score', 0):.3f})")
                    if 'snippet' in result:
                        snippet = result['snippet'].replace('\n', ' ')[:100]
                        print(f"     {snippet}...")
            else:
                print("  No results found")
                
        except Exception as e:
            print(f"  Error: {e}")
    
    # Test dispatcher with semantic search
    print("\n\n=== Testing Dispatcher with Semantic Search ===")
    dispatcher = EnhancedDispatcher(
        plugins=[],  # No plugins to force BM25 + semantic fallback
        sqlite_store=sqlite_store,
        enable_advanced_features=True,
        use_plugin_factory=False,  # Disable to avoid plugin loading
        lazy_load=False,
        semantic_search_enabled=True
    )
    
    for query in test_queries[:2]:
        print(f"\nQuery: '{query}'")
        results = list(dispatcher.search(query, semantic=True, limit=5))
        
        if results:
            print(f"Found {len(results)} results:")
            for i, result in enumerate(results[:3], 1):
                print(f"  {i}. {result['file']} (line {result.get('line', '?')})")
                if 'snippet' in result:
                    snippet = result['snippet'].replace('\n', ' ')[:100]
                    print(f"     {snippet}...")
        else:
            print("  No results found")


if __name__ == "__main__":
    test_semantic_search()