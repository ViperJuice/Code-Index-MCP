#!/usr/bin/env python3
"""
Inspect the payload structure of embeddings in Qdrant.
"""

from pathlib import Path
from qdrant_client import QdrantClient
import json
from mcp_server.core.path_utils import PathUtils

def inspect_payloads():
    """Inspect payload structure in Qdrant collections."""
    print("=" * 60)
    print("INSPECTING QDRANT PAYLOAD STRUCTURE")
    print("=" * 60)
    
    qdrant_path = "PathUtils.get_workspace_root()/.indexes/qdrant/main.qdrant"
    collection_name = "code-embeddings"
    
    # Remove lock file
    lock_file = Path(qdrant_path) / ".lock"
    if lock_file.exists():
        try:
            lock_file.unlink()
        except:
            pass
    
    try:
        client = QdrantClient(path=qdrant_path)
        
        # Get sample points
        sample = client.scroll(
            collection_name=collection_name,
            limit=10,
            with_payload=True,
            with_vectors=False  # Don't need vectors for inspection
        )
        
        if sample[0]:
            print(f"Found {len(sample[0])} points in '{collection_name}'")
            print("\nSample payloads:\n")
            
            for i, point in enumerate(sample[0][:5]):
                print(f"Point {i+1} (ID: {point.id}):")
                print(json.dumps(point.payload, indent=2))
                print("-" * 40)
                
            # Analyze payload keys
            all_keys = set()
            for point in sample[0]:
                all_keys.update(point.payload.keys())
                
            print(f"\nAll payload keys found: {sorted(all_keys)}")
            
            # Check for file path patterns
            file_patterns = 0
            for point in sample[0]:
                for key, value in point.payload.items():
                    if isinstance(value, str) and ("mcp_server" in value or ".py" in value):
                        file_patterns += 1
                        print(f"\nFound file pattern in key '{key}': {value[:100]}...")
                        break
                        
            print(f"\nPoints with recognizable file patterns: {file_patterns}/{len(sample[0])}")
            
        else:
            print(f"Collection '{collection_name}' is empty")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    inspect_payloads()