#!/usr/bin/env python3
"""
Debug MCP tool responses to understand why they return empty results.
"""

import asyncio
import json
import sys
import subprocess
from pathlib import Path

# Test 1: Check if MCP server is accessible
def test_mcp_server():
    """Test if MCP server starts and responds."""
    print("Test 1: MCP Server Accessibility")
    print("-" * 40)
    
    cmd = ["python", "scripts/cli/mcp_server_cli.py"]
    env = {
        "PYTHONPATH": "/workspaces/Code-Index-MCP",
        "MCP_LOG_LEVEL": "DEBUG"
    }
    
    try:
        # Start MCP server and send a simple request
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={**os.environ, **env},
            text=True
        )
        
        # Send initialization request
        init_request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "capabilities": {}
            },
            "id": 1
        }
        
        proc.stdin.write(json.dumps(init_request) + "\n")
        proc.stdin.flush()
        
        # Read response
        response = proc.stdout.readline()
        print(f"Response: {response}")
        
        # Terminate
        proc.terminate()
        
    except Exception as e:
        print(f"Error: {e}")


# Test 2: Direct Python API test
def test_direct_api():
    """Test MCP tools via direct Python API."""
    print("\nTest 2: Direct Python API")
    print("-" * 40)
    
    sys.path.insert(0, "/workspaces/Code-Index-MCP")
    
    try:
        from scripts.cli.mcp_server_cli import dispatcher, initialize_services
        
        # Initialize services
        asyncio.run(initialize_services())
        
        if dispatcher:
            # Test symbol lookup
            result = dispatcher.lookup("IndexManager")
            print(f"Symbol lookup result: {result}")
            
            # Test search
            search_results = list(dispatcher.search("centralized storage", limit=5))
            print(f"Search results: {len(search_results)} found")
            for r in search_results[:2]:
                print(f"  - {r.get('file')}:{r.get('line')}")
        else:
            print("Dispatcher not initialized")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


# Test 3: Check index content
def test_index_content():
    """Check if index has data."""
    print("\nTest 3: Index Content Check")
    print("-" * 40)
    
    import sqlite3
    
    # Check main repo index
    index_path = Path.home() / ".mcp" / "indexes" / "f7b49f5d0ae0" / "current.db"
    
    if index_path.exists():
        try:
            conn = sqlite3.connect(str(index_path))
            cursor = conn.cursor()
            
            # Check documents
            cursor.execute("SELECT COUNT(*) FROM documents")
            doc_count = cursor.fetchone()[0]
            print(f"Documents in index: {doc_count}")
            
            # Check BM25 index
            cursor.execute("SELECT COUNT(*) FROM bm25_index")
            bm25_count = cursor.fetchone()[0]
            print(f"BM25 entries: {bm25_count}")
            
            # Sample search
            cursor.execute("""
                SELECT filepath, snippet 
                FROM bm25_index 
                WHERE bm25_index MATCH 'IndexManager' 
                LIMIT 5
            """)
            results = cursor.fetchall()
            print(f"Sample BM25 search results: {len(results)}")
            for filepath, snippet in results:
                print(f"  - {filepath}: {snippet[:50]}...")
            
            conn.close()
            
        except Exception as e:
            print(f"Error reading index: {e}")
    else:
        print(f"Index not found at {index_path}")


# Test 4: Test MCP in isolation
def test_mcp_isolation():
    """Test MCP functionality in isolation."""
    print("\nTest 4: MCP Isolation Test")
    print("-" * 40)
    
    # Create a minimal test to see if MCP tools work at all
    test_query = "class IndexManager"
    
    print(f"Testing query: '{test_query}'")
    
    # Compare grep vs theoretical MCP
    print("\nGrep results:")
    grep_result = subprocess.run(
        ["grep", "-r", "-n", test_query, "/workspaces/Code-Index-MCP", "--include=*.py"],
        capture_output=True,
        text=True
    )
    
    lines = grep_result.stdout.strip().split('\n')[:5]
    for line in lines:
        if line:
            print(f"  {line}")
    
    print(f"\nTotal grep matches: {len(grep_result.stdout.strip().split('\n'))}")


if __name__ == "__main__":
    import os
    
    print("MCP Tool Debugging")
    print("=" * 60)
    
    test_mcp_server()
    test_direct_api()
    test_index_content()
    test_mcp_isolation()
    
    print("\n" + "=" * 60)
    print("Debugging complete")