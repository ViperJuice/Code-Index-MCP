#!/usr/bin/env python3
"""
MCP Server Wrapper - Ensures responses are never empty to prevent Claude Code from stalling.
"""

import sys
import json
import asyncio
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import the actual server
from scripts.cli.mcp_server_cli import main

# Override the stdio to intercept responses
original_stdout = sys.stdout


class ResponseWrapper:
    """Wraps stdout to ensure responses are never empty."""
    
    def __init__(self, stream):
        self.stream = stream
        self.buffer = ""
    
    def write(self, data):
        """Intercept and ensure responses are valid."""
        if data.strip():
            try:
                # Check if it's a JSON response
                parsed = json.loads(data.strip())
                
                # If it's a result with empty content, add a message
                if "result" in parsed and not parsed["result"]:
                    parsed["result"] = [{
                        "type": "text",
                        "text": json.dumps({
                            "status": "empty_result",
                            "message": "No results found",
                            "hint": "Try different search terms or check if the index is populated"
                        })
                    }]
                    data = json.dumps(parsed) + "\n"
                
                # If it's an error without details, add them
                elif "error" in parsed and not parsed["error"].get("data"):
                    parsed["error"]["data"] = "Check MCP server logs for details"
                    data = json.dumps(parsed) + "\n"
                    
            except json.JSONDecodeError:
                # Not JSON, pass through
                pass
            except Exception as e:
                # On any error, ensure we return something
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32000,
                        "message": "Response processing error",
                        "data": str(e)
                    }
                }
                data = json.dumps(error_response) + "\n"
        
        # Always write something
        if data:
            self.stream.write(data)
            self.stream.flush()
    
    def flush(self):
        self.stream.flush()
    
    def __getattr__(self, name):
        return getattr(self.stream, name)


# Wrap stdout
sys.stdout = ResponseWrapper(original_stdout)

# Run the actual server
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        # On any fatal error, output a proper error response
        error_response = {
            "jsonrpc": "2.0",
            "id": None,
            "error": {
                "code": -32603,
                "message": "Internal error",
                "data": f"MCP server crashed: {str(e)}"
            }
        }
        sys.stdout.write(json.dumps(error_response) + "\n")
        sys.stdout.flush()
        sys.exit(1)