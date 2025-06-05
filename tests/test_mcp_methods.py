"""Tests for MCP method routing system."""

import pytest
import json
from typing import Dict, Any

from mcp_server.protocol import (
    MCPMethod,
    MethodRegistry,
    MethodRouter,
    create_default_registry,
    MCPJSONRPCHandler,
    create_mcp_jsonrpc_handler,
    process_mcp_request,
    JSONRPCError,
    JSONRPCErrorCode,
)
from mcp_server.interfaces.mcp_interfaces import MCPRequest


class TestMethodRegistry:
    """Test the MCP method registry."""
    
    @pytest.mark.asyncio
    async def test_register_method(self):
        """Test registering a method handler."""
        registry = MethodRegistry()
        
        async def test_handler():
            return {"test": "result"}
        
        registry.register(
            "test/method",
            test_handler,
            description="Test method"
        )
        
        assert "test/method" in registry.list_methods()
        handler = registry.get_handler("test/method")
        assert handler is not None
        assert handler.description == "Test method"
    
    def test_register_non_async_handler(self):
        """Test that registering non-async handler fails."""
        registry = MethodRegistry()
        
        def sync_handler():
            return {"test": "result"}
        
        with pytest.raises(ValueError, match="must be an async function"):
            registry.register("test/method", sync_handler)
    
    def test_unregister_method(self):
        """Test unregistering a method."""
        registry = MethodRegistry()
        
        async def test_handler():
            return {"test": "result"}
        
        registry.register("test/method", test_handler)
        assert "test/method" in registry.list_methods()
        
        registry.unregister("test/method")
        assert "test/method" not in registry.list_methods()
    
    def test_initialization_state(self):
        """Test registry initialization state."""
        registry = MethodRegistry()
        assert not registry.is_initialized()
        
        registry.set_initialized(True)
        assert registry.is_initialized()


class TestMethodRouter:
    """Test the MCP method router."""
    
    @pytest.mark.asyncio
    async def test_route_to_handler(self):
        """Test routing a request to its handler."""
        registry = MethodRegistry()
        router = MethodRouter(registry)
        
        async def echo_handler(message: str) -> Dict[str, Any]:
            return {"echo": message}
        
        registry.register("echo", echo_handler, requires_initialization=False)
        
        request = MCPRequest(method="echo", params={"message": "Hello"})
        response = await router.route(request)
        
        assert response.result == {"echo": "Hello"}
        assert response.error is None
    
    @pytest.mark.asyncio
    async def test_method_not_found(self):
        """Test error when method is not found."""
        router = MethodRouter()
        request = MCPRequest(method="nonexistent/method")
        
        with pytest.raises(JSONRPCError) as exc_info:
            await router.route(request)
        
        assert exc_info.value.code == JSONRPCErrorCode.METHOD_NOT_FOUND
    
    @pytest.mark.asyncio
    async def test_initialization_required(self):
        """Test that methods require initialization."""
        router = MethodRouter(create_default_registry())
        
        # Try to call a method that requires initialization
        request = MCPRequest(method=MCPMethod.RESOURCES_LIST.value)
        
        with pytest.raises(JSONRPCError) as exc_info:
            await router.route(request)
        
        assert exc_info.value.code == JSONRPCErrorCode.SERVER_NOT_INITIALIZED
    
    @pytest.mark.asyncio
    async def test_initialize_sets_state(self):
        """Test that initialize method sets initialization state."""
        router = MethodRouter(create_default_registry())
        
        assert not router.registry.is_initialized()
        
        request = MCPRequest(
            method=MCPMethod.INITIALIZE.value,
            params={
                "protocolVersion": "1.0",
                "capabilities": {}
            }
        )
        response = await router.route(request)
        
        assert router.registry.is_initialized()
        assert response.result["protocolVersion"] == "1.0"
    
    @pytest.mark.asyncio
    async def test_invalid_params(self):
        """Test error with invalid parameters."""
        router = MethodRouter(create_default_registry())
        
        # Initialize first
        await router.route(MCPRequest(
            method=MCPMethod.INITIALIZE.value,
            params={"protocolVersion": "1.0", "capabilities": {}}
        ))
        
        # Call with missing required param
        request = MCPRequest(
            method=MCPMethod.RESOURCES_READ.value,
            params={}  # Missing 'uri'
        )
        
        with pytest.raises(JSONRPCError) as exc_info:
            await router.route(request)
        
        assert exc_info.value.code == JSONRPCErrorCode.INVALID_PARAMS


