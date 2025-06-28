#!/usr/bin/env python3
"""
Simple comprehensive indexing using existing MCP infrastructure.
"""

import sys
import os
from pathlib import Path
import json
import time
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set environment variables
os.environ["MCP_ENABLE_MULTI_REPO"] = "true"
os.environ["MCP_INDEX_STORAGE_PATH"] = "/workspaces/Code-Index-MCP/.indexes"
os.environ["PYTHONPATH"] = "/workspaces/Code-Index-MCP"

from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.core.path_utils import PathUtils
from mcp_server.indexer.bm25_indexer import BM25Indexer


def main():
    """Main indexing function."""
    print("\nSIMPLE COMPREHENSIVE INDEXING")
    print("=" * 60)
    
    # Setup paths
    workspace_root = PathUtils.get_workspace_root()
    repo_hash = "844145265d7a"
    index_dir = PathUtils.get_index_storage_path() / repo_hash
    index_path = index_dir / "code_index.db"
    
    print(f"Repository: {workspace_root}")
    print(f"Index path: {index_path}")
    
    # Ensure directory exists
    index_dir.mkdir(parents=True, exist_ok=True)
    
    # Create fresh SQLite store
    store = SQLiteStore(str(index_path))
    print("✓ Created SQLite store")
    
    # Create BM25 indexer
    bm25_indexer = BM25Indexer(store)
    print("✓ Created BM25 indexer")
    
    # Create dispatcher with all plugins
    print("\nInitializing dispatcher with plugins...")
    dispatcher = EnhancedDispatcher(
        sqlite_store=store,
        enable_advanced_features=True,
        use_plugin_factory=True,
        lazy_load=False,  # Load all plugins for indexing
        semantic_search_enabled=False,
        memory_aware=True,
        multi_repo_enabled=False  # Single repo indexing
    )
    print(f"✓ Dispatcher ready with {len(dispatcher.supported_languages)} language support")
    
    # Index the repository
    print(f"\nIndexing {workspace_root}...")
    start_time = time.time()
    
    # Use dispatcher's built-in indexing
    stats = dispatcher.index_directory(workspace_root, recursive=True)
    
    # Also ensure BM25 is populated
    print("\nEnsuring BM25 population...")
    with store._get_connection() as conn:
        # Check if we need to populate BM25 from files/symbols
        cursor = conn.execute("SELECT COUNT(*) FROM files")
        file_count = cursor.fetchone()[0]
        
        cursor = conn.execute("SELECT COUNT(*) FROM symbols")  
        symbol_count = cursor.fetchone()[0]
        
        # Check BM25 tables
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'bm25%'")
        bm25_tables = [row[0] for row in cursor.fetchall()]
        
        print(f"  Files: {file_count}")
        print(f"  Symbols: {symbol_count}")
        print(f"  BM25 tables: {bm25_tables}")
        
        # If we have bm25_content table, check its content
        if 'bm25_content' in bm25_tables:
            cursor = conn.execute("SELECT COUNT(*) FROM bm25_content")
            bm25_count = cursor.fetchone()[0]
            print(f"  BM25 documents: {bm25_count}")
        
        # If we have fts_code table, check it
        if 'fts_code' in bm25_tables:
            cursor = conn.execute("SELECT COUNT(*) FROM fts_code")
            fts_count = cursor.fetchone()[0]
            print(f"  FTS documents: {fts_count}")
    
    # Optimize
    print("\nOptimizing indexes...")
    try:
        bm25_indexer.optimize()
        print("✓ BM25 optimization complete")
    except:
        print("⚠ BM25 optimization skipped")
    
    elapsed_time = time.time() - start_time
    
    # Update registry
    print("\nUpdating registry...")
    registry_path = PathUtils.get_index_storage_path() / "repository_registry.json"
    
    if registry_path.exists():
        with open(registry_path, 'r') as f:
            registry = json.load(f)
    else:
        registry = {}
    
    registry[repo_hash] = {
        "repository_id": repo_hash,
        "name": "Code-Index-MCP",
        "path": str(workspace_root),
        "index_path": str(index_path),
        "language_stats": stats.get("by_language", {}),
        "total_files": stats.get("indexed_files", 0),
        "total_symbols": symbol_count if 'symbol_count' in locals() else 0,
        "indexed_at": datetime.now().isoformat(),
        "active": True,
        "priority": 10
    }
    
    with open(registry_path, 'w') as f:
        json.dump(registry, f, indent=2)
    
    print("✓ Registry updated")
    
    # Summary
    print("\n" + "=" * 60)
    print("INDEXING COMPLETE")
    print("=" * 60)
    print(f"Total files: {stats.get('total_files', 0)}")
    print(f"Indexed files: {stats.get('indexed_files', 0)}")
    print(f"Failed files: {stats.get('failed_files', 0)}")
    print(f"Ignored files: {stats.get('ignored_files', 0)}")
    print(f"Time taken: {elapsed_time:.2f} seconds")
    
    if stats.get("by_language"):
        print("\nLanguage breakdown:")
        for lang, count in sorted(stats["by_language"].items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {lang}: {count} files")
    
    print(f"\n✅ Index ready at: {index_path}")


if __name__ == "__main__":
    main()