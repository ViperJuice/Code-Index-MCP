#!/usr/bin/env python3
"""
Migrate existing indexes to centralized storage
"""

import os
import sys
import shutil
from pathlib import Path
import json
from datetime import datetime

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_server.storage.index_manager import IndexManager
from mcp_server.utils.index_discovery import IndexDiscovery


def migrate_repository_index(repo_path: Path, dry_run: bool = False):
    """
    Migrate a repository's index to centralized storage.
    
    Args:
        repo_path: Path to the repository
        dry_run: If True, only show what would be done
    """
    print(f"\n🔍 Checking repository: {repo_path}")
    
    # Check for existing .mcp-index directory
    local_index_dir = repo_path / ".mcp-index"
    if not local_index_dir.exists():
        print("  ❌ No .mcp-index directory found")
        return False
    
    # Find database files
    db_files = list(local_index_dir.glob("*.db"))
    if not db_files:
        print("  ❌ No database files found")
        return False
    
    print(f"  ✓ Found {len(db_files)} database file(s)")
    
    # Create index manager with centralized storage
    manager = IndexManager(storage_strategy="centralized")
    
    for db_file in db_files:
        print(f"\n  📄 Processing: {db_file.name}")
        
        # Check if it's a valid SQLite database
        import sqlite3
        try:
            conn = sqlite3.connect(str(db_file))
            conn.execute("SELECT 1 FROM sqlite_master LIMIT 1")
            conn.close()
        except Exception as e:
            print(f"    ⚠️  Invalid database: {e}")
            continue
        
        if dry_run:
            # Show what would be done
            target_path = manager.get_index_path(repo_path)
            print(f"    Would copy to: {target_path}")
            print(f"    Would create metadata at: {target_path.with_suffix('.metadata.json')}")
        else:
            # Actually migrate
            try:
                # Look for existing metadata
                metadata = {}
                metadata_files = [
                    db_file.with_suffix(".metadata.json"),
                    local_index_dir / ".index_metadata.json",
                    local_index_dir / "metadata.json"
                ]
                
                for metadata_file in metadata_files:
                    if metadata_file.exists():
                        with open(metadata_file) as f:
                            metadata = json.load(f)
                        break
                
                # Create index in centralized storage
                new_path = manager.create_index(repo_path, db_file, metadata)
                print(f"    ✓ Migrated to: {new_path}")
                
                # Update .mcp-index.json if it exists
                config_file = repo_path / ".mcp-index.json"
                if config_file.exists():
                    with open(config_file) as f:
                        config = json.load(f)
                    
                    # Update to centralized storage
                    config["storage_strategy"] = "centralized"
                    config["storage_path"] = str(manager.storage_path)
                    
                    with open(config_file, "w") as f:
                        json.dump(config, f, indent=2)
                    
                    print(f"    ✓ Updated .mcp-index.json to use centralized storage")
                
            except Exception as e:
                print(f"    ❌ Migration failed: {e}")
                return False
    
    if not dry_run:
        print(f"\n  🎯 Migration complete!")
        print(f"  💡 You can now remove the .mcp-index directory if desired")
        print(f"     rm -rf {local_index_dir}")
    
    return True


def main():
    """Main migration function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate MCP indexes to centralized storage")
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Repository path to migrate (default: current directory)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Search for and migrate all repositories under the given path"
    )
    
    args = parser.parse_args()
    
    root_path = Path(args.path).resolve()
    
    print("=== MCP Index Migration Tool ===")
    print(f"Mode: {'Dry run' if args.dry_run else 'Live migration'}")
    
    if args.all:
        # Find all repositories with .mcp-index directories
        repos_found = 0
        repos_migrated = 0
        
        for mcp_index_dir in root_path.rglob(".mcp-index"):
            if mcp_index_dir.is_dir():
                repo_path = mcp_index_dir.parent
                repos_found += 1
                
                if migrate_repository_index(repo_path, dry_run=args.dry_run):
                    repos_migrated += 1
        
        print(f"\n=== Summary ===")
        print(f"Repositories found: {repos_found}")
        print(f"Repositories migrated: {repos_migrated}")
        
    else:
        # Migrate single repository
        success = migrate_repository_index(root_path, dry_run=args.dry_run)
        
        if not success and not args.dry_run:
            sys.exit(1)
    
    if args.dry_run:
        print("\n💡 This was a dry run. Use without --dry-run to perform actual migration.")


if __name__ == "__main__":
    main()