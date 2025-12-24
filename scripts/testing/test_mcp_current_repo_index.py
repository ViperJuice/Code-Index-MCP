#!/usr/bin/env python3
"""
Test MCP with current repository's migrated index.
"""

import sys
import os
from pathlib import Path
import json
import time

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set environment variables as if launched by Claude Code
os.environ["MCP_ENABLE_MULTI_REPO"] = "true"
os.environ["MCP_INDEX_STORAGE_PATH"] = "/workspaces/Code-Index-MCP/.indexes"
os.environ["MCP_REPO_REGISTRY"] = "/workspaces/Code-Index-MCP/.indexes/repository_registry.json"
os.environ["PYTHONPATH"] = "/workspaces/Code-Index-MCP"

from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.utils.index_discovery import IndexDiscovery
from mcp_server.core.path_utils import PathUtils


def test_current_repo():
    """Test MCP functionality with current repository."""
    print("Testing MCP with Current Repository")
    print("=" * 60)
    
    # Create dispatcher as MCP would
    print("\nInitializing MCP components...")
    
    # Find the current repo's index directly
    current_repo_id = "844145265d7a"  # From the migration
    index_path = Path(f".indexes/{current_repo_id}/code_index.db")
    
    if not index_path.exists():
        print(f"Error: Index not found at {index_path}")
        return
        
    print(f"Using index: {index_path}")
    
    # Create SQLite store
    store = SQLiteStore(str(index_path))
    
    # Create dispatcher
    dispatcher = EnhancedDispatcher(
        sqlite_store=store,
        enable_advanced_features=True,
        use_plugin_factory=True,
        lazy_load=True,
        semantic_search_enabled=False,  # Disable to avoid API key issues
        memory_aware=True,
        multi_repo_enabled=True  # Force enable
    )
    
    print(f"Multi-repo manager initialized: {dispatcher._multi_repo_manager is not None}")
    
    # Test 1: Symbol lookup
    print("\n[TEST 1] Symbol Lookup - PathUtils")
    print("-" * 40)
    start = time.time()
    result = dispatcher.lookup("PathUtils")
    elapsed = time.time() - start
    
    if result:
        print(f"✓ Found symbol in {elapsed:.3f}s")
        print(f"  File: {result.get('defined_in')}")
        print(f"  Line: {result.get('line')}")
        print(f"  Kind: {result.get('kind')}")
    else:
        print(f"✗ Symbol not found ({elapsed:.3f}s)")
    
    # Test 2: Code search
    print("\n[TEST 2] Code Search - 'def get_workspace_root'")
    print("-" * 40)
    start = time.time()
    results = list(dispatcher.search("def get_workspace_root", semantic=False, limit=5))
    elapsed = time.time() - start
    
    print(f"Found {len(results)} results in {elapsed:.3f}s")
    for i, result in enumerate(results[:3]):
        print(f"  {i+1}. {result.file}:{result.line}")
        print(f"     Score: {result.score:.3f}")
        if result.snippet:
            preview = result.snippet.strip()[:60]
            print(f"     Preview: {preview}...")
    
    # Test 3: Direct BM25 search
    print("\n[TEST 3] Direct BM25 Search - 'multi_repo_manager'")
    print("-" * 40)
    start = time.time()
    bm25_results = store.search_bm25("multi_repo_manager", limit=5)
    elapsed = time.time() - start
    
    print(f"Found {len(bm25_results)} BM25 results in {elapsed:.3f}s")
    for i, result in enumerate(bm25_results[:3]):
        print(f"  {i+1}. {result['filepath']}:{result.get('line_number', '?')}")
        print(f"     Score: {result['score']:.3f}")
    
    # Test 4: Check BM25 content quality
    print("\n[TEST 4] BM25 Content Check")
    print("-" * 40)
    # Get a sample of BM25 content
    conn = store.conn
    cursor = conn.execute("""
        SELECT filepath, substr(content, 1, 100) 
        FROM bm25_content 
        WHERE content NOT LIKE '%[hash]%'
        LIMIT 3
    """)
    
    valid_content = 0
    for filepath, content in cursor.fetchall():
        valid_content += 1
        print(f"  {filepath}")
        print(f"    Content: {content[:60]}...")
    
    if valid_content > 0:
        print(f"\n✓ BM25 content contains actual file text")
    else:
        print(f"\n✗ BM25 content appears to be corrupted")
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary:")
    print(f"  - Multi-repo support: {'✓ Enabled' if dispatcher._multi_repo_manager else '✗ Disabled'}")
    print(f"  - Index location: {index_path}")
    print(f"  - BM25 content: {'✓ Valid' if valid_content > 0 else '✗ Corrupted'}")


if __name__ == "__main__":
    test_current_repo()