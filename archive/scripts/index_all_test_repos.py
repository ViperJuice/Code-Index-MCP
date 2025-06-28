#!/usr/bin/env python3
"""
Index all test repositories for comprehensive testing.
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from typing import List, Dict
import time

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def find_test_repositories() -> List[Path]:
    """Find all test repositories."""
    test_repos_dir = Path("/workspaces/Code-Index-MCP/test_repos")
    repos = []
    
    # Find all .git directories
    for git_dir in sorted(test_repos_dir.rglob(".git")):
        if git_dir.is_dir():
            repos.append(git_dir.parent)
    
    return repos


def index_repository(repo_path: Path) -> Dict[str, any]:
    """Index a single repository."""
    print(f"\nIndexing {repo_path.name}...")
    start_time = time.time()
    
    result = {
        "repo": str(repo_path),
        "name": repo_path.name,
        "success": False,
        "error": None,
        "time": 0
    }
    
    try:
        # Use the mcp-index-kit CLI
        cmd = [
            "python", "-m", "mcp_server.cli.index",
            "--path", str(repo_path),
            "--verbose"
        ]
        
        # Set environment to ensure proper Python path
        env = os.environ.copy()
        env["PYTHONPATH"] = "/workspaces/Code-Index-MCP"
        
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            timeout=300  # 5 minute timeout
        )
        
        if process.returncode == 0:
            result["success"] = True
            print(f"  ✅ Successfully indexed {repo_path.name}")
        else:
            result["error"] = process.stderr
            print(f"  ❌ Failed to index {repo_path.name}")
            print(f"     Error: {process.stderr[:200]}...")
            
    except subprocess.TimeoutExpired:
        result["error"] = "Timeout after 5 minutes"
        print(f"  ❌ Timeout indexing {repo_path.name}")
    except Exception as e:
        result["error"] = str(e)
        print(f"  ❌ Error indexing {repo_path.name}: {e}")
    
    result["time"] = time.time() - start_time
    return result


def main():
    """Main function to index all test repositories."""
    print("Indexing All Test Repositories")
    print("=" * 60)
    
    repos = find_test_repositories()
    print(f"Found {len(repos)} repositories to index")
    
    # Check if we have the index CLI available
    try:
        subprocess.run(
            ["python", "-m", "mcp_server.cli.index", "--help"],
            capture_output=True,
            check=True
        )
    except:
        print("\n❌ MCP index CLI not available. Trying alternative approach...")
        
        # Try using mcp-index directly
        try:
            subprocess.run(
                ["mcp-index", "--help"],
                capture_output=True,
                check=True
            )
            print("✅ Found mcp-index command")
        except:
            print("❌ mcp-index command not found either")
            print("\nPlease install mcp-index-kit first:")
            print("  cd mcp-index-kit && ./install.sh")
            return
    
    # Index each repository
    results = []
    success_count = 0
    
    for i, repo in enumerate(repos):
        print(f"\n[{i+1}/{len(repos)}] Processing {repo.name}...")
        
        # Try indexing with mcp-index command
        try:
            cmd = ["mcp-index", "index", "--path", str(repo)]
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if process.returncode == 0:
                print(f"  ✅ Successfully indexed {repo.name}")
                success_count += 1
                results.append({
                    "repo": str(repo),
                    "name": repo.name,
                    "success": True
                })
            else:
                print(f"  ❌ Failed to index {repo.name}")
                print(f"     Error: {process.stderr[:200]}...")
                results.append({
                    "repo": str(repo),
                    "name": repo.name,
                    "success": False,
                    "error": process.stderr
                })
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
            results.append({
                "repo": str(repo),
                "name": repo.name,
                "success": False,
                "error": str(e)
            })
    
    # Summary
    print("\n" + "=" * 60)
    print("Indexing Summary")
    print("=" * 60)
    print(f"Total repositories: {len(repos)}")
    print(f"Successfully indexed: {success_count}")
    print(f"Failed: {len(repos) - success_count}")
    
    # Save results
    report_path = Path("/workspaces/Code-Index-MCP/test_repo_indexing_results.json")
    with open(report_path, "w") as f:
        json.dump({
            "total": len(repos),
            "success": success_count,
            "failed": len(repos) - success_count,
            "results": results
        }, f, indent=2)
    
    print(f"\nDetailed results saved to: {report_path}")
    
    if success_count < len(repos):
        print("\n⚠️  Some repositories failed to index.")
        print("This might be due to:")
        print("  - Large repository size")
        print("  - Missing language plugins")
        print("  - Insufficient memory")
        print("\nYou can try indexing failed repos individually with:")
        print("  mcp-index index --path <repo_path>")


if __name__ == "__main__":
    main()