"""Tests for WatcherSweeper — periodic full-tree sweep for inotify/FSEvents drop recovery."""

import os
from pathlib import Path
from unittest.mock import Mock

import pytest

from mcp_server.watcher.sweeper import DEFAULT_SWEEP_MINUTES, ENV_SWEEP_MINUTES, WatcherSweeper

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_sqlite_store(tmp_path: Path):
    """Return a real SQLiteStore backed by a temp DB with a file entry."""
    from mcp_server.storage.sqlite_store import SQLiteStore

    db_path = tmp_path / "test.db"
    store = SQLiteStore(str(db_path))
    return store


def _store_file(store, repo_id_int: int, relative_path: str):
    """Insert a file record directly via the store."""
    store.store_file(
        file_path=Path(f"/repo/{relative_path}"),
        language="python",
        repository_id=repo_id_int,
        relative_path=relative_path,
    )


# ---------------------------------------------------------------------------
# test_sweeper_recovers_missed_event (acceptance #5)
# ---------------------------------------------------------------------------


class TestSweeperRecoversMissedEvent:
    """Sweeper detects a file present on disk but absent from SQLite."""

    def test_sweeper_recovers_missed_event(self, tmp_path):
        """Create a file without firing watchdog; sweep_once should call on_missed_path."""
        repo_id = "repo-abc"
        repo_root = tmp_path / "myrepo"
        repo_root.mkdir()

        # Write a Python file WITHOUT triggering watchdog (filesystem only)
        missed_file = repo_root / "missed.py"
        missed_file.write_text("x = 1\n")

        # SQLite store has NO record of missed.py
        store = _make_sqlite_store(tmp_path)
        # Register a repository so store knows about it
        store.create_repository(path=str(repo_root), name="myrepo")

        missed_calls = []

        def on_missed(r_id, rel_path):
            missed_calls.append((r_id, rel_path))

        sweeper = WatcherSweeper(
            on_missed_path=on_missed,
            repo_roots_provider=lambda: {repo_id: repo_root},
            store=store,
            interval_minutes=60,
        )

        drifted = sweeper.sweep_once()

        assert repo_id in drifted
        assert len(missed_calls) == 1
        assert missed_calls[0][0] == repo_id
        assert missed_calls[0][1] == "missed.py"


# ---------------------------------------------------------------------------
# test_sweeper_interval_env_override
# ---------------------------------------------------------------------------


class TestSweeperIntervalEnvOverride:
    """ENV_SWEEP_MINUTES overrides the default interval."""

    def test_sweeper_interval_env_override(self, monkeypatch):
        """When env var is set, WatcherSweeper uses that interval."""
        monkeypatch.setenv(ENV_SWEEP_MINUTES, "5")

        sweeper = WatcherSweeper(
            on_missed_path=lambda r, p: None,
            repo_roots_provider=lambda: {},
            store=Mock(),
        )

        assert sweeper.interval_minutes == 5


# ---------------------------------------------------------------------------
# test_sweeper_noop_when_no_drift
# ---------------------------------------------------------------------------


class TestSweeperNoopWhenNoDrift:
    """Sweeper finds no missed paths when filesystem matches SQLite."""

    def test_sweeper_noop_when_no_drift(self, tmp_path):
        """If all disk files are in SQLite, on_missed_path is never called."""
        repo_id = "repo-clean"
        repo_root = tmp_path / "cleanrepo"
        repo_root.mkdir()

        py_file = repo_root / "existing.py"
        py_file.write_text("pass\n")

        store = _make_sqlite_store(tmp_path)
        store.create_repository(path=str(repo_root), name="cleanrepo")
        # Store the file record so sweeper sees it as known
        store.store_file(
            file_path=py_file,
            language="python",
            repository_id=1,
            relative_path="existing.py",
        )

        missed_calls = []

        sweeper = WatcherSweeper(
            on_missed_path=lambda r, p: missed_calls.append((r, p)),
            repo_roots_provider=lambda: {repo_id: repo_root},
            store=store,
            interval_minutes=60,
        )

        drifted = sweeper.sweep_once()

        assert missed_calls == []
        assert drifted == []


# ---------------------------------------------------------------------------
# test_sweeper_start_stop
# ---------------------------------------------------------------------------


class TestSweeperStartStop:
    """start/stop lifecycle — sweeper thread must not leak."""

    def test_start_stop_no_error(self, tmp_path):
        store = _make_sqlite_store(tmp_path)
        sweeper = WatcherSweeper(
            on_missed_path=lambda r, p: None,
            repo_roots_provider=lambda: {},
            store=store,
            interval_minutes=60,
        )
        sweeper.start()
        assert sweeper._thread is not None
        sweeper.stop()
        sweeper._thread.join(timeout=3)
        assert not sweeper._thread.is_alive()
