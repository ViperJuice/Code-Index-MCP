#!/usr/bin/env python3
"""Test MCP server startup."""

import subprocess
import json
import time

def test_mcp_server():
    """Test if MCP server starts correctly."""
    print("Testing MCP server startup...")
    
    # Start the MCP server process
    cmd = [
        "/usr/local/bin/python",
        "/workspaces/Code-Index-MCP/scripts/cli/mcp_server_cli.py"
    ]
    
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd="/workspaces/Code-Index-MCP",
        env={
            "PYTHONPATH": "/workspaces/Code-Index-MCP",
            "MCP_INDEX_STORAGE_PATH": "/workspaces/Code-Index-MCP/.indexes"
        }
    )
    
    # Give it a moment to start
    time.sleep(1)
    
    # Check if process is still running
    if proc.poll() is not None:
        stdout, stderr = proc.communicate()
        print(f"Server crashed immediately!")
        print(f"Return code: {proc.returncode}")
        print(f"Stderr: {stderr}")
        print(f"Stdout: {stdout}")
        return False
    
    print("Server started successfully!")
    
    # Send a simple ping-like request (this will fail but shows server is responsive)
    try:
        proc.stdin.write('{"jsonrpc": "2.0", "method": "test", "id": 1}\n')
        proc.stdin.flush()
        
        # Wait for response with timeout
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        # This is expected - server is waiting for more input
        print("Server is running and waiting for input (good!)")
        proc.terminate()
        return True
    except Exception as e:
        print(f"Error: {e}")
        proc.terminate()
        return False
    
    return True

if __name__ == "__main__":
    success = test_mcp_server()
    print(f"\nMCP server test: {'PASSED' if success else 'FAILED'}")