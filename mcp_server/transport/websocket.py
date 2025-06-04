"""WebSocket transport implementation for MCP"""
import asyncio
import json
import logging
from typing import Optional, Dict, Any, AsyncIterator, Set
from dataclasses import dataclass
import aiohttp
from aiohttp import web
import weakref

from .base import Transport, TransportError, TransportState

logger = logging.getLogger(__name__)

@dataclass
class ConnectionInfo:
    """WebSocket connection information"""
    session_id: str
    websocket: web.WebSocketResponse
    remote_address: str
    headers: Dict[str, str]

class WebSocketTransport(Transport[str]):
    """WebSocket transport for MCP protocol"""
    
    def __init__(self, protocol_handler=None):
        """
        Initialize WebSocket transport
        
        Args:
            protocol_handler: MCP protocol handler instance
        """
        super().__init__()
        self.protocol_handler = protocol_handler
        self.connections: Dict[str, ConnectionInfo] = {}
        self.app: Optional[web.Application] = None
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None
        self._connection_tasks: Set[asyncio.Task] = set()
    
    async def connect(self, host: str = "0.0.0.0", port: int = 8765, **kwargs) -> None:
        """
        Start WebSocket server
        
        Args:
            host: Host to bind to
            port: Port to bind to
        """
        if self.is_connected:
            raise TransportError("WebSocket server already running")
        
        await self._set_state(TransportState.CONNECTING)
        
        try:
            # Create aiohttp application
            self.app = web.Application()
            self.app.router.add_get('/mcp', self.handle_websocket)
            self.app.router.add_get('/health', self.handle_health)
            
            # Setup runner
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            
            # Create site and start server
            self.site = web.TCPSite(self.runner, host, port)
            await self.site.start()
            
            self._metadata.local_address = f"{host}:{port}"
            await self._set_state(TransportState.CONNECTED)
            
            logger.info(f"WebSocket server started on {host}:{port}")
            
        except Exception as e:
            await self._set_state(TransportState.ERROR)
            raise TransportError(f"Failed to start WebSocket server: {e}") from e
    
    async def disconnect(self) -> None:
        """Stop WebSocket server and close all connections"""
        if not self.is_connected:
            return
        
        await self._set_state(TransportState.DISCONNECTING)
        
        # Close all active connections
        for session_id in list(self.connections.keys()):
            await self.close_connection(session_id)
        
        # Cancel all connection tasks
        for task in self._connection_tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        if self._connection_tasks:
            await asyncio.gather(*self._connection_tasks, return_exceptions=True)
        self._connection_tasks.clear()
        
        # Stop the server
        if self.site:
            await self.site.stop()
            self.site = None
        
        if self.runner:
            await self.runner.cleanup()
            self.runner = None
        
        self.app = None
        
        await self._set_state(TransportState.DISCONNECTED)
        logger.info("WebSocket server stopped")
    
    async def send(self, message: str, session_id: Optional[str] = None) -> None:
        """
        Send message to WebSocket client(s)
        
        Args:
            message: Message to send
            session_id: Optional session ID to send to specific client
        """
        if not self.is_connected:
            raise TransportError("WebSocket server not running")
        
        if session_id:
            # Send to specific client
            conn = self.connections.get(session_id)
            if conn:
                try:
                    await conn.websocket.send_str(message)
                    self._statistics.record_sent(len(message))
                    self._metadata.update_activity()
                except Exception as e:
                    logger.error(f"Error sending to {session_id}: {e}")
                    await self.close_connection(session_id)
                    raise TransportError(f"Failed to send message: {e}") from e
            else:
                raise TransportError(f"Unknown session: {session_id}")
        else:
            # Broadcast to all clients
            errors = []
            for sid, conn in list(self.connections.items()):
                try:
                    await conn.websocket.send_str(message)
                    self._statistics.record_sent(len(message))
                except Exception as e:
                    logger.error(f"Error broadcasting to {sid}: {e}")
                    errors.append((sid, e))
                    await self.close_connection(sid)
            
            if errors:
                raise TransportError(f"Failed to broadcast to {len(errors)} clients")
        
        self._metadata.update_activity()
    
    async def receive(self) -> AsyncIterator[str]:
        """
        This method is not used for WebSocket server transport.
        Messages are received via handle_websocket callback.
        """
        raise NotImplementedError("WebSocket server uses callback-based message handling")
    
    async def is_alive(self) -> bool:
        """Check if WebSocket server is alive"""
        return self.is_connected and self.site is not None
    
    async def handle_websocket(self, request: web.Request) -> web.WebSocketResponse:
        """Handle incoming WebSocket connection"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        # Generate session ID
        session_id = f"ws-{id(ws)}"
        
        # Store connection info
        conn_info = ConnectionInfo(
            session_id=session_id,
            websocket=ws,
            remote_address=request.remote or "unknown",
            headers=dict(request.headers)
        )
        self.connections[session_id] = conn_info
        
        logger.info(f"WebSocket client connected: {session_id} from {conn_info.remote_address}")
        
        # Create task to handle this connection
        task = asyncio.create_task(self._handle_connection(session_id, ws))
        self._connection_tasks.add(task)
        task.add_done_callback(self._connection_tasks.discard)
        
        return ws
    
    async def _handle_connection(self, session_id: str, ws: web.WebSocketResponse):
        """Handle messages from a WebSocket connection"""
        try:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        # Update statistics
                        self._statistics.record_received(len(msg.data))
                        self._metadata.update_activity()
                        
                        # Handle message through protocol handler
                        if self.protocol_handler:
                            response = await self.protocol_handler.handle_message(msg.data, session_id)
                            if response:
                                await ws.send_str(response)
                                self._statistics.record_sent(len(response))
                        
                    except Exception as e:
                        logger.error(f"Error handling message from {session_id}: {e}", exc_info=True)
                        error_response = json.dumps({
                            "jsonrpc": "2.0",
                            "error": {
                                "code": -32603,
                                "message": "Internal error",
                                "data": str(e)
                            },
                            "id": None
                        })
                        await ws.send_str(error_response)
                        
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"WebSocket error from {session_id}: {ws.exception()}")
                    break
                    
                elif msg.type == aiohttp.WSMsgType.CLOSE:
                    logger.info(f"WebSocket closed by client {session_id}")
                    break
                    
        except Exception as e:
            logger.error(f"Connection handler error for {session_id}: {e}", exc_info=True)
        finally:
            await self.close_connection(session_id)
    
    async def close_connection(self, session_id: str):
        """Close a specific WebSocket connection"""
        conn = self.connections.pop(session_id, None)
        if conn:
            try:
                await conn.websocket.close()
            except Exception as e:
                logger.error(f"Error closing WebSocket for {session_id}: {e}")
            
            logger.info(f"WebSocket client disconnected: {session_id}")
    
    async def handle_health(self, request: web.Request) -> web.Response:
        """Health check endpoint"""
        status = {
            "status": "healthy" if self.is_connected else "unhealthy",
            "connections": len(self.connections),
            "uptime": (self._metadata.last_activity - self._metadata.created_at).total_seconds(),
            "statistics": {
                "messages_sent": self._statistics.messages_sent,
                "messages_received": self._statistics.messages_received,
                "bytes_sent": self._statistics.bytes_sent,
                "bytes_received": self._statistics.bytes_received,
                "errors": self._statistics.errors_count
            }
        }
        return web.json_response(status)
    
    def list_connections(self) -> Dict[str, Dict[str, Any]]:
        """List all active connections"""
        return {
            session_id: {
                "remote_address": conn.remote_address,
                "headers": conn.headers,
                "connected": True
            }
            for session_id, conn in self.connections.items()
        }
    
    async def send_notification(self, method: str, params: Optional[Dict[str, Any]] = None, 
                              session_id: Optional[str] = None):
        """
        Send JSON-RPC notification
        
        Args:
            method: Notification method
            params: Notification parameters
            session_id: Optional session to send to (broadcasts if None)
        """
        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {}
        }
        
        message = json.dumps(notification)
        await self.send(message, session_id)


class WebSocketClient(Transport[str]):
    """WebSocket client transport for MCP protocol"""
    
    def __init__(self, protocol_handler=None):
        """
        Initialize WebSocket client
        
        Args:
            protocol_handler: MCP protocol handler instance
        """
        super().__init__()
        self.protocol_handler = protocol_handler
        self.session: Optional[aiohttp.ClientSession] = None
        self.ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._receive_task: Optional[asyncio.Task] = None
        self._message_queue: asyncio.Queue[str] = asyncio.Queue()
    
    async def connect(self, url: str, **kwargs) -> None:
        """
        Connect to WebSocket server
        
        Args:
            url: WebSocket URL to connect to
        """
        if self.is_connected:
            raise TransportError("Already connected")
        
        await self._set_state(TransportState.CONNECTING)
        
        try:
            self.session = aiohttp.ClientSession()
            self.ws = await self.session.ws_connect(url, **kwargs)
            
            self._metadata.remote_address = url
            await self._set_state(TransportState.CONNECTED)
            
            # Start receive task
            self._receive_task = asyncio.create_task(self._receive_loop())
            
            logger.info(f"Connected to WebSocket server at {url}")
            
        except Exception as e:
            await self._set_state(TransportState.ERROR)
            if self.session:
                await self.session.close()
                self.session = None
            raise TransportError(f"Failed to connect: {e}") from e
    
    async def disconnect(self) -> None:
        """Disconnect from WebSocket server"""
        if not self.is_connected:
            return
        
        await self._set_state(TransportState.DISCONNECTING)
        
        # Cancel receive task
        if self._receive_task and not self._receive_task.done():
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
        
        # Close WebSocket
        if self.ws:
            await self.ws.close()
            self.ws = None
        
        # Close session
        if self.session:
            await self.session.close()
            self.session = None
        
        await self._set_state(TransportState.DISCONNECTED)
        logger.info("Disconnected from WebSocket server")
    
    async def send(self, message: str) -> None:
        """Send message to WebSocket server"""
        if not self.is_connected or not self.ws:
            raise TransportError("Not connected")
        
        try:
            await self.ws.send_str(message)
            self._statistics.record_sent(len(message))
            self._metadata.update_activity()
        except Exception as e:
            await self._set_state(TransportState.ERROR)
            raise TransportError(f"Failed to send message: {e}") from e
    
    async def receive(self) -> AsyncIterator[str]:
        """Receive messages from WebSocket server"""
        while self.is_connected:
            try:
                message = await self._message_queue.get()
                yield message
            except asyncio.CancelledError:
                break
    
    async def _receive_loop(self):
        """Background task to receive messages"""
        try:
            async for msg in self.ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    self._statistics.record_received(len(msg.data))
                    self._metadata.update_activity()
                    
                    # Add to queue for receive() method
                    await self._message_queue.put(msg.data)
                    
                    # Also handle through protocol handler if available
                    if self.protocol_handler:
                        response = await self.protocol_handler.handle_message(msg.data, self._transport_id)
                        if response:
                            await self.send(response)
                            
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {self.ws.exception()}")
                    await self._set_state(TransportState.ERROR)
                    break
                    
                elif msg.type == aiohttp.WSMsgType.CLOSE:
                    logger.info("WebSocket closed by server")
                    break
                    
        except Exception as e:
            logger.error(f"Receive loop error: {e}", exc_info=True)
            await self._set_state(TransportState.ERROR)
    
    async def is_alive(self) -> bool:
        """Check if connection is alive"""
        return self.is_connected and self.ws is not None and not self.ws.closed