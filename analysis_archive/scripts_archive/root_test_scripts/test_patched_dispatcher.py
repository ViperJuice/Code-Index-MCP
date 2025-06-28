#!/usr/bin/env python3
"""Test the patched enhanced dispatcher with timeout and BM25 bypass."""

import sys
from pathlib import Path
import time

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher


def test_patched_dispatcher():
    """Test the patched dispatcher on multiple indexes."""
    
    print("TESTING PATCHED ENHANCED DISPATCHER")
    print("=" * 80)
    
    # Test indexes
    test_cases = [
        (".indexes/f7b49f5d0ae0/current.db", "Code-Index-MCP"),
        (".indexes/e3acd2328eea/current.db", "TypeScript project (74K files)"),
        (".indexes/48f70bd595a6/current.db", "Dart SDK (51K files)"),
    ]
    
    for db_path, description in test_cases:
        if not Path(db_path).exists():
            print(f"\n❌ {description}: Database not found")
            continue
        
        print(f"\n📁 Testing {description}")
        print("-" * 60)
        
        try:
            # Create store and dispatcher
            store = SQLiteStore(db_path)
            print("✓ SQLiteStore created")
            
            # Create dispatcher with minimal config to test fixes
            dispatcher = EnhancedDispatcher(
                sqlite_store=store,
                semantic_search_enabled=False,  # Avoid Qdrant issues
                lazy_load=True,  # Will trigger plugin loading with timeout
                use_plugin_factory=True
            )
            print("✓ EnhancedDispatcher created")
            
            # Test queries
            test_queries = ["def", "class", "function", "import", "TODO"]
            
            for query in test_queries:
                try:
                    start_time = time.time()
                    results = list(dispatcher.search(query, limit=5))
                    elapsed = time.time() - start_time
                    
                    if results:
                        print(f"\n✓ Query '{query}': {len(results)} results in {elapsed:.3f}s")
                        # Show first result
                        first = results[0]
                        # Handle both dict and object results
                        if isinstance(first, dict):
                            file_path = first.get('file', first.get('file_path', 'Unknown'))
                            snippet = first.get('snippet', '')
                        else:
                            file_path = first.file_path if hasattr(first, 'file_path') else 'Unknown'
                            snippet = first.snippet if hasattr(first, 'snippet') else ''
                        
                        print(f"  First match: {file_path}")
                        if snippet:
                            snippet = snippet.replace('\n', ' ').strip()
                            print(f"  Snippet: {snippet[:100]}...")
                    else:
                        print(f"\n⚠️ Query '{query}': No results in {elapsed:.3f}s")
                        
                except Exception as e:
                    print(f"\n❌ Query '{query}': Error - {e}")
                    import traceback
                    traceback.print_exc()
            
            # Get stats if available
            if hasattr(dispatcher, 'get_stats'):
                stats = dispatcher.get_stats()
                print(f"\n📊 Statistics: {stats}")
            
        except Exception as e:
            print(f"\n❌ Fatal error: {e}")
            import traceback
            traceback.print_exc()
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("\nThe patched dispatcher should:")
    print("1. ✓ Not hang on plugin loading (5s timeout)")
    print("2. ✓ Use direct BM25 bypass when no plugins loaded")
    print("3. ✓ Return search results quickly")


def test_timeout_behavior():
    """Specifically test the timeout behavior."""
    
    print("\n\nTESTING TIMEOUT BEHAVIOR")
    print("=" * 80)
    
    db_path = ".indexes/f7b49f5d0ae0/current.db"
    
    if not Path(db_path).exists():
        print("❌ Test database not found")
        return
    
    store = SQLiteStore(db_path)
    
    # Create dispatcher that will trigger plugin loading
    print("\nCreating dispatcher with plugin loading enabled...")
    start = time.time()
    
    dispatcher = EnhancedDispatcher(
        sqlite_store=store,
        semantic_search_enabled=False,
        lazy_load=False,  # Load plugins immediately
        use_plugin_factory=True
    )
    
    elapsed = time.time() - start
    print(f"Dispatcher created in {elapsed:.3f}s")
    
    if elapsed > 6:
        print("⚠️ Plugin loading took longer than timeout (might not be working)")
    else:
        print("✓ Plugin loading completed within timeout")
    
    # Test a search
    results = list(dispatcher.search("test", limit=1))
    print(f"\nSearch test: {len(results)} results")


if __name__ == "__main__":
    test_patched_dispatcher()
    test_timeout_behavior()