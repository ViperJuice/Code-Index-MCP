"""
Tests for MCP session management.
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, MagicMock

from mcp_server.session import (
    Session,
    SessionManager,
    SessionState,
    SessionEvent,
    ClientInfo,
    SessionContext,
    SessionStore,
    ClientCapabilities,
    ServerCapabilities,
    negotiate_capabilities
)
from mcp_server.transport.base import Transport
from mcp_server.interfaces.shared_interfaces import Event, IEventBus


class MockTransport(Transport):
    """Mock transport for testing."""
    
    def __init__(self):
        self.sent_messages = []
        self.closed = False
    
    async def send(self, message: str) -> None:
        self.sent_messages.append(message)
    
    async def receive(self):
        while True:
            yield "test message"
    
    async def close(self) -> None:
        self.closed = True


class MockEventBus(IEventBus):
    """Mock event bus for testing."""
    
    def __init__(self):
        self.events = []
    
    def publish(self, event: Event) -> None:
        self.events.append(event)
    
    def subscribe(self, event_type: str, handler) -> None:
        pass
    
    def unsubscribe(self, event_type: str, handler) -> None:
        pass


@pytest.mark.asyncio
async def test_session_lifecycle():
    """Test session state transitions."""
    transport = MockTransport()
    event_bus = MockEventBus()
    
    session = Session("test-session", transport, timeout_seconds=3600, event_bus=event_bus)
    
    # Initial state
    assert session.state == SessionState.INITIALIZING
    assert session.is_active
    
    # Initialize session
    client_info = ClientInfo(name="test-client", version="1.0")
    client_caps = ClientCapabilities()
    
    await session.initialize(client_info, client_caps)
    
    assert session.state == SessionState.READY
    assert session.context.client_info == client_info
    assert session.context.client_capabilities == client_caps
    assert session.context.server_capabilities is not None
    assert session.context.negotiated_capabilities is not None
    
    # Check events
    event_types = [e.event_type for e in event_bus.events]
    assert SessionEvent.INITIALIZED.value in event_types
    assert SessionEvent.READY.value in event_types
    
    # Close session
    await session.close()
    
    assert session.state == SessionState.CLOSED
    assert not session.is_active
    assert transport.closed
    
    # Check closing events
    event_types = [e.event_type for e in event_bus.events]
    assert SessionEvent.CLOSING.value in event_types
    assert SessionEvent.CLOSED.value in event_types


@pytest.mark.asyncio
async def test_session_timeout():
    """Test session timeout handling."""
    transport = MockTransport()
    event_bus = MockEventBus()
    
    # Create session with 1 second timeout
    session = Session("test-session", transport, timeout_seconds=1, event_bus=event_bus)
    
    # Initialize session
    client_info = ClientInfo(name="test-client", version="1.0")
    await session.initialize(client_info, ClientCapabilities())
    
    # Wait for timeout
    await asyncio.sleep(1.5)
    
    # Session should be closed due to timeout
    assert session.state == SessionState.CLOSED
    
    # Check timeout event
    event_types = [e.event_type for e in event_bus.events]
    assert SessionEvent.TIMEOUT.value in event_types


@pytest.mark.asyncio
async def test_session_activity_tracking():
    """Test session activity updates."""
    transport = MockTransport()
    session = Session("test-session", transport)
    
    initial_activity = session.context.last_activity
    
    # Wait a bit
    await asyncio.sleep(0.1)
    
    # Update activity
    await session.update_activity()
    
    assert session.context.last_activity > initial_activity


@pytest.mark.asyncio
async def test_session_subscriptions():
    """Test session subscription management."""
    transport = MockTransport()
    session = Session("test-session", transport)
    
    # Add subscriptions
    await session.add_subscription("resource://file/test.py")
    await session.add_subscription("resource://project/myproject")
    
    subs = session.get_subscriptions()
    assert len(subs) == 2
    assert "resource://file/test.py" in subs
    assert "resource://project/myproject" in subs
    
    # Remove subscription
    await session.remove_subscription("resource://file/test.py")
    
    subs = session.get_subscriptions()
    assert len(subs) == 1
    assert "resource://project/myproject" in subs


@pytest.mark.asyncio
async def test_session_manager_create():
    """Test session manager creation."""
    store = SessionStore()
    event_bus = MockEventBus()
    manager = SessionManager(store=store, event_bus=event_bus)
    
    transport = MockTransport()
    session = await manager.create_session(transport)
    
    assert session is not None
    assert session.id is not None
    assert await manager.get_session(session.id) == session
    
    # Check event
    assert any(e.event_type == SessionEvent.CREATED.value for e in event_bus.events)
    
    # Cleanup
    await manager.shutdown()


@pytest.mark.asyncio
async def test_session_manager_client_limits():
    """Test client session limits."""
    manager = SessionManager(max_sessions_per_client=2)
    
    # Create sessions for a client
    transport1 = MockTransport()
    session1 = await manager.create_session(transport1, client_id="client1")
    
    transport2 = MockTransport()
    session2 = await manager.create_session(transport2, client_id="client1")
    
    # Third session should remove the oldest
    transport3 = MockTransport()
    session3 = await manager.create_session(transport3, client_id="client1")
    
    # First session should be closed
    assert await manager.get_session(session1.id) is None
    assert await manager.get_session(session2.id) is not None
    assert await manager.get_session(session3.id) is not None
    
    # Cleanup
    await manager.shutdown()


@pytest.mark.asyncio
async def test_session_manager_list():
    """Test listing sessions."""
    manager = SessionManager()
    
    # Create sessions
    transport1 = MockTransport()
    session1 = await manager.create_session(transport1, client_id="client1")
    await session1.initialize(
        ClientInfo(name="client1", version="1.0"),
        ClientCapabilities()
    )
    
    transport2 = MockTransport()
    session2 = await manager.create_session(transport2, client_id="client2")
    
    # List all sessions
    sessions = await manager.list_sessions()
    assert len(sessions) == 2
    
    # List by client
    client1_sessions = await manager.list_sessions(client_id="client1")
    assert len(client1_sessions) == 1
    assert client1_sessions[0].id == session1.id
    
    # List by state
    ready_sessions = await manager.list_sessions(state=SessionState.READY)
    assert len(ready_sessions) == 1
    assert ready_sessions[0].id == session1.id
    
    # Cleanup
    await manager.shutdown()


@pytest.mark.asyncio
async def test_session_manager_cleanup():
    """Test inactive session cleanup."""
    manager = SessionManager(default_timeout=1)
    
    # Create session
    transport = MockTransport()
    session = await manager.create_session(transport)
    
    # Wait for timeout
    await asyncio.sleep(1.5)
    
    # Run cleanup
    cleaned = await manager.cleanup_inactive_sessions()
    assert cleaned == 1
    
    # Session should be gone
    assert await manager.get_session(session.id) is None
    
    # Cleanup
    await manager.shutdown()


@pytest.mark.asyncio
async def test_capability_negotiation():
    """Test capability negotiation."""
    client_caps = ClientCapabilities(
        supports_resources=True,
        supports_tools=True,
        supports_streaming=True,
        supported_resource_types=["file", "project"]
    )
    
    server_caps = ServerCapabilities.get_default()
    
    negotiated = negotiate_capabilities(client_caps, server_caps)
    
    # Check negotiated features
    assert negotiated["features"]["resources"]["enabled"]
    assert negotiated["features"]["tools"]["enabled"]
    assert not negotiated["features"].get("streaming", {}).get("enabled", False)
    
    # Check resource types
    resource_types = negotiated["features"]["resources"]["types"]
    assert "file" in resource_types
    assert "project" in resource_types
    assert len(resource_types) == 2  # Only the ones client supports


@pytest.mark.asyncio
async def test_session_store():
    """Test session storage."""
    store = SessionStore(persist_sessions=False)
    
    # Create context
    context = SessionContext(
        session_id="test-123",
        client_info=ClientInfo(name="test", version="1.0")
    )
    
    # Save
    await store.save(context)
    assert await store.exists("test-123")
    
    # Find
    found = await store.find("test-123")
    assert found is not None
    assert found.session_id == "test-123"
    assert found.client_info.name == "test"
    
    # List with filters
    all_sessions = await store.find_all()
    assert len(all_sessions) == 1
    
    filtered = await store.find_all({"client_name": "test"})
    assert len(filtered) == 1
    
    filtered = await store.find_all({"client_name": "other"})
    assert len(filtered) == 0
    
    # Delete
    assert await store.delete("test-123")
    assert not await store.exists("test-123")


@pytest.mark.asyncio
async def test_session_store_persistence(tmp_path):
    """Test session persistence to disk."""
    persistence_path = tmp_path / "sessions.json"
    
    # Create store with persistence
    store1 = SessionStore(persist_sessions=True, persistence_path=persistence_path)
    
    # Save a session
    context = SessionContext(
        session_id="persist-123",
        client_info=ClientInfo(name="persistent", version="2.0"),
        metadata={"key": "value"}
    )
    await store1.save(context)
    
    # Wait for persistence
    await asyncio.sleep(0.1)
    
    # Create new store and check if session was loaded
    store2 = SessionStore(persist_sessions=True, persistence_path=persistence_path)
    await asyncio.sleep(0.1)  # Wait for load
    
    loaded = await store2.find("persist-123")
    assert loaded is not None
    assert loaded.client_info.name == "persistent"
    assert loaded.metadata["key"] == "value"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])