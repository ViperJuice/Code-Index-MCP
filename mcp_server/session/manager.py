"""
MCP session lifecycle management.

Manages session creation, state transitions, and cleanup.
"""

import asyncio
import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Set, List, Callable, Awaitable, Union
import weakref
from contextlib import asynccontextmanager

from ..interfaces.shared_interfaces import IEventBus, Event, ILogger
from ..transport.base import Transport
from .models import SessionState, SessionEvent, ClientInfo, SessionContext, SessionError
from .capabilities import ServerCapabilities, ClientCapabilities, negotiate_capabilities

logger = logging.getLogger(__name__)


class Session:
    """Individual session instance with full lifecycle management."""
    
    def __init__(
        self,
        session_id: str,
        transport: Transport,
        timeout_seconds: int = 3600,
        event_bus: Optional[IEventBus] = None,
        logger: Optional[ILogger] = None
    ):
        self.id = session_id
        self.transport = transport
        self.timeout_seconds = timeout_seconds
        self.event_bus = event_bus
        self.logger = logger or logging.getLogger(__name__)
        
        self._state = SessionState.INITIALIZING
        self._context = SessionContext(session_id=session_id)
        self._state_lock = asyncio.Lock()
        self._timeout_task: Optional[asyncio.Task] = None
        self._subscriptions: Set[str] = set()
        self._handlers: Dict[str, List[Callable]] = {}
        self._closing_event = asyncio.Event()
        self._ready_event = asyncio.Event()
        
        # State transition validators
        self._valid_transitions = {
            SessionState.INITIALIZING: {SessionState.READY, SessionState.ERROR, SessionState.CLOSED},
            SessionState.READY: {SessionState.CLOSING, SessionState.ERROR},
            SessionState.ERROR: {SessionState.CLOSING, SessionState.CLOSED},
            SessionState.CLOSING: {SessionState.CLOSED},
            SessionState.CLOSED: set()
        }
        
        # Start timeout monitoring
        self._start_timeout_monitoring()
    
    @property
    def state(self) -> SessionState:
        """Get current session state."""
        return self._state
    
    @property
    def context(self) -> SessionContext:
        """Get session context."""
        return self._context
    
    @property
    def is_active(self) -> bool:
        """Check if session is active."""
        return self._state in (SessionState.INITIALIZING, SessionState.READY)
    
    @property
    def is_ready(self) -> bool:
        """Check if session is ready for operations."""
        return self._state == SessionState.READY
    
    async def wait_ready(self, timeout: Optional[float] = None) -> bool:
        """Wait for session to become ready."""
        try:
            await asyncio.wait_for(self._ready_event.wait(), timeout)
            return True
        except asyncio.TimeoutError:
            return False
    
    async def initialize(
        self,
        client_info: ClientInfo,
        client_capabilities: ClientCapabilities
    ) -> None:
        """Initialize the session with client information."""
        async with self._state_lock:
            if self._state != SessionState.INITIALIZING:
                raise SessionError(f"Cannot initialize session in state {self._state}")
            
            try:
                self._context.client_info = client_info
                self._context.client_capabilities = client_capabilities
                
                # Get server capabilities
                self._context.server_capabilities = ServerCapabilities.get_default()
                
                # Negotiate capabilities
                self._context.negotiated_capabilities = negotiate_capabilities(
                    client_capabilities,
                    self._context.server_capabilities
                )
                
                await self._transition_to(SessionState.READY)
                self._ready_event.set()
                await self._emit_event(SessionEvent.INITIALIZED)
                await self._emit_event(SessionEvent.READY)
                
            except Exception as e:
                self.logger.error(f"Error initializing session {self.id}: {e}")
                self._context.error = str(e)
                await self._transition_to(SessionState.ERROR)
                await self._emit_event(SessionEvent.ERROR, {"error": str(e)})
                raise SessionError(f"Session initialization failed: {e}") from e
    
    async def update_activity(self) -> None:
        """Update last activity timestamp."""
        self._context.last_activity = datetime.utcnow()
        self._reset_timeout()
        await self._emit_event(SessionEvent.ACTIVITY_UPDATED)
    
    async def add_subscription(self, resource_uri: str) -> None:
        """Add a resource subscription."""
        if not self.is_ready:
            raise SessionError(f"Cannot add subscription in state {self._state}")
        self._subscriptions.add(resource_uri)
        await self.update_activity()
    
    async def remove_subscription(self, resource_uri: str) -> None:
        """Remove a resource subscription."""
        self._subscriptions.discard(resource_uri)
        await self.update_activity()
    
    def get_subscriptions(self) -> Set[str]:
        """Get all active subscriptions."""
        return self._subscriptions.copy()
    
    async def send_message(self, message: str) -> None:
        """Send a message through the transport."""
        if not self.is_active:
            raise SessionError(f"Cannot send message in state {self._state}")
        
        try:
            await self.transport.send(message)
            await self.update_activity()
        except Exception as e:
            self.logger.error(f"Error sending message in session {self.id}: {e}")
            await self._handle_error(e)
            raise
    async def close(self, reason: Optional[str] = None) -> None:
        """Close the session gracefully."""
        async with self._state_lock:
            if self._state == SessionState.CLOSED:
                return
            
            if self._state != SessionState.CLOSING:
                await self._transition_to(SessionState.CLOSING)
                await self._emit_event(SessionEvent.CLOSING, {"reason": reason})
            
            # Set closing event
            self._closing_event.set()
            
            # Cancel timeout monitoring
            if self._timeout_task:
                self._timeout_task.cancel()
                try:
                    await self._timeout_task
                except asyncio.CancelledError:
                    pass
            
            # Close transport
            try:
                await self.transport.close()
            except Exception as e:
                self.logger.error(f"Error closing transport for session {self.id}: {e}")
            
            # Clear subscriptions
            self._subscriptions.clear()
            
            # Clear handlers
            self._handlers.clear()
            
            await self._transition_to(SessionState.CLOSED)
            await self._emit_event(SessionEvent.CLOSED, {"reason": reason})
    
    async def _handle_error(self, error: Exception) -> None:
        """Handle session error."""
        self._context.error = str(error)
        if self._state not in (SessionState.CLOSING, SessionState.CLOSED, SessionState.ERROR):
            await self._transition_to(SessionState.ERROR)
            await self._emit_event(SessionEvent.ERROR, {"error": str(error)})
    
    async def _transition_to(self, new_state: SessionState) -> None:
        """Transition to a new state with validation."""
        old_state = self._state
        
        # Validate transition
        if new_state not in self._valid_transitions.get(old_state, set()):
            raise SessionError(f"Invalid state transition from {old_state} to {new_state}")
        
        self._state = new_state
        self._context.state = new_state
        
        self.logger.info(f"Session {self.id} transitioned from {old_state} to {new_state}")
        
        await self._emit_event(SessionEvent.STATE_CHANGED, {
            "old_state": old_state.value,
            "new_state": new_state.value
        })
    
    async def _emit_event(self, event_type: SessionEvent, data: Optional[Dict[str, Any]] = None) -> None:
        """Emit a session event."""
        if self.event_bus:
            event = Event(
                event_type=event_type.value,
                timestamp=datetime.utcnow(),
                source=f"session:{self.id}",
                data={
                    "session_id": self.id,
                    "state": self._state.value,
                    **(data or {})
                }
            )
            self.event_bus.publish(event)
    
    def _start_timeout_monitoring(self) -> None:
        """Start timeout monitoring."""
        if self.timeout_seconds > 0:
            self._timeout_task = asyncio.create_task(self._monitor_timeout())
    
    def _reset_timeout(self) -> None:
        """Reset the timeout timer."""
        if self._timeout_task:
            self._timeout_task.cancel()
        if self.timeout_seconds > 0 and self.is_active:
            self._timeout_task = asyncio.create_task(self._monitor_timeout())
    
    async def _monitor_timeout(self) -> None:
        """Monitor session timeout."""
        try:
            await asyncio.sleep(self.timeout_seconds)
            
            # Check if session has timed out
            if self.is_active:
                inactive_seconds = (datetime.utcnow() - self._context.last_activity).total_seconds()
                if inactive_seconds >= self.timeout_seconds:
                    self.logger.warning(f"Session {self.id} timed out after {inactive_seconds} seconds")
                    await self._emit_event(SessionEvent.TIMEOUT)
                    await self.close(reason="timeout")
        except asyncio.CancelledError:
            pass


