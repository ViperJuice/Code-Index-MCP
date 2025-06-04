"""
JSON-RPC 2.0 protocol handler for MCP.

This module implements the complete JSON-RPC 2.0 protocol handling
for the Model Context Protocol, including request/response serialization,
error handling, and batch request support.
"""

import json
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Union, Callable
from enum import IntEnum
import logging

logger = logging.getLogger(__name__)


class JSONRPCErrorCode(IntEnum):
    """Standard JSON-RPC 2.0 error codes."""
    
    # JSON-RPC 2.0 standard error codes
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    
    # Implementation-defined errors (-32000 to -32099)
    SERVER_NOT_INITIALIZED = -32002
    UNKNOWN_ERROR = -32001
    REQUEST_CANCELLED = -32000


class JSONRPCError(Exception):
    """JSON-RPC 2.0 error exception."""
    
    def __init__(
        self,
        code: int,
        message: str,
        data: Optional[Any] = None
    ):
        """
        Initialize a JSON-RPC error.
        
        Args:
            code: Error code (should use JSONRPCErrorCode values)
            message: Human-readable error message
            data: Optional additional error data
        """
        self.code = code
        self.message = message
        self.data = data
        super().__init__(f"JSON-RPC Error {code}: {message}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary format."""
        error_dict = {
            "code": int(self.code),  # Ensure code is serialized as int
            "message": self.message
        }
        if self.data is not None:
            error_dict["data"] = self.data
        return error_dict


@dataclass
class JSONRPCRequest:
    """JSON-RPC 2.0 request object."""
    
    method: str
    params: Optional[Union[List[Any], Dict[str, Any]]] = None
    id: Optional[Union[str, int]] = None
    jsonrpc: str = field(default="2.0", init=False)
    
    def __post_init__(self):
        """Validate request after initialization."""
        if not isinstance(self.method, str) or not self.method:
            raise JSONRPCError(
                JSONRPCErrorCode.INVALID_REQUEST,
                "Method must be a non-empty string"
            )
        
        if self.params is not None:
            if not isinstance(self.params, (list, dict)):
                raise JSONRPCError(
                    JSONRPCErrorCode.INVALID_REQUEST,
                    "Params must be an array or object"
                )
        
        if self.id is not None:
            if not isinstance(self.id, (str, int)):
                raise JSONRPCError(
                    JSONRPCErrorCode.INVALID_REQUEST,
                    "ID must be a string or number"
                )
    
    @property
    def is_notification(self) -> bool:
        """Check if this is a notification (no ID)."""
        return self.id is None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert request to dictionary format."""
        request_dict = {
            "jsonrpc": self.jsonrpc,
            "method": self.method
        }
        
        if self.params is not None:
            request_dict["params"] = self.params
        
        if self.id is not None:
            request_dict["id"] = self.id
            
        return request_dict


@dataclass
class JSONRPCResponse:
    """JSON-RPC 2.0 response object."""
    
    id: Optional[Union[str, int]]
    result: Optional[Any] = None
    error: Optional[JSONRPCError] = None
    jsonrpc: str = field(default="2.0", init=False)
    
    def __post_init__(self):
        """Validate response after initialization."""
        if self.result is not None and self.error is not None:
            raise ValueError("Response cannot have both result and error")
        
        if self.result is None and self.error is None:
            raise ValueError("Response must have either result or error")
    
    @classmethod
    def success(cls, id: Optional[Union[str, int]], result: Any) -> "JSONRPCResponse":
        """Create a successful response."""
        return cls(id=id, result=result)
    
    @classmethod
    def error_response(
        cls,
        id: Optional[Union[str, int]],
        error: JSONRPCError
    ) -> "JSONRPCResponse":
        """Create an error response."""
        return cls(id=id, error=error)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary format."""
        response_dict = {
            "jsonrpc": self.jsonrpc,
            "id": self.id
        }
        
        if self.error is not None:
            response_dict["error"] = self.error.to_dict()
        else:
            response_dict["result"] = self.result
            
        return response_dict


class JSONRPCParser:
    """Parser for JSON-RPC 2.0 messages."""
    
    @staticmethod
    def parse_request(data: Union[str, bytes, Dict[str, Any]]) -> Union[JSONRPCRequest, List[JSONRPCRequest]]:
        """
        Parse a JSON-RPC 2.0 request.
        
        Args:
            data: Raw request data (JSON string, bytes, or dict)
            
        Returns:
            Single JSONRPCRequest or list of requests for batch
            
        Raises:
            JSONRPCError: If parsing or validation fails
        """
        try:
            if isinstance(data, (str, bytes)):
                # Handle empty string/bytes case
                if not data or (isinstance(data, str) and not data.strip()):
                    raise JSONRPCError(
                        JSONRPCErrorCode.PARSE_ERROR,
                        "Parse error: Empty request"
                    )
                parsed = json.loads(data)
            else:
                parsed = data
        except json.JSONDecodeError as e:
            # Provide cleaner error message for common cases
            error_msg = str(e)
            if "Expecting value" in error_msg and "line 1 column 1 (char 0)" in error_msg:
                error_msg = "Empty or invalid JSON"
            else:
                error_msg = f"Invalid JSON: {error_msg}"
            
            raise JSONRPCError(
                JSONRPCErrorCode.PARSE_ERROR,
                f"Parse error: {error_msg}"
            )
        
        if isinstance(parsed, list):
            # Batch request
            if not parsed:
                raise JSONRPCError(
                    JSONRPCErrorCode.INVALID_REQUEST,
                    "Batch request cannot be empty"
                )
            return [JSONRPCParser._parse_single_request(req) for req in parsed]
        else:
            # Single request
            return JSONRPCParser._parse_single_request(parsed)
    
    @staticmethod
    def _parse_single_request(data: Dict[str, Any]) -> JSONRPCRequest:
        """Parse a single JSON-RPC request."""
        if not isinstance(data, dict):
            raise JSONRPCError(
                JSONRPCErrorCode.INVALID_REQUEST,
                "Request must be an object"
            )
        
        # Check JSON-RPC version
        if data.get("jsonrpc") != "2.0":
            raise JSONRPCError(
                JSONRPCErrorCode.INVALID_REQUEST,
                "JSON-RPC version must be '2.0'"
            )
        
        # Extract required fields
        if "method" not in data:
            raise JSONRPCError(
                JSONRPCErrorCode.INVALID_REQUEST,
                "Missing required field: method"
            )
        
        try:
            return JSONRPCRequest(
                method=data["method"],
                params=data.get("params"),
                id=data.get("id")
            )
        except JSONRPCError:
            raise
        except Exception as e:
            raise JSONRPCError(
                JSONRPCErrorCode.INVALID_REQUEST,
                f"Invalid request: {str(e)}"
            )
    
    @staticmethod
    def parse_response(data: Union[str, bytes, Dict[str, Any]]) -> JSONRPCResponse:
        """
        Parse a JSON-RPC 2.0 response.
        
        Args:
            data: Raw response data (JSON string, bytes, or dict)
            
        Returns:
            JSONRPCResponse object
            
        Raises:
            JSONRPCError: If parsing or validation fails
        """
        try:
            if isinstance(data, (str, bytes)):
                # Handle empty string/bytes case
                if not data or (isinstance(data, str) and not data.strip()):
                    raise JSONRPCError(
                        JSONRPCErrorCode.PARSE_ERROR,
                        "Parse error: Empty response"
                    )
                parsed = json.loads(data)
            else:
                parsed = data
        except json.JSONDecodeError as e:
            # Provide cleaner error message for common cases
            error_msg = str(e)
            if "Expecting value" in error_msg and "line 1 column 1 (char 0)" in error_msg:
                error_msg = "Empty or invalid JSON"
            else:
                error_msg = f"Invalid JSON: {error_msg}"
            
            raise JSONRPCError(
                JSONRPCErrorCode.PARSE_ERROR,
                f"Parse error: {error_msg}"
            )
        
        if not isinstance(parsed, dict):
            raise JSONRPCError(
                JSONRPCErrorCode.INVALID_REQUEST,
                "Response must be an object"
            )
        
        # Check JSON-RPC version
        if parsed.get("jsonrpc") != "2.0":
            raise JSONRPCError(
                JSONRPCErrorCode.INVALID_REQUEST,
                "JSON-RPC version must be '2.0'"
            )
        
        # Parse error if present
        error = None
        if "error" in parsed:
            error_data = parsed["error"]
            if not isinstance(error_data, dict):
                raise JSONRPCError(
                    JSONRPCErrorCode.INVALID_REQUEST,
                    "Error must be an object"
                )
            
            error = JSONRPCError(
                code=error_data.get("code", JSONRPCErrorCode.UNKNOWN_ERROR),
                message=error_data.get("message", "Unknown error"),
                data=error_data.get("data")
            )
        
        try:
            return JSONRPCResponse(
                id=parsed.get("id"),
                result=parsed.get("result"),
                error=error
            )
        except Exception as e:
            raise JSONRPCError(
                JSONRPCErrorCode.INVALID_REQUEST,
                f"Invalid response: {str(e)}"
            )


class JSONRPCSerializer:
    """Serializer for JSON-RPC 2.0 messages."""
    
    @staticmethod
    def serialize_request(request: Union[JSONRPCRequest, List[JSONRPCRequest]]) -> str:
        """
        Serialize a JSON-RPC request to JSON string.
        
        Args:
            request: Single request or list of requests (batch)
            
        Returns:
            JSON string representation
        """
        if isinstance(request, list):
            data = [req.to_dict() for req in request]
        else:
            data = request.to_dict()
        
        return json.dumps(data, separators=(',', ':'))
    
    @staticmethod
    def serialize_response(response: Union[JSONRPCResponse, List[JSONRPCResponse]]) -> str:
        """
        Serialize a JSON-RPC response to JSON string.
        
        Args:
            response: Single response or list of responses (batch)
            
        Returns:
            JSON string representation
        """
        if isinstance(response, list):
            data = [resp.to_dict() for resp in response]
        else:
            data = response.to_dict()
        
        return json.dumps(data, separators=(',', ':'))


class JSONRPCHandler:
    """Handler for processing JSON-RPC 2.0 requests."""
    
    def __init__(self):
        """Initialize the JSON-RPC handler."""
        self.methods: Dict[str, Callable] = {}
    
    def register_method(self, name: str, handler: Callable) -> None:
        """
        Register a method handler.
        
        Args:
            name: Method name
            handler: Callable that handles the method
        """
        self.methods[name] = handler
        logger.debug(f"Registered JSON-RPC method: {name}")
    
    def unregister_method(self, name: str) -> None:
        """
        Unregister a method handler.
        
        Args:
            name: Method name to unregister
        """
        if name in self.methods:
            del self.methods[name]
            logger.debug(f"Unregistered JSON-RPC method: {name}")
    
    async def handle_request(
        self,
        request: Union[JSONRPCRequest, List[JSONRPCRequest]]
    ) -> Optional[Union[JSONRPCResponse, List[JSONRPCResponse]]]:
        """
        Handle a JSON-RPC request.
        
        Args:
            request: Single request or batch of requests
            
        Returns:
            Response(s) or None for notifications
        """
        if isinstance(request, list):
            # Handle batch request
            responses = []
            for req in request:
                resp = await self._handle_single_request(req)
                if resp is not None:
                    responses.append(resp)
            return responses if responses else None
        else:
            # Handle single request
            return await self._handle_single_request(request)
    
    async def _handle_single_request(self, request: JSONRPCRequest) -> Optional[JSONRPCResponse]:
        """Handle a single JSON-RPC request."""
        # Skip response for notifications
        if request.is_notification:
            try:
                await self._execute_method(request)
            except Exception as e:
                logger.error(f"Error in notification handler: {e}")
            return None
        
        try:
            result = await self._execute_method(request)
            return JSONRPCResponse.success(request.id, result)
        except JSONRPCError as e:
            return JSONRPCResponse.error_response(request.id, e)
        except Exception as e:
            logger.error(f"Unexpected error handling request: {e}")
            error = JSONRPCError(
                JSONRPCErrorCode.INTERNAL_ERROR,
                "Internal error",
                data=str(e)
            )
            return JSONRPCResponse.error_response(request.id, error)
    
    async def _execute_method(self, request: JSONRPCRequest) -> Any:
        """Execute a method for a request."""
        if request.method not in self.methods:
            raise JSONRPCError(
                JSONRPCErrorCode.METHOD_NOT_FOUND,
                f"Method not found: {request.method}"
            )
        
        handler = self.methods[request.method]
        
        try:
            # Call handler with params
            if request.params is None:
                return await handler()
            elif isinstance(request.params, list):
                return await handler(*request.params)
            elif isinstance(request.params, dict):
                return await handler(**request.params)
        except TypeError as e:
            raise JSONRPCError(
                JSONRPCErrorCode.INVALID_PARAMS,
                f"Invalid parameters: {str(e)}"
            )


# Standard error instances for common cases
PARSE_ERROR = JSONRPCError(
    JSONRPCErrorCode.PARSE_ERROR,
    "Parse error"
)

INVALID_REQUEST = JSONRPCError(
    JSONRPCErrorCode.INVALID_REQUEST,
    "Invalid Request"
)

METHOD_NOT_FOUND = JSONRPCError(
    JSONRPCErrorCode.METHOD_NOT_FOUND,
    "Method not found"
)

INVALID_PARAMS = JSONRPCError(
    JSONRPCErrorCode.INVALID_PARAMS,
    "Invalid params"
)

INTERNAL_ERROR = JSONRPCError(
    JSONRPCErrorCode.INTERNAL_ERROR,
    "Internal error"
)

# Common aliases for backward compatibility
JsonRpcRequest = JSONRPCRequest
JsonRpcResponse = JSONRPCResponse
JsonRpcError = JSONRPCError
JsonRpcNotification = JSONRPCRequest  # Notifications are requests without ID
JsonRpcMessage = JSONRPCRequest  # Generic message type