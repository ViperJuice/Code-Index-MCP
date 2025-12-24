#!/usr/bin/env python3
"""
Test all MCP query types with the newly indexed repository.
"""

import sys
import os
from pathlib import Path
import json
import time
import asyncio

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set environment variables as MCP would
os.environ["MCP_ENABLE_MULTI_REPO"] = "true"
os.environ["MCP_INDEX_STORAGE_PATH"] = "/workspaces/Code-Index-MCP/.indexes"
os.environ["MCP_REPO_REGISTRY"] = "/workspaces/Code-Index-MCP/.indexes/repository_registry.json"
os.environ["PYTHONPATH"] = "/workspaces/Code-Index-MCP"
os.environ["MCP_WORKSPACE_ROOT"] = "/workspaces/Code-Index-MCP"

# Import MCP server components
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "cli"))
from mcp_server_cli import initialize_services, call_tool


async def test_all_mcp_queries():
    """Test all MCP query types."""
    print("MCP Comprehensive Query Test")
    print("=" * 60)
    
    # Initialize services
    print("\n1. INITIALIZING MCP SERVICES")
    print("-" * 40)
    try:
        await initialize_services()
        print("✓ Services initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize: {e}")
        return
    
    # Test data
    test_queries = {
        "symbol_lookup": [
            {"symbol": "PathUtils"},
            {"symbol": "EnhancedDispatcher"},
            {"symbol": "SQLiteStore"},
            {"symbol": "get_workspace_root"},
            {"symbol": "MultiRepositoryManager"}
        ],
        "search_code": [
            {"query": "class PathUtils", "semantic": False, "limit": 5},
            {"query": "def get_workspace_root", "semantic": False, "limit": 5},
            {"query": "multi_repo_manager", "semantic": False, "limit": 5},
            {"query": "import os", "semantic": False, "limit": 5},
            {"query": "MCP_ENABLE_MULTI_REPO", "semantic": False, "limit": 5}
        ],
        "get_status": [
            {}
        ],
        "list_plugins": [
            {}
        ],
        "reindex": [
            {"path": "/workspaces/Code-Index-MCP/mcp_server/core/path_utils.py"}
        ]
    }
    
    results = {}
    
    # Test 1: Symbol Lookup
    print("\n2. TESTING SYMBOL LOOKUP")
    print("-" * 40)
    results["symbol_lookup"] = []
    
    for test in test_queries["symbol_lookup"]:
        symbol = test["symbol"]
        print(f"\nLooking up: {symbol}")
        
        try:
            start = time.time()
            response = await call_tool("symbol_lookup", test)
            elapsed = time.time() - start
            
            if response and len(response) > 0:
                text_content = response[0].text if hasattr(response[0], 'text') else str(response[0])
                data = json.loads(text_content)
                
                if "symbol" in data:
                    print(f"  ✓ Found in {elapsed:.3f}s")
                    print(f"    File: {data.get('defined_in', 'N/A')}")
                    print(f"    Line: {data.get('line', 'N/A')}")
                    print(f"    Kind: {data.get('kind', 'N/A')}")
                    results["symbol_lookup"].append({"symbol": symbol, "found": True, "data": data})
                else:
                    print(f"  ✗ Not found ({elapsed:.3f}s)")
                    results["symbol_lookup"].append({"symbol": symbol, "found": False})
        except Exception as e:
            print(f"  ✗ Error: {e}")
            results["symbol_lookup"].append({"symbol": symbol, "error": str(e)})
    
    # Test 2: Code Search
    print("\n3. TESTING CODE SEARCH")
    print("-" * 40)
    results["search_code"] = []
    
    for test in test_queries["search_code"]:
        query = test["query"]
        print(f"\nSearching for: '{query}'")
        
        try:
            start = time.time()
            response = await call_tool("search_code", test)
            elapsed = time.time() - start
            
            if response and len(response) > 0:
                text_content = response[0].text if hasattr(response[0], 'text') else str(response[0])
                data = json.loads(text_content)
                
                result_count = len(data.get("results", []))
                print(f"  ✓ Found {result_count} results in {elapsed:.3f}s")
                
                for i, result in enumerate(data.get("results", [])[:3]):
                    print(f"    {i+1}. {result.get('file', 'N/A')}:{result.get('line', '?')}")
                    if result.get('snippet'):
                        snippet = result['snippet'].strip()[:60]
                        print(f"       {snippet}...")
                
                results["search_code"].append({
                    "query": query, 
                    "count": result_count,
                    "results": data.get("results", [])
                })
        except Exception as e:
            print(f"  ✗ Error: {e}")
            results["search_code"].append({"query": query, "error": str(e)})
    
    # Test 3: Get Status
    print("\n4. TESTING GET STATUS")
    print("-" * 40)
    
    try:
        start = time.time()
        response = await call_tool("get_status", {})
        elapsed = time.time() - start
        
        if response and len(response) > 0:
            text_content = response[0].text if hasattr(response[0], 'text') else str(response[0])
            data = json.loads(text_content)
            
            print(f"✓ Status retrieved in {elapsed:.3f}s")
            print(f"  Index: {data.get('index', {}).get('path', 'N/A')}")
            print(f"  Total files: {data.get('index', {}).get('total_files', 0)}")
            print(f"  Indexed files: {data.get('index', {}).get('indexed_files', 0)}")
            print(f"  Symbols: {data.get('index', {}).get('symbols', 0)}")
            print(f"  Health: {data.get('health', 'N/A')}")
            
            results["status"] = data
    except Exception as e:
        print(f"✗ Error: {e}")
        results["status"] = {"error": str(e)}
    
    # Test 4: List Plugins
    print("\n5. TESTING LIST PLUGINS")
    print("-" * 40)
    
    try:
        start = time.time()
        response = await call_tool("list_plugins", {})
        elapsed = time.time() - start
        
        if response and len(response) > 0:
            text_content = response[0].text if hasattr(response[0], 'text') else str(response[0])
            data = json.loads(text_content)
            
            plugin_count = len(data.get("loaded_plugins", []))
            language_count = len(data.get("supported_languages", []))
            
            print(f"✓ Plugin info retrieved in {elapsed:.3f}s")
            print(f"  Loaded plugins: {plugin_count}")
            print(f"  Supported languages: {language_count}")
            
            # Show first few languages
            languages = data.get("supported_languages", [])[:10]
            if languages:
                print(f"  Languages: {', '.join(languages)}...")
            
            results["plugins"] = data
    except Exception as e:
        print(f"✗ Error: {e}")
        results["plugins"] = {"error": str(e)}
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("-" * 40)
    
    # Symbol lookup results
    symbols_found = sum(1 for r in results.get("symbol_lookup", []) if r.get("found"))
    print(f"Symbol Lookup: {symbols_found}/{len(test_queries['symbol_lookup'])} found")
    
    # Code search results
    searches_successful = sum(1 for r in results.get("search_code", []) if "count" in r)
    total_results = sum(r.get("count", 0) for r in results.get("search_code", []))
    print(f"Code Search: {searches_successful}/{len(test_queries['search_code'])} successful, {total_results} total results")
    
    # Status
    print(f"Status: {'✓' if 'index' in results.get('status', {}) else '✗'}")
    
    # Plugins
    print(f"Plugins: {'✓' if 'loaded_plugins' in results.get('plugins', {}) else '✗'}")
    
    print("\n✅ MCP query testing complete!")
    
    # Return results for further analysis
    return results


async def main():
    """Main entry point."""
    results = await test_all_mcp_queries()
    
    # Save results
    with open("mcp_query_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: mcp_query_test_results.json")


if __name__ == "__main__":
    asyncio.run(main())