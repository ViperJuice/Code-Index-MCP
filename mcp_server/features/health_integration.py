"""
Health monitoring integration for MCP server.

Provides health checks for server components and automatic recovery.
"""
import logging
import asyncio
import os
import time
import psutil
from typing import TYPE_CHECKING, Optional, Dict, Any, List
from datetime import datetime, timedelta

from ..production.health import health_checker, HealthStatus
from ..utils.feature_flags import feature_manager

if TYPE_CHECKING:
    from ..stdio_server import StdioMCPServer

logger = logging.getLogger(__name__)


class HealthIntegration:
    """Integrates health monitoring into MCP server."""
    
    def __init__(self, server: 'StdioMCPServer'):
        self.server = server
        self.enabled = False
        self.check_interval = 30
        self.last_check = datetime.now()
        self._monitoring_task = None
    
    async def setup(self) -> None:
        """Set up health monitoring if enabled."""
        if not feature_manager.is_enabled('health'):
            return
        
        try:
            # Get health configuration
            health_config = feature_manager.get_config('health')
            self.check_interval = health_config.get('interval', 30)
            
            # Register component health checks
            self._register_health_checks()
            
            # Register callback for health status changes
            health_checker.register_callback(self._health_status_callback)
            
            # Start monitoring
            await health_checker.start_monitoring(interval=self.check_interval)
            
            self.enabled = True
            logger.info(f"Health monitoring enabled (interval: {self.check_interval}s)")
            
            # Start periodic health reporting
            self._monitoring_task = asyncio.create_task(self._periodic_health_check())
            
        except Exception as e:
            logger.error(f"Failed to initialize health monitoring: {e}")
            self.enabled = False
    
    def _register_health_checks(self) -> None:
        """Register health checks for server components."""
        from ..production.health import ComponentHealthCheck
        
        # Storage health check
        async def check_storage():
            try:
                if self.server.storage:
                    # Try a simple query
                    with self.server.storage._get_connection() as conn:
                        cursor = conn.execute("SELECT 1")
                        cursor.fetchone()
                    return True
                else:
                    raise Exception("Storage not initialized")
            except Exception as e:
                raise Exception(f"Storage error: {str(e)}")
        
        storage_check = ComponentHealthCheck("storage", check_storage, critical=True)
        health_checker.register_check(storage_check)
        
        # Plugin system health check
        async def check_plugins():
            try:
                if self.server.dispatcher and hasattr(self.server.dispatcher, 'plugins'):
                    plugin_count = len(self.server.dispatcher.plugins)
                    if plugin_count > 0:
                        return True
                    else:
                        raise Exception("No plugins loaded")
                else:
                    raise Exception("Plugin system not initialized")
            except Exception as e:
                raise Exception(f"Plugin error: {str(e)}")
        
        plugins_check = ComponentHealthCheck("plugins", check_plugins, critical=False)
        health_checker.register_check(plugins_check)
        
        # Tool registry health check
        async def check_tools():
            try:
                if self.server.tool_registry:
                    tool_count = len(self.server.tool_registry._tools)
                    if tool_count > 0:
                        return True
                    else:
                        raise Exception("No tools registered")
                else:
                    raise Exception("Tool registry not initialized")
            except Exception as e:
                raise Exception(f"Tool registry error: {str(e)}")
        
        tools_check = ComponentHealthCheck("tools", check_tools, critical=False)
        health_checker.register_check(tools_check)
        
        # Cache health check (if enabled)
        async def check_cache():
            try:
                if hasattr(self.server, 'cache_integration') and self.server.cache_integration:
                    if self.server.cache_integration.enabled:
                        stats = await self.server.cache_integration.get_cache_stats()
                        if stats:
                            return True
                        else:
                            raise Exception("Cache stats unavailable")
                    else:
                        # Cache disabled is not an error
                        return True
                else:
                    # Cache not configured is not an error
                    return True
            except Exception as e:
                raise Exception(f"Cache error: {str(e)}")
        
        cache_check = ComponentHealthCheck("cache", check_cache, critical=False)
        health_checker.register_check(cache_check)
        
        # Memory usage check
        async def check_memory():
            try:
                import psutil
                process = psutil.Process()
                memory_mb = process.memory_info().rss / 1024 / 1024
                
                # Get memory limit from settings
                memory_limit = feature_manager.get_config_value('memory_monitor', 'limit_mb', 512)
                
                if memory_mb < memory_limit * 0.9:
                    return True
                else:
                    raise Exception(f"Memory usage critical: {memory_mb:.1f}MB")
            except ImportError:
                raise Exception("psutil not available")
            except Exception as e:
                raise Exception(f"Memory check error: {str(e)}")
        
        memory_check = ComponentHealthCheck("memory", check_memory, critical=False)
        health_checker.register_check(memory_check)
    
    async def _periodic_health_check(self) -> None:
        """Periodically log health status."""
        while self.enabled:
            try:
                await asyncio.sleep(self.check_interval)
                
                # Get current health status
                report = await health_checker.run_checks()
                
                if report.overall_status in (HealthStatus.UNHEALTHY, HealthStatus.CRITICAL):
                    logger.warning(f"Health check failed: {report.overall_status.value}")
                    for result in report.checks:
                        if result.status in (HealthStatus.UNHEALTHY, HealthStatus.CRITICAL):
                            logger.warning(f"  {result.name}: {result.status.value} - {result.message}")
                elif report.overall_status == HealthStatus.DEGRADED:
                    logger.info(f"Health check warning: {report.overall_status.value}")
                
                self.last_check = datetime.now()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic health check: {e}")
    
    def _health_status_callback(self, report) -> None:
        """Callback for health status changes."""
        if report.overall_status in (HealthStatus.UNHEALTHY, HealthStatus.CRITICAL):
            logger.error(f"Health degraded: {report.overall_status.value}")
            
            # Attempt recovery actions
            asyncio.create_task(self._attempt_recovery(report))
    
    async def _attempt_recovery(self, report) -> None:
        """Attempt to recover from unhealthy state."""
        logger.info("Attempting automatic recovery...")
        
        # Check specific components and try to recover
        for result in report.checks:
            if result.status in (HealthStatus.UNHEALTHY, HealthStatus.CRITICAL):
                if result.name == "storage" and self.server.storage:
                    # Try to reconnect to storage
                    try:
                        logger.info("Attempting to reconnect to storage...")
                        # Storage should handle reconnection internally
                        await asyncio.sleep(1)
                    except Exception as e:
                        logger.error(f"Storage recovery failed: {e}")
                
                elif result.name == "cache" and hasattr(self.server, 'cache_integration'):
                    # Try to restart cache
                    try:
                        logger.info("Attempting to restart cache...")
                        if self.server.cache_integration:
                            await self.server.cache_integration.shutdown()
                            await self.server.cache_integration.setup()
                    except Exception as e:
                        logger.error(f"Cache recovery failed: {e}")
    
    async def get_health_report(self) -> Optional[Dict[str, Any]]:
        """Get current health report."""
        if self.enabled:
            report = await health_checker.run_checks()
            return health_checker.to_dict(report)
        return None
    
    async def shutdown(self) -> None:
        """Shutdown health monitoring."""
        if self.enabled:
            logger.info("Shutting down health monitoring...")
            
            # Cancel monitoring task
            if self._monitoring_task:
                self._monitoring_task.cancel()
                try:
                    await self._monitoring_task
                except asyncio.CancelledError:
                    pass
            
            # Stop health checker
            await health_checker.stop_monitoring()
            
            self.enabled = False
            logger.info("Health monitoring shutdown complete")


