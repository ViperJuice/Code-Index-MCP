#!/usr/bin/env python3
"""Verify MCP doesn't hang by simulating the exact call pattern."""
import asyncio
import sys
import os
import time
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def test_mcp_async():
    """Test MCP in async context like the actual server."""
    # Import after path setup
    from scripts.cli.mcp_server_cli import call_tool, initialize_services
    
    print("Initializing MCP services...")
    try:
        await initialize_services()
        print("Services initialized successfully")
    except Exception as e:
        print(f"Initialization error: {e}")
        return
    
    # Test search_code tool
    print("\nTesting search_code tool...")
    queries = [
        ("EnhancedDispatcher", 3),
        ("multi_repo_manager", 3),
        ("def search", 5)
    ]
    
    for query, limit in queries:
        print(f"\nSearching for: {query} (limit={limit})")
        start_time = time.time()
        
        try:
            # Call the tool exactly as MCP would
            result = await call_tool("search_code", {"query": query, "limit": limit})
            elapsed = time.time() - start_time
            
            print(f"Completed in {elapsed:.2f}s")
            
            # Parse result
            if result and len(result) > 0:
                text_content = result[0].text
                try:
                    data = json.loads(text_content)
                    if isinstance(data, list):
                        print(f"Found {len(data)} results")
                    elif isinstance(data, dict) and 'results' in data:
                        print(f"Found {len(data['results'])} results")
                    elif 'error' in data:
                        print(f"Error: {data['error']}")
                    else:
                        print(f"Result type: {type(data)}")
                except:
                    print(f"Raw result: {text_content[:200]}...")
            else:
                print("No result returned")
                
        except asyncio.TimeoutError:
            elapsed = time.time() - start_time
            print(f"Timed out after {elapsed:.2f}s")
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"Error after {elapsed:.2f}s: {e}")
    
    print("\n✓ All tests completed without hanging")

if __name__ == "__main__":
    # Run the async test
    asyncio.run(test_mcp_async())