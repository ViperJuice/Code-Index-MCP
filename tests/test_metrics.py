"""Comprehensive tests for the metrics collection system."""

import asyncio
import sqlite3
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock

import pytest

from mcp_server.metrics import (
    HealthCheckResult,
    HealthStatus,
)
from mcp_server.metrics.health_check import (
    ComponentHealthChecker,
    get_health_checker,
    set_health_checker,
)
from mcp_server.metrics.metrics_collector import (
    PrometheusMetricsCollector,
    get_metrics_collector,
    set_metrics_collector,
)
from mcp_server.metrics.middleware import (
    BusinessMetricsCollector,
    MetricsMiddleware,
    get_business_metrics,
)


class TestPrometheusMetricsCollector:
    """Test the Prometheus metrics collector implementation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.collector = PrometheusMetricsCollector(namespace="test")

    def test_initialization(self):
        """Test collector initialization."""
        assert self.collector.namespace == "test"
        assert len(self.collector._counters) > 0  # Default metrics initialized
        assert len(self.collector._gauges) > 0

        stats = self.collector.get_stats()
        assert stats["total"] > 0

    def test_counter_metrics(self):
        """Test counter metric operations."""
        # Test increment
        self.collector.increment_counter("test_counter", 5.0)
        value = self.collector.get_metric_value("test_counter")
        assert value == 5.0

        # Test additional increment
        self.collector.increment_counter("test_counter", 3.0)
        value = self.collector.get_metric_value("test_counter")
        assert value == 8.0

        # Test with labels
        self.collector.increment_counter("test_counter", 2.0, {"label": "value1"})
        value = self.collector.get_metric_value("test_counter", {"label": "value1"})
        assert value == 2.0

        # Test negative value rejection
        with pytest.raises(ValueError):
            self.collector.increment_counter("test_counter", -1.0)

    def test_gauge_metrics(self):
        """Test gauge metric operations."""
        # Test set
        self.collector.set_gauge("test_gauge", 10.0)
        value = self.collector.get_metric_value("test_gauge")
        assert value == 10.0

        # Test overwrite
        self.collector.set_gauge("test_gauge", 15.0)
        value = self.collector.get_metric_value("test_gauge")
        assert value == 15.0

        # Test with labels
        self.collector.set_gauge("test_gauge", 20.0, {"env": "test"})
        value = self.collector.get_metric_value("test_gauge", {"env": "test"})
        assert value == 20.0

    def test_histogram_metrics(self):
        """Test histogram metric operations."""
        # Test observations
        values = [0.001, 0.01, 0.1, 1.0, 5.0]
        for val in values:
            self.collector.observe_histogram("test_histogram", val)

        # Check if metric exists (histogram count is returned)
        count = self.collector.get_metric_value("test_histogram")
        assert count == len(values)

        # Test with labels
        self.collector.observe_histogram("test_histogram", 2.5, {"type": "slow"})
        count = self.collector.get_metric_value("test_histogram", {"type": "slow"})
        assert count == 1.0

    def test_time_function_context_manager(self):
        """Test the timing context manager."""
        start_time = time.time()

        with self.collector.time_function("test_timer"):
            time.sleep(0.01)  # Small delay

        end_time = time.time()

        # Check that the timer metric was recorded
        count = self.collector.get_metric_value("test_timer_duration_seconds")
        assert count == 1.0  # One observation

        # Verify timing was roughly correct (within reasonable bounds)
        assert end_time - start_time >= 0.01

    def test_prometheus_format_output(self):
        """Test Prometheus format output."""
        # Add some test metrics
        self.collector.increment_counter("requests_total", 10, {"method": "GET"})
        self.collector.set_gauge("active_connections", 5)
        self.collector.observe_histogram("request_duration", 0.5)

        prometheus_output = self.collector.get_metrics()

        # Check that output contains expected elements
        assert "# HELP" in prometheus_output
        assert "# TYPE" in prometheus_output
        assert "test_requests_total" in prometheus_output
        assert "test_active_connections" in prometheus_output
        assert "test_request_duration" in prometheus_output
        assert 'method="GET"' in prometheus_output

    def test_metric_families_output(self):
        """Test structured metric families output."""
        self.collector.increment_counter("api_calls", 5, {"endpoint": "/health"})
        self.collector.set_gauge("cpu_usage", 75.5)

        families = self.collector.get_metric_families()

        assert len(families) > 0

        # Find our test metrics
        api_calls_family = next((f for f in families if "api_calls" in f["name"]), None)
        assert api_calls_family is not None
        assert api_calls_family["type"] == "counter"

        cpu_family = next((f for f in families if "cpu_usage" in f["name"]), None)
        assert cpu_family is not None
        assert cpu_family["type"] == "gauge"

    def test_reset_metrics(self):
        """Test metrics reset functionality."""
        # Add some metrics
        self.collector.increment_counter("test_counter", 10)
        self.collector.set_gauge("test_gauge", 20)

        stats_before = self.collector.get_stats()
        assert stats_before["total"] > 0

        # Reset
        self.collector.reset_metrics()

        # Check that custom metrics are gone but defaults are restored
        value = self.collector.get_metric_value("test_counter")
        assert value is None

        stats_after = self.collector.get_stats()
        assert stats_after["total"] > 0  # Default metrics restored

    def test_thread_safety(self):
        """Test thread safety of metrics collection."""
        import threading
        import time

        # Function to increment counter in thread
        def increment_worker():
            for _ in range(100):
                self.collector.increment_counter("thread_test")
                time.sleep(0.001)

        # Start multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=increment_worker)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Check final value
        final_value = self.collector.get_metric_value("thread_test")
        assert final_value == 500.0  # 5 threads * 100 increments


class TestComponentHealthChecker:
    """Test the health checker implementation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.health_checker = ComponentHealthChecker(max_workers=2)

    def teardown_method(self):
        """Clean up after tests."""
        self.health_checker.shutdown()

    @pytest.mark.asyncio
    async def test_basic_health_checks(self):
        """Test basic health check functionality."""
        # Check system health
        result = await self.health_checker.check_component("system")
        assert result.component == "system"
        assert result.status in [
            HealthStatus.HEALTHY,
            HealthStatus.DEGRADED,
            HealthStatus.UNHEALTHY,
        ]
        assert result.message is not None

        # Check memory health
        result = await self.health_checker.check_component("memory")
        assert result.component == "memory"
        assert result.status in [
            HealthStatus.HEALTHY,
            HealthStatus.DEGRADED,
            HealthStatus.UNHEALTHY,
        ]
        assert "memory" in result.message.lower()

    @pytest.mark.asyncio
    async def test_custom_health_check_registration(self):
        """Test registering custom health checks."""

        # Create a mock health check
        async def mock_health_check():
            return HealthCheckResult(
                component="test_component",
                status=HealthStatus.HEALTHY,
                message="Test component is healthy",
            )

        # Register the health check
        self.health_checker.register_health_check("test_component", mock_health_check)

        # Test the health check
        result = await self.health_checker.check_component("test_component")
        assert result.component == "test_component"
        assert result.status == HealthStatus.HEALTHY
        assert result.message == "Test component is healthy"

    @pytest.mark.asyncio
    async def test_health_check_timeout(self):
        """Test health check timeout handling."""

        # Create a slow health check
        async def slow_health_check():
            await asyncio.sleep(35)  # Longer than 30s timeout
            return HealthCheckResult(
                component="slow_component",
                status=HealthStatus.HEALTHY,
                message="This should timeout",
            )

        self.health_checker.register_health_check("slow_component", slow_health_check)

        # This should timeout
        result = await self.health_checker.check_component("slow_component")
        assert result.component == "slow_component"
        assert result.status == HealthStatus.UNHEALTHY
        assert "timeout" in result.message.lower()

    @pytest.mark.asyncio
    async def test_failing_health_check(self):
        """Test handling of failing health checks."""

        # Create a failing health check
        async def failing_health_check():
            raise Exception("Simulated failure")

        self.health_checker.register_health_check("failing_component", failing_health_check)

        result = await self.health_checker.check_component("failing_component")
        assert result.component == "failing_component"
        assert result.status == HealthStatus.UNHEALTHY
        assert "failed" in result.message.lower()

    @pytest.mark.asyncio
    async def test_overall_health_status(self):
        """Test overall health status calculation."""

        # Register multiple health checks with different statuses
        async def healthy_check():
            return HealthCheckResult("healthy1", HealthStatus.HEALTHY, "All good")

        async def degraded_check():
            return HealthCheckResult("degraded1", HealthStatus.DEGRADED, "Some issues")

        async def unhealthy_check():
            return HealthCheckResult("unhealthy1", HealthStatus.UNHEALTHY, "Problems")

        self.health_checker.register_health_check("healthy1", healthy_check)
        self.health_checker.register_health_check("degraded1", degraded_check)
        self.health_checker.register_health_check("unhealthy1", unhealthy_check)

        overall = await self.health_checker.get_overall_health()

        # Should be unhealthy due to one unhealthy component
        assert overall.status == HealthStatus.UNHEALTHY
        assert overall.details is not None
        assert overall.details["unhealthy"] >= 1

    @pytest.mark.asyncio
    async def test_all_components_check(self):
        """Test checking all components at once."""

        # Register a few health checks
        async def test_check(name, status):
            return HealthCheckResult(name, status, f"{name} message")

        self.health_checker.register_health_check(
            "comp1", lambda: test_check("comp1", HealthStatus.HEALTHY)
        )
        self.health_checker.register_health_check(
            "comp2", lambda: test_check("comp2", HealthStatus.DEGRADED)
        )

        results = await self.health_checker.check_all_components()

        # Should include default checks plus our custom ones
        assert len(results) >= 2

        comp_names = [r.component for r in results]
        assert "comp1" in comp_names
        assert "comp2" in comp_names

    def test_database_health_check_creation(self):
        """Test database health check creation."""
        # Create a temporary database
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_db:
            temp_path = temp_db.name

            # Create a simple database
            conn = sqlite3.connect(temp_path)
            conn.execute("CREATE TABLE test (id INTEGER)")
            conn.close()

        try:
            # Create health check
            db_check = self.health_checker.create_database_health_check(temp_path)

            # This should be a callable
            assert callable(db_check)

            # Test the health check
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(db_check())
                assert result.component == "database"
                assert result.status == HealthStatus.HEALTHY
            finally:
                loop.close()

        finally:
            # Clean up
            Path(temp_path).unlink(missing_ok=True)

    def test_plugin_health_check_creation(self):
        """Test plugin health check creation."""
        # Create a mock plugin manager
        mock_plugin_manager = Mock()
        mock_plugin_manager.get_plugin_status.return_value = {
            "plugin1": {"state": "active", "enabled": True},
            "plugin2": {"state": "failed", "enabled": True},
        }
        mock_plugin_manager.get_active_plugins.return_value = {"plugin1": Mock()}

        # Create health check
        plugin_check = self.health_checker.create_plugin_health_check(mock_plugin_manager)

        # Test the health check
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(plugin_check())
            assert result.component == "plugins"
            assert result.status == HealthStatus.DEGRADED  # One failed plugin
            assert "1 plugins failed" in result.message
        finally:
            loop.close()


