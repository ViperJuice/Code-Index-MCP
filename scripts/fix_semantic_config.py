#!/usr/bin/env python3
"""
Fix semantic search configuration to use the correct collection.
"""

import sys
from pathlib import Path
from mcp_server.core.path_utils import PathUtils

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_server.utils.semantic_indexer import SemanticIndexer
from qdrant_client import QdrantClient

def test_semantic_search():
    """Test semantic search with the correct collection."""
    print("=" * 60)
    print("TESTING SEMANTIC SEARCH WITH CORRECT COLLECTION")
    print("=" * 60)
    
    qdrant_path = "PathUtils.get_workspace_root()/.indexes/qdrant/main.qdrant"
    collection_name = "code-embeddings"  # The working collection
    
    print(f"Qdrant path: {qdrant_path}")
    print(f"Collection: {collection_name}")
    
    # Remove stale lock if it exists
    lock_file = Path(qdrant_path) / ".lock"
    if lock_file.exists():
        try:
            lock_file.unlink()
        except OSError:
            pass
    
    try:
        # Initialize semantic indexer with correct collection
        semantic_indexer = SemanticIndexer(
            qdrant_path=qdrant_path,
            collection=collection_name
        )
        print("✅ Connected to semantic indexer")
        
        # Test searches
        test_queries = [
            "function search",
            "class Dispatcher",
            "semantic indexer",
            "plugin factory",
            "MCP server"
        ]
        
        print("\nTesting semantic search queries:")
        for query in test_queries:
            print(f"\nQuery: '{query}'")
            try:
                results = semantic_indexer.search(query, limit=3)
                if results:
                    print(f"  ✅ Found {len(results)} results:")
                    for i, result in enumerate(results[:3]):
                        file_path = (
                            result.get("file") or
                            result.get("relative_path") or
                            result.get("filepath") or
                            "unknown"
                        )
                        score = result.get("score", 0)
                        print(f"     {i+1}. {file_path} (score: {score:.3f})")
                else:
                    print("  ❌ No results found")
            except Exception as e:
                print(f"  ❌ Search failed: {e}")
                
        # Test with direct Qdrant client to verify
        print("\nDirect Qdrant test:")
        client = QdrantClient(path=qdrant_path)
        
        # Get a sample embedding to use as query
        sample = client.scroll(
            collection_name=collection_name,
            limit=1,
            with_vectors=True
        )
        
        if sample[0]:
            query_vector = sample[0][0].vector
            search_results = client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=3
            )
            
            if search_results:
                print("✅ Direct Qdrant search works!")
                for i, result in enumerate(search_results):
                    file_path = (
                        result.payload.get("file") or
                        result.payload.get("relative_path") or
                        result.payload.get("filepath") or
                        "unknown"
                    )
                    print(f"   {i+1}. {file_path} (score: {result.score:.3f})")
                    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
    
    # Provide configuration recommendation
    print("\n📝 CONFIGURATION FIX NEEDED:")
    print("The semantic discovery should be updated to use 'code-embeddings' collection")
    print("instead of trying to use the empty 'codebase-f7b49f5d0ae0' collection.")
    print("\nThe issue is in the semantic discovery logic that needs to check")
    print("which collections actually contain data for the current codebase.")

if __name__ == "__main__":
    test_semantic_search()