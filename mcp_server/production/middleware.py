"""
Production middleware for MCP server.

Provides request tracking, error handling, and production features.
"""

import asyncio
import time
import uuid
import logging
from typing import Dict, List, Optional, Any, Callable, Awaitable, Union
from dataclasses import dataclass
from datetime import datetime
import traceback
import json

from ..protocol.jsonrpc import JsonRpcRequest, JsonRpcResponse, JsonRpcNotification
from ..protocol.errors import McpError, ErrorCode
from ..performance.rate_limiter import RateLimiter, RateLimitResult
from .monitoring import monitoring_system
from .logger import production_logger

logger = logging.getLogger(__name__)


@dataclass
class RequestContext:
    """Context information for a request."""
    request_id: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    correlation_id: Optional[str] = None
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    start_time: float = 0.0
    method: str = ""
    params: Optional[Dict[str, Any]] = None


class RequestTracker:
    """Tracks active requests and their context."""
    
    def __init__(self):
        self._active_requests: Dict[str, RequestContext] = {}
        self._request_history: List[RequestContext] = []
        self._max_history = 1000
    
    def start_request(self, request: Union[JsonRpcRequest, JsonRpcNotification],
                     client_info: Optional[Dict[str, Any]] = None) -> RequestContext:
        """Start tracking a request."""
        request_id = str(uuid.uuid4())
        
        context = RequestContext(
            request_id=request_id,
            start_time=time.time(),
            method=request.method,
            params=request.params
        )
        
        # Extract client information
        if client_info:
            context.user_id = client_info.get("user_id")
            context.session_id = client_info.get("session_id")
            context.correlation_id = client_info.get("correlation_id")
            context.client_ip = client_info.get("client_ip")
            context.user_agent = client_info.get("user_agent")
        
        self._active_requests[request_id] = context
        return context
    
    def end_request(self, request_id: str) -> Optional[RequestContext]:
        """End tracking a request."""
        context = self._active_requests.pop(request_id, None)
        if context:
            self._request_history.append(context)
            
            # Limit history size
            if len(self._request_history) > self._max_history:
                self._request_history = self._request_history[-self._max_history:]
        
        return context
    
    def get_active_requests(self) -> List[RequestContext]:
        """Get all active requests."""
        return list(self._active_requests.values())
    
    def get_request_history(self, limit: Optional[int] = None) -> List[RequestContext]:
        """Get request history."""
        if limit:
            return self._request_history[-limit:]
        return self._request_history.copy()
    
    def get_request_count(self) -> Dict[str, int]:
        """Get request counts."""
        return {
            "active": len(self._active_requests),
            "total_history": len(self._request_history)
        }


