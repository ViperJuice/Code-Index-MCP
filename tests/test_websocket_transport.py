"""
Test suite for WebSocket transport implementation.
"""

import asyncio
import json
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from mcp_server.transport.websocket import (
    WebSocketTransport,
    WebSocketServer,
    WebSocketClient,
    ConnectionState,
    ConnectionInfo
)
from mcp_server.protocol.jsonrpc import JSONRPCRequest, JSONRPCResponse


@pytest.fixture
def mock_ws():
    """Create a mock WebSocket response."""
    ws = AsyncMock()
    ws._req = Mock()
    ws._req.remote = "127.0.0.1:12345"
    ws.send_str = AsyncMock()
    ws.close = AsyncMock()
    ws.ping = AsyncMock(return_value=asyncio.Future())
    ws.ping.return_value.set_result(None)
    return ws


@pytest.fixture
def mock_request():
    """Create a mock aiohttp request."""
    request = Mock()
    request.remote = "127.0.0.1:12345"
    return request


class TestConnectionInfo:
    """Test ConnectionInfo dataclass."""
    
    def test_initialization(self):
        """Test ConnectionInfo initialization."""
        info = ConnectionInfo(
            connection_id="test-123",
            remote_address="127.0.0.1:12345",
            connected_at=datetime.now(),
            state=ConnectionState.CONNECTED
        )
        
        assert info.connection_id == "test-123"
        assert info.remote_address == "127.0.0.1:12345"
        assert info.state == ConnectionState.CONNECTED
        assert info.message_count == 0
        assert info.error_count == 0
    
    def test_update_activity(self):
        """Test activity update."""
        info = ConnectionInfo(
            connection_id="test-123",
            remote_address="127.0.0.1:12345",
            connected_at=datetime.now(),
            state=ConnectionState.CONNECTED
        )
        
        original_time = info.last_activity
        info.update_activity()
        assert info.last_activity > original_time
    
    def test_increment_messages(self):
        """Test message count increment."""
        info = ConnectionInfo(
            connection_id="test-123",
            remote_address="127.0.0.1:12345",
            connected_at=datetime.now(),
            state=ConnectionState.CONNECTED
        )
        
        original_time = info.last_activity
        info.increment_messages()
        assert info.message_count == 1
        assert info.last_activity > original_time
    
    def test_increment_errors(self):
        """Test error count increment."""
        info = ConnectionInfo(
            connection_id="test-123",
            remote_address="127.0.0.1:12345",
            connected_at=datetime.now(),
            state=ConnectionState.CONNECTED
        )
        
        info.increment_errors()
        assert info.error_count == 1


