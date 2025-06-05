"""
Test session management functionality.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, MagicMock, patch

from mcp_server.session.manager import (
    SessionManager, Session, SessionState, SessionEvent,
    ClientInfo, SessionContext, SessionError
)
from mcp_server.session.capabilities import ServerCapabilities, ClientCapabilities
from mcp_server.transport.base import Transport
from mcp_server.interfaces.shared_interfaces import IEventBus, Event


class MockTransport(Transport):
    """Mock transport for testing."""
    
    def __init__(self):
        self.sent_messages = []
        self.closed = False
        self._receive_queue = asyncio.Queue()
    
    async def send(self, message: str) -> None:
        self.sent_messages.append(message)
    
    async def receive(self):
        while True:
            message = await self._receive_queue.get()
            yield message
    
    async def close(self) -> None:
        self.closed = True
    
    async def add_received_message(self, message: str):
        await self._receive_queue.put(message)


class TestSession:
    """Test Session class."""
    
    @pytest.mark.asyncio
    async def test_session_creation(self):
        """Test session creation and initial state."""
        transport = MockTransport()
        session = Session("test-session-123", transport)
        
        assert session.id == "test-session-123"
        assert session.state == SessionState.INITIALIZING
        assert session.is_active
        assert not session.is_ready
        assert session.timeout_seconds == 3600
    
    @pytest.mark.asyncio
    async def test_session_initialization(self):
        """Test session initialization."""
        transport = MockTransport()
        event_bus = Mock(spec=IEventBus)
        session = Session("test-session", transport, event_bus=event_bus)
        
        client_info = ClientInfo(name="TestClient", version="1.0.0")
        client_capabilities = ClientCapabilities(
            methods=["test/method"],
            notifications=["test/notification"]
        )
        
        await session.initialize(client_info, client_capabilities)
        
        assert session.state == SessionState.READY
        assert session.is_ready
        assert session.context.client_info == client_info
        assert session.context.client_capabilities == client_capabilities
        assert session.context.server_capabilities is not None
        assert session.context.negotiated_capabilities is not None
        
        # Check events were emitted
        assert event_bus.publish.call_count >= 3  # INITIALIZED, READY, STATE_CHANGED
    
    @pytest.mark.asyncio
    async def test_session_state_transitions(self):
        """Test valid and invalid state transitions."""
        transport = MockTransport()
        session = Session("test-session", transport)
        
        # Valid transition: INITIALIZING -> READY
        client_info = ClientInfo(name="TestClient", version="1.0.0")
        client_capabilities = ClientCapabilities(methods=[], notifications=[])
        await session.initialize(client_info, client_capabilities)
        assert session.state == SessionState.READY
        
        # Valid transition: READY -> CLOSING -> CLOSED
        await session.close()
        assert session.state == SessionState.CLOSED
        
        # Invalid transition: CLOSED -> READY
        with pytest.raises(SessionError):
            await session.initialize(client_info, client_capabilities)
    
    @pytest.mark.asyncio
    async def test_session_timeout(self):
        """Test session timeout handling."""
        transport = MockTransport()
        event_bus = Mock(spec=IEventBus)
        session = Session("test-session", transport, timeout_seconds=1, event_bus=event_bus)
        
        # Initialize session
        client_info = ClientInfo(name="TestClient", version="1.0.0")
        client_capabilities = ClientCapabilities(methods=[], notifications=[])
        await session.initialize(client_info, client_capabilities)
        
        # Wait for timeout
        await asyncio.sleep(1.5)
        
        # Session should be closed due to timeout
        assert session.state == SessionState.CLOSED
        
        # Check timeout event was emitted
        timeout_events = [
            call.args[0] for call in event_bus.publish.call_args_list
            if call.args[0].event_type == SessionEvent.TIMEOUT.value
        ]
        assert len(timeout_events) > 0
    
    @pytest.mark.asyncio
    async def test_activity_update_resets_timeout(self):
        """Test that activity updates reset the timeout."""
        transport = MockTransport()
        session = Session("test-session", transport, timeout_seconds=1)
        
        # Initialize session
        client_info = ClientInfo(name="TestClient", version="1.0.0")
        client_capabilities = ClientCapabilities(methods=[], notifications=[])
        await session.initialize(client_info, client_capabilities)
        
        # Update activity before timeout
        await asyncio.sleep(0.5)
        await session.update_activity()
        
        # Wait another 0.8 seconds (total 1.3s, but timeout reset)
        await asyncio.sleep(0.8)
        
        # Session should still be active
        assert session.is_active
        assert session.state == SessionState.READY
    
    @pytest.mark.asyncio
    async def test_subscription_management(self):
        """Test subscription add/remove functionality."""
        transport = MockTransport()
        session = Session("test-session", transport)
        
        # Initialize session first
        client_info = ClientInfo(name="TestClient", version="1.0.0")
        client_capabilities = ClientCapabilities(methods=[], notifications=[])
        await session.initialize(client_info, client_capabilities)
        
        # Add subscriptions
        await session.add_subscription("resource1")
        await session.add_subscription("resource2")
        
        subscriptions = session.get_subscriptions()
        assert "resource1" in subscriptions
        assert "resource2" in subscriptions
        assert len(subscriptions) == 2
        
        # Remove subscription
        await session.remove_subscription("resource1")
        subscriptions = session.get_subscriptions()
        assert "resource1" not in subscriptions
        assert "resource2" in subscriptions
        assert len(subscriptions) == 1
    
    @pytest.mark.asyncio
    async def test_send_message(self):
        """Test sending messages through transport."""
        transport = MockTransport()
        session = Session("test-session", transport)
        
        # Initialize session
        client_info = ClientInfo(name="TestClient", version="1.0.0")
        client_capabilities = ClientCapabilities(methods=[], notifications=[])
        await session.initialize(client_info, client_capabilities)
        
        # Send message
        await session.send_message("test message")
        
        assert len(transport.sent_messages) == 1
        assert transport.sent_messages[0] == "test message"
    
    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error state handling."""
        transport = MockTransport()
        event_bus = Mock(spec=IEventBus)
        session = Session("test-session", transport, event_bus=event_bus)
        
        # Force an error during initialization
        with patch.object(ServerCapabilities, "get_default", side_effect=Exception("Test error")):
            client_info = ClientInfo(name="TestClient", version="1.0.0")
            client_capabilities = ClientCapabilities(methods=[], notifications=[])
            
            with pytest.raises(SessionError):
                await session.initialize(client_info, client_capabilities)
            
            assert session.state == SessionState.ERROR
            assert session.context.error == "Test error"
            
            # Check error event was emitted
            error_events = [
                call.args[0] for call in event_bus.publish.call_args_list
                if call.args[0].event_type == SessionEvent.ERROR.value
            ]
            assert len(error_events) > 0


