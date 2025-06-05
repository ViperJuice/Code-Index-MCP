"""
Memory optimization utilities for the MCP server.

Provides memory monitoring, garbage collection optimization, and resource management.
"""

import gc
import sys
import asyncio
import logging
import psutil
import weakref
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field
from collections import defaultdict
from datetime import datetime, timedelta
import threading
import time

logger = logging.getLogger(__name__)


@dataclass
class MemoryStats:
    """Memory usage statistics."""
    total_memory_mb: float = 0.0
    available_memory_mb: float = 0.0
    used_memory_mb: float = 0.0
    process_memory_mb: float = 0.0
    process_memory_percent: float = 0.0
    gc_collections: Dict[int, int] = field(default_factory=dict)
    gc_collected: Dict[int, int] = field(default_factory=dict)
    gc_uncollectable: Dict[int, int] = field(default_factory=dict)
    object_count: int = 0
    large_objects_count: int = 0
    weak_references_count: int = 0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class MemoryThresholds:
    """Memory usage thresholds for optimization."""
    warning_percent: float = 80.0
    critical_percent: float = 90.0
    gc_trigger_percent: float = 75.0
    cleanup_trigger_percent: float = 85.0
    max_object_size_mb: float = 10.0
    max_cache_size_mb: float = 100.0


