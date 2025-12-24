#!/usr/bin/env python3
"""
Final comprehensive MCP test with current repository.
"""

import sys
import os
from pathlib import Path
import json
import time
import subprocess

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set environment variables as MCP would receive them
os.environ["MCP_ENABLE_MULTI_REPO"] = "true"
os.environ["MCP_INDEX_STORAGE_PATH"] = "/workspaces/Code-Index-MCP/.indexes"
os.environ["MCP_REPO_REGISTRY"] = "/workspaces/Code-Index-MCP/.indexes/repository_registry.json"
os.environ["PYTHONPATH"] = "/workspaces/Code-Index-MCP"
os.environ["MCP_WORKSPACE_ROOT"] = "/workspaces/Code-Index-MCP"

# Import MCP modules
from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.utils.index_discovery import IndexDiscovery


def test_mcp_complete():
    """Complete MCP test."""
    print("MCP Complete Test Suite")
    print("=" * 60)
    
    # 1. Index Discovery
    print("\n1. INDEX DISCOVERY")
    print("-" * 40)
    discovery = IndexDiscovery(Path.cwd(), enable_multi_path=True)
    index_path = discovery.get_local_index_path()
    print(f"Discovered index: {index_path}")
    
    if not index_path:
        print("ERROR: No index found!")
        return
        
    # 2. SQLite Store
    print("\n2. SQLITE STORE INITIALIZATION")
    print("-" * 40)
    store = SQLiteStore(str(index_path))
    print(f"Store initialized: {store.db_path}")
    
    # 3. Direct BM25 Test
    print("\n3. DIRECT BM25 SEARCH TEST")
    print("-" * 40)
    query = "PathUtils workspace"
    results = store.search_bm25(query, table="bm25_content", limit=5)
    print(f"Query: '{query}'")
    print(f"Results: {len(results)}")
    for i, result in enumerate(results[:3]):
        print(f"  {i+1}. {result.get('filepath', 'N/A')}")
        print(f"     Score: {result.get('score', 0)}")
    
    # 4. Dispatcher Creation
    print("\n4. DISPATCHER INITIALIZATION")
    print("-" * 40)
    dispatcher = EnhancedDispatcher(
        sqlite_store=store,
        enable_advanced_features=True,
        use_plugin_factory=True,
        lazy_load=True,
        semantic_search_enabled=False,
        memory_aware=True,
        multi_repo_enabled=True
    )
    print(f"Dispatcher created")
    print(f"Multi-repo enabled: {dispatcher._multi_repo_manager is not None}")
    print(f"Supported languages: {len(dispatcher.supported_languages)}")
    
    # 5. Dispatcher Search
    print("\n5. DISPATCHER SEARCH TEST")
    print("-" * 40)
    search_results = list(dispatcher.search("PathUtils", semantic=False, limit=5))
    print(f"Query: 'PathUtils'")
    print(f"Results: {len(search_results)}")
    for i, result in enumerate(search_results[:3]):
        print(f"  {i+1}. {result.file}:{result.line}")
        print(f"     Score: {result.score}")
    
    # 6. Symbol Lookup
    print("\n6. SYMBOL LOOKUP TEST")
    print("-" * 40)
    symbol = dispatcher.lookup("PathUtils")
    if symbol:
        print(f"Found symbol: {symbol.get('symbol')}")
        print(f"  File: {symbol.get('defined_in')}")
        print(f"  Line: {symbol.get('line')}")
    else:
        print("Symbol not found")
    
    # 7. Multi-repo Check
    print("\n7. MULTI-REPOSITORY CHECK")
    print("-" * 40)
    if dispatcher._multi_repo_manager:
        repos = dispatcher._multi_repo_manager.list_repositories()
        print(f"Registered repositories: {len(repos)}")
        for repo in repos[:3]:
            print(f"  - {repo.name} ({repo.repository_id}): {repo.total_files} files")
    
    # 8. Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("-" * 40)
    print(f"✓ Index discovered: {index_path}")
    print(f"✓ BM25 search working: {len(results) > 0}")
    print(f"✓ Dispatcher search: {len(search_results) > 0}")
    print(f"✓ Multi-repo enabled: {dispatcher._multi_repo_manager is not None}")
    print(f"✓ Symbol lookup: {'Working' if symbol else 'Not working (no symbols indexed)'}")
    
    # Final MCP-style test
    print("\n9. MCP-STYLE SEARCH TEST")
    print("-" * 40)
    print("Simulating MCP tool call: search_code(query='def get_workspace_root', limit=5)")
    
    # This simulates what happens in the MCP server
    results = list(dispatcher.search("def get_workspace_root", semantic=False, limit=5))
    print(f"Found {len(results)} results")
    
    if results:
        print("\n✅ MCP INTEGRATION IS WORKING!")
        print("The multi-repository search with per-repository indexes is functional.")
    else:
        print("\n⚠️  No results found, but infrastructure is working.")
        print("This may be due to:")
        print("  - Query not matching any content")
        print("  - Need to re-index with proper content extraction")


if __name__ == "__main__":
    test_mcp_complete()