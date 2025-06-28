#!/usr/bin/env python3
"""
Test multi-repository search functionality after fix.
"""

import sys
import os
import asyncio
import time
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set environment variables
os.environ["MCP_ENABLE_MULTI_REPO"] = "true"
os.environ["MCP_INDEX_STORAGE_PATH"] = "/workspaces/Code-Index-MCP/.indexes"
os.environ["PYTHONPATH"] = "/workspaces/Code-Index-MCP"

from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.storage.multi_repo_manager import MultiRepositoryManager
from mcp_server.core.path_utils import PathUtils


async def test_multi_repo_search():
    """Test multi-repository search functionality."""
    print("MULTI-REPOSITORY SEARCH TEST")
    print("=" * 60)
    
    # Initialize components
    repo_hash = "844145265d7a"
    index_path = PathUtils.get_index_storage_path() / repo_hash / "code_index.db"
    
    if not index_path.exists():
        print(f"❌ Index not found at {index_path}")
        return
    
    # Create store and multi-repo manager
    store = SQLiteStore(str(index_path))
    # Specify the correct registry path
    registry_path = PathUtils.get_index_storage_path() / "repository_registry.json"
    multi_repo_manager = MultiRepositoryManager(central_index_path=registry_path)
    
    # Check registered repositories
    repos = multi_repo_manager.list_repositories()
    print(f"\nRegistered repositories: {len(repos)}")
    for repo in repos[:3]:
        print(f"  - {repo.name} ({repo.repository_id}): {repo.total_files} files")
    
    # Test queries
    test_queries = [
        {
            "query": "EnhancedDispatcher",
            "repo_ids": [repo_hash],
            "expected": True
        },
        {
            "query": "multi_repo_manager",
            "repo_ids": [repo_hash],
            "expected": True
        },
        {
            "query": "def search",
            "repo_ids": [repo_hash],
            "expected": True
        }
    ]
    
    results_summary = []
    
    for test in test_queries:
        print(f"\n🔍 Testing: '{test['query']}'")
        print(f"   Repository IDs: {test['repo_ids']}")
        
        start_time = time.time()
        
        try:
            # Test with timeout
            search_results = await asyncio.wait_for(
                multi_repo_manager.search_code(
                    test["query"],
                    repository_ids=test["repo_ids"],
                    limit=5
                ),
                timeout=10.0
            )
            
            elapsed = time.time() - start_time
            
            # Count total results
            total_results = sum(len(r.results) for r in search_results)
            
            print(f"   ✅ Completed in {elapsed:.2f}s")
            print(f"   Found {total_results} results across {len(search_results)} repositories")
            
            # Show sample results
            for repo_result in search_results:
                if repo_result.results:
                    print(f"\n   Repository: {repo_result.repository_name}")
                    for i, result in enumerate(repo_result.results[:2]):
                        print(f"     {i+1}. {result['file']}:{result.get('line', 0)}")
                        if result.get('snippet'):
                            snippet = result['snippet'][:100].replace('\n', ' ')
                            print(f"        {snippet}...")
            
            results_summary.append({
                "query": test["query"],
                "status": "success",
                "elapsed": elapsed,
                "total_results": total_results,
                "hung": False
            })
            
        except asyncio.TimeoutError:
            elapsed = time.time() - start_time
            print(f"   ❌ TIMEOUT after {elapsed:.2f}s")
            results_summary.append({
                "query": test["query"],
                "status": "timeout",
                "elapsed": elapsed,
                "hung": True
            })
            
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"   ❌ ERROR: {str(e)[:100]}...")
            results_summary.append({
                "query": test["query"],
                "status": "error",
                "elapsed": elapsed,
                "error": str(e),
                "hung": False
            })
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    success_count = sum(1 for r in results_summary if r["status"] == "success")
    timeout_count = sum(1 for r in results_summary if r.get("hung", False))
    
    print(f"Total tests: {len(results_summary)}")
    print(f"Successful: {success_count}")
    print(f"Timeouts: {timeout_count}")
    
    if timeout_count == 0:
        print("\n✅ SUCCESS: No hanging detected!")
        print("✅ Multi-repository search is working correctly")
    else:
        print(f"\n❌ FAILURE: {timeout_count} tests timed out")
    
    # Save results
    with open("multi_repo_search_test_results.json", "w") as f:
        json.dump(results_summary, f, indent=2)
    
    print(f"\nResults saved to: multi_repo_search_test_results.json")


async def main():
    """Main entry point."""
    await test_multi_repo_search()


if __name__ == "__main__":
    asyncio.run(main())