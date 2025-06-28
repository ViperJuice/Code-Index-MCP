#!/usr/bin/env python3
"""
Find which Qdrant collection contains embeddings for the current codebase.
"""

import sys
from pathlib import Path
from mcp_server.core.path_utils import PathUtils

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from qdrant_client import QdrantClient

def find_codebase_embeddings():
    """Find which collection has current codebase embeddings."""
    print("=" * 60)
    print("SEARCHING FOR CURRENT CODEBASE EMBEDDINGS")
    print("=" * 60)
    
    qdrant_path = "PathUtils.get_workspace_root()/.indexes/qdrant/main.qdrant"
    
    # Remove stale lock if it exists
    lock_file = Path(qdrant_path) / ".lock"
    if lock_file.exists():
        try:
            lock_file.unlink()
        except OSError:
            pass
    
    try:
        client = QdrantClient(path=qdrant_path)
        collections = client.get_collections()
        
        codebase_patterns = [
            "mcp_server",
            "code-index-mcp", 
            "code_index_mcp",
            "/workspaces/code-index-mcp",
            "dispatcher",
            "semantic_indexer",
            "plugin_factory"
        ]
        
        print(f"Searching patterns: {codebase_patterns[:3]}...\n")
        
        results = {}
        
        for collection in collections.collections:
            try:
                info = client.get_collection(collection.name)
                if info.points_count == 0:
                    continue
                    
                # Sample more points to get better coverage
                sample_size = min(info.points_count, 200)
                sample = client.scroll(
                    collection_name=collection.name,
                    limit=sample_size,
                    with_payload=True
                )
                
                if not sample[0]:
                    continue
                
                matches = 0
                matched_files = []
                
                for point in sample[0]:
                    file_path = (
                        point.payload.get("file") or
                        point.payload.get("relative_path") or
                        point.payload.get("filepath") or
                        point.payload.get("path") or
                        ""
                    ).lower()
                    
                    # Check all payload keys
                    for key, value in point.payload.items():
                        if isinstance(value, str):
                            value_lower = value.lower()
                            if any(pattern in value_lower for pattern in codebase_patterns):
                                matches += 1
                                if file_path and len(matched_files) < 5:
                                    matched_files.append(file_path)
                                break
                
                if matches > 0:
                    match_rate = (matches / sample_size) * 100
                    results[collection.name] = {
                        "matches": matches,
                        "sample_size": sample_size,
                        "match_rate": match_rate,
                        "total_points": info.points_count,
                        "matched_files": matched_files
                    }
                    
            except Exception as e:
                print(f"Error checking {collection.name}: {e}")
        
        # Display results
        if results:
            print("Collections containing current codebase files:\n")
            sorted_results = sorted(results.items(), key=lambda x: x[1]["match_rate"], reverse=True)
            
            for collection_name, data in sorted_results:
                print(f"Collection: {collection_name}")
                print(f"  Total points: {data['total_points']}")
                print(f"  Matches: {data['matches']}/{data['sample_size']} ({data['match_rate']:.1f}%)")
                if data['matched_files']:
                    print(f"  Sample matched files:")
                    for i, file in enumerate(data['matched_files'][:3]):
                        print(f"    {i+1}. {file}")
                print()
                
            # Recommend the best collection
            best_collection = sorted_results[0][0]
            print(f"🎯 RECOMMENDATION: Use collection '{best_collection}'")
            print(f"   This collection has the highest match rate for current codebase files.")
        else:
            print("❌ No collections found containing current codebase files!")
            print("   All embeddings may be using different file paths or the index is empty.")
            
            # Try to inspect payload structure
            print("\nInspecting payload structure of code-embeddings collection...")
            try:
                sample = client.scroll(
                    collection_name="code-embeddings",
                    limit=3,
                    with_payload=True
                )
                
                if sample[0]:
                    print("Sample payload keys:")
                    for i, point in enumerate(sample[0][:3]):
                        print(f"\nPoint {i+1}:")
                        for key, value in point.payload.items():
                            print(f"  {key}: {value if len(str(value)) < 100 else str(value)[:100] + '...'}")
                            
            except Exception as e:
                print(f"Could not inspect code-embeddings: {e}")
                
    except Exception as e:
        print(f"❌ Failed to connect to Qdrant: {e}")
        
    print("\n" + "=" * 60)
    print("SEARCH COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    find_codebase_embeddings()