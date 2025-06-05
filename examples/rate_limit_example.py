#!/usr/bin/env python3
"""
Example demonstrating the fixed rate limiting functionality.

This example shows how to use the rate limiting system with the corrected
RateLimiterConfig parameters.
"""
import asyncio
import time
from typing import Dict, Any

# Assuming this script is run from the project root
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from mcp_server.performance.rate_limiter import RateLimiter, RateLimiterConfig, RateLimitAlgorithm


async def example_basic_rate_limiting():
    """Example of basic rate limiting usage."""
    print("=== Basic Rate Limiting Example ===")
    
    # Create rate limiter configuration with CORRECT parameters
    config = RateLimiterConfig(
        algorithm=RateLimitAlgorithm.TOKEN_BUCKET,
        max_requests=5,  # Allow 5 requests
        window_seconds=10.0,  # Per 10 seconds
        burst_limit=7  # Allow burst up to 7 requests
    )
    
    # Create and start rate limiter
    limiter = RateLimiter(config)
    await limiter.start()
    
    client_id = "example_client"
    
    print(f"Rate limiter allows {config.max_requests} requests per {config.window_seconds} seconds")
    print(f"Burst limit: {config.burst_limit} requests")
    print()
    
    # Simulate rapid requests
    for i in range(10):
        result = await limiter.check_limit(client_id)
        status = "✓ ALLOWED" if result.allowed else "✗ DENIED"
        print(f"Request {i+1:2d}: {status} (remaining: {result.remaining}, limit: {result.limit})")
        
        if not result.allowed and result.retry_after:
            print(f"           Retry after: {result.retry_after:.1f} seconds")
        
        # Small delay between requests
        await asyncio.sleep(0.1)
    
    await limiter.stop()
    print()


async def example_multiple_algorithms():
    """Example comparing different rate limiting algorithms."""
    print("=== Multiple Algorithm Comparison ===")
    
    algorithms = [
        RateLimitAlgorithm.TOKEN_BUCKET,
        RateLimitAlgorithm.SLIDING_WINDOW,
        RateLimitAlgorithm.FIXED_WINDOW
    ]
    
    for algorithm in algorithms:
        print(f"\nTesting {algorithm.value}:")
        
        config = RateLimiterConfig(
            algorithm=algorithm,
            max_requests=3,
            window_seconds=5.0
        )
        
        limiter = RateLimiter(config)
        await limiter.start()
        
        client_id = f"client_{algorithm.value}"
        
        # Make 5 rapid requests
        for i in range(5):
            result = await limiter.check_limit(client_id)
            status = "✓" if result.allowed else "✗"
            print(f"  Request {i+1}: {status} (remaining: {result.remaining})")
        
        await limiter.stop()


async def example_rate_limit_integration():
    """Example showing how the integration would be used."""
    print("=== Rate Limit Integration Example ===")
    
    # This simulates how the RateLimitIntegration would be configured
    rate_limiters: Dict[str, RateLimiter] = {}
    
    # Default rate limiter
    default_config = RateLimiterConfig(
        algorithm=RateLimitAlgorithm.TOKEN_BUCKET,
        max_requests=100,
        window_seconds=60.0,
        burst_limit=150
    )
    rate_limiters["default"] = RateLimiter(default_config)
    
    # Expensive operations limiter
    expensive_config = RateLimiterConfig(
        algorithm=RateLimitAlgorithm.TOKEN_BUCKET,
        max_requests=10,
        window_seconds=60.0,
        burst_limit=15
    )
    rate_limiters["index_file"] = RateLimiter(expensive_config)
    
    # Start all limiters
    for limiter in rate_limiters.values():
        await limiter.start()
    
    print("Rate limiters configured:")
    for name, limiter in rate_limiters.items():
        config = limiter.config
        print(f"  {name}: {config.max_requests} req/{config.window_seconds}s (burst: {config.burst_limit})")
    
    # Simulate some requests
    client_id = "integration_client"
    
    print(f"\nSimulating requests for client '{client_id}':")
    
    # Regular operation
    result = await rate_limiters["default"].check_limit(client_id)
    print(f"Default operation: {'allowed' if result.allowed else 'denied'} (remaining: {result.remaining})")
    
    # Expensive operation
    result = await rate_limiters["index_file"].check_limit(client_id)
    print(f"Index file operation: {'allowed' if result.allowed else 'denied'} (remaining: {result.remaining})")
    
    # Stop all limiters
    for limiter in rate_limiters.values():
        await limiter.stop()
    
    print()


async def main():
    """Main example function."""
    print("Rate Limiting Examples - FIXED Configuration")
    print("=" * 50)
    
    await example_basic_rate_limiting()
    await example_multiple_algorithms()
    await example_rate_limit_integration()
    
    print("All examples completed successfully! 🎉")
    print("\nKey fixes applied:")
    print("1. ✓ Changed 'requests_per_window' to 'max_requests'")
    print("2. ✓ Removed non-existent parameters like 'burst_size' and 'block_duration_seconds'")
    print("3. ✓ Updated method calls to match actual RateLimiter API")
    print("4. ✓ Proper algorithm configuration using RateLimitAlgorithm enum")


if __name__ == "__main__":
    asyncio.run(main())