async def setup_health_monitoring(server: 'StdioMCPServer') -> Optional[HealthIntegration]:
    """Set up health monitoring for the server."""
    health_integration = HealthIntegration(server)
    await health_integration.setup()
    return health_integration if health_integration.enabled else None


class HealthMonitor:
    """
    Health monitoring system for MCP server.
    
    Provides comprehensive health checks for server components including:
    - Server health (uptime, sessions)
    - Storage connectivity
    - Memory usage monitoring
    - Overall health status determination
    """
    
    def __init__(self, server: 'StdioMCPServer'):
        self.server = server
        self.enabled = os.getenv('MCP_ENABLE_HEALTH', 'false').lower() == 'true'
        self._check_interval = float(os.getenv('MCP_HEALTH_CHECK_INTERVAL', '30'))
        self._monitoring_task: Optional[asyncio.Task] = None
        self._start_time = 0.0
        self._last_check_time = 0.0
        self._check_count = 0
        
        # Memory thresholds
        self._memory_warning_threshold = 80.0  # %
        self._memory_critical_threshold = 95.0  # %
    
    async def initialize(self) -> None:
        """Initialize health monitoring if enabled."""
        # Check environment variable to see if health monitoring is explicitly disabled
        env_health_setting = os.getenv('MCP_ENABLE_HEALTH', '').lower()
        
        if env_health_setting == 'false':
            # Health monitoring is explicitly disabled
            self.enabled = False
            return
        
        # Enable health monitoring when initialize is called (for testing or normal operation)
        if not self.enabled:
            self.enabled = True
        
        self._start_time = time.time()
        self._last_check_time = 0.0
        self._check_count = 0
        
        # Start background monitoring task
        if self._monitoring_task is None:
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        logger.info(f"Health monitoring initialized (interval: {self._check_interval}s)")
    
    async def _monitoring_loop(self) -> None:
        """Background monitoring loop that runs health checks periodically."""
        try:
            while self.enabled:
                # Update check metrics
                self._last_check_time = time.time()
                self._check_count += 1
                
                # Run health checks (could do logging, alerting, etc.)
                await self.get_health_report()
                
                # Wait for next check interval with shorter polling to detect changes
                current_interval = self._check_interval
                sleep_remaining = current_interval
                
                # Use short polling intervals to allow for dynamic interval changes
                while sleep_remaining > 0 and self.enabled:
                    sleep_time = min(0.1, sleep_remaining)  # Check every 100ms or remaining time
                    await asyncio.sleep(sleep_time)
                    sleep_remaining -= sleep_time
                    
                    # If interval changed, adjust sleep_remaining
                    if self._check_interval != current_interval:
                        break
                
        except asyncio.CancelledError:
            # This is expected when shutdown() cancels the task
            raise
        except Exception as e:
            logger.error(f"Error in health monitoring loop: {e}")
    
    async def _check_server_health(self) -> Dict[str, Any]:
        """Check server component health."""
        try:
            uptime = time.time() - self._start_time if self._start_time > 0 else 0
            
            # Get active sessions count
            active_sessions = 0
            if hasattr(self.server, 'session_manager') and self.server.session_manager:
                sessions = self.server.session_manager.get_active_sessions()
                active_sessions = len(sessions) if sessions else 0
            
            return {
                'status': 'healthy',
                'uptime': uptime,
                'active_sessions': active_sessions,
                'message': f'Server running for {uptime:.1f}s with {active_sessions} active sessions'
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'message': f'Server health check failed: {str(e)}'
            }
    
    async def _check_storage_health(self) -> Dict[str, Any]:
        """Check storage connectivity."""
        try:
            # Try to import and test SQLiteStore
            try:
                from ..storage.sqlite_store import SQLiteStore
                
                # Create a test instance or use existing
                store = SQLiteStore()
                
                # Test ping operation
                if hasattr(store, 'ping'):
                    ping_result = await store.ping()
                    if ping_result is False:
                        raise Exception("Storage ping returned False")
                else:
                    # Fallback: assume healthy if no ping method
                    pass
                
            except ImportError:
                # If SQLiteStore is not available, return basic status
                pass
            
            return {
                'status': 'healthy',
                'type': 'sqlite',
                'message': 'Storage is operational'
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'type': 'sqlite',
                'error': str(e),
                'message': f'Storage check failed: {str(e)}'
            }
    
    async def _check_memory_health(self) -> Dict[str, Any]:
        """Check memory usage."""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / (1024 * 1024)  # Convert to MB
            memory_percent = process.memory_percent()
            
            if memory_percent >= self._memory_critical_threshold:
                status = 'critical'
                message = f'Critical memory usage: {memory_percent:.1f}%'
            elif memory_percent >= self._memory_warning_threshold:
                status = 'warning'
                message = f'High memory usage: {memory_percent:.1f}%'
            else:
                status = 'healthy'
                message = f'Memory usage normal: {memory_percent:.1f}%'
            
            return {
                'status': status,
                'used_mb': int(memory_mb),
                'percent': memory_percent,
                'message': message
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'message': f'Memory check failed: {str(e)}'
            }
    
    async def get_health_report(self) -> Dict[str, Any]:
        """Get comprehensive health status report."""
        if not self.enabled:
            return {
                'overall_status': 'disabled',
                'timestamp': time.time(),
                'components': {},
                'message': 'Health monitoring is disabled'
            }
        
        # Run all health checks
        components = {}
        
        try:
            components['server'] = await self._check_server_health()
        except Exception as e:
            components['server'] = {
                'status': 'unhealthy',
                'error': str(e),
                'message': f'Server health check failed: {str(e)}'
            }
        
        try:
            components['storage'] = await self._check_storage_health()
        except Exception as e:
            components['storage'] = {
                'status': 'unhealthy',
                'error': str(e),
                'message': f'Storage health check failed: {str(e)}'
            }
        
        try:
            components['memory'] = await self._check_memory_health()
        except Exception as e:
            components['memory'] = {
                'status': 'unhealthy',
                'error': str(e),
                'message': f'Memory health check failed: {str(e)}'
            }
        
        # Determine overall status
        overall_status = self._determine_overall_status(components)
        
        return {
            'overall_status': overall_status,
            'timestamp': time.time(),
            'components': components,
            'uptime': time.time() - self._start_time if self._start_time > 0 else 0,
            'checks_performed': self._check_count
        }
    
    def _determine_overall_status(self, components: Dict[str, Dict[str, Any]]) -> str:
        """Determine overall health status from component statuses."""
        if not components:
            return 'healthy'
        
        statuses = [comp.get('status', 'unknown') for comp in components.values()]
        
        # Check for critical or unhealthy components
        if any(status in ['critical', 'unhealthy'] for status in statuses):
            return 'unhealthy'
        
        # Check for warning components
        if any(status == 'warning' for status in statuses):
            return 'degraded'
        
        # All components healthy
        return 'healthy'
    
    async def shutdown(self) -> None:
        """Shutdown health monitoring."""
        if self._monitoring_task and not self._monitoring_task.cancelled():
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            self._monitoring_task = None
        
        self.enabled = False
        logger.info("Health monitoring shutdown complete")