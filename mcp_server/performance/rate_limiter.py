"""
Rate limiting implementation for MCP server.

Provides rate limiting with various algorithms and distributed support.
"""

import asyncio
import time
import logging
from typing import Dict, Optional, Any, List, Tuple, Callable
from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod
import hashlib
import json

logger = logging.getLogger(__name__)


class RateLimitAlgorithm(Enum):
    """Rate limiting algorithms."""
    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"
    LEAKY_BUCKET = "leaky_bucket"


@dataclass
class RateLimiterConfig:
    """Rate limiter configuration."""
    algorithm: RateLimitAlgorithm = RateLimitAlgorithm.TOKEN_BUCKET
    max_requests: int = 100
    window_seconds: float = 60.0
    burst_limit: Optional[int] = None  # For token bucket
    leak_rate: Optional[float] = None  # For leaky bucket
    enable_distributed: bool = False
    redis_key_prefix: str = "rate_limit:"
    cleanup_interval: float = 300.0  # 5 minutes


@dataclass
class RateLimitResult:
    """Result of rate limit check."""
    allowed: bool
    remaining: int
    reset_time: float
    retry_after: Optional[float] = None
    limit: int = 0


class RateLimitStore(ABC):
    """Abstract store for rate limit data."""
    
    @abstractmethod
    async def get_bucket_state(self, key: str) -> Optional[Dict[str, Any]]:
        """Get bucket state for a key."""
        pass
    
    @abstractmethod
    async def set_bucket_state(self, key: str, state: Dict[str, Any], ttl: float) -> None:
        """Set bucket state for a key."""
        pass
    
    @abstractmethod
    async def increment_counter(self, key: str, window_start: float, ttl: float) -> int:
        """Increment counter for a window."""
        pass
    
    @abstractmethod
    async def get_window_requests(self, key: str, window_start: float, 
                                  window_end: float) -> List[float]:
        """Get requests in a time window."""
        pass
    
    @abstractmethod
    async def add_request(self, key: str, timestamp: float, ttl: float) -> None:
        """Add a request timestamp."""
        pass
    
    @abstractmethod
    async def cleanup_expired(self) -> int:
        """Clean up expired entries."""
        pass


class MemoryRateLimitStore(RateLimitStore):
    """In-memory rate limit store."""
    
    def __init__(self):
        self._buckets: Dict[str, Dict[str, Any]] = {}
        self._counters: Dict[str, int] = {}
        self._requests: Dict[str, List[float]] = {}
        self._lock = asyncio.Lock()
    
    async def get_bucket_state(self, key: str) -> Optional[Dict[str, Any]]:
        async with self._lock:
            return self._buckets.get(key)
    
    async def set_bucket_state(self, key: str, state: Dict[str, Any], ttl: float) -> None:
        async with self._lock:
            state['expires_at'] = time.time() + ttl
            self._buckets[key] = state
    
    async def increment_counter(self, key: str, window_start: float, ttl: float) -> int:
        async with self._lock:
            window_key = f"{key}:{int(window_start)}"
            count = self._counters.get(window_key, 0) + 1
            self._counters[window_key] = count
            return count
    
    async def get_window_requests(self, key: str, window_start: float, 
                                  window_end: float) -> List[float]:
        async with self._lock:
            requests = self._requests.get(key, [])
            return [req for req in requests if window_start <= req <= window_end]
    
    async def add_request(self, key: str, timestamp: float, ttl: float) -> None:
        async with self._lock:
            if key not in self._requests:
                self._requests[key] = []
            self._requests[key].append(timestamp)
    
    async def cleanup_expired(self) -> int:
        async with self._lock:
            current_time = time.time()
            cleaned = 0
            
            # Clean buckets
            expired_buckets = [
                key for key, state in self._buckets.items()
                if state.get('expires_at', 0) < current_time
            ]
            for key in expired_buckets:
                del self._buckets[key]
                cleaned += 1
            
            # Clean counters (keep recent windows)
            expired_counters = [
                key for key in self._counters.keys()
                if current_time - float(key.split(':')[-1]) > 3600  # 1 hour
            ]
            for key in expired_counters:
                del self._counters[key]
                cleaned += 1
            
            # Clean old requests
            for key in list(self._requests.keys()):
                old_requests = [
                    req for req in self._requests[key]
                    if current_time - req > 3600  # 1 hour
                ]
                if old_requests:
                    self._requests[key] = [
                        req for req in self._requests[key]
                        if current_time - req <= 3600
                    ]
                    cleaned += len(old_requests)
                
                if not self._requests[key]:
                    del self._requests[key]
            
            return cleaned


