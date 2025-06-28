#!/usr/bin/env python3
"""
Test MCP multi-repository search functionality.
"""

import os
import sys
import json
import subprocess
import time
from pathlib import Path
from mcp_server.core.path_utils import PathUtils

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_mcp_search(query: str, repository: str = None):
    """Test MCP search with optional repository filter."""
    env = os.environ.copy()
    env['MCP_INDEX_STORAGE_PATH'] = 'PathUtils.get_workspace_root()/.indexes'
    env['MCP_ENABLE_MULTI_REPO'] = 'true'
    env['SEMANTIC_SEARCH_ENABLED'] = 'true'
    
    # Build command
    cmd = [
        sys.executable,
        "scripts/cli/mcp_server_cli.py",
        "search",
        "search_code",
        query
    ]
    
    if repository:
        cmd.extend(["--repository", repository])
    
    print(f"\n{'='*60}")
    print(f"Testing: {' '.join(cmd[-3:])}")
    if repository:
        print(f"Repository: {repository}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print("✅ Success!")
            # Try to parse JSON output
            try:
                data = json.loads(result.stdout)
                print(f"Results: {len(data.get('results', []))}")
                for i, res in enumerate(data.get('results', [])[:3]):
                    print(f"\nResult {i+1}:")
                    print(f"  File: {res.get('file', 'N/A')}")
                    print(f"  Repo: {res.get('repository', 'N/A')}")
                    print(f"  Score: {res.get('score', 'N/A')}")
            except:
                print(result.stdout[:500])
        else:
            print("❌ Failed!")
            print(f"Error: {result.stderr[:500]}")
            
    except subprocess.TimeoutExpired:
        print("⏱️ Timeout!")
    except Exception as e:
        print(f"❌ Error: {e}")


def test_cross_repo_search():
    """Test cross-repository search."""
    env = os.environ.copy()
    env['MCP_INDEX_STORAGE_PATH'] = 'PathUtils.get_workspace_root()/.indexes'
    env['MCP_ENABLE_MULTI_REPO'] = 'true'
    
    # Test JSON-RPC request
    request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "search_repositories",
            "arguments": {
                "query": "authentication",
                "limit": 10
            }
        },
        "id": 1
    }
    
    print(f"\n{'='*60}")
    print("Testing cross-repository search via JSON-RPC")
    print(f"{'='*60}")
    
    try:
        proc = subprocess.Popen(
            [sys.executable, "scripts/cli/mcp_server_cli.py"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env
        )
        
        # Send request
        stdout, stderr = proc.communicate(
            input=json.dumps(request) + "\n",
            timeout=30
        )
        
        print("Response:")
        print(stdout[:1000])
        
        if stderr:
            print("\nErrors:")
            print(stderr[:500])
            
    except subprocess.TimeoutExpired:
        print("⏱️ Timeout!")
        proc.kill()
    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    """Run multi-repo tests."""
    print("MCP Multi-Repository Test")
    print("="*80)
    
    # Test 1: Search without repository filter (should search all)
    test_mcp_search("async function")
    
    # Test 2: Search with specific repository
    test_mcp_search("useState", "react")
    
    # Test 3: Search Django repository
    test_mcp_search("Model", "django")
    
    # Test 4: Cross-repo search
    test_cross_repo_search()
    
    print("\n" + "="*80)
    print("Test complete!")


if __name__ == "__main__":
    main()