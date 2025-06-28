#!/usr/bin/env python3
"""
Test MCP functionality with existing indexes.
"""

import subprocess
import json
from pathlib import Path
import time

def test_mcp_search(query):
    """Test MCP search functionality."""
    print(f"\nTesting MCP search with query: '{query}'")
    
    # Call MCP server
    cmd = [
        "/usr/local/bin/python",
        "/workspaces/Code-Index-MCP/scripts/cli/mcp_server_cli.py"
    ]
    
    # Create MCP request
    request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "search",
            "arguments": {
                "query": query,
                "limit": 5
            }
        },
        "id": 1
    }
    
    try:
        # Send request
        result = subprocess.run(
            cmd,
            input=json.dumps(request),
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print(f"Success! Output length: {len(result.stdout)} chars")
            
            # Try to parse response
            try:
                response = json.loads(result.stdout)
                if 'result' in response and 'content' in response['result']:
                    results = response['result']['content']
                    if isinstance(results, list):
                        print(f"Found {len(results)} results")
                        for i, r in enumerate(results[:3]):
                            if 'text' in r:
                                print(f"  {i+1}. {r['text'][:100]}...")
                    else:
                        print(f"Content: {str(results)[:200]}...")
                else:
                    print("Response structure:", json.dumps(response, indent=2)[:500])
            except json.JSONDecodeError:
                print(f"Raw output: {result.stdout[:500]}...")
        else:
            print(f"Error! Return code: {result.returncode}")
            print(f"Stderr: {result.stderr[:500]}")
            
    except subprocess.TimeoutExpired:
        print("Request timed out!")
    except Exception as e:
        print(f"Error: {e}")

def check_available_indexes():
    """Check which indexes are available."""
    index_dir = Path('.indexes')
    indexes = []
    
    for subdir in index_dir.iterdir():
        if subdir.is_dir():
            db_path = subdir / 'code_index.db'
            metadata_path = subdir / 'metadata.json'
            
            if db_path.exists() and metadata_path.exists():
                try:
                    with open(metadata_path) as f:
                        metadata = json.load(f)
                    indexes.append({
                        'hash': subdir.name,
                        'name': metadata.get('repository', 'Unknown'),
                        'language': metadata.get('language', 'Unknown'),
                        'stats': metadata.get('stats', {})
                    })
                except:
                    pass
    
    print(f"Found {len(indexes)} indexes:")
    for idx in indexes[:10]:
        stats = idx['stats']
        if 'bm25_count' in stats:
            print(f"  - {idx['name']} ({idx['language']}): {stats.get('bm25_count', 0)} documents")
    
    return indexes

def main():
    """Main test function."""
    print("MCP Index Testing")
    print("=" * 60)
    
    # Check available indexes
    indexes = check_available_indexes()
    
    if not indexes:
        print("No indexes found!")
        return
    
    # Test queries
    test_queries = [
        "function",
        "class",
        "import",
        "test",
        "error handling",
        "configuration",
        "database connection",
        "authentication"
    ]
    
    print(f"\nRunning {len(test_queries)} test queries...")
    
    for query in test_queries:
        test_mcp_search(query)
        time.sleep(0.5)  # Small delay between queries

if __name__ == "__main__":
    main()