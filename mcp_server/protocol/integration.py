"""
Integration module for connecting JSON-RPC handler with MCP method routing.

This module provides the glue between the JSON-RPC protocol layer and the
MCP method routing system.
"""

import logging
from typing import Dict, Any, Optional, Union, List

from .jsonrpc import JSONRPCHandler, JSONRPCRequest, JSONRPCResponse, JSONRPCError
from .methods import MethodRouter, MethodRegistry, default_registry
from ..interfaces.mcp_interfaces import MCPRequest

logger = logging.getLogger(__name__)


class MCPJSONRPCHandler(JSONRPCHandler):
    """
    JSON-RPC handler integrated with MCP method routing.
    
    This handler automatically routes JSON-RPC requests to the appropriate
    MCP method handlers.
    """
    
    def __init__(self, method_router: Optional[MethodRouter] = None):
        """
        Initialize the MCP JSON-RPC handler.
        
        Args:
            method_router: MCP method router (uses default if not provided)
        """
        super().__init__()
        self.method_router = method_router or MethodRouter(default_registry)
        
        # Register all MCP methods with the JSON-RPC handler
        self._register_mcp_methods()
    
    def _register_mcp_methods(self) -> None:
        """Register all MCP methods from the router's registry."""
        for method_name in self.method_router.registry.list_methods():
            # Create a closure to capture the method name
            async def handle_method(method=method_name, **params):
                return await self._handle_mcp_method(method, params)
            
            # Register with JSON-RPC handler
            self.register_method(method_name, handle_method)
            logger.debug(f"Registered MCP method with JSON-RPC: {method_name}")
    
    async def _handle_mcp_method(self, method: str, params: Optional[Dict[str, Any]]) -> Any:
        """
        Handle an MCP method call.
        
        Args:
            method: Method name
            params: Method parameters
            
        Returns:
            Method result
            
        Raises:
            JSONRPCError: If method handling fails
        """
        # Create MCP request
        mcp_request = MCPRequest(method=method, params=params)
        
        # Route through MCP method router
        mcp_response = await self.method_router.route(mcp_request)
        
        # Check for errors
        if mcp_response.error:
            raise JSONRPCError(
                code=mcp_response.error.get("code", -32603),
                message=mcp_response.error.get("message", "Unknown error"),
                data=mcp_response.error.get("data")
            )
        
        return mcp_response.result
    
    def update_registry(self, registry: MethodRegistry) -> None:
        """
        Update the method registry and re-register methods.
        
        Args:
            registry: New method registry to use
        """
        # Clear existing methods
        for method_name in list(self.methods.keys()):
            self.unregister_method(method_name)
        
        # Update router
        self.method_router = MethodRouter(registry)
        
        # Re-register methods
        self._register_mcp_methods()


def create_mcp_jsonrpc_handler(
    registry: Optional[MethodRegistry] = None
) -> MCPJSONRPCHandler:
    """
    Create a JSON-RPC handler configured for MCP.
    
    Args:
        registry: Method registry to use (uses default if not provided)
        
    Returns:
        Configured MCPJSONRPCHandler instance
    """
    router = MethodRouter(registry or default_registry)
    return MCPJSONRPCHandler(router)


async def process_mcp_request(
    handler: MCPJSONRPCHandler,
    data: Union[str, bytes, Dict[str, Any]]
) -> Optional[str]:
    """
    Process an MCP request through JSON-RPC.
    
    Args:
        handler: MCP JSON-RPC handler
        data: Raw request data
        
    Returns:
        JSON-RPC response string, or None for notifications
    """
    from .jsonrpc import JSONRPCParser, JSONRPCSerializer
    
    try:
        # Parse request
        request = JSONRPCParser.parse_request(data)
        
        # Handle request
        response = await handler.handle_request(request)
        
        # Serialize response if not a notification
        if response is not None:
            return JSONRPCSerializer.serialize_response(response)
        
        return None
        
    except Exception as e:
        logger.error(f"Error processing MCP request: {e}")
        raise