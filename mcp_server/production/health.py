"""
Health checking system for MCP server.

Provides comprehensive health monitoring and reporting.
"""

import asyncio
import time
import logging
from typing import Dict, List, Optional, Any, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import psutil
import json

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health check status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    name: str
    status: HealthStatus
    message: str
    duration_ms: float
    timestamp: datetime = field(default_factory=datetime.now)
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class HealthReport:
    """Overall health report."""
    overall_status: HealthStatus
    checks: List[HealthCheckResult]
    timestamp: datetime = field(default_factory=datetime.now)
    system_info: Dict[str, Any] = field(default_factory=dict)
    uptime_seconds: float = 0.0
    version: str = "1.0.0"


class HealthCheck:
    """Base health check implementation."""
    
    def __init__(self, name: str, timeout: float = 5.0, critical: bool = False):
        self.name = name
        self.timeout = timeout
        self.critical = critical
        self._last_result: Optional[HealthCheckResult] = None
        self._failure_count = 0
        self._last_success_time: Optional[datetime] = None
    
    async def run(self) -> HealthCheckResult:
        """Run the health check."""
        start_time = time.time()
        
        try:
            await asyncio.wait_for(self.check(), timeout=self.timeout)
            duration_ms = (time.time() - start_time) * 1000
            
            result = HealthCheckResult(
                name=self.name,
                status=HealthStatus.HEALTHY,
                message="Check passed",
                duration_ms=duration_ms
            )
            
            self._failure_count = 0
            self._last_success_time = datetime.now()
            
        except asyncio.TimeoutError:
            duration_ms = (time.time() - start_time) * 1000
            self._failure_count += 1
            
            result = HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Check timed out after {self.timeout}s",
                duration_ms=duration_ms,
                error="timeout"
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self._failure_count += 1
            
            # Determine status based on failure count and criticality
            if self._failure_count >= 3:
                status = HealthStatus.CRITICAL if self.critical else HealthStatus.UNHEALTHY
            else:
                status = HealthStatus.DEGRADED
            
            result = HealthCheckResult(
                name=self.name,
                status=status,
                message=f"Check failed: {str(e)}",
                duration_ms=duration_ms,
                error=str(e)
            )
        
        self._last_result = result
        return result
    
    async def check(self) -> None:
        """Override this method to implement the actual check."""
        raise NotImplementedError
    
    @property
    def last_result(self) -> Optional[HealthCheckResult]:
        """Get the last check result."""
        return self._last_result
    
    @property
    def failure_count(self) -> int:
        """Get consecutive failure count."""
        return self._failure_count


class DatabaseHealthCheck(HealthCheck):
    """Health check for database connectivity."""
    
    def __init__(self, connection_factory: Callable[[], Awaitable[Any]], 
                 name: str = "database", timeout: float = 5.0):
        super().__init__(name, timeout, critical=True)
        self.connection_factory = connection_factory
    
    async def check(self) -> None:
        """Check database connectivity."""
        conn = await self.connection_factory()
        
        # Try a simple query
        if hasattr(conn, 'execute'):
            await conn.execute("SELECT 1")
        elif hasattr(conn, 'ping'):
            await conn.ping()
        
        # Close connection
        if hasattr(conn, 'close'):
            await conn.close()


class MemoryHealthCheck(HealthCheck):
    """Health check for memory usage."""
    
    def __init__(self, warning_threshold: float = 80.0, critical_threshold: float = 95.0,
                 name: str = "memory", timeout: float = 2.0):
        super().__init__(name, timeout, critical=False)
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
    
    async def check(self) -> None:
        """Check memory usage."""
        memory = psutil.virtual_memory()
        usage_percent = memory.percent
        
        if usage_percent >= self.critical_threshold:
            raise Exception(f"Memory usage critical: {usage_percent:.1f}%")
        elif usage_percent >= self.warning_threshold:
            # This will be caught and result in DEGRADED status
            raise Exception(f"Memory usage high: {usage_percent:.1f}%")


