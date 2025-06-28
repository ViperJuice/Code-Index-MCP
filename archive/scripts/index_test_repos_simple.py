#!/usr/bin/env python3
"""
Simple script to index test repositories using mcp-index-kit.
"""

import subprocess
import time
from pathlib import Path
import json

def index_repo(repo_path: Path, mcp_index_path: str) -> bool:
    """Index a single repository."""
    print(f"Indexing {repo_path.name}...", end=" ", flush=True)
    
    try:
        # Change to repo directory and run indexing
        result = subprocess.run(
            [mcp_index_path, "build"],
            cwd=str(repo_path),
            capture_output=True,
            text=True,
            timeout=120  # 2 minute timeout
        )
        
        if result.returncode == 0:
            print("✅")
            return True
        else:
            print(f"❌ ({result.stderr.strip()[:50]}...)")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ (timeout)")
        return False
    except Exception as e:
        print(f"❌ ({str(e)})")
        return False


def main():
    # Path to mcp-index
    mcp_index = "/workspaces/Code-Index-MCP/mcp-index-kit/bin/mcp-index"
    
    # Get test repos
    test_repos_dir = Path("/workspaces/Code-Index-MCP/test_repos")
    repos = []
    
    for git_dir in sorted(test_repos_dir.rglob(".git")):
        if git_dir.is_dir():
            repos.append(git_dir.parent)
    
    print(f"Found {len(repos)} repositories to index\n")
    
    # Index each repo
    success = 0
    failed = []
    
    for i, repo in enumerate(repos[:20]):  # First 20 repos
        print(f"[{i+1}/20] ", end="")
        if index_repo(repo, mcp_index):
            success += 1
        else:
            failed.append(repo.name)
    
    print(f"\nSummary: {success}/20 indexed successfully")
    
    if failed:
        print(f"Failed: {', '.join(failed)}")


if __name__ == "__main__":
    main()