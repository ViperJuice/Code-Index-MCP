#!/usr/bin/env python3
"""Test semantic search with file-based Qdrant."""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Use file mode for testing
os.environ["QDRANT_USE_SERVER"] = "false"

# Clean up any existing locks
lock_file = Path(".indexes/qdrant/main.qdrant/.lock")
if lock_file.exists():
    print(f"Removing lock file: {lock_file}")
    lock_file.unlink()

def test_semantic_indexer():
    """Test semantic indexer with file-based Qdrant."""
    
    print("TESTING SEMANTIC SEARCH WITH FILE-BASED QDRANT")
    print("=" * 80)
    
    # Check for API key
    if not os.environ.get("VOYAGE_API_KEY") and not os.environ.get("VOYAGE_AI_API_KEY"):
        print("\n⚠️  No Voyage AI API key found")
        print("Semantic search requires a Voyage AI API key.")
        print("\nTo get an API key:")
        print("1. Visit https://www.voyageai.com/")
        print("2. Sign up for an account")
        print("3. Set the key: export VOYAGE_AI_API_KEY=your_key_here")
        return
    
    try:
        from mcp_server.utils.semantic_indexer import SemanticIndexer
        
        print("\nInitializing semantic indexer...")
        
        # Use a specific path for testing
        qdrant_path = ".indexes/qdrant/test.qdrant"
        indexer = SemanticIndexer(
            collection="test-collection",
            qdrant_path=qdrant_path
        )
        
        print("✓ Semantic indexer initialized")
        print(f"  Using Qdrant at: {qdrant_path}")
        
        # Test indexing some sample code
        print("\n📝 Indexing sample code...")
        
        sample_code = '''
def calculate_fibonacci(n):
    """Calculate the nth Fibonacci number."""
    if n <= 1:
        return n
    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)

class DataProcessor:
    """Process and analyze data."""
    def __init__(self):
        self.data = []
    
    def process(self, item):
        """Process a single data item."""
        # TODO: Implement processing logic
        pass
'''
        
        # Index the sample
        indexer.index_code(
            code=sample_code,
            file_path="sample.py",
            language="python"
        )
        
        print("✓ Sample code indexed")
        
        # Test search
        print("\n🔍 Testing semantic search...")
        
        test_queries = [
            "fibonacci calculation",
            "data processing class",
            "TODO comment",
            "recursive function"
        ]
        
        for query in test_queries:
            print(f"\nSearching for: '{query}'")
            results = indexer.search(query, limit=3)
            
            if results:
                print(f"  Found {len(results)} results")
                for i, result in enumerate(results):
                    score = result.get('score', 0)
                    snippet = result.get('code', '')[:80].replace('\n', ' ')
                    print(f"  {i+1}. Score: {score:.3f}")
                    print(f"     {snippet}...")
            else:
                print("  No results found")
        
        print("\n✅ Semantic search is working!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


def test_enhanced_dispatcher_semantic():
    """Test enhanced dispatcher with semantic search."""
    
    print("\n\nTESTING ENHANCED DISPATCHER WITH SEMANTIC SEARCH")
    print("=" * 80)
    
    if not os.environ.get("VOYAGE_API_KEY") and not os.environ.get("VOYAGE_AI_API_KEY"):
        print("⚠️  Skipping - no API key")
        return
    
    try:
        from mcp_server.storage.sqlite_store import SQLiteStore
        from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
        
        # Use a test database
        db_path = ".indexes/f7b49f5d0ae0/current.db"
        
        if not Path(db_path).exists():
            print("❌ Test database not found")
            return
        
        store = SQLiteStore(db_path)
        
        # Create dispatcher with semantic search enabled
        dispatcher = EnhancedDispatcher(
            sqlite_store=store,
            semantic_search_enabled=True,
            lazy_load=True
        )
        
        print("✓ Dispatcher created with semantic search")
        
        # Test semantic search
        results = list(dispatcher.search("calculate fibonacci recursively", semantic=True, limit=5))
        
        if results:
            print(f"\n✓ Semantic search returned {len(results)} results")
            for i, result in enumerate(results[:3]):
                if isinstance(result, dict):
                    file_path = result.get('file', 'Unknown')
                else:
                    file_path = getattr(result, 'file_path', 'Unknown')
                print(f"  {i+1}. {file_path}")
        else:
            print("\n⚠️ No semantic search results")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_semantic_indexer()
    test_enhanced_dispatcher_semantic()