#!/usr/bin/env python3
"""
Debug MCP search to understand why it returns 0 results.
"""

import os
import sys
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from mcp_server.core.path_utils import PathUtils

def test_mcp_search_with_debug():
    """Test MCP search with debug logging."""
    env = os.environ.copy()
    env['MCP_WORKSPACE_ROOT'] = str(PathUtils.get_workspace_root())
    env['MCP_INDEX_STORAGE_PATH'] = str(PathUtils.get_index_storage_path())
    env['MCP_REPO_REGISTRY'] = str(PathUtils.get_repo_registry_path())
    env['MCP_ENABLE_MULTI_REPO'] = 'true'
    env['MCP_ENABLE_MULTI_PATH'] = 'true'
    env['SEMANTIC_SEARCH_ENABLED'] = 'false'  # Disable semantic to test BM25
    env['PYTHONPATH'] = str(PathUtils.get_workspace_root())
    env['MCP_DEBUG'] = 'true'  # Enable debug logging
    
    print("Testing MCP search with debug logging...")
    print("=" * 60)
    
    # Test 1: Simple query
    print("\n[Test 1: Simple query 'def']")
    cmd = [
        sys.executable,
        str(PathUtils.get_workspace_root() / "scripts/cli/mcp_server_cli.py"),
        "search",
        "search_code",
        "def",
        "--limit", "5"
    ]
    
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    print(f"Exit code: {result.returncode}")
    print(f"Output:\n{result.stdout}")
    if result.stderr:
        print(f"Stderr:\n{result.stderr}")
    
    # Test 2: Check current repository index
    print("\n\n[Test 2: Check if current repo is indexed]")
    
    # Look for the current repo's index
    from mcp_server.storage.multi_repo_manager import MultiRepoIndexManager
    import hashlib
    
    current_repo_path = str(PathUtils.get_workspace_root())
    repo_hash = hashlib.sha256(current_repo_path.encode()).hexdigest()[:12]
    current_index = PathUtils.get_index_storage_path() / repo_hash / "code_index.db"
    
    print(f"Current repo path: {current_repo_path}")
    print(f"Expected repo hash: {repo_hash}")
    print(f"Expected index path: {current_index}")
    print(f"Index exists: {current_index.exists()}")
    
    if not current_index.exists():
        # Check if there's a 'current' directory
        current_alt = PathUtils.get_index_storage_path() / "current" / "code_index.db"
        if current_alt.exists():
            print(f"Found index at alternate location: {current_alt}")
            current_index = current_alt
    
    # Test 3: Direct dispatcher test
    print("\n\n[Test 3: Direct dispatcher test]")
    test_script = f"""
import sys
sys.path.insert(0, '{PathUtils.get_workspace_root()}')

from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
from mcp_server.storage.sqlite_store import SQLiteStore

# Find an index to test with
from pathlib import Path
index_path = Path('{PathUtils.get_index_storage_path()}')
db_files = list(index_path.glob('*/code_index.db'))

if db_files:
    db_file = db_files[0]
    print(f"Testing with index: {{db_file}}")
    
    store = SQLiteStore(str(db_file))
    dispatcher = EnhancedDispatcher(
        sqlite_store=store,
        enable_semantic=False,
        lazy_load=False
    )
    
    results = list(dispatcher.search("def", semantic=False, limit=5))
    print(f"\\nDispatcher search results: {{len(results)}} found")
    
    for i, result in enumerate(results[:3]):
        print(f"  {{i+1}}. {{result.file_path}}:{{result.line}}")
else:
    print("No index databases found!")
"""
    
    result = subprocess.run([sys.executable, "-c", test_script], capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(f"Stderr: {result.stderr}")

if __name__ == "__main__":
    test_mcp_search_with_debug()