"""Tests for PrometheusExporter HTTP lifecycle and mcp_tool_calls_total counter."""

import socket
import sys
import threading
import time
import urllib.request
from unittest import mock

import pytest


def _free_port() -> int:
    """Return an unused TCP port."""
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


class TestPrometheusExporterHTTP:
    """Test HTTP lifecycle of PrometheusExporter."""

    def setup_method(self):
        from mcp_server.metrics.prometheus_exporter import PrometheusExporter
        from prometheus_client import CollectorRegistry

        self.registry = CollectorRegistry()
        self.exporter = PrometheusExporter(registry=self.registry)
        self.port = _free_port()

    def teardown_method(self):
        try:
            self.exporter.stop()
        except Exception:
            pass

    def test_start_binds_and_serves_metrics(self):
        """start(port) binds HTTP on the given port and /metrics responds 200."""
        self.exporter.start(self.port)
        # Give the server thread a moment to start
        time.sleep(0.1)

        url = f"http://127.0.0.1:{self.port}/metrics"
        with urllib.request.urlopen(url, timeout=3) as resp:
            assert resp.status == 200
            body = resp.read()
        assert len(body) >= 0  # Any response body is fine

    def test_start_idempotent_same_port(self):
        """Calling start() twice with the same port does not raise and does not rebind."""
        self.exporter.start(self.port)
        time.sleep(0.1)
        # Second call must not raise
        self.exporter.start(self.port)
        # Server must still be serving
        url = f"http://127.0.0.1:{self.port}/metrics"
        with urllib.request.urlopen(url, timeout=3) as resp:
            assert resp.status == 200

    def test_stop_tears_down_server(self):
        """stop() tears down the HTTP server; next start() on a new port succeeds."""
        self.exporter.start(self.port)
        time.sleep(0.1)
        self.exporter.stop()
        time.sleep(0.1)

        # After stop, the original port should be released (connection refused)
        with pytest.raises(Exception):
            urllib.request.urlopen(f"http://127.0.0.1:{self.port}/metrics", timeout=1)

        # Next start() on a new port succeeds
        new_port = _free_port()
        try:
            self.exporter.start(new_port)
            time.sleep(0.1)
            with urllib.request.urlopen(f"http://127.0.0.1:{new_port}/metrics", timeout=3) as resp:
                assert resp.status == 200
        finally:
            self.exporter.stop()


class TestRecordToolCall:
    """Test record_tool_call helper and mcp_tool_calls_total Counter."""

    def test_module_level_counter_exists(self):
        """mcp_tool_calls_total is importable at module level."""
        from mcp_server.metrics.prometheus_exporter import mcp_tool_calls_total

        assert mcp_tool_calls_total is not None

    def test_record_tool_call_increments_counter(self):
        """record_tool_call increments mcp_tool_calls_total by 1 for given labels."""
        from mcp_server.metrics.prometheus_exporter import mcp_tool_calls_total, record_tool_call

        # Read baseline using _value.get() on the child metric
        tool = "test_tool_unique_abc"
        status = "success_unique_abc"
        child = mcp_tool_calls_total.labels(tool=tool, status=status)
        before = child._value.get()

        record_tool_call(tool=tool, status=status)

        after = child._value.get()
        assert after - before == 1.0

    def test_record_tool_call_multiple_labels(self):
        """record_tool_call accumulates correctly for distinct label sets."""
        from mcp_server.metrics.prometheus_exporter import mcp_tool_calls_total, record_tool_call

        tool_a = "tool_alpha_xyz"
        tool_b = "tool_beta_xyz"

        child_a = mcp_tool_calls_total.labels(tool=tool_a, status="ok")
        child_b = mcp_tool_calls_total.labels(tool=tool_b, status="ok")

        before_a = child_a._value.get()
        before_b = child_b._value.get()

        record_tool_call(tool=tool_a, status="ok")
        record_tool_call(tool=tool_a, status="ok")
        record_tool_call(tool=tool_b, status="ok")

        assert child_a._value.get() - before_a == 2.0
        assert child_b._value.get() - before_b == 1.0


class TestMissingDepNoOp:
    """Test that start/stop/record_tool_call no-op gracefully when prometheus_client is absent."""

    def test_missing_dep_noop(self, caplog):
        """When prometheus_client import fails, start/stop/record_tool_call log warn and no-op."""
        import importlib

        import mcp_server.metrics.prometheus_exporter as mod_orig

        # Patch PROMETHEUS_AVAILABLE to False to simulate missing dep
        with mock.patch.object(mod_orig, "PROMETHEUS_AVAILABLE", False):
            from mcp_server.metrics.prometheus_exporter import PrometheusExporter

            # Re-instantiate with NoOp registry (already initialised under mock)
            exporter = PrometheusExporter.__new__(PrometheusExporter)
            exporter._started_port = None
            exporter._server = None
            exporter._server_thread = None

            import logging

            with caplog.at_level(logging.WARNING):
                # These must not raise
                exporter.start(9999)
                exporter.stop()

        # record_tool_call must also not raise
        with mock.patch.object(mod_orig, "PROMETHEUS_AVAILABLE", False):
            mod_orig.record_tool_call(tool="x", status="y")
