"""
MCP error definitions and handling.

This module extends JSON-RPC error handling with MCP-specific error codes,
provides consistent error response formatting, and integrates with the
logging system for proper error tracking.
"""

from enum import IntEnum
from typing import Any, Dict, Optional, Union
import logging
import traceback

from ..core.logging import get_logger
from .jsonrpc import JSONRPCError, JSONRPCErrorCode, JSONRPCResponse

logger = get_logger(__name__)


class MCPErrorCode(IntEnum):
    """
    MCP-specific error codes.
    
    These extend the JSON-RPC error codes with MCP-specific errors.
    MCP error codes are in the range -32800 to -32899.
    """
    
    # Resource errors (-32800 to -32809)
    RESOURCE_NOT_FOUND = -32800
    RESOURCE_ACCESS_DENIED = -32801
    RESOURCE_CONFLICT = -32802
    RESOURCE_INVALID = -32803
    
    # Tool errors (-32810 to -32819)
    TOOL_NOT_FOUND = -32810
    TOOL_EXECUTION_FAILED = -32811
    TOOL_INVALID_PARAMS = -32812
    TOOL_TIMEOUT = -32813
    
    # Transport errors (-32820 to -32829)
    TRANSPORT_ERROR = -32820
    CONNECTION_CLOSED = -32821
    MESSAGE_TOO_LARGE = -32822
    
    # Session errors (-32830 to -32839)
    SESSION_NOT_INITIALIZED = -32830
    SESSION_EXPIRED = -32831
    CAPABILITY_NOT_SUPPORTED = -32832
    
    # Subscription errors (-32840 to -32849)
    SUBSCRIPTION_NOT_FOUND = -32840
    SUBSCRIPTION_FAILED = -32841
    
    # Authentication/Authorization errors (-32850 to -32859)
    AUTHENTICATION_REQUIRED = -32850
    AUTHENTICATION_FAILED = -32851
    AUTHORIZATION_FAILED = -32852
    
    # Rate limiting errors (-32860 to -32869)
    RATE_LIMIT_EXCEEDED = -32860
    QUOTA_EXCEEDED = -32861
    
    # General MCP errors (-32890 to -32899)
    MCP_PROTOCOL_ERROR = -32890
    MCP_INTERNAL_ERROR = -32891
    MCP_NOT_IMPLEMENTED = -32892


