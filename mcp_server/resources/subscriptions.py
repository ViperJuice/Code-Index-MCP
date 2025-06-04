"""
Resource subscription management for MCP.

Handles resource change notifications and subscriptions with real-time updates,
batching, filtering, and session management.
"""

import asyncio
import logging
import time
import weakref
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import (
    Any, AsyncIterator, Callable, Dict, List, Optional, Set, 
    Union, Protocol, Awaitable
)
from uuid import uuid4

from ..interfaces.mcp_interfaces import IMCPResource
from ..interfaces.shared_interfaces import Result, Error

logger = logging.getLogger(__name__)


class NotificationType(Enum):
    """Types of notifications that can be sent."""
    FILE_CREATED = "file_created"
    FILE_MODIFIED = "file_modified" 
    FILE_DELETED = "file_deleted"
    FILE_MOVED = "file_moved"
    SYMBOL_ADDED = "symbol_added"
    SYMBOL_UPDATED = "symbol_updated"
    SYMBOL_REMOVED = "symbol_removed"
    SEARCH_RESULTS_UPDATED = "search_results_updated"
    INDEX_UPDATED = "index_updated"
    PROJECT_STRUCTURE_CHANGED = "project_structure_changed"


class SubscriptionScope(Enum):
    """Scope of subscriptions."""
    FILE = "file"           # Subscribe to specific file changes
    DIRECTORY = "directory" # Subscribe to directory tree changes
    PROJECT = "project"     # Subscribe to entire project changes
    SYMBOL = "symbol"       # Subscribe to symbol changes
    SEARCH = "search"       # Subscribe to search result changes
    GLOBAL = "global"       # Subscribe to all changes


@dataclass
class NotificationFilter:
    """Filter criteria for notifications."""
    file_patterns: Optional[List[str]] = None      # Glob patterns for files
    file_extensions: Optional[Set[str]] = None     # File extensions
    languages: Optional[Set[str]] = None           # Programming languages
    notification_types: Optional[Set[NotificationType]] = None
    symbol_types: Optional[Set[str]] = None        # function, class, etc.
    min_severity: Optional[str] = None             # Minimum severity level
    exclude_patterns: Optional[List[str]] = None   # Patterns to exclude
    include_metadata: bool = True                  # Include metadata in notifications


@dataclass
class NotificationEvent:
    """A notification event to be sent to subscribers."""
    id: str
    type: NotificationType
    resource_uri: str
    timestamp: datetime
    data: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None
    source: Optional[str] = None  # Source component that generated the event


@dataclass
class Subscription:
    """A resource subscription."""
    id: str
    session_id: str
    scope: SubscriptionScope
    resource_uri: str  # URI pattern or specific resource
    filter: Optional[NotificationFilter] = None
    callback: Optional[Callable[[NotificationEvent], Awaitable[None]]] = None
    created_at: datetime = field(default_factory=datetime.now)
    last_notification: Optional[datetime] = None
    notification_count: int = 0
    active: bool = True


class SubscriptionSession:
    """Manages subscriptions for a client session."""
    
    def __init__(self, session_id: str, max_subscriptions: int = 100):
        self.session_id = session_id
        self.subscriptions: Dict[str, Subscription] = {}
        self.max_subscriptions = max_subscriptions
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.notification_queue: deque = deque(maxlen=1000)
        self._cleanup_task: Optional[asyncio.Task] = None
    
    def add_subscription(self, subscription: Subscription) -> bool:
        """Add a subscription to this session."""
        if len(self.subscriptions) >= self.max_subscriptions:
            return False
        
        self.subscriptions[subscription.id] = subscription
        self.last_activity = datetime.now()
        return True
    
    def remove_subscription(self, subscription_id: str) -> bool:
        """Remove a subscription from this session."""
        if subscription_id in self.subscriptions:
            self.subscriptions[subscription_id].active = False
            del self.subscriptions[subscription_id]
            self.last_activity = datetime.now()
            return True
        return False
    
    def get_active_subscriptions(self) -> List[Subscription]:
        """Get all active subscriptions for this session."""
        return [sub for sub in self.subscriptions.values() if sub.active]