class TestBusinessMetricsCollector:
    """Test the business metrics collector."""

    def setup_method(self):
        """Set up test fixtures."""
        self.metrics_collector = PrometheusMetricsCollector(namespace="test")
        set_metrics_collector(self.metrics_collector)
        self.business_metrics = BusinessMetricsCollector()

    def test_file_indexing_metrics(self):
        """Test file indexing metrics recording."""
        # Record file indexing
        self.business_metrics.record_file_indexed(
            file_path="/test/file.py",
            language="python",
            symbols_count=25,
            duration=0.15,
        )

        # Check metrics were recorded
        files_indexed = self.metrics_collector.get_metric_value(
            "files_indexed_total", {"language": "python"}
        )
        assert files_indexed == 1.0

        symbols_indexed = self.metrics_collector.get_metric_value(
            "symbols_indexed_total", {"language": "python"}
        )
        assert symbols_indexed == 25.0

        # Check that duration was recorded (histogram count)
        duration_count = self.metrics_collector.get_metric_value(
            "file_indexing_duration_seconds", {"language": "python"}
        )
        assert duration_count == 1.0

    def test_search_metrics(self):
        """Test search metrics recording."""
        # Record search
        self.business_metrics.record_search_performed(
            query="test query", semantic=True, results_count=5, duration=0.05
        )

        # Check metrics
        searches = self.metrics_collector.get_metric_value(
            "searches_performed_total", {"search_type": "semantic"}
        )
        assert searches == 1.0

        duration_count = self.metrics_collector.get_metric_value(
            "search_duration_seconds", {"search_type": "semantic"}
        )
        assert duration_count == 1.0

        results_count = self.metrics_collector.get_metric_value(
            "search_results_count", {"search_type": "semantic"}
        )
        assert results_count == 1.0

    def test_plugin_event_metrics(self):
        """Test plugin event metrics recording."""
        # Record plugin event
        self.business_metrics.record_plugin_event(
            plugin_name="test_plugin", event_type="load", duration=1.5
        )

        # Check metrics
        events = self.metrics_collector.get_metric_value(
            "plugin_events_total", {"plugin_name": "test_plugin", "event_type": "load"}
        )
        assert events == 1.0

        duration_count = self.metrics_collector.get_metric_value(
            "plugin_operation_duration_seconds",
            {"plugin_name": "test_plugin", "operation": "load"},
        )
        assert duration_count == 1.0

    def test_system_metrics_update(self):
        """Test system metrics updating."""
        # Update system metrics
        self.business_metrics.update_system_metrics(
            active_plugins=3,
            indexed_files=150,
            database_size=1024000,
            memory_usage=512000000,
        )

        # Check metrics
        assert self.metrics_collector.get_metric_value("plugins_active_total") == 3.0
        assert self.metrics_collector.get_metric_value("files_indexed_current") == 150.0
        assert self.metrics_collector.get_metric_value("database_size_bytes") == 1024000.0
        assert self.metrics_collector.get_metric_value("memory_usage_bytes") == 512000000.0


