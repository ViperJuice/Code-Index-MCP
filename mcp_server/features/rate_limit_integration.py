"""
Rate limiting integration for MCP server.

Provides request rate limiting per client and operation type.
"""
import logging
import time
import asyncio
import os
from typing import TYPE_CHECKING, Optional, Dict, Any, Tuple, Set, Callable
from collections import defaultdict, deque
from datetime import datetime, timedelta

from ..performance.rate_limiter import RateLimiter, RateLimiterConfig, RateLimitAlgorithm
from ..utils.feature_flags import feature_manager

if TYPE_CHECKING:
    from ..stdio_server import StdioMCPServer

logger = logging.getLogger(__name__)


class RateLimitIntegration:
    """Integrates rate limiting into MCP server."""
    
    def __init__(self, server: 'StdioMCPServer'):
        self.server = server
        self.enabled = False
        self.requests_limit = 100
        self.window_seconds = 60
        
        # Rate limiters for different operations
        self.rate_limiters: Dict[str, RateLimiter] = {}
        
        # Track requests per client/operation for legacy compatibility
        self.request_history = defaultdict(lambda: deque())
        self.blocked_until = {}
    
    async def setup(self) -> None:
        """Set up rate limiting if enabled."""
        if not feature_manager.is_enabled('rate_limit'):
            return
        
        try:
            # Get rate limit configuration
            config = feature_manager.get_config('rate_limit')
            self.requests_limit = config.get('requests', 100)
            self.window_seconds = config.get('window', 60)
            
            # Configure default rate limiter
            default_config = RateLimiterConfig(
                algorithm=RateLimitAlgorithm.TOKEN_BUCKET,
                max_requests=self.requests_limit,
                window_seconds=self.window_seconds,
                burst_limit=int(self.requests_limit * 1.5)  # Allow 50% burst
            )
            self.rate_limiters["default"] = RateLimiter(default_config)
            
            # More restrictive for expensive operations
            expensive_config = RateLimiterConfig(
                algorithm=RateLimitAlgorithm.TOKEN_BUCKET,
                max_requests=10,
                window_seconds=60,
                burst_limit=15
            )
            self.rate_limiters["index_file"] = RateLimiter(expensive_config)
            
            search_config = RateLimiterConfig(
                algorithm=RateLimitAlgorithm.TOKEN_BUCKET,
                max_requests=50,
                window_seconds=60,
                burst_limit=75
            )
            self.rate_limiters["search_code"] = RateLimiter(search_config)
            
            # Start rate limiters
            for limiter in self.rate_limiters.values():
                await limiter.start()
            
            self.enabled = True
            logger.info(f"Rate limiting enabled ({self.requests_limit} requests per {self.window_seconds}s)")
            
        except Exception as e:
            logger.error(f"Failed to initialize rate limiting: {e}")
            self.enabled = False
    
    async def check_rate_limit(self, client_id: str, operation: str) -> Tuple[bool, Optional[str]]:
        """
        Check if request is within rate limits.
        
        Returns:
            Tuple of (allowed, error_message)
        """
        if not self.enabled:
            return True, None
        
        try:
            # Check if client is blocked
            if client_id in self.blocked_until:
                if datetime.now() < self.blocked_until[client_id]:
                    remaining = (self.blocked_until[client_id] - datetime.now()).seconds
                    return False, f"Rate limit exceeded. Blocked for {remaining} seconds."
                else:
                    del self.blocked_until[client_id]
            
            # Get appropriate rate limiter
            limiter_name = operation if operation in self.rate_limiters else "default"
            limiter = self.rate_limiters[limiter_name]
            
            # Check rate limit
            result = await limiter.check_limit(client_id)
            
            if not result.allowed:
                # Block client for retry_after seconds or 60 seconds default
                block_duration = result.retry_after or 60
                self.blocked_until[client_id] = datetime.now() + timedelta(seconds=block_duration)
                return False, f"Rate limit exceeded for {operation}. Try again in {block_duration} seconds."
            
            # Track request for legacy compatibility
            self._track_request(client_id, operation)
            
            return True, None
            
        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            # On error, allow request but log
            return True, None
    
    def _track_request(self, client_id: str, operation: str) -> None:
        """Track request for statistics."""
        key = f"{client_id}:{operation}"
        now = time.time()
        
        # Clean old entries
        history = self.request_history[key]
        cutoff = now - self.window_seconds
        while history and history[0] < cutoff:
            history.popleft()
        
        # Add new entry
        history.append(now)
    
    def wrap_handler_with_rate_limit(self, handler, operation: str):
        """Wrap a handler with rate limiting."""
        async def rate_limited_handler(params: Dict[str, Any]) -> Dict[str, Any]:
            # Extract client ID (in real implementation, this would come from session/auth)
            client_id = params.get('_client_id', 'default')
            
            # Check rate limit
            allowed, error_msg = await self.check_rate_limit(client_id, operation)
            
            if not allowed:
                return {
                    "error": {
                        "code": -32603,
                        "message": error_msg,
                        "data": {"type": "rate_limit"}
                    }
                }
            
            # Execute handler
            return await handler(params)
        
        return rate_limited_handler
    
    def apply_rate_limits(self) -> None:
        """Apply rate limits to all handlers."""
        if not self.enabled or not self.server.tool_registry:
            return
        
        # Wrap tool handlers
        for tool_name, handler in self.server.tool_registry._tools.items():
            self.server.tool_registry._tools[tool_name] = self.wrap_handler_with_rate_limit(
                handler, tool_name
            )
            logger.debug(f"Applied rate limiting to tool: {tool_name}")
    
    async def get_rate_limit_stats(self) -> Dict[str, Any]:
        """Get rate limiting statistics."""
        stats = {
            "enabled": self.enabled,
            "limits": {
                "default": f"{self.requests_limit} per {self.window_seconds}s"
            },
            "current_blocks": len(self.blocked_until),
            "request_counts": {}
        }
        
        # Calculate current request rates
        now = time.time()
        cutoff = now - self.window_seconds
        
        for key, history in self.request_history.items():
            # Count recent requests
            recent_count = sum(1 for t in history if t > cutoff)
            if recent_count > 0:
                stats["request_counts"][key] = {
                    "count": recent_count,
                    "rate": recent_count / self.window_seconds
                }
        
        # Add rate limiter configurations
        if self.enabled:
            stats["rate_limiters"] = {}
            for name, limiter in self.rate_limiters.items():
                stats["rate_limiters"][name] = {
                    "algorithm": limiter.config.algorithm.value,
                    "max_requests": limiter.config.max_requests,
                    "window_seconds": limiter.config.window_seconds,
                    "burst_limit": limiter.config.burst_limit
                }
        
        return stats
    
    async def reset_client_limits(self, client_id: str) -> None:
        """Reset rate limits for a specific client."""
        if not self.enabled:
            return
        
        # Remove from blocked list
        if client_id in self.blocked_until:
            del self.blocked_until[client_id]
        
        # Clear history
        keys_to_remove = [k for k in self.request_history if k.startswith(f"{client_id}:")]
        for key in keys_to_remove:
            del self.request_history[key]
        
        # Reset in all rate limiters
        for limiter in self.rate_limiters.values():
            await limiter.reset_limit(client_id)
        
        logger.info(f"Reset rate limits for client: {client_id}")
    
    async def shutdown(self) -> None:
        """Shutdown rate limiting."""
        if self.enabled:
            logger.info("Shutting down rate limiting...")
            
            # Stop all rate limiters
            for limiter in self.rate_limiters.values():
                await limiter.stop()
            
            self.enabled = False
            logger.info("Rate limiting shutdown complete")


