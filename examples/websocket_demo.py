#!/usr/bin/env python3
"""
WebSocket transport demonstration for MCP.

This example shows how to:
1. Start a WebSocket server
2. Connect a client
3. Exchange JSON-RPC messages
4. Handle reconnection
5. Broadcast to multiple clients
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_server.transport import WebSocketServer, WebSocketClient
from mcp_server.protocol.jsonrpc import JSONRPCHandler, JSONRPCRequest, JSONRPCSerializer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DemoMCPServer:
    """Demo MCP server with WebSocket transport."""
    
    def __init__(self, port: int = 8765):
        self.server = WebSocketServer(port=port)
        self.handler = JSONRPCHandler()
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup JSON-RPC method handlers."""
        self.handler.register_method("echo", self.handle_echo)
        self.handler.register_method("get_time", self.handle_get_time)
        self.handler.register_method("broadcast", self.handle_broadcast)
    
    async def handle_echo(self, message: str) -> str:
        """Echo back the received message."""
        logger.info(f"Echo request: {message}")
        return f"Echo: {message}"
    
    async def handle_get_time(self) -> str:
        """Return current server time."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    async def handle_broadcast(self, message: str) -> str:
        """Broadcast a message to all connected clients."""
        notification = JSONRPCRequest(
            method="notification",
            params={"message": f"Broadcast: {message}"}
        )
        
        await self.server.broadcast(
            JSONRPCSerializer.serialize_request(notification)
        )
        
        return f"Broadcasted to {len(self.server.get_connections())} clients"
    
    async def handle_connection(self, connection_id: str):
        """Handle a client connection."""
        logger.info(f"New connection: {connection_id}")
        
        # Get the transport for this connection
        transport = self.server._connections.get(connection_id)
        if not transport:
            return
        
        try:
            # Process messages from this connection
            async for message in transport.receive():
                try:
                    # Parse JSON-RPC request
                    request_data = json.loads(message)
                    request = JSONRPCRequest(
                        method=request_data["method"],
                        params=request_data.get("params"),
                        id=request_data.get("id")
                    )
                    
                    # Handle the request
                    response = await self.handler.handle_request(request)
                    
                    # Send response if not a notification
                    if response:
                        response_json = JSONRPCSerializer.serialize_response(response)
                        await transport.send(response_json)
                        
                except Exception as e:
                    logger.error(f"Error handling message: {e}")
                    
        except Exception as e:
            logger.error(f"Connection error: {e}")
        finally:
            logger.info(f"Connection closed: {connection_id}")
    
    async def start(self):
        """Start the server."""
        await self.server.start()
        logger.info(f"Server started on port {self.server.port}")
        
        # Monitor for new connections
        while True:
            await asyncio.sleep(0.1)
            
            # Check for new connections
            for conn_id, transport in list(self.server._connections.items()):
                if not hasattr(transport, '_handler_task'):
                    # Start handler for new connection
                    transport._handler_task = asyncio.create_task(
                        self.handle_connection(conn_id)
                    )


class DemoMCPClient:
    """Demo MCP client with WebSocket transport."""
    
    def __init__(self, url: str = "ws://localhost:8765"):
        self.client = WebSocketClient(url)
        self.request_id = 0
    
    def _next_id(self) -> int:
        """Get next request ID."""
        self.request_id += 1
        return self.request_id
    
    async def echo_test(self, message: str):
        """Test echo method."""
        transport = await self.client.connect()
        
        request = {
            "jsonrpc": "2.0",
            "method": "echo",
            "params": {"message": message},
            "id": self._next_id()
        }
        
        await transport.send(json.dumps(request))
        logger.info(f"Sent echo request: {message}")
    
    async def get_time_test(self):
        """Test get_time method."""
        transport = await self.client.connect()
        
        request = {
            "jsonrpc": "2.0",
            "method": "get_time",
            "id": self._next_id()
        }
        
        await transport.send(json.dumps(request))
        logger.info("Sent get_time request")
    
    async def broadcast_test(self, message: str):
        """Test broadcast method."""
        transport = await self.client.connect()
        
        request = {
            "jsonrpc": "2.0",
            "method": "broadcast",
            "params": {"message": message},
            "id": self._next_id()
        }
        
        await transport.send(json.dumps(request))
        logger.info(f"Sent broadcast request: {message}")
    
    async def listen_for_responses(self):
        """Listen for server responses."""
        transport = self.client.transport
        if not transport:
            logger.error("No active transport")
            return
        
        try:
            async for message in transport.receive():
                data = json.loads(message)
                
                if "result" in data:
                    logger.info(f"Response: {data['result']}")
                elif "error" in data:
                    logger.error(f"Error response: {data['error']}")
                elif "method" in data:
                    logger.info(f"Notification: {data}")
                    
        except Exception as e:
            logger.error(f"Error receiving messages: {e}")
    
    async def run_tests(self):
        """Run client tests."""
        # Connect to server
        await self.client.connect()
        
        # Start listening for responses
        listen_task = asyncio.create_task(self.listen_for_responses())
        
        # Run tests
        await self.echo_test("Hello, WebSocket!")
        await asyncio.sleep(0.5)
        
        await self.get_time_test()
        await asyncio.sleep(0.5)
        
        await self.broadcast_test("Hello, everyone!")
        await asyncio.sleep(0.5)
        
        # Test multiple messages
        for i in range(3):
            await self.echo_test(f"Message {i+1}")
            await asyncio.sleep(0.2)
        
        # Wait a bit more for responses
        await asyncio.sleep(2)
        
        # Cancel listener
        listen_task.cancel()
        try:
            await listen_task
        except asyncio.CancelledError:
            pass
        
        # Close client
        await self.client.close()


async def demo_server():
    """Run demo server."""
    server = DemoMCPServer()
    
    try:
        await server.start()
    except KeyboardInterrupt:
        logger.info("Server shutting down...")
        await server.server.stop()


async def demo_client():
    """Run demo client."""
    # Wait a bit for server to start
    await asyncio.sleep(1)
    
    client = DemoMCPClient()
    
    try:
        await client.run_tests()
    except Exception as e:
        logger.error(f"Client error: {e}")


async def demo_multiple_clients():
    """Demo with multiple clients."""
    # Create multiple clients
    clients = [
        DemoMCPClient() for _ in range(3)
    ]
    
    # Connect all clients
    for i, client in enumerate(clients):
        await client.client.connect()
        logger.info(f"Client {i+1} connected")
    
    # Start listeners for all clients
    listen_tasks = []
    for i, client in enumerate(clients):
        task = asyncio.create_task(client.listen_for_responses())
        listen_tasks.append(task)
    
    # Client 1 sends a broadcast
    transport = clients[0].client.transport
    request = {
        "jsonrpc": "2.0",
        "method": "broadcast",
        "params": {"message": "Hello from Client 1!"},
        "id": 1
    }
    await transport.send(json.dumps(request))
    
    # Wait for messages to propagate
    await asyncio.sleep(2)
    
    # Cleanup
    for task in listen_tasks:
        task.cancel()
    
    for client in clients:
        await client.client.close()


async def main():
    """Run the demo."""
    import argparse
    
    parser = argparse.ArgumentParser(description="WebSocket transport demo")
    parser.add_argument(
        "mode",
        choices=["server", "client", "both", "multi"],
        help="Demo mode to run"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Server port (default: 8765)"
    )
    
    args = parser.parse_args()
    
    if args.mode == "server":
        await demo_server()
    elif args.mode == "client":
        await demo_client()
    elif args.mode == "multi":
        # Run server and multiple clients
        server_task = asyncio.create_task(demo_server())
        await asyncio.sleep(1)  # Let server start
        
        await demo_multiple_clients()
        
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass
    else:  # both
        # Run server and client together
        server_task = asyncio.create_task(demo_server())
        client_task = asyncio.create_task(demo_client())
        
        try:
            await asyncio.gather(server_task, client_task)
        except KeyboardInterrupt:
            server_task.cancel()
            client_task.cancel()
            await asyncio.gather(server_task, client_task, return_exceptions=True)


if __name__ == "__main__":
    asyncio.run(main())