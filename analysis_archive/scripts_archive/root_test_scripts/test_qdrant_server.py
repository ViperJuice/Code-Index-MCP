#!/usr/bin/env python3
"""Test Qdrant server connectivity and semantic search."""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set environment to use server mode
os.environ["QDRANT_USE_SERVER"] = "true"
os.environ["QDRANT_URL"] = "http://localhost:6333"


def test_qdrant_connection():
    """Test basic Qdrant connectivity."""
    try:
        from qdrant_client import QdrantClient
        
        print("Testing Qdrant connection...")
        client = QdrantClient(url="http://localhost:6333", timeout=5)
        
        # Test connection
        collections = client.get_collections()
        print(f"✓ Connected to Qdrant server")
        print(f"  Collections: {len(collections.collections)}")
        
        for collection in collections.collections:
            info = client.get_collection(collection.name)
            print(f"  - {collection.name}: {info.vectors_count} vectors")
        
        return True
        
    except Exception as e:
        print(f"✗ Failed to connect to Qdrant: {e}")
        print("\nMake sure Qdrant server is running:")
        print("  docker-compose -f docker-compose.qdrant.yml up -d")
        return False


def test_semantic_search():
    """Test semantic search functionality."""
    if not test_qdrant_connection():
        return
    
    # Check for Voyage API key
    if not os.environ.get("VOYAGE_API_KEY") and not os.environ.get("VOYAGE_AI_API_KEY"):
        print("\n⚠️  No Voyage AI API key found")
        print("Set VOYAGE_AI_API_KEY environment variable to test semantic search")
        return
    
    try:
        from mcp_server.utils.semantic_indexer import SemanticIndexer
        
        print("\nTesting semantic indexer...")
        indexer = SemanticIndexer()
        
        # Test search
        results = indexer.search("function definition", limit=5)
        print(f"✓ Semantic search returned {len(results)} results")
        
        if results:
            print("\nSample results:")
            for i, result in enumerate(results[:3]):
                print(f"  {i+1}. {result.get('file_path', 'Unknown')}")
                print(f"     Score: {result.get('score', 0):.3f}")
        
    except Exception as e:
        print(f"✗ Semantic search error: {e}")


if __name__ == "__main__":
    test_semantic_search()
