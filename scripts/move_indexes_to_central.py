#!/usr/bin/env python3
"""
Move existing MCP indexes to the central storage location (~/.mcp/indexes).

This is a one-time migration tool to move indexes from local .mcp-index directories
to the central storage location. After running this, the MCP server will automatically
use the central location.
"""

import os
import shutil
import hashlib
import subprocess
from pathlib import Path
import json
from datetime import datetime


def get_repo_identifier(repo_path):
    """Generate a unique identifier for a repository."""
    try:
        # Try to get remote URL
        result = subprocess.run(
            ["git", "-C", str(repo_path), "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True
        )
        remote_url = result.stdout.strip()
        # Create hash from URL
        return hashlib.sha256(remote_url.encode()).hexdigest()[:12]
    except:
        # Fallback to path hash
        return hashlib.sha256(str(repo_path.absolute()).encode()).hexdigest()[:12]


def get_git_info(repo_path):
    """Get current git branch and commit."""
    info = {"branch": "main", "commit": "unknown"}
    
    try:
        # Get branch
        result = subprocess.run(
            ["git", "-C", str(repo_path), "branch", "--show-current"],
            capture_output=True,
            text=True,
            check=True
        )
        if result.stdout.strip():
            info["branch"] = result.stdout.strip()
        
        # Get commit
        result = subprocess.run(
            ["git", "-C", str(repo_path), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True
        )
        info["commit"] = result.stdout.strip()[:7]
    except:
        pass
    
    return info


def move_index_to_central(repo_path, dry_run=False):
    """Move an index from repository to central location."""
    repo_path = Path(repo_path).absolute()
    # Central storage location - default to local .indexes
    mcp_root = Path(__file__).parent.parent
    default_central_path = mcp_root / ".indexes"
    central_path = Path(os.getenv("MCP_INDEX_STORAGE_PATH", str(default_central_path)))
    
    # Check for existing index
    local_index = repo_path / ".mcp-index" / "code_index.db"
    if not local_index.exists():
        print(f"❌ No index found at {local_index}")
        print(f"   Create an index first with: mcp-index index")
        return False
    
    # Create central directory structure
    repo_id = get_repo_identifier(repo_path)
    repo_central_dir = central_path / repo_id
    
    if not dry_run:
        repo_central_dir.mkdir(parents=True, exist_ok=True)
    
    # Get git info for naming
    git_info = get_git_info(repo_path)
    central_db_name = f"{git_info['branch']}_{git_info['commit']}.db"
    central_db_path = repo_central_dir / central_db_name
    
    print(f"\n📦 Repository: {repo_path.name}")
    print(f"   Repo ID: {repo_id}")
    print(f"   Source: {local_index}")
    print(f"   Target: {central_db_path}")
    
    if dry_run:
        print("   [DRY RUN] Would copy index")
    else:
        # Copy the index
        shutil.copy2(local_index, central_db_path)
        print("   ✓ Index copied")
        
        # Create metadata file
        metadata = {
            "repository_path": str(repo_path),
            "repository_name": repo_path.name,
            "branch": git_info["branch"],
            "commit": git_info["commit"],
            "moved_at": datetime.now().isoformat(),
            "original_path": str(local_index)
        }
        
        metadata_path = central_db_path.with_suffix(".metadata.json")
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
        
        # Create a "current" symlink
        current_link = repo_central_dir / "current.db"
        if current_link.exists():
            current_link.unlink()
        current_link.symlink_to(central_db_name)
        
        print("   ✓ Created metadata and current symlink")
        print(f"\n✅ Index moved successfully!")
        print(f"   The MCP server will now use the central index automatically.")
        print(f"   You can safely delete {local_index} if desired.")
    
    return True


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Move MCP indexes to central storage location",
        epilog="After migration, indexes are stored at ~/.mcp/indexes/"
    )
    parser.add_argument("repo", nargs="?", default=".", help="Repository path (default: current directory)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    
    args = parser.parse_args()
    
    print("=== MCP Index Migration Tool ===")
    print("Moving indexes to central storage location...")
    
    success = move_index_to_central(args.repo, args.dry_run)
    
    if args.dry_run and success:
        print("\n💡 This was a dry run. Use without --dry-run to perform actual migration.")


if __name__ == "__main__":
    main()