class ErrorHandler:
    """Handles and processes errors in production."""
    
    def __init__(self):
        self._error_counts: Dict[str, int] = {}
        self._recent_errors: List[Dict[str, Any]] = []
        self._max_recent_errors = 100
    
    def handle_error(self, error: Exception, context: RequestContext,
                    request: Optional[Union[JsonRpcRequest, JsonRpcNotification]] = None) -> JsonRpcResponse:
        """Handle an error and return appropriate response."""
        error_type = type(error).__name__
        error_message = str(error)
        
        # Track error statistics
        self._error_counts[error_type] = self._error_counts.get(error_type, 0) + 1
        
        # Log error details
        error_info = {
            "error_type": error_type,
            "error_message": error_message,
            "request_id": context.request_id,
            "method": context.method,
            "user_id": context.user_id,
            "timestamp": datetime.now().isoformat(),
            "stack_trace": traceback.format_exc()
        }
        
        self._recent_errors.append(error_info)
        if len(self._recent_errors) > self._max_recent_errors:
            self._recent_errors = self._recent_errors[-self._max_recent_errors:]
        
        # Log with structured logger
        structured_logger = production_logger.get_logger("error_handler")
        structured_logger.error(
            f"Request error: {error_message}",
            error=error,
            request_id=context.request_id,
            method=context.method,
            user_id=context.user_id,
            error_type=error_type
        )
        
        # Record metrics
        asyncio.create_task(monitoring_system.performance.record_error(
            error_type, context.method, {"user_id": context.user_id or "unknown"}
        ))
        
        # Convert to appropriate MCP error
        if isinstance(error, McpError):
            mcp_error = error
        elif isinstance(error, ValueError):
            mcp_error = McpError(
                code=ErrorCode.INVALID_PARAMS,
                message=error_message
            )
        elif isinstance(error, NotImplementedError):
            mcp_error = McpError(
                code=ErrorCode.METHOD_NOT_FOUND,
                message=error_message
            )
        elif isinstance(error, TimeoutError):
            mcp_error = McpError(
                code=ErrorCode.INTERNAL_ERROR,
                message="Request timeout"
            )
        else:
            mcp_error = McpError(
                code=ErrorCode.INTERNAL_ERROR,
                message="Internal server error"
            )
        
        # Create error response
        if request and hasattr(request, 'id'):
            return JsonRpcResponse(
                id=request.id,
                error=mcp_error.to_dict()
            )
        else:
            # For notifications, we can't send a response
            return None
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics."""
        return {
            "error_counts": dict(self._error_counts),
            "recent_errors": self._recent_errors[-10:],  # Last 10 errors
            "total_errors": sum(self._error_counts.values())
        }


class ProductionMiddleware:
    """Main production middleware that coordinates all features."""
    
    def __init__(self, rate_limiter: Optional[RateLimiter] = None):
        self.request_tracker = RequestTracker()
        self.error_handler = ErrorHandler()
        self.rate_limiter = rate_limiter
        self._logger = production_logger.get_logger("middleware")
    
    async def process_request(self, request: Union[JsonRpcRequest, JsonRpcNotification],
                             handler: Callable, client_info: Optional[Dict[str, Any]] = None) -> Optional[JsonRpcResponse]:
        """Process a request through all middleware layers."""
        # Start request tracking
        context = self.request_tracker.start_request(request, client_info)
        
        try:
            # Rate limiting
            if self.rate_limiter:
                rate_result = await self._check_rate_limit(context)
                if not rate_result.allowed:
                    return self._create_rate_limit_response(request, rate_result)
            
            # Start performance monitoring
            await monitoring_system.performance.start_request(
                context.request_id,
                context.method,
                {"user_id": context.user_id or "unknown"}
            )
            
            # Log request start
            self._logger.info(
                f"Request started: {context.method}",
                request_id=context.request_id,
                method=context.method,
                user_id=context.user_id,
                session_id=context.session_id,
                correlation_id=context.correlation_id
            )
            
            # Execute the actual handler
            response = await handler(request)
            
            # Log successful completion
            duration = time.time() - context.start_time
            self._logger.info(
                f"Request completed: {context.method}",
                request_id=context.request_id,
                method=context.method,
                duration_ms=duration * 1000,
                user_id=context.user_id
            )
            
            # End performance monitoring
            await monitoring_system.performance.end_request(
                context.request_id,
                context.method,
                "success",
                {"user_id": context.user_id or "unknown"}
            )
            
            return response
            
        except Exception as error:
            # Handle error
            error_response = self.error_handler.handle_error(error, context, request)
            
            # End performance monitoring with error status
            await monitoring_system.performance.end_request(
                context.request_id,
                context.method,
                "error",
                {"user_id": context.user_id or "unknown"}
            )
            
            return error_response
            
        finally:
            # End request tracking
            self.request_tracker.end_request(context.request_id)
    
    async def _check_rate_limit(self, context: RequestContext) -> RateLimitResult:
        """Check rate limiting for a request."""
        identifier = context.user_id or context.client_ip or "anonymous"
        rate_context = {
            "method": context.method,
            "user_id": context.user_id
        }
        
        return await self.rate_limiter.check_limit(identifier, rate_context)
    
    def _create_rate_limit_response(self, request: Union[JsonRpcRequest, JsonRpcNotification],
                                   rate_result: RateLimitResult) -> Optional[JsonRpcResponse]:
        """Create rate limit error response."""
        if hasattr(request, 'id'):
            return JsonRpcResponse(
                id=request.id,
                error=McpError(
                    code=ErrorCode.INTERNAL_ERROR,
                    message=f"Rate limit exceeded. Try again in {rate_result.retry_after:.1f} seconds",
                    data={
                        "retry_after": rate_result.retry_after,
                        "limit": rate_result.limit,
                        "remaining": rate_result.remaining
                    }
                ).to_dict()
            )
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get middleware statistics."""
        return {
            "requests": self.request_tracker.get_request_count(),
            "errors": self.error_handler.get_error_stats(),
            "timestamp": datetime.now().isoformat()
        }


class MiddlewareStack:
    """Stack of middleware components."""
    
    def __init__(self):
        self._middleware: List[ProductionMiddleware] = []
        self._default_middleware: Optional[ProductionMiddleware] = None
    
    def add_middleware(self, middleware: ProductionMiddleware) -> None:
        """Add middleware to the stack."""
        self._middleware.append(middleware)
    
    def set_default_middleware(self, middleware: ProductionMiddleware) -> None:
        """Set the default middleware."""
        self._default_middleware = middleware
    
    async def process_request(self, request: Union[JsonRpcRequest, JsonRpcNotification],
                             handler: Callable, client_info: Optional[Dict[str, Any]] = None) -> Optional[JsonRpcResponse]:
        """Process request through middleware stack."""
        # Use default middleware if available
        if self._default_middleware:
            return await self._default_middleware.process_request(request, handler, client_info)
        
        # Otherwise, process through stack (for future extensibility)
        for middleware in self._middleware:
            response = await middleware.process_request(request, handler, client_info)
            if response:
                return response
        
        # If no middleware handled it, call handler directly
        return await handler(request)
    
    def get_combined_stats(self) -> Dict[str, Any]:
        """Get combined statistics from all middleware."""
        stats = {"middleware": []}
        
        if self._default_middleware:
            stats["default"] = self._default_middleware.get_stats()
        
        for i, middleware in enumerate(self._middleware):
            stats["middleware"].append({
                "index": i,
                "stats": middleware.get_stats()
            })
        
        return stats


# Global middleware stack
middleware_stack = MiddlewareStack()

# Create and configure default middleware
default_middleware = ProductionMiddleware()
middleware_stack.set_default_middleware(default_middleware)