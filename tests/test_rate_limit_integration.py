"""
Tests for rate limiting integration.
"""
import os
import asyncio
import time
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from mcp_server.features.rate_limit_integration import RateLimiter


class TestRateLimiter:
    """Test rate limiting integration."""
    
    @pytest.fixture
    async def rate_limiter(self):
        """Create rate limiter instance."""
        server_mock = Mock()
        
        with patch.dict(os.environ, {
            'MCP_ENABLE_RATE_LIMIT': 'true',
            'MCP_RATE_LIMIT_REQUESTS': '10',
            'MCP_RATE_LIMIT_WINDOW': '1'  # 1 second window
        }):
            limiter = RateLimiter(server_mock)
            await limiter.initialize()
            yield limiter
            await limiter.shutdown()
    
    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test rate limiter initialization."""
        server_mock = Mock()
        limiter = RateLimiter(server_mock)
        
        assert not limiter.enabled
        assert limiter._max_requests == 100  # default
        
        # Enable and initialize
        with patch.dict(os.environ, {
            'MCP_ENABLE_RATE_LIMIT': 'true',
            'MCP_RATE_LIMIT_REQUESTS': '50'
        }):
            limiter = RateLimiter(server_mock)
            await limiter.initialize()
            
            assert limiter.enabled
            assert limiter._max_requests == 50
    
    @pytest.mark.asyncio
    async def test_check_rate_limit_allowed(self, rate_limiter):
        """Test rate limit allows requests under limit."""
        client_id = 'test_client'
        
        # First few requests should be allowed
        for i in range(5):
            allowed = await rate_limiter.check_rate_limit(client_id)
            assert allowed is True
    
    @pytest.mark.asyncio
    async def test_check_rate_limit_exceeded(self, rate_limiter):
        """Test rate limit blocks requests over limit."""
        client_id = 'test_client'
        
        # Make requests up to limit
        for i in range(10):
            await rate_limiter.check_rate_limit(client_id)
        
        # Next request should be blocked
        allowed = await rate_limiter.check_rate_limit(client_id)
        assert allowed is False
    
    @pytest.mark.asyncio
    async def test_rate_limit_window_reset(self, rate_limiter):
        """Test rate limit resets after window."""
        client_id = 'test_client'
        rate_limiter._window_seconds = 0.1  # Short window for testing
        
        # Exhaust limit
        for i in range(10):
            await rate_limiter.check_rate_limit(client_id)
        
        # Should be blocked
        assert await rate_limiter.check_rate_limit(client_id) is False
        
        # Wait for window to reset
        await asyncio.sleep(0.2)
        
        # Should be allowed again
        assert await rate_limiter.check_rate_limit(client_id) is True
    
    @pytest.mark.asyncio
    async def test_multiple_clients(self, rate_limiter):
        """Test rate limiting tracks multiple clients independently."""
        client1 = 'client1'
        client2 = 'client2'
        
        # Exhaust limit for client1
        for i in range(10):
            await rate_limiter.check_rate_limit(client1)
        
        # Client1 should be blocked
        assert await rate_limiter.check_rate_limit(client1) is False
        
        # Client2 should still be allowed
        assert await rate_limiter.check_rate_limit(client2) is True
    
    @pytest.mark.asyncio
    async def test_sliding_window(self, rate_limiter):
        """Test sliding window implementation."""
        client_id = 'test_client'
        rate_limiter._window_seconds = 1.0
        
        # Make 5 requests
        for i in range(5):
            await rate_limiter.check_rate_limit(client_id)
        
        # Wait half window
        await asyncio.sleep(0.5)
        
        # Make 5 more requests
        for i in range(5):
            await rate_limiter.check_rate_limit(client_id)
        
        # Should be at limit but not over
        assert await rate_limiter.check_rate_limit(client_id) is False
        
        # Wait for first requests to expire
        await asyncio.sleep(0.6)
        
        # Should be allowed again
        assert await rate_limiter.check_rate_limit(client_id) is True
    
    @pytest.mark.asyncio
    async def test_get_rate_limit_stats(self, rate_limiter):
        """Test getting rate limit statistics."""
        # Generate some activity
        await rate_limiter.check_rate_limit('client1')
        await rate_limiter.check_rate_limit('client1')
        await rate_limiter.check_rate_limit('client2')
        
        stats = await rate_limiter.get_rate_limit_stats()
        
        assert 'total_requests' in stats
        assert stats['total_requests'] == 3
        assert 'unique_clients' in stats
        assert stats['unique_clients'] == 2
        assert 'blocked_requests' in stats
    
    @pytest.mark.asyncio
    async def test_cleanup_old_entries(self, rate_limiter):
        """Test cleanup of old request entries."""
        client_id = 'test_client'
        rate_limiter._window_seconds = 0.1
        
        # Make some requests
        for i in range(5):
            await rate_limiter.check_rate_limit(client_id)
        
        # Wait for them to expire
        await asyncio.sleep(0.2)
        
        # Trigger cleanup
        await rate_limiter._cleanup_old_requests()
        
        # Old requests should be removed
        assert len(rate_limiter._request_history.get(client_id, [])) == 0
    
    @pytest.mark.asyncio
    async def test_wrapper_function(self, rate_limiter):
        """Test rate limit wrapper for handlers."""
        # Mock handler
        async def test_handler(request):
            return {'result': 'success'}
        
        # Wrap handler
        wrapped = rate_limiter.wrap_handler(test_handler)
        
        # Create request with client info
        request = Mock()
        request.client_id = 'test_client'
        
        # Should work under limit
        result = await wrapped(request)
        assert result == {'result': 'success'}
        
        # Exhaust limit
        for i in range(10):
            await rate_limiter.check_rate_limit('test_client')
        
        # Should raise rate limit error
        with pytest.raises(Exception) as exc_info:
            await wrapped(request)
        assert 'rate limit' in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_burst_handling(self, rate_limiter):
        """Test handling of burst requests."""
        client_id = 'burst_client'
        
        # Send burst of concurrent requests
        tasks = []
        for i in range(15):  # More than limit
            tasks.append(rate_limiter.check_rate_limit(client_id))
        
        results = await asyncio.gather(*tasks)
        
        # First 10 should be allowed
        allowed_count = sum(1 for r in results if r is True)
        assert allowed_count == 10
        
        # Rest should be blocked
        blocked_count = sum(1 for r in results if r is False)
        assert blocked_count == 5
    
    @pytest.mark.asyncio
    async def test_disabled_rate_limiter(self):
        """Test rate limiter when disabled."""
        server_mock = Mock()
        
        with patch.dict(os.environ, {'MCP_ENABLE_RATE_LIMIT': 'false'}):
            limiter = RateLimiter(server_mock)
            await limiter.initialize()
            
            assert not limiter.enabled
            
            # Should always allow requests
            for i in range(100):
                allowed = await limiter.check_rate_limit('client')
                assert allowed is True
    
    @pytest.mark.asyncio
    async def test_whitelist_functionality(self, rate_limiter):
        """Test whitelisting clients from rate limits."""
        # Add to whitelist
        rate_limiter.add_to_whitelist('special_client')
        
        # Should never be rate limited
        for i in range(100):
            allowed = await rate_limiter.check_rate_limit('special_client')
            assert allowed is True
    
    @pytest.mark.asyncio
    async def test_custom_limits_per_client(self, rate_limiter):
        """Test custom rate limits for specific clients."""
        # Set custom limit
        rate_limiter.set_custom_limit('premium_client', 50)
        
        # Should allow up to custom limit
        for i in range(50):
            allowed = await rate_limiter.check_rate_limit('premium_client')
            assert allowed is True
        
        # Should block after custom limit
        allowed = await rate_limiter.check_rate_limit('premium_client')
        assert allowed is False
    
    @pytest.mark.asyncio
    async def test_rate_limit_headers(self, rate_limiter):
        """Test rate limit headers for responses."""
        client_id = 'test_client'
        
        # Make some requests
        for i in range(5):
            await rate_limiter.check_rate_limit(client_id)
        
        headers = rate_limiter.get_rate_limit_headers(client_id)
        
        assert 'X-RateLimit-Limit' in headers
        assert headers['X-RateLimit-Limit'] == '10'
        assert 'X-RateLimit-Remaining' in headers
        assert headers['X-RateLimit-Remaining'] == '5'
        assert 'X-RateLimit-Reset' in headers