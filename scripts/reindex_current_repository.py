#!/usr/bin/env python3
"""
Reindex the current repository with proper BM25 content and symbols.
"""

import sys
import os
from pathlib import Path
import json
import shutil
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set environment variables
os.environ["MCP_ENABLE_MULTI_REPO"] = "true"
os.environ["MCP_INDEX_STORAGE_PATH"] = "/workspaces/Code-Index-MCP/.indexes"
os.environ["MCP_REPO_REGISTRY"] = "/workspaces/Code-Index-MCP/.indexes/repository_registry.json"
os.environ["PYTHONPATH"] = "/workspaces/Code-Index-MCP"

from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.core.path_utils import PathUtils
import hashlib


def reindex_current_repo():
    """Reindex the current repository."""
    print("Reindexing Current Repository")
    print("=" * 60)
    
    # Get paths
    workspace_root = PathUtils.get_workspace_root()
    repo_hash = "844145265d7a"  # Current repo hash
    index_dir = PathUtils.get_index_storage_path() / repo_hash
    index_path = index_dir / "code_index.db"
    
    print(f"Repository: {workspace_root}")
    print(f"Index path: {index_path}")
    
    # Backup existing index
    if index_path.exists():
        backup_path = index_path.with_suffix('.db.backup')
        shutil.copy2(index_path, backup_path)
        print(f"Backed up existing index to: {backup_path}")
        
        # Remove existing index to start fresh
        index_path.unlink()
        print("Removed existing index")
    
    # Create index directory if needed
    index_dir.mkdir(parents=True, exist_ok=True)
    
    # Create SQLite store
    store = SQLiteStore(str(index_path))
    print(f"Created new SQLite store")
    
    # Create dispatcher
    dispatcher = EnhancedDispatcher(
        sqlite_store=store,
        enable_advanced_features=True,
        use_plugin_factory=True,
        lazy_load=False,  # Load all plugins for indexing
        semantic_search_enabled=False,
        memory_aware=True,
        multi_repo_enabled=True
    )
    
    print(f"Dispatcher initialized with {len(dispatcher.supported_languages)} language support")
    
    # Index the repository
    print("\nStarting indexing...")
    stats = dispatcher.index_directory(
        workspace_root,
        recursive=True
    )
    
    print(f"\nIndexing complete!")
    print(f"  Total files: {stats.get('total_files', 0)}")
    print(f"  Indexed files: {stats.get('indexed_files', 0)}")
    print(f"  Ignored files: {stats.get('ignored_files', 0)}")
    print(f"  Failed files: {stats.get('failed_files', 0)}")
    
    # Verify BM25 content
    print("\nVerifying BM25 content...")
    conn = store._get_connection()
    cursor = conn.execute("SELECT COUNT(*) FROM bm25_content")
    bm25_count = cursor.fetchone()[0]
    print(f"  BM25 documents: {bm25_count}")
    
    # Check for symbols
    try:
        cursor = conn.execute("SELECT COUNT(*) FROM symbols")
        symbol_count = cursor.fetchone()[0]
        print(f"  Symbols: {symbol_count}")
    except:
        print(f"  Symbols: No symbols table")
    
    # Update registry
    print("\nUpdating repository registry...")
    update_registry(repo_hash, workspace_root, index_path, stats)
    
    print("\n✅ Reindexing complete!")
    return index_path


def update_registry(repo_hash, repo_path, index_path, stats):
    """Update repository registry."""
    registry_path = PathUtils.get_index_storage_path() / "repository_registry.json"
    
    # Load existing registry
    if registry_path.exists():
        with open(registry_path, 'r') as f:
            registry = json.load(f)
    else:
        registry = {}
    
    # Update current repo entry
    registry[repo_hash] = {
        "repository_id": repo_hash,
        "name": "Code-Index-MCP",
        "path": str(repo_path),
        "index_path": str(index_path),
        "language_stats": {"python": stats.get('indexed_files', 0)},
        "total_files": stats.get('indexed_files', 0),
        "total_symbols": 0,  # Will be updated after symbol extraction
        "indexed_at": datetime.now().isoformat(),
        "active": True,
        "priority": 10
    }
    
    # Save registry
    with open(registry_path, 'w') as f:
        json.dump(registry, f, indent=2)
    
    print(f"Updated registry: {registry_path}")


if __name__ == "__main__":
    reindex_current_repo()