class RateLimiter:
    """Rate limiter for MCP server with feature management integration."""
    
    def __init__(self, server: 'StdioMCPServer'):
        self.server = server
        self.enabled = False
        self._max_requests = 100
        self._window_seconds = 60
        self._request_history: Dict[str, deque] = defaultdict(deque)
        self._whitelist: Set[str] = set()
        self._custom_limits: Dict[str, int] = {}
        self._total_requests = 0
        self._blocked_requests = 0
        self._cleanup_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
    
    async def initialize(self) -> None:
        """Initialize rate limiting if enabled."""
        # Check if rate limit feature is enabled
        rate_limit_enabled = os.environ.get('MCP_ENABLE_RATE_LIMIT', 'false').lower() == 'true'
        
        if not rate_limit_enabled:
            self.enabled = False
            return
        
        # Get configuration from environment
        self._max_requests = int(os.environ.get('MCP_RATE_LIMIT_REQUESTS', '100'))
        self._window_seconds = float(os.environ.get('MCP_RATE_LIMIT_WINDOW', '60'))
        
        self.enabled = True
        
        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
        
        logger.info(f"Rate limiting enabled: {self._max_requests} requests per {self._window_seconds}s")
    
    async def shutdown(self) -> None:
        """Shutdown rate limiting."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Error during cleanup task shutdown: {e}")
        
        logger.info("Rate limiting shutdown complete")
    
    async def check_rate_limit(self, client_id: str) -> bool:
        """Check if request is allowed for client."""
        if not self.enabled:
            return True
        
        # Check whitelist
        if client_id in self._whitelist:
            return True
        
        async with self._lock:
            self._total_requests += 1
            
            current_time = time.time()
            history = self._request_history[client_id]
            
            # Clean old requests
            cutoff_time = current_time - self._window_seconds
            while history and history[0] < cutoff_time:
                history.popleft()
            
            # Get limit for this client
            limit = self._custom_limits.get(client_id, self._max_requests)
            
            # Check if under limit
            if len(history) < limit:
                history.append(current_time)
                return True
            else:
                self._blocked_requests += 1
                return False
    
    def wrap_handler(self, handler: Callable) -> Callable:
        """Wrap request handlers with rate limiting."""
        async def wrapped_handler(request):
            client_id = getattr(request, 'client_id', 'default')
            
            if not await self.check_rate_limit(client_id):
                raise Exception("Rate limit exceeded")
            
            return await handler(request)
        
        return wrapped_handler
    
    async def get_rate_limit_stats(self) -> Dict[str, Any]:
        """Get statistics on rate limiting."""
        async with self._lock:
            unique_clients = len(self._request_history)
            
            return {
                'enabled': self.enabled,
                'total_requests': self._total_requests,
                'blocked_requests': self._blocked_requests,
                'unique_clients': unique_clients,
                'max_requests': self._max_requests,
                'window_seconds': self._window_seconds,
                'whitelist_size': len(self._whitelist),
                'custom_limits': len(self._custom_limits)
            }
    
    def get_rate_limit_headers(self, client_id: str) -> Dict[str, str]:
        """Get rate limit headers for HTTP responses."""
        if not self.enabled:
            return {}
        
        # Get current usage
        current_time = time.time()
        history = self._request_history.get(client_id, deque())
        
        # Clean old requests
        cutoff_time = current_time - self._window_seconds
        while history and history[0] < cutoff_time:
            history.popleft()
        
        limit = self._custom_limits.get(client_id, self._max_requests)
        remaining = max(0, limit - len(history))
        
        # Calculate reset time (when oldest request expires)
        reset_time = int(current_time + self._window_seconds)
        if history:
            reset_time = int(history[0] + self._window_seconds)
        
        return {
            'X-RateLimit-Limit': str(limit),
            'X-RateLimit-Remaining': str(remaining),
            'X-RateLimit-Reset': str(reset_time)
        }
    
    def add_to_whitelist(self, client_id: str) -> None:
        """Exempt specific clients from rate limiting."""
        self._whitelist.add(client_id)
        logger.info(f"Added client {client_id} to rate limit whitelist")
    
    def set_custom_limit(self, client_id: str, limit: int) -> None:
        """Set custom limits per client."""
        self._custom_limits[client_id] = limit
        logger.info(f"Set custom rate limit for client {client_id}: {limit} requests")
    
    async def _cleanup_old_requests(self) -> None:
        """Remove expired request history."""
        async with self._lock:
            current_time = time.time()
            cutoff_time = current_time - self._window_seconds
            
            clients_to_remove = []
            for client_id, history in self._request_history.items():
                while history and history[0] < cutoff_time:
                    history.popleft()
                
                # Remove empty histories
                if not history:
                    clients_to_remove.append(client_id)
            
            for client_id in clients_to_remove:
                del self._request_history[client_id]
    
    async def _periodic_cleanup(self) -> None:
        """Periodic cleanup task."""
        while True:
            try:
                await asyncio.sleep(self._window_seconds)
                await self._cleanup_old_requests()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Rate limiter cleanup error: {e}")


async def setup_rate_limiter(server: 'StdioMCPServer') -> Optional[RateLimitIntegration]:
    """Set up rate limiting for the server."""
    rate_limit_integration = RateLimitIntegration(server)
    await rate_limit_integration.setup()
    
    # Apply rate limits to handlers
    if rate_limit_integration.enabled:
        rate_limit_integration.apply_rate_limits()
    
    return rate_limit_integration if rate_limit_integration.enabled else None