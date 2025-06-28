#!/usr/bin/env python3
"""Debug test for semantic search integration."""

import os
import sys
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Load environment
from dotenv import load_dotenv
load_dotenv()

# Force semantic search enabled
os.environ["SEMANTIC_SEARCH_ENABLED"] = "true"

sys.path.insert(0, str(Path(__file__).parent))


def test_environment():
    """Test environment variables are loaded."""
    print("=== Testing Environment ===")
    print(f"VOYAGE_API_KEY present: {'VOYAGE_API_KEY' in os.environ}")
    print(f"SEMANTIC_SEARCH_ENABLED: {os.environ.get('SEMANTIC_SEARCH_ENABLED')}")
    print(f"QDRANT_HOST: {os.environ.get('QDRANT_HOST')}")
    print()


def test_plugin_loading():
    """Test if semantic plugin loads."""
    print("=== Testing Plugin Loading ===")
    
    # This should trigger semantic plugin import
    from mcp_server.plugins.python_plugin import Plugin
    
    print(f"Plugin class: {Plugin.__name__}")
    print(f"Plugin module: {Plugin.__module__}")
    
    # Check if it's the semantic version
    is_semantic = Plugin.__module__.endswith('plugin_semantic')
    if is_semantic:
        print("✓ Semantic plugin loaded")
    else:
        print("✗ Basic plugin loaded")
    
    return Plugin


def test_semantic_indexer():
    """Test semantic indexer directly."""
    print("\n=== Testing Semantic Indexer ===")
    
    try:
        from mcp_server.utils.semantic_indexer import SemanticIndexer
        
        # Test with in-memory Qdrant
        indexer = SemanticIndexer(collection="test", qdrant_path=":memory:")
        print("✓ SemanticIndexer created successfully")
        
        # Test indexing
        indexer.index_symbol(
            file="test.py",
            name="test_function",
            kind="function",
            signature="def test_function():",
            line=1,
            span=(1, 5),
            doc="Test function",
            content="def test_function():\n    pass"
        )
        print("✓ Symbol indexed successfully")
        
        # Test search
        results = indexer.search("test function", limit=5)
        print(f"✓ Search returned {len(results)} results")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_plugin_with_store():
    """Test plugin with SQLite store."""
    print("\n=== Testing Plugin with Store ===")
    
    try:
        from mcp_server.storage.sqlite_store import SQLiteStore
        from mcp_server.plugins.python_plugin import Plugin
        
        # Create in-memory store
        store = SQLiteStore(":memory:")
        
        # Override environment for in-memory Qdrant
        os.environ["QDRANT_HOST"] = ":memory:"
        
        # Create plugin - this should use semantic features if enabled
        plugin = Plugin(sqlite_store=store)
        
        # Check semantic features
        if hasattr(plugin, '_enable_semantic'):
            print(f"✓ Plugin has semantic features: {plugin._enable_semantic}")
            if hasattr(plugin, '_semantic_indexer'):
                print(f"✓ Semantic indexer present: {plugin._semantic_indexer is not None}")
        else:
            print("✗ Plugin doesn't have semantic attributes")
        
        return plugin
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_full_workflow(plugin):
    """Test full indexing and search workflow."""
    print("\n=== Testing Full Workflow ===")
    
    if not plugin:
        print("✗ No plugin to test")
        return
    
    try:
        import tempfile
        
        # Create test file
        test_code = '''
def calculate_fibonacci(n):
    """Calculate the nth Fibonacci number recursively."""
    if n <= 1:
        return n
    return calculate_fibonacci(n - 1) + calculate_fibonacci(n - 2)

class MathHelper:
    """Helper class for mathematical operations."""
    
    def factorial(self, n):
        """Calculate factorial of n."""
        if n == 0:
            return 1
        return n * self.factorial(n - 1)
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_code)
            test_file = f.name
        
        print(f"Created test file: {test_file}")
        
        # Index the file
        shard = plugin.indexFile(test_file, test_code)
        print(f"✓ Indexed file with {len(shard['symbols'])} symbols")
        
        # Test semantic search
        print("\nTesting semantic search...")
        queries = [
            "recursive function to calculate mathematical series",
            "class for math operations",
            "factorial calculation"
        ]
        
        for query in queries:
            print(f"\nQuery: '{query}'")
            
            # Semantic search
            results = list(plugin.search(query, {"semantic": True, "limit": 3}))
            print(f"  Semantic results: {len(results)}")
            for r in results[:2]:
                print(f"    - {r['file']} line {r['line']}")
            
            # Traditional search for comparison
            results = list(plugin.search(query, {"semantic": False, "limit": 3}))
            print(f"  Traditional results: {len(results)}")
        
        # Cleanup
        os.unlink(test_file)
        
    except Exception as e:
        print(f"✗ Error in workflow: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Run all tests."""
    print("=== Semantic Search Debug Test ===\n")
    
    test_environment()
    
    Plugin = test_plugin_loading()
    
    if test_semantic_indexer():
        print("\n✓ Direct semantic indexing works!")
    
    plugin = test_plugin_with_store()
    
    test_full_workflow(plugin)
    
    print("\n=== Test Complete ===")


if __name__ == "__main__":
    main()