"""Metrics collection system for the MCP Server.

This package provides Prometheus-compatible metrics collection, health checks,
and performance monitoring for all system components.
"""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class HealthStatus(Enum):
    """Health check status enumeration."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


class MetricType(Enum):
    """Types of metrics that can be collected."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class HealthCheckResult:
    """Result of a health check operation."""

    component: str
    status: HealthStatus
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: float = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


@dataclass
class MetricPoint:
    """A single metric data point."""

    name: str
    value: float
    labels: Dict[str, str]
    metric_type: MetricType
    timestamp: float = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


class IMetricsCollector(ABC):
    """Interface for collecting and exposing metrics."""

    @abstractmethod
    def increment_counter(
        self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Increment a counter metric.

        Args:
            name: Metric name
            value: Value to add (default 1.0)
            labels: Optional labels for the metric
        """

    @abstractmethod
    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Set a gauge metric value.

        Args:
            name: Metric name
            value: Value to set
            labels: Optional labels for the metric
        """

    @abstractmethod
    def observe_histogram(
        self, name: str, value: float, labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Observe a value in a histogram metric.

        Args:
            name: Metric name
            value: Value to observe
            labels: Optional labels for the metric
        """

    @abstractmethod
    def time_function(self, name: str, labels: Optional[Dict[str, str]] = None):
        """Context manager for timing function execution.

        Args:
            name: Metric name for the timer
            labels: Optional labels for the metric

        Returns:
            Context manager that records execution time
        """

    @abstractmethod
    def get_metrics(self) -> str:
        """Get all metrics in Prometheus format.

        Returns:
            Prometheus-formatted metrics string
        """

    @abstractmethod
    def get_metric_families(self) -> List[Dict[str, Any]]:
        """Get all metric families as structured data.

        Returns:
            List of metric family dictionaries
        """


class IHealthCheck(ABC):
    """Interface for performing health checks on system components."""

    @abstractmethod
    async def check_component(self, component_name: str) -> HealthCheckResult:
        """Check the health of a specific component.

        Args:
            component_name: Name of the component to check

        Returns:
            Health check result
        """

    @abstractmethod
    async def check_all_components(self) -> List[HealthCheckResult]:
        """Check the health of all registered components.

        Returns:
            List of health check results for all components
        """

    @abstractmethod
    def register_health_check(self, component_name: str, check_func: callable) -> None:
        """Register a health check function for a component.

        Args:
            component_name: Name of the component
            check_func: Async function that returns HealthCheckResult
        """

    @abstractmethod
    def unregister_health_check(self, component_name: str) -> None:
        """Unregister a health check for a component.

        Args:
            component_name: Name of the component
        """

    @abstractmethod
    async def get_overall_health(self) -> HealthCheckResult:
        """Get overall system health status.

        Returns:
            Overall health check result
        """


from .health_check import ComponentHealthChecker  # noqa: E402

# Import implementations
from .metrics_collector import PrometheusMetricsCollector  # noqa: E402


# Factory functions
def get_metrics_collector() -> IMetricsCollector:
    """Get the default metrics collector instance."""
    return PrometheusMetricsCollector()


def get_health_checker() -> IHealthCheck:
    """Get the default health checker instance."""
    return ComponentHealthChecker()


# Export key classes and interfaces
__all__ = [
    "IMetricsCollector",
    "IHealthCheck",
    "HealthStatus",
    "HealthCheckResult",
    "MetricType",
    "MetricPoint",
    "PrometheusMetricsCollector",
    "ComponentHealthChecker",
    "get_metrics_collector",
    "get_health_checker",
]