class TestWebSocketTransport:
    """Test WebSocketTransport class."""
    
    @pytest.mark.asyncio
    async def test_initialization(self, mock_ws):
        """Test transport initialization."""
        transport = WebSocketTransport(mock_ws)
        
        assert transport.ws == mock_ws
        assert transport.connection_id is not None
        assert transport.max_message_size == 10 * 1024 * 1024
        assert transport.ping_interval == 30.0
        assert transport.ping_timeout == 10.0
        assert not transport._closed
        assert transport.connection_info.state == ConnectionState.CONNECTED
        
        # Cleanup
        await transport.close()
    
    @pytest.mark.asyncio
    async def test_send_message(self, mock_ws):
        """Test sending a message."""
        transport = WebSocketTransport(mock_ws)
        
        message = json.dumps({
            "jsonrpc": "2.0",
            "method": "test",
            "id": 1
        })
        
        await transport.send(message)
        
        mock_ws.send_str.assert_called_once_with(message)
        assert transport.connection_info.message_count == 1
        
        # Cleanup
        await transport.close()
    
    @pytest.mark.asyncio
    async def test_send_message_when_closed(self, mock_ws):
        """Test sending message when connection is closed."""
        transport = WebSocketTransport(mock_ws)
        await transport.close()
        
        with pytest.raises(ConnectionError):
            await transport.send("test message")
    
    @pytest.mark.asyncio
    async def test_send_oversized_message(self, mock_ws):
        """Test sending message that exceeds max size."""
        transport = WebSocketTransport(mock_ws, max_message_size=100)
        
        large_message = "x" * 200
        
        with pytest.raises(ValueError):
            await transport.send(large_message)
        
        # Cleanup
        await transport.close()
    
    @pytest.mark.asyncio
    async def test_receive_complete_message(self, mock_ws):
        """Test receiving a complete JSON-RPC message."""
        transport = WebSocketTransport(mock_ws)
        
        # Simulate receiving a complete message
        message = json.dumps({
            "jsonrpc": "2.0",
            "method": "test",
            "params": {"data": "hello"},
            "id": 1
        })
        
        await transport._handle_text_message(message)
        
        # Check message was queued
        received = await asyncio.wait_for(transport._receive_queue.get(), timeout=1.0)
        assert received == message
        assert transport.connection_info.message_count == 1
        
        # Cleanup
        await transport.close()
    
    @pytest.mark.asyncio
    async def test_receive_partial_messages(self, mock_ws):
        """Test receiving and buffering partial messages."""
        transport = WebSocketTransport(mock_ws)
        
        # Split a message into parts
        complete_message = json.dumps({
            "jsonrpc": "2.0",
            "method": "test",
            "id": 1
        })
        
        part1 = complete_message[:15]
        part2 = complete_message[15:]
        
        # Send partial messages
        await transport._handle_text_message(part1)
        
        # Should not have a complete message yet
        assert transport._receive_queue.empty()
        
        # Send rest of message
        await transport._handle_text_message(part2)
        
        # Now should have complete message
        received = await asyncio.wait_for(transport._receive_queue.get(), timeout=1.0)
        assert received == complete_message
        
        # Cleanup
        await transport.close()
    
    @pytest.mark.asyncio
    async def test_receive_multiple_messages(self, mock_ws):
        """Test receiving multiple messages in one chunk."""
        transport = WebSocketTransport(mock_ws)
        
        message1 = json.dumps({"jsonrpc": "2.0", "method": "test1", "id": 1})
        message2 = json.dumps({"jsonrpc": "2.0", "method": "test2", "id": 2})
        
        # Send both messages together
        await transport._handle_text_message(message1 + message2)
        
        # Should receive both messages
        received1 = await asyncio.wait_for(transport._receive_queue.get(), timeout=1.0)
        received2 = await asyncio.wait_for(transport._receive_queue.get(), timeout=1.0)
        
        assert received1 == message1
        assert received2 == message2
        assert transport.connection_info.message_count == 2
        
        # Cleanup
        await transport.close()
    
    @pytest.mark.asyncio
    async def test_receive_invalid_json(self, mock_ws):
        """Test handling invalid JSON messages."""
        transport = WebSocketTransport(mock_ws)
        
        # Send invalid JSON
        await transport._handle_text_message("not valid json{")
        
        # Should clear buffer and not queue anything
        assert transport._receive_queue.empty()
        assert transport._message_buffer == ""
        assert transport.connection_info.error_count == 1
        
        # Cleanup
        await transport.close()
    
    @pytest.mark.asyncio
    async def test_close_connection(self, mock_ws):
        """Test closing connection."""
        transport = WebSocketTransport(mock_ws)
        
        assert not transport._closed
        assert transport.connection_info.state == ConnectionState.CONNECTED
        
        await transport.close()
        
        assert transport._closed
        assert transport.connection_info.state == ConnectionState.DISCONNECTED
        mock_ws.close.assert_called_once()
        
        # Should be idempotent
        await transport.close()
        mock_ws.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_ping_timeout(self, mock_ws):
        """Test ping timeout handling."""
        # Mock ping to timeout
        ping_future = asyncio.Future()
        mock_ws.ping = AsyncMock(return_value=ping_future)
        
        transport = WebSocketTransport(mock_ws, ping_interval=0.1, ping_timeout=0.1)
        
        # Wait for ping to timeout
        await asyncio.sleep(0.3)
        
        # Should have closed due to timeout
        assert transport._closed
        assert transport.connection_info.state == ConnectionState.DISCONNECTED


