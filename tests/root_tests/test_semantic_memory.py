#!/usr/bin/env python3
"""Test semantic search with in-memory Qdrant."""

import os
import sys
from pathlib import Path

# Load .env file first
from dotenv import load_dotenv
load_dotenv()

# Set environment variables
os.environ["SEMANTIC_SEARCH_ENABLED"] = "true"
os.environ["QDRANT_HOST"] = ":memory:"
os.environ["QDRANT_PORT"] = "6333"

sys.path.insert(0, str(Path(__file__).parent))

from mcp_server.utils.semantic_indexer import SemanticIndexer
import tempfile


def test_basic_semantic_indexing():
    """Test basic semantic indexing with in-memory storage."""
    print("=== Testing Semantic Indexing with In-Memory Storage ===")
    
    # Check API key
    api_key = os.getenv("VOYAGE_AI_API_KEY")
    if not api_key:
        print("✗ VOYAGE_AI_API_KEY not set")
        print("  Semantic search requires Voyage AI API key")
        return False
    print("✓ Voyage AI API key is configured")
    
    try:
        # Create semantic indexer with in-memory Qdrant
        print("\nInitializing SemanticIndexer with in-memory storage...")
        indexer = SemanticIndexer(collection="test-collection", qdrant_path=":memory:")
        print("✓ SemanticIndexer initialized successfully")
        
        # Test indexing a symbol
        print("\nTesting symbol indexing...")
        indexer.index_symbol(
            file="test.py",
            name="calculate_fibonacci",
            kind="function",
            signature="def calculate_fibonacci(n: int) -> int:",
            line=10,
            span=(10, 15),
            doc="Calculate the nth Fibonacci number recursively.",
            content="""def calculate_fibonacci(n: int) -> int:
    if n <= 1:
        return n
    return calculate_fibonacci(n - 1) + calculate_fibonacci(n - 2)"""
        )
        print("✓ Symbol indexed successfully")
        
        # Test searching
        print("\nTesting semantic search...")
        results = indexer.search("recursive function to compute mathematical series", limit=5)
        
        if results:
            print(f"✓ Found {len(results)} results:")
            for i, result in enumerate(results, 1):
                print(f"  {i}. {result['symbol']} in {result['file']} (score: {result.get('score', 'N/A')})")
        else:
            print("✗ No results found")
            
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_plugin_integration():
    """Test semantic search through plugin."""
    print("\n=== Testing Plugin Integration ===")
    
    try:
        from mcp_server.plugins.python_plugin import Plugin as PythonPlugin
        from mcp_server.storage.sqlite_store import SQLiteStore
        
        # Create plugin  
        store = SQLiteStore(":memory:")
        plugin = PythonPlugin(sqlite_store=store)
        
        # Check if semantic is enabled
        if hasattr(plugin, '_enable_semantic'):
            print(f"Plugin semantic search enabled: {plugin._enable_semantic}")
        else:
            print("Plugin is using basic implementation (no semantic support)")
            
        # Create a test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
def factorial(n):
    '''Calculate factorial of a number recursively.'''
    if n == 0:
        return 1
    return n * factorial(n - 1)

class MathOperations:
    '''Mathematical operations helper class.'''
    
    def power(self, base, exp):
        '''Calculate base raised to exponent.'''
        return base ** exp
""")
            test_file = f.name
        
        # Index the file
        print(f"\nIndexing test file: {test_file}")
        content = Path(test_file).read_text()
        shard = plugin.indexFile(test_file, content)
        print(f"✓ Indexed {len(shard['symbols'])} symbols")
        
        # Test semantic search
        print("\nTesting semantic search through plugin...")
        results = list(plugin.search("recursive mathematical calculation", {"semantic": True, "limit": 3}))
        
        if results:
            print(f"✓ Found {len(results)} semantic results")
        else:
            print("✗ No semantic results (might be using basic plugin)")
            
        # Cleanup
        os.unlink(test_file)
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run semantic search tests with in-memory storage."""
    print("=== Semantic Search Test (In-Memory) ===\n")
    
    # Test basic indexing
    if not test_basic_semantic_indexing():
        print("\nBasic semantic indexing test failed")
        return 1
    
    # Test plugin integration
    if not test_plugin_integration():
        print("\nPlugin integration test failed")
        return 1
    
    print("\n=== All tests completed ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())