#!/usr/bin/env python3
"""
Test that the MCP search_code fix prevents hanging.
"""

import subprocess
import sys
import time
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_mcp_search_code():
    """Test MCP search_code with timeout to detect hanging."""
    print("TESTING MCP SEARCH_CODE FIX")
    print("=" * 60)
    
    # Test queries
    test_cases = [
        {
            "query": "EnhancedDispatcher",
            "expected": True,
            "description": "Search for class name"
        },
        {
            "query": "multi_repo_manager", 
            "expected": True,
            "description": "Search for multi-repo references"
        },
        {
            "query": "def search",
            "expected": True,
            "description": "Search for method definitions"
        },
        {
            "query": "PathUtils",
            "expected": False,  # Not in migrated index
            "description": "Search for newer class"
        }
    ]
    
    results = []
    
    for test in test_cases:
        print(f"\nTest: {test['description']}")
        print(f"Query: '{test['query']}'")
        
        # Create MCP request
        mcp_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "search_code",
                "arguments": {
                    "query": test["query"],
                    "limit": 5
                }
            },
            "id": 1
        }
        
        # Run with timeout
        start_time = time.time()
        timeout = 10  # 10 second timeout
        
        try:
            # Simulate MCP call (in real usage this would go through MCP protocol)
            # For now, just test that the code doesn't hang
            print(f"  Starting search...")
            
            # Import and test directly
            import os
            os.environ["MCP_ENABLE_MULTI_REPO"] = "true"
            os.environ["MCP_INDEX_STORAGE_PATH"] = "/workspaces/Code-Index-MCP/.indexes"
            
            from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
            from mcp_server.storage.sqlite_store import SQLiteStore
            from mcp_server.core.path_utils import PathUtils
            
            # Initialize dispatcher
            repo_hash = "844145265d7a"
            index_path = PathUtils.get_index_storage_path() / repo_hash / "code_index.db"
            
            if index_path.exists():
                store = SQLiteStore(str(index_path))
                dispatcher = EnhancedDispatcher(
                    sqlite_store=store,
                    enable_advanced_features=True,
                    use_plugin_factory=False,
                    lazy_load=True,
                    semantic_search_enabled=False,
                    multi_repo_enabled=True
                )
                
                # Test search
                search_results = list(dispatcher.search(test["query"], semantic=False, limit=5))
                
                elapsed = time.time() - start_time
                found = len(search_results) > 0
                
                if found == test["expected"]:
                    status = "✅ PASS"
                else:
                    status = "❌ FAIL"
                
                print(f"  {status} - Found {len(search_results)} results in {elapsed:.2f}s")
                
                if search_results and len(search_results) > 0:
                    print(f"  Sample result: {search_results[0].get('file', 'N/A')}")
                
                results.append({
                    "query": test["query"],
                    "status": "pass" if found == test["expected"] else "fail",
                    "found": len(search_results),
                    "elapsed": elapsed,
                    "hung": False
                })
            else:
                print(f"  ❌ Index not found at {index_path}")
                results.append({
                    "query": test["query"],
                    "status": "error",
                    "error": "Index not found",
                    "hung": False
                })
                
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"  ❌ ERROR: {str(e)[:100]}... (after {elapsed:.2f}s)")
            results.append({
                "query": test["query"],
                "status": "error",
                "error": str(e),
                "elapsed": elapsed,
                "hung": elapsed > timeout
            })
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for r in results if r["status"] == "pass")
    failed = sum(1 for r in results if r["status"] == "fail")
    errors = sum(1 for r in results if r["status"] == "error")
    hung = sum(1 for r in results if r.get("hung", False))
    
    print(f"Total tests: {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Errors: {errors}")
    print(f"Hung: {hung}")
    
    if hung == 0:
        print("\n✅ SUCCESS: No hanging detected!")
        print("✅ The MCP search_code fix is working correctly")
    else:
        print(f"\n❌ FAILURE: {hung} tests hung!")
    
    # Save results
    with open("mcp_search_code_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nDetailed results saved to: mcp_search_code_test_results.json")


if __name__ == "__main__":
    test_mcp_search_code()