#!/usr/bin/env python3
"""
Verify that embeddings exist in the Qdrant collections.
"""

import sys
from pathlib import Path
from mcp_server.core.path_utils import PathUtils

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from qdrant_client import QdrantClient

def verify_embeddings():
    """Verify embeddings exist in all collections."""
    print("=" * 60)
    print("VERIFYING EMBEDDINGS IN QDRANT COLLECTIONS")
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
        
        print(f"Found {len(collections.collections)} collections:\n")
        
        for collection in collections.collections:
            try:
                info = client.get_collection(collection.name)
                print(f"Collection: {collection.name}")
                print(f"  Points: {info.points_count}")
                
                if info.points_count > 0:
                    # Get a sample point to verify it has embeddings
                    sample = client.scroll(
                        collection_name=collection.name,
                        limit=1,
                        with_vectors=True
                    )
                    
                    if sample[0]:
                        point = sample[0][0]
                        vector_size = len(point.vector) if point.vector else 0
                        print(f"  Vector dimension: {vector_size}")
                        print(f"  ✅ Has embeddings: YES")
                    else:
                        print(f"  ❌ Has embeddings: NO (empty)")
                else:
                    print(f"  ❌ Has embeddings: NO (0 points)")
                    
                print()
                
            except Exception as e:
                print(f"  Error checking collection: {e}\n")
        
        # Check specifically for the current codebase collection
        print("Checking current codebase collection:")
        print(f"Collection name: codebase-f7b49f5d0ae0")
        
        try:
            info = client.get_collection("codebase-f7b49f5d0ae0")
            if info.points_count == 0:
                print("❌ Current codebase collection is EMPTY!")
                print("   This is why semantic search is not working.")
                
                # Check if embeddings exist in code-embeddings collection
                try:
                    code_info = client.get_collection("code-embeddings")
                    if code_info.points_count > 0:
                        print("\n✅ But 'code-embeddings' collection has data!")
                        print(f"   Points: {code_info.points_count}")
                        
                        # Sample to see what's in there
                        sample = client.scroll(
                            collection_name="code-embeddings",
                            limit=5,
                            with_payload=True
                        )
                        
                        if sample[0]:
                            print("   Sample files:")
                            for i, point in enumerate(sample[0][:5]):
                                file_path = (
                                    point.payload.get("file") or
                                    point.payload.get("relative_path") or
                                    point.payload.get("filepath") or
                                    "unknown"
                                )
                                print(f"     {i+1}. {file_path}")
                                
                            # Check if any match current workspace
                            workspace_count = 0
                            check_sample = client.scroll(
                                collection_name="code-embeddings",
                                limit=100,
                                with_payload=True
                            )
                            
                            for point in check_sample[0]:
                                file_path = (
                                    point.payload.get("file") or
                                    point.payload.get("relative_path") or
                                    point.payload.get("filepath") or
                                    ""
                                )
                                if "mcp_server" in file_path.lower() or "code-index-mcp" in file_path.lower():
                                    workspace_count += 1
                            
                            if workspace_count > 0:
                                print(f"\n   ✅ Found {workspace_count} files from current workspace!")
                                print("   → We should use 'code-embeddings' collection instead!")
                            
                except Exception as e:
                    print(f"Could not check code-embeddings: {e}")
                    
        except Exception as e:
            print(f"Error checking current codebase collection: {e}")
            
    except Exception as e:
        print(f"❌ Failed to connect to Qdrant: {e}")
        
    print("\n" + "=" * 60)
    print("VERIFICATION COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    verify_embeddings()