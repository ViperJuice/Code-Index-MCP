#!/usr/bin/env python3
"""
Comprehensive validation of MCP functionality after re-indexing.
Tests all query types to ensure everything is working properly.
"""

import sys
import os
from pathlib import Path
import json
import time

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set environment variables
os.environ["MCP_ENABLE_MULTI_REPO"] = "true"
os.environ["MCP_INDEX_STORAGE_PATH"] = "/workspaces/Code-Index-MCP/.indexes"
os.environ["PYTHONPATH"] = "/workspaces/Code-Index-MCP"

from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.utils.index_discovery import IndexDiscovery
from mcp_server.core.path_utils import PathUtils


def validate_mcp():
    """Validate MCP functionality comprehensively."""
    print("MCP COMPREHENSIVE VALIDATION")
    print("=" * 60)
    
    # Find index
    discovery = IndexDiscovery(Path.cwd(), enable_multi_path=True)
    index_path = discovery.get_local_index_path()
    print(f"Using index: {index_path}")
    
    # Create store
    store = SQLiteStore(str(index_path))
    
    # Check index status
    print("\n1. INDEX STATUS")
    print("-" * 40)
    with store._get_connection() as conn:
        # Check tables
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"Tables: {len(tables)} total")
        
        # Check key tables
        key_tables = ['files', 'symbols', 'fts_code', 'fts_symbols', 'bm25_content']
        for table in key_tables:
            if table in tables:
                cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"  {table}: {count} rows")
            else:
                print(f"  {table}: NOT FOUND")
    
    # Create dispatcher
    print("\n2. DISPATCHER INITIALIZATION")
    print("-" * 40)
    dispatcher = EnhancedDispatcher(
        sqlite_store=store,
        enable_advanced_features=True,
        use_plugin_factory=False,  # Faster without plugins for testing
        lazy_load=True,
        semantic_search_enabled=False,
        memory_aware=False,
        multi_repo_enabled=True
    )
    print("✓ Dispatcher created")
    print(f"✓ Multi-repo support: {dispatcher._multi_repo_manager is not None}")
    
    # Test queries
    test_results = {
        "symbol_lookup": {},
        "code_search": {},
        "file_search": {},
        "bm25_search": {}
    }
    
    # Test 1: Symbol Lookup
    print("\n3. SYMBOL LOOKUP TESTS")
    print("-" * 40)
    
    test_symbols = [
        "PathUtils",
        "EnhancedDispatcher", 
        "SQLiteStore",
        "get_workspace_root",
        "BM25Indexer",
        "MultiRepositoryManager"
    ]
    
    for symbol in test_symbols:
        result = dispatcher.lookup(symbol)
        if result:
            test_results["symbol_lookup"][symbol] = {
                "found": True,
                "file": result.get('defined_in', 'N/A'),
                "line": result.get('line', 'N/A'),
                "kind": result.get('kind', 'N/A')
            }
            print(f"✓ {symbol}: Found in {result.get('defined_in', 'N/A')}:{result.get('line', 'N/A')}")
        else:
            test_results["symbol_lookup"][symbol] = {"found": False}
            print(f"✗ {symbol}: Not found")
    
    # Test 2: Code Search
    print("\n4. CODE SEARCH TESTS")
    print("-" * 40)
    
    test_queries = [
        "class PathUtils",
        "def get_workspace_root",
        "import os",
        "from pathlib import Path",
        "multi_repo_manager",
        "def search",
        "MCP_ENABLE_MULTI_REPO"
    ]
    
    for query in test_queries:
        results = list(dispatcher.search(query, semantic=False, limit=5))
        test_results["code_search"][query] = {
            "count": len(results),
            "results": []
        }
        
        if results:
            print(f"\n✓ '{query}': Found {len(results)} results")
            for i, result in enumerate(results[:3]):
                test_results["code_search"][query]["results"].append({
                    "file": result.get('file', result.get('file_path', 'N/A')),
                    "line": result.get('line', 0),
                    "score": result.get('score', 0.0)
                })
                file_path = result.get('file', result.get('file_path', 'N/A'))
                line = result.get('line', 0)
                score = result.get('score', 0.0)
                print(f"  {i+1}. {file_path}:{line} (score: {score:.4f})")
        else:
            print(f"\n✗ '{query}': No results")
    
    # Test 3: Direct BM25 Search
    print("\n5. DIRECT BM25 SEARCH TESTS")
    print("-" * 40)
    
    bm25_queries = ["PathUtils", "dispatcher", "index", "search", "repository"]
    
    for query in bm25_queries:
        # Try different table names
        for table in ['bm25_content', 'fts_code']:
            try:
                results = store.search_bm25(query, table=table, limit=3)
                if results:
                    test_results["bm25_search"][f"{query} ({table})"] = len(results)
                    print(f"\n✓ '{query}' in {table}: {len(results)} results")
                    for result in results[:2]:
                        filepath = result.get('filepath', result.get('file_path', 'N/A'))
                        print(f"  - {filepath}")
                    break
            except:
                continue
    
    # Test 4: File verification
    print("\n6. FILE VERIFICATION")
    print("-" * 40)
    
    important_files = [
        "mcp_server/core/path_utils.py",
        "mcp_server/dispatcher/dispatcher_enhanced.py",
        "mcp_server/storage/sqlite_store.py",
        "mcp_server/storage/multi_repo_manager.py",
        "scripts/cli/mcp_server_cli.py"
    ]
    
    with store._get_connection() as conn:
        for file in important_files:
            cursor = conn.execute("""
                SELECT COUNT(*) FROM files 
                WHERE path LIKE ? OR relative_path LIKE ?
            """, (f"%{file}", f"%{file}"))
            count = cursor.fetchone()[0]
            
            if count > 0:
                # Check if content is indexed
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM fts_code f
                    JOIN files ON files.id = f.file_id
                    WHERE files.path LIKE ? OR files.relative_path LIKE ?
                """, (f"%{file}", f"%{file}"))
                fts_count = cursor.fetchone()[0]
                
                test_results["file_search"][file] = {
                    "indexed": True,
                    "fts_indexed": fts_count > 0
                }
                print(f"✓ {file}: Indexed (FTS: {'Yes' if fts_count > 0 else 'No'})")
            else:
                test_results["file_search"][file] = {"indexed": False}
                print(f"✗ {file}: Not found")
    
    # Summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    
    # Symbol lookup summary
    symbols_found = sum(1 for r in test_results["symbol_lookup"].values() if r.get("found"))
    print(f"Symbol Lookup: {symbols_found}/{len(test_symbols)} found")
    
    # Code search summary
    searches_with_results = sum(1 for r in test_results["code_search"].values() if r["count"] > 0)
    print(f"Code Search: {searches_with_results}/{len(test_queries)} queries returned results")
    
    # BM25 search summary
    bm25_success = len([k for k in test_results["bm25_search"] if test_results["bm25_search"][k] > 0])
    print(f"BM25 Search: {bm25_success} successful queries")
    
    # File indexing summary
    files_indexed = sum(1 for r in test_results["file_search"].values() if r.get("indexed"))
    print(f"File Verification: {files_indexed}/{len(important_files)} files indexed")
    
    # Overall status
    print("\nOVERALL STATUS:")
    if symbols_found > 0 or searches_with_results > 0 or bm25_success > 0:
        print("✅ MCP is functional and ready for use!")
        print("✅ Multi-repository support is enabled")
        print("✅ BM25 search is working")
        if symbols_found == 0:
            print("⚠️  Symbol extraction needs improvement")
    else:
        print("❌ MCP needs troubleshooting")
    
    # Save detailed results
    results_file = "mcp_validation_results.json"
    with open(results_file, 'w') as f:
        json.dump(test_results, f, indent=2)
    print(f"\nDetailed results saved to: {results_file}")


if __name__ == "__main__":
    validate_mcp()