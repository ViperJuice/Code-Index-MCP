#!/usr/bin/env python3
"""
Direct test of multi-repository search functionality.
Tests the MultiRepositoryManager directly without MCP.
"""

import sys
import os
from pathlib import Path
import json

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from mcp_server.storage.multi_repo_manager import MultiRepositoryManager, get_multi_repo_manager
from mcp_server.core.path_utils import PathUtils


def test_multi_repo_direct():
    """Test multi-repository functionality directly."""
    print("Testing Multi-Repository Search")
    print("=" * 60)
    
    # Set up paths
    registry_path = PathUtils.get_index_storage_path() / "repository_registry.json"
    print(f"Registry path: {registry_path}")
    
    # Create manager
    manager = MultiRepositoryManager(central_index_path=registry_path)
    
    # List repositories
    print("\nRegistered Repositories:")
    repos = manager.list_repositories()
    for repo in repos[:5]:  # Show first 5
        print(f"  - {repo.name} ({repo.repository_id}): {repo.total_files} files")
        print(f"    Path: {repo.path}")
        print(f"    Index: {repo.index_path}")
        if repo.index_path.exists():
            print(f"    Status: ✓ Index exists")
        else:
            print(f"    Status: ✗ Index missing")
    
    if len(repos) > 5:
        print(f"  ... and {len(repos) - 5} more repositories")
    
    # Find current repository
    current_repo_path = str(PathUtils.get_workspace_root())
    current_repo = None
    for repo in repos:
        if str(repo.path) == current_repo_path:
            current_repo = repo
            break
    
    if current_repo:
        print(f"\nCurrent repository found: {current_repo.name}")
        print(f"  ID: {current_repo.repository_id}")
        print(f"  Files: {current_repo.total_files}")
        
        # Test search in current repository
        print("\nTesting search in current repository...")
        try:
            # Use synchronous search since we're not in async context
            import asyncio
            
            async def run_search():
                results = await manager.search_symbol(
                    "PathUtils",
                    repository_ids=[current_repo.repository_id],
                    limit=5
                )
                return results
            
            results = asyncio.run(run_search())
            
            print(f"Search results for 'PathUtils':")
            for result in results:
                print(f"  Repository: {result.repository_name}")
                print(f"  Found {len(result.results)} matches")
                for match in result.results[:3]:
                    print(f"    - {match['symbol']} in {match['file']}:{match['line']}")
                
        except Exception as e:
            print(f"  Error during search: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"\nCurrent repository not found in registry!")
        print(f"Current path: {current_repo_path}")
    
    # Check health
    print("\nRepository Health Check:")
    health = manager.health_check()
    print(f"  Healthy: {health['healthy']}")
    print(f"  Unhealthy: {health['unhealthy']}")
    
    for repo_health in health['repositories'][:3]:
        if repo_health['issues']:
            print(f"  {repo_health['name']}: {repo_health['status']} - {repo_health['issues']}")


if __name__ == "__main__":
    test_multi_repo_direct()