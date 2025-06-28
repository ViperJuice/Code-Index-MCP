#!/usr/bin/env python3
"""Create BM25 index for current repository."""

import os
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from mcp_server.indexer.bm25_indexer import BM25Indexer

def main():
    """Create BM25 index."""
    repo_path = Path.cwd()
    
    # Create indexer
    indexer = BM25Indexer(repo_path)
    
    # Index the repository
    print(f"Indexing {repo_path}...")
    stats = indexer.index_directory(force=True)
    
    print(f"\nIndexing complete:")
    print(f"  Files indexed: {stats['indexed_files']}")
    print(f"  Files skipped: {stats['skipped_files']}")
    print(f"  Errors: {stats['errors']}")
    
    # Move to central location
    import shutil
    import hashlib
    import subprocess
    
    # Get repo ID
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True
        )
        remote_url = result.stdout.strip()
        repo_id = hashlib.sha256(remote_url.encode()).hexdigest()[:12]
    except:
        repo_id = hashlib.sha256(str(repo_path.absolute()).encode()).hexdigest()[:12]
    
    print(f"\nRepo ID: {repo_id}")
    
    # Move index
    central_path = Path.home() / ".mcp/indexes" / repo_id
    central_path.mkdir(parents=True, exist_ok=True)
    
    local_index = repo_path / ".mcp-index" / "bm25_index.db"
    if local_index.exists():
        target = central_path / "current_index.db"
        print(f"Moving index to {target}...")
        shutil.copy2(local_index, target)
        
        # Update symlink
        current_link = central_path / "current.db"
        if current_link.exists():
            current_link.unlink()
        current_link.symlink_to("current_index.db")
        
        print("Index moved successfully!")
    else:
        print(f"ERROR: No index found at {local_index}")

if __name__ == "__main__":
    main()