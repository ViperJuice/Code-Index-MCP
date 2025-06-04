"""
Abstract base transport interface.

Defines the common interface that all transport implementations must follow,
including connection state management, error handling, and transport metadata.
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional, Dict, Any, Callable, List, TypeVar, Generic
from enum import Enum, auto
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
import logging
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

T = TypeVar('T')


class TransportState(Enum):
    """Common transport connection states."""
    INITIALIZING = "initializing"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    CLOSED = "closed"


class TransportError(Exception):
    """Base exception for transport-related errors."""
    pass


class ConnectionError(TransportError):
    """Raised when connection-related errors occur."""
    pass


class MessageError(TransportError):
    """Raised when message handling errors occur."""
    pass


class TransportClosedError(TransportError):
    """Raised when operations are attempted on a closed transport."""
    pass


@dataclass
class TransportMetadata:
    """Metadata about a transport connection."""
    transport_type: str
    transport_id: str
    created_at: datetime = field(default_factory=datetime.now)
    connected_at: Optional[datetime] = None
    disconnected_at: Optional[datetime] = None
    last_activity: datetime = field(default_factory=datetime.now)
    remote_address: Optional[str] = None
    local_address: Optional[str] = None
    protocol_version: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)
    
    def update_activity(self) -> None:
        """Update the last activity timestamp."""
        self.last_activity = datetime.now()
        
    def mark_connected(self) -> None:
        """Mark the transport as connected."""
        self.connected_at = datetime.now()
        self.update_activity()
        
    def mark_disconnected(self) -> None:
        """Mark the transport as disconnected."""
        self.disconnected_at = datetime.now()
        self.update_activity()


@dataclass
class TransportStatistics:
    """Statistics for transport operations."""
    messages_sent: int = 0
    messages_received: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    errors_count: int = 0
    reconnect_count: int = 0
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None
    
    def record_sent(self, message_size: int) -> None:
        """Record a sent message."""
        self.messages_sent += 1
        self.bytes_sent += message_size
        
    def record_received(self, message_size: int) -> None:
        """Record a received message."""
        self.messages_received += 1
        self.bytes_received += message_size
        
    def record_error(self, error_msg: str) -> None:
        """Record an error."""
        self.errors_count += 1
        self.last_error = error_msg
        self.last_error_time = datetime.now()
        
    def record_reconnect(self) -> None:
        """Record a reconnection attempt."""
        self.reconnect_count += 1


class TransportEventType(Enum):
    """Types of transport events."""
    CONNECTING = auto()
    CONNECTED = auto()
    DISCONNECTING = auto()
    DISCONNECTED = auto()
    MESSAGE_SENT = auto()
    MESSAGE_RECEIVED = auto()
    ERROR = auto()
    RECONNECTING = auto()
    STATE_CHANGED = auto()


@dataclass
class TransportEvent:
    """Event emitted by transport operations."""
    event_type: TransportEventType
    transport_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    data: Optional[Dict[str, Any]] = None
    error: Optional[Exception] = None


# Type alias for event callbacks
EventCallback = Callable[[TransportEvent], asyncio.Future[None]]


class Transport(ABC, Generic[T]):
    """
    Abstract base class for MCP transports.
    
    This class defines the interface that all transport implementations must follow,
    including connection management, message handling, state tracking, and statistics.
    """
    
    def __init__(self, transport_id: Optional[str] = None):
        """
        Initialize the transport.
        
        Args:
            transport_id: Optional unique identifier for this transport instance
        """
        from uuid import uuid4
        self._transport_id = transport_id or str(uuid4())
        self._state = TransportState.INITIALIZING
        self._metadata = TransportMetadata(
            transport_type=self.__class__.__name__,
            transport_id=self._transport_id
        )
        self._statistics = TransportStatistics()
        self._event_callbacks: List[EventCallback] = []
        self._state_lock = asyncio.Lock()
        self._closed = False
        
    @property
    def transport_id(self) -> str:
        """Get the unique transport identifier."""
        return self._transport_id
        
    @property
    def state(self) -> TransportState:
        """Get the current transport state."""
        return self._state
        
    @property
    def metadata(self) -> TransportMetadata:
        """Get transport metadata."""
        return self._metadata
        
    @property
    def statistics(self) -> TransportStatistics:
        """Get transport statistics."""
        return self._statistics
        
    @property
    def is_connected(self) -> bool:
        """Check if transport is currently connected."""
        return self._state == TransportState.CONNECTED
        
    @property
    def is_closed(self) -> bool:
        """Check if transport has been closed."""
        return self._closed
        
    async def _set_state(self, new_state: TransportState) -> None:
        """
        Set the transport state with proper locking.
        
        Args:
            new_state: The new transport state
        """
        async with self._state_lock:
            old_state = self._state
            self._state = new_state
            logger.debug(f"Transport {self._transport_id} state changed: {old_state} -> {new_state}")
            
            # Update metadata based on state
            if new_state == TransportState.CONNECTED:
                self._metadata.mark_connected()
            elif new_state in (TransportState.DISCONNECTED, TransportState.CLOSED):
                self._metadata.mark_disconnected()
                
            # Emit state change event
            await self._emit_event(TransportEvent(
                event_type=TransportEventType.STATE_CHANGED,
                transport_id=self._transport_id,
                data={"old_state": old_state.value, "new_state": new_state.value}
            ))
    
    @abstractmethod
    async def connect(self, **kwargs) -> None:
        """
        Establish the transport connection.
        
        Args:
            **kwargs: Transport-specific connection parameters
            
        Raises:
            ConnectionError: If connection cannot be established
        """
        pass
        
    @abstractmethod
    async def disconnect(self) -> None:
        """
        Gracefully disconnect the transport.
        
        This should attempt to close the connection cleanly,
        sending any necessary closing messages.
        """
        pass
        
    @abstractmethod
    async def send(self, message: T) -> None:
        """
        Send a message over the transport.
        
        Args:
            message: The message to send
            
        Raises:
            TransportClosedError: If transport is closed
            MessageError: If message cannot be sent
        """
        pass
        
    @abstractmethod
    async def receive(self) -> AsyncIterator[T]:
        """
        Receive messages from the transport.
        
        Yields:
            Messages received from the transport
            
        Raises:
            TransportClosedError: If transport is closed
            MessageError: If message cannot be received
        """
        pass
        
    async def close(self) -> None:
        """
        Close the transport and clean up resources.
        
        This method ensures proper cleanup of the transport,
        including disconnection and resource deallocation.
        """
        if self._closed:
            return
            
        logger.info(f"Closing transport {self._transport_id}")
        
        try:
            # Disconnect if still connected
            if self.is_connected:
                await self.disconnect()
        except Exception as e:
            logger.error(f"Error during disconnect while closing: {e}")
            
        # Set closed state
        await self._set_state(TransportState.CLOSED)
        self._closed = True
        
        # Clear callbacks to prevent memory leaks
        self._event_callbacks.clear()
        
    @abstractmethod
    async def is_alive(self) -> bool:
        """
        Check if the transport connection is alive.
        
        Returns:
            True if the connection is alive and functional
        """
        pass
        
    async def reconnect(self, **kwargs) -> None:
        """
        Attempt to reconnect the transport.
        
        Args:
            **kwargs: Transport-specific reconnection parameters
            
        Raises:
            ConnectionError: If reconnection fails
        """
        logger.info(f"Attempting to reconnect transport {self._transport_id}")
        await self._set_state(TransportState.RECONNECTING)
        self._statistics.record_reconnect()
        
        try:
            await self.disconnect()
            await self.connect(**kwargs)
        except Exception as e:
            await self._set_state(TransportState.ERROR)
            await self._emit_event(TransportEvent(
                event_type=TransportEventType.ERROR,
                transport_id=self._transport_id,
                error=e
            ))
            raise ConnectionError(f"Reconnection failed: {e}") from e
            
    def add_event_callback(self, callback: EventCallback) -> None:
        """
        Add an event callback.
        
        Args:
            callback: Async function to call on events
        """
        self._event_callbacks.append(callback)
        
    def remove_event_callback(self, callback: EventCallback) -> None:
        """
        Remove an event callback.
        
        Args:
            callback: The callback to remove
        """
        if callback in self._event_callbacks:
            self._event_callbacks.remove(callback)
            
    async def _emit_event(self, event: TransportEvent) -> None:
        """
        Emit an event to all registered callbacks.
        
        Args:
            event: The event to emit
        """
        # Create tasks for all callbacks
        tasks = []
        for callback in self._event_callbacks:
            try:
                task = asyncio.create_task(callback(event))
                tasks.append(task)
            except Exception as e:
                logger.error(f"Error creating task for callback: {e}")
                
        # Wait for all callbacks to complete
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Event callback error: {result}")
                    
    async def wait_for_state(self, state: TransportState, timeout: Optional[float] = None) -> bool:
        """
        Wait for the transport to reach a specific state.
        
        Args:
            state: The state to wait for
            timeout: Optional timeout in seconds
            
        Returns:
            True if state was reached, False if timeout occurred
        """
        try:
            async with asyncio.timeout(timeout):
                while self._state != state and not self._closed:
                    await asyncio.sleep(0.1)
                return self._state == state
        except asyncio.TimeoutError:
            return False
            
    @asynccontextmanager
    async def error_handler(self, operation: str):
        """
        Context manager for handling transport errors.
        
        Args:
            operation: Description of the operation being performed
        """
        try:
            yield
        except Exception as e:
            error_msg = f"Error during {operation}: {e}"
            logger.error(error_msg)
            self._statistics.record_error(error_msg)
            
            if not isinstance(e, TransportError):
                # Wrap non-transport errors
                raise TransportError(error_msg) from e
                
            await self._emit_event(TransportEvent(
                event_type=TransportEventType.ERROR,
                transport_id=self._transport_id,
                error=e,
                data={"operation": operation}
            ))
            
            # Set error state if not already closed
            if not self._closed and self._state != TransportState.ERROR:
                await self._set_state(TransportState.ERROR)
                
            raise
            
    def get_info(self) -> Dict[str, Any]:
        """
        Get comprehensive information about the transport.
        
        Returns:
            Dictionary containing transport information
        """
        return {
            "transport_id": self._transport_id,
            "transport_type": self._metadata.transport_type,
            "state": self._state.value,
            "is_connected": self.is_connected,
            "is_closed": self.is_closed,
            "metadata": {
                "created_at": self._metadata.created_at.isoformat(),
                "connected_at": self._metadata.connected_at.isoformat() if self._metadata.connected_at else None,
                "disconnected_at": self._metadata.disconnected_at.isoformat() if self._metadata.disconnected_at else None,
                "last_activity": self._metadata.last_activity.isoformat(),
                "remote_address": self._metadata.remote_address,
                "local_address": self._metadata.local_address,
                "protocol_version": self._metadata.protocol_version,
                "extra": self._metadata.extra
            },
            "statistics": {
                "messages_sent": self._statistics.messages_sent,
                "messages_received": self._statistics.messages_received,
                "bytes_sent": self._statistics.bytes_sent,
                "bytes_received": self._statistics.bytes_received,
                "errors_count": self._statistics.errors_count,
                "reconnect_count": self._statistics.reconnect_count,
                "last_error": self._statistics.last_error,
                "last_error_time": self._statistics.last_error_time.isoformat() if self._statistics.last_error_time else None
            }
        }


class BufferedTransport(Transport[T]):
    """
    Base class for transports that need message buffering.
    
    Provides common buffering functionality for transports that need to
    queue messages during connection establishment or temporary disconnections.
    """
    
    def __init__(self, transport_id: Optional[str] = None, buffer_size: int = 1000):
        """
        Initialize buffered transport.
        
        Args:
            transport_id: Optional unique identifier
            buffer_size: Maximum number of messages to buffer
        """
        super().__init__(transport_id)
        self._send_buffer: asyncio.Queue[T] = asyncio.Queue(maxsize=buffer_size)
        self._receive_buffer: asyncio.Queue[T] = asyncio.Queue(maxsize=buffer_size)
        self._buffer_size = buffer_size
        
    async def buffered_send(self, message: T) -> None:
        """
        Send a message with buffering support.
        
        If not connected, messages are queued until connection is established.
        
        Args:
            message: The message to send
            
        Raises:
            asyncio.QueueFull: If send buffer is full
        """
        if self.is_connected:
            await self.send(message)
        else:
            await self._send_buffer.put(message)
            
    async def flush_send_buffer(self) -> int:
        """
        Flush all buffered messages.
        
        Returns:
            Number of messages flushed
        """
        count = 0
        while not self._send_buffer.empty():
            try:
                message = self._send_buffer.get_nowait()
                await self.send(message)
                count += 1
            except asyncio.QueueEmpty:
                break
            except Exception as e:
                logger.error(f"Error flushing message: {e}")
                # Put message back if send failed
                try:
                    self._send_buffer.put_nowait(message)
                except asyncio.QueueFull:
                    pass
                raise
                
        return count
        
    def get_buffer_stats(self) -> Dict[str, int]:
        """Get buffer statistics."""
        return {
            "send_buffer_size": self._send_buffer.qsize(),
            "send_buffer_max": self._buffer_size,
            "receive_buffer_size": self._receive_buffer.qsize(),
            "receive_buffer_max": self._buffer_size
        }
