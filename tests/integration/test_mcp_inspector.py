#!/usr/bin/env python3
"""
Test MCP server through MCP Inspector client.
"""

import asyncio
import json
import subprocess
import time
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def test_mcp_through_inspector():
    """Test MCP server functionality through the Inspector."""
    print("🔍 MCP Inspector Client Test")
    print("=" * 50)
    
    # Test different MCP methods
    test_cases = [
        {
            "name": "Initialize",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "clientInfo": {"name": "test-client", "version": "1.0"},
                "capabilities": {}
            }
        },
        {
            "name": "List Tools",
            "method": "tools/list",
            "params": {}
        },
        {
            "name": "List Resources",
            "method": "resources/list", 
            "params": {}
        },
        {
            "name": "List Prompts",
            "method": "prompts/list",
            "params": {}
        },
        {
            "name": "Call Search Tool",
            "method": "tools/call",
            "params": {
                "name": "search_code",
                "arguments": {
                    "query": "def",
                    "limit": 5
                }
            }
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases):
        print(f"\n{i+1}. Testing {test_case['name']}...")
        
        try:
            # Create JSON-RPC request
            request = {
                "jsonrpc": "2.0",
                "method": test_case["method"],
                "params": test_case["params"],
                "id": i + 1
            }
            
            # Send request via stdio to our server
            proc = await asyncio.create_subprocess_exec(
                "python", "-m", "mcp_server", "--transport", "stdio",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(project_root)
            )
            
            # Send request
            request_json = json.dumps(request) + "\n"
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(request_json.encode()),
                timeout=10
            )
            
            # Parse response
            response_data = stdout.decode().strip()
            if response_data:
                try:
                    response = json.loads(response_data)
                    
                    if "result" in response:
                        print(f"   ✅ Success: {test_case['name']}")
                        if test_case["method"] == "tools/list":
                            tools = response["result"].get("tools", [])
                            print(f"      Found {len(tools)} tools")
                        elif test_case["method"] == "resources/list":
                            resources = response["result"].get("resources", [])
                            print(f"      Found {len(resources)} resources")
                        elif test_case["method"] == "prompts/list":
                            prompts = response["result"].get("prompts", [])
                            print(f"      Found {len(prompts)} prompts")
                        results.append((test_case["name"], True, "Success"))
                    elif "error" in response:
                        error = response["error"]
                        print(f"   ⚠️  Error: {error.get('message', 'Unknown error')}")
                        results.append((test_case["name"], False, error.get("message", "Error")))
                    else:
                        print(f"   ❌ Invalid response format")
                        results.append((test_case["name"], False, "Invalid response"))
                        
                except json.JSONDecodeError as e:
                    print(f"   ❌ JSON decode error: {e}")
                    print(f"      Raw response: {response_data}")
                    results.append((test_case["name"], False, f"JSON error: {e}"))
            else:
                print(f"   ❌ No response received")
                results.append((test_case["name"], False, "No response"))
                
        except asyncio.TimeoutError:
            print(f"   ❌ Timeout waiting for response")
            results.append((test_case["name"], False, "Timeout"))
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results.append((test_case["name"], False, str(e)))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)
    
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    for test_name, success, message in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name:<20} {message}")
    
    print(f"\nOverall: {passed}/{total} tests passed ({(passed/total)*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 All MCP methods working correctly!")
        print("🚀 Ready for MCP Inspector and AI assistant integration!")
    else:
        print(f"\n⚠️  {total-passed} methods need attention.")
    
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(test_mcp_through_inspector())
    sys.exit(0 if success else 1)