class NotificationBatcher:
    """Batches notifications for efficient delivery."""
    
    def __init__(self, batch_size: int = 10, batch_timeout: float = 1.0):
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.pending_notifications: Dict[str, List[NotificationEvent]] = defaultdict(list)
        self.batch_timers: Dict[str, asyncio.Task] = {}
        self.delivery_callback: Optional[Callable[[str, List[NotificationEvent]], Awaitable[None]]] = None
    
    async def add_notification(self, session_id: str, event: NotificationEvent):
        """Add a notification to the batch for a session."""
        self.pending_notifications[session_id].append(event)
        
        # If batch is full, deliver immediately
        if len(self.pending_notifications[session_id]) >= self.batch_size:
            await self._deliver_batch(session_id)
        else:
            # Start or reset timer for this session
            await self._schedule_batch_delivery(session_id)
    
    async def _schedule_batch_delivery(self, session_id: str):
        """Schedule batch delivery for a session."""
        # Cancel existing timer
        if session_id in self.batch_timers:
            self.batch_timers[session_id].cancel()
        
        # Schedule new delivery
        self.batch_timers[session_id] = asyncio.create_task(
            self._delayed_delivery(session_id)
        )
    
    async def _delayed_delivery(self, session_id: str):
        """Deliver batch after timeout."""
        try:
            await asyncio.sleep(self.batch_timeout)
            await self._deliver_batch(session_id)
        except asyncio.CancelledError:
            pass
    
    async def _deliver_batch(self, session_id: str):
        """Deliver batched notifications for a session."""
        if session_id in self.pending_notifications and self.pending_notifications[session_id]:
            notifications = self.pending_notifications[session_id].copy()
            self.pending_notifications[session_id].clear()
            
            # Remove timer
            if session_id in self.batch_timers:
                self.batch_timers[session_id].cancel()
                del self.batch_timers[session_id]
            
            # Deliver notifications
            if self.delivery_callback:
                try:
                    await self.delivery_callback(session_id, notifications)
                except Exception as e:
                    logger.error(f"Error delivering batch to session {session_id}: {e}")
    
    async def flush_all(self):
        """Flush all pending notifications immediately."""
        for session_id in list(self.pending_notifications.keys()):
            await self._deliver_batch(session_id)


