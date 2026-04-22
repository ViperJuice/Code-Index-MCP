"""Periodic full-tree sweeper that recovers inotify/FSEvents drop events (IF-0-P14-5)."""

import logging
import os
import threading
import time
from pathlib import Path
from typing import Callable, Dict, List

from ..core.ignore_patterns import build_walker_filter
from ..metrics.prometheus_exporter import mcp_watcher_sweep_errors_total
from ..storage.sqlite_store import SQLiteStore

logger = logging.getLogger(__name__)

# Supported code-file extensions (mirrors _Handler.code_extensions)
_CODE_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".java",
    ".c",
    ".cpp",
    ".cc",
    ".cxx",
    ".h",
    ".hpp",
    ".cs",
    ".go",
    ".rb",
    ".rs",
    ".swift",
    ".kt",
    ".scala",
    ".php",
    ".r",
    ".m",
    ".mm",
    ".dart",
    ".lua",
    ".pl",
    ".sh",
    ".sql",
    ".html",
    ".css",
    ".scss",
    ".vue",
    ".elm",
    ".ex",
    ".exs",
    ".erl",
    ".clj",
    ".cljs",
    ".hs",
    ".ml",
    ".mli",
    ".f90",
    ".f95",
}

ENV_SWEEP_MINUTES: str = "MCP_WATCHER_SWEEP_MINUTES"
DEFAULT_SWEEP_MINUTES: int = 60


class WatcherSweeper:
    """Periodically diffs filesystem vs SQLite to recover missed watchdog events.

    Calls on_missed_path(repo_id, relative_path) for each code file present on disk
    but absent from the SQLite index. The caller is responsible for re-indexing the file.

    Thread model: single daemon thread using Event.wait() for clean stop.
    """

    def __init__(
        self,
        on_missed_path: Callable[[str, str], None],
        repo_roots_provider: Callable[[], Dict[str, Path]],
        store: SQLiteStore,
        interval_minutes: int = DEFAULT_SWEEP_MINUTES,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._on_missed_path = on_missed_path
        self._repo_roots_provider = repo_roots_provider
        self._store = store
        self._clock = clock

        # Env var overrides constructor arg when set
        env_val = os.environ.get(ENV_SWEEP_MINUTES)
        if env_val is not None:
            try:
                interval_minutes = int(env_val)
            except ValueError:
                pass

        self.interval_minutes = interval_minutes
        self._stop_event = threading.Event()
        self._thread: threading.Thread = None  # type: ignore[assignment]

    def start(self) -> None:
        """Start the background sweep thread."""
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="watcher-sweeper")
        self._thread.start()

    def stop(self) -> None:
        """Signal the sweep thread to stop; returns immediately."""
        self._stop_event.set()

    def _loop(self) -> None:
        """Daemon loop: wait for interval or stop, then sweep."""
        while not self._stop_event.is_set():
            self._stop_event.wait(timeout=self.interval_minutes * 60)
            if self._stop_event.is_set():
                break
            try:
                self.sweep_once()
            except Exception as e:
                logger.warning("watcher sweep error: %s", e)
                mcp_watcher_sweep_errors_total.inc()

    def sweep_once(self) -> List[str]:
        """Diff filesystem vs SQLite; call on_missed_path for each absent file.

        Returns list of repo_ids that had drift.
        """
        drifted: List[str] = []
        repos = self._repo_roots_provider()

        for repo_id, repo_root in repos.items():
            repo_root = Path(repo_root)
            if not repo_root.exists():
                continue

            # Resolve SQLite integer repo id
            repo_record = self._store.get_repository(str(repo_root))
            if repo_record is None:
                continue
            sqlite_repo_id: int = repo_record["id"]

            # Build set of known relative paths from SQLite
            known_files = self._store.get_all_files(repository_id=sqlite_repo_id)
            known_rel_paths = {f["relative_path"] for f in known_files if f.get("relative_path")}

            gitignore_filter = build_walker_filter(repo_root)
            repo_has_drift = False

            for fs_path in repo_root.rglob("*"):
                if not fs_path.is_file():
                    continue
                if fs_path.suffix not in _CODE_EXTENSIONS:
                    continue
                if gitignore_filter(fs_path):
                    continue

                try:
                    rel = fs_path.relative_to(repo_root)
                except ValueError:
                    continue

                rel_str = str(rel).replace("\\", "/")
                if rel_str not in known_rel_paths:
                    self._on_missed_path(repo_id, rel_str)
                    repo_has_drift = True

            if repo_has_drift:
                drifted.append(repo_id)

        return drifted
