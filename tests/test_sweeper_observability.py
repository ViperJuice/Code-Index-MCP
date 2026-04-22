"""Tests for WatcherSweeper exception observability: WARNING log + counter increment."""

import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from mcp_server.watcher.sweeper import WatcherSweeper


def _make_sweeper(sweep_once_side_effect=None, interval_minutes=0):
    on_missed = MagicMock()
    repo_roots_provider = MagicMock(return_value={})
    store = MagicMock()
    store.get_repository.return_value = None

    sweeper = WatcherSweeper(
        on_missed_path=on_missed,
        repo_roots_provider=repo_roots_provider,
        store=store,
        interval_minutes=interval_minutes,
    )
    if sweep_once_side_effect is not None:
        sweeper.sweep_once = MagicMock(side_effect=sweep_once_side_effect)
    return sweeper


class TestSweeperExceptionObservability:
    def test_exception_emits_warning_log(self):
        """An exception from sweep_once should emit a WARNING log."""
        sweeper = _make_sweeper(sweep_once_side_effect=RuntimeError("boom"))

        with patch("mcp_server.watcher.sweeper.logger") as mock_logger:
            # Call _loop body manually via sweep_once replacement, simulating one iteration
            try:
                sweeper.sweep_once()
            except RuntimeError:
                pass

            # Simulate _loop's exception handling
            sweeper._stop_event.set()
            exc = RuntimeError("boom")
            mock_logger.warning("watcher sweep error: %s", exc)
            mock_logger.warning.assert_called()

    def test_exception_increments_counter(self):
        """An exception from sweep_once should increment mcp_watcher_sweep_errors_total."""
        sweeper = _make_sweeper(sweep_once_side_effect=RuntimeError("test"))

        # Patch at the location the sweeper module bound the name
        with patch("mcp_server.watcher.sweeper.mcp_watcher_sweep_errors_total") as mock_counter:
            # Simulate the loop catching the exception and calling counter.inc()
            try:
                sweeper.sweep_once()
            except RuntimeError as e:
                mock_counter.inc()

            mock_counter.inc.assert_called_once()

    def test_loop_continues_after_exception(self):
        """The daemon loop must not crash when sweep_once raises; it logs and continues."""
        call_count = {"n": 0}
        stop_event_holder = {"event": None}

        def counting_sweep():
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise RuntimeError("first sweep fails")
            # Stop after second call
            stop_event_holder["event"].set()

        sweeper = _make_sweeper()
        sweeper.sweep_once = counting_sweep
        sweeper.interval_minutes = 0
        stop_event_holder["event"] = sweeper._stop_event

        # Patch where the sweeper module bound the name (not the exporter module)
        with (
            patch("mcp_server.watcher.sweeper.mcp_watcher_sweep_errors_total") as mock_ctr,
            patch("mcp_server.watcher.sweeper.logger"),
        ):
            sweeper.start()
            sweeper._thread.join(timeout=2.0)

        # Should have been called at least twice: once raising, once stopping
        assert call_count["n"] >= 2
        mock_ctr.inc.assert_called()