class MCPError(JSONRPCError):
    """
    MCP-specific error that extends JSONRPCError.
    
    Provides additional context and logging for MCP errors.
    """
    
    def __init__(
        self,
        code: int,
        message: str,
        data: Optional[Any] = None,
        context: Optional[Dict[str, Any]] = None,
        should_log: bool = True
    ):
        """Initialize MCP error with additional context and logging."""
        super().__init__(code, message, data)
        self.context = context
        self.should_log = should_log
        
        if self.should_log:
            self._log_error()
    
    def _log_error(self) -> None:
        """Log the error with appropriate severity."""
        # Determine log level based on error code
        if self.code in [
            MCPErrorCode.MCP_INTERNAL_ERROR,
            MCPErrorCode.TOOL_EXECUTION_FAILED,
            JSONRPCErrorCode.INTERNAL_ERROR
        ]:
            logger.error(
                f"MCP Error {self.code}: {self.message}",
                extra={"error_data": self.data, "context": self.context}
            )
        elif self.code in [
            MCPErrorCode.RESOURCE_NOT_FOUND,
            MCPErrorCode.TOOL_NOT_FOUND,
            JSONRPCErrorCode.METHOD_NOT_FOUND
        ]:
            logger.warning(
                f"MCP Error {self.code}: {self.message}",
                extra={"error_data": self.data, "context": self.context}
            )
        else:
            logger.info(
                f"MCP Error {self.code}: {self.message}",
                extra={"error_data": self.data, "context": self.context}
            )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary format with optional context."""
        error_dict = super().to_dict()
        
        # Add context to data if present
        if self.context:
            if error_dict.get("data") is None:
                error_dict["data"] = {}
            elif isinstance(error_dict["data"], str):
                error_dict["data"] = {"message": error_dict["data"]}
            
            if isinstance(error_dict["data"], dict):
                error_dict["data"]["context"] = self.context
        
        return error_dict


class MCPException(Exception):
    """
    Base exception for MCP-specific errors.
    
    This is raised internally and converted to MCPError for protocol responses.
    """
    
    def __init__(
        self,
        code: Union[MCPErrorCode, JSONRPCErrorCode],
        message: str,
        data: Optional[Any] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """Initialize MCP exception."""
        self.code = code
        self.message = message
        self.data = data
        self.context = context
        super().__init__(message)
    
    def to_mcp_error(self) -> MCPError:
        """Convert exception to MCPError for protocol response."""
        return MCPError(
            code=int(self.code),
            message=self.message,
            data=self.data,
            context=self.context
        )


# Specific exception classes for different MCP error scenarios

class ResourceNotFoundException(MCPException):
    """Raised when a requested resource is not found."""
    
    def __init__(self, resource_uri: str, message: Optional[str] = None):
        super().__init__(
            MCPErrorCode.RESOURCE_NOT_FOUND,
            message or f"Resource not found: {resource_uri}",
            data={"uri": resource_uri}
        )


class ResourceAccessDeniedException(MCPException):
    """Raised when access to a resource is denied."""
    
    def __init__(self, resource_uri: str, reason: Optional[str] = None):
        super().__init__(
            MCPErrorCode.RESOURCE_ACCESS_DENIED,
            f"Access denied to resource: {resource_uri}",
            data={"uri": resource_uri, "reason": reason}
        )


class ToolNotFoundException(MCPException):
    """Raised when a requested tool is not found."""
    
    def __init__(self, tool_name: str):
        super().__init__(
            MCPErrorCode.TOOL_NOT_FOUND,
            f"Tool not found: {tool_name}",
            data={"tool": tool_name}
        )


class ToolExecutionException(MCPException):
    """Raised when tool execution fails."""
    
    def __init__(self, tool_name: str, error: Exception):
        super().__init__(
            MCPErrorCode.TOOL_EXECUTION_FAILED,
            f"Tool execution failed: {tool_name}",
            data={
                "tool": tool_name,
                "error": str(error),
                "traceback": traceback.format_exc()
            }
        )


class SessionNotInitializedException(MCPException):
    """Raised when attempting operations before session initialization."""
    
    def __init__(self, operation: str):
        super().__init__(
            MCPErrorCode.SESSION_NOT_INITIALIZED,
            f"Session not initialized for operation: {operation}",
            data={"operation": operation}
        )


class CapabilityNotSupportedException(MCPException):
    """Raised when a requested capability is not supported."""
    
    def __init__(self, capability: str):
        super().__init__(
            MCPErrorCode.CAPABILITY_NOT_SUPPORTED,
            f"Capability not supported: {capability}",
            data={"capability": capability}
        )


class AuthenticationRequiredException(MCPException):
    """Raised when authentication is required but not provided."""
    
    def __init__(self, realm: Optional[str] = None):
        super().__init__(
            MCPErrorCode.AUTHENTICATION_REQUIRED,
            "Authentication required",
            data={"realm": realm} if realm else None
        )


class RateLimitExceededException(MCPException):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, limit: int, window: str, retry_after: Optional[int] = None):
        super().__init__(
            MCPErrorCode.RATE_LIMIT_EXCEEDED,
            f"Rate limit exceeded: {limit} requests per {window}",
            data={
                "limit": limit,
                "window": window,
                "retry_after": retry_after
            }
        )


# Helper functions for creating consistent error responses

def create_error_response(
    request_id: Optional[Union[str, int]],
    error: Union[MCPException, MCPError, JSONRPCError, Exception]
) -> JSONRPCResponse:
    """
    Create a JSON-RPC error response from various error types.
    
    Args:
        request_id: The request ID to include in the response
        error: The error to convert to a response
        
    Returns:
        JSONRPCResponse with error information
    """
    if isinstance(error, MCPException):
        mcp_error = error.to_mcp_error()
    elif isinstance(error, (MCPError, JSONRPCError)):
        mcp_error = error
    else:
        # Convert generic exceptions to MCP internal error
        logger.exception("Unexpected error in MCP handler")
        mcp_error = MCPError(
            code=int(MCPErrorCode.MCP_INTERNAL_ERROR),
            message="Internal MCP error",
            data={
                "error": str(error),
                "type": type(error).__name__,
                "traceback": traceback.format_exc()
            }
        )
    
    return JSONRPCResponse.error_response(request_id, mcp_error)


def create_method_not_found_error(method: str) -> MCPError:
    """Create a standardized method not found error."""
    return MCPError(
        code=int(JSONRPCErrorCode.METHOD_NOT_FOUND),
        message=f"Method not found: {method}",
        data={"method": method},
        should_log=False  # Don't log method not found as it's common
    )


def create_invalid_params_error(method: str, details: str) -> MCPError:
    """Create a standardized invalid parameters error."""
    return MCPError(
        code=int(JSONRPCErrorCode.INVALID_PARAMS),
        message=f"Invalid parameters for method '{method}': {details}",
        data={"method": method, "details": details}
    )


def create_internal_error(details: Optional[str] = None) -> MCPError:
    """Create a standardized internal error."""
    return MCPError(
        code=int(MCPErrorCode.MCP_INTERNAL_ERROR),
        message="Internal MCP server error",
        data={"details": details} if details else None
    )


def log_error_context(
    error: Union[MCPError, MCPException, Exception],
    context: Dict[str, Any]
) -> None:
    """
    Log additional error context for debugging.
    
    Args:
        error: The error that occurred
        context: Additional context information
    """
    error_info = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "context": context
    }
    
    if isinstance(error, (MCPError, MCPException)):
        error_info["error_code"] = error.code
        error_info["error_data"] = getattr(error, "data", None)
    
    logger.error("Error with context", extra=error_info)


# Standard error instances for common cases
RESOURCE_NOT_FOUND = MCPError(
    code=int(MCPErrorCode.RESOURCE_NOT_FOUND),
    message="Resource not found",
    should_log=False
)

TOOL_NOT_FOUND = MCPError(
    code=int(MCPErrorCode.TOOL_NOT_FOUND),
    message="Tool not found",
    should_log=False
)

SESSION_NOT_INITIALIZED = MCPError(
    code=int(MCPErrorCode.SESSION_NOT_INITIALIZED),
    message="Session not initialized",
    should_log=False
)

AUTHENTICATION_REQUIRED = MCPError(
    code=int(MCPErrorCode.AUTHENTICATION_REQUIRED),
    message="Authentication required",
    should_log=False
)

# Common aliases for backward compatibility
McpError = MCPError
ErrorCode = MCPErrorCode
