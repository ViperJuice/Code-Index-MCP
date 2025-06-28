#!/usr/bin/env python3
"""
Ensure all test repositories are properly indexed in the centralized location.
"""

import os
import sys
import subprocess
import hashlib
from pathlib import Path
import json
from typing import Dict, List, Optional
from mcp_server.core.path_utils import PathUtils

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.indexer.bm25_indexer import BM25Indexer


def get_repo_hash(repo_path: Path) -> str:
    """Get repository hash for centralized storage."""
    try:
        # Get git remote URL
        result = subprocess.run(
            ['git', '-C', str(repo_path), 'remote', 'get-url', 'origin'],
            capture_output=True, text=True, check=True
        )
        remote_url = result.stdout.strip()
    except:
        # If no remote, use absolute path
        remote_url = str(repo_path.resolve())
    
    # Generate hash
    return hashlib.sha256(remote_url.encode()).hexdigest()[:12]


def find_test_repositories() -> List[Dict[str, str]]:
    """Find all test repositories."""
    test_repos_dir = Path("PathUtils.get_workspace_root()/test_repos")
    repos = []
    
    if not test_repos_dir.exists():
        print(f"Test repos directory not found: {test_repos_dir}")
        return repos
    
    # Find all .git directories
    for git_dir in test_repos_dir.rglob(".git"):
        if git_dir.is_dir():
            repo_path = git_dir.parent
            repo_name = f"{repo_path.parent.name}/{repo_path.name}"
            
            repos.append({
                "name": repo_name,
                "path": str(repo_path),
                "hash": get_repo_hash(repo_path)
            })
    
    return repos


def check_index_exists(repo_info: Dict[str, str]) -> bool:
    """Check if repository is already indexed in central location."""
    central_dir = Path.home() / ".mcp" / "indexes" / repo_info["hash"]
    
    if central_dir.exists():
        # Check for current.db symlink
        current_db = central_dir / "current.db"
        if current_db.exists():
            # Verify it's a valid database
            try:
                conn = sqlite3.connect(str(current_db))
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM documents")
                count = cursor.fetchone()[0]
                conn.close()
                return count > 0
            except:
                pass
    
    return False


def index_repository(repo_info: Dict[str, str]) -> bool:
    """Index a repository using the standard indexing process."""
    print(f"\nIndexing {repo_info['name']}...")
    
    try:
        # Use the mcp_cli.py script to index
        cmd = [
            "python", "PathUtils.get_workspace_root()/scripts/cli/mcp_cli.py",
            "index",
            "--path", repo_info["path"],
            "--verbose"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"  ✓ Successfully indexed {repo_info['name']}")
            return True
        else:
            print(f"  ✗ Failed to index {repo_info['name']}: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"  ✗ Error indexing {repo_info['name']}: {e}")
        return False


def main():
    """Main function to ensure all test repos are indexed."""
    print("Checking test repository indexes...")
    
    # Find all test repositories
    repos = find_test_repositories()
    print(f"\nFound {len(repos)} test repositories")
    
    # Check which need indexing
    need_indexing = []
    already_indexed = []
    
    for repo in repos:
        if check_index_exists(repo):
            already_indexed.append(repo)
        else:
            need_indexing.append(repo)
    
    print(f"\nAlready indexed: {len(already_indexed)}")
    print(f"Need indexing: {len(need_indexing)}")
    
    if need_indexing:
        print("\nRepositories needing indexing:")
        for repo in need_indexing:
            print(f"  - {repo['name']} ({repo['hash']})")
        
        # Index missing repositories
        response = input("\nIndex missing repositories? (y/n): ")
        if response.lower() == 'y':
            success_count = 0
            for repo in need_indexing:
                if index_repository(repo):
                    success_count += 1
            
            print(f"\nIndexing complete: {success_count}/{len(need_indexing)} successful")
    
    # Summary
    print("\n=== Summary ===")
    print(f"Total repositories: {len(repos)}")
    print(f"Indexed: {len(already_indexed) + sum(1 for r in need_indexing if check_index_exists(r))}")
    
    # List all indexed repos with their hashes
    print("\nIndexed repositories:")
    for repo in repos:
        if check_index_exists(repo):
            print(f"  {repo['name']:30} -> {repo['hash']}")


if __name__ == "__main__":
    import sqlite3
    main()