#!/usr/bin/env python3
"""
Demonstrate centralized index management
"""

import os
import sys
from pathlib import Path
from mcp_server.core.path_utils import PathUtils

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_server.storage.index_manager import IndexManager
from mcp_server.storage.sqlite_store import SQLiteStore
import subprocess
import tempfile


def demo_centralized_storage():
    """Demonstrate centralized index storage functionality."""
    
    print("=== Centralized Index Management Demo ===\n")
    
    # Create index manager with centralized storage
    manager = IndexManager(storage_strategy="centralized")
    print(f"✓ Index storage location: {manager.storage_path}")
    
    # Get repository info
    repo_path = Path("PathUtils.get_workspace_root()")
    repo_info = manager.get_repository_info(repo_path)
    print(f"\n✓ Repository Information:")
    print(f"  Name: {repo_info['name']}")
    print(f"  Branch: {repo_info['branch']}")
    print(f"  Commit: {repo_info['commit_short']}")
    
    # Get repository hash
    repo_hash = manager.get_repository_hash(repo_path)
    print(f"\n✓ Repository Hash: {repo_hash}")
    
    # Check for existing indexes
    print(f"\n✓ Checking for existing indexes...")
    current_index = manager.get_current_index_path(repo_path)
    if current_index:
        print(f"  Found current index: {current_index}")
    else:
        print(f"  No current index found")
    
    # List all indexes
    all_indexes = manager.list_indexes(repo_path)
    print(f"\n✓ All indexes for this repository:")
    if all_indexes:
        for idx in all_indexes:
            print(f"  - {Path(idx['path']).name}")
            print(f"    Branch: {idx.get('branch', 'unknown')}")
            print(f"    Commit: {idx.get('commit_short', 'unknown')}")
            print(f"    Created: {idx.get('created_at', 'unknown')}")
            print(f"    Size: {idx.get('size', 0) / 1024 / 1024:.2f} MB")
    else:
        print("  No indexes found")
    
    # Demonstrate creating a new index
    print(f"\n✓ Creating a new index...")
    
    # Use existing index if available
    source_db = repo_path / ".mcp-index" / "code_index.db"
    if source_db.exists():
        new_index_path = manager.create_index(
            repo_path,
            source_db,
            metadata={
                "indexed_files": 161,
                "demo": True
            }
        )
        print(f"  Created: {new_index_path}")
        print(f"  Metadata saved: {new_index_path.with_suffix('.metadata.json')}")
    else:
        print("  No source database found at .mcp-index/code_index.db")
    
    # Show retention policy
    print(f"\n✓ Retention Policy:")
    print(f"  Max indexes per branch: {manager.retention_policy['max_indexes_per_branch']}")
    print(f"  Max age (days): {manager.retention_policy['max_age_days']}")
    print(f"  Keep tagged commits: {manager.retention_policy['keep_tagged_commits']}")
    
    print("\n=== Demo Complete ===")


def demo_storage_strategies():
    """Compare different storage strategies."""
    
    print("\n=== Storage Strategy Comparison ===\n")
    
    repo_path = Path("PathUtils.get_workspace_root()")
    
    # Test each strategy
    strategies = ["centralized", "portable", "inline"]
    
    for strategy in strategies:
        print(f"\n--- Strategy: {strategy} ---")
        manager = IndexManager(storage_strategy=strategy)
        
        # Get index path for current repo
        index_path = manager.get_index_path(repo_path)
        print(f"Index would be stored at: {index_path}")
        
        # Check if parent directory exists
        if index_path.parent.exists():
            print(f"Storage directory exists: ✓")
        else:
            print(f"Storage directory exists: ✗ (would be created)")


if __name__ == "__main__":
    demo_centralized_storage()
    demo_storage_strategies()