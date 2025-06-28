#!/usr/bin/env python3
"""
Diagnose MCP multi-repository initialization.
"""

import sys
import os
from pathlib import Path

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


def diagnose_multi_repo():
    """Diagnose multi-repository setup."""
    print("MCP Multi-Repository Diagnostic")
    print("=" * 60)
    
    # Check environment
    print("\nEnvironment Variables:")
    print(f"  MCP_ENABLE_MULTI_REPO: {os.environ.get('MCP_ENABLE_MULTI_REPO')}")
    print(f"  MCP_INDEX_STORAGE_PATH: {os.environ.get('MCP_INDEX_STORAGE_PATH')}")
    print(f"  MCP_REPO_REGISTRY: {os.environ.get('MCP_REPO_REGISTRY')}")
    
    # Find index using discovery
    print("\nIndex Discovery:")
    discovery = IndexDiscovery(Path.cwd(), enable_multi_path=True)
    index_path = discovery.get_local_index_path()
    
    if index_path:
        print(f"  Found index: {index_path}")
        
        # Create SQLite store
        store = SQLiteStore(str(index_path))
        
        # Create dispatcher
        print("\nCreating Enhanced Dispatcher...")
        dispatcher = EnhancedDispatcher(
            sqlite_store=store,
            enable_advanced_features=True,
            use_plugin_factory=True,
            lazy_load=True,
            semantic_search_enabled=True,
            memory_aware=True,
            multi_repo_enabled=None  # Should auto-detect from env
        )
        
        # Check if multi-repo was initialized
        print("\nMulti-Repository Status:")
        print(f"  Has _multi_repo_manager: {hasattr(dispatcher, '_multi_repo_manager')}")
        if hasattr(dispatcher, '_multi_repo_manager'):
            print(f"  _multi_repo_manager is None: {dispatcher._multi_repo_manager is None}")
            
            if dispatcher._multi_repo_manager:
                # Test the manager
                repos = dispatcher._multi_repo_manager.list_repositories()
                print(f"  Registered repositories: {len(repos)}")
                for repo in repos[:3]:
                    print(f"    - {repo.name} ({repo.repository_id})")
        
        # Test a search
        print("\nTesting search_code...")
        try:
            results = dispatcher.search_code("PathUtils", limit=5)
            print(f"  Found {len(results)} results")
            for result in results[:3]:
                print(f"    - {result.file}:{result.line}")
        except Exception as e:
            print(f"  Error: {e}")
            import traceback
            traceback.print_exc()
            
    else:
        print("  No index found!")
        
        # Check registry directly
        registry_path = Path(os.environ.get("MCP_REPO_REGISTRY", ""))
        if registry_path.exists():
            print(f"\nRegistry exists at: {registry_path}")
            import json
            with open(registry_path) as f:
                registry = json.load(f)
            print(f"Registry contains {len(registry)} repositories")


if __name__ == "__main__":
    diagnose_multi_repo()