class SubscriptionManager:
    """
    Central manager for resource subscriptions.
    
    Handles subscription lifecycle, notification routing, batching,
    and integration with file watchers and other components.
    """
    
    def __init__(self, 
                 batch_size: int = 10,
                 batch_timeout: float = 1.0,
                 session_timeout: timedelta = timedelta(hours=24),
                 max_sessions: int = 1000):
        """
        Initialize the subscription manager.
        
        Args:
            batch_size: Number of notifications to batch before delivery
            batch_timeout: Time to wait before delivering partial batches
            session_timeout: Time before inactive sessions are cleaned up
            max_sessions: Maximum number of concurrent sessions
        """
        self.sessions: Dict[str, SubscriptionSession] = {}
        self.max_sessions = max_sessions
        self.session_timeout = session_timeout
        
        # Notification batching
        self.batcher = NotificationBatcher(batch_size, batch_timeout)
        self.batcher.delivery_callback = self._deliver_notifications
        
        # Event routing
        self.subscription_index: Dict[SubscriptionScope, Set[str]] = defaultdict(set)
        self.uri_subscriptions: Dict[str, Set[str]] = defaultdict(set)  # URI -> subscription IDs
        
        # Performance tracking
        self.stats = {
            "total_subscriptions": 0,
            "active_sessions": 0,
            "notifications_sent": 0,
            "notifications_batched": 0,
            "subscription_matches": 0
        }
        
        # Cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start(self):
        """Start the subscription manager."""
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Subscription manager started")
    
    async def stop(self):
        """Stop the subscription manager."""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
        
        # Flush pending notifications
        await self.batcher.flush_all()
        
        # Clean up sessions
        for session in self.sessions.values():
            if session._cleanup_task:
                session._cleanup_task.cancel()
        
        logger.info("Subscription manager stopped")
    
    def create_session(self, session_id: Optional[str] = None) -> str:
        """Create a new subscription session."""
        if session_id is None:
            session_id = str(uuid4())
        
        if len(self.sessions) >= self.max_sessions:
            # Remove oldest inactive session
            self._cleanup_oldest_session()
        
        session = SubscriptionSession(session_id)
        self.sessions[session_id] = session
        self.stats["active_sessions"] = len(self.sessions)
        
        logger.debug(f"Created subscription session: {session_id}")
        return session_id
    
    def _cleanup_oldest_session(self):
        """Remove the oldest inactive session."""
        if not self.sessions:
            return
        
        oldest_session = min(
            self.sessions.values(),
            key=lambda s: s.last_activity
        )
        self.remove_session(oldest_session.session_id)
    
    def remove_session(self, session_id: str) -> bool:
        """Remove a subscription session and all its subscriptions."""
        if session_id not in self.sessions:
            return False
        
        session = self.sessions[session_id]
        
        # Remove all subscriptions for this session
        for subscription_id in list(session.subscriptions.keys()):
            self._remove_subscription_internal(subscription_id, session_id)
        
        # Cancel cleanup task
        if session._cleanup_task:
            session._cleanup_task.cancel()
        
        del self.sessions[session_id]
        self.stats["active_sessions"] = len(self.sessions)
        
        logger.debug(f"Removed subscription session: {session_id}")
        return True
    
    async def subscribe(self,
                       session_id: str,
                       scope: SubscriptionScope,
                       resource_uri: str,
                       notification_filter: Optional[NotificationFilter] = None,
                       callback: Optional[Callable[[NotificationEvent], Awaitable[None]]] = None) -> Result[str]:
        """
        Create a new subscription.
        
        Args:
            session_id: Session identifier
            scope: Subscription scope
            resource_uri: URI or pattern to subscribe to
            notification_filter: Optional filter for notifications
            callback: Optional callback for notifications
        
        Returns:
            Result containing subscription ID or error
        """
        try:
            # Get or create session
            if session_id not in self.sessions:
                session_id = self.create_session(session_id)
            
            session = self.sessions[session_id]
            
            # Create subscription
            subscription_id = str(uuid4())
            subscription = Subscription(
                id=subscription_id,
                session_id=session_id,
                scope=scope,
                resource_uri=resource_uri,
                filter=notification_filter,
                callback=callback
            )
            
            # Add to session
            if not session.add_subscription(subscription):
                return Result.error_result(Error("SUBSCRIPTION_FAILED", "Failed to add subscription to session", {}, datetime.now()))
            
            # Update indices
            self.subscription_index[scope].add(subscription_id)
            self.uri_subscriptions[resource_uri].add(subscription_id)
            
            self.stats["total_subscriptions"] += 1
            
            logger.debug(f"Created subscription {subscription_id} for session {session_id}")
            return Result.success_result(subscription_id)
            
        except Exception as e:
            logger.error(f"Error creating subscription: {e}")
            return Result.error_result(Error("SUBSCRIPTION_ERROR", str(e), {}, datetime.now()))
    
    async def unsubscribe(self, session_id: str, subscription_id: str) -> Result[bool]:
        """Remove a subscription."""
        try:
            if session_id not in self.sessions:
                return Result.error_result(Error("SESSION_NOT_FOUND", f"Session {session_id} not found", {}, datetime.now()))
            
            session = self.sessions[session_id]
            if subscription_id not in session.subscriptions:
                return Result.error_result(Error("SUBSCRIPTION_NOT_FOUND", f"Subscription {subscription_id} not found", {}, datetime.now()))
            
            success = self._remove_subscription_internal(subscription_id, session_id)
            return Result.success_result(success)
            
        except Exception as e:
            logger.error(f"Error removing subscription: {e}")
            return Result.error_result(Error("UNSUBSCRIBE_ERROR", str(e), {}, datetime.now()))
    
    def _remove_subscription_internal(self, subscription_id: str, session_id: str) -> bool:
        """Internal method to remove subscription from indices."""
        session = self.sessions.get(session_id)
        if not session or subscription_id not in session.subscriptions:
            return False
        
        subscription = session.subscriptions[subscription_id]
        
        # Remove from indices
        self.subscription_index[subscription.scope].discard(subscription_id)
        self.uri_subscriptions[subscription.resource_uri].discard(subscription_id)
        
        # Remove from session
        session.remove_subscription(subscription_id)
        
        logger.debug(f"Removed subscription {subscription_id} from session {session_id}")
        return True
    
    async def notify(self, 
                    event_type: NotificationType,
                    resource_uri: str,
                    data: Dict[str, Any],
                    metadata: Optional[Dict[str, Any]] = None,
                    source: Optional[str] = None):
        """
        Send a notification to relevant subscribers.
        
        Args:
            event_type: Type of notification
            resource_uri: URI of the changed resource
            data: Event data
            metadata: Optional metadata
            source: Source component that generated the event
        """
        try:
            # Create notification event
            event = NotificationEvent(
                id=str(uuid4()),
                type=event_type,
                resource_uri=resource_uri,
                timestamp=datetime.now(),
                data=data,
                metadata=metadata,
                source=source
            )
            
            # Find matching subscriptions
            matching_subscriptions = await self._find_matching_subscriptions(event)
            
            # Send notifications to matching subscriptions
            for subscription in matching_subscriptions:
                session = self.sessions.get(subscription.session_id)
                if session and subscription.active:
                    # Apply filtering
                    if self._should_notify(subscription, event):
                        # Update subscription stats
                        subscription.last_notification = datetime.now()
                        subscription.notification_count += 1
                        
                        # Add to batch for delivery
                        await self.batcher.add_notification(subscription.session_id, event)
                        
                        # Call callback if present
                        if subscription.callback:
                            try:
                                await subscription.callback(event)
                            except Exception as e:
                                logger.error(f"Error in subscription callback: {e}")
            
            self.stats["subscription_matches"] += len(matching_subscriptions)
            
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
    
    async def _find_matching_subscriptions(self, event: NotificationEvent) -> List[Subscription]:
        """Find subscriptions that match the given event."""
        matching = []
        
        # Direct URI matches
        for subscription_id in self.uri_subscriptions.get(event.resource_uri, set()):
            subscription = self._get_subscription_by_id(subscription_id)
            if subscription:
                matching.append(subscription)
        
        # Pattern matches for different scopes
        for scope in SubscriptionScope:
            for subscription_id in self.subscription_index.get(scope, set()):
                subscription = self._get_subscription_by_id(subscription_id)
                if subscription and self._uri_matches_pattern(event.resource_uri, subscription.resource_uri, scope):
                    matching.append(subscription)
        
        return matching
    
    def _get_subscription_by_id(self, subscription_id: str) -> Optional[Subscription]:
        """Get subscription by ID across all sessions."""
        for session in self.sessions.values():
            if subscription_id in session.subscriptions:
                return session.subscriptions[subscription_id]
        return None
    
    def _uri_matches_pattern(self, uri: str, pattern: str, scope: SubscriptionScope) -> bool:
        """Check if URI matches the subscription pattern for the given scope."""
        import fnmatch
        
        if scope == SubscriptionScope.GLOBAL:
            return True
        elif scope == SubscriptionScope.PROJECT:
            # Match if URI is within the project
            return uri.startswith(pattern) or pattern.startswith(uri)
        elif scope == SubscriptionScope.DIRECTORY:
            # Match if URI is within the directory tree
            path_uri = Path(uri)
            pattern_path = Path(pattern)
            try:
                path_uri.relative_to(pattern_path)
                return True
            except ValueError:
                return False
        elif scope == SubscriptionScope.FILE:
            # Exact match or pattern match
            return uri == pattern or fnmatch.fnmatch(uri, pattern)
        elif scope == SubscriptionScope.SYMBOL:
            # Symbol-specific matching (could be enhanced)
            return fnmatch.fnmatch(uri, pattern)
        elif scope == SubscriptionScope.SEARCH:
            # Search result matching
            return fnmatch.fnmatch(uri, pattern)
        
        return False
    
    def _should_notify(self, subscription: Subscription, event: NotificationEvent) -> bool:
        """Check if subscription should receive the notification based on filters."""
        if not subscription.filter:
            return True
        
        filter_obj = subscription.filter
        
        # Check notification type filter
        if (filter_obj.notification_types and 
            event.type not in filter_obj.notification_types):
            return False
        
        # Check file extension filter
        if filter_obj.file_extensions:
            path = Path(event.resource_uri)
            if path.suffix.lstrip(".") not in filter_obj.file_extensions:
                return False
        
        # Check file pattern filter
        if filter_obj.file_patterns:
            import fnmatch
            path_str = str(event.resource_uri)
            if not any(fnmatch.fnmatch(path_str, pattern) for pattern in filter_obj.file_patterns):
                return False
        
        # Check exclusion patterns
        if filter_obj.exclude_patterns:
            import fnmatch
            path_str = str(event.resource_uri)
            if any(fnmatch.fnmatch(path_str, pattern) for pattern in filter_obj.exclude_patterns):
                return False
        
        # Check language filter
        if filter_obj.languages and event.metadata:
            event_language = event.metadata.get("language")
            if event_language and event_language not in filter_obj.languages:
                return False
        
        return True
    
    async def _deliver_notifications(self, session_id: str, notifications: List[NotificationEvent]):
        """Deliver batched notifications to a session."""
        session = self.sessions.get(session_id)
        if not session:
            logger.warning(f"Session {session_id} not found for notification delivery")
            return
        
        # Add to session queue
        for notification in notifications:
            session.notification_queue.append(notification)
        
        session.last_activity = datetime.now()
        self.stats["notifications_sent"] += len(notifications)
        self.stats["notifications_batched"] += 1
        
        logger.debug(f"Delivered {len(notifications)} notifications to session {session_id}")
    
    async def get_session_notifications(self, session_id: str, limit: int = 100) -> Result[List[NotificationEvent]]:
        """Get pending notifications for a session."""
        try:
            session = self.sessions.get(session_id)
            if not session:
                return Result.error_result(Error("SESSION_NOT_FOUND", f"Session {session_id} not found", {}, datetime.now()))
            
            # Get notifications from queue
            notifications = []
            while session.notification_queue and len(notifications) < limit:
                notifications.append(session.notification_queue.popleft())
            
            session.last_activity = datetime.now()
            return Result.success_result(notifications)
            
        except Exception as e:
            logger.error(f"Error getting session notifications: {e}")
            return Result.error_result(Error("NOTIFICATION_ERROR", str(e), {}, datetime.now()))
    
    def get_subscription_stats(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Get subscription statistics."""
        stats = self.stats.copy()
        
        if session_id:
            session = self.sessions.get(session_id)
            if session:
                stats.update({
                    "session_subscriptions": len(session.subscriptions),
                    "session_notifications": len(session.notification_queue),
                    "session_created": session.created_at.isoformat(),
                    "session_last_activity": session.last_activity.isoformat()
                })
        
        return stats
    
    def list_subscriptions(self, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List subscriptions for a session or all sessions."""
        subscriptions = []
        
        sessions_to_check = [self.sessions[session_id]] if session_id and session_id in self.sessions else self.sessions.values()
        
        for session in sessions_to_check:
            for subscription in session.subscriptions.values():
                subscriptions.append({
                    "id": subscription.id,
                    "session_id": subscription.session_id,
                    "scope": subscription.scope.value,
                    "resource_uri": subscription.resource_uri,
                    "created_at": subscription.created_at.isoformat(),
                    "last_notification": subscription.last_notification.isoformat() if subscription.last_notification else None,
                    "notification_count": subscription.notification_count,
                    "active": subscription.active
                })
        
        return subscriptions
    
    async def _cleanup_loop(self):
        """Background cleanup task for expired sessions."""
        while self._running:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                await self._cleanup_expired_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
    
    async def _cleanup_expired_sessions(self):
        """Remove expired sessions."""
        now = datetime.now()
        expired_sessions = []
        
        for session_id, session in self.sessions.items():
            if now - session.last_activity > self.session_timeout:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            self.remove_session(session_id)
            logger.info(f"Cleaned up expired session: {session_id}")


class FileWatcherIntegration:
    """Integration bridge between file watcher and subscription manager."""
    
    def __init__(self, subscription_manager: SubscriptionManager):
        self.subscription_manager = subscription_manager
    
    async def on_file_created(self, path: Path, metadata: Optional[Dict[str, Any]] = None):
        """Handle file creation events."""
        await self.subscription_manager.notify(
            NotificationType.FILE_CREATED,
            str(path),
            {"path": str(path)},
            metadata,
            "file_watcher"
        )
    
    async def on_file_modified(self, path: Path, metadata: Optional[Dict[str, Any]] = None):
        """Handle file modification events."""
        await self.subscription_manager.notify(
            NotificationType.FILE_MODIFIED,
            str(path),
            {"path": str(path)},
            metadata,
            "file_watcher"
        )
    
    async def on_file_deleted(self, path: Path, metadata: Optional[Dict[str, Any]] = None):
        """Handle file deletion events."""
        await self.subscription_manager.notify(
            NotificationType.FILE_DELETED,
            str(path),
            {"path": str(path)},
            metadata,
            "file_watcher"
        )
    
    async def on_file_moved(self, old_path: Path, new_path: Path, metadata: Optional[Dict[str, Any]] = None):
        """Handle file move events."""
        await self.subscription_manager.notify(
            NotificationType.FILE_MOVED,
            str(new_path),
            {"old_path": str(old_path), "new_path": str(new_path)},
            metadata,
            "file_watcher"
        )


# Factory function for easy integration
def create_subscription_manager(**kwargs) -> SubscriptionManager:
    """Create and configure a subscription manager."""
    return SubscriptionManager(**kwargs)
