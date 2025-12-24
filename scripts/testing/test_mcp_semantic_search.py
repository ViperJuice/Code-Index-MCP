#!/usr/bin/env python3
"""
Test MCP server semantic search after configuration fixes.
"""

import json
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.utils.index_discovery import IndexDiscovery

async def test_mcp_semantic_search():
    """Test MCP semantic search functionality."""
    print("=" * 60)
    print("TESTING MCP SEMANTIC SEARCH")
    print("=" * 60)
    
    # Step 1: Initialize components like MCP server does
    current_dir = Path.cwd()
    
    print("1. Finding SQL index...")
    discovery = IndexDiscovery(current_dir, enable_multi_path=True)
    index_path = discovery.get_local_index_path()
    
    if not index_path:
        print("❌ No SQL index found")
        return
        
    print(f"✅ Found SQL index: {index_path}")
    
    # Initialize SQLite store
    sqlite_store = SQLiteStore(str(index_path))
    
    # Step 2: Create dispatcher with semantic search enabled
    print("\n2. Creating enhanced dispatcher...")
    dispatcher = EnhancedDispatcher(
        sqlite_store=sqlite_store,
        enable_advanced_features=True,
        use_plugin_factory=True,
        lazy_load=True,
        semantic_search_enabled=True,
        memory_aware=True,
        multi_repo_enabled=None
    )
    
    print(f"✅ Dispatcher created with {len(dispatcher.supported_languages)} supported languages")
    
    # Step 3: Test searches
    test_queries = [
        ("search_code", {"query": "class EnhancedDispatcher", "semantic": False}, "SQL BM25"),
        ("search_code", {"query": "class EnhancedDispatcher", "semantic": True}, "Semantic"),
        ("search_code", {"query": "semantic indexer", "semantic": False}, "SQL BM25"),
        ("search_code", {"query": "semantic indexer", "semantic": True}, "Semantic"),
        ("symbol_lookup", {"symbol": "EnhancedDispatcher"}, "Symbol")
    ]
    
    print("\n3. Testing queries:")
    results_summary = []
    
    for tool_name, args, desc in test_queries:
        print(f"\n{desc} Query: {args}")
        
        try:
            start_time = time.time()
            
            if tool_name == "search_code":
                results = list(dispatcher.search(
                    args["query"], 
                    semantic=args.get("semantic", False), 
                    limit=5
                ))
            elif tool_name == "symbol_lookup":
                result = dispatcher.lookup(args["symbol"])
                results = [result] if result else []
            
            elapsed_ms = (time.time() - start_time) * 1000
            
            print(f"  Response time: {elapsed_ms:.1f}ms")
            print(f"  Results: {len(results)}")
            
            if results:
                for i, r in enumerate(results[:3]):
                    if tool_name == "search_code":
                        file_path = r.get("file", "unknown")
                        line = r.get("line", "?")
                        snippet = r.get("snippet", "")[:80]
                        print(f"    {i+1}. {file_path}:{line}")
                        if snippet:
                            print(f"       {snippet}...")
                    else:
                        print(f"    {r}")
                        
            results_summary.append({
                "method": desc,
                "query": str(args),
                "response_time_ms": elapsed_ms,
                "results_count": len(results),
                "success": len(results) > 0
            })
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
            results_summary.append({
                "method": desc,
                "query": str(args),
                "response_time_ms": 0,
                "results_count": 0,
                "success": False,
                "error": str(e)
            })
    
    # Step 4: Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    for result in results_summary:
        status = "✅" if result["success"] else "❌"
        print(f"{status} {result['method']}: {result['results_count']} results in {result['response_time_ms']:.1f}ms")
        if "error" in result:
            print(f"   Error: {result['error']}")
    
    # Check if semantic search worked
    semantic_results = [r for r in results_summary if "Semantic" in r["method"]]
    semantic_working = any(r["success"] for r in semantic_results)
    
    print(f"\nSemantic Search Status: {'✅ WORKING' if semantic_working else '❌ NOT WORKING'}")
    
    if not semantic_working:
        print("\nTroubleshooting:")
        print("1. Check if VOYAGE_AI_API_KEY is set in .env")
        print("2. Verify semantic discovery finds correct collection")
        print("3. Check if embeddings exist in Qdrant collections")

if __name__ == "__main__":
    import time
    asyncio.run(test_mcp_semantic_search())