class TokenBucketLimiter:
    """Token bucket rate limiter implementation."""
    
    def __init__(self, config: RateLimiterConfig, store: RateLimitStore):
        self.config = config
        self.store = store
        self.capacity = config.burst_limit or config.max_requests
        self.refill_rate = config.max_requests / config.window_seconds
    
    async def check_limit(self, key: str) -> RateLimitResult:
        """Check if request is allowed under token bucket algorithm."""
        current_time = time.time()
        
        # Get current bucket state
        bucket = await self.store.get_bucket_state(key)
        if not bucket:
            bucket = {
                'tokens': self.capacity,
                'last_refill': current_time
            }
        
        # Calculate tokens to add based on time elapsed
        time_elapsed = current_time - bucket['last_refill']
        tokens_to_add = int(time_elapsed * self.refill_rate)
        
        # Update bucket
        bucket['tokens'] = min(self.capacity, bucket['tokens'] + tokens_to_add)
        bucket['last_refill'] = current_time
        
        # Check if request can be allowed
        if bucket['tokens'] >= 1:
            bucket['tokens'] -= 1
            allowed = True
            remaining = bucket['tokens']
            retry_after = None
        else:
            allowed = False
            remaining = 0
            retry_after = 1.0 / self.refill_rate  # Time to get one token
        
        # Save bucket state
        await self.store.set_bucket_state(key, bucket, self.config.window_seconds * 2)
        
        return RateLimitResult(
            allowed=allowed,
            remaining=remaining,
            reset_time=current_time + self.config.window_seconds,
            retry_after=retry_after,
            limit=self.capacity
        )


class SlidingWindowLimiter:
    """Sliding window rate limiter implementation."""
    
    def __init__(self, config: RateLimiterConfig, store: RateLimitStore):
        self.config = config
        self.store = store
    
    async def check_limit(self, key: str) -> RateLimitResult:
        """Check if request is allowed under sliding window algorithm."""
        current_time = time.time()
        window_start = current_time - self.config.window_seconds
        
        # Get requests in current window
        requests = await self.store.get_window_requests(key, window_start, current_time)
        
        if len(requests) < self.config.max_requests:
            # Allow request and record timestamp
            await self.store.add_request(key, current_time, self.config.window_seconds * 2)
            
            return RateLimitResult(
                allowed=True,
                remaining=self.config.max_requests - len(requests) - 1,
                reset_time=requests[0] + self.config.window_seconds if requests else current_time + self.config.window_seconds,
                limit=self.config.max_requests
            )
        else:
            # Calculate when oldest request will expire
            oldest_request = min(requests)
            retry_after = oldest_request + self.config.window_seconds - current_time
            
            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_time=oldest_request + self.config.window_seconds,
                retry_after=max(0, retry_after),
                limit=self.config.max_requests
            )


class FixedWindowLimiter:
    """Fixed window rate limiter implementation."""
    
    def __init__(self, config: RateLimiterConfig, store: RateLimitStore):
        self.config = config
        self.store = store
    
    async def check_limit(self, key: str) -> RateLimitResult:
        """Check if request is allowed under fixed window algorithm."""
        current_time = time.time()
        window_start = int(current_time // self.config.window_seconds) * self.config.window_seconds
        
        # Increment counter for current window
        count = await self.store.increment_counter(key, window_start, self.config.window_seconds * 2)
        
        if count <= self.config.max_requests:
            return RateLimitResult(
                allowed=True,
                remaining=self.config.max_requests - count,
                reset_time=window_start + self.config.window_seconds,
                limit=self.config.max_requests
            )
        else:
            retry_after = window_start + self.config.window_seconds - current_time
            
            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_time=window_start + self.config.window_seconds,
                retry_after=max(0, retry_after),
                limit=self.config.max_requests
            )


