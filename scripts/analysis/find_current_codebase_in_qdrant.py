#!/usr/bin/env python3
"""
Find files from the current codebase in Qdrant collections.
"""

from pathlib import Path
from qdrant_client import QdrantClient
from mcp_server.core.path_utils import PathUtils

def find_current_codebase():
    """Find current codebase files in Qdrant."""
    print("=" * 60)
    print("SEARCHING FOR CURRENT CODEBASE FILES IN QDRANT")
    print("=" * 60)
    
    qdrant_path = "PathUtils.get_workspace_root()/.indexes/qdrant/main.qdrant"
    
    # Remove lock file
    lock_file = Path(qdrant_path) / ".lock"
    if lock_file.exists():
        try:
            lock_file.unlink()
        except:
            pass
    
    try:
        client = QdrantClient(path=qdrant_path)
        collections = client.get_collections()
        
        # Patterns to identify current codebase
        patterns = [
            "mcp_server",
            "dispatcher",
            "semantic_indexer",
            "plugin_factory",
            "comprehensive_semantic_analysis",
            "PathUtils.get_workspace_root()/mcp_server",
            "PathUtils.get_workspace_root()/scripts"
        ]
        
        print(f"Searching for patterns: {patterns[:3]}...\n")
        
        for collection in collections.collections:
            try:
                info = client.get_collection(collection.name)
                if info.points_count == 0:
                    continue
                
                print(f"\nCollection: {collection.name} ({info.points_count} points)")
                
                # Scroll through all points to find matches
                offset = None
                matches = []
                total_checked = 0
                
                while True:
                    batch = client.scroll(
                        collection_name=collection.name,
                        limit=100,
                        offset=offset,
                        with_payload=True,
                        with_vectors=False
                    )
                    
                    if not batch[0]:
                        break
                        
                    for point in batch[0]:
                        total_checked += 1
                        file_path = point.payload.get("file_path", "")
                        
                        # Check all payload values
                        for key, value in point.payload.items():
                            if isinstance(value, str):
                                for pattern in patterns:
                                    if pattern.lower() in value.lower():
                                        matches.append({
                                            "id": point.id,
                                            "file_path": file_path or value,
                                            "matched_key": key,
                                            "matched_pattern": pattern
                                        })
                                        break
                    
                    offset = batch[1]
                    if offset is None:
                        break
                
                if matches:
                    print(f"  ✅ Found {len(matches)} matches out of {total_checked} checked")
                    # Show unique file paths
                    unique_files = list(set(m["file_path"] for m in matches))[:5]
                    for i, file_path in enumerate(unique_files):
                        print(f"     {i+1}. {file_path}")
                    if len(unique_files) > 5:
                        print(f"     ... and {len(unique_files) - 5} more")
                else:
                    print(f"  ❌ No matches found (checked {total_checked} points)")
                    
            except Exception as e:
                print(f"  Error: {e}")
        
        print("\n" + "=" * 60)
        print("SEARCH COMPLETE")
        print("=" * 60)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    find_current_codebase()