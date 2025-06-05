"""
Comprehensive tests for Phase 4 advanced MCP features.

Tests prompts, performance optimization, advanced protocol features, and production components.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List

# Import Phase 4 components
from mcp_server.prompts.registry import PromptRegistry, PromptTemplate, PromptArgument
from mcp_server.prompts.handlers import PromptHandler
from mcp_server.performance.connection_pool import ConnectionPool, ConnectionPoolConfig, PooledConnection
from mcp_server.performance.memory_optimizer import MemoryOptimizer, MemoryThresholds
from mcp_server.performance.rate_limiter import RateLimiter, RateLimiterConfig, RateLimitAlgorithm
from mcp_server.protocol.advanced import (
    AdvancedProtocolHandler, CompletionEngine, StreamingManager, BatchProcessor,
    SamplingConfig, CompletionRequest, BatchRequest
)
from mcp_server.production.logger import ProductionLogger, LogConfig, LogLevel
from mcp_server.production.health import HealthChecker, HealthCheck, HealthStatus
from mcp_server.production.monitoring import MonitoringSystem, MetricsCollector
from mcp_server.production.middleware import ProductionMiddleware, RequestTracker, ErrorHandler
from mcp_server.protocol.jsonrpc import JsonRpcRequest, JsonRpcResponse
from mcp_server.protocol.errors import McpError, ErrorCode


class TestPromptSystem:
    """Test the MCP prompts system."""
    
    @pytest.fixture
    def prompt_registry(self):
        return PromptRegistry()
    
    @pytest.fixture
    def prompt_handler(self, prompt_registry):
        return PromptHandler()
    
    def test_prompt_registration(self, prompt_registry):
        """Test prompt template registration."""
        template = PromptTemplate(
            name="test_prompt",
            description="Test prompt",
            prompt="Hello {name}!",
            arguments=[
                PromptArgument("name", "Name to greet")
            ]
        )
        
        prompt_registry.register_prompt(template)
        
        retrieved = prompt_registry.get_prompt("test_prompt")
        assert retrieved is not None
        assert retrieved.name == "test_prompt"
        assert retrieved.description == "Test prompt"
    
    @pytest.mark.asyncio
    async def test_prompt_generation(self, prompt_registry):
        """Test prompt generation with arguments."""
        template = PromptTemplate(
            name="greeting",
            description="Generate greeting",
            prompt="Hello {name}, welcome to {place}!",
            arguments=[
                PromptArgument("name", "Name to greet"),
                PromptArgument("place", "Place to welcome to")
            ]
        )
        
        prompt_registry.register_prompt(template)
        
        result = await prompt_registry.generate_prompt(
            "greeting",
            {"name": "Alice", "place": "MCP Server"}
        )
        
        assert result == "Hello Alice, welcome to MCP Server!"
    
    @pytest.mark.asyncio
    async def test_prompt_handler_list(self, prompt_handler):
        """Test listing prompts through handler."""
        result = await prompt_handler.list_prompts()
        
        assert "prompts" in result
        assert isinstance(result["prompts"], list)
        # Should have built-in prompts
        assert len(result["prompts"]) > 0
    
    @pytest.mark.asyncio
    async def test_prompt_handler_get(self, prompt_handler):
        """Test getting prompt through handler."""
        # Use a built-in prompt
        result = await prompt_handler.get_prompt({
            "name": "code_review",
            "arguments": {
                "file_path": "test.py",
                "language": "python",
                "code": "def hello(): pass"
            }
        })
        
        assert "description" in result
        assert "messages" in result
        assert len(result["messages"]) > 0
    
    def test_prompt_search(self, prompt_registry):
        """Test searching prompts."""
        matches = prompt_registry.search_prompts("review")
        assert "code_review" in matches
    
    def test_prompt_categories(self, prompt_registry):
        """Test getting prompt categories."""
        categories = prompt_registry.get_categories()
        assert isinstance(categories, list)
        assert len(categories) > 0


class TestPerformanceOptimization:
    """Test performance optimization components."""
    
    @pytest.mark.asyncio
    async def test_memory_optimizer(self):
        """Test memory monitoring and optimization."""
        optimizer = MemoryOptimizer()
        
        # Get current stats
        stats = await optimizer.get_memory_stats()
        assert stats.process_memory_mb > 0
        assert stats.total_memory_mb > 0
        
        # Test garbage collection
        collected = await optimizer.force_garbage_collection()
        assert isinstance(collected, dict)
        
        # Test optimization
        result = await optimizer.optimize_memory()
        assert "initial_memory_mb" in result
        assert "final_memory_mb" in result
    
    @pytest.mark.asyncio
    async def test_rate_limiter_token_bucket(self):
        """Test token bucket rate limiter."""
        config = RateLimiterConfig(
            algorithm=RateLimitAlgorithm.TOKEN_BUCKET,
            max_requests=5,
            window_seconds=60.0,
            burst_limit=10
        )
        
        limiter = RateLimiter(config)
        await limiter.start()
        
        try:
            # First few requests should be allowed
            for i in range(5):
                result = await limiter.check_limit(f"user_{i}")
                assert result.allowed
                assert result.remaining >= 0
            
            # Check rate limiting behavior
            result = await limiter.check_limit("heavy_user")
            # Should still be allowed due to burst limit
            assert result.allowed
            
        finally:
            await limiter.stop()
    
    @pytest.mark.asyncio
    async def test_rate_limiter_sliding_window(self):
        """Test sliding window rate limiter."""
        config = RateLimiterConfig(
            algorithm=RateLimitAlgorithm.SLIDING_WINDOW,
            max_requests=3,
            window_seconds=1.0  # Short window for testing
        )
        
        limiter = RateLimiter(config)
        await limiter.start()
        
        try:
            user_id = "test_user"
            
            # First 3 requests should be allowed
            for i in range(3):
                result = await limiter.check_limit(user_id)
                assert result.allowed
            
            # 4th request should be rate limited
            result = await limiter.check_limit(user_id)
            assert not result.allowed
            assert result.retry_after is not None
            
        finally:
            await limiter.stop()


class TestAdvancedProtocol:
    """Test advanced protocol features."""
    
    @pytest.fixture
    def completion_engine(self):
        return CompletionEngine()
    
    @pytest.fixture
    def streaming_manager(self):
        return StreamingManager()
    
    @pytest.fixture
    def advanced_handler(self):
        mock_handler = AsyncMock()
        return AdvancedProtocolHandler(mock_handler)
    
    @pytest.mark.asyncio
    async def test_completion_engine(self, completion_engine):
        """Test text completion engine."""
        request = CompletionRequest(
            prompt="def hello_world():",
            model="template",
            sampling=SamplingConfig(temperature=0.7)
        )
        
        response = await completion_engine.complete(request)
        
        assert response.id is not None
        assert len(response.choices) > 0
        assert response.choices[0].text is not None
        assert response.model == "template"
    
    @pytest.mark.asyncio
    async def test_streaming_completion(self, completion_engine):
        """Test streaming completion."""
        request = CompletionRequest(
            prompt="Generate a function",
            model="echo",
            stream=True
        )
        
        chunks = []
        async for chunk in completion_engine.stream_complete(request):
            chunks.append(chunk)
            if chunk.is_final:
                break
        
        assert len(chunks) > 0
        assert chunks[-1].is_final
        assert all(chunk.chunk_type == "text" for chunk in chunks[:-1] if not chunk.is_final)
    
    @pytest.mark.asyncio
    async def test_batch_processing(self, advanced_handler):
        """Test batch request processing."""
        # Mock handler for batch processor
        async def mock_handler(request):
            return JsonRpcResponse(
                id=request.id,
                result={"method": request.method, "success": True}
            )
        
        processor = BatchProcessor(mock_handler)
        
        # Create batch request
        batch = BatchRequest(
            id="test_batch",
            requests=[
                JsonRpcRequest(id=1, method="test1", params={}),
                JsonRpcRequest(id=2, method="test2", params={}),
                JsonRpcRequest(id=3, method="test3", params={})
            ],
            parallel=True
        )
        
        response = await processor.process_batch(batch)
        
        assert response.id == "test_batch"
        assert len(response.responses) == 3
        assert response.completed == 3
        assert response.failed == 0
    
    @pytest.mark.asyncio
    async def test_streaming_manager(self, streaming_manager):
        """Test streaming manager."""
        # Register a test stream handler
        async def test_stream_handler(params):
            for i in range(3):
                yield {
                    "id": f"chunk_{i}",
                    "chunk_type": "data",
                    "data": f"chunk {i}",
                    "index": i,
                    "is_final": i == 2
                }
        
        streaming_manager.register_stream_handler("test", test_stream_handler)
        
        # Start stream
        stream_id = "test_stream"
        await streaming_manager.start_stream(stream_id, "test", {})
        
        # Read chunks
        chunks = []
        while True:
            chunk = await streaming_manager.get_stream_chunk(stream_id)
            if chunk is None:
                break
            chunks.append(chunk)
        
        assert len(chunks) == 3
        assert chunks[-1]["is_final"]


class TestProductionFeatures:
    """Test production features."""
    
    @pytest.fixture
    def production_logger(self):
        config = LogConfig(
            level=LogLevel.INFO,
            enable_console=False,
            enable_file=False  # Don't write files in tests
        )
        logger = ProductionLogger(config)
        return logger
    
    @pytest.fixture
    def health_checker(self):
        return HealthChecker()
    
    @pytest.fixture
    def monitoring_system(self):
        return MonitoringSystem()
    
    @pytest.fixture
    def middleware(self):
        return ProductionMiddleware()
    
    def test_structured_logging(self, production_logger):
        """Test structured logging."""
        logger_instance = production_logger.get_logger("test")
        
        # Test context setting
        logger_instance.set_context(user_id="test_user", session_id="test_session")
        
        # Test context logger
        context_logger = logger_instance.with_context(request_id="test_request")
        
        # These should not raise exceptions
        logger_instance.info("Test message")
        context_logger.info("Context message")
        logger_instance.error("Error message", error=Exception("test error"))
    
    @pytest.mark.asyncio
    async def test_health_checker(self, health_checker):
        """Test health checking system."""
        # Add a simple health check
        class TestHealthCheck(HealthCheck):
            def __init__(self):
                super().__init__("test_check", timeout=1.0, critical=False)
            
            async def check(self):
                # Always pass
                pass
        
        health_checker.register_check(TestHealthCheck())
        
        # Run checks
        report = await health_checker.run_checks()
        
        assert report.overall_status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]
        assert len(report.checks) > 0
        
        # Test getting specific check status
        status = health_checker.get_check_status("test_check")
        assert status is not None
    
    @pytest.mark.asyncio
    async def test_metrics_collector(self, monitoring_system):
        """Test metrics collection."""
        metrics = monitoring_system.metrics
        
        # Test counter
        await metrics.counter("test_counter", 1.0, {"type": "test"})
        
        # Test gauge
        await metrics.gauge("test_gauge", 42.0, {"unit": "count"})
        
        # Test histogram
        await metrics.histogram("test_histogram", 1.5, {"operation": "test"})
        
        # Test timer
        await metrics.timer("test_timer", 0.1, {"endpoint": "test"})
        
        # Get all metrics
        all_metrics = await metrics.get_metrics()
        
        assert len(all_metrics) > 0
        
        # Check specific metrics exist
        metric_names = [metric.name for metric in all_metrics.values()]
        assert "test_counter" in metric_names
        assert "test_gauge" in metric_names
    
    @pytest.mark.asyncio
    async def test_request_tracking(self, middleware):
        """Test request tracking in middleware."""
        tracker = middleware.request_tracker
        
        # Create a mock request
        request = JsonRpcRequest(id=1, method="test_method", params={"key": "value"})
        
        # Start tracking
        context = tracker.start_request(request, {"user_id": "test_user"})
        
        assert context.request_id is not None
        assert context.method == "test_method"
        assert context.user_id == "test_user"
        
        # Check active requests
        active = tracker.get_active_requests()
        assert len(active) == 1
        assert active[0].request_id == context.request_id
        
        # End tracking
        ended_context = tracker.end_request(context.request_id)
        assert ended_context is not None
        
        # Check no longer active
        active = tracker.get_active_requests()
        assert len(active) == 0
    
    @pytest.mark.asyncio
    async def test_error_handling(self, middleware):
        """Test error handling in middleware."""
        error_handler = middleware.error_handler
        
        # Create mock context
        from mcp_server.production.middleware import RequestContext
        context = RequestContext(
            request_id="test_request",
            method="test_method",
            user_id="test_user"
        )
        
        # Create mock request
        request = JsonRpcRequest(id=1, method="test_method", params={})
        
        # Test error handling
        test_error = ValueError("Test error")
        response = error_handler.handle_error(test_error, context, request)
        
        assert response is not None
        assert response.id == 1
        assert "error" in response.to_dict()
        
        # Check error stats
        stats = error_handler.get_error_stats()
        assert stats["total_errors"] > 0
        assert "ValueError" in stats["error_counts"]
    
    @pytest.mark.asyncio
    async def test_middleware_integration(self, middleware):
        """Test full middleware processing."""
        # Mock handler
        async def mock_handler(request):
            if request.method == "success":
                return JsonRpcResponse(id=request.id, result={"status": "ok"})
            elif request.method == "error":
                raise ValueError("Test error")
            else:
                raise NotImplementedError("Unknown method")
        
        # Test successful request
        success_request = JsonRpcRequest(id=1, method="success", params={})
        response = await middleware.process_request(
            success_request, 
            mock_handler,
            {"user_id": "test_user"}
        )
        
        assert response is not None
        assert response.id == 1
        assert "result" in response.to_dict()
        
        # Test error request
        error_request = JsonRpcRequest(id=2, method="error", params={})
        response = await middleware.process_request(
            error_request,
            mock_handler,
            {"user_id": "test_user"}
        )
        
        assert response is not None
        assert response.id == 2
        assert "error" in response.to_dict()


class TestIntegration:
    """Integration tests for Phase 4 components."""
    
    @pytest.mark.asyncio
    async def test_server_initialization(self):
        """Test that all components can be initialized together."""
        from mcp_server.stdio_server import StdioMCPServer
        
        # Create server with test settings
        server = StdioMCPServer()
        # Note: StdioMCPServer doesn't have settings attribute like MCPServer
        # Settings are managed through config/enhanced_settings
        
        try:
            # Initialize components
            await server.initialize()
            
            # Verify components are initialized
            assert server.session_manager is not None
            assert server.tool_manager is not None
            assert server.resource_manager is not None
            assert server.cache_manager is not None
            
        finally:
            # Clean up
            await server.shutdown()
    
    @pytest.mark.asyncio
    async def test_end_to_end_request_processing(self):
        """Test end-to-end request processing through all layers."""
        from mcp_server.stdio_server import StdioMCPServer
        
        server = StdioMCPServer()
        # Note: StdioMCPServer uses enhanced_settings for configuration
        
        try:
            await server.initialize()
            
            # Test a simple request
            request_data = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list",
                "params": {}
            }
            
            response = await server._handle_message(request_data)
            
            assert response is not None
            assert "jsonrpc" in response
            assert response["id"] == 1
            
        finally:
            await server.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])