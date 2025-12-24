"""Prometheus-compatible metrics collector implementation."""

import logging
import threading
import time
from collections import defaultdict, deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional

from . import IMetricsCollector

logger = logging.getLogger(__name__)


@dataclass
class CounterMetric:
    """Counter metric that only increases."""

    name: str
    value: float = 0.0
    labels: Dict[str, str] = field(default_factory=dict)

    def increment(self, value: float = 1.0) -> None:
        """Increment the counter by the given value."""
        if value < 0:
            raise ValueError("Counter values can only increase")
        self.value += value


@dataclass
class GaugeMetric:
    """Gauge metric that can increase or decrease."""

    name: str
    value: float = 0.0
    labels: Dict[str, str] = field(default_factory=dict)

    def set(self, value: float) -> None:
        """Set the gauge to the given value."""
        self.value = value

    def increment(self, value: float = 1.0) -> None:
        """Increment the gauge by the given value."""
        self.value += value

    def decrement(self, value: float = 1.0) -> None:
        """Decrement the gauge by the given value."""
        self.value -= value


@dataclass
class HistogramMetric:
    """Histogram metric for observing distributions."""

    name: str
    buckets: List[float] = field(
        default_factory=lambda: [
            0.005,
            0.01,
            0.025,
            0.05,
            0.1,
            0.25,
            0.5,
            1.0,
            2.5,
            5.0,
            10.0,
        ]
    )
    labels: Dict[str, str] = field(default_factory=dict)
    observations: Deque[float] = field(default_factory=deque)
    bucket_counts: Dict[float, int] = field(default_factory=dict)
    total_count: int = 0
    total_sum: float = 0.0

    def __post_init__(self):
        """Initialize bucket counts."""
        for bucket in self.buckets:
            self.bucket_counts[bucket] = 0
        self.bucket_counts[float("inf")] = 0  # +Inf bucket

    def observe(self, value: float) -> None:
        """Observe a value in the histogram."""
        self.observations.append(value)
        self.total_count += 1
        self.total_sum += value

        # Update bucket counts
        for bucket in self.buckets:
            if value <= bucket:
                self.bucket_counts[bucket] += 1
        self.bucket_counts[float("inf")] += 1  # +Inf bucket always gets incremented

        # Keep only recent observations for memory efficiency
        if len(self.observations) > 10000:
            self.observations.popleft()


