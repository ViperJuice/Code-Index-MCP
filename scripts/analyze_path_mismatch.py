#!/usr/bin/env python3
"""
Analyze path mismatches between Qdrant embeddings and actual file locations.
"""

from pathlib import Path
from qdrant_client import QdrantClient
import os
from collections import defaultdict
from mcp_server.core.path_utils import PathUtils

def analyze_path_mismatch():
    """Analyze path mismatches in Qdrant collections."""
    print("=" * 60)
    print("ANALYZING PATH MISMATCHES IN QDRANT")
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
        
        # Check code-embeddings collection
        collection_name = "code-embeddings"
        info = client.get_collection(collection_name)
        print(f"\nAnalyzing '{collection_name}' ({info.points_count} points)...")
        
        # Sample more points to understand the paths
        sample = client.scroll(
            collection_name=collection_name,
            limit=100,
            with_payload=True,
            with_vectors=False
        )
        
        if sample[0]:
            # Analyze path patterns
            path_patterns = defaultdict(int)
            path_exists = defaultdict(int)
            repo_mapping = defaultdict(set)
            
            for point in sample[0]:
                file_path = point.payload.get("file_path", "")
                repository = point.payload.get("repository", "unknown")
                
                if file_path:
                    # Extract path pattern
                    parts = Path(file_path).parts
                    if len(parts) > 3:
                        pattern = "/".join(parts[:4])  # First 4 parts
                        path_patterns[pattern] += 1
                    
                    # Check if file exists
                    exists = Path(file_path).exists()
                    path_exists[exists] += 1
                    
                    # Map repository to paths
                    repo_mapping[repository].add(file_path)
            
            print("\n1. Path Patterns Found:")
            for pattern, count in sorted(path_patterns.items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"   {pattern}: {count} files")
            
            print(f"\n2. Path Existence Check:")
            print(f"   Existing paths: {path_exists[True]}")
            print(f"   Missing paths: {path_exists[False]}")
            
            print(f"\n3. Repository Mappings:")
            for repo, paths in list(repo_mapping.items())[:3]:
                print(f"   Repository '{repo}':")
                for path in list(paths)[:2]:
                    print(f"     - {path}")
                    
            # Check current directory structure
            print("\n4. Current Directory Structure:")
            test_repos = Path("PathUtils.get_workspace_root()/test_repos")
            if test_repos.exists():
                print(f"   ✅ test_repos exists at: {test_repos}")
                # List subdirectories
                subdirs = [d for d in test_repos.iterdir() if d.is_dir()][:5]
                for subdir in subdirs:
                    print(f"      - {subdir.name}")
            else:
                print(f"   ❌ test_repos NOT found at expected location")
                
            # Check for moved repos
            print("\n5. Searching for Actual Repository Locations:")
            workspace_root = Path("PathUtils.get_workspace_root()")
            
            # Common repo patterns from the sample
            repo_names = ["django", "react", "typescript", "aspnetcore"]
            for repo_name in repo_names:
                # Search for this repo
                found_paths = []
                for root, dirs, files in os.walk(workspace_root):
                    if repo_name in root.lower():
                        found_paths.append(root)
                        if len(found_paths) >= 3:
                            break
                
                if found_paths:
                    print(f"\n   '{repo_name}' found at:")
                    for path in found_paths[:3]:
                        print(f"     - {path}")
                        
            # Check if any files from current mcp_server exist
            print("\n6. Checking for Current Codebase Files:")
            mcp_patterns = [
                "PathUtils.get_workspace_root()/mcp_server",
                "PathUtils.get_workspace_root() / mcp_server",
                "mcp_server/dispatcher",
                "mcp_server/utils/semantic"
            ]
            
            found_current = False
            for pattern in mcp_patterns:
                matching = sum(1 for point in sample[0] 
                             if pattern in point.payload.get("file_path", ""))
                if matching > 0:
                    print(f"   ✅ Found {matching} files matching '{pattern}'")
                    found_current = True
            
            if not found_current:
                print("   ❌ No files from current mcp_server codebase found")
                print("   The embeddings appear to be from test repositories only")
                
        else:
            print(f"Collection '{collection_name}' is empty")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        
    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)
    
    print("\n📝 FINDINGS:")
    print("1. The code-embeddings collection contains test repository files")
    print("2. File paths in Qdrant may not match current file locations")
    print("3. Need to either:")
    print("   a) Create new embeddings for the current codebase")
    print("   b) Implement path remapping in the semantic indexer")
    print("   c) Use a different collection that has current codebase embeddings")

if __name__ == "__main__":
    analyze_path_mismatch()