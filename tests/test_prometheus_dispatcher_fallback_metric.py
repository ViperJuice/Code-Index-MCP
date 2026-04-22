"""Tests for the mcp_dispatcher_fallback_duration_seconds histogram (IF-0-P11-3)."""

import pytest

import mcp_server.metrics.prometheus_exporter as prometheus_exporter
from mcp_server.metrics.prometheus_exporter import (
    _DISPATCHER_FALLBACK_BUCKETS,
    PROMETHEUS_AVAILABLE,
    PrometheusExporter,
)

pytestmark = pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")


def test_histogram_registered():
    exporter = PrometheusExporter()
    hist = exporter.dispatcher_fallback_histogram
    assert hist is not None

    # Verify metric name via collected samples
    names = {m.name for m in exporter.registry.collect()}
    assert "mcp_dispatcher_fallback_duration_seconds" in names

    # Verify label names
    assert hist._labelnames == ("outcome",)

    # Verify buckets (prometheus_client appends +Inf; strip it)
    assert tuple(hist._upper_bounds)[:-1] == _DISPATCHER_FALLBACK_BUCKETS


def test_prometheus_unavailable_returns_none(monkeypatch):
    monkeypatch.setattr(prometheus_exporter, "PROMETHEUS_AVAILABLE", False)
    exporter = PrometheusExporter()
    assert exporter.dispatcher_fallback_histogram is None


def test_histogram_records_outcomes():
    exporter = PrometheusExporter()
    hist = exporter.dispatcher_fallback_histogram

    for outcome in ("hit", "miss", "timeout", "error"):
        hist.labels(outcome=outcome).observe(0.1)

    samples = {
        s.labels.get("outcome"): s.value
        for m in exporter.registry.collect()
        if m.name == "mcp_dispatcher_fallback_duration_seconds"
        for s in m.samples
        if s.name.endswith("_count")
    }

    for outcome in ("hit", "miss", "timeout", "error"):
        assert samples.get(outcome) == 1.0, f"outcome={outcome!r} not recorded"
