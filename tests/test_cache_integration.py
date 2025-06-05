"""
Tests for cache integration.
"""
import os
import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from mcp_server.features.cache_integration import CacheIntegration
from mcp_server.cache.cache_manager import CacheManager


class TestCacheIntegration:
    """Test cache integration with server."""
    
    @pytest.fixture
    async def cache_integration(self):
        """Create cache integration instance."""
        server_mock = Mock()
        server_mock.tool_manager = Mock()
        server_mock.tool_manager.get_handler = Mock()
        
        integration = CacheIntegration(server_mock)
        # Enable cache for testing
        integration.enabled = True
        yield integration
        await integration.shutdown()
    
    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test cache integration initialization."""
        server_mock = Mock()
        integration = CacheIntegration(server_mock)
        
        assert not integration.enabled
        assert integration.cache_manager is None
        
        # Enable and initialize
        with patch.dict(os.environ, {'MCP_ENABLE_CACHE': 'true'}):
            integration = CacheIntegration(server_mock)
            await integration.initialize()
            
            assert integration.enabled
            assert integration.cache_manager is not None
    
    @pytest.mark.asyncio
    async def test_tool_wrapping(self, cache_integration):
        """Test wrapping of tool handlers."""
        # Mock tool handlers
        original_handlers = {
            'search_code': AsyncMock(return_value={'results': ['test']}),
            'lookup_symbol': AsyncMock(return_value={'symbol': 'TestClass'}),
            'find_references': AsyncMock(return_value={'refs': []}),
        }
        
        cache_integration.server.tool_manager.get_handler.side_effect = \
            lambda name: original_handlers.get(name)
        
        # Apply cache wrapping
        cache_integration._apply_cache_to_tools()
        
        # Verify handlers were wrapped
        assert cache_integration.server.tool_manager.register_handler.call_count >= 3
    
    @pytest.mark.asyncio
    async def test_cache_hit(self, cache_integration):
        """Test cache hit scenario."""
        # Setup
        params = {'query': 'test_function', 'path': '/test'}
        cached_result = {'results': ['cached_result']}
        
        # Mock cache manager
        cache_integration.cache_manager = AsyncMock()
        cache_integration.cache_manager.get = AsyncMock(return_value=cached_result)
        
        # Create wrapped handler
        original_handler = AsyncMock()
        wrapped = cache_integration._cache_search_code(original_handler)
        
        # Call wrapped handler
        result = await wrapped(params)
        
        # Verify cache was checked and original not called
        assert result == cached_result
        cache_integration.cache_manager.get.assert_called_once()
        original_handler.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_cache_miss(self, cache_integration):
        """Test cache miss scenario."""
        # Setup
        params = {'query': 'test_function', 'path': '/test'}
        fresh_result = {'results': ['fresh_result']}
        
        # Mock cache manager
        cache_integration.cache_manager = AsyncMock()
        cache_integration.cache_manager.get = AsyncMock(return_value=None)
        cache_integration.cache_manager.set = AsyncMock()
        
        # Create wrapped handler
        original_handler = AsyncMock(return_value=fresh_result)
        wrapped = cache_integration._cache_search_code(original_handler)
        
        # Call wrapped handler
        result = await wrapped(params)
        
        # Verify original was called and result cached
        assert result == fresh_result
        cache_integration.cache_manager.get.assert_called_once()
        original_handler.assert_called_once_with(params)
        cache_integration.cache_manager.set.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cache_invalidation_on_index(self, cache_integration):
        """Test cache invalidation when indexing."""
        # Mock cache manager
        cache_integration.cache_manager = AsyncMock()
        cache_integration.cache_manager.clear = AsyncMock()
        
        # Simulate index file completion
        await cache_integration.on_index_complete('/test/file.py')
        
        # Verify cache was cleared
        cache_integration.cache_manager.clear.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cache_error_handling(self, cache_integration):
        """Test error handling in cache operations."""
        # Setup
        params = {'query': 'test'}
        expected_result = {'results': ['result']}
        
        # Mock cache manager that throws error
        cache_integration.cache_manager = AsyncMock()
        cache_integration.cache_manager.get = AsyncMock(
            side_effect=Exception("Cache error")
        )
        
        # Create wrapped handler
        original_handler = AsyncMock(return_value=expected_result)
        wrapped = cache_integration._cache_search_code(original_handler)
        
        # Call should fall back to original handler
        result = await wrapped(params)
        
        assert result == expected_result
        original_handler.assert_called_once_with(params)
    
    @pytest.mark.asyncio
    async def test_cache_stats(self, cache_integration):
        """Test getting cache statistics."""
        # Mock cache manager stats
        expected_stats = {
            'hits': 100,
            'misses': 50,
            'size': 150,
            'hit_rate': 0.67
        }
        
        cache_integration.cache_manager = AsyncMock()
        
        # Mock the metrics object that get_metrics returns
        mock_metrics = AsyncMock()
        mock_metrics.hits = 100
        mock_metrics.misses = 50
        mock_metrics.entries_count = 150
        mock_metrics.hit_rate = 0.67
        
        cache_integration.cache_manager.get_metrics = AsyncMock(
            return_value=mock_metrics
        )
        
        stats = await cache_integration.get_cache_stats()
        
        assert stats == expected_stats
        cache_integration.cache_manager.get_metrics.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_shutdown(self):
        """Test cache integration shutdown."""
        # Create a separate instance for shutdown testing
        server_mock = Mock()
        integration = CacheIntegration(server_mock)
        integration.enabled = True
        
        # Mock cache manager
        mock_cache_manager = AsyncMock()
        mock_cache_manager.clear = AsyncMock()
        mock_cache_manager.shutdown = AsyncMock()
        integration.cache_manager = mock_cache_manager
        
        await integration.shutdown()
        
        # Verify cleanup
        mock_cache_manager.clear.assert_called_once()
        mock_cache_manager.shutdown.assert_called_once()
        
        # Verify state after shutdown
        assert not integration.enabled
        assert integration.cache_manager is None
    
    @pytest.mark.asyncio
    async def test_disabled_cache(self):
        """Test cache integration when disabled."""
        server_mock = Mock()
        server_mock.tool_manager = Mock()
        
        # Explicitly set cache to be disabled
        with patch('mcp_server.features.cache_integration.feature_manager') as mock_feature_manager:
            mock_feature_manager.initialize_from_env.return_value = None
            mock_feature_manager.is_enabled.return_value = False
            mock_feature_manager.get_config.return_value = None
            
            integration = CacheIntegration(server_mock)
            await integration.initialize()
            
            assert not integration.enabled
            assert integration.cache_manager is None
            
            # Should not wrap tools
            integration._apply_cache_to_tools()
            # Since no tools are wrapped, register_handler should not be called
            if hasattr(server_mock.tool_manager, 'register_handler'):
                server_mock.tool_manager.register_handler.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_cache_key_generation(self, cache_integration):
        """Test cache key generation."""
        # Test different parameter combinations
        test_cases = [
            ({'query': 'test'}, 'search_code'),
            ({'query': 'test', 'path': '/src'}, 'search_code'),
            ({'symbol': 'MyClass'}, 'lookup_symbol'),
            ({'symbol': 'MyClass', 'path': '/test.py'}, 'find_references'),
        ]
        
        generated_keys = set()
        
        for params, tool_name in test_cases:
            key = cache_integration._generate_cache_key(tool_name, params)
            
            # Keys should be unique
            assert key not in generated_keys
            generated_keys.add(key)
            
            # Keys should be consistent
            key2 = cache_integration._generate_cache_key(tool_name, params)
            assert key == key2
    
    @pytest.mark.asyncio
    async def test_concurrent_cache_access(self, cache_integration):
        """Test concurrent cache access."""
        # Mock cache manager
        cache_integration.cache_manager = AsyncMock()
        cache_integration.cache_manager.get = AsyncMock(return_value=None)
        cache_integration.cache_manager.set = AsyncMock()
        
        # Create wrapped handler
        call_count = 0
        async def slow_handler(params):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)  # Shorter sleep to reduce test time
            return {'result': f'result_{call_count}'}
        
        wrapped = cache_integration._cache_search_code(slow_handler)
        
        # Make concurrent calls with same params
        params = {'query': 'test'}
        tasks = [wrapped(params) for _ in range(5)]
        results = await asyncio.gather(*tasks)
        
        # Since we don't have cache coalescing, each call will execute the handler
        # But the cache manager should still be called for get/set operations
        assert call_count == 5  # All calls execute since no cache coalescing
        assert cache_integration.cache_manager.get.call_count == 5
        assert cache_integration.cache_manager.set.call_count == 5