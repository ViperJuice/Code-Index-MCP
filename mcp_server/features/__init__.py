"""
Feature integration modules for MCP server.

Each module provides integration logic for optional features.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..stdio_server import StdioMCPServer

# Import integration functions
from .cache_integration import setup_cache
from .health_integration import setup_health_monitoring
from .metrics_integration import setup_metrics
from .rate_limit_integration import setup_rate_limiter
from .memory_integration import setup_memory_monitor
from .graceful_shutdown import setup_graceful_shutdown

__all__ = [
    'setup_cache',
    'setup_health_monitoring',
    'setup_metrics',
    'setup_rate_limiter',
    'setup_memory_monitor',
    'setup_graceful_shutdown',
    'setup_websocket',  # TODO: Implement
    'setup_batch_handler',  # TODO: Implement
    'setup_watcher',  # TODO: Implement
    'setup_middleware',  # TODO: Implement
]