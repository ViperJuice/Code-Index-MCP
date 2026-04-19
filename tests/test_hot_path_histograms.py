"""Tests for hot-path latency histograms (IF-0-P12-4).

Covers:
- PrometheusExporter exposes dispatcher_lookup_histogram and dispatcher_search_histogram
- Both are None when prometheus_client unavailable
- Both share the _DISPATCHER_FALLBACK_BUCKETS tuple
- dispatcher_lookup_histogram._count increments by exactly 1 per dispatcher.lookup call
- dispatcher_search_histogram._count increments by exactly 1 per dispatcher.search call
- Metric names appear on generate_metrics() output
- NO double-count: dispatcher_fallback_histogram._count does NOT increment on a
  hot-path call that returns before hitting run_gated_fallback
"""
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import mcp_server.metrics.prometheus_exporter as prometheus_exporter
from mcp_server.metrics.prometheus_exporter import (
    PROMETHEUS_AVAILABLE,
    PrometheusExporter,
    _DISPATCHER_FALLBACK_BUCKETS,
)

pytestmark = pytest.mark.skipif(
    not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed"
)

LOOKUP_METRIC_NAME = "mcp_dispatcher_symbol_lookup_duration_seconds"
SEARCH_METRIC_NAME = "mcp_dispatcher_search_duration_seconds"


# ---------------------------------------------------------------------------
# Exporter attribute / registration tests
# ---------------------------------------------------------------------------

def test_exporter_exposes_lookup_histogram():
    exporter = PrometheusExporter()
    assert exporter.dispatcher_lookup_histogram is not None


def test_exporter_exposes_search_histogram():
    exporter = PrometheusExporter()
    assert exporter.dispatcher_search_histogram is not None


def test_both_none_when_prometheus_unavailable(monkeypatch):
    monkeypatch.setattr(prometheus_exporter, "PROMETHEUS_AVAILABLE", False)
    exporter = PrometheusExporter()
    assert exporter.dispatcher_lookup_histogram is None
    assert exporter.dispatcher_search_histogram is None


def test_lookup_histogram_shares_bucket_tuple():
    exporter = PrometheusExporter()
    hist = exporter.dispatcher_lookup_histogram
    # prometheus_client appends +Inf; strip it
    assert tuple(hist._upper_bounds)[:-1] == _DISPATCHER_FALLBACK_BUCKETS


def test_search_histogram_shares_bucket_tuple():
    exporter = PrometheusExporter()
    hist = exporter.dispatcher_search_histogram
    assert tuple(hist._upper_bounds)[:-1] == _DISPATCHER_FALLBACK_BUCKETS


def test_lookup_histogram_metric_name_on_scrape():
    exporter = PrometheusExporter()
    names = {m.name for m in exporter.registry.collect()}
    assert LOOKUP_METRIC_NAME in names


def test_search_histogram_metric_name_on_scrape():
    exporter = PrometheusExporter()
    names = {m.name for m in exporter.registry.collect()}
    assert SEARCH_METRIC_NAME in names


# ---------------------------------------------------------------------------
# Helpers to build a minimal SQLite DB with a symbols row for fast BM25 hit
# ---------------------------------------------------------------------------

def _make_db_with_symbol(tmp_path: Path, symbol: str) -> str:
    from mcp_server.storage.sqlite_store import SQLiteStore

    db_path = str(tmp_path / "test_hot.db")
    # Let SQLiteStore create the full schema first
    store = SQLiteStore(db_path)
    conn = sqlite3.connect(db_path)
    # Insert a repository row (required FK for files)
    conn.execute(
        "INSERT OR IGNORE INTO repositories(id, path, name) VALUES (1, '/repo', 'test')"
    )
    # Insert a file row
    conn.execute(
        "INSERT INTO files(id, repository_id, path, relative_path, language) "
        "VALUES (1, 1, 'src/foo.py', 'src/foo.py', 'python')"
    )
    # Insert a symbol row (line_end required by schema)
    conn.execute(
        "INSERT INTO symbols(name, kind, line_start, line_end, signature, documentation, file_id) "
        "VALUES (?, 'function', 1, 1, ?, NULL, 1)",
        (symbol, f"def {symbol}()"),
    )
    conn.commit()
    conn.close()
    return db_path


def _make_bm25_db(tmp_path: Path, query_word: str) -> str:
    db_path = str(tmp_path / "test_bm25.db")
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE VIRTUAL TABLE bm25_content USING fts5"
        "(filepath, filename, content, language)"
    )
    conn.execute(
        "INSERT INTO bm25_content VALUES (?, ?, ?, ?)",
        ("src/bar.py", "bar.py", f"{query_word} something here", "python"),
    )
    conn.commit()
    conn.close()
    return db_path


