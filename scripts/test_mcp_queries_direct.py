#!/usr/bin/env python3
"""
Test MCP queries directly without full initialization.
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


def test_direct_queries():
    """Test MCP queries directly."""
    print("Direct MCP Query Test")
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
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('fts_code', 'symbols', 'files')")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"Tables found: {', '.join(tables)}")
        
        # Check file count
        cursor = conn.execute("SELECT COUNT(*) FROM files")
        file_count = cursor.fetchone()[0]
        print(f"Total files: {file_count}")
        
        # Check FTS content
        cursor = conn.execute("SELECT COUNT(*) FROM fts_code")
        fts_count = cursor.fetchone()[0]
        print(f"FTS documents: {fts_count}")
        
        # Check symbols
        cursor = conn.execute("SELECT COUNT(*) FROM symbols")
        symbol_count = cursor.fetchone()[0]
        print(f"Symbols: {symbol_count}")
    
    # Create dispatcher (minimal config)
    print("\n2. CREATING DISPATCHER")
    print("-" * 40)
    dispatcher = EnhancedDispatcher(
        sqlite_store=store,
        enable_advanced_features=True,
        use_plugin_factory=False,  # Don't load plugins
        lazy_load=True,
        semantic_search_enabled=False,
        memory_aware=False,
        multi_repo_enabled=False  # Keep it simple
    )
    print(f"Dispatcher created")
    
    # Test 1: Direct SQLite FTS search
    print("\n3. DIRECT FTS SEARCH")
    print("-" * 40)
    
    test_queries = [
        "PathUtils",
        "get_workspace_root",
        "class",
        "def",
        "import os"
    ]
    
    for query in test_queries:
        results = store.search_code_fts(query, limit=5)
        print(f"\nQuery: '{query}' - Found {len(results)} results")
        for i, result in enumerate(results[:3]):
            print(f"  {i+1}. {result.get('filepath', 'N/A')}:{result.get('line', '?')}")
            if result.get('snippet'):
                snippet = result['snippet'].strip()[:60]
                print(f"     {snippet}...")
    
    # Test 2: Symbol lookup
    print("\n4. SYMBOL LOOKUP")
    print("-" * 40)
    
    symbols_to_find = ["PathUtils", "SQLiteStore", "EnhancedDispatcher"]
    
    for symbol in symbols_to_find:
        # Try fuzzy search
        results = store.search_symbols_fuzzy(symbol, limit=5)
        print(f"\nSymbol: '{symbol}' - Found {len(results)} matches")
        for i, result in enumerate(results[:3]):
            print(f"  {i+1}. {result.get('name', 'N/A')} in {result.get('file_path', 'N/A')}:{result.get('line', '?')}")
            print(f"     Kind: {result.get('kind', 'N/A')}")
    
    # Test 3: Dispatcher search
    print("\n5. DISPATCHER SEARCH")
    print("-" * 40)
    
    search_terms = ["PathUtils", "multi_repo", "def index_file"]
    
    for term in search_terms:
        print(f"\nSearching: '{term}'")
        try:
            results = list(dispatcher.search(term, semantic=False, limit=5))
            print(f"Found {len(results)} results")
            for i, result in enumerate(results[:3]):
                print(f"  {i+1}. {result.file}:{result.line}")
                if result.snippet:
                    snippet = result.snippet.strip()[:60]
                    print(f"     {snippet}...")
        except Exception as e:
            print(f"Error: {e}")
    
    # Test 4: Check specific files
    print("\n6. SPECIFIC FILE CHECK")
    print("-" * 40)
    
    files_to_check = [
        "/workspaces/Code-Index-MCP/mcp_server/core/path_utils.py",
        "/workspaces/Code-Index-MCP/mcp_server/dispatcher/dispatcher_enhanced.py",
        "/workspaces/Code-Index-MCP/mcp_server/storage/sqlite_store.py"
    ]
    
    for file_path in files_to_check:
        with store._get_connection() as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM files WHERE path = ?",
                (file_path,)
            )
            exists = cursor.fetchone()[0] > 0
            print(f"{file_path}: {'✓ Indexed' if exists else '✗ Not found'}")
    
    print("\n" + "=" * 60)
    print("✅ Direct query testing complete!")


if __name__ == "__main__":
    test_direct_queries()