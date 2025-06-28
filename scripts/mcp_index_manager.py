#!/usr/bin/env python3
"""
MCP Index Manager CLI - Manage centralized MCP indexes
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime
import json

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_server.storage.index_manager import IndexManager
from mcp_server.utils.index_discovery import IndexDiscovery


def cmd_list(args):
    """List all indexes."""
    manager = IndexManager(storage_strategy=args.strategy)
    
    repo_path = Path(args.repo) if args.repo else None
    indexes = manager.list_indexes(repo_path)
    
    if not indexes:
        print("No indexes found.")
        return
    
    # Group by repository
    by_repo = {}
    for idx in indexes:
        repo_name = idx.get('repository', 'unknown')
        if repo_name not in by_repo:
            by_repo[repo_name] = []
        by_repo[repo_name].append(idx)
    
    # Display
    for repo_name, repo_indexes in by_repo.items():
        print(f"\n📦 {repo_name}")
        
        # Sort by creation date
        repo_indexes.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        for idx in repo_indexes:
            path = Path(idx['path'])
            print(f"  📄 {path.name}")
            print(f"     Branch: {idx.get('branch', 'unknown')}")
            print(f"     Commit: {idx.get('commit_short', 'unknown')}")
            print(f"     Created: {idx.get('created_at', 'unknown')}")
            print(f"     Size: {idx.get('size', 0) / 1024 / 1024:.2f} MB")
            
            # Check if this is the current index
            if path.parent.exists():
                current_link = path.parent / "current"
                if current_link.exists() and current_link.resolve() == path:
                    print(f"     Status: ✓ CURRENT")


def cmd_clean(args):
    """Clean up old indexes."""
    manager = IndexManager(storage_strategy=args.strategy)
    
    if args.repo:
        # Clean specific repository
        repo_path = Path(args.repo).resolve()
        removed = manager.cleanup_old_indexes(repo_path)
        
        if removed:
            print(f"Removed {len(removed)} old index(es):")
            for path in removed:
                print(f"  ❌ {path.name}")
        else:
            print("No indexes needed cleaning.")
    else:
        # Clean all repositories
        if manager.storage_strategy != "centralized":
            print("Global cleanup only available for centralized storage.")
            return
            
        total_removed = 0
        for repo_dir in manager.storage_path.iterdir():
            if repo_dir.is_dir():
                # Try to find corresponding repository
                # This is a limitation - we can't easily map back to repos
                print(f"\n🗑️  Cleaning {repo_dir.name}...")
                
                # For now, just count the files
                before = len(list(repo_dir.glob("*.db")))
                print(f"   Before: {before} indexes")
                
        print(f"\n💡 For proper cleanup, run this command from each repository.")


def cmd_info(args):
    """Show information about current index configuration."""
    print("=== MCP Index Configuration ===\n")
    
    # Check environment variables
    print("Environment Variables:")
    print(f"  MCP_INDEX_STRATEGY: {os.getenv('MCP_INDEX_STRATEGY', 'not set')}")
    print(f"  MCP_INDEX_STORAGE_PATH: {os.getenv('MCP_INDEX_STORAGE_PATH', 'not set')}")
    print(f"  MCP_INDEX_AUTO_CLEANUP: {os.getenv('MCP_INDEX_AUTO_CLEANUP', 'not set')}")
    
    # Check current directory configuration
    cwd = Path.cwd()
    discovery = IndexDiscovery(cwd)
    config = discovery.get_index_config()
    
    if config:
        print(f"\n.mcp-index.json Configuration:")
        print(f"  Storage Strategy: {config.get('storage_strategy', 'inline')}")
        print(f"  Storage Path: {config.get('storage_path', 'default')}")
        print(f"  Auto Download: {config.get('auto_download', True)}")
        print(f"  Auto Upload: {config.get('auto_upload', True)}")
        
        retention = config.get('retention_policy', {})
        if retention:
            print(f"\nRetention Policy:")
            print(f"  Max per branch: {retention.get('max_indexes_per_branch', 3)}")
            print(f"  Max age days: {retention.get('max_age_days', 30)}")
            print(f"  Keep tagged: {retention.get('keep_tagged_commits', True)}")
    else:
        print(f"\nNo .mcp-index.json found in {cwd}")
    
    # Show current index
    manager = IndexManager(storage_strategy=args.strategy)
    current = manager.get_current_index_path(cwd)
    
    if current:
        print(f"\nCurrent Index:")
        print(f"  Path: {current}")
        print(f"  Size: {current.stat().st_size / 1024 / 1024:.2f} MB")
        
        # Load metadata if available
        metadata_path = current.with_suffix(".metadata.json")
        if metadata_path.exists():
            with open(metadata_path) as f:
                metadata = json.load(f)
            print(f"  Files: {metadata.get('indexed_files', 'unknown')}")
            print(f"  Created: {metadata.get('created_at', 'unknown')}")
    else:
        print(f"\nNo current index found")


def cmd_switch(args):
    """Switch to a different index version."""
    manager = IndexManager(storage_strategy="centralized")
    
    if manager.storage_strategy != "centralized":
        print("Index switching only available for centralized storage.")
        return
    
    repo_path = Path.cwd()
    repo_hash = manager.get_repository_hash(repo_path)
    repo_dir = manager.storage_path / repo_hash
    
    if not repo_dir.exists():
        print("No indexes found for this repository.")
        return
    
    # Find the target index
    target = None
    for db_file in repo_dir.glob("*.db"):
        if args.target in db_file.name:
            target = db_file
            break
    
    if not target:
        print(f"No index matching '{args.target}' found.")
        print("\nAvailable indexes:")
        for db_file in repo_dir.glob("*.db"):
            print(f"  - {db_file.name}")
        return
    
    # Update current symlink
    current_link = repo_dir / "current"
    if current_link.exists():
        current_link.unlink()
    
    current_link.symlink_to(target.name)
    print(f"✓ Switched to: {target.name}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="MCP Index Manager - Manage centralized MCP indexes"
    )
    
    parser.add_argument(
        "--strategy",
        choices=["centralized", "portable", "inline"],
        default="centralized",
        help="Storage strategy to use (default: centralized)"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List all indexes")
    list_parser.add_argument(
        "--repo",
        help="Filter by repository path"
    )
    
    # Clean command
    clean_parser = subparsers.add_parser("clean", help="Clean up old indexes")
    clean_parser.add_argument(
        "--repo",
        help="Clean specific repository (default: all)"
    )
    
    # Info command
    info_parser = subparsers.add_parser("info", help="Show current configuration")
    
    # Switch command
    switch_parser = subparsers.add_parser("switch", help="Switch to different index version")
    switch_parser.add_argument(
        "target",
        help="Index name or partial match"
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Execute command
    if args.command == "list":
        cmd_list(args)
    elif args.command == "clean":
        cmd_clean(args)
    elif args.command == "info":
        cmd_info(args)
    elif args.command == "switch":
        cmd_switch(args)


if __name__ == "__main__":
    main()