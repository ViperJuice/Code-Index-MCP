"""
Session storage implementation.

Stores active session data and provides retrieval methods.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, Set
from dataclasses import asdict
import aiofiles
from pathlib import Path

from ..interfaces.shared_interfaces import IAsyncRepository
from .models import SessionContext, SessionState, ClientInfo

logger = logging.getLogger(__name__)


class SessionStore(IAsyncRepository[SessionContext]):
    """
    Thread-safe session storage with optional persistence.
    
    Provides in-memory storage with optional file-based persistence
    for session recovery across restarts.
    """
    
    def __init__(
        self,
        persist_sessions: bool = False,
        persistence_path: Optional[Path] = None
    ):
        self.persist_sessions = persist_sessions
        self.persistence_path = persistence_path or Path("./sessions.json")
        
        self._sessions: Dict[str, SessionContext] = {}
        self._lock = asyncio.Lock()
        
        # Load persisted sessions on startup
        if self.persist_sessions:
            asyncio.create_task(self._load_sessions())
    
    async def find(self, id: str) -> Optional[SessionContext]:
        """Find a session by ID."""
        async with self._lock:
            return self._sessions.get(id)
    
    async def find_all(
        self,
        filter_criteria: Optional[Dict[str, Any]] = None
    ) -> List[SessionContext]:
        """Find all sessions matching criteria."""
        async with self._lock:
            sessions = list(self._sessions.values())
            
            if not filter_criteria:
                return sessions
            
            # Apply filters
            filtered = []
            for session in sessions:
                match = True
                
                # Check client info filters
                if "client_name" in filter_criteria:
                    if not session.client_info or session.client_info.name != filter_criteria["client_name"]:
                        match = False
                
                if "client_version" in filter_criteria:
                    if not session.client_info or session.client_info.version != filter_criteria["client_version"]:
                        match = False
                
                # Check capability filters
                if "has_capability" in filter_criteria:
                    capability = filter_criteria["has_capability"]
                    if not session.negotiated_capabilities or capability not in session.negotiated_capabilities:
                        match = False
                
                # Check time-based filters
                if "created_after" in filter_criteria:
                    if session.created_at < filter_criteria["created_after"]:
                        match = False
                
                if "active_after" in filter_criteria:
                    if session.last_activity < filter_criteria["active_after"]:
                        match = False
                
                if match:
                    filtered.append(session)
            
            return filtered
    
    async def save(self, entity: SessionContext) -> SessionContext:
        """Save a session context."""
        async with self._lock:
            self._sessions[entity.session_id] = entity
            
            if self.persist_sessions:
                await self._persist_sessions()
            
            return entity
    
    async def delete(self, id: str) -> bool:
        """Delete a session by ID."""
        async with self._lock:
            if id in self._sessions:
                del self._sessions[id]
                
                if self.persist_sessions:
                    await self._persist_sessions()
                
                return True
            return False
    
    async def exists(self, id: str) -> bool:
        """Check if a session exists."""
        async with self._lock:
            return id in self._sessions
    
    # Additional convenience methods
    
    async def save_session(self, session_id: str, context: SessionContext) -> None:
        """Save a session context (alias for save)."""
        await self.save(context)
    
    async def get_session(self, session_id: str) -> Optional[SessionContext]:
        """Get a session context (alias for find)."""
        return await self.find(session_id)
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete a session (alias for delete)."""
        return await self.delete(session_id)
    
    async def list_sessions(
        self,
        client_name: Optional[str] = None,
        active_only: bool = False
    ) -> List[SessionContext]:
        """List sessions with common filters."""
        criteria = {}
        
        if client_name:
            criteria["client_name"] = client_name
        
        if active_only:
            # Consider sessions active if accessed in the last hour
            from datetime import timedelta
            criteria["active_after"] = datetime.utcnow() - timedelta(hours=1)
        
        return await self.find_all(criteria)
    
    async def count_sessions(
        self,
        client_name: Optional[str] = None
    ) -> int:
        """Count sessions with optional client filter."""
        sessions = await self.list_sessions(client_name=client_name)
        return len(sessions)
    
    async def get_client_sessions(self, client_name: str) -> List[SessionContext]:
        """Get all sessions for a specific client."""
        return await self.find_all({"client_name": client_name})
    
    async def cleanup_old_sessions(self, max_age_hours: int = 24) -> int:
        """Clean up sessions older than specified hours."""
        from datetime import timedelta
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        
        sessions = await self.find_all()
        count = 0
        
        for session in sessions:
            if session.last_activity < cutoff_time:
                if await self.delete(session.session_id):
                    count += 1
        
        logger.info(f"Cleaned up {count} old sessions")
        return count
    
    # Persistence methods
    
    async def _persist_sessions(self) -> None:
        """Persist sessions to disk."""
        if not self.persist_sessions:
            return
        
        try:
            # Convert sessions to serializable format
            data = {
                "sessions": [
                    self._session_to_dict(session)
                    for session in self._sessions.values()
                ],
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Write to temporary file first
            temp_path = self.persistence_path.with_suffix(".tmp")
            async with aiofiles.open(temp_path, "w") as f:
                await f.write(json.dumps(data, indent=2))
            
            # Atomic rename
            temp_path.replace(self.persistence_path)
            
        except Exception as e:
            logger.error(f"Failed to persist sessions: {e}")
    
    async def _load_sessions(self) -> None:
        """Load persisted sessions from disk."""
        if not self.persistence_path.exists():
            return
        
        try:
            async with aiofiles.open(self.persistence_path, "r") as f:
                data = json.loads(await f.read())
            
            async with self._lock:
                for session_data in data.get("sessions", []):
                    try:
                        session = self._dict_to_session(session_data)
                        self._sessions[session.session_id] = session
                    except Exception as e:
                        logger.error(f"Failed to load session: {e}")
            
            logger.info(f"Loaded {len(self._sessions)} persisted sessions")
            
        except Exception as e:
            logger.error(f"Failed to load persisted sessions: {e}")
    
    def _session_to_dict(self, session: SessionContext) -> Dict[str, Any]:
        """Convert session context to dictionary for serialization."""
        data = {
            "session_id": session.session_id,
            "created_at": session.created_at.isoformat(),
            "last_activity": session.last_activity.isoformat(),
            "metadata": session.metadata
        }
        
        if session.client_info:
            data["client_info"] = asdict(session.client_info)
        
        if session.client_capabilities:
            data["client_capabilities"] = asdict(session.client_capabilities)
        
        if session.server_capabilities:
            data["server_capabilities"] = asdict(session.server_capabilities)
        
        if session.negotiated_capabilities:
            data["negotiated_capabilities"] = session.negotiated_capabilities
        
        return data
    
    def _dict_to_session(self, data: Dict[str, Any]) -> SessionContext:
        """Convert dictionary to session context."""
        session = SessionContext(
            session_id=data["session_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            last_activity=datetime.fromisoformat(data["last_activity"]),
            metadata=data.get("metadata", {})
        )
        
        if "client_info" in data:
            session.client_info = ClientInfo(**data["client_info"])
        
        # Note: We don't restore full capabilities as they may have changed
        # Sessions will need to re-negotiate capabilities on reconnect
        
        return session