class TestWebSocketServer:
    """Test WebSocketServer class."""
    
    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test server initialization."""
        server = WebSocketServer(host="localhost", port=8765, max_connections=50)
        
        assert server.host == "localhost"
        assert server.port == 8765
        assert server.max_connections == 50
        assert len(server._connections) == 0
    
    @pytest.mark.asyncio
    async def test_handle_websocket_connection_limit(self, mock_request):
        """Test connection limit enforcement."""
        server = WebSocketServer(max_connections=1)
        
        # Add a mock connection to reach limit
        mock_transport = Mock()
        mock_transport.connection_id = "test-123"
        server._connections["test-123"] = mock_transport
        
        with patch('aiohttp.web.Response') as MockResponse:
            response = await server.handle_websocket(mock_request)
            MockResponse.assert_called_with(status=503, text="Service Unavailable")
    
    @pytest.mark.asyncio
    async def test_broadcast(self):
        """Test broadcasting message to all connections."""
        server = WebSocketServer()
        
        # Create mock transports
        transport1 = Mock()
        transport1.is_closed = False
        transport1.send = AsyncMock()
        
        transport2 = Mock()
        transport2.is_closed = False
        transport2.send = AsyncMock()
        
        transport3 = Mock()
        transport3.is_closed = True
        transport3.send = AsyncMock()
        
        server._connections = {
            "conn1": transport1,
            "conn2": transport2,
            "conn3": transport3  # Closed connection
        }
        
        message = json.dumps({"test": "broadcast"})
        await server.broadcast(message)
        
        # Should send to open connections only
        transport1.send.assert_called_once_with(message)
        transport2.send.assert_called_once_with(message)
        transport3.send.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_broadcast_with_exclude(self):
        """Test broadcasting with exclusion list."""
        server = WebSocketServer()
        
        transport1 = Mock()
        transport1.is_closed = False
        transport1.send = AsyncMock()
        
        transport2 = Mock()
        transport2.is_closed = False
        transport2.send = AsyncMock()
        
        server._connections = {
            "conn1": transport1,
            "conn2": transport2
        }
        
        message = json.dumps({"test": "broadcast"})
        await server.broadcast(message, exclude={"conn1"})
        
        # Should only send to conn2
        transport1.send.assert_not_called()
        transport2.send.assert_called_once_with(message)
    
    def test_get_connections(self):
        """Test getting connection information."""
        server = WebSocketServer()
        
        # Create mock transports with connection info
        transport1 = Mock()
        transport1.connection_info = ConnectionInfo(
            connection_id="conn1",
            remote_address="127.0.0.1:1111",
            connected_at=datetime.now(),
            state=ConnectionState.CONNECTED
        )
        
        transport2 = Mock()
        transport2.connection_info = ConnectionInfo(
            connection_id="conn2",
            remote_address="127.0.0.1:2222",
            connected_at=datetime.now(),
            state=ConnectionState.CONNECTED
        )
        
        server._connections = {
            "conn1": transport1,
            "conn2": transport2
        }
        
        connections = server.get_connections()
        
        assert len(connections) == 2
        assert "conn1" in connections
        assert "conn2" in connections
        assert connections["conn1"].remote_address == "127.0.0.1:1111"
        assert connections["conn2"].remote_address == "127.0.0.1:2222"


class TestWebSocketClient:
    """Test WebSocketClient class."""
    
    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test client initialization."""
        client = WebSocketClient(
            url="ws://localhost:8765",
            reconnect_interval=10.0,
            max_reconnect_attempts=5
        )
        
        assert client.url == "ws://localhost:8765"
        assert client.reconnect_interval == 10.0
        assert client.max_reconnect_attempts == 5
        assert client._transport is None
        assert not client._closed
    
    @pytest.mark.asyncio
    async def test_connect_success(self):
        """Test successful connection."""
        client = WebSocketClient("ws://localhost:8765")
        
        mock_session = AsyncMock()
        mock_ws = AsyncMock()
        mock_ws._req = Mock()
        mock_ws._req.remote = "127.0.0.1:8765"
        mock_session.ws_connect = AsyncMock(return_value=mock_ws)
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            transport = await client.connect()
            
            assert transport is not None
            assert client._transport == transport
            assert client._reconnect_attempts == 0
            mock_session.ws_connect.assert_called_once_with("ws://localhost:8765")
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_connect_failure(self):
        """Test connection failure."""
        client = WebSocketClient("ws://localhost:8765")
        
        mock_session = AsyncMock()
        mock_session.ws_connect = AsyncMock(side_effect=Exception("Connection failed"))
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            with pytest.raises(ConnectionError):
                await client.connect()
    
    @pytest.mark.asyncio
    async def test_reconnect_on_disconnect(self):
        """Test automatic reconnection."""
        client = WebSocketClient(
            "ws://localhost:8765",
            reconnect_interval=0.1,
            max_reconnect_attempts=2
        )
        
        # Mock successful initial connection
        mock_session = AsyncMock()
        mock_ws = AsyncMock()
        mock_ws._req = Mock()
        mock_ws._req.remote = "127.0.0.1:8765"
        
        # First connect succeeds, then fails, then succeeds again
        connect_results = [mock_ws, Exception("Disconnected"), mock_ws]
        mock_session.ws_connect = AsyncMock(side_effect=connect_results)
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            # Initial connection
            transport = await client.connect()
            assert transport is not None
            
            # Simulate disconnection
            transport._closed = True
            
            # Wait for reconnection
            await asyncio.sleep(0.3)
            
            # Should have attempted to reconnect
            assert mock_session.ws_connect.call_count >= 2
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_max_reconnect_attempts(self):
        """Test maximum reconnection attempts."""
        client = WebSocketClient(
            "ws://localhost:8765",
            reconnect_interval=0.1,
            max_reconnect_attempts=2
        )
        
        # Mock connection that always fails
        mock_session = AsyncMock()
        mock_session.ws_connect = AsyncMock(side_effect=Exception("Connection failed"))
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            # Try to connect
            with pytest.raises(ConnectionError):
                await client.connect()
            
            # Simulate transport was set but connection lost
            mock_transport = Mock()
            mock_transport.is_closed = True
            client._transport = mock_transport
            
            # Trigger reconnection
            await client._reconnect()
            
            # Should stop after max attempts
            assert client._reconnect_attempts == 2
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_close(self):
        """Test client close."""
        client = WebSocketClient("ws://localhost:8765")
        
        # Mock components
        mock_transport = AsyncMock()
        mock_session = AsyncMock()
        mock_reconnect_task = AsyncMock()
        
        client._transport = mock_transport
        client._session = mock_session
        client._reconnect_task = mock_reconnect_task
        
        await client.close()
        
        assert client._closed
        mock_transport.close.assert_called_once()
        mock_session.close.assert_called_once()
        mock_reconnect_task.cancel.assert_called_once()
        assert client._transport is None
        assert client._session is None
    
    def test_transport_property(self):
        """Test transport property."""
        client = WebSocketClient("ws://localhost:8765")
        
        # No transport
        assert client.transport is None
        
        # Closed transport
        mock_transport = Mock()
        mock_transport.is_closed = True
        client._transport = mock_transport
        assert client.transport is None
        
        # Active transport
        mock_transport.is_closed = False
        assert client.transport == mock_transport


# Integration test
@pytest.mark.asyncio
async def test_server_client_integration():
    """Test full server-client integration."""
    # Start server
    server = WebSocketServer(port=18765)
    await server.start()
    
    try:
        # Connect client
        client = WebSocketClient("ws://localhost:18765")
        transport = await client.connect()
        
        # Send message from client
        request = json.dumps({
            "jsonrpc": "2.0",
            "method": "test",
            "params": {"message": "Hello, Server!"},
            "id": 1
        })
        await transport.send(request)
        
        # Verify server has connection
        connections = server.get_connections()
        assert len(connections) == 1
        
        # Close client
        await client.close()
        
        # Wait a bit for cleanup
        await asyncio.sleep(0.1)
        
        # Verify connection removed
        connections = server.get_connections()
        assert len(connections) == 0
        
    finally:
        await server.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])