#!/usr/bin/env python3
"""Test MCP protocol directly by simulating Claude's tool calls."""
import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path

async def test_mcp_protocol():
    """Test MCP protocol by sending requests directly to the server."""
    print("Starting MCP server process...")
    
    # Start the MCP server as a subprocess
    env = {
        **subprocess.os.environ,
        "PYTHONPATH": "/workspaces/Code-Index-MCP",
        "MCP_WORKSPACE_ROOT": "/workspaces/Code-Index-MCP",
        "MCP_INDEX_STORAGE_PATH": "/workspaces/Code-Index-MCP/.indexes",
        "MCP_REPO_REGISTRY": "/workspaces/Code-Index-MCP/.indexes/repository_registry.json",
        "MCP_ENABLE_MULTI_REPO": "true",
        "MCP_DEBUG": "1"  # Enable debug mode
    }
    
    server_proc = subprocess.Popen(
        ["python3", "/workspaces/Code-Index-MCP/scripts/cli/mcp_server_cli.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        text=True,
        bufsize=0  # Unbuffered
    )
    
    # Wait for server to start
    time.sleep(2)
    
    try:
        # Send initialization request
        print("\nSending initialization request...")
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0"
                }
            }
        }
        
        server_proc.stdin.write(json.dumps(init_request) + "\n")
        server_proc.stdin.flush()
        
        # Read response with timeout
        response_line = None
        start_time = time.time()
        while time.time() - start_time < 5:
            try:
                line = server_proc.stdout.readline()
                if line:
                    print(f"Server response: {line.strip()}")
                    response_line = line
                    break
            except:
                pass
        
        if not response_line:
            print("No response from server initialization")
            # Check stderr
            stderr_output = server_proc.stderr.read()
            if stderr_output:
                print(f"Server stderr: {stderr_output}")
        
        # Send tool call request
        print("\nSending search_code tool call...")
        tool_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "search_code",
                "arguments": {
                    "query": "EnhancedDispatcher",
                    "limit": 3
                }
            }
        }
        
        server_proc.stdin.write(json.dumps(tool_request) + "\n")
        server_proc.stdin.flush()
        
        # Read response with timeout
        print("Waiting for tool response...")
        start_time = time.time()
        response_received = False
        
        while time.time() - start_time < 10:
            try:
                line = server_proc.stdout.readline()
                if line:
                    print(f"Server response: {line.strip()}")
                    response_received = True
                    break
            except:
                pass
        
        if not response_received:
            print("No response from server - tool call may be hanging")
            # Check stderr
            stderr_output = server_proc.stderr.read()
            if stderr_output:
                print(f"Server stderr: {stderr_output}")
        
    finally:
        # Terminate server
        print("\nTerminating server...")
        server_proc.terminate()
        try:
            server_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_proc.kill()
            server_proc.wait()
        
        print("Test complete")

if __name__ == "__main__":
    asyncio.run(test_mcp_protocol())