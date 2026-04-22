"""Tests for run_gated_fallback in mcp_server/dispatcher/fallback.py."""

import signal
import time
from typing import Optional
from unittest.mock import MagicMock

import pytest

import mcp_server.dispatcher.fallback as fallback_module
from mcp_server.dispatcher.fallback import run_gated_fallback
from mcp_server.plugin_base import SymbolDef
from mcp_server.plugin_system.plugin_registry import PluginRegistry
from tests.fixtures.slow_plugin import SlowPlugin


class FakeHistogram:
    """Duck-typed histogram for asserting observation calls."""

    def __init__(self):
        self.calls: list[dict] = []

    def labels(self, **kwargs):
        return _FakeObserver(self.calls, kwargs)


class _FakeObserver:
    def __init__(self, calls: list, labels: dict):
        self._calls = calls
        self._labels = labels

    def observe(self, value: float):
        self._calls.append({**self._labels, "value": value})


def _make_symbol_def(symbol: str = "foo") -> SymbolDef:
    return SymbolDef(
        symbol=symbol,
        kind="function",
        language="slow",
        signature=f"def {symbol}()",
        doc=None,
        defined_in="test.slow",
        start_line=1,
        end_line=1,
        span=(1, 1),
    )


def _make_registry_with(plugin_class_name: str, ext: str) -> PluginRegistry:
    registry = PluginRegistry()
    registry._extension_map[ext] = [plugin_class_name]
    return registry


def test_slow_plugin_respects_timeout():
    slow = SlowPlugin(sleep_seconds=5.0)
    fake = FakeHistogram()
    registry = _make_registry_with("SlowPlugin", ".slow")

    t0 = time.monotonic()
    result = run_gated_fallback(
        [slow],
        "foo",
        source_ext=".slow",
        timeout_ms=200,
        histogram=fake,
        registry=registry,
    )
    elapsed = time.monotonic() - t0

    assert result is None
    assert elapsed < 0.4, f"wall-clock exceeded 400ms: {elapsed:.3f}s"
    assert len(fake.calls) == 1
    assert fake.calls[0]["outcome"] == "timeout"


def test_source_ext_none_returns_none():
    mock_plugin = MagicMock()
    fake = FakeHistogram()

    result = run_gated_fallback(
        [mock_plugin],
        "foo",
        source_ext=None,
        timeout_ms=200,
        histogram=fake,
    )

    assert result is None
    mock_plugin.getDefinition.assert_not_called()


def test_py_dispatch_skips_c_plugin():
    """Plugin registered only under .c should not be called when source_ext is .py."""
    registry = PluginRegistry()
    registry._extension_map[".c"] = ["MockCPlugin"]
    registry._extension_map[".cpp"] = ["MockCPlugin"]

    mock_c_plugin = MagicMock()
    mock_c_plugin.__class__ = type("MockCPlugin", (), {})
    # Rename the class to match what's in the registry
    mock_c_plugin.__class__.__name__ = "MockCPlugin"

    result = run_gated_fallback(
        [mock_c_plugin],
        "foo",
        source_ext=".py",
        timeout_ms=200,
        histogram=None,
        registry=registry,
    )

    assert result is None
    mock_c_plugin.getDefinition.assert_not_called()


def test_histogram_none_is_noop():
    slow = SlowPlugin(sleep_seconds=0.0, symbol_def=None)
    registry = _make_registry_with("SlowPlugin", ".slow")

    # Should not raise AttributeError
    result = run_gated_fallback(
        [slow],
        "foo",
        source_ext=".slow",
        timeout_ms=500,
        histogram=None,
        registry=registry,
    )

    assert result is None


def test_no_sigalrm_usage():
    original_handler = signal.getsignal(signal.SIGALRM)

    slow = SlowPlugin(sleep_seconds=0.0)
    registry = _make_registry_with("SlowPlugin", ".slow")
    fake = FakeHistogram()

    run_gated_fallback(
        [slow],
        "foo",
        source_ext=".slow",
        timeout_ms=500,
        histogram=fake,
        registry=registry,
    )

    assert (
        signal.getsignal(signal.SIGALRM) == original_handler
    ), "run_gated_fallback must not modify SIGALRM handler"
    assert "signal" not in dir(fallback_module), "fallback module must not import signal"


def test_hit_observed_correctly():
    sym = _make_symbol_def("bar")
    fast = SlowPlugin(sleep_seconds=0.0, symbol_def=sym)
    registry = _make_registry_with("SlowPlugin", ".slow")
    fake = FakeHistogram()

    result = run_gated_fallback(
        [fast],
        "bar",
        source_ext=".slow",
        timeout_ms=500,
        histogram=fake,
        registry=registry,
    )

    assert result == sym
    assert len(fake.calls) == 1
    assert fake.calls[0]["outcome"] == "hit"