class DiskHealthCheck(HealthCheck):
    """Health check for disk space."""
    
    def __init__(self, path: str = "/", warning_threshold: float = 80.0, 
                 critical_threshold: float = 95.0, name: str = "disk", timeout: float = 2.0):
        super().__init__(name, timeout, critical=False)
        self.path = path
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
    
    async def check(self) -> None:
        """Check disk space."""
        disk = psutil.disk_usage(self.path)
        usage_percent = (disk.used / disk.total) * 100
        
        if usage_percent >= self.critical_threshold:
            raise Exception(f"Disk usage critical: {usage_percent:.1f}%")
        elif usage_percent >= self.warning_threshold:
            raise Exception(f"Disk usage high: {usage_percent:.1f}%")


class ComponentHealthCheck(HealthCheck):
    """Health check for application components."""
    
    def __init__(self, component_name: str, health_function: Callable[[], Awaitable[bool]],
                 name: Optional[str] = None, timeout: float = 5.0, critical: bool = True):
        super().__init__(name or f"component_{component_name}", timeout, critical)
        self.component_name = component_name
        self.health_function = health_function
    
    async def check(self) -> None:
        """Check component health."""
        is_healthy = await self.health_function()
        if not is_healthy:
            raise Exception(f"Component {self.component_name} is unhealthy")


class ExternalServiceHealthCheck(HealthCheck):
    """Health check for external services."""
    
    def __init__(self, service_name: str, url: str, expected_status: int = 200,
                 name: Optional[str] = None, timeout: float = 10.0):
        super().__init__(name or f"service_{service_name}", timeout, critical=False)
        self.service_name = service_name
        self.url = url
        self.expected_status = expected_status
    
    async def check(self) -> None:
        """Check external service health."""
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.get(self.url) as response:
                if response.status != self.expected_status:
                    raise Exception(
                        f"Service {self.service_name} returned status {response.status}, "
                        f"expected {self.expected_status}"
                    )


