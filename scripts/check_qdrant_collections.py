#!/usr/bin/env python3
"""
Check what collections exist in the Qdrant databases and sample their content.
"""

import sys
import logging
from pathlib import Path
from mcp_server.core.path_utils import PathUtils

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from qdrant_client import QdrantClient

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_qdrant_collections():
    """Check what collections exist and sample their content."""
    print("=" * 60)
    print("QDRANT COLLECTIONS INSPECTION")
    print("=" * 60)
    
    qdrant_path = "PathUtils.get_workspace_root()/.indexes/qdrant/main.qdrant"
    
    # Remove stale lock if it exists
    lock_file = Path(qdrant_path) / ".lock"
    if lock_file.exists():
        try:
            lock_file.unlink()
            print(f"Removed stale lock: {lock_file}")
        except OSError:
            pass
    
    try:
        client = QdrantClient(path=qdrant_path)
        print(f"✅ Connected to Qdrant: {qdrant_path}")
        
        # Get all collections
        collections = client.get_collections()
        print(f"\nFound {len(collections.collections)} collections:")
        
        for i, collection in enumerate(collections.collections):
            print(f"\n{i+1}. Collection: {collection.name}")
            
            # Get collection info
            try:
                info = client.get_collection(collection.name)
                print(f"   Vectors: {info.vectors_count}")
                print(f"   Points: {info.points_count}")
                
                # Sample some data
                sample = client.scroll(
                    collection_name=collection.name,
                    limit=10,
                    with_payload=True
                )
                
                if sample[0]:
                    print(f"   Sample files:")
                    for j, point in enumerate(sample[0][:5]):
                        file_path = (
                            point.payload.get("file") or
                            point.payload.get("relative_path") or
                            point.payload.get("filepath") or
                            "unknown"
                        )
                        print(f"     {j+1}. {file_path}")
                        
                    # Check for workspace patterns
                    workspace_files = []
                    for point in sample[0]:
                        file_path = (
                            point.payload.get("file") or
                            point.payload.get("relative_path") or
                            point.payload.get("filepath") or
                            ""
                        )
                        if file_path and "/workspaces/code-index-mcp" in file_path.lower():
                            workspace_files.append(file_path)
                    
                    if workspace_files:
                        print(f"   ✅ Contains workspace files: {len(workspace_files)}")
                    else:
                        print(f"   ❌ No workspace files found in sample")
                else:
                    print(f"   Empty collection")
                    
            except Exception as e:
                print(f"   Error getting info: {e}")
        
        print(f"\n" + "=" * 60)
        print("COLLECTIONS INSPECTION COMPLETE")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Failed to connect to Qdrant: {e}")

if __name__ == "__main__":
    check_qdrant_collections()