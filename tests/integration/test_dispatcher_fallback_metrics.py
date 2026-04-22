"""Integration test: dispatcher fallback histogram appears on /metrics after triggered timeout."""

import os
import sqlite3
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock

import pytest

from mcp_server.metrics.prometheus_exporter import PROMETHEUS_AVAILABLE

pytestmark = pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")


def _make_slow_db(tmp_path: Path, filepath: str) -> str:
    db_path = str(tmp_path / "slow_test.db")
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE VIRTUAL TABLE bm25_content USING fts5(filepath, filename, content, language)"
    )
    conn.execute(
        "INSERT INTO bm25_content(filepath, filename, content, language) VALUES (?, ?, ?, ?)",
        (filepath, os.path.basename(filepath), "slowsym slow symbol definition", "slow"),
    )
    conn.commit()
    conn.close()
    return db_path


def test_fallback_timeout_histogram_on_metrics_endpoint(tmp_path, monkeypatch):
    """After a SlowPlugin-triggered timeout, PrometheusExporter exposes histogram count>=1."""
    monkeypatch.setenv("MCP_DISPATCHER_FALLBACK_MS", "200")

    # Reset the global exporter so a fresh PrometheusExporter picks up our histogram
    import mcp_server.metrics.prometheus_exporter as exp_mod

    original_exporter = exp_mod._exporter
    exp_mod._exporter = exp_mod.PrometheusExporter()

    try:
        from mcp_server.core.repo_context import RepoContext
        from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
        from mcp_server.storage.multi_repo_manager import RepositoryInfo
        from mcp_server.storage.sqlite_store import SQLiteStore
        from tests.fixtures.slow_plugin import SlowPlugin

        REPO_ID = "integration-fallback-test"

        db_path = _make_slow_db(tmp_path, "src/slow_code.slow")

        store = SQLiteStore(db_path)
        registry_entry = MagicMock(spec=RepositoryInfo)
        registry_entry.tracked_branch = "main"
        ctx = RepoContext(
            repo_id=REPO_ID,
            sqlite_store=store,
            workspace_root=tmp_path,
            tracked_branch="main",
            registry_entry=registry_entry,
        )

        # Build dispatcher and inject SlowPlugin directly into the plugin set registry
        dispatcher = EnhancedDispatcher(
            plugins=None,
            enable_advanced_features=False,
            use_plugin_factory=False,
            lazy_load=False,
            semantic_search_enabled=False,
        )
        slow_plugin = SlowPlugin(sleep_seconds=5.0)
        dispatcher._plugin_set_registry._cache[REPO_ID] = [slow_plugin]

        # Trigger a timeout via lookup — "slowsym" matches the BM25 row with .slow ext
        result = dispatcher.lookup(ctx, "slowsym", limit=20)
        assert result is None, "SlowPlugin timeout should yield None"

        # Verify the histogram was observed (histogram is on the global exporter)
        exporter = exp_mod.get_prometheus_exporter()
        hist = exporter.dispatcher_fallback_histogram
        assert hist is not None, "dispatcher_fallback_histogram must be available"

        samples = {
            s.labels.get("outcome"): s.value
            for m in exporter.registry.collect()
            if m.name == "mcp_dispatcher_fallback_duration_seconds"
            for s in m.samples
            if s.name.endswith("_count")
        }
        assert samples.get("timeout", 0) >= 1, f"Expected timeout count >=1, got samples={samples}"

        # Verify the PrometheusExporter generates metrics text with the histogram
        metrics_bytes = exporter.generate_metrics()
        metrics_text = (
            metrics_bytes.decode("utf-8") if isinstance(metrics_bytes, bytes) else metrics_bytes
        )
        assert (
            "mcp_dispatcher_fallback_duration_seconds_bucket" in metrics_text
        ), "Expected bucket metric in PrometheusExporter output"
        assert (
            'outcome="timeout"' in metrics_text
        ), "Expected timeout label in PrometheusExporter output"
        assert (
            "mcp_dispatcher_fallback_duration_seconds_count" in metrics_text
        ), "Expected count metric in PrometheusExporter output"

    finally:
        exp_mod._exporter = original_exporter
