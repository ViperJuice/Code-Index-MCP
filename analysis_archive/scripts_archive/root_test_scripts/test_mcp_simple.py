#!/usr/bin/env python3
"""Simple MCP test."""

import json
import subprocess
import sys
import os

# Test request
request = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
        "name": "get_status",
        "arguments": {}
    }
}

# Run MCP server and send request
proc = subprocess.Popen(
    [sys.executable, "scripts/cli/mcp_server_cli.py"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    env={**dict(os.environ), "MCP_DEBUG": "1"}
)

# First initialize
init_req = {
    "jsonrpc": "2.0",
    "id": 0,
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {"tools": {}},
        "clientInfo": {"name": "test", "version": "1.0"}
    }
}

proc.stdin.write(json.dumps(init_req) + "\n")
proc.stdin.flush()
init_resp = proc.stdout.readline()
print(f"Init response: {init_resp}")

# Send initialized
proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "initialized"}) + "\n")
proc.stdin.flush()

# Now send the actual request
proc.stdin.write(json.dumps(request) + "\n")
proc.stdin.flush()

# Read response
response = proc.stdout.readline()
print(f"Response: {response}")

# Check stderr
stderr = proc.stderr.read()
if stderr:
    print(f"Stderr: {stderr}")

proc.terminate()