class TestDefaultHandlers:
    """Test the default MCP method handlers."""
    
    @pytest.mark.asyncio
    async def test_ping_handler(self):
        """Test the ping handler."""
        router = MethodRouter(create_default_registry())
        
        request = MCPRequest(method=MCPMethod.PING.value)
        response = await router.route(request)
        
        assert response.result == {"pong": True}
    
    @pytest.mark.asyncio
    async def test_shutdown_handler(self):
        """Test the shutdown handler."""
        router = MethodRouter(create_default_registry())
        
        request = MCPRequest(method=MCPMethod.SHUTDOWN.value)
        response = await router.route(request)
        
        assert response.result == {"status": "ok"}
    
    @pytest.mark.asyncio
    async def test_resources_list_handler(self):
        """Test the resources/list handler."""
        router = MethodRouter(create_default_registry())
        
        # Initialize first
        await router.route(MCPRequest(
            method=MCPMethod.INITIALIZE.value,
            params={"protocolVersion": "1.0", "capabilities": {}}
        ))
        
        request = MCPRequest(method=MCPMethod.RESOURCES_LIST.value)
        response = await router.route(request)
        
        assert response.result == {"resources": []}
    
    @pytest.mark.asyncio
    async def test_tools_list_handler(self):
        """Test the tools/list handler."""
        router = MethodRouter(create_default_registry())
        
        # Initialize first
        await router.route(MCPRequest(
            method=MCPMethod.INITIALIZE.value,
            params={"protocolVersion": "1.0", "capabilities": {}}
        ))
        
        request = MCPRequest(method=MCPMethod.TOOLS_LIST.value)
        response = await router.route(request)
        
        assert response.result == {"tools": []}
    
    @pytest.mark.asyncio
    async def test_prompts_list_handler(self):
        """Test the prompts/list handler."""
        router = MethodRouter(create_default_registry())
        
        # Initialize first
        await router.route(MCPRequest(
            method=MCPMethod.INITIALIZE.value,
            params={"protocolVersion": "1.0", "capabilities": {}}
        ))
        
        request = MCPRequest(method=MCPMethod.PROMPTS_LIST.value)
        response = await router.route(request)
        
        assert response.result == {"prompts": []}


class TestJSONRPCIntegration:
    """Test JSON-RPC integration with MCP methods."""
    
    @pytest.mark.asyncio
    async def test_process_single_request(self):
        """Test processing a single JSON-RPC request."""
        handler = create_mcp_jsonrpc_handler()
        
        request_data = {
            "jsonrpc": "2.0",
            "method": "ping",
            "id": 1
        }
        
        response = await process_mcp_request(handler, request_data)
        assert response is not None
        
        response_data = json.loads(response)
        assert response_data["id"] == 1
        assert response_data["result"] == {"pong": True}
    
    @pytest.mark.asyncio
    async def test_process_batch_request(self):
        """Test processing a batch JSON-RPC request."""
        handler = create_mcp_jsonrpc_handler()
        
        batch_request = [
            {"jsonrpc": "2.0", "method": "ping", "id": 1},
            {"jsonrpc": "2.0", "method": "ping", "id": 2}
        ]
        
        response = await process_mcp_request(handler, batch_request)
        assert response is not None
        
        response_data = json.loads(response)
        assert len(response_data) == 2
        assert all(r["result"] == {"pong": True} for r in response_data)
    
    @pytest.mark.asyncio
    async def test_process_notification(self):
        """Test processing a notification (no response expected)."""
        handler = create_mcp_jsonrpc_handler()
        
        notification = {
            "jsonrpc": "2.0",
            "method": "ping"
            # No ID means this is a notification
        }
        
        response = await process_mcp_request(handler, notification)
        assert response is None
    
    @pytest.mark.asyncio
    async def test_custom_registry_integration(self):
        """Test using a custom registry with JSON-RPC handler."""
        registry = MethodRegistry()
        
        async def custom_method(value: int) -> Dict[str, Any]:
            return {"doubled": value * 2}
        
        registry.register(
            "custom/double",
            custom_method,
            requires_initialization=False
        )
        
        handler = create_mcp_jsonrpc_handler(registry)
        
        request_data = {
            "jsonrpc": "2.0",
            "method": "custom/double",
            "params": {"value": 21},
            "id": 1
        }
        
        response = await process_mcp_request(handler, request_data)
        response_data = json.loads(response)
        
        assert response_data["result"] == {"doubled": 42}