#!/usr/bin/env python3
"""
Test semantic search connectivity and database mapping.
This will verify that we can connect to the correct Qdrant database and collection.
"""

import sys
import logging
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_server.utils.semantic_discovery import SemanticDatabaseDiscovery
from mcp_server.utils.semantic_indexer import SemanticIndexer

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_semantic_connectivity():
    """Test semantic database connectivity and collection mapping."""
    print("=" * 60)
    print("SEMANTIC SEARCH CONNECTIVITY TEST")
    print("=" * 60)
    
    # Test 1: Discovery
    print("\n1. Testing Semantic Database Discovery...")
    workspace_root = Path.cwd()
    print(f"Workspace: {workspace_root}")
    
    discovery = SemanticDatabaseDiscovery(workspace_root)
    print(f"Discovered Qdrant paths: {discovery.qdrant_paths}")
    
    # Test 2: Repository Identification
    print("\n2. Repository Identification...")
    repo_id = discovery.get_repository_identifier()
    print(f"Repository ID: {repo_id}")
    
    # Test 3: Collection Discovery
    print("\n3. Finding Codebase Collections...")
    matches = discovery.find_codebase_collections()
    print(f"Found {len(matches)} matching collections:")
    
    for i, (qdrant_path, collection_name, metadata) in enumerate(matches):
        print(f"  {i+1}. {collection_name}")
        print(f"     Path: {qdrant_path}")
        print(f"     Score: {metadata['match_score']:.2f}")
        print(f"     Sample files: {metadata['sample_files'][:3]}")
        print()
    
    # Test 4: Best Collection
    print("4. Best Collection Selection...")
    best_collection = discovery.get_best_collection()
    if best_collection:
        qdrant_path, collection_name = best_collection
        print(f"Selected: {collection_name}")
        print(f"Path: {qdrant_path}")
    else:
        print("No suitable collection found")
        
    # Test 5: Default Configuration
    print("\n5. Default Configuration...")
    default_path, default_collection = discovery.get_default_collection_config()
    print(f"Default path: {default_path}")
    print(f"Default collection: {default_collection}")
    print(f"Path exists: {Path(default_path).exists()}")
    
    # Test 6: Direct Connection Test
    print("\n6. Direct Semantic Indexer Test...")
    if best_collection:
        qdrant_path, collection_name = best_collection
        try:
            semantic_indexer = SemanticIndexer(
                qdrant_path=qdrant_path,
                collection=collection_name
            )
            print(f"✅ Successfully connected to {collection_name}")
            
            # Test a simple search
            print("\n7. Testing Search Functionality...")
            try:
                results = semantic_indexer.search("function", limit=5)
                print(f"Search results: {len(results)} found")
                for i, result in enumerate(results[:3]):
                    print(f"  {i+1}. {result.get('relative_path', 'unknown')} (score: {result.get('score', 0):.3f})")
            except Exception as e:
                print(f"❌ Search failed: {e}")
                
        except Exception as e:
            print(f"❌ Failed to connect: {e}")
    else:
        print("❌ No collection to test")
    
    # Test 7: Collection Summary
    print("\n8. Collection Summary...")
    summary = discovery.get_collection_summary()
    print(f"Summary:")
    print(f"  Repository ID: {summary['repository_id']}")
    print(f"  Collections found: {len(summary['collections'])}")
    print(f"  Recommendations: {summary['recommendations']}")
    
    print("\n" + "=" * 60)
    print("CONNECTIVITY TEST COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    test_semantic_connectivity()