#!/usr/bin/env python3
"""
Patch MCP server to work with test repository indexes.
"""

import os
import json
import shutil
from pathlib import Path
from mcp_server.core.path_utils import PathUtils

def create_test_mcp_configs():
    """Create MCP configurations for each test repository."""
    test_repos = [
        ("d8df70cdcd6e", "django", "PathUtils.get_workspace_root()/test_repos/web/python/django"),
        ("a91ba02537ca", "flask", "PathUtils.get_workspace_root()/test_repos/web/python/flask"),
        ("bb4442cd5cc6", "express", "PathUtils.get_workspace_root()/test_repos/web/javascript/express"),
        ("d72d7e1e17d2", "react", "PathUtils.get_workspace_root()/test_repos/web/javascript/react"),
    ]
    
    configs_created = []
    
    for repo_id, name, repo_path in test_repos:
        repo_path = Path(repo_path)
        if not repo_path.exists():
            print(f"Skipping {name}: repository not found")
            continue
        
        # Create .mcp-index.json in the repository
        mcp_index_config = {
            "version": "1.0",
            "index": {
                "include": ["**/*"],
                "exclude": [
                    ".git/**",
                    "node_modules/**",
                    "venv/**",
                    "__pycache__/**"
                ]
            }
        }
        
        config_path = repo_path / ".mcp-index.json"
        with open(config_path, 'w') as f:
            json.dump(mcp_index_config, f, indent=2)
        
        # Create symlink to the index
        index_source = Path(f"PathUtils.get_workspace_root()/.indexes/{repo_id}/code_index.db")
        index_target = repo_path / ".mcp-index" / "code_index.db"
        
        if index_source.exists():
            # Create .mcp-index directory
            index_target.parent.mkdir(exist_ok=True)
            
            # Remove existing symlink/file
            if index_target.exists():
                index_target.unlink()
            
            # Create symlink
            index_target.symlink_to(index_source)
            
            print(f"✓ Created index symlink for {name}")
            configs_created.append({
                "name": name,
                "path": str(repo_path),
                "index": str(index_target)
            })
        else:
            print(f"✗ Index not found for {name}")
    
    return configs_created


def test_mcp_in_repo(repo_path):
    """Test MCP functionality in a specific repository."""
    import subprocess
    import sys
    
    print(f"\nTesting MCP in {repo_path}")
    print("="*60)
    
    # Change to repository directory
    original_dir = os.getcwd()
    os.chdir(repo_path)
    
    try:
        # Test MCP server
        env = os.environ.copy()
        env['PYTHONPATH'] = 'PathUtils.get_workspace_root()'
        
        # Simple test script
        test_script = """
import sys
sys.path.insert(0, 'PathUtils.get_workspace_root()')
from mcp_server.utils.index_discovery import IndexDiscovery
from pathlib import Path

discovery = IndexDiscovery(Path.cwd())
if discovery.is_index_enabled():
    index_path = discovery.get_local_index_path()
    if index_path:
        print(f"✓ Index found: {index_path}")
        # Quick test query
        from mcp_server.storage.sqlite_store import SQLiteStore
        store = SQLiteStore(str(index_path))
        results = store.search_bm25("function", limit=3)
        print(f"✓ Search test: found {len(results)} results")
    else:
        print("✗ No index found")
else:
    print("✗ MCP not enabled")
"""
        
        result = subprocess.run(
            [sys.executable, "-c", test_script],
            env=env,
            capture_output=True,
            text=True
        )
        
        print(result.stdout)
        if result.stderr:
            print(f"Errors: {result.stderr}")
            
    finally:
        os.chdir(original_dir)


def main():
    """Main function."""
    print("Patching MCP for test repositories")
    print("="*80)
    
    # Create configurations
    configs = create_test_mcp_configs()
    
    print(f"\nCreated {len(configs)} configurations")
    
    # Test one repository
    if configs:
        test_repo = configs[0]
        test_mcp_in_repo(test_repo["path"])
    
    print("\nPatch complete!")
    print("\nTo use MCP with a test repository:")
    print("1. cd to the repository directory")
    print("2. The MCP tools should now find the index")


if __name__ == "__main__":
    main()