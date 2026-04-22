"""Tests for multi-process safe RepositoryRegistry.save() via flock."""

import json
import multiprocessing
import os
import stat
import time
from datetime import datetime
from pathlib import Path

import pytest

from mcp_server.storage.multi_repo_manager import RepositoryInfo
from mcp_server.storage.repository_registry import RepositoryRegistry


def _worker_save_many(registry_path: Path, start_idx: int, count: int) -> None:
    """Worker: register `count` repos in a fresh RepositoryRegistry and save each."""
    reg = RepositoryRegistry(registry_path=registry_path)
    for i in range(start_idx, start_idx + count):
        repo_info = RepositoryInfo(
            repository_id=f"repo_{i:04d}",
            name=f"repo_{i:04d}",
            path=registry_path.parent / f"repo_{i:04d}",
            index_path=registry_path.parent / f"repo_{i:04d}" / "index.db",
            language_stats={},
            total_files=0,
            total_symbols=0,
            indexed_at=datetime.now(),
        )
        reg.register(repo_info)


def test_save_is_flocked(tmp_path: Path):
    """Two processes each register 50 repos; after both exit all 100 must be present."""
    registry_path = tmp_path / "registry.json"

    p1 = multiprocessing.Process(target=_worker_save_many, args=(registry_path, 0, 50))
    p2 = multiprocessing.Process(target=_worker_save_many, args=(registry_path, 50, 50))
    p1.start()
    p2.start()
    p1.join(timeout=30)
    p2.join(timeout=30)

    assert p1.exitcode == 0, f"Worker 1 exited with code {p1.exitcode}"
    assert p2.exitcode == 0, f"Worker 2 exited with code {p2.exitcode}"

    final = RepositoryRegistry(registry_path=registry_path)
    assert len(final._registry) == 100, f"Expected 100 entries, got {len(final._registry)}"


def _worker_slow_replace(registry_path: Path, start_idx: int, count: int, delay_s: float) -> None:
    """Worker that monkey-patches Path.replace to sleep before renaming."""
    import mcp_server.storage.repository_registry as _mod

    original_save = _mod.RepositoryRegistry.save

    def slow_save(self):
        import fcntl
        import json as _json

        lock_path = self.registry_path.with_suffix(".lock")
        fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            data = {}
            if self.registry_path.exists():
                with open(self.registry_path) as f:
                    data = _json.load(f)
            for repo_id, repo_data in self._registry.items():
                entry = repo_data.copy()
                entry["path"] = str(entry["path"])
                entry["index_path"] = str(entry["index_path"])
                if hasattr(entry.get("indexed_at"), "isoformat"):
                    entry["indexed_at"] = entry["indexed_at"].isoformat()
                data[repo_id] = entry
            temp_path = self.registry_path.with_suffix(".tmp")
            with open(temp_path, "w") as f:
                _json.dump(data, f, indent=2)
            time.sleep(delay_s)
            temp_path.replace(self.registry_path)
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    _mod.RepositoryRegistry.save = slow_save

    reg = RepositoryRegistry(registry_path=registry_path)
    for i in range(start_idx, start_idx + count):
        repo_info = RepositoryInfo(
            repository_id=f"slow_{i:04d}",
            name=f"slow_{i:04d}",
            path=registry_path.parent / f"slow_{i:04d}",
            index_path=registry_path.parent / f"slow_{i:04d}" / "index.db",
            language_stats={},
            total_files=0,
            total_symbols=0,
            indexed_at=datetime.now(),
        )
        reg.register(repo_info)


def test_save_holds_lock_during_rename(tmp_path: Path):
    """Flock exclusivity: second process must wait for slow first process."""
    registry_path = tmp_path / "registry.json"
    delay = 0.1

    t0 = time.monotonic()
    p1 = multiprocessing.Process(target=_worker_slow_replace, args=(registry_path, 0, 1, delay))
    p2 = multiprocessing.Process(target=_worker_slow_replace, args=(registry_path, 1, 1, delay))
    p1.start()
    p2.start()
    p1.join(timeout=10)
    p2.join(timeout=10)
    elapsed = time.monotonic() - t0

    assert p1.exitcode == 0
    assert p2.exitcode == 0
    assert elapsed >= delay, f"Total elapsed {elapsed:.3f}s < {delay}s — locking not working"
    assert elapsed < 5.0, f"Total elapsed {elapsed:.3f}s — too slow"


def test_save_releases_lock_on_exception(tmp_path: Path):
    """Lock must be released even when save raises; subsequent save must succeed."""
    registry_path = tmp_path / "registry.json"
    reg = RepositoryRegistry(registry_path=registry_path)

    repo_info = RepositoryInfo(
        repository_id="before_err",
        name="before_err",
        path=tmp_path / "before_err",
        index_path=tmp_path / "before_err" / "index.db",
        language_stats={},
        total_files=0,
        total_symbols=0,
        indexed_at=datetime.now(),
    )
    reg._registry["before_err"] = {
        "repository_id": "before_err",
        "name": "before_err",
        "path": tmp_path / "before_err",
        "index_path": tmp_path / "before_err" / "index.db",
        "language_stats": {},
        "total_files": 0,
        "total_symbols": 0,
        "indexed_at": datetime.now(),
        "active": True,
        "priority": 0,
    }

    import builtins

    original_json_dumps = json.dumps
    call_count = {"n": 0}

    def _raise_once(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("injected json.dumps failure")
        return original_json_dumps(*args, **kwargs)

    import mcp_server.storage.repository_registry as _mod

    original_json_mod = _mod.json

    class _PatchedJson:
        def __getattr__(self, name):
            if name == "dumps":
                return _raise_once
            return getattr(original_json_mod, name)

    _mod.json = _PatchedJson()  # type: ignore[assignment]
    try:
        try:
            reg.save()
        except Exception:
            pass

        # Restore json before the second save
        _mod.json = original_json_mod
        reg.save()
    finally:
        _mod.json = original_json_mod

    assert registry_path.exists(), "Registry file should exist after successful second save"


def test_lock_file_mode_0o600(tmp_path: Path):
    """Sidecar .lock file must have mode 0o600."""
    registry_path = tmp_path / "registry.json"
    reg = RepositoryRegistry(registry_path=registry_path)

    repo_info = RepositoryInfo(
        repository_id="mode_test",
        name="mode_test",
        path=tmp_path / "mode_test",
        index_path=tmp_path / "mode_test" / "index.db",
        language_stats={},
        total_files=0,
        total_symbols=0,
        indexed_at=datetime.now(),
    )
    reg.register(repo_info)

    lock_path = registry_path.with_suffix(".lock")
    assert lock_path.exists(), "Lock file should be created after save()"
    mode = stat.S_IMODE(os.stat(lock_path).st_mode)
    assert mode == 0o600, f"Expected 0o600, got {oct(mode)}"
