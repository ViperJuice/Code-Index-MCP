#!/usr/bin/env python3
"""Test MCP server stdio communication directly."""
import subprocess
import json
import time
import sys

def test_mcp_stdio():
    """Test MCP server by sending messages via stdio."""
    print("Starting MCP server subprocess...")
    
    # Start MCP server
    env = {
        **subprocess.os.environ,
        "PYTHONPATH": "/workspaces/Code-Index-MCP",
        "MCP_WORKSPACE_ROOT": "/workspaces/Code-Index-MCP",
        "MCP_INDEX_STORAGE_PATH": "/workspaces/Code-Index-MCP/.indexes",
        "MCP_DEBUG": "1"
    }
    
    proc = subprocess.Popen(
        ["python3", "/workspaces/Code-Index-MCP/scripts/cli/mcp_server_cli.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        text=True
    )
    
    # Give it time to start
    time.sleep(2)
    
    # Check if server started
    if proc.poll() is not None:
        stdout, stderr = proc.communicate()
        print(f"Server exited early!")
        print(f"Stdout: {stdout}")
        print(f"Stderr: {stderr}")
        return
    
    print("Server started, checking stderr...")
    
    # Try to read any stderr output (non-blocking)
    import select
    import fcntl
    import os
    
    # Make stderr non-blocking
    flags = fcntl.fcntl(proc.stderr.fileno(), fcntl.F_GETFL)
    fcntl.fcntl(proc.stderr.fileno(), fcntl.F_SETFL, flags | os.O_NONBLOCK)
    
    # Read available stderr
    stderr_lines = []
    while True:
        ready, _, _ = select.select([proc.stderr], [], [], 0.1)
        if ready:
            try:
                line = proc.stderr.readline()
                if line:
                    stderr_lines.append(line)
                else:
                    break
            except:
                break
        else:
            break
    
    if stderr_lines:
        print("Initial stderr output:")
        for line in stderr_lines:
            print(f"  {line.strip()}")
    
    print("\nSending initialize request...")
    
    # Send proper MCP initialization
    init_msg = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "id": 1,
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "roots": {
                    "listChanged": True
                },
                "sampling": {}
            },
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        }
    }
    
    proc.stdin.write(json.dumps(init_msg) + "\n")
    proc.stdin.flush()
    
    # Wait for response
    print("Waiting for initialization response...")
    try:
        response = proc.stdout.readline()
        if response:
            print(f"Response: {response.strip()}")
        else:
            print("No response received")
    except Exception as e:
        print(f"Error reading response: {e}")
    
    # Now test search_code tool call
    print("\nSending search_code tool call...")
    
    tool_msg = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "id": 2,
        "params": {
            "name": "search_code",
            "arguments": {
                "query": "EnhancedDispatcher",
                "limit": 3
            }
        }
    }
    
    proc.stdin.write(json.dumps(tool_msg) + "\n")
    proc.stdin.flush()
    
    # Wait for response with timeout
    print("Waiting for tool response...")
    import select
    
    start_time = time.time()
    timeout = 15  # 15 second timeout
    
    while time.time() - start_time < timeout:
        # Check if data is available
        ready, _, _ = select.select([proc.stdout], [], [], 0.1)
        if ready:
            try:
                response = proc.stdout.readline()
                if response:
                    print(f"Tool response received after {time.time() - start_time:.2f}s")
                    print(f"Response: {response.strip()[:200]}...")
                    break
            except Exception as e:
                print(f"Error reading: {e}")
                break
        
        # Check if process is still alive
        if proc.poll() is not None:
            print("Process terminated unexpectedly")
            stdout, stderr = proc.communicate()
            print(f"Final stdout: {stdout}")
            print(f"Final stderr: {stderr}")
            break
    else:
        print(f"Timeout after {timeout}s - no response received")
    
    # Clean up
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()

if __name__ == "__main__":
    test_mcp_stdio()