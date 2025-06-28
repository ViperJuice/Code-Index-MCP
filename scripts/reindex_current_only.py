#!/usr/bin/env python3
"""
Reindex only the current repository (excluding test_repos).
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
from mcp_server.plugins.language_registry import get_language_by_extension
import hashlib


def should_index_file(file_path):
    """Check if file should be indexed."""
    path_str = str(file_path)
    
    # Exclude test repositories
    if '/test_repos/' in path_str:
        return False
        
    # Exclude .git and other hidden directories
    parts = Path(path_str).parts
    for part in parts:
        if part.startswith('.') and part not in ['.github', '.vscode']:
            return False
    
    # Exclude specific directories
    exclude_dirs = ['__pycache__', 'node_modules', 'venv', 'env', '.pytest_cache', 
                    '.mypy_cache', '.coverage', 'dist', 'build', '.eggs']
    for exclude in exclude_dirs:
        if exclude in parts:
            return False
    
    # Check if it's a supported file type
    suffix = file_path.suffix.lower()
    if suffix in ['.pyc', '.pyo', '.so', '.dll', '.dylib', '.egg', '.whl']:
        return False
        
    return True


def reindex_current_repo():
    """Reindex the current repository."""
    print("Reindexing Current Repository (excluding test_repos)")
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
    
    # Index files manually with filtering
    print("\nStarting selective indexing...")
    stats = {
        "total_files": 0,
        "indexed_files": 0,
        "skipped_files": 0,
        "failed_files": 0
    }
    
    # Walk through repository
    for file_path in workspace_root.rglob('*'):
        if file_path.is_file():
            stats["total_files"] += 1
            
            if should_index_file(file_path):
                try:
                    dispatcher.index_file(file_path)
                    stats["indexed_files"] += 1
                    
                    if stats["indexed_files"] % 100 == 0:
                        print(f"  Indexed {stats['indexed_files']} files...")
                        
                except Exception as e:
                    stats["failed_files"] += 1
                    if "test_repos" not in str(file_path):
                        print(f"  Failed to index {file_path}: {e}")
            else:
                stats["skipped_files"] += 1
    
    print(f"\nIndexing complete!")
    print(f"  Total files: {stats['total_files']}")
    print(f"  Indexed files: {stats['indexed_files']}")
    print(f"  Skipped files: {stats['skipped_files']}")
    print(f"  Failed files: {stats['failed_files']}")
    
    # Verify BM25 content
    print("\nVerifying BM25 content...")
    with store._get_connection() as conn:
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
        
        # Check if PathUtils is indexed
        cursor = conn.execute("""
            SELECT COUNT(*) FROM bm25_content 
            WHERE content LIKE '%class PathUtils%'
        """)
        pathutils_count = cursor.fetchone()[0]
        print(f"  Files containing 'class PathUtils': {pathutils_count}")
    
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