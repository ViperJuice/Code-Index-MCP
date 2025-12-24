#!/usr/bin/env python3
"""
Search all Qdrant locations for MCP codebase embeddings.
"""

from pathlib import Path
from qdrant_client import QdrantClient
import os
from mcp_server.core.path_utils import PathUtils

def find_mcp_embeddings():
    """Search for MCP codebase embeddings in all Qdrant locations."""
    print("=" * 60)
    print("SEARCHING FOR MCP CODEBASE EMBEDDINGS")
    print("=" * 60)
    
    # Check all possible Qdrant locations
    qdrant_locations = [
        "PathUtils.get_workspace_root()/.indexes/qdrant/main.qdrant",
        "PathUtils.get_workspace_root()/vector_index.qdrant",
        "PathUtils.get_workspace_root()/.mcp-index/vector_index.qdrant",
    ]
    
    # Add any Qdrant databases in data directory
    data_path = Path("PathUtils.get_workspace_root()/data")
    if data_path.exists():
        for root, dirs, files in os.walk(data_path):
            if "qdrant" in root:
                qdrant_locations.append(root)
    
    mcp_patterns = [
        "mcp_server",
        "dispatcher.py",
        "semantic_indexer",
        "plugin_factory",
        "enhanced_dispatcher",
        "PathUtils.get_workspace_root()/mcp_server",
        "PathUtils.get_workspace_root() / mcp_server"
    ]
    
    for qdrant_path in qdrant_locations:
        if not Path(qdrant_path).exists():
            continue
            
        print(f"\nChecking: {qdrant_path}")
        
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
            
            print(f"  Found {len(collections.collections)} collections")
            
            for collection in collections.collections:
                try:
                    info = client.get_collection(collection.name)
                    if info.points_count == 0:
                        continue
                    
                    # Sample points to check content
                    sample = client.scroll(
                        collection_name=collection.name,
                        limit=50,
                        with_payload=True,
                        with_vectors=False
                    )
                    
                    if not sample[0]:
                        continue
                    
                    # Check for MCP patterns
                    matches = 0
                    matched_files = []
                    
                    for point in sample[0]:
                        payload_str = str(point.payload).lower()
                        
                        for pattern in mcp_patterns:
                            if pattern.lower() in payload_str:
                                matches += 1
                                # Extract file path from payload
                                file_path = None
                                for key in ["file_path", "file", "relative_path", "filepath", "path"]:
                                    if key in point.payload:
                                        file_path = point.payload[key]
                                        break
                                
                                if file_path and file_path not in matched_files:
                                    matched_files.append(file_path)
                                break
                    
                    if matches > 0:
                        print(f"\n  ✅ Collection '{collection.name}' ({info.points_count} points)")
                        print(f"     Found {matches} MCP-related entries in sample")
                        print(f"     Sample files:")
                        for i, file in enumerate(matched_files[:3]):
                            print(f"       {i+1}. {file}")
                            
                except Exception as e:
                    print(f"  Error checking {collection.name}: {e}")
                    
        except Exception as e:
            print(f"  Error connecting: {e}")
    
    # Also check if there are any index-specific Qdrant databases
    print("\n\nChecking index-specific Qdrant databases...")
    indexes_path = Path("PathUtils.get_workspace_root()/.indexes")
    if indexes_path.exists():
        for index_dir in indexes_path.iterdir():
            if index_dir.is_dir() and index_dir.name != "qdrant":
                # Check if this index has its own Qdrant
                qdrant_path = index_dir / "vector_index.qdrant"
                if qdrant_path.exists():
                    print(f"\nFound index-specific Qdrant: {qdrant_path}")
                    # Could check this too if needed
    
    print("\n" + "=" * 60)
    print("SEARCH COMPLETE")
    print("=" * 60)
    
    print("\n📝 RECOMMENDATIONS:")
    print("1. The current MCP codebase embeddings are missing")
    print("2. The 'codebase-f7b49f5d0ae0' collection is empty and needs to be populated")
    print("3. The 'code-embeddings' collection only has test repository data")
    print("\nTo fix semantic search:")
    print("- Option 1: Populate the codebase-f7b49f5d0ae0 collection with current codebase")
    print("- Option 2: Create a new collection with proper embeddings")
    print("- Option 3: Disable semantic search and use SQL-only for now")

if __name__ == "__main__":
    find_mcp_embeddings()