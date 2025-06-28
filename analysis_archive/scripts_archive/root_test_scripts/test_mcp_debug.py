#\!/usr/bin/env python3
"""
Debug test of MCP functionality.
"""

import sqlite3
from pathlib import Path
import json
import subprocess
import sys
import time

def test_bm25_direct():
    """Test BM25 index directly."""
    print("1. Testing BM25 Index Directly")
    print("-" * 50)
    
    index_path = Path.home() / ".mcp/indexes/f7b49f5d0ae0/main_f48abb0.db"
    
    if not index_path.exists():
        print(f"✗ Index not found at {index_path}")
        return False
    
    conn = sqlite3.connect(str(index_path))
    cursor = conn.cursor()
    
    # Test queries
    test_queries = [
        ("BM25Indexer", "class BM25Indexer"),
        ("SQLiteStore", "class SQLiteStore"),
        ("reranking", "reranking")
    ]
    
    all_good = True
    for name, query in test_queries:
        cursor.execute("""
            SELECT filepath, snippet(bm25_content, -1, '<<', '>>', '...', 20), language
            FROM bm25_content
            WHERE bm25_content MATCH ?
            ORDER BY rank
            LIMIT 3
        """, (query,))
        
        results = cursor.fetchall()
        if results:
            print(f"✓ {name}: {len(results)} results found")
            print(f"  First result: {results[0][0]}")
        else:
            print(f"✗ {name}: No results")
            all_good = False
    
    conn.close()
    return all_good

def test_mcp_initialization():
    """Test MCP server initialization."""
    print("\n2. Testing MCP Server Initialization")
    print("-" * 50)
    
    # Create initialization request
    init_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "clientInfo": {"name": "test", "version": "1.0"}
        }
    }
    
    # Create initialized notification
    initialized_notif = {
        "jsonrpc": "2.0",
        "method": "initialized",
        "params": {}
    }
    
    # Run MCP server
    proc = subprocess.Popen(
        [sys.executable, "scripts/cli/mcp_server_cli.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    try:
        # Send initialization
        proc.stdin.write(json.dumps(init_request) + "\n")
        proc.stdin.flush()
        
        # Read response
        response_line = proc.stdout.readline()
        if response_line:
            response = json.loads(response_line)
            if "result" in response:
                print("✓ Server initialized successfully")
                capabilities = response["result"].get("capabilities", {})
                tools = capabilities.get("tools", {})
                print(f"  Tools available: {len(tools)} tools")
                
                # Send initialized notification
                proc.stdin.write(json.dumps(initialized_notif) + "\n")
                proc.stdin.flush()
                
                return True, proc
            else:
                print(f"✗ Initialization failed: {response}")
                proc.terminate()
                return False, None
        else:
            print("✗ No response from server")
            proc.terminate()
            return False, None
            
    except Exception as e:
        print(f"✗ Error during initialization: {e}")
        proc.terminate()
        return False, None

def test_mcp_tools(proc):
    """Test MCP tools."""
    print("\n3. Testing MCP Tools")
    print("-" * 50)
    
    # Test tool list request
    list_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {}
    }
    
    proc.stdin.write(json.dumps(list_request) + "\n")
    proc.stdin.flush()
    
    response_line = proc.stdout.readline()
    if response_line:
        response = json.loads(response_line)
        if "result" in response:
            tools = response["result"].get("tools", [])
            print(f"✓ Found {len(tools)} tools:")
            for tool in tools[:5]:
                print(f"  - {tool['name']}: {tool.get('description', '')[:60]}...")
            return True
        else:
            print(f"✗ Tool list failed: {response}")
            return False
    else:
        print("✗ No response for tool list")
        return False

def test_mcp_search(proc):
    """Test MCP search functionality."""
    print("\n4. Testing MCP Search")
    print("-" * 50)
    
    # Test search_code tool
    search_request = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "search_code",
            "arguments": {
                "query": "BM25Indexer",
                "limit": 3
            }
        }
    }
    
    start_time = time.time()
    proc.stdin.write(json.dumps(search_request) + "\n")
    proc.stdin.flush()
    
    response_line = proc.stdout.readline()
    elapsed = time.time() - start_time
    
    if response_line:
        response = json.loads(response_line)
        if "result" in response:
            # Parse the result content
            content = response["result"][0]["text"]
            results = json.loads(content)
            
            print(f"✓ Search completed in {elapsed:.3f}s")
            print(f"  Found {len(results)} results")
            if results:
                print(f"  First result: {results[0]['file']}")
            return True
        else:
            print(f"✗ Search failed: {response}")
            return False
    else:
        print("✗ No response for search")
        return False

def test_mcp_lookup(proc):
    """Test MCP symbol lookup."""
    print("\n5. Testing MCP Symbol Lookup")
    print("-" * 50)
    
    # Test symbol_lookup tool
    lookup_request = {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {
            "name": "symbol_lookup",
            "arguments": {
                "symbol": "SQLiteStore"
            }
        }
    }
    
    start_time = time.time()
    proc.stdin.write(json.dumps(lookup_request) + "\n")
    proc.stdin.flush()
    
    response_line = proc.stdout.readline()
    elapsed = time.time() - start_time
    
    if response_line:
        response = json.loads(response_line)
        if "result" in response:
            # Parse the result content
            content = response["result"][0]["text"]
            result = json.loads(content)
            
            print(f"✓ Lookup completed in {elapsed:.3f}s")
            print(f"  Symbol: {result['symbol']}")
            print(f"  File: {result['defined_in']}")
            print(f"  Kind: {result['kind']}")
            return True
        else:
            print(f"✗ Lookup failed: {response}")
            return False
    else:
        print("✗ No response for lookup")
        return False

def main():
    """Run MCP tests."""
    print("MCP Functionality Test")
    print("=" * 80)
    
    # Test 1: BM25 Direct
    bm25_ok = test_bm25_direct()
    
    # Test 2: MCP Initialization
    mcp_ok, proc = test_mcp_initialization()
    
    if mcp_ok and proc:
        # Test 3: Tool List
        tools_ok = test_mcp_tools(proc)
        
        # Test 4: Search
        search_ok = test_mcp_search(proc)
        
        # Test 5: Lookup
        lookup_ok = test_mcp_lookup(proc)
        
        # Cleanup
        proc.terminate()
        
        # Summary
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"BM25 Direct Access: {'✓' if bm25_ok else '✗'}")
        print(f"MCP Initialization: {'✓' if mcp_ok else '✗'}")
        print(f"MCP Tools List: {'✓' if tools_ok else '✗'}")
        print(f"MCP Search: {'✓' if search_ok else '✗'}")
        print(f"MCP Symbol Lookup: {'✓' if lookup_ok else '✗'}")
        
        if all([bm25_ok, mcp_ok, tools_ok, search_ok, lookup_ok]):
            print("\n✓ All tests passed\! MCP is working correctly.")
            return 0
        else:
            print("\n✗ Some tests failed. Check the output above.")
            return 1
    else:
        print("\n✗ MCP initialization failed. Cannot proceed with tests.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
