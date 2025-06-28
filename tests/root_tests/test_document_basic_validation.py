#!/usr/bin/env python3
"""Basic validation test for document processing functionality."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from mcp_server.plugins.plugin_factory import PluginFactory
from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
from mcp_server.storage.sqlite_store import SQLiteStore


def test_basic_functionality():
    """Test basic document processing functionality."""
    print("🧪 Testing Document Processing Basic Functionality")
    print("="*50)
    
    # Create components
    store = SQLiteStore(':memory:')
    # PluginFactory is not instantiable, will pass the class
    
    # Create dispatcher with factory (not passing plugins list)
    dispatcher = EnhancedDispatcher(
        plugins=None,
        sqlite_store=store,
        use_plugin_factory=True,
        lazy_load=False,  # Load all plugins immediately
        enable_advanced_features=True,
        semantic_search_enabled=True
    )
    
    # Test 1: Markdown indexing
    print("\n✅ Test 1: Markdown Indexing")
    try:
        result = dispatcher.index_file('test_data/markdown_samples/simple.md')
        print(f"  Indexed {len(result)} symbols from simple.md")
        if result:
            print(f"  First symbol: {result[0].get('name', 'unnamed')} at line {result[0].get('start_line', 0)}")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    # Test 2: PlainText indexing
    print("\n✅ Test 2: PlainText Indexing")
    try:
        result = dispatcher.index_file('test_data/plaintext_samples/simple.txt')
        print(f"  Indexed {len(result)} symbols from simple.txt")
        if result:
            print(f"  First symbol: {result[0].get('name', 'unnamed')} at line {result[0].get('start_line', 0)}")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    # Test 3: Document search
    print("\n✅ Test 3: Document Search")
    try:
        results = dispatcher.search('installation')
        print(f"  Found {len(results)} results for 'installation'")
        if results:
            print(f"  First result: {results[0]['file']} (score: {results[0].get('relevance', 0):.2f})")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    # Test 4: Natural language query
    print("\n✅ Test 4: Natural Language Query")
    try:
        results = dispatcher.search('how to install')
        print(f"  Found {len(results)} results for 'how to install'")
        if results:
            print(f"  First result: {results[0]['file']} (score: {results[0].get('relevance', 0):.2f})")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    # Test 5: Metadata extraction
    print("\n✅ Test 5: Metadata Extraction")
    try:
        # Index a file with frontmatter
        result = dispatcher.index_file('test_data/markdown_samples/complex.md')
        # Check if metadata was extracted
        symbols = dispatcher.get_symbols('test_data/markdown_samples/complex.md')
        has_metadata = any(s.get('metadata') for s in symbols)
        print(f"  Metadata extracted: {has_metadata}")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    # Test 6: Plugin status
    print("\n✅ Test 6: Plugin Status")
    try:
        status = dispatcher.get_status()
        print(f"  Plugins loaded: {status.get('plugins_loaded', 0)}")
        print(f"  Languages supported: {', '.join(sorted(status.get('loaded_languages', [])))}")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    print("\n" + "="*50)
    print("✅ Basic validation complete!")


if __name__ == "__main__":
    test_basic_functionality()