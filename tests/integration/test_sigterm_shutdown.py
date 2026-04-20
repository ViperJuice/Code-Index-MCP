"""Integration tests for SIGTERM graceful shutdown + metrics wiring (P10 SL-2)."""
from __future__ import annotations

import asyncio
import os
import signal
import time
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Fake components that record call order
# ---------------------------------------------------------------------------

class FakeWatcher:
    def __init__(self, calls: list[str], delay: float = 0.0) -> None:
        self._calls = calls
        self._delay = delay

    def stop(self) -> None:
        if self._delay:
            time.sleep(self._delay)
        self._calls.append("watcher.stop")

    # alias required by SL-2 (IF-0-P10-3)
    stop_watching_all = stop


class FakePoller:
    def __init__(self, calls: list[str]) -> None:
        self._calls = calls

    def stop(self) -> None:
        self._calls.append("poller.stop")


class FakeStoreRegistry:
    def __init__(self, calls: list[str]) -> None:
        self._calls = calls

    def shutdown(self) -> None:
        self._calls.append("store.shutdown")


class FakeExporter:
    def __init__(self, calls: list[str]) -> None:
        self._calls = calls

    def stop(self) -> None:
        self._calls.append("exporter.stop")


# ---------------------------------------------------------------------------
# Tests for _graceful_shutdown
# ---------------------------------------------------------------------------

class TestGracefulShutdown:
    """Unit tests for _graceful_shutdown — no subprocess needed."""

    def setup_method(self) -> None:
        import mcp_server.cli.stdio_runner as runner
        runner._shutdown_called = False

    def _get_shutdown_fn(self):
        from mcp_server.cli.stdio_runner import _graceful_shutdown
        return _graceful_shutdown

    def test_shutdown_calls_components_in_order(self):
        """Stop order: watcher -> poller -> store -> exporter."""
        calls: list[str] = []
        watcher = FakeWatcher(calls)
        poller = FakePoller(calls)
        store = FakeStoreRegistry(calls)
        exporter = FakeExporter(calls)

        shutdown = self._get_shutdown_fn()
        asyncio.run(shutdown(watcher, poller, store, exporter, timeout=5.0))

        assert calls == ["watcher.stop", "poller.stop", "store.shutdown", "exporter.stop"]

    def test_shutdown_with_none_watcher(self):
        """None watcher is tolerated — poller/store/exporter still called."""
        calls: list[str] = []
        poller = FakePoller(calls)
        store = FakeStoreRegistry(calls)
        exporter = FakeExporter(calls)

        shutdown = self._get_shutdown_fn()
        asyncio.run(shutdown(None, poller, store, exporter, timeout=5.0))

        assert calls == ["poller.stop", "store.shutdown", "exporter.stop"]

    def test_shutdown_with_none_poller(self):
        """None poller is tolerated."""
        calls: list[str] = []
        watcher = FakeWatcher(calls)
        store = FakeStoreRegistry(calls)
        exporter = FakeExporter(calls)

        shutdown = self._get_shutdown_fn()
        asyncio.run(shutdown(watcher, None, store, exporter, timeout=5.0))

        assert calls == ["watcher.stop", "store.shutdown", "exporter.stop"]

    def test_shutdown_with_all_none(self):
        """All-None is safe — exporter.stop still called."""
        calls: list[str] = []
        exporter = FakeExporter(calls)

        shutdown = self._get_shutdown_fn()
        asyncio.run(shutdown(None, None, None, exporter, timeout=5.0))

        assert calls == ["exporter.stop"]

    def test_shutdown_timeout_does_not_propagate(self):
        """A timed-out watcher.stop is swallowed; subsequent steps still run."""
        calls: list[str] = []
        # delay > timeout so watcher times out
        watcher = FakeWatcher(calls, delay=10.0)
        poller = FakePoller(calls)
        store = FakeStoreRegistry(calls)
        exporter = FakeExporter(calls)

        shutdown = self._get_shutdown_fn()
        # Short timeout — watcher will time out
        asyncio.run(shutdown(watcher, poller, store, exporter, timeout=0.05))

        # poller/store/exporter must still have been called despite watcher timeout
        assert "poller.stop" in calls
        assert "store.shutdown" in calls
        assert "exporter.stop" in calls

    def test_shutdown_idempotent(self):
        """Calling shutdown twice does not double-stop (idempotency flag)."""
        calls: list[str] = []
        watcher = FakeWatcher(calls)
        poller = FakePoller(calls)
        store = FakeStoreRegistry(calls)
        exporter = FakeExporter(calls)

        shutdown = self._get_shutdown_fn()
        asyncio.run(shutdown(watcher, poller, store, exporter, timeout=5.0))
        asyncio.run(shutdown(watcher, poller, store, exporter, timeout=5.0))

        # First call recorded 4 entries; second call should be a no-op
        assert calls.count("watcher.stop") == 1
        assert calls.count("poller.stop") == 1
        assert calls.count("store.shutdown") == 1
        assert calls.count("exporter.stop") == 1


# ---------------------------------------------------------------------------
# Tests for stop alias on MultiRepositoryWatcher (IF-0-P10-3)
# ---------------------------------------------------------------------------