def _make_dispatcher():
    from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher

    return EnhancedDispatcher(
        plugins=None,
        enable_advanced_features=False,
        use_plugin_factory=False,
        lazy_load=False,
        semantic_search_enabled=False,
    )


def _make_ctx(db_path: str, tmp_path: Path):
    from mcp_server.core.repo_context import RepoContext
    from mcp_server.storage.multi_repo_manager import RepositoryInfo
    from mcp_server.storage.sqlite_store import SQLiteStore

    store = SQLiteStore(db_path)
    registry_entry = MagicMock(spec=RepositoryInfo)
    registry_entry.tracked_branch = "main"
    return RepoContext(
        repo_id="hp-test",
        sqlite_store=store,
        workspace_root=tmp_path,
        tracked_branch="main",
        registry_entry=registry_entry,
    )


# ---------------------------------------------------------------------------
# _count increment tests
# ---------------------------------------------------------------------------

def test_lookup_histogram_count_increments(tmp_path):
    """dispatcher.lookup increments dispatcher_lookup_histogram._count by exactly 1."""
    original_exporter = prometheus_exporter._exporter
    prometheus_exporter._exporter = None
    try:
        db_path = _make_db_with_symbol(tmp_path, "my_func")
        dispatcher = _make_dispatcher()
        ctx = _make_ctx(db_path, tmp_path)

        exporter = prometheus_exporter.get_prometheus_exporter()
        hist = exporter.dispatcher_lookup_histogram
        assert hist is not None

        def _count():
            return sum(
                s.value
                for m in exporter.registry.collect()
                if m.name == LOOKUP_METRIC_NAME
                for s in m.samples
                if s.name.endswith("_count")
            )

        before = _count()
        dispatcher.lookup(ctx, "my_func", limit=5)
        after = _count()
        assert after - before == 1.0
    finally:
        prometheus_exporter._exporter = original_exporter


def test_search_histogram_count_increments(tmp_path):
    """dispatcher.search increments dispatcher_search_histogram._count by exactly 1."""
    original_exporter = prometheus_exporter._exporter
    prometheus_exporter._exporter = None
    try:
        db_path = _make_bm25_db(tmp_path, "searchword")
        dispatcher = _make_dispatcher()
        ctx = _make_ctx(db_path, tmp_path)

        exporter = prometheus_exporter.get_prometheus_exporter()
        hist = exporter.dispatcher_search_histogram
        assert hist is not None

        def _count():
            return sum(
                s.value
                for m in exporter.registry.collect()
                if m.name == SEARCH_METRIC_NAME
                for s in m.samples
                if s.name.endswith("_count")
            )

        before = _count()
        list(dispatcher.search(ctx, "searchword", limit=5))
        after = _count()
        assert after - before == 1.0
    finally:
        prometheus_exporter._exporter = original_exporter


# ---------------------------------------------------------------------------
# No-double-count test: fallback histogram must NOT fire on a pure BM25 hit
# ---------------------------------------------------------------------------

def test_no_double_count_fallback_histogram(tmp_path):
    """A symbols-table hit must not increment dispatcher_fallback_histogram."""
    original_exporter = prometheus_exporter._exporter
    prometheus_exporter._exporter = None
    try:
        db_path = _make_db_with_symbol(tmp_path, "pure_bm25_sym")
        dispatcher = _make_dispatcher()
        ctx = _make_ctx(db_path, tmp_path)

        exporter = prometheus_exporter.get_prometheus_exporter()
        fallback_hist = exporter.dispatcher_fallback_histogram
        assert fallback_hist is not None

        def _fallback_count():
            return sum(
                s.value
                for m in exporter.registry.collect()
                if m.name == "mcp_dispatcher_fallback_duration_seconds"
                for s in m.samples
                if s.name.endswith("_count")
            )

        before = _fallback_count()
        dispatcher.lookup(ctx, "pure_bm25_sym", limit=5)
        after = _fallback_count()
        assert after == before, (
            f"dispatcher_fallback_histogram must not fire on a BM25 hit; "
            f"before={before}, after={after}"
        )
    finally:
        prometheus_exporter._exporter = original_exporter


# ---------------------------------------------------------------------------
# generate_metrics output contains both new metric name strings
# ---------------------------------------------------------------------------

def test_metric_names_appear_in_generate_metrics():
    exporter = PrometheusExporter()
    # Observe once so bucket/count lines appear
    exporter.dispatcher_lookup_histogram.observe(0.01)
    exporter.dispatcher_search_histogram.observe(0.01)
    output = exporter.generate_metrics()
    text = output.decode("utf-8") if isinstance(output, bytes) else output
    assert LOOKUP_METRIC_NAME in text
    assert SEARCH_METRIC_NAME in text
