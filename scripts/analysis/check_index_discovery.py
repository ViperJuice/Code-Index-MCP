#!/usr/bin/env python3
"""
Check what index the MCP discovery finds.
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set environment variables
os.environ["MCP_ENABLE_MULTI_REPO"] = "true"
os.environ["MCP_INDEX_STORAGE_PATH"] = "/workspaces/Code-Index-MCP/.indexes"
os.environ["MCP_REPO_REGISTRY"] = "/workspaces/Code-Index-MCP/.indexes/repository_registry.json"

from mcp_server.utils.index_discovery import IndexDiscovery
from mcp_server.config.index_paths import IndexPathConfig
from mcp_server.core.path_utils import PathUtils


def check_discovery():
    """Check index discovery."""
    print("Index Discovery Analysis")
    print("=" * 60)
    
    # Create discovery
    discovery = IndexDiscovery(Path.cwd(), enable_multi_path=True)
    
    # Get repo ID
    repo_id = discovery._get_repository_identifier()
    print(f"\nRepository ID: {repo_id}")
    
    # Get search paths
    path_config = IndexPathConfig()
    search_paths = path_config.get_search_paths(repo_id)
    
    print(f"\nSearch paths ({len(search_paths)}):")
    for i, path in enumerate(search_paths[:10]):
        exists = path.exists() if path else False
        print(f"  {i+1}. {path} {'[EXISTS]' if exists else '[missing]'}")
        
        # Check what indexes exist in this path
        if exists and path.is_dir():
            db_files = list(path.glob("*.db"))
            if db_files:
                print(f"     Found databases: {[f.name for f in db_files]}")
    
    # Find actual index
    index_path = discovery.get_local_index_path()
    print(f"\nDiscovered index: {index_path}")
    
    # Check .indexes directory
    print("\n.indexes directory contents:")
    indexes_dir = Path(".indexes")
    if indexes_dir.exists():
        for item in sorted(indexes_dir.iterdir()):
            if item.is_dir():
                db_files = list(item.glob("*.db"))
                if db_files:
                    print(f"  {item.name}/")
                    for db in db_files:
                        print(f"    - {db.name}")
    
    # Check if we can find the right index
    current_repo_hash = "844145265d7a"
    correct_index = indexes_dir / current_repo_hash / "code_index.db"
    print(f"\nCorrect index path: {correct_index}")
    print(f"Correct index exists: {correct_index.exists()}")


if __name__ == "__main__":
    check_discovery()