class RateLimiter:
    """Main rate limiter class."""
    
    def __init__(self, config: Optional[RateLimiterConfig] = None, store: Optional[RateLimitStore] = None,
                 algorithm: Optional[str] = None, requests_per_minute: Optional[int] = None):
        # Support simplified constructor for testing
        if config is None:
            alg = RateLimitAlgorithm.TOKEN_BUCKET
            if algorithm:
                alg = RateLimitAlgorithm(algorithm)
            
            config = RateLimiterConfig(
                algorithm=alg,
                max_requests=requests_per_minute or 60,
                window_seconds=60.0
            )
        
        self.config = config
        self.store = store or MemoryRateLimitStore()
        self._limiter = self._create_limiter()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
    
    def _create_limiter(self):
        """Create the appropriate limiter based on algorithm."""
        if self.config.algorithm == RateLimitAlgorithm.TOKEN_BUCKET:
            return TokenBucketLimiter(self.config, self.store)
        elif self.config.algorithm == RateLimitAlgorithm.SLIDING_WINDOW:
            return SlidingWindowLimiter(self.config, self.store)
        elif self.config.algorithm == RateLimitAlgorithm.FIXED_WINDOW:
            return FixedWindowLimiter(self.config, self.store)
        else:
            raise ValueError(f"Unsupported algorithm: {self.config.algorithm}")
    
    async def start(self) -> None:
        """Start the rate limiter."""
        if self._running:
            return
        
        self._running = True
        
        # Start cleanup task
        if self.config.cleanup_interval > 0:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        logger.info(f"Rate limiter started with {self.config.algorithm.value} algorithm")
    
    async def stop(self) -> None:
        """Stop the rate limiter."""
        if not self._running:
            return
        
        self._running = False
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Rate limiter stopped")
    
    async def _cleanup_loop(self) -> None:
        """Background cleanup loop."""
        while self._running:
            try:
                await asyncio.sleep(self.config.cleanup_interval)
                cleaned = await self.store.cleanup_expired()
                if cleaned > 0:
                    logger.debug(f"Cleaned up {cleaned} expired rate limit entries")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Rate limiter cleanup error: {e}")
    
    async def check_limit(self, identifier: str, context: Optional[Dict[str, Any]] = None) -> RateLimitResult:
        """Check if request is allowed for the given identifier."""
        # Generate key
        key = self._generate_key(identifier, context)
        
        try:
            result = await self._limiter.check_limit(key)
            
            if not result.allowed:
                logger.debug(f"Rate limit exceeded for {identifier}")
            
            return result
            
        except Exception as e:
            logger.error(f"Rate limit check error for {identifier}: {e}")
            # Fail open - allow request on error
            return RateLimitResult(
                allowed=True,
                remaining=self.config.max_requests,
                reset_time=time.time() + self.config.window_seconds,
                limit=self.config.max_requests
            )
    
    async def is_allowed(self, identifier: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """Check if request is allowed for the given identifier."""
        result = await self.check_limit(identifier, context)
        return result.allowed
    
    def _generate_key(self, identifier: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Generate a key for rate limiting."""
        key_parts = [self.config.redis_key_prefix, identifier]
        
        if context:
            # Include relevant context in key
            context_str = json.dumps(context, sort_keys=True)
            context_hash = hashlib.md5(context_str.encode()).hexdigest()[:8]
            key_parts.append(context_hash)
        
        return ":".join(key_parts)
    
    async def reset_limit(self, identifier: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """Reset rate limit for an identifier."""
        key = self._generate_key(identifier, context)
        
        try:
            # For now, we'll just set an expired bucket
            await self.store.set_bucket_state(key, {'tokens': 0, 'last_refill': 0}, 0.1)
            logger.info(f"Reset rate limit for {identifier}")
            return True
        except Exception as e:
            logger.error(f"Failed to reset rate limit for {identifier}: {e}")
            return False


class MultiLimiter:
    """Multiple rate limiters with different rules."""
    
    def __init__(self):
        self._limiters: Dict[str, RateLimiter] = {}
        self._rules: List[Tuple[str, Callable[[str, Optional[Dict[str, Any]]], bool]]] = []
    
    def add_limiter(self, name: str, limiter: RateLimiter) -> None:
        """Add a rate limiter."""
        self._limiters[name] = limiter
    
    def add_rule(self, limiter_name: str, 
                 condition: Callable[[str, Optional[Dict[str, Any]]], bool]) -> None:
        """Add a rule for when to apply a limiter."""
        self._rules.append((limiter_name, condition))
    
    async def check_limits(self, identifier: str, 
                          context: Optional[Dict[str, Any]] = None) -> List[RateLimitResult]:
        """Check all applicable rate limits."""
        results = []
        
        for limiter_name, condition in self._rules:
            if condition(identifier, context):
                limiter = self._limiters.get(limiter_name)
                if limiter:
                    result = await limiter.check_limit(identifier, context)
                    results.append(result)
        
        return results
    
    async def is_allowed(self, identifier: str, 
                        context: Optional[Dict[str, Any]] = None) -> Tuple[bool, List[RateLimitResult]]:
        """Check if request is allowed by all applicable limiters."""
        results = await self.check_limits(identifier, context)
        allowed = all(result.allowed for result in results)
        return allowed, results
    
    async def start_all(self) -> None:
        """Start all limiters."""
        for limiter in self._limiters.values():
            await limiter.start()
    
    async def stop_all(self) -> None:
        """Stop all limiters."""
        for limiter in self._limiters.values():
            await limiter.stop()


# Create default rate limiter
default_config = RateLimiterConfig(
    algorithm=RateLimitAlgorithm.TOKEN_BUCKET,
    max_requests=100,
    window_seconds=60.0,
    burst_limit=120
)

rate_limiter = RateLimiter(default_config)