class PrometheusMetricsCollector(IMetricsCollector):
    """Prometheus-compatible metrics collector."""

    def __init__(self, namespace: str = "mcp_server"):
        """Initialize the metrics collector.

        Args:
            namespace: Namespace prefix for all metrics
        """
        self.namespace = namespace
        self._lock = threading.RLock()
        self._counters: Dict[str, CounterMetric] = {}
        self._gauges: Dict[str, GaugeMetric] = {}
        self._histograms: Dict[str, HistogramMetric] = {}

        # Initialize default metrics
        self._initialize_default_metrics()

    def _initialize_default_metrics(self) -> None:
        """Initialize default system metrics."""
        # HTTP request metrics
        self.increment_counter("http_requests_total", 0, {"method": "GET", "endpoint": "/health"})
        self.set_gauge("http_request_duration_seconds", 0)

        # Plugin metrics
        self.set_gauge("plugins_loaded_total", 0)
        self.set_gauge("plugins_active_total", 0)

        # Indexing metrics
        self.increment_counter("files_indexed_total", 0)
        self.set_gauge("index_size_bytes", 0)
        self.set_gauge("symbols_indexed_total", 0)

        # Database metrics
        self.set_gauge("database_connections_active", 0)
        self.increment_counter("database_queries_total", 0)

        # System metrics
        self.set_gauge("memory_usage_bytes", 0)
        self.set_gauge("cpu_usage_percent", 0)

    def _get_metric_key(self, name: str, labels: Optional[Dict[str, str]] = None) -> str:
        """Generate a unique key for a metric with labels."""
        if labels:
            label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
            return f"{name}#{label_str}"
        return name

    def increment_counter(
        self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Increment a counter metric."""
        if value < 0:
            raise ValueError("Counter values can only increase")

        full_name = f"{self.namespace}_{name}"
        key = self._get_metric_key(full_name, labels)

        with self._lock:
            if key not in self._counters:
                self._counters[key] = CounterMetric(full_name, 0.0, labels or {})
            self._counters[key].increment(value)

    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Set a gauge metric value."""
        full_name = f"{self.namespace}_{name}"
        key = self._get_metric_key(full_name, labels)

        with self._lock:
            if key not in self._gauges:
                self._gauges[key] = GaugeMetric(full_name, 0.0, labels or {})
            self._gauges[key].set(value)

    def observe_histogram(
        self, name: str, value: float, labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Observe a value in a histogram metric."""
        full_name = f"{self.namespace}_{name}"
        key = self._get_metric_key(full_name, labels)

        with self._lock:
            if key not in self._histograms:
                self._histograms[key] = HistogramMetric(full_name, labels=labels or {})
            self._histograms[key].observe(value)

    @contextmanager
    def time_function(self, name: str, labels: Optional[Dict[str, str]] = None):
        """Context manager for timing function execution."""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.observe_histogram(f"{name}_duration_seconds", duration, labels)

    def get_metrics(self) -> str:
        """Get all metrics in Prometheus format."""
        lines = []

        with self._lock:
            # Export counters
            for counter in self._counters.values():
                help_line = f"# HELP {counter.name} Counter metric"
                type_line = f"# TYPE {counter.name} counter"
                lines.extend([help_line, type_line])

                if counter.labels:
                    label_str = ",".join(f'{k}="{v}"' for k, v in counter.labels.items())
                    metric_line = f"{counter.name}{{{label_str}}} {counter.value}"
                else:
                    metric_line = f"{counter.name} {counter.value}"
                lines.append(metric_line)
                lines.append("")  # Empty line between metrics

            # Export gauges
            for gauge in self._gauges.values():
                help_line = f"# HELP {gauge.name} Gauge metric"
                type_line = f"# TYPE {gauge.name} gauge"
                lines.extend([help_line, type_line])

                if gauge.labels:
                    label_str = ",".join(f'{k}="{v}"' for k, v in gauge.labels.items())
                    metric_line = f"{gauge.name}{{{label_str}}} {gauge.value}"
                else:
                    metric_line = f"{gauge.name} {gauge.value}"
                lines.append(metric_line)
                lines.append("")

            # Export histograms
            for histogram in self._histograms.values():
                help_line = f"# HELP {histogram.name} Histogram metric"
                type_line = f"# TYPE {histogram.name} histogram"
                lines.extend([help_line, type_line])

                # Export buckets
                for bucket in sorted(histogram.buckets) + [float("inf")]:
                    bucket_count = histogram.bucket_counts.get(bucket, 0)
                    if histogram.labels:
                        label_str = ",".join(f'{k}="{v}"' for k, v in histogram.labels.items())
                        bucket_line = (
                            f'{histogram.name}_bucket{{le="{bucket}",{label_str}}} {bucket_count}'
                        )
                    else:
                        bucket_line = f'{histogram.name}_bucket{{le="{bucket}"}} {bucket_count}'
                    lines.append(bucket_line)

                # Export count and sum
                if histogram.labels:
                    label_str = ",".join(f'{k}="{v}"' for k, v in histogram.labels.items())
                    count_line = f"{histogram.name}_count{{{label_str}}} {histogram.total_count}"
                    sum_line = f"{histogram.name}_sum{{{label_str}}} {histogram.total_sum}"
                else:
                    count_line = f"{histogram.name}_count {histogram.total_count}"
                    sum_line = f"{histogram.name}_sum {histogram.total_sum}"
                lines.extend([count_line, sum_line, ""])

        return "\n".join(lines)

    def get_metric_families(self) -> List[Dict[str, Any]]:
        """Get all metric families as structured data."""
        families = []

        with self._lock:
            # Group metrics by name
            metric_groups = defaultdict(list)

            # Group counters
            for counter in self._counters.values():
                metric_groups[counter.name].append(
                    {
                        "type": "counter",
                        "value": counter.value,
                        "labels": counter.labels,
                    }
                )

            # Group gauges
            for gauge in self._gauges.values():
                metric_groups[gauge.name].append(
                    {"type": "gauge", "value": gauge.value, "labels": gauge.labels}
                )

            # Group histograms
            for histogram in self._histograms.values():
                metric_groups[histogram.name].append(
                    {
                        "type": "histogram",
                        "buckets": histogram.bucket_counts,
                        "count": histogram.total_count,
                        "sum": histogram.total_sum,
                        "labels": histogram.labels,
                    }
                )

            # Convert to family format
            for name, metrics in metric_groups.items():
                family = {
                    "name": name,
                    "help": f"Metric {name}",
                    "type": metrics[0]["type"],
                    "samples": metrics,
                }
                families.append(family)

        return families

    def get_metric_value(
        self, name: str, labels: Optional[Dict[str, str]] = None
    ) -> Optional[float]:
        """Get the current value of a specific metric.

        Args:
            name: Metric name (without namespace prefix)
            labels: Optional labels to match

        Returns:
            Current metric value if found, None otherwise
        """
        full_name = f"{self.namespace}_{name}"
        key = self._get_metric_key(full_name, labels)

        with self._lock:
            # Check counters
            if key in self._counters:
                return self._counters[key].value

            # Check gauges
            if key in self._gauges:
                return self._gauges[key].value

            # For histograms, return the count
            if key in self._histograms:
                return float(self._histograms[key].total_count)

        return None

    def reset_metrics(self) -> None:
        """Reset all metrics (useful for testing)."""
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()
            self._initialize_default_metrics()

    def get_stats(self) -> Dict[str, int]:
        """Get collector statistics.

        Returns:
            Dictionary with metric counts by type
        """
        with self._lock:
            return {
                "counters": len(self._counters),
                "gauges": len(self._gauges),
                "histograms": len(self._histograms),
                "total": len(self._counters) + len(self._gauges) + len(self._histograms),
            }


# Global metrics collector instance
_metrics_collector: Optional[PrometheusMetricsCollector] = None


def get_metrics_collector() -> PrometheusMetricsCollector:
    """Get the global metrics collector instance.

    Returns:
        Global metrics collector instance
    """
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = PrometheusMetricsCollector()
        logger.info("Initialized global metrics collector")
    return _metrics_collector


def set_metrics_collector(collector: PrometheusMetricsCollector) -> None:
    """Set the global metrics collector instance.

    Args:
        collector: Metrics collector instance to set as global
    """
    global _metrics_collector
    _metrics_collector = collector
    logger.info("Set global metrics collector")
