#!/usr/bin/env python3
"""
Test script to verify MCP server logging goes to stderr, not stdout.
This ensures INFO messages don't interfere with the MCP protocol.
"""

import json
import subprocess
import sys


def test_mcp_logging():
    """Test that MCP server sends logs to stderr, not stdout."""

    # Start the MCP server and send a simple request
    process = subprocess.Popen(
        [sys.executable, "mcp_server_cli.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # Send initialization request
    init_request = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {"capabilities": {}},
        "id": 1,
    }

    # Send the request
    process.stdin.write(json.dumps(init_request) + "\n")
    process.stdin.flush()

    # Wait briefly for response
    import time

    time.sleep(1)

    # Terminate the process
    process.terminate()
    stdout, stderr = process.communicate(timeout=5)

    print("=== STDOUT (should contain only JSON-RPC messages) ===")
    print(stdout)
    print("\n=== STDERR (should contain log messages) ===")
    print(stderr)

    # Check that stdout only contains JSON
    stdout_lines = stdout.strip().split("\n")
    for line in stdout_lines:
        if line.strip():
            try:
                json.loads(line)
                print(f"✓ Valid JSON on stdout: {line[:50]}...")
            except json.JSONDecodeError:
                print(f"✗ Non-JSON on stdout: {line}")
                return False

    # Check that stderr contains logging messages
    if "INFO" in stderr and "Initializing" in stderr:
        print("\n✓ Log messages correctly sent to stderr")
        return True
    else:
        print("\n✗ No log messages found on stderr")
        return False


if __name__ == "__main__":
    if test_mcp_logging():
        print("\n✅ MCP logging configuration is correct!")
        sys.exit(0)
    else:
        print("\n❌ MCP logging configuration has issues!")
        sys.exit(1)
