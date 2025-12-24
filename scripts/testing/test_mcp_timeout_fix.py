#!/usr/bin/env python3
"""Test that the MCP search_code tool now has proper timeout protection."""
import subprocess
import json
import time
import sys

def test_mcp_search():
    """Test MCP search_code with timeout protection."""
    print("Testing MCP search_code tool with timeout protection...")
    
    # Prepare the MCP tool call
    tool_input = {
        "query": "EnhancedDispatcher",
        "limit": 3
    }
    
    # Start timing
    start_time = time.time()
    
    # Run mcp directly
    cmd = [
        sys.executable,
        "-m", "mcp",
        "call-tool",
        "/workspaces/Code-Index-MCP/.mcp.json",
        "code-index-mcp",
        "search_code",
        json.dumps(tool_input)
    ]
    
    try:
        # Run with a 15-second timeout (should timeout internally at 10s)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=15
        )
        
        elapsed = time.time() - start_time
        
        print(f"\nCompleted in {elapsed:.2f} seconds")
        print(f"Return code: {result.returncode}")
        
        if result.stdout:
            print("\nStdout:")
            print(result.stdout)
            
        if result.stderr:
            print("\nStderr:")
            print(result.stderr)
            
        # Check if it timed out internally
        if "timeout" in result.stdout.lower() or "timeout" in result.stderr.lower():
            print("\n✓ Tool properly timed out internally")
        elif elapsed > 12:
            print("\n✗ Tool took too long without timing out")
        else:
            print("\n✓ Tool completed successfully within timeout")
            
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start_time
        print(f"\n✗ Process timed out at system level after {elapsed:.2f} seconds")
        print("The internal timeout protection may not be working")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")

if __name__ == "__main__":
    test_mcp_search()