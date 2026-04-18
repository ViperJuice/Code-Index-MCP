"""Tracked-ref poller: triggers incremental reindex on branch tip advance."""

import logging
import subprocess
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class RefPoller:
    """Poll refs/heads/<tracked_branch> per repo and trigger reindex on advance."""

    def __init__(
        self,
        registry: Any,
        git_index_manager: Any,
        dispatcher: Any,
        repo_resolver: Any,
        *,
        interval_seconds: int = 30,
    ) -> None:
        self._registry = registry
        self._git_index_manager = git_index_manager
        self._interval = interval_seconds
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="RefPoller")
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)

    def _run(self) -> None:
        while not self._stop_event.is_set():
            for repo in self._registry.list_all():
                try:
                    self._poll_one(repo)
                except Exception:
                    logger.exception("Unhandled error polling repo %s", getattr(repo, "repository_id", repo))
            self._stop_event.wait(self._interval)

    def _poll_one(self, repo_info: Any) -> None:
        tracked_branch = getattr(repo_info, "tracked_branch", None)
        if not tracked_branch:
            return

        repo_path = Path(repo_info.path)
        tip_sha = self._read_ref(repo_path, tracked_branch)
        if tip_sha is None:
            return

        last = getattr(repo_info, "last_indexed_commit", None)
        if tip_sha != last:
            self._git_index_manager.sync_repository_index(repo_info.repository_id)

    def _read_ref(self, repo_path: Path, branch: str) -> str | None:
        ref_file = repo_path / ".git" / "refs" / "heads" / branch
        if ref_file.exists():
            return ref_file.read_text().strip()

        # Fallback: packed refs via git rev-parse
        try:
            result = subprocess.run(
                ["git", "--git-dir", str(repo_path / ".git"), "rev-parse", f"refs/heads/{branch}"],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            logger.warning(
                "Could not resolve ref refs/heads/%s for repo at %s; skipping",
                branch,
                repo_path,
            )
            return None