class SessionManager:
    """
    Manages all active sessions with thread-safe operations.
    
    Features:
    - Session lifecycle management
    - Client session limits
    - Automatic timeout handling
    - Event notifications
    - Persistent session storage
    """
    
    def __init__(
        self,
        store: Optional["SessionStore"] = None,  # Use string annotation to avoid import
        event_bus: Optional[IEventBus] = None,
        default_timeout: int = 3600,
        max_sessions_per_client: int = 10,
        cleanup_interval: int = 60,
        logger: Optional[ILogger] = None
    ):
        # Lazy import to avoid circular dependency
        if store is None:
            from .store import SessionStore
            store = SessionStore()
        
        self.store = store
        self.event_bus = event_bus
        self.default_timeout = default_timeout
        self.max_sessions_per_client = max_sessions_per_client
        self.cleanup_interval = cleanup_interval
        self.logger = logger or logging.getLogger(__name__)
        
        self._sessions: Dict[str, Session] = {}
        self._client_sessions: Dict[str, Set[str]] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        
        # Weak references for transport tracking
        self._transport_sessions: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()
        
        # Start periodic cleanup
        self._start_cleanup_task()
    
    async def create_session(
        self,
        transport: Transport,
        client_id: Optional[str] = None,
        timeout: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Session:
        """Create a new session with the given transport."""
        async with self._lock:
            # Check client session limit
            if client_id:
                await self._enforce_client_session_limit(client_id)
            
            # Generate session ID
            session_id = str(uuid.uuid4())
            
            # Create session
            session = Session(
                session_id=session_id,
                transport=transport,
                timeout_seconds=timeout or self.default_timeout,
                event_bus=self.event_bus,
                logger=self.logger
            )
            
            # Add metadata
            if metadata:
                session.context.metadata.update(metadata)
            
            # Store session
            self._sessions[session_id] = session
            self._transport_sessions[transport] = session_id
            
            if client_id:
                if client_id not in self._client_sessions:
                    self._client_sessions[client_id] = set()
                self._client_sessions[client_id].add(session_id)
            
            # Store in persistent store
            await self.store.save_session(session_id, session.context)
            
            # Emit event
            if self.event_bus:
                event = Event(
                    event_type=SessionEvent.CREATED.value,
                    timestamp=datetime.utcnow(),
                    source="session_manager",
                    data={
                        "session_id": session_id,
                        "client_id": client_id,
                        "timeout": session.timeout_seconds
                    }
                )
                self.event_bus.publish(event)
            
            self.logger.info(f"Created session {session_id} for client {client_id}")
            return session
    
    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID."""
        return self._sessions.get(session_id)
    
    async def get_session_by_transport(self, transport: Transport) -> Optional[Session]:
        """Get a session by its transport."""
        session_id = self._transport_sessions.get(transport)
        if session_id:
            return await self.get_session(session_id)
        return None
    
    async def list_sessions(
        self,
        client_id: Optional[str] = None,
        state: Optional[SessionState] = None,
        active_only: bool = False
    ) -> List[Session]:
        """List sessions with optional filters."""
        sessions = list(self._sessions.values())
        
        if client_id:
            session_ids = self._client_sessions.get(client_id, set())
            sessions = [s for s in sessions if s.id in session_ids]
        
        if state:
            sessions = [s for s in sessions if s.state == state]
        
        if active_only:
            sessions = [s for s in sessions if s.is_active]
        
        return sessions
    async def close_session(self, session_id: str, reason: Optional[str] = None) -> bool:
        """Close a specific session."""
        async with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return False
            
            await session.close(reason=reason)
            
            # Remove from tracking
            del self._sessions[session_id]
            
            # Remove from client sessions
            for client_sessions in self._client_sessions.values():
                client_sessions.discard(session_id)
            
            # Remove from store
            await self.store.delete_session(session_id)
            
            self.logger.info(f"Closed session {session_id} (reason: {reason})")
            return True
    
    async def close_client_sessions(self, client_id: str, reason: Optional[str] = None) -> int:
        """Close all sessions for a client."""
        session_ids = self._client_sessions.get(client_id, set()).copy()
        count = 0
        
        for session_id in session_ids:
            if await self.close_session(session_id, reason=reason):
                count += 1
        
        # Remove client entry if no sessions left
        if client_id in self._client_sessions and not self._client_sessions[client_id]:
            del self._client_sessions[client_id]
        
        return count
    
    async def close_all_sessions(self, reason: Optional[str] = None) -> int:
        """Close all active sessions."""
        session_ids = list(self._sessions.keys())
        count = 0
        
        for session_id in session_ids:
            if await self.close_session(session_id, reason=reason):
                count += 1
        
        return count
    
    async def cleanup_inactive_sessions(self) -> int:
        """Clean up inactive and timed-out sessions."""
        count = 0
        current_time = datetime.utcnow()
        
        for session in list(self._sessions.values()):
            if not session.is_active:
                if await self.close_session(session.id, reason="inactive"):
                    count += 1
            elif session.timeout_seconds > 0:
                inactive_seconds = (current_time - session.context.last_activity).total_seconds()
                if inactive_seconds > session.timeout_seconds:
                    self.logger.info(f"Cleaning up inactive session {session.id}")
                    if await self.close_session(session.id, reason="timeout"):
                        count += 1
        
        return count
    
    @asynccontextmanager
    async def session_context(
        self,
        transport: Transport,
        client_id: Optional[str] = None,
        timeout: Optional[int] = None
    ):
        """Context manager for session lifecycle."""
        session = await self.create_session(transport, client_id, timeout)
        try:
            yield session
        finally:
            await self.close_session(session.id, reason="context_exit")
    
    async def _enforce_client_session_limit(self, client_id: str) -> None:
        """Enforce per-client session limits."""
        client_sessions = self._client_sessions.get(client_id, set())
        
        while len(client_sessions) >= self.max_sessions_per_client:
            # Find oldest session
            oldest_session = None
            oldest_time = datetime.utcnow()
            
            for session_id in client_sessions:
                session = self._sessions.get(session_id)
                if session and session.context.created_at < oldest_time:
                    oldest_session = session_id
                    oldest_time = session.context.created_at
            
            if oldest_session:
                await self.close_session(oldest_session, reason="client_limit_exceeded")
                client_sessions.discard(oldest_session)
            else:
                break
    
    def _start_cleanup_task(self) -> None:
        """Start periodic cleanup task."""
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
    
    async def _periodic_cleanup(self) -> None:
        """Periodically clean up inactive sessions."""
        while not self._shutdown_event.is_set():
            try:
                await asyncio.wait_for(
                    self._shutdown_event.wait(),
                    timeout=self.cleanup_interval
                )
            except asyncio.TimeoutError:
                try:
                    count = await self.cleanup_inactive_sessions()
                    if count > 0:
                        self.logger.info(f"Cleaned up {count} inactive sessions")
                except Exception as e:
                    self.logger.error(f"Error in periodic cleanup: {e}")
    
    async def shutdown(self) -> None:
        """Shutdown the session manager gracefully."""
        self.logger.info("Shutting down session manager...")
        
        # Signal shutdown
        self._shutdown_event.set()
        
        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Close all sessions
        count = await self.close_all_sessions(reason="shutdown")
        self.logger.info(f"Session manager shutdown complete, closed {count} sessions")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get session manager statistics."""
        return {
            "total_sessions": len(self._sessions),
            "active_sessions": sum(1 for s in self._sessions.values() if s.is_active),
            "ready_sessions": sum(1 for s in self._sessions.values() if s.is_ready),
            "error_sessions": sum(1 for s in self._sessions.values() if s.state == SessionState.ERROR),
            "clients": len(self._client_sessions),
            "states": {
                state.value: sum(1 for s in self._sessions.values() if s.state == state)
                for state in SessionState
            }
        }