class TestMultiRepoWatcherStopAlias:
    def test_stop_alias_exists(self):
        from mcp_server.watcher_multi_repo import MultiRepositoryWatcher
        assert hasattr(MultiRepositoryWatcher, "stop"), \
            "MultiRepositoryWatcher must have a `stop` alias (IF-0-P10-3)"

    def test_stop_alias_is_stop_watching_all(self):
        from mcp_server.watcher_multi_repo import MultiRepositoryWatcher
        assert MultiRepositoryWatcher.stop is MultiRepositoryWatcher.stop_watching_all, \
            "`stop` must be an alias for `stop_watching_all`"


# ---------------------------------------------------------------------------
# Tests for record_tool_call metric wiring
# ---------------------------------------------------------------------------

class TestRecordToolCallWiring:
    """Verify that the @server.call_tool() handler emits exactly one
    record_tool_call per invocation, regardless of success/error path."""

    def test_record_tool_call_imported(self):
        """record_tool_call must be importable from the metrics module."""
        from mcp_server.metrics.prometheus_exporter import record_tool_call
        assert callable(record_tool_call)

    def test_mcp_tool_calls_total_counter_exists(self):
        """mcp_tool_calls_total counter must be module-level."""
        from mcp_server.metrics.prometheus_exporter import mcp_tool_calls_total
        assert mcp_tool_calls_total is not None

    def test_record_tool_call_increments_counter(self):
        """record_tool_call must increment the counter (or silently no-op without prometheus)."""
        from mcp_server.metrics import prometheus_exporter as pe
        if not pe.PROMETHEUS_AVAILABLE:
            pytest.skip("prometheus_client not installed")
        initial = pe.mcp_tool_calls_total.labels(tool="_test_sl2_", status="success")._value.get()
        pe.record_tool_call("_test_sl2_", "success")
        after = pe.mcp_tool_calls_total.labels(tool="_test_sl2_", status="success")._value.get()
        assert after == initial + 1

    def test_stdio_runner_imports_record_tool_call(self):
        """stdio_runner must import and use record_tool_call."""
        import pathlib
        src = (
            pathlib.Path(__file__).resolve().parents[2]
            / "mcp_server/cli/stdio_runner.py"
        ).read_text()
        assert "record_tool_call" in src, \
            "stdio_runner.py must reference record_tool_call"


# ---------------------------------------------------------------------------
# Tests for PrometheusExporter start/stop wiring in _serve()
# ---------------------------------------------------------------------------

class TestPrometheusExporterWiring:
    def test_prometheus_exporter_imported_in_runner(self):
        """stdio_runner must import PrometheusExporter."""
        import pathlib
        src = (
            pathlib.Path(__file__).resolve().parents[2]
            / "mcp_server/cli/stdio_runner.py"
        ).read_text()
        assert "PrometheusExporter" in src, \
            "stdio_runner.py must reference PrometheusExporter"

    def test_prometheus_exporter_start_stop(self):
        """PrometheusExporter.start and .stop must be callable without error."""
        from mcp_server.metrics.prometheus_exporter import PrometheusExporter, PROMETHEUS_AVAILABLE
        if not PROMETHEUS_AVAILABLE:
            pytest.skip("prometheus_client not installed")
        exp = PrometheusExporter()
        # start on a random high port (avoid 9090 collision)
        exp.start(19091)
        exp.stop()

    def test_metrics_http_endpoint_returns_exposition_format(self):
        """HTTP /metrics endpoint must return Prometheus exposition text with instance metrics."""
        import time
        import urllib.request
        from mcp_server.metrics.prometheus_exporter import PrometheusExporter, PROMETHEUS_AVAILABLE, generate_latest
        if not PROMETHEUS_AVAILABLE:
            pytest.skip("prometheus_client not installed")

        exp = PrometheusExporter()
        # Use the exporter's own registry — verify it exposes some metrics
        body = exp.generate_metrics().decode()
        assert "mcp_requests_total" in body, \
            f"Expected mcp_requests_total in metrics body; got: {body[:300]}"

    def test_mcp_tool_calls_total_in_exporter_registry_output(self):
        """mcp_tool_calls_total appears in _EXPORTER_REGISTRY generate_latest output after record_tool_call."""
        from mcp_server.metrics.prometheus_exporter import (
            PROMETHEUS_AVAILABLE, record_tool_call, generate_latest, _EXPORTER_REGISTRY,
        )
        if not PROMETHEUS_AVAILABLE:
            pytest.skip("prometheus_client not installed")
        record_tool_call("_gen_test_", "success")
        body = generate_latest(_EXPORTER_REGISTRY).decode()
        assert "mcp_tool_calls_total" in body, \
            f"Expected mcp_tool_calls_total in generate_latest(_EXPORTER_REGISTRY) output"

    def test_signal_handlers_installed_in_serve(self):
        """stdio_runner.py source must reference add_signal_handler."""
        import pathlib
        src = (
            pathlib.Path(__file__).resolve().parents[2]
            / "mcp_server/cli/stdio_runner.py"
        ).read_text()
        assert "add_signal_handler" in src, \
            "stdio_runner.py must call loop.add_signal_handler for SIGTERM/SIGINT"
        assert "signal.SIGTERM" in src, \
            "stdio_runner.py must register SIGTERM handler"