class TestSessionManager:
    """Test SessionManager class."""
    
    @pytest.mark.asyncio
    async def test_manager_creation(self):
        """Test session manager creation."""
        manager = SessionManager()
        
        assert manager.default_timeout == 3600
        assert manager.max_sessions_per_client == 10
        assert manager.cleanup_interval == 60
        
        stats = manager.get_stats()
        assert stats["total_sessions"] == 0
        assert stats["active_sessions"] == 0
        assert stats["clients"] == 0
    
    @pytest.mark.asyncio
    async def test_create_session(self):
        """Test creating a new session."""
        manager = SessionManager()
        transport = MockTransport()
        
        session = await manager.create_session(transport, client_id="client1")
        
        assert session is not None
        assert session.state == SessionState.INITIALIZING
        assert await manager.get_session(session.id) == session
        
        stats = manager.get_stats()
        assert stats["total_sessions"] == 1
        assert stats["active_sessions"] == 1
    
    @pytest.mark.asyncio
    async def test_get_session_by_transport(self):
        """Test getting session by transport."""
        manager = SessionManager()
        transport = MockTransport()
        
        session = await manager.create_session(transport)
        retrieved_session = await manager.get_session_by_transport(transport)
        
        assert retrieved_session == session
    
    @pytest.mark.asyncio
    async def test_client_session_limit(self):
        """Test per-client session limits."""
        manager = SessionManager(max_sessions_per_client=2)
        
        # Create 3 sessions for the same client
        sessions = []
        for i in range(3):
            transport = MockTransport()
            session = await manager.create_session(transport, client_id="client1")
            sessions.append(session)
        
        # Only the last 2 sessions should be active
        assert await manager.get_session(sessions[0].id) is None  # First session closed
        assert await manager.get_session(sessions[1].id) is not None
        assert await manager.get_session(sessions[2].id) is not None
        
        client_sessions = await manager.list_sessions(client_id="client1")
        assert len(client_sessions) == 2
    
    @pytest.mark.asyncio
    async def test_list_sessions_with_filters(self):
        """Test listing sessions with various filters."""
        manager = SessionManager()
        
        # Create sessions for different clients
        transport1 = MockTransport()
        session1 = await manager.create_session(transport1, client_id="client1")
        
        transport2 = MockTransport()
        session2 = await manager.create_session(transport2, client_id="client2")
        
        # Initialize one session
        client_info = ClientInfo(name="TestClient", version="1.0.0")
        client_capabilities = ClientCapabilities(methods=[], notifications=[])
        await session1.initialize(client_info, client_capabilities)
        
        # Test filtering by client
        client1_sessions = await manager.list_sessions(client_id="client1")
        assert len(client1_sessions) == 1
        assert client1_sessions[0] == session1
        
        # Test filtering by state
        ready_sessions = await manager.list_sessions(state=SessionState.READY)
        assert len(ready_sessions) == 1
        assert ready_sessions[0] == session1
        
        # Test active only filter
        active_sessions = await manager.list_sessions(active_only=True)
        assert len(active_sessions) == 2
    
    @pytest.mark.asyncio
    async def test_close_session(self):
        """Test closing a specific session."""
        manager = SessionManager()
        transport = MockTransport()
        
        session = await manager.create_session(transport)
        session_id = session.id
        
        # Close session
        result = await manager.close_session(session_id, reason="test")
        assert result is True
        assert transport.closed is True
        
        # Session should be removed
        assert await manager.get_session(session_id) is None
        
        # Closing non-existent session should return False
        result = await manager.close_session("non-existent")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_close_client_sessions(self):
        """Test closing all sessions for a client."""
        manager = SessionManager()
        
        # Create multiple sessions for one client
        sessions = []
        for i in range(3):
            transport = MockTransport()
            session = await manager.create_session(transport, client_id="client1")
            sessions.append(session)
        
        # Close all client sessions
        count = await manager.close_client_sessions("client1", reason="client disconnect")
        assert count == 3
        
        # All sessions should be closed
        for session in sessions:
            assert await manager.get_session(session.id) is None
    
    @pytest.mark.asyncio
    async def test_cleanup_inactive_sessions(self):
        """Test cleanup of inactive sessions."""
        manager = SessionManager()
        
        # Create a session with short timeout
        transport = MockTransport()
        session = await manager.create_session(transport, timeout=1)
        
        # Initialize session
        client_info = ClientInfo(name="TestClient", version="1.0.0")
        client_capabilities = ClientCapabilities(methods=[], notifications=[])
        await session.initialize(client_info, client_capabilities)
        
        # Wait for timeout
        await asyncio.sleep(1.5)
        
        # Run cleanup
        count = await manager.cleanup_inactive_sessions()
        assert count == 1
        
        # Session should be removed
        assert await manager.get_session(session.id) is None
    
    @pytest.mark.asyncio
    async def test_session_context_manager(self):
        """Test session context manager."""
        manager = SessionManager()
        transport = MockTransport()
        
        async with manager.session_context(transport, client_id="client1") as session:
            assert session is not None
            assert session.state == SessionState.INITIALIZING
            session_id = session.id
            
            # Session should exist in manager
            assert await manager.get_session(session_id) is not None
        
        # Session should be closed after context exit
        assert await manager.get_session(session_id) is None
    
    @pytest.mark.asyncio
    async def test_shutdown(self):
        """Test graceful shutdown."""
        manager = SessionManager()
        
        # Create multiple sessions
        sessions = []
        for i in range(3):
            transport = MockTransport()
            session = await manager.create_session(transport)
            sessions.append(session)
        
        # Shutdown manager
        await manager.shutdown()
        
        # All sessions should be closed
        stats = manager.get_stats()
        assert stats["total_sessions"] == 0
        
        # Cleanup task should be cancelled
        assert manager._cleanup_task.cancelled()


@pytest.mark.asyncio
async def test_client_info_validation():
    """Test ClientInfo validation."""
    # Valid client info
    client_info = ClientInfo(name="TestClient", version="1.0.0")
    assert client_info.name == "TestClient"
    assert client_info.version == "1.0.0"
    
    # Invalid client info - empty name
    with pytest.raises(ValueError, match="Client name is required"):
        ClientInfo(name="", version="1.0.0")
    
    # Invalid client info - empty version
    with pytest.raises(ValueError, match="Client version is required"):
        ClientInfo(name="TestClient", version="")
