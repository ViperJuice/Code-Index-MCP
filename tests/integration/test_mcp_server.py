#!/usr/bin/env python3
"""
Test script to verify MCP server functionality.
Run this after starting the MCP server with: python -m mcp_server.server
"""

import asyncio
import json
import websockets
import sys
from datetime import datetime


async def test_mcp_server():
    """Test MCP server functionality."""
    uri = "ws://localhost:8765"
    
    print(f"[{datetime.now()}] Connecting to MCP server at {uri}...")
    
    try:
        async with websockets.connect(uri) as websocket:
            print(f"[{datetime.now()}] Connected successfully!")
            
            # Test 1: Initialize
            print(f"\n[{datetime.now()}] Testing initialize...")
            init_request = {
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "clientInfo": {
                        "name": "test-client",
                        "version": "1.0"
                    },
                    "capabilities": {}
                },
                "id": 1
            }
            
            await websocket.send(json.dumps(init_request))
            response = await websocket.recv()
            init_response = json.loads(response)
            print(f"[{datetime.now()}] Initialize response: {json.dumps(init_response, indent=2)}")
            
            # Test 2: List tools
            print(f"\n[{datetime.now()}] Testing tools/list...")
            tools_request = {
                "jsonrpc": "2.0",
                "method": "tools/list",
                "id": 2
            }
            
            await websocket.send(json.dumps(tools_request))
            response = await websocket.recv()
            tools_response = json.loads(response)
            print(f"[{datetime.now()}] Available tools:")
            if "result" in tools_response and "tools" in tools_response["result"]:
                for tool in tools_response["result"]["tools"]:
                    print(f"  - {tool['name']}: {tool.get('description', 'No description')}")
            
            # Test 3: List resources
            print(f"\n[{datetime.now()}] Testing resources/list...")
            resources_request = {
                "jsonrpc": "2.0",
                "method": "resources/list",
                "id": 3
            }
            
            await websocket.send(json.dumps(resources_request))
            response = await websocket.recv()
            resources_response = json.loads(response)
            print(f"[{datetime.now()}] Available resources:")
            if "result" in resources_response and "resources" in resources_response["result"]:
                for resource in resources_response["result"]["resources"][:5]:  # Show first 5
                    print(f"  - {resource['uri']}: {resource.get('name', 'No name')}")
                if len(resources_response["result"]["resources"]) > 5:
                    print(f"  ... and {len(resources_response['result']['resources']) - 5} more")
            
            # Test 4: Call a tool
            print(f"\n[{datetime.now()}] Testing tool call (search_code)...")
            search_request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "search_code",
                    "arguments": {
                        "query": "def test",
                        "limit": 3
                    }
                },
                "id": 4
            }
            
            await websocket.send(json.dumps(search_request))
            response = await websocket.recv()
            search_response = json.loads(response)
            print(f"[{datetime.now()}] Search results:")
            if "result" in search_response and "content" in search_response["result"]:
                for content in search_response["result"]["content"]:
                    if content["type"] == "text":
                        print(f"  {content['text'][:100]}...")
            
            print(f"\n[{datetime.now()}] All tests completed successfully!")
            
    except websockets.exceptions.ConnectionRefused:
        print(f"[{datetime.now()}] ERROR: Could not connect to MCP server at {uri}")
        print("Make sure the server is running with: python -m mcp_server.server")
        sys.exit(1)
    except Exception as e:
        print(f"[{datetime.now()}] ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    print("MCP Server Test Script")
    print("=" * 50)
    asyncio.run(test_mcp_server())