"""
Transport layer implementations for MCP.

This module provides various transport mechanisms for MCP communication:
- WebSocket transport for real-time bidirectional communication
- Standard I/O transport for subprocess-based usage
- Base transport interface for custom implementations
"""

from .base import Transport
from .stdio import (
    StdioTransport,
    StdioSubprocessTransport,
    ProcessState,
    ProcessInfo,
    stdio_context
)

# WebSocket transport is optional - requires aiohttp
try:
    from .websocket import (
        WebSocketTransport,
        WebSocketServer,
        WebSocketClient,
        ConnectionState,
        ConnectionInfo
    )
    _WEBSOCKET_AVAILABLE = True
except ImportError:
    _WEBSOCKET_AVAILABLE = False
    WebSocketTransport = None
    WebSocketServer = None
    WebSocketClient = None
    ConnectionState = None
    ConnectionInfo = None

__all__ = [
    "Transport",
    "StdioTransport",
    "StdioSubprocessTransport",
    "ProcessState",
    "ProcessInfo",
    "stdio_context"
]

if _WEBSOCKET_AVAILABLE:
    __all__.extend([
        "WebSocketTransport",
        "WebSocketServer",
        "WebSocketClient",
        "ConnectionState",
        "ConnectionInfo"
    ])