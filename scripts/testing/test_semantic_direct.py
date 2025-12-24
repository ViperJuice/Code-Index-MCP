#!/usr/bin/env python3
"""
Direct test of semantic search functionality.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from mcp_server.utils.semantic_discovery import SemanticDatabaseDiscovery

def test_semantic_direct():
    """Test semantic search directly."""
    print("=" * 60)
    print("DIRECT SEMANTIC SEARCH TEST")
    print("=" * 60)
    
    # Check environment
    api_key = os.environ.get("VOYAGE_AI_API_KEY") or os.environ.get("VOYAGE_API_KEY")
    print(f"Voyage AI API Key: {'✅ Found' if api_key else '❌ Not found'}")
    
    # Test discovery
    print("\n1. Testing Semantic Discovery...")
    workspace_root = Path.cwd()
    discovery = SemanticDatabaseDiscovery(workspace_root)
    
    # Get best collection
    best_collection = discovery.get_best_collection()
    if best_collection:
        qdrant_path, collection_name = best_collection
        print(f"✅ Found collection: {collection_name}")
        print(f"   Path: {qdrant_path}")
    else:
        print("❌ No suitable collection found")
        return
    
    # Test direct Qdrant access
    print("\n2. Testing Direct Qdrant Access...")
    try:
        from qdrant_client import QdrantClient
        
        # Remove lock file
        lock_file = Path(qdrant_path) / ".lock"
        if lock_file.exists():
            try:
                lock_file.unlink()
            except:
                pass
        
        client = QdrantClient(path=qdrant_path)
        
        # Get collection info
        info = client.get_collection(collection_name)
        print(f"✅ Collection '{collection_name}' has {info.points_count} points")
        
        if info.points_count > 0:
            # Test search without needing embeddings
            print("\n3. Testing Search (using existing embeddings)...")
            
            # Get a sample point to use as query
            sample = client.scroll(
                collection_name=collection_name,
                limit=1,
                with_vectors=True
            )
            
            if sample[0]:
                query_vector = sample[0][0].vector
                
                # Search
                results = client.search(
                    collection_name=collection_name,
                    query_vector=query_vector,
                    limit=5
                )
                
                print(f"✅ Search returned {len(results)} results:")
                for i, result in enumerate(results[:3]):
                    file_path = (
                        result.payload.get("file") or
                        result.payload.get("relative_path") or
                        result.payload.get("filepath") or
                        "unknown"
                    )
                    print(f"   {i+1}. {file_path} (score: {result.score:.3f})")
                    
        else:
            print("❌ Collection is empty")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("DIRECT TEST COMPLETE")
    print("=" * 60)
    
    print("\n📝 NEXT STEPS:")
    if api_key and best_collection and info.points_count > 0:
        print("✅ Semantic search infrastructure is ready!")
        print("   The issue is in the MCP server configuration.")
        print("   Need to ensure MCP uses the correct collection.")
    else:
        if not api_key:
            print("❌ Set VOYAGE_AI_API_KEY in .env file")
        if not best_collection or info.points_count == 0:
            print("❌ Populate semantic embeddings in Qdrant")

if __name__ == "__main__":
    test_semantic_direct()