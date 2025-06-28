#!/usr/bin/env python3
"""
Directly index test repositories using the Python API.
"""

import os
import sys
import time
from pathlib import Path
import json
import sqlite3
import hashlib

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.indexer.bm25_indexer import BM25Indexer
from mcp_server.plugin_system.plugin_manager import PluginManager
from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
from mcp_server.core.path_resolver import PathResolver


def get_repo_hash(repo_path: Path) -> str:
    """Get repository hash for centralized storage."""
    # Use path-based hash for test repos
    return hashlib.sha256(str(repo_path.resolve()).encode()).hexdigest()[:12]


def index_repository(repo_path: Path) -> bool:
    """Index a single repository."""
    print(f"Indexing {repo_path.name}...", end=" ", flush=True)
    
    try:
        # Get central storage location
        repo_hash = get_repo_hash(repo_path)
        central_dir = Path.home() / ".mcp" / "indexes" / repo_hash
        central_dir.mkdir(parents=True, exist_ok=True)
        
        # Create index database
        db_path = central_dir / "test_index.db"
        
        # Initialize storage
        storage = SQLiteStore(str(db_path))
        
        # Initialize plugin manager
        from mcp_server.plugin_system.models import PluginSystemConfig
        
        config = PluginSystemConfig()
        plugin_manager = PluginManager(config=config, sqlite_store=storage)
        
        # Initialize dispatcher
        dispatcher = EnhancedDispatcher(
            plugin_manager=plugin_manager,
            storage=storage
        )
        
        # Initialize path resolver
        path_resolver = PathResolver(base_path=repo_path)
        
        # Index the repository
        start_time = time.time()
        dispatcher.index(str(repo_path))
        elapsed = time.time() - start_time
        
        # Create symlink for current
        current_link = central_dir / "current.db"
        if current_link.exists():
            current_link.unlink()
        current_link.symlink_to("test_index.db")
        
        # Create metadata
        metadata = {
            "repository_path": str(repo_path),
            "indexed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "elapsed_seconds": elapsed,
            "branch": "main",
            "commit": "test"
        }
        
        with open(central_dir / "test_index.metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)
        
        # Check if indexing succeeded
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM documents")
        doc_count = cursor.fetchone()[0]
        conn.close()
        
        if doc_count > 0:
            print(f"✅ ({doc_count} docs, {elapsed:.1f}s)")
            return True
        else:
            print("❌ (no documents indexed)")
            return False
            
    except Exception as e:
        print(f"❌ ({str(e)[:50]}...)")
        return False


def main():
    """Main function."""
    print("Direct Repository Indexing")
    print("=" * 60)
    
    # Get test repos
    test_repos_dir = Path("/workspaces/Code-Index-MCP/test_repos")
    repos = []
    
    for git_dir in sorted(test_repos_dir.rglob(".git")):
        if git_dir.is_dir():
            repos.append(git_dir.parent)
    
    print(f"Found {len(repos)} repositories\n")
    
    # Index first 20 repos
    success = 0
    
    for i, repo in enumerate(repos[:20]):
        print(f"[{i+1}/20] ", end="")
        if index_repository(repo):
            success += 1
    
    print(f"\nSuccessfully indexed: {success}/20")
    
    # Verify indexes
    print("\nVerifying indexes...")
    verify_count = 0
    
    for repo in repos[:20]:
        repo_hash = get_repo_hash(repo)
        current_db = Path.home() / ".mcp" / "indexes" / repo_hash / "current.db"
        if current_db.exists():
            verify_count += 1
    
    print(f"Verified: {verify_count}/20 repositories have indexes")


if __name__ == "__main__":
    main()