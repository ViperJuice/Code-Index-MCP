"""
Session data models and types.

Shared models used across the session management system.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass, field


class SessionState(Enum):
    """Session lifecycle states."""
    INITIALIZING = "initializing"
    READY = "ready"
    CLOSING = "closing"
    CLOSED = "closed"
    ERROR = "error"


class SessionEvent(Enum):
    """Session lifecycle events."""
    CREATED = "session.created"
    INITIALIZED = "session.initialized"
    READY = "session.ready"
    CLOSING = "session.closing"
    CLOSED = "session.closed"
    TIMEOUT = "session.timeout"
    ERROR = "session.error"
    ACTIVITY_UPDATED = "session.activity_updated"
    STATE_CHANGED = "session.state_changed"


@dataclass
class ClientInfo:
    """Client information."""
    name: str
    version: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate client info."""
        if not self.name:
            raise ValueError("Client name is required")
        if not self.version:
            raise ValueError("Client version is required")


@dataclass
class SessionContext:
    """Session context data."""
    session_id: str
    client_info: Optional[ClientInfo] = None
    client_capabilities: Optional['ClientCapabilities'] = None
    server_capabilities: Optional['ServerCapabilities'] = None
    negotiated_capabilities: Optional[Dict[str, Any]] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    state: SessionState = SessionState.INITIALIZING
    error: Optional[str] = None


class SessionError(Exception):
    """Session-specific error."""
    pass
