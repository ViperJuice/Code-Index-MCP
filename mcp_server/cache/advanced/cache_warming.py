"""Cache warming and invalidation strategies for multi-tier cache."""
import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Set, Optional, Callable, Awaitable, Tuple
from enum import Enum
from pathlib import Path

from .tiered_cache import TieredCache, CacheTier

logger = logging.getLogger(__name__)


class WarmingStrategy(Enum):
    """Cache warming strategies."""
    EAGER = "eager"          # Warm all at startup
    LAZY = "lazy"           # Warm on first access
    PREDICTIVE = "predictive"  # Warm based on patterns
    SCHEDULED = "scheduled"  # Warm at specific times
    

class InvalidationStrategy(Enum):
    """Cache invalidation strategies."""
    TIME_BASED = "time_based"        # TTL expiration
    DEPENDENCY_BASED = "dependency_based"  # Invalidate dependent keys
    PATTERN_BASED = "pattern_based"  # Invalidate by key patterns
    TAG_BASED = "tag_based"         # Invalidate by tags
    

@dataclass
class WarmingRule:
    """Rule for cache warming."""
    key_pattern: str
    factory_func: Callable[[str], Awaitable[Any]]
    strategy: WarmingStrategy = WarmingStrategy.LAZY
    priority: int = 1  # Higher = more important
    dependencies: Set[str] = field(default_factory=set)
    schedule_cron: Optional[str] = None  # For scheduled warming
    max_age_seconds: int = 3600  # Max age before re-warming
    

@dataclass
class InvalidationRule:
    """Rule for cache invalidation."""
    trigger_pattern: str
    target_patterns: List[str]
    strategy: InvalidationStrategy = InvalidationStrategy.DEPENDENCY_BASED
    cascade: bool = True  # Whether to cascade invalidation
    delay_seconds: int = 0  # Delay before invalidation
    

