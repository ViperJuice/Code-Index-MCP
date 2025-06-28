#!/usr/bin/env python3
"""Test MCP dispatcher retrieval to diagnose why it returns 0 results."""

import sys
from pathlib import Path
import time

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher


def test_dispatcher():
    """Test dispatcher on working indexes."""
    
    print("TESTING MCP DISPATCHER")
    print("=" * 80)
    
    # Test on Code-Index-MCP's own index
    db_path = ".indexes/f7b49f5d0ae0/current.db"
    
    print(f"\nTesting with database: {db_path}")
    
    try:
        # Create SQLite store
        store = SQLiteStore(db_path)
        print("✓ SQLiteStore created")
        
        # Test direct SQLite query first
        print("\n1. Testing direct SQLite query:")
        results = store.search_bm25("BM25Indexer", limit=5)
        print(f"   Direct BM25 search: {len(results)} results")
        
        # Create dispatcher without semantic search to avoid Qdrant issues
        print("\n2. Creating EnhancedDispatcher:")
        dispatcher = EnhancedDispatcher(
            sqlite_store=store,
            semantic_search_enabled=False,  # Disable to avoid Qdrant
            lazy_load=False,  # Load plugins immediately
            use_plugin_factory=False  # Avoid plugin loading issues
        )
        print("✓ Dispatcher created")
        
        # Check dispatcher state
        print(f"   - SQLite store: {dispatcher.sqlite_store is not None}")
        print(f"   - Semantic enabled: {dispatcher.semantic_search_enabled}")
        print(f"   - Plugin manager: {dispatcher.plugin_manager is not None}")
        
        # Test different search methods
        print("\n3. Testing dispatcher search methods:")
        
        # Test search() method
        print("\n   a) Testing search() method:")
        queries = ["BM25Indexer", "def", "class", "import"]
        
        for query in queries:
            try:
                start = time.time()
                results = list(dispatcher.search(query, limit=5))
                duration = time.time() - start
                print(f"      Query '{query}': {len(results)} results in {duration:.3f}s")
                
                if results:
                    first = results[0]
                    print(f"        First result: {first.get('file_path', 'N/A')}")
                    
            except Exception as e:
                print(f"      Query '{query}': ERROR - {e}")
        
        # Test search_bm25() if available
        if hasattr(dispatcher, 'search_bm25'):
            print("\n   b) Testing search_bm25() method:")
            try:
                results = list(dispatcher.search_bm25("BM25Indexer", limit=5))
                print(f"      Direct BM25: {len(results)} results")
            except Exception as e:
                print(f"      Direct BM25: ERROR - {e}")
        
        # Check if dispatcher is using the correct search backend
        print("\n4. Debugging dispatcher internals:")
        
        # Check if there's a route issue
        if hasattr(dispatcher, '_route_query'):
            print("   - Has _route_query method")
            try:
                route = dispatcher._route_query("BM25Indexer")
                print(f"   - Query routed to: {route}")
            except Exception as e:
                print(f"   - Route error: {e}")
        
        # Check available search methods
        search_methods = [m for m in dir(dispatcher) if 'search' in m and not m.startswith('_')]
        print(f"   - Available search methods: {search_methods}")
        
        # Test symbol lookup directly
        print("\n5. Testing symbol lookup:")
        if hasattr(store, 'get_symbol'):
            try:
                symbols = store.get_symbol("BM25Indexer")
                print(f"   Symbol lookup: {len(symbols)} results")
            except Exception as e:
                print(f"   Symbol lookup error: {e}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Try with a different dispatcher configuration
    print("\n\n6. Testing with minimal dispatcher:")
    try:
        # Create minimal dispatcher
        dispatcher2 = EnhancedDispatcher(
            plugins=[],  # No plugins
            sqlite_store=store,
            enable_advanced_features=False,
            semantic_search_enabled=False
        )
        
        results = list(dispatcher2.search("def", limit=5))
        print(f"   Minimal dispatcher search: {len(results)} results")
        
    except Exception as e:
        print(f"   Minimal dispatcher error: {e}")


if __name__ == "__main__":
    test_dispatcher()