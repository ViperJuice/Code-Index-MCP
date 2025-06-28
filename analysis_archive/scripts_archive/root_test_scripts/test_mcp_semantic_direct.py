#!/usr/bin/env python3
"""Test MCP server semantic search directly."""

import subprocess
import json
import sys
import os

# Set environment variables
env = os.environ.copy()
env['VOYAGE_AI_API_KEY'] = 'pa-Fdhj97wixjABvuP4oGuOgNTgjoPM3-ovbmg-4VktTnL'
env['PYTHONPATH'] = '/workspaces/Code-Index-MCP'

# Test queries
test_queries = [
    # BM25 queries (keyword-based)
    ("symbol_lookup", {"symbol": "EnhancedDispatcher"}, False),
    ("search_code", {"query": "def search", "limit": 5}, False),
    
    # Semantic queries (natural language)
    ("search_code", {"query": "how to initialize a class", "semantic": True, "limit": 5}, True),
    ("search_code", {"query": "error handling in main function", "semantic": True, "limit": 5}, True),
]

print("Testing MCP server semantic search...\n")

for tool, params, is_semantic in test_queries:
    query_type = "Semantic" if is_semantic else "BM25"
    print(f"\n=== {query_type} Query: {tool} with {params} ===")
    
    # Prepare MCP request
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool,
            "arguments": params
        }
    }
    
    # Run MCP server with request
    cmd = [
        sys.executable,
        "/workspaces/Code-Index-MCP/scripts/cli/mcp_server_cli.py"
    ]
    
    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True
        )
        
        # Send request
        stdout, stderr = proc.communicate(input=json.dumps(request))
        
        # Parse response
        if stdout:
            try:
                # Extract JSON from stdout
                lines = stdout.strip().split('\n')
                for line in lines:
                    if line.strip().startswith('{'):
                        response = json.loads(line)
                        if 'result' in response:
                            results = response['result']
                            if isinstance(results, list) and results:
                                content = results[0].get('content', {})
                                if isinstance(content, str):
                                    try:
                                        content = json.loads(content)
                                    except:
                                        pass
                                
                                print(f"Response: {json.dumps(content, indent=2)[:500]}...")
                            else:
                                print("No results returned")
                        break
            except json.JSONDecodeError as e:
                print(f"Failed to parse response: {e}")
                print(f"Raw output: {stdout[:200]}...")
        
        if stderr:
            print(f"Errors: {stderr[:200]}...")
            
    except Exception as e:
        print(f"Error running MCP server: {e}")

print("\n\nTest complete!")