class ObjectTracker:
    """Tracks object creation and memory usage."""
    
    def __init__(self):
        self._objects: Set[weakref.ref] = set()
        self._object_sizes: Dict[int, int] = {}
        self._type_counts: Dict[str, int] = defaultdict(int)
        self._lock = threading.Lock()
    
    def track_object(self, obj: Any) -> None:
        """Track an object for memory monitoring."""
        try:
            obj_id = id(obj)
            obj_size = sys.getsizeof(obj)
            obj_type = type(obj).__name__
            
            with self._lock:
                # Create weak reference with cleanup callback
                def cleanup(ref):
                    with self._lock:
                        self._objects.discard(ref)
                        if obj_id in self._object_sizes:
                            del self._object_sizes[obj_id]
                        self._type_counts[obj_type] = max(0, self._type_counts[obj_type] - 1)
                
                weak_ref = weakref.ref(obj, cleanup)
                self._objects.add(weak_ref)
                self._object_sizes[obj_id] = obj_size
                self._type_counts[obj_type] += 1
                
        except Exception as e:
            logger.warning(f"Failed to track object: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get tracking statistics."""
        with self._lock:
            total_size = sum(self._object_sizes.values())
            return {
                "tracked_objects": len(self._objects),
                "total_size_bytes": total_size,
                "total_size_mb": total_size / (1024 * 1024),
                "type_counts": dict(self._type_counts),
                "average_size_bytes": total_size / len(self._objects) if self._objects else 0
            }
    
    def cleanup_dead_references(self) -> int:
        """Clean up dead weak references."""
        with self._lock:
            before_count = len(self._objects)
            self._objects = {ref for ref in self._objects if ref() is not None}
            cleaned = before_count - len(self._objects)
            return cleaned


class MemoryOptimizer:
    """Memory optimization and monitoring system."""
    
    def __init__(self, thresholds: Optional[MemoryThresholds] = None):
        self.thresholds = thresholds or MemoryThresholds()
        self.tracker = ObjectTracker()
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._stats_history: List[MemoryStats] = []
        self._max_history = 100
        self._callbacks: List[Callable[[MemoryStats], None]] = []
        self._last_gc_time = time.time()
        self._gc_frequency = 60  # seconds
    
    async def start_monitoring(self, interval: float = 30.0) -> None:
        """Start memory monitoring."""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._monitor_task = asyncio.create_task(self._monitoring_loop(interval))
        logger.info("Memory monitoring started")
    
    async def stop_monitoring(self) -> None:
        """Stop memory monitoring."""
        if not self._monitoring:
            return
        
        self._monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Memory monitoring stopped")
    
    async def _monitoring_loop(self, interval: float) -> None:
        """Main monitoring loop."""
        while self._monitoring:
            try:
                stats = await self.get_memory_stats()
                self._update_stats_history(stats)
                
                # Check thresholds and trigger optimizations
                await self._check_thresholds(stats)
                
                # Notify callbacks
                for callback in self._callbacks:
                    try:
                        callback(stats)
                    except Exception as e:
                        logger.error(f"Memory monitoring callback error: {e}")
                
                await asyncio.sleep(interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Memory monitoring error: {e}")
                await asyncio.sleep(interval)
    
    def _update_stats_history(self, stats: MemoryStats) -> None:
        """Update statistics history."""
        self._stats_history.append(stats)
        if len(self._stats_history) > self._max_history:
            self._stats_history.pop(0)
    
    async def _check_thresholds(self, stats: MemoryStats) -> None:
        """Check memory thresholds and trigger optimizations."""
        memory_percent = stats.process_memory_percent
        
        # Trigger garbage collection
        if (memory_percent >= self.thresholds.gc_trigger_percent and
            time.time() - self._last_gc_time >= self._gc_frequency):
            await self.force_garbage_collection()
            self._last_gc_time = time.time()
        
        # Trigger cleanup
        if memory_percent >= self.thresholds.cleanup_trigger_percent:
            await self.cleanup_resources()
        
        # Log warnings
        if memory_percent >= self.thresholds.critical_percent:
            logger.critical(f"Memory usage critical: {memory_percent:.1f}%")
        elif memory_percent >= self.thresholds.warning_percent:
            logger.warning(f"Memory usage high: {memory_percent:.1f}%")
    
    async def get_memory_stats(self) -> MemoryStats:
        """Get current memory statistics."""
        # System memory
        memory = psutil.virtual_memory()
        
        # Process memory
        process = psutil.Process()
        process_memory = process.memory_info()
        
        # Garbage collection stats
        gc_stats = {}
        gc_collected = {}
        gc_uncollectable = {}
        
        for generation in range(3):
            stats = gc.get_stats()[generation]
            gc_stats[generation] = stats.get('collections', 0)
            gc_collected[generation] = stats.get('collected', 0)
            gc_uncollectable[generation] = stats.get('uncollectable', 0)
        
        # Object tracking stats
        tracker_stats = self.tracker.get_stats()
        
        return MemoryStats(
            total_memory_mb=memory.total / (1024 * 1024),
            available_memory_mb=memory.available / (1024 * 1024),
            used_memory_mb=memory.used / (1024 * 1024),
            process_memory_mb=process_memory.rss / (1024 * 1024),
            process_memory_percent=(process_memory.rss / memory.total) * 100,
            gc_collections=gc_stats,
            gc_collected=gc_collected,
            gc_uncollectable=gc_uncollectable,
            object_count=len(gc.get_objects()),
            large_objects_count=self._count_large_objects(),
            weak_references_count=tracker_stats["tracked_objects"]
        )
    
    def _count_large_objects(self) -> int:
        """Count objects larger than threshold."""
        large_count = 0
        threshold_bytes = self.thresholds.max_object_size_mb * 1024 * 1024
        
        for obj in gc.get_objects():
            try:
                if sys.getsizeof(obj) > threshold_bytes:
                    large_count += 1
            except Exception:
                # Some objects don't support getsizeof
                pass
        
        return large_count
    
    async def force_garbage_collection(self) -> Dict[str, int]:
        """Force garbage collection and return collected counts."""
        logger.debug("Forcing garbage collection")
        
        # Run in thread to avoid blocking
        def run_gc():
            collected = {}
            for generation in range(3):
                collected[generation] = gc.collect(generation)
            return collected
        
        loop = asyncio.get_event_loop()
        collected = await loop.run_in_executor(None, run_gc)
        
        total_collected = sum(collected.values())
        if total_collected > 0:
            logger.info(f"Garbage collection freed {total_collected} objects")
        
        return collected
    
    async def cleanup_resources(self) -> Dict[str, int]:
        """Clean up various resources to free memory."""
        logger.info("Running resource cleanup")
        
        cleanup_stats = {
            "weak_references_cleaned": 0,
            "gc_objects_collected": 0,
            "cache_entries_cleared": 0
        }
        
        # Clean up dead weak references
        cleanup_stats["weak_references_cleaned"] = self.tracker.cleanup_dead_references()
        
        # Force garbage collection
        gc_collected = await self.force_garbage_collection()
        cleanup_stats["gc_objects_collected"] = sum(gc_collected.values())
        
        # Notify external systems to clean up caches
        # This would trigger cache cleanup in other components
        await self._notify_cleanup_needed()
        
        logger.info(f"Resource cleanup completed: {cleanup_stats}")
        return cleanup_stats
    
    async def _notify_cleanup_needed(self) -> None:
        """Notify other components that cleanup is needed."""
        # This would integrate with cache managers and other components
        # For now, we'll just emit a log message
        logger.debug("Notifying components to clean up resources")
    
    def register_callback(self, callback: Callable[[MemoryStats], None]) -> None:
        """Register a callback for memory statistics updates."""
        self._callbacks.append(callback)
    
    def unregister_callback(self, callback: Callable[[MemoryStats], None]) -> None:
        """Unregister a callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def get_stats_history(self, limit: Optional[int] = None) -> List[MemoryStats]:
        """Get memory statistics history."""
        if limit:
            return self._stats_history[-limit:]
        return self._stats_history.copy()
    
    def get_memory_trend(self, window_minutes: int = 10) -> Dict[str, float]:
        """Get memory usage trend over time window."""
        if not self._stats_history:
            return {"trend": 0.0, "average": 0.0, "peak": 0.0}
        
        cutoff_time = datetime.now() - timedelta(minutes=window_minutes)
        recent_stats = [
            stats for stats in self._stats_history
            if stats.timestamp >= cutoff_time
        ]
        
        if len(recent_stats) < 2:
            return {"trend": 0.0, "average": 0.0, "peak": 0.0}
        
        # Calculate trend (change per minute)
        first_usage = recent_stats[0].process_memory_percent
        last_usage = recent_stats[-1].process_memory_percent
        time_diff = (recent_stats[-1].timestamp - recent_stats[0].timestamp).total_seconds() / 60
        trend = (last_usage - first_usage) / time_diff if time_diff > 0 else 0.0
        
        # Calculate average and peak
        usage_values = [stats.process_memory_percent for stats in recent_stats]
        average = sum(usage_values) / len(usage_values)
        peak = max(usage_values)
        
        return {
            "trend": trend,
            "average": average,
            "peak": peak,
            "samples": len(recent_stats)
        }
    
    def track_object(self, obj: Any) -> None:
        """Track an object for memory monitoring."""
        self.tracker.track_object(obj)
    
    async def optimize_memory(self) -> Dict[str, Any]:
        """Perform comprehensive memory optimization."""
        logger.info("Starting comprehensive memory optimization")
        
        initial_stats = await self.get_memory_stats()
        
        # Run cleanup
        cleanup_stats = await self.cleanup_resources()
        
        # Wait a moment for cleanup to take effect
        await asyncio.sleep(1)
        
        final_stats = await self.get_memory_stats()
        
        optimization_result = {
            "initial_memory_mb": initial_stats.process_memory_mb,
            "final_memory_mb": final_stats.process_memory_mb,
            "memory_freed_mb": initial_stats.process_memory_mb - final_stats.process_memory_mb,
            "cleanup_stats": cleanup_stats,
            "optimization_timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Memory optimization completed: freed {optimization_result['memory_freed_mb']:.2f} MB")
        return optimization_result


# Global memory optimizer instance
memory_optimizer = MemoryOptimizer()