class HealthChecker:
    """Main health checking system."""
    
    def __init__(self):
        self._checks: Dict[str, HealthCheck] = {}
        self._start_time = time.time()
        self._last_report: Optional[HealthReport] = None
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._check_interval = 30.0  # 30 seconds
        self._callbacks: List[Callable[[HealthReport], None]] = []
    
    def register_check(self, check: HealthCheck) -> None:
        """Register a health check."""
        self._checks[check.name] = check
        logger.info(f"Registered health check: {check.name}")
    
    def unregister_check(self, name: str) -> bool:
        """Unregister a health check."""
        if name in self._checks:
            del self._checks[name]
            logger.info(f"Unregistered health check: {name}")
            return True
        return False
    
    def register_callback(self, callback: Callable[[HealthReport], None]) -> None:
        """Register a callback for health reports."""
        self._callbacks.append(callback)
    
    def unregister_callback(self, callback: Callable[[HealthReport], None]) -> None:
        """Unregister a callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    async def run_checks(self, check_names: Optional[List[str]] = None) -> HealthReport:
        """Run health checks and return a report."""
        if check_names:
            checks_to_run = {name: check for name, check in self._checks.items() 
                           if name in check_names}
        else:
            checks_to_run = self._checks
        
        # Run checks concurrently
        tasks = []
        for check in checks_to_run.values():
            tasks.append(check.run())
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to error results
        check_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                check_name = list(checks_to_run.keys())[i]
                check_results.append(HealthCheckResult(
                    name=check_name,
                    status=HealthStatus.CRITICAL,
                    message=f"Health check failed: {str(result)}",
                    duration_ms=0.0,
                    error=str(result)
                ))
            else:
                check_results.append(result)
        
        # Determine overall status
        overall_status = self._determine_overall_status(check_results)
        
        # Get system information
        system_info = self._get_system_info()
        
        # Create report
        report = HealthReport(
            overall_status=overall_status,
            checks=check_results,
            system_info=system_info,
            uptime_seconds=time.time() - self._start_time
        )
        
        self._last_report = report
        
        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(report)
            except Exception as e:
                logger.error(f"Health check callback error: {e}")
        
        return report
    
    def _determine_overall_status(self, results: List[HealthCheckResult]) -> HealthStatus:
        """Determine overall health status from check results."""
        if not results:
            return HealthStatus.HEALTHY
        
        # Check for critical failures
        critical_failures = [r for r in results if r.status == HealthStatus.CRITICAL]
        if critical_failures:
            return HealthStatus.CRITICAL
        
        # Check for unhealthy status
        unhealthy_checks = [r for r in results if r.status == HealthStatus.UNHEALTHY]
        if unhealthy_checks:
            # If any critical check is unhealthy, overall is unhealthy
            critical_checks = [name for name, check in self._checks.items() if check.critical]
            if any(r.name in critical_checks for r in unhealthy_checks):
                return HealthStatus.UNHEALTHY
            else:
                return HealthStatus.DEGRADED
        
        # Check for degraded status
        degraded_checks = [r for r in results if r.status == HealthStatus.DEGRADED]
        if degraded_checks:
            return HealthStatus.DEGRADED
        
        return HealthStatus.HEALTHY
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Get system information."""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                "cpu_percent": cpu_percent,
                "memory_total_mb": memory.total / (1024 * 1024),
                "memory_used_mb": memory.used / (1024 * 1024),
                "memory_percent": memory.percent,
                "disk_total_gb": disk.total / (1024 * 1024 * 1024),
                "disk_used_gb": disk.used / (1024 * 1024 * 1024),
                "disk_percent": (disk.used / disk.total) * 100,
                "load_average": list(psutil.getloadavg()) if hasattr(psutil, 'getloadavg') else None,
                "process_count": len(psutil.pids())
            }
        except Exception as e:
            logger.warning(f"Failed to get system info: {e}")
            return {"error": str(e)}
    
    async def start_monitoring(self, interval: float = 30.0) -> None:
        """Start continuous health monitoring."""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._check_interval = interval
        self._monitor_task = asyncio.create_task(self._monitoring_loop())
        logger.info(f"Health monitoring started (interval: {interval}s)")
    
    async def stop_monitoring(self) -> None:
        """Stop continuous health monitoring."""
        if not self._monitoring:
            return
        
        self._monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Health monitoring stopped")
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while self._monitoring:
            try:
                await self.run_checks()
                await asyncio.sleep(self._check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
                await asyncio.sleep(self._check_interval)
    
    def get_last_report(self) -> Optional[HealthReport]:
        """Get the last health report."""
        return self._last_report
    
    def get_check_status(self, name: str) -> Optional[HealthCheckResult]:
        """Get status of a specific check."""
        check = self._checks.get(name)
        return check.last_result if check else None
    
    def is_healthy(self) -> bool:
        """Check if the system is healthy overall."""
        if not self._last_report:
            return True  # No checks run yet, assume healthy
        
        return self._last_report.overall_status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]
    
    def to_dict(self, report: Optional[HealthReport] = None) -> Dict[str, Any]:
        """Convert health report to dictionary."""
        if not report:
            report = self._last_report
        
        if not report:
            return {"status": "unknown", "message": "No health checks run"}
        
        return {
            "status": report.overall_status.value,
            "timestamp": report.timestamp.isoformat(),
            "uptime_seconds": report.uptime_seconds,
            "version": report.version,
            "checks": [
                {
                    "name": check.name,
                    "status": check.status.value,
                    "message": check.message,
                    "duration_ms": check.duration_ms,
                    "timestamp": check.timestamp.isoformat(),
                    "details": check.details,
                    "error": check.error
                }
                for check in report.checks
            ],
            "system_info": report.system_info
        }


# Global health checker instance
health_checker = HealthChecker()

# Register default health checks
health_checker.register_check(MemoryHealthCheck())
health_checker.register_check(DiskHealthCheck())