#!/usr/bin/env python3
"""
Migrate all test indexes to central storage location
"""

import os
import sys
import shutil
import hashlib
from pathlib import Path
import json
from datetime import datetime
from mcp_server.core.path_utils import PathUtils

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_repo_hash_from_name(repo_name):
    """Generate a consistent hash for test repositories based on name."""
    # Use a consistent naming scheme for test repos
    fake_url = f"https://github.com/test/{repo_name}.git"
    return hashlib.sha256(fake_url.encode()).hexdigest()[:12]


def migrate_test_indexes():
    """Migrate all test indexes to central storage."""
    test_indexes_dir = Path("PathUtils.get_workspace_root()/test_indexes")
    central_path = Path.home() / ".mcp" / "indexes"
    
    if not test_indexes_dir.exists():
        print("No test_indexes directory found")
        return
    
    # Find all test repositories
    for repo_dir in test_indexes_dir.iterdir():
        if not repo_dir.is_dir():
            continue
            
        print(f"\n📦 Processing test repo: {repo_dir.name}")
        
        # Find all .db files in this test repo
        db_files = list(repo_dir.glob("*.db"))
        if not db_files:
            print(f"  ⚠️  No database files found")
            continue
            
        # Generate consistent repo hash
        repo_hash = get_repo_hash_from_name(repo_dir.name)
        repo_central_dir = central_path / repo_hash
        repo_central_dir.mkdir(parents=True, exist_ok=True)
        
        # Move each database
        for db_file in db_files:
            # Use a generic name for test indexes
            if "bm25" in db_file.name or "simple" in db_file.name:
                target_name = "test_bm25.db"
            else:
                target_name = "test_main.db"
                
            target_path = repo_central_dir / target_name
            
            print(f"  📄 {db_file.name} -> {target_path}")
            shutil.copy2(db_file, target_path)
            
            # Create metadata
            metadata = {
                "repository_name": repo_dir.name,
                "original_path": str(db_file),
                "test_repository": True,
                "moved_at": datetime.now().isoformat()
            }
            
            metadata_path = target_path.with_suffix(".metadata.json")
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)
                
        # Create current symlink pointing to main db
        current_link = repo_central_dir / "current.db"
        if current_link.exists():
            current_link.unlink()
            
        if (repo_central_dir / "test_main.db").exists():
            current_link.symlink_to("test_main.db")
        elif (repo_central_dir / "test_bm25.db").exists():
            current_link.symlink_to("test_bm25.db")
            
        print(f"  ✓ Migrated to {repo_central_dir}")


def cleanup_old_locations():
    """Remove the .mcp-index directory since we're using central storage only."""
    mcp_index_dir = Path("PathUtils.get_workspace_root()/.mcp-index")
    
    if mcp_index_dir.exists():
        print(f"\n🗑️  Removing {mcp_index_dir}")
        print("  Contents:")
        for item in mcp_index_dir.iterdir():
            print(f"    - {item.name}")
        
        # Actually remove it
        shutil.rmtree(mcp_index_dir)
        print("  ✓ Removed")


def main():
    print("=== Migrating All Indexes to Central Storage ===")
    
    # First migrate test indexes
    migrate_test_indexes()
    
    # Then cleanup old locations
    cleanup_old_locations()
    
    print("\n✅ Migration complete!")
    print(f"All indexes are now in: ~/.mcp/indexes/")


if __name__ == "__main__":
    main()