class TestMetricsMiddleware:
    """Test the FastAPI metrics middleware."""

    def setup_method(self):
        """Set up test fixtures."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        self.app = FastAPI()
        self.metrics_collector = PrometheusMetricsCollector(namespace="test")
        set_metrics_collector(self.metrics_collector)

        # Add middleware
        self.app.add_middleware(MetricsMiddleware, enable_detailed_metrics=True)

        # Add test endpoints
        @self.app.get("/test")
        def test_endpoint():
            return {"message": "test"}

        @self.app.get("/error")
        def error_endpoint():
            raise Exception("Test error")

        self.client = TestClient(self.app)

    def test_successful_request_metrics(self):
        """Test metrics collection for successful requests."""
        # Make a request
        response = self.client.get("/test")
        assert response.status_code == 200

        # Check that metrics were recorded
        requests_total = self.metrics_collector.get_metric_value(
            "http_requests_total", {"method": "GET", "endpoint": "/test"}
        )
        assert requests_total == 1.0

        responses_total = self.metrics_collector.get_metric_value(
            "http_responses_total",
            {
                "method": "GET",
                "endpoint": "/test",
                "status_code": "200",
                "status_class": "2xx",
            },
        )
        assert responses_total == 1.0

        # Check duration was recorded
        duration_count = self.metrics_collector.get_metric_value(
            "http_request_duration_seconds",
            {
                "method": "GET",
                "endpoint": "/test",
                "status_code": "200",
                "status_class": "2xx",
            },
        )
        assert duration_count == 1.0

    def test_error_request_metrics(self):
        """Test metrics collection for error requests."""
        # Make a request that will error
        response = self.client.get("/error")
        assert response.status_code == 500

        # Check error metrics
        failed_requests = self.metrics_collector.get_metric_value(
            "http_requests_failed_total",
            {"method": "GET", "endpoint": "/error", "error_type": "Exception"},
        )
        assert failed_requests == 1.0

        # Check duration was still recorded
        duration_count = self.metrics_collector.get_metric_value(
            "http_request_duration_seconds",
            {
                "method": "GET",
                "endpoint": "/error",
                "status_code": "500",
                "status_class": "5xx",
            },
        )
        assert duration_count == 1.0

    def test_path_normalization(self):
        """Test URL path normalization for metrics."""
        middleware = MetricsMiddleware(app=self.app)

        # Test ID-like path normalization
        assert middleware._normalize_path("/users/123/profile") == "/users/{id}/profile"
        assert middleware._normalize_path("/api/v1/items/abc-123-def") == "/api/v1/items/{id}"
        assert middleware._normalize_path("/files/deadbeef1234") == "/files/{id}"

        # Test regular paths
        assert middleware._normalize_path("/health") == "/health"
        assert middleware._normalize_path("/api/v1/search") == "/api/v1/search"

        # Test edge cases
        assert middleware._normalize_path("/") == "/"
        assert middleware._normalize_path("") == "/"


class TestGlobalInstances:
    """Test global instance management."""

    def test_metrics_collector_singleton(self):
        """Test metrics collector singleton behavior."""
        collector1 = get_metrics_collector()
        collector2 = get_metrics_collector()

        # Should be the same instance
        assert collector1 is collector2

        # Test setting custom collector
        custom_collector = PrometheusMetricsCollector(namespace="custom")
        set_metrics_collector(custom_collector)

        collector3 = get_metrics_collector()
        assert collector3 is custom_collector
        assert collector3 is not collector1

    def test_health_checker_singleton(self):
        """Test health checker singleton behavior."""
        checker1 = get_health_checker()
        checker2 = get_health_checker()

        # Should be the same instance
        assert checker1 is checker2

        # Test setting custom checker
        custom_checker = ComponentHealthChecker(max_workers=2)
        set_health_checker(custom_checker)

        checker3 = get_health_checker()
        assert checker3 is custom_checker
        assert checker3 is not checker1

        # Clean up
        custom_checker.shutdown()

    def test_business_metrics_singleton(self):
        """Test business metrics collector singleton behavior."""
        business1 = get_business_metrics()
        business2 = get_business_metrics()

        # Should be the same instance
        assert business1 is business2


@pytest.mark.integration
class TestMetricsIntegration:
    """Integration tests for the complete metrics system."""

    def setup_method(self):
        """Set up integration test fixtures."""
        # Reset global instances
        import mcp_server.metrics.health_check as hc

        # Clear globals for clean testing
        import mcp_server.metrics.metrics_collector as mc
        import mcp_server.metrics.middleware as mw

        mc._metrics_collector = None
        hc._health_checker = None
        mw._business_metrics = None

    def test_full_metrics_pipeline(self):
        """Test complete metrics collection pipeline."""
        # Get instances (should create new ones)
        metrics_collector = get_metrics_collector()
        health_checker = get_health_checker()
        business_metrics = get_business_metrics()

        # Record some business metrics
        business_metrics.record_file_indexed("/test.py", "python", 10, 0.1)
        business_metrics.record_search_performed("test", False, 5, 0.05)

        # Get prometheus output
        prometheus_output = metrics_collector.get_metrics()

        # Verify metrics are in output
        assert "files_indexed_total" in prometheus_output
        assert "searches_performed_total" in prometheus_output
        assert 'language="python"' in prometheus_output
        assert 'search_type="fuzzy"' in prometheus_output

        # Test health checks
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            overall_health = loop.run_until_complete(health_checker.get_overall_health())
            assert overall_health.component == "system"
            assert overall_health.status in [
                HealthStatus.HEALTHY,
                HealthStatus.DEGRADED,
                HealthStatus.UNHEALTHY,
            ]
        finally:
            loop.close()
            health_checker.shutdown()


if __name__ == "__main__":
    pytest.main([__file__])
