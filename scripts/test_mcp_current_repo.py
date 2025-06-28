#!/usr/bin/env python3
"""
Test MCP server functionality on current repository.
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from mcp_server.core.path_utils import PathUtils

def test_mcp_cli():
    """Test MCP CLI directly."""
    env = os.environ.copy()
    env['MCP_INDEX_STORAGE_PATH'] = str(PathUtils.get_index_storage_path())
    env['MCP_ENABLE_MULTI_REPO'] = 'true'
    env['MCP_REPO_REGISTRY'] = str(PathUtils.get_repo_registry_path())
    env['SEMANTIC_SEARCH_ENABLED'] = 'true'
    env['PYTHONPATH'] = str(PathUtils.get_workspace_root())
    
    # Test 1: Search in current repository
    print("Test 1: Search in current repository")
    print("="*60)
    
    cmd = [
        sys.executable,
        str(PathUtils.get_workspace_root() / "scripts/cli/mcp_server_cli.py"),
        "search",
        "search_code",
        "EnhancedDispatcher",
        "--limit", "5"
    ]
    
    try:
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=10)
        print(f"Exit code: {result.returncode}")
        print(f"Output: {result.stdout[:500]}")
        if result.stderr:
            print(f"Error: {result.stderr[:500]}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 2: Get status
    print("\n\nTest 2: Get status")
    print("="*60)
    
    cmd = [
        sys.executable,
        "PathUtils.get_workspace_root()/scripts/cli/mcp_server_cli.py",
        "status"
    ]
    
    try:
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=10)
        print(f"Exit code: {result.returncode}")
        print(f"Output: {result.stdout[:500]}")
        if result.stderr:
            print(f"Error: {result.stderr[:500]}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 3: Check if we can query Django index directly
    print("\n\nTest 3: Direct Django index query")
    print("="*60)
    
    # Create a test script that queries Django index
    test_script = """
import sys
sys.path.insert(0, 'PathUtils.get_workspace_root()')
from mcp_server.storage.sqlite_store import SQLiteStore

store = SQLiteStore('PathUtils.get_workspace_root()/.indexes/d8df70cdcd6e/code_index.db')
results = store.search_bm25('Model', limit=3)
print(f"Found {len(results)} results in Django")
for r in results:
    print(f"  - {r.file}:{r.line}")
"""
    
    result = subprocess.run([sys.executable, "-c", test_script], capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(f"Error: {result.stderr}")

if __name__ == "__main__":
    test_mcp_cli()