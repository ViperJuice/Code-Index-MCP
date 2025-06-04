"""Session management for MCP protocol"""
import uuid
import time
from typing import Dict, Any, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import logging
import asyncio

logger = logging.getLogger(__name__)

class SessionState(Enum):
    """MCP session states"""
    CREATED = "created"
    INITIALIZING = "initializing"
    INITIALIZED = "initialized"
    SHUTTING_DOWN = "shutting_down"
    CLOSED = "closed"

@dataclass
class ClientInfo:
    """Client information from MCP initialize request"""
    name: str
    version: str
    extension_data: Optional[Dict[str, Any]] = None

@dataclass
class MCPCapabilities:
    """MCP server capabilities"""
    resources: Dict[str, Any] = field(default_factory=dict)
    tools: Dict[str, Any] = field(default_factory=dict)
    prompts: Dict[str, Any] = field(default_factory=dict)
    sampling: Dict[str, Any] = field(default_factory=dict)
    completion: Dict[str, Any] = field(default_factory=dict)
    logging: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert capabilities to dictionary"""
        result = {}
        if self.resources:
            result["resources"] = self.resources
        if self.tools:
            result["tools"] = self.tools
        if self.prompts:
            result["prompts"] = self.prompts
        if self.sampling:
            result["sampling"] = self.sampling
        if self.completion:
            result["completion"] = self.completion
        if self.logging:
            result["logging"] = self.logging
        return result

@dataclass
class MCPSession:
    """MCP session object"""
    session_id: str
    client_info: Optional[ClientInfo] = None
    protocol_version: str = "1.0"
    state: SessionState = SessionState.CREATED
    capabilities: MCPCapabilities = field(default_factory=MCPCapabilities)
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    subscriptions: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = time.time()
    
    def is_initialized(self) -> bool:
        """Check if session is initialized"""
        return self.state == SessionState.INITIALIZED
    
    def subscribe(self, resource_uri: str):
        """Add resource subscription"""
        self.subscriptions.add(resource_uri)
        logger.debug(f"Session {self.session_id} subscribed to {resource_uri}")
    
    def unsubscribe(self, resource_uri: str):
        """Remove resource subscription"""
        self.subscriptions.discard(resource_uri)
        logger.debug(f"Session {self.session_id} unsubscribed from {resource_uri}")
    
    def is_subscribed(self, resource_uri: str) -> bool:
        """Check if subscribed to resource"""
        return resource_uri in self.subscriptions

class SessionManager:
    """Manages MCP sessions"""
    
    def __init__(self, session_timeout: int = 3600):
        """
        Initialize session manager
        
        Args:
            session_timeout: Session timeout in seconds (default 1 hour)
        """
        self.sessions: Dict[str, MCPSession] = {}
        self.session_timeout = session_timeout
        self._cleanup_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
    
    async def start(self):
        """Start session manager background tasks"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("Session manager started")
    
    async def stop(self):
        """Stop session manager background tasks"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
        
        # Close all sessions
        async with self._lock:
            for session in self.sessions.values():
                session.state = SessionState.CLOSED
            self.sessions.clear()
        
        logger.info("Session manager stopped")
    
    def generate_session_id(self) -> str:
        """Generate unique session ID"""
        return str(uuid.uuid4())
    
    async def create_session(self, session_id: Optional[str] = None) -> MCPSession:
        """
        Create new MCP session
        
        Args:
            session_id: Optional session ID, generates one if not provided
            
        Returns:
            New MCPSession object
        """
        if session_id is None:
            session_id = self.generate_session_id()
        
        async with self._lock:
            if session_id in self.sessions:
                raise ValueError(f"Session {session_id} already exists")
            
            session = MCPSession(session_id=session_id)
            self.sessions[session_id] = session
            logger.info(f"Created session {session_id}")
            return session
    
    async def get_session(self, session_id: str) -> Optional[MCPSession]:
        """
        Get session by ID
        
        Args:
            session_id: Session ID to lookup
            
        Returns:
            MCPSession object or None if not found
        """
        async with self._lock:
            session = self.sessions.get(session_id)
            if session:
                session.update_activity()
            return session
    
    async def remove_session(self, session_id: str):
        """
        Remove session
        
        Args:
            session_id: Session ID to remove
        """
        async with self._lock:
            session = self.sessions.pop(session_id, None)
            if session:
                session.state = SessionState.CLOSED
                logger.info(f"Removed session {session_id}")
    
    async def initialize_session(
        self,
        session_id: str,
        client_info: ClientInfo,
        protocol_version: str,
        capabilities: MCPCapabilities
    ) -> MCPSession:
        """
        Initialize a session with client info
        
        Args:
            session_id: Session ID
            client_info: Client information
            protocol_version: Protocol version
            capabilities: Server capabilities
            
        Returns:
            Updated MCPSession object
        """
        async with self._lock:
            session = self.sessions.get(session_id)
            if not session:
                raise ValueError(f"Session {session_id} not found")
            
            if session.state != SessionState.CREATED:
                raise ValueError(f"Session {session_id} already initialized")
            
            session.state = SessionState.INITIALIZING
            session.client_info = client_info
            session.protocol_version = protocol_version
            session.capabilities = capabilities
            session.state = SessionState.INITIALIZED
            session.update_activity()
            
            logger.info(f"Initialized session {session_id} for client {client_info.name} v{client_info.version}")
            return session
    
    async def shutdown_session(self, session_id: str):
        """
        Shutdown a session gracefully
        
        Args:
            session_id: Session ID to shutdown
        """
        async with self._lock:
            session = self.sessions.get(session_id)
            if session:
                session.state = SessionState.SHUTTING_DOWN
                # Allow cleanup operations
                await asyncio.sleep(0.1)
                session.state = SessionState.CLOSED
                logger.info(f"Shutdown session {session_id}")
    
    async def list_sessions(self) -> Dict[str, Dict[str, Any]]:
        """
        List all active sessions
        
        Returns:
            Dictionary of session ID to session info
        """
        async with self._lock:
            return {
                session_id: {
                    "client": session.client_info.name if session.client_info else "Unknown",
                    "version": session.client_info.version if session.client_info else "Unknown",
                    "state": session.state.value,
                    "created_at": session.created_at,
                    "last_activity": session.last_activity,
                    "subscriptions": len(session.subscriptions)
                }
                for session_id, session in self.sessions.items()
            }
    
    async def _cleanup_loop(self):
        """Background task to cleanup expired sessions"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                await self._cleanup_expired_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in session cleanup: {e}")
    
    async def _cleanup_expired_sessions(self):
        """Remove expired sessions"""
        current_time = time.time()
        expired_sessions = []
        
        async with self._lock:
            for session_id, session in self.sessions.items():
                if current_time - session.last_activity > self.session_timeout:
                    expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            await self.remove_session(session_id)
            logger.info(f"Cleaned up expired session {session_id}")
    
    async def broadcast_notification(self, method: str, params: Optional[Dict[str, Any]] = None):
        """
        Broadcast notification to all active sessions
        
        Args:
            method: Notification method name
            params: Notification parameters
        """
        async with self._lock:
            active_sessions = [
                session for session in self.sessions.values()
                if session.state == SessionState.INITIALIZED
            ]
        
        logger.debug(f"Broadcasting {method} to {len(active_sessions)} sessions")
        # Note: Actual notification sending would be handled by transport layer