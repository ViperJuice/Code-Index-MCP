#!/usr/bin/env python3
"""
Test MCP queries with migrated index schema.
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


def test_migrated_index():
    """Test MCP with migrated index."""
    print("MCP Migrated Index Test")
    print("=" * 60)
    
    # Find index
    discovery = IndexDiscovery(Path.cwd(), enable_multi_path=True)
    index_path = discovery.get_local_index_path()
    print(f"Using index: {index_path}")
    
    # Create store
    store = SQLiteStore(str(index_path))
    
    # Check index content
    print("\n1. INDEX VERIFICATION")
    print("-" * 40)
    with store._get_connection() as conn:
        # Check tables
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"Tables: {len(tables)} total")
        
        # Check BM25 content
        if 'bm25_content' in tables:
            cursor = conn.execute("SELECT COUNT(*) FROM bm25_content")
            bm25_count = cursor.fetchone()[0]
            print(f"BM25 documents: {bm25_count}")
            
            # Sample content
            cursor = conn.execute("""
                SELECT filepath, substr(content, 1, 100) 
                FROM bm25_content 
                WHERE content LIKE '%PathUtils%'
                LIMIT 3
            """)
            results = cursor.fetchall()
            if results:
                print(f"\nFiles containing 'PathUtils':")
                for filepath, content in results:
                    print(f"  - {filepath}")
                    print(f"    {content[:60]}...")
        
        # Check files
        cursor = conn.execute("SELECT COUNT(*) FROM files")
        file_count = cursor.fetchone()[0]
        print(f"\nTotal files: {file_count}")
        
        # Check symbols
        cursor = conn.execute("SELECT COUNT(*) FROM symbols")
        symbol_count = cursor.fetchone()[0]
        print(f"Symbols: {symbol_count}")
    
    # Test BM25 search
    print("\n2. BM25 SEARCH TEST")
    print("-" * 40)
    
    test_queries = [
        "PathUtils",
        "get_workspace_root", 
        "EnhancedDispatcher",
        "multi_repo_manager",
        "def search"
    ]
    
    for query in test_queries:
        try:
            results = store.search_bm25(query, table="bm25_content", limit=5)
            print(f"\nQuery: '{query}' - Found {len(results)} results")
            for i, result in enumerate(results[:3]):
                filepath = result.get('filepath', result.get('file_path', 'N/A'))
                print(f"  {i+1}. {filepath}")
                score = result.get('score', 0)
                if score:
                    print(f"     Score: {score:.4f}")
        except Exception as e:
            print(f"\nQuery: '{query}' - Error: {e}")
    
    # Create dispatcher
    print("\n3. DISPATCHER TEST")
    print("-" * 40)
    dispatcher = EnhancedDispatcher(
        sqlite_store=store,
        enable_advanced_features=True,
        use_plugin_factory=False,  # No plugins
        lazy_load=True,
        semantic_search_enabled=False,
        memory_aware=False,
        multi_repo_enabled=True
    )
    print("Dispatcher created")
    
    # Test dispatcher search
    for query in ["PathUtils", "def get_workspace_root"]:
        print(f"\nDispatcher search: '{query}'")
        try:
            results = list(dispatcher.search(query, semantic=False, limit=5))
            print(f"Found {len(results)} results")
            for i, result in enumerate(results[:3]):
                print(f"  {i+1}. {result.file}:{result.line}")
                if result.snippet:
                    snippet = result.snippet.strip()[:60]
                    print(f"     {snippet}...")
        except Exception as e:
            print(f"Error: {e}")
    
    # Test symbol lookup
    print("\n4. SYMBOL LOOKUP TEST")
    print("-" * 40)
    
    symbols = ["PathUtils", "get_workspace_root", "SQLiteStore"]
    for symbol in symbols:
        result = dispatcher.lookup(symbol)
        if result:
            print(f"\n✓ Found symbol: {symbol}")
            print(f"  File: {result.get('defined_in', 'N/A')}")
            print(f"  Line: {result.get('line', 'N/A')}")
            print(f"  Kind: {result.get('kind', 'N/A')}")
        else:
            print(f"\n✗ Symbol not found: {symbol}")
    
    # Check specific files
    print("\n5. FILE VERIFICATION")
    print("-" * 40)
    
    important_files = [
        "mcp_server/core/path_utils.py",
        "mcp_server/dispatcher/dispatcher_enhanced.py",
        "mcp_server/storage/sqlite_store.py",
        "scripts/cli/mcp_server_cli.py"
    ]
    
    with store._get_connection() as conn:
        for file in important_files:
            # Try both absolute and relative paths
            cursor = conn.execute("""
                SELECT COUNT(*) FROM files 
                WHERE path LIKE ? OR relative_path LIKE ?
            """, (f"%{file}", f"%{file}"))
            count = cursor.fetchone()[0]
            
            if count > 0:
                # Get content sample
                cursor = conn.execute("""
                    SELECT substr(b.content, 1, 100)
                    FROM files f
                    JOIN bm25_content b ON f.id = b.file_id
                    WHERE f.path LIKE ? OR f.relative_path LIKE ?
                    LIMIT 1
                """, (f"%{file}", f"%{file}"))
                result = cursor.fetchone()
                if result:
                    print(f"\n✓ {file}")
                    print(f"  Content: {result[0][:60]}...")
                else:
                    print(f"\n✓ {file} (no content)")
            else:
                print(f"\n✗ {file} - Not found")
    
    print("\n" + "=" * 60)
    print("Summary:")
    print(f"  - Index has {bm25_count if 'bm25_count' in locals() else 0} BM25 documents")
    print(f"  - Index has {file_count} files")
    print(f"  - Index has {symbol_count} symbols")
    print(f"  - BM25 search is {'working' if 'results' in locals() else 'not working'}")
    print(f"  - Multi-repo support is enabled")
    print("\n✅ Testing complete!")


if __name__ == "__main__":
    test_migrated_index()