class CacheWarmingManager:
    """Manages cache warming and invalidation strategies."""
    
    def __init__(self, cache: TieredCache):
        self.cache = cache
        self.warming_rules: Dict[str, WarmingRule] = {}
        self.invalidation_rules: Dict[str, InvalidationRule] = {}
        self.warming_queue: asyncio.Queue = asyncio.Queue()
        self.invalidation_queue: asyncio.Queue = asyncio.Queue()
        
        # Tracking
        self.warming_stats = {
            "total_warmings": 0,
            "successful_warmings": 0,
            "failed_warmings": 0,
            "avg_warming_time_ms": 0.0
        }
        
        # Background tasks
        self._running = True
        self._warming_task: Optional[asyncio.Task] = None
        self._invalidation_task: Optional[asyncio.Task] = None
        self._scheduled_task: Optional[asyncio.Task] = None
        
        self._start_background_tasks()
    
    def _start_background_tasks(self):
        """Start background warming and invalidation tasks."""
        self._warming_task = asyncio.create_task(self._warming_worker())
        self._invalidation_task = asyncio.create_task(self._invalidation_worker())
        self._scheduled_task = asyncio.create_task(self._scheduled_warming_worker())
    
    async def _warming_worker(self):
        """Background worker for cache warming."""
        while self._running:
            try:
                # Get warming job with timeout
                try:
                    key, rule = await asyncio.wait_for(
                        self.warming_queue.get(), timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                await self._execute_warming(key, rule)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in warming worker: {e}")
    
    async def _invalidation_worker(self):
        """Background worker for cache invalidation."""
        while self._running:
            try:
                # Get invalidation job with timeout
                try:
                    rule, trigger_key = await asyncio.wait_for(
                        self.invalidation_queue.get(), timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                await self._execute_invalidation(rule, trigger_key)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in invalidation worker: {e}")
    
    async def _scheduled_warming_worker(self):
        """Background worker for scheduled cache warming."""
        while self._running:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                current_time = time.time()
                for pattern, rule in self.warming_rules.items():
                    if rule.strategy == WarmingStrategy.SCHEDULED:
                        # Check if it's time to warm (simplified - would use cron in real implementation)
                        if await self._should_schedule_warming(rule, current_time):
                            await self._schedule_pattern_warming(pattern, rule)
                            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduled warming worker: {e}")
    
    async def _should_schedule_warming(self, rule: WarmingRule, current_time: float) -> bool:
        """Check if scheduled warming should run (simplified implementation)."""
        # In a real implementation, this would parse the cron expression
        # For now, we'll just check if data is older than max_age
        return True  # Simplified for demo
    
    def add_warming_rule(self, pattern: str, rule: WarmingRule):
        """Add a cache warming rule."""
        self.warming_rules[pattern] = rule
        logger.info(f"Added warming rule for pattern: {pattern}")
    
    def add_invalidation_rule(self, trigger: str, rule: InvalidationRule):
        """Add a cache invalidation rule."""
        self.invalidation_rules[trigger] = rule
        logger.info(f"Added invalidation rule for trigger: {trigger}")
    
    async def warm_cache(self, keys: List[str], strategy: WarmingStrategy = WarmingStrategy.EAGER) -> Dict[str, bool]:
        """Warm cache for specific keys."""
        results = {}
        
        if strategy == WarmingStrategy.EAGER:
            # Warm all keys immediately
            tasks = []
            for key in keys:
                rule = self._find_warming_rule(key)
                if rule:
                    task = asyncio.create_task(self._execute_warming(key, rule))
                    tasks.append((key, task))
            
            # Wait for all warming tasks
            for key, task in tasks:
                try:
                    results[key] = await task
                except Exception as e:
                    logger.error(f"Failed to warm {key}: {e}")
                    results[key] = False
        
        elif strategy == WarmingStrategy.LAZY:
            # Queue for lazy warming
            for key in keys:
                rule = self._find_warming_rule(key)
                if rule:
                    await self.warming_queue.put((key, rule))
                    results[key] = True  # Queued successfully
        
        elif strategy == WarmingStrategy.PREDICTIVE:
            # Use access patterns to prioritize
            prioritized_keys = await self._prioritize_keys_by_patterns(keys)
            for key in prioritized_keys:
                rule = self._find_warming_rule(key)
                if rule:
                    await self.warming_queue.put((key, rule))
                    results[key] = True
        
        return results
    
    def _find_warming_rule(self, key: str) -> Optional[WarmingRule]:
        """Find the best matching warming rule for a key."""
        import fnmatch
        
        best_rule = None
        best_specificity = 0
        
        for pattern, rule in self.warming_rules.items():
            if fnmatch.fnmatch(key, pattern):
                # Calculate specificity (longer patterns are more specific)
                specificity = len(pattern.replace('*', ''))
                if specificity > best_specificity:
                    best_rule = rule
                    best_specificity = specificity
        
        return best_rule
    
    async def _prioritize_keys_by_patterns(self, keys: List[str]) -> List[str]:
        """Prioritize keys based on access patterns."""
        key_scores = []
        
        for key in keys:
            score = 0
            
            # Check if key has access pattern data
            if key in self.cache.access_patterns:
                pattern = self.cache.access_patterns[key]
                score += pattern.access_frequency * 10  # Frequency weight
                score += max(0, 100 - (time.time() - pattern.last_accessed))  # Recency weight
            
            # Check warming rule priority
            rule = self._find_warming_rule(key)
            if rule:
                score += rule.priority * 5
            
            key_scores.append((key, score))
        
        # Sort by score (highest first)
        key_scores.sort(key=lambda x: x[1], reverse=True)
        return [key for key, _ in key_scores]
    
    async def _execute_warming(self, key: str, rule: WarmingRule) -> bool:
        """Execute cache warming for a specific key."""
        start_time = time.time()
        
        try:
            self.warming_stats["total_warmings"] += 1
            
            # Check if already cached and fresh
            cached_value = await self.cache.get(key)
            if cached_value is not None:
                # Check age if we have access pattern data
                if key in self.cache.access_patterns:
                    pattern = self.cache.access_patterns[key]
                    age = time.time() - pattern.last_accessed
                    if age < rule.max_age_seconds:
                        return True  # Already fresh
            
            # Generate new value using factory function
            value = await rule.factory_func(key)
            
            # Determine optimal tier for storage
            tier_hint = None
            if rule.priority >= 3:
                tier_hint = CacheTier.L1  # High priority goes to L1
            elif rule.priority >= 2:
                tier_hint = CacheTier.L2  # Medium priority goes to L2
            
            # Store in cache
            success = await self.cache.set(
                key, value, 
                ttl=rule.max_age_seconds,
                tier_hint=tier_hint
            )
            
            if success:
                self.warming_stats["successful_warmings"] += 1
                logger.debug(f"Successfully warmed cache for key: {key}")
            else:
                self.warming_stats["failed_warmings"] += 1
                logger.warning(f"Failed to warm cache for key: {key}")
            
            # Update average warming time
            warming_time = (time.time() - start_time) * 1000  # ms
            current_avg = self.warming_stats["avg_warming_time_ms"]
            self.warming_stats["avg_warming_time_ms"] = (
                (current_avg * 0.9) + (warming_time * 0.1)
            )
            
            return success
            
        except Exception as e:
            self.warming_stats["failed_warmings"] += 1
            logger.error(f"Error warming cache for key {key}: {e}")
            return False
    
    async def invalidate(self, trigger_key: str, cascade: bool = True) -> int:
        """Trigger cache invalidation based on rules."""
        invalidated_count = 0
        
        # Find matching invalidation rules
        matching_rules = self._find_invalidation_rules(trigger_key)
        
        for rule in matching_rules:
            if rule.delay_seconds > 0:
                # Queue for delayed invalidation
                await self.invalidation_queue.put((rule, trigger_key))
            else:
                # Execute immediately
                count = await self._execute_invalidation(rule, trigger_key)
                invalidated_count += count
        
        return invalidated_count
    
    def _find_invalidation_rules(self, trigger_key: str) -> List[InvalidationRule]:
        """Find invalidation rules that match the trigger key."""
        import fnmatch
        
        matching_rules = []
        for pattern, rule in self.invalidation_rules.items():
            if fnmatch.fnmatch(trigger_key, pattern):
                matching_rules.append(rule)
        
        return matching_rules
    
    async def _execute_invalidation(self, rule: InvalidationRule, trigger_key: str) -> int:
        """Execute cache invalidation based on rule."""
        invalidated_count = 0
        
        try:
            if rule.delay_seconds > 0:
                await asyncio.sleep(rule.delay_seconds)
            
            if rule.strategy == InvalidationStrategy.DEPENDENCY_BASED:
                # Invalidate based on dependency patterns
                for target_pattern in rule.target_patterns:
                    count = await self._invalidate_by_pattern(target_pattern)
                    invalidated_count += count
            
            elif rule.strategy == InvalidationStrategy.TAG_BASED:
                # Invalidate by tags (if implemented in cache)
                tags = set(rule.target_patterns)
                # Note: TieredCache would need tag support for this
                logger.warning("Tag-based invalidation not fully implemented")
            
            elif rule.strategy == InvalidationStrategy.PATTERN_BASED:
                # Direct pattern invalidation
                for pattern in rule.target_patterns:
                    count = await self._invalidate_by_pattern(pattern)
                    invalidated_count += count
            
            logger.info(f"Invalidated {invalidated_count} entries for trigger: {trigger_key}")
            
        except Exception as e:
            logger.error(f"Error executing invalidation for {trigger_key}: {e}")
        
        return invalidated_count
    
    async def _invalidate_by_pattern(self, pattern: str) -> int:
        """Invalidate cache entries matching a pattern."""
        import fnmatch
        
        invalidated_count = 0
        
        # Check L1 cache
        l1_keys_to_remove = []
        for key in self.cache.l1_cache:
            if fnmatch.fnmatch(key, pattern):
                l1_keys_to_remove.append(key)
        
        for key in l1_keys_to_remove:
            await self.cache.delete(key)
            invalidated_count += 1
        
        # For L2 and L3, we'd need to implement pattern matching
        # This is a simplified version
        logger.debug(f"Invalidated {invalidated_count} L1 entries for pattern: {pattern}")
        
        return invalidated_count
    
    async def _schedule_pattern_warming(self, pattern: str, rule: WarmingRule):
        """Schedule warming for all keys matching a pattern."""
        # This would require a way to enumerate keys matching a pattern
        # For now, we'll just log the intent
        logger.info(f"Scheduled warming for pattern: {pattern}")
    
    async def get_warming_stats(self) -> Dict[str, Any]:
        """Get cache warming statistics."""
        return {
            "warming_rules_count": len(self.warming_rules),
            "invalidation_rules_count": len(self.invalidation_rules),
            "warming_queue_size": self.warming_queue.qsize(),
            "invalidation_queue_size": self.invalidation_queue.qsize(),
            "stats": self.warming_stats.copy()
        }
    
    async def preload_common_patterns(self, patterns: List[str]) -> Dict[str, int]:
        """Preload cache with common access patterns."""
        results = {}
        
        for pattern in patterns:
            rule = self._find_warming_rule(pattern)
            if rule:
                # For demo, we'll just warm a few example keys
                example_keys = [f"{pattern.replace('*', str(i))}" for i in range(5)]
                warmed = await self.warm_cache(example_keys, WarmingStrategy.EAGER)
                results[pattern] = sum(1 for success in warmed.values() if success)
        
        return results
    
    async def shutdown(self):
        """Shutdown the warming manager."""
        self._running = False
        
        tasks = [self._warming_task, self._invalidation_task, self._scheduled_task]
        for task in tasks:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass


# Convenience functions for common patterns
def create_symbol_warming_rule(
    factory_func: Callable[[str], Awaitable[Any]]
) -> WarmingRule:
    """Create warming rule for symbol lookups."""
    return WarmingRule(
        key_pattern="symbol:*",
        factory_func=factory_func,
        strategy=WarmingStrategy.PREDICTIVE,
        priority=3,
        max_age_seconds=1800  # 30 minutes
    )


def create_search_warming_rule(
    factory_func: Callable[[str], Awaitable[Any]]
) -> WarmingRule:
    """Create warming rule for search results."""
    return WarmingRule(
        key_pattern="search:*",
        factory_func=factory_func,
        strategy=WarmingStrategy.LAZY,
        priority=2,
        max_age_seconds=600  # 10 minutes
    )


def create_file_invalidation_rule() -> InvalidationRule:
    """Create invalidation rule for file changes."""
    return InvalidationRule(
        trigger_pattern="file_changed:*",
        target_patterns=["file:*", "symbol:*", "search:*"],
        strategy=InvalidationStrategy.DEPENDENCY_BASED,
        cascade=True
    )