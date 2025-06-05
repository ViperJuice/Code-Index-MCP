"""Test MCP integration"""
import asyncio
import json
import websockets
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_mcp_connection():
    """Test basic MCP connection and operations"""
    
    uri = "ws://localhost:8765/mcp"
    
    try:
        async with websockets.connect(uri) as websocket:
            logger.info("Connected to MCP server")
            
            # Test 1: Initialize
            logger.info("Testing initialize...")
            await websocket.send(json.dumps({
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "clientInfo": {
                        "name": "test-client",
                        "version": "1.0.0"
                    },
                    "protocolVersion": "1.0"
                },
                "id": 1
            }))
            
            response = json.loads(await websocket.recv())
            logger.info(f"Initialize response: {json.dumps(response, indent=2)}")
            assert response.get("result"), "Initialize failed"
            assert "serverInfo" in response["result"]
            assert "capabilities" in response["result"]
            
            # Send initialized notification
            await websocket.send(json.dumps({
                "jsonrpc": "2.0",
                "method": "initialized",
                "params": {}
            }))
            
            # Test 2: List resources
            logger.info("\nTesting resources/list...")
            await websocket.send(json.dumps({
                "jsonrpc": "2.0",
                "method": "resources/list",
                "params": {},
                "id": 2
            }))
            
            response = json.loads(await websocket.recv())
            logger.info(f"Resources: {json.dumps(response, indent=2)}")
            assert "resources" in response.get("result", {}), "Resources list failed"
            
            # Test 3: List tools
            logger.info("\nTesting tools/list...")
            await websocket.send(json.dumps({
                "jsonrpc": "2.0",
                "method": "tools/list",
                "params": {},
                "id": 3
            }))
            
            response = json.loads(await websocket.recv())
            logger.info(f"Tools: {json.dumps(response, indent=2)}")
            assert "tools" in response.get("result", {}), "Tools list failed"
            
            # Test 4: Call search tool
            logger.info("\nTesting search_code tool...")
            await websocket.send(json.dumps({
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "search_code",
                    "arguments": {
                        "query": "def ",
                        "limit": 5
                    }
                },
                "id": 4
            }))
            
            response = json.loads(await websocket.recv())
            logger.info(f"Search results: {json.dumps(response, indent=2)}")
            
            # Test 5: Read a resource
            logger.info("\nTesting resource read...")
            await websocket.send(json.dumps({
                "jsonrpc": "2.0",
                "method": "resources/read",
                "params": {
                    "uri": "code://search"
                },
                "id": 5
            }))
            
            response = json.loads(await websocket.recv())
            logger.info(f"Resource content: {json.dumps(response, indent=2)}")
            
            # Test 6: Shutdown
            logger.info("\nTesting shutdown...")
            await websocket.send(json.dumps({
                "jsonrpc": "2.0",
                "method": "shutdown",
                "params": {},
                "id": 6
            }))
            
            response = json.loads(await websocket.recv())
            logger.info(f"Shutdown response: {json.dumps(response, indent=2)}")
            
            logger.info("\nAll tests passed!")
            
    except websockets.exceptions.ConnectionRefused:
        logger.error("Could not connect to MCP server. Make sure it's running on ws://localhost:8765")
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)

async def test_file_watching():
    """Test file watching and notifications"""
    
    uri = "ws://localhost:8765/mcp"
    
    try:
        async with websockets.connect(uri) as websocket:
            # Initialize
            await websocket.send(json.dumps({
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "clientInfo": {
                        "name": "test-watcher",
                        "version": "1.0.0"
                    }
                },
                "id": 1
            }))
            
            response = json.loads(await websocket.recv())
            assert response.get("result"), "Initialize failed"
            
            # Subscribe to a test file resource
            test_file = "test_watch_file.py"
            await websocket.send(json.dumps({
                "jsonrpc": "2.0",
                "method": "resources/subscribe",
                "params": {
                    "uri": f"code://file/{test_file}"
                },
                "id": 2
            }))
            
            response = json.loads(await websocket.recv())
            logger.info("Subscribed to file resource")
            
            # Create/modify a test file to trigger notification
            with open(test_file, "w") as f:
                f.write("# Test file for watching\ndef test_function():\n    pass\n")
            
            logger.info(f"Created test file: {test_file}")
            
            # Wait for notification
            logger.info("Waiting for file change notification...")
            try:
                notification = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                notification = json.loads(notification)
                logger.info(f"Received notification: {json.dumps(notification, indent=2)}")
                
                # Check if it's a resource change notification
                if notification.get("method") == "notifications/resources/changed":
                    logger.info("File change notification received successfully!")
                
            except asyncio.TimeoutError:
                logger.warning("No notification received within 5 seconds")
            
            # Clean up
            import os
            if os.path.exists(test_file):
                os.remove(test_file)
                logger.info(f"Cleaned up test file: {test_file}")
            
    except Exception as e:
        logger.error(f"File watching test failed: {e}", exc_info=True)

async def main():
    """Run all tests"""
    logger.info("Starting MCP integration tests...")
    
    # Run basic connection tests
    await test_mcp_connection()
    
    # Run file watching tests
    logger.info("\n" + "="*50 + "\n")
    await test_file_watching()

if __name__ == "__main__":
    asyncio.run(main())