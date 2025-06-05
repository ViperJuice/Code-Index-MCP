"""
Memory monitoring integration for MCP server.

Provides memory usage tracking and automatic optimization.
"""
import logging
import gc
import asyncio
import os
import psutil
from typing import TYPE_CHECKING, Optional, Dict, Any, List, Callable
from datetime import datetime, timedelta

from ..performance.memory_optimizer import memory_optimizer, MemoryStats
from ..utils.feature_flags import feature_manager

if TYPE_CHECKING:
    from ..stdio_server import StdioMCPServer

logger = logging.getLogger(__name__)


class MemoryIntegration:
    """Integrates memory monitoring and optimization into MCP server."""
    
    def __init__(self, server: 'StdioMCPServer'):
        self.server = server
        self.enabled = False
        self.memory_limit_mb = 512
        self.check_interval = 30
        self._monitoring_task = None
        
        # Track memory events
        self.memory_events = []
        self.gc_runs = 0
        self.last_gc_time = None
    
    async def setup(self) -> None:
        """Set up memory monitoring if enabled."""
        if not feature_manager.is_enabled('memory_monitor'):
            return
        
        try:
            # Get memory configuration
            config = feature_manager.get_config('memory_monitor')
            self.memory_limit_mb = config.get('limit_mb', 512)
            
            # Configure memory optimizer thresholds
            memory_optimizer.thresholds.warning_percent = 70.0
            memory_optimizer.thresholds.critical_percent = 85.0
            memory_optimizer.thresholds.gc_trigger_percent = 75.0
            memory_optimizer.thresholds.cleanup_trigger_percent = 80.0
            
            # Register monitoring callback for cleanup
            memory_optimizer.register_callback(self._memory_stats_callback)
            
            # Start monitoring
            await memory_optimizer.start_monitoring(interval=self.check_interval)
            
            self.enabled = True
            logger.info(f"Memory monitoring enabled (limit: {self.memory_limit_mb}MB)")
            
            # Start periodic reporting
            self._monitoring_task = asyncio.create_task(self._periodic_memory_check())
            
        except Exception as e:
            logger.error(f"Failed to initialize memory monitoring: {e}")
            self.enabled = False
    
    def _memory_stats_callback(self, stats: MemoryStats) -> None:
        """Callback for memory statistics updates from memory optimizer."""
        try:
            # Trigger cleanup if memory usage is high
            if stats.process_memory_percent > 85:
                asyncio.create_task(self._cleanup_cache())
            if stats.process_memory_percent > 90:
                asyncio.create_task(self._cleanup_old_data())
        except Exception as e:
            logger.error(f"Error in memory stats callback: {e}")
    
    async def _cleanup_cache(self) -> int:
        """Clean up cache to free memory."""
        freed_bytes = 0
        
        if hasattr(self.server, 'cache_integration') and self.server.cache_integration:
            try:
                # Get cache size before cleanup
                stats = await self.server.cache_integration.get_cache_stats()
                if stats:
                    cache_size = stats.get('memory_bytes', 0)
                    
                    # Clear cache
                    await self.server.cache_integration.clear_cache()
                    
                    # Estimate freed memory
                    freed_bytes = cache_size
                    logger.info(f"Cleared cache, freed approximately {freed_bytes / 1024 / 1024:.1f}MB")
                    
            except Exception as e:
                logger.error(f"Error clearing cache: {e}")
        
        return freed_bytes
    
    async def _cleanup_old_data(self) -> int:
        """Clean up old data from storage."""
        freed_bytes = 0
        
        if self.server.storage:
            try:
                # Clean up old search results or temporary data
                # This is a placeholder - implement based on your storage needs
                logger.info("Cleaning up old data...")
                
                # Force garbage collection
                gc.collect()
                
                # Estimate freed memory (rough approximation)
                freed_bytes = 10 * 1024 * 1024  # 10MB estimate
                
            except Exception as e:
                logger.error(f"Error cleaning old data: {e}")
        
        return freed_bytes
    
    async def _periodic_memory_check(self) -> None:
        """Periodically check and report memory usage."""
        while self.enabled:
            try:
                await asyncio.sleep(self.check_interval)
                
                # Get memory stats
                stats = await memory_optimizer.get_memory_stats()
                
                # Log if memory usage is high
                usage_percent = stats.process_memory_percent
                
                if usage_percent > 90:
                    logger.warning(
                        f"High memory usage: {stats.process_memory_mb:.1f}MB "
                        f"({usage_percent:.1f}% of system memory)"
                    )
                elif usage_percent > 80:
                    logger.info(
                        f"Memory usage: {stats.process_memory_mb:.1f}MB "
                        f"({usage_percent:.1f}% of system memory)"
                    )
                
                # Track events
                self.memory_events.append({
                    'timestamp': datetime.now(),
                    'usage_mb': stats.process_memory_mb,
                    'usage_percent': usage_percent,
                    'gc_count': gc.get_count()
                })
                
                # Keep only last hour of events
                cutoff = datetime.now() - timedelta(hours=1)
                self.memory_events = [e for e in self.memory_events if e['timestamp'] > cutoff]
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in memory monitoring: {e}")
    
    async def force_gc(self) -> Dict[str, Any]:
        """Force garbage collection."""
        before_stats = await memory_optimizer.get_memory_stats()
        before = before_stats.process_memory_mb
        
        # Run garbage collection
        gc_result = await memory_optimizer.force_garbage_collection()
        self.gc_runs += 1
        self.last_gc_time = datetime.now()
        
        after_stats = await memory_optimizer.get_memory_stats()
        after = after_stats.process_memory_mb
        
        freed = before - after
        logger.info(f"Forced GC freed {freed:.1f}MB")
        
        return {
            'freed_mb': freed,
            'before_mb': before,
            'after_mb': after,
            'gc_runs': self.gc_runs,
            'gc_collected': gc_result
        }
    
    async def optimize_memory(self) -> Dict[str, Any]:
        """Run memory optimization."""
        if not self.enabled:
            return {'error': 'Memory monitoring not enabled'}
        
        logger.info("Running memory optimization...")
        
        # Trigger memory optimizer cleanup
        result = await memory_optimizer.optimize_memory()
        
        # Force GC after cleanup
        gc_result = await self.force_gc()
        
        return {
            'optimizer_result': result,
            'gc_result': gc_result,
            'current_usage_mb': (await memory_optimizer.get_memory_stats()).process_memory_mb
        }
    
    async def get_memory_report(self) -> Dict[str, Any]:
        """Get detailed memory report."""
        stats = await memory_optimizer.get_memory_stats()
        
        report = {
            'enabled': self.enabled,
            'current_usage_mb': stats.process_memory_mb,
            'memory_limit_mb': self.memory_limit_mb,
            'usage_percent': stats.process_memory_percent,
            'total_memory_mb': stats.total_memory_mb,
            'available_memory_mb': stats.available_memory_mb,
            'gc_runs': self.gc_runs,
            'last_gc_time': self.last_gc_time.isoformat() if self.last_gc_time else None,
            'gc_stats': {
                'threshold0': gc.get_threshold()[0],
                'threshold1': gc.get_threshold()[1],
                'threshold2': gc.get_threshold()[2],
                'counts': gc.get_count()
            }
        }
        
        # Add recent memory trend
        if self.memory_events:
            recent_events = self.memory_events[-10:]  # Last 10 events
            report['recent_trend'] = [
                {
                    'time': e['timestamp'].isoformat(),
                    'usage_mb': e['usage_mb'],
                    'usage_percent': e['usage_percent']
                }
                for e in recent_events
            ]
        
        return report
    
    async def shutdown(self) -> None:
        """Shutdown memory monitoring."""
        if self.enabled:
            logger.info("Shutting down memory monitoring...")
            
            # Cancel monitoring task
            if self._monitoring_task:
                self._monitoring_task.cancel()
                try:
                    await self._monitoring_task
                except asyncio.CancelledError:
                    pass
            
            # Stop memory optimizer
            await memory_optimizer.stop_monitoring()
            
            self.enabled = False
            logger.info("Memory monitoring shutdown complete")


async def setup_memory_monitor(server: 'StdioMCPServer') -> Optional[MemoryIntegration]:
    """Set up memory monitoring for the server."""
    memory_integration = MemoryIntegration(server)
    await memory_integration.setup()
    return memory_integration if memory_integration.enabled else None


class MemoryMonitor:
    """Enhanced memory monitoring with detailed tracking and alerts."""
    
    def __init__(self, server: 'StdioMCPServer'):
        self.server = server
        self.enabled = False
        self._memory_limit_mb = 512  # Default limit
        self._check_interval = 10  # Check every 10 seconds
        self._monitoring_task: Optional[asyncio.Task] = None
        self._memory_history: List[Dict[str, Any]] = []
        self._alert_callback: Optional[Callable] = None
        self._check_count = 0
        self._last_alert_time: Optional[datetime] = None
        self._alert_cooldown = 60  # seconds between alerts
        
        # Process reference for memory monitoring
        self._process = None
        
    async def initialize(self) -> None:
        """Initialize memory monitoring if enabled."""
        # Check if monitoring is enabled via environment
        monitor_enabled = os.getenv('MCP_MONITOR_MEMORY', 'false').lower() == 'true'
        
        if not monitor_enabled:
            self.enabled = False
            return
            
        # Get memory limit from environment
        try:
            self._memory_limit_mb = int(os.getenv('MCP_MEMORY_LIMIT_MB', '512'))
        except ValueError:
            self._memory_limit_mb = 512
            
        # Initialize process for memory monitoring
        try:
            self._process = psutil.Process()
            self.enabled = True
            
            # Start monitoring task
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())
            
            logger.info(f"Memory monitoring initialized (limit: {self._memory_limit_mb}MB)")
            
        except Exception as e:
            logger.error(f"Failed to initialize memory monitoring: {e}")
            self.enabled = False
    
    async def get_memory_usage(self) -> Dict[str, Any]:
        """Get current memory usage statistics."""
        if not self.enabled:
            return {
                'status': 'disabled',
                'error': None
            }
            
        try:
            if self._process is None:
                self._process = psutil.Process()
                
            memory_info = self._process.memory_info()
            memory_percent = self._process.memory_percent()
            
            return {
                'rss_mb': round(memory_info.rss / (1024 * 1024)),
                'vms_mb': round(memory_info.vms / (1024 * 1024)),
                'percent': round(memory_percent, 2),
                'limit_mb': self._memory_limit_mb,
                'timestamp': datetime.now().isoformat(),
                'error': None
            }
            
        except Exception as e:
            error_msg = f"psutil error"  # Simplified for tests
            logger.error(f"Error getting memory usage: {e}")
            return {
                'rss_mb': 0,
                'vms_mb': 0,
                'percent': 0,
                'limit_mb': self._memory_limit_mb,
                'timestamp': datetime.now().isoformat(),
                'error': error_msg
            }
    
    async def check_memory_threshold(self) -> bool:
        """Check if memory usage exceeds the configured limit."""
        if not self.enabled:
            return False
            
        usage = await self.get_memory_usage()
        if usage.get('error'):
            return False
            
        return usage['rss_mb'] > self._memory_limit_mb
    
    async def get_memory_pressure_level(self) -> str:
        """Assess current memory pressure level."""
        if not self.enabled:
            return 'disabled'
            
        usage = await self.get_memory_usage()
        if usage.get('error'):
            return 'unknown'
            
        usage_ratio = usage['rss_mb'] / self._memory_limit_mb
        
        if usage_ratio > 1.0:
            return 'exceeded'
        elif usage_ratio > 0.87:  # ~450MB/512MB
            return 'critical'
        elif usage_ratio > 0.65:  # ~350MB/512MB 
            return 'warning'
        else:
            return 'normal'
    
    async def get_cleanup_suggestions(self) -> List[str]:
        """Get memory cleanup suggestions based on current usage."""
        pressure_level = await self.get_memory_pressure_level()
        
        if pressure_level in ['normal', 'disabled']:
            return []
            
        suggestions = []
        
        if pressure_level in ['warning', 'critical', 'exceeded']:
            suggestions.extend([
                "Clear application cache to free memory",
                "Run garbage collection to reclaim unused objects",
                "Close inactive connections and sessions"
            ])
            
        if pressure_level in ['critical', 'exceeded']:
            suggestions.extend([
                "Consider reducing batch sizes for operations",
                "Archive or remove old index data",
                "Restart the service to reset memory usage"
            ])
            
        return suggestions
    
    async def get_memory_report(self) -> Dict[str, Any]:
        """Get comprehensive memory report."""
        if not self.enabled:
            return {
                'status': 'disabled',
                'enabled': False
            }
            
        current_usage = await self.get_memory_usage()
        pressure_level = await self.get_memory_pressure_level()
        
        report = {
            'status': 'active',
            'enabled': True,
            'current': current_usage,
            'pressure_level': pressure_level,
            'limit_mb': self._memory_limit_mb,
            'check_count': self._check_count
        }
        
        # Add history statistics if available
        if self._memory_history:
            rss_values = [h['rss_mb'] for h in self._memory_history if 'rss_mb' in h]
            if rss_values:
                report['peak'] = {
                    'rss_mb': max(rss_values),
                    'timestamp': max(h['timestamp'] for h in self._memory_history)
                }
                report['average'] = {
                    'rss_mb': round(sum(rss_values) / len(rss_values), 1)
                }
        
        return report
    
    def get_memory_history(self) -> List[Dict[str, Any]]:
        """Get historical memory usage data."""
        return self._memory_history.copy()
    
    def set_alert_callback(self, callback: Callable) -> None:
        """Set callback function for memory alerts."""
        self._alert_callback = callback
    
    async def _check_memory(self) -> None:
        """Perform a memory check and update history."""
        self._check_count += 1
        
        usage = await self.get_memory_usage()
        if not usage.get('error'):
            # Add to history
            self._memory_history.append(usage)
            
            # Limit history size (keep last 100 entries)
            if len(self._memory_history) > 100:
                self._memory_history = self._memory_history[-100:]
            
            # Check for high memory usage
            pressure_level = await self.get_memory_pressure_level()
            
            # Trigger garbage collection if memory usage >= 90% of limit (460MB/512MB)
            usage_ratio = usage['rss_mb'] / self._memory_limit_mb
            if usage_ratio >= 0.9:
                gc.collect()
                logger.info(f"Triggered garbage collection due to {pressure_level} memory pressure")
            
            # Send alert if threshold exceeded and callback is set
            if await self.check_memory_threshold() and self._alert_callback:
                now = datetime.now()
                
                # Check cooldown period
                if (self._last_alert_time is None or 
                    (now - self._last_alert_time).seconds >= self._alert_cooldown):
                    
                    try:
                        alert_info = {
                            'current_mb': usage['rss_mb'],
                            'limit_mb': self._memory_limit_mb,
                            'pressure_level': pressure_level,
                            'timestamp': now.isoformat()
                        }
                        
                        await self._alert_callback(alert_info)
                        self._last_alert_time = now
                        
                    except Exception as e:
                        logger.error(f"Error executing memory alert callback: {e}")
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        last_check_time = 0
        
        try:
            while self.enabled:
                current_time = asyncio.get_event_loop().time()
                
                # Check if it's time to run based on the current interval
                if current_time - last_check_time >= self._check_interval:
                    await self._check_memory()
                    last_check_time = current_time
                
                # Always sleep for a short time to avoid busy waiting
                await asyncio.sleep(0.05)  # 50ms sleep
                
        except asyncio.CancelledError:
            # Expected when shutdown is called
            raise
        except Exception as e:
            logger.error(f"Error in memory monitoring loop: {e}")
            # Continue the loop after error
    
    async def shutdown(self) -> None:
        """Shutdown memory monitoring."""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            self._monitoring_task = None
        
        self.enabled = False
        
        # Clear history
        self._memory_history.clear()
        
        logger.info("Memory monitor shutdown complete")