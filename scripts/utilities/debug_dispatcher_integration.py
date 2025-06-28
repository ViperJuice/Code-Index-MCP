#!/usr/bin/env python3
"""Debug dispatcher integration issues."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
from mcp_server.plugins.plugin_factory import PluginFactory
from mcp_server.storage.sqlite_store import SQLiteStore


def debug_dispatcher_integration():
    """Debug why dispatcher search/lookup isn't working."""
    print("=== Debugging Dispatcher Integration ===\n")
    
    # Create simple test
    go_code = '''package main

func fibonacci(n int) int {
    if n <= 1 {
        return n
    }
    return fibonacci(n-1) + fibonacci(n-2)
}

func main() {
    println(fibonacci(10))
}'''
    
    # Create store and dispatcher
    store = SQLiteStore(":memory:")
    dispatcher = EnhancedDispatcher(
        plugins=None,
        sqlite_store=store,
        use_plugin_factory=True,
        lazy_load=True
    )
    
    # Create test file
    test_file = Path("debug.go")
    test_file.write_text(go_code)
    
    try:
        print("1. Testing direct plugin functionality...")
        plugin = PluginFactory.create_plugin("go", store, enable_semantic=False)
        shard = plugin.indexFile(test_file, go_code)
        plugin_search = list(plugin.search("fibonacci", {"limit": 5}))
        plugin_lookup = plugin.getDefinition("fibonacci")
        
        print(f"   Plugin symbols: {len(shard['symbols'])}")
        print(f"   Plugin search results: {len(plugin_search)}")
        print(f"   Plugin lookup result: {'Found' if plugin_lookup else 'Not found'}")
        
        print("\n2. Testing dispatcher functionality...")
        dispatcher.index_file(test_file)
        
        # Check what plugins are loaded
        print(f"   Loaded plugins: {len(dispatcher._plugins)}")
        print(f"   Plugin languages: {list(dispatcher._by_lang.keys())}")
        
        # Test dispatcher search
        dispatcher_search = list(dispatcher.search("fibonacci", limit=5))
        print(f"   Dispatcher search results: {len(dispatcher_search)}")
        for result in dispatcher_search[:3]:
            print(f"     - {result.get('file', 'N/A')}:{result.get('line', 'N/A')}")
        
        # Test dispatcher lookup
        dispatcher_lookup = dispatcher.lookup("fibonacci")
        print(f"   Dispatcher lookup result: {'Found' if dispatcher_lookup else 'Not found'}")
        if dispatcher_lookup:
            print(f"     - Kind: {dispatcher_lookup.get('kind', 'N/A')}")
            print(f"     - File: {dispatcher_lookup.get('defined_in', 'N/A')}")
        
        print("\n3. Investigating plugin method compatibility...")
        go_plugin = dispatcher._by_lang.get('go')
        if go_plugin:
            print(f"   Go plugin class: {go_plugin.__class__.__name__}")
            print(f"   Has search method: {hasattr(go_plugin, 'search')}")
            print(f"   Has getDefinition method: {hasattr(go_plugin, 'getDefinition')}")
            
            # Test direct calls
            if hasattr(go_plugin, 'search'):
                direct_search = list(go_plugin.search("fibonacci", {"limit": 5}))
                print(f"   Direct plugin search: {len(direct_search)} results")
            
            if hasattr(go_plugin, 'getDefinition'):
                direct_lookup = go_plugin.getDefinition("fibonacci")
                print(f"   Direct plugin lookup: {'Found' if direct_lookup else 'Not found'}")
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        test_file.unlink(missing_ok=True)


if __name__ == "__main__":
    debug_dispatcher_integration()