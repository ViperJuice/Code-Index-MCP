"""Tests for JSON-RPC 2.0 protocol implementation."""

import json
import pytest
import asyncio
from mcp_server.protocol import (
    JSONRPCRequest,
    JSONRPCResponse,
    JSONRPCError,
    JSONRPCErrorCode,
    JSONRPCParser,
    JSONRPCSerializer,
    JSONRPCHandler,
)


class TestJSONRPCRequest:
    """Test JSONRPCRequest class."""
    
    def test_create_request(self):
        """Test creating a valid request."""
        req = JSONRPCRequest(method="test_method", params={"key": "value"}, id=1)
        assert req.method == "test_method"
        assert req.params == {"key": "value"}
        assert req.id == 1
        assert req.jsonrpc == "2.0"
    
    def test_notification(self):
        """Test notification request (no ID)."""
        req = JSONRPCRequest(method="notify")
        assert req.is_notification
        assert req.id is None
    
    def test_invalid_method(self):
        """Test invalid method raises error."""
        with pytest.raises(JSONRPCError) as exc_info:
            JSONRPCRequest(method="")
        assert exc_info.value.code == JSONRPCErrorCode.INVALID_REQUEST
    
    def test_invalid_params(self):
        """Test invalid params raises error."""
        with pytest.raises(JSONRPCError) as exc_info:
            JSONRPCRequest(method="test", params="invalid")
        assert exc_info.value.code == JSONRPCErrorCode.INVALID_REQUEST
    
    def test_to_dict(self):
        """Test converting request to dictionary."""
        req = JSONRPCRequest(method="test", params=[1, 2, 3], id="abc")
        d = req.to_dict()
        assert d == {
            "jsonrpc": "2.0",
            "method": "test",
            "params": [1, 2, 3],
            "id": "abc"
        }


class TestJSONRPCResponse:
    """Test JSONRPCResponse class."""
    
    def test_success_response(self):
        """Test creating a successful response."""
        resp = JSONRPCResponse.success(id=1, result={"data": "test"})
        assert resp.id == 1
        assert resp.result == {"data": "test"}
        assert resp.error is None
    
    def test_error_response(self):
        """Test creating an error response."""
        error = JSONRPCError(JSONRPCErrorCode.METHOD_NOT_FOUND, "Method not found")
        resp = JSONRPCResponse.error_response(id=2, error=error)
        assert resp.id == 2
        assert resp.result is None
        assert resp.error == error
    
    def test_invalid_response(self):
        """Test response must have either result or error."""
        with pytest.raises(ValueError):
            JSONRPCResponse(id=1)
    
    def test_to_dict(self):
        """Test converting response to dictionary."""
        # Success response
        resp = JSONRPCResponse.success(id=1, result="ok")
        d = resp.to_dict()
        assert d == {
            "jsonrpc": "2.0",
            "id": 1,
            "result": "ok"
        }
        
        # Error response
        error = JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "Invalid params")
        resp = JSONRPCResponse.error_response(id=2, error=error)
        d = resp.to_dict()
        assert d == {
            "jsonrpc": "2.0",
            "id": 2,
            "error": {
                "code": -32602,
                "message": "Invalid params"
            }
        }


class TestJSONRPCParser:
    """Test JSONRPCParser class."""
    
    def test_parse_request_from_string(self):
        """Test parsing request from JSON string."""
        json_str = '{"jsonrpc":"2.0","method":"test","params":[1,2],"id":1}'
        req = JSONRPCParser.parse_request(json_str)
        assert isinstance(req, JSONRPCRequest)
        assert req.method == "test"
        assert req.params == [1, 2]
        assert req.id == 1
    
    def test_parse_request_from_dict(self):
        """Test parsing request from dictionary."""
        data = {"jsonrpc": "2.0", "method": "test", "id": "abc"}
        req = JSONRPCParser.parse_request(data)
        assert isinstance(req, JSONRPCRequest)
        assert req.method == "test"
        assert req.id == "abc"
    
    def test_parse_batch_request(self):
        """Test parsing batch request."""
        json_str = '[{"jsonrpc":"2.0","method":"test1","id":1},{"jsonrpc":"2.0","method":"test2","id":2}]'
        reqs = JSONRPCParser.parse_request(json_str)
        assert isinstance(reqs, list)
        assert len(reqs) == 2
        assert reqs[0].method == "test1"
        assert reqs[1].method == "test2"
    
    def test_parse_invalid_json(self):
        """Test parsing invalid JSON raises error."""
        with pytest.raises(JSONRPCError) as exc_info:
            JSONRPCParser.parse_request("{invalid json")
        assert exc_info.value.code == JSONRPCErrorCode.PARSE_ERROR
    
    def test_parse_invalid_version(self):
        """Test parsing request with wrong version."""
        data = {"jsonrpc": "1.0", "method": "test", "id": 1}
        with pytest.raises(JSONRPCError) as exc_info:
            JSONRPCParser.parse_request(data)
        assert exc_info.value.code == JSONRPCErrorCode.INVALID_REQUEST
    
    def test_parse_response(self):
        """Test parsing response."""
        json_str = '{"jsonrpc":"2.0","result":"ok","id":1}'
        resp = JSONRPCParser.parse_response(json_str)
        assert isinstance(resp, JSONRPCResponse)
        assert resp.result == "ok"
        assert resp.id == 1


class TestJSONRPCSerializer:
    """Test JSONRPCSerializer class."""
    
    def test_serialize_request(self):
        """Test serializing request."""
        req = JSONRPCRequest(method="test", params={"a": 1}, id=1)
        json_str = JSONRPCSerializer.serialize_request(req)
        parsed = json.loads(json_str)
        assert parsed == {
            "jsonrpc": "2.0",
            "method": "test",
            "params": {"a": 1},
            "id": 1
        }
    
    def test_serialize_batch_request(self):
        """Test serializing batch request."""
        reqs = [
            JSONRPCRequest(method="test1", id=1),
            JSONRPCRequest(method="test2", id=2)
        ]
        json_str = JSONRPCSerializer.serialize_request(reqs)
        parsed = json.loads(json_str)
        assert len(parsed) == 2
        assert parsed[0]["method"] == "test1"
        assert parsed[1]["method"] == "test2"
    
    def test_serialize_response(self):
        """Test serializing response."""
        resp = JSONRPCResponse.success(id=1, result="ok")
        json_str = JSONRPCSerializer.serialize_response(resp)
        parsed = json.loads(json_str)
        assert parsed == {
            "jsonrpc": "2.0",
            "id": 1,
            "result": "ok"
        }


class TestJSONRPCHandler:
    """Test JSONRPCHandler class."""
    
    @pytest.mark.asyncio
    async def test_register_and_call_method(self):
        """Test registering and calling a method."""
        handler = JSONRPCHandler()
        
        async def test_method(a, b):
            return a + b
        
        handler.register_method("add", test_method)
        
        req = JSONRPCRequest(method="add", params=[5, 3], id=1)
        resp = await handler.handle_request(req)
        
        assert resp.id == 1
        assert resp.result == 8
        assert resp.error is None
    
    @pytest.mark.asyncio
    async def test_method_not_found(self):
        """Test calling non-existent method."""
        handler = JSONRPCHandler()
        
        req = JSONRPCRequest(method="unknown", id=1)
        resp = await handler.handle_request(req)
        
        assert resp.id == 1
        assert resp.result is None
        assert resp.error.code == JSONRPCErrorCode.METHOD_NOT_FOUND
    
    @pytest.mark.asyncio
    async def test_notification(self):
        """Test handling notification (no response)."""
        handler = JSONRPCHandler()
        
        called = False
        async def notify_method():
            nonlocal called
            called = True
        
        handler.register_method("notify", notify_method)
        
        req = JSONRPCRequest(method="notify")  # No ID = notification
        resp = await handler.handle_request(req)
        
        assert resp is None
        assert called
    
    @pytest.mark.asyncio
    async def test_batch_request(self):
        """Test handling batch request."""
        handler = JSONRPCHandler()
        
        async def add(a, b):
            return a + b
        
        async def multiply(a, b):
            return a * b
        
        handler.register_method("add", add)
        handler.register_method("multiply", multiply)
        
        reqs = [
            JSONRPCRequest(method="add", params=[2, 3], id=1),
            JSONRPCRequest(method="multiply", params=[4, 5], id=2),
            JSONRPCRequest(method="notify"),  # Notification, no response
        ]
        
        resps = await handler.handle_request(reqs)
        
        assert len(resps) == 2  # Only 2 responses (notification excluded)
        assert resps[0].id == 1
        assert resps[0].result == 5
        assert resps[1].id == 2
        assert resps[1].result == 20
    
    @pytest.mark.asyncio
    async def test_dict_params(self):
        """Test method with dictionary parameters."""
        handler = JSONRPCHandler()
        
        async def greet(name, greeting="Hello"):
            return f"{greeting}, {name}!"
        
        handler.register_method("greet", greet)
        
        req = JSONRPCRequest(
            method="greet",
            params={"name": "World", "greeting": "Hi"},
            id=1
        )
        resp = await handler.handle_request(req)
        
        assert resp.result == "Hi, World!"
    
    @pytest.mark.asyncio
    async def test_invalid_params(self):
        """Test calling method with invalid parameters."""
        handler = JSONRPCHandler()
        
        async def strict_method(a: int, b: int):
            return a + b
        
        handler.register_method("strict", strict_method)
        
        # Wrong number of params
        req = JSONRPCRequest(method="strict", params=[1], id=1)
        resp = await handler.handle_request(req)
        
        assert resp.error.code == JSONRPCErrorCode.INVALID_PARAMS