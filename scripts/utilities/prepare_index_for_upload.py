#!/usr/bin/env python3
"""
Prepare index files for GitHub artifact upload.

This script stages index files from the new .indexes/ directory structure
for upload to GitHub artifacts.
"""

import os
import sys
import shutil
import hashlib
import subprocess
import argparse
import tempfile
from pathlib import Path
from typing import Optional, Tuple

def get_repo_hash() -> str:
    """Get the repository hash based on git remote URL."""
    try:
        result = subprocess.run(
            ['git', 'remote', 'get-url', 'origin'],
            capture_output=True,
            text=True,
            check=True
        )
        remote_url = result.stdout.strip()
        return hashlib.sha256(remote_url.encode()).hexdigest()[:12]
    except:
        raise Exception("Could not determine repository hash from git remote")

def find_current_index(indexes_dir: Path, repo_hash: str) -> Optional[Path]:
    """Find the current index database for the repository."""
    repo_dir = indexes_dir / repo_hash
    
    if not repo_dir.exists():
        return None
    
    # Check for current.db symlink
    current_db = repo_dir / 'current.db'
    if current_db.exists() and current_db.is_symlink():
        # Follow symlink to actual file
        actual_db = current_db.resolve()
        if actual_db.exists():
            return repo_dir
    
    # Fallback: look for any .db file
    db_files = list(repo_dir.glob('*.db'))
    if db_files:
        return repo_dir
    
    return None

def prepare_for_upload(index_dir: Path, staging_dir: Path) -> Tuple[bool, str]:
    """
    Prepare index files for upload by staging them in a directory.
    
    Returns:
        Tuple of (success, message)
    """
    try:
        # Clear staging directory
        if staging_dir.exists():
            shutil.rmtree(staging_dir)
        staging_dir.mkdir(parents=True)
        
        # Find the current.db symlink
        current_db = index_dir / 'current.db'
        if current_db.exists():
            # Copy the actual database file as code_index.db
            actual_db = current_db.resolve()
            dest_db = staging_dir / 'code_index.db'
            print(f"  Copying {actual_db.name} -> code_index.db")
            shutil.copy2(actual_db, dest_db)
        else:
            # Look for any .db file
            db_files = list(index_dir.glob('*.db'))
            if db_files:
                # Use the most recent one
                latest_db = max(db_files, key=lambda p: p.stat().st_mtime)
                dest_db = staging_dir / 'code_index.db'
                print(f"  Copying {latest_db.name} -> code_index.db")
                shutil.copy2(latest_db, dest_db)
            else:
                return False, "No database file found"
        
        # Copy metadata file if it exists
        metadata_files = list(index_dir.glob('*.metadata.json'))
        if metadata_files:
            # Find the one matching our database
            for metadata_file in metadata_files:
                dest_metadata = staging_dir / '.index_metadata.json'
                print(f"  Copying {metadata_file.name} -> .index_metadata.json")
                shutil.copy2(metadata_file, dest_metadata)
                break
        
        # Copy vector index if it exists
        vector_index = index_dir / 'vector_index.qdrant'
        if vector_index.exists():
            dest_vector = staging_dir / 'vector_index.qdrant'
            print(f"  Copying vector_index.qdrant/")
            shutil.copytree(vector_index, dest_vector)
        
        return True, f"Staged {len(list(staging_dir.iterdir()))} items"
        
    except Exception as e:
        return False, f"Error: {str(e)}"

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Prepare index files for GitHub artifact upload'
    )
    parser.add_argument(
        '--indexes-dir',
        type=Path,
        help='Path to .indexes directory (default: auto-detect)'
    )
    parser.add_argument(
        '--staging-dir',
        type=Path,
        default=Path('.mcp-index-staging'),
        help='Staging directory for upload (default: .mcp-index-staging)'
    )
    parser.add_argument(
        '--repo-hash',
        help='Repository hash (default: auto-detect from git)'
    )
    
    args = parser.parse_args()
    
    # Determine indexes directory
    if args.indexes_dir:
        indexes_dir = args.indexes_dir
    else:
        # Default to .indexes in MCP server directory
        mcp_server_dir = Path(__file__).parent.parent.parent
        indexes_dir = mcp_server_dir / '.indexes'
    
    if not indexes_dir.exists():
        print(f"❌ Indexes directory not found: {indexes_dir}")
        sys.exit(1)
    
    # Get repository hash
    try:
        repo_hash = args.repo_hash or get_repo_hash()
        print(f"🔑 Repository hash: {repo_hash}")
    except Exception as e:
        print(f"❌ {e}")
        sys.exit(1)
    
    # Find current index
    index_dir = find_current_index(indexes_dir, repo_hash)
    if not index_dir:
        print(f"❌ No index found for repository in {indexes_dir}/{repo_hash}/")
        sys.exit(1)
    
    print(f"📂 Found index at: {index_dir}")
    
    # Prepare for upload
    print(f"\n📦 Staging files to: {args.staging_dir}")
    success, message = prepare_for_upload(index_dir, args.staging_dir)
    
    if success:
        print(f"✅ {message}")
        print(f"\nNext steps:")
        print(f"1. cd {args.staging_dir}")
        print(f"2. python ../index-artifact-upload-v2.py")
    else:
        print(f"❌ {message}")
        sys.exit(1)

if __name__ == '__main__':
    main()