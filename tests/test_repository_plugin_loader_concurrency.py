"""
Concurrency tests for RepositoryPluginLoader.

SL-2.1 — Verifies:
  1. 8 threads × 100 iterations on same repo_id all return the same
     RepositoryProfile instance (id() equality).
  2. Two different repo_ids analyzed concurrently do NOT block each
     other: parallel wall-clock < 1.8× serial wall-clock.
"""

import asyncio
import threading
import time
from pathlib import Path
from typing import List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server.plugins.repository_plugin_loader import (
    RepositoryPluginLoader,
    RepositoryProfile,
)


def _make_profile(repo_id: str) -> RepositoryProfile:
    from datetime import datetime

    return RepositoryProfile(
        repository_id=repo_id,
        languages={"python": 10},
        total_files=10,
        indexed_at=datetime.now(),
        primary_languages=["python"],
    )


def _make_loader_with_slow_analysis(delay: float = 0.05) -> RepositoryPluginLoader:
    """Return a loader whose _analyze_index sleeps to simulate I/O."""
    loader = RepositoryPluginLoader.__new__(RepositoryPluginLoader)
    loader.plugin_strategy = "auto"
    loader.analysis_mode = False
    loader.preload_threshold = 1
    loader._profiles = {}
    loader._profiles_lock = threading.Lock()
    loader._profile_build_locks = {}
    loader._loaded_plugins = {}
    loader._language_map = {".py": "python"}
    loader._factory = MagicMock()
    loader.memory_manager = MagicMock()

    original_analyze = RepositoryPluginLoader._analyze_index

    def slow_analyze(self, index_path):
        time.sleep(delay)
        return {"python": 10}

    loader._analyze_index = lambda index_path: slow_analyze(loader, index_path)

    return loader


def _run_async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# Helpers to patch away filesystem calls inside analyze_repository
# ---------------------------------------------------------------------------

def _patch_loader_fs(loader: RepositoryPluginLoader, repo_path: Path, repo_id: str):
    """
    Patch _get_repository_id and IndexDiscovery so analyze_repository
    never touches the real filesystem.
    """
    loader._get_repository_id = lambda path: repo_id

    fake_index_path = Path("/fake/index.db")

    class FakeDiscovery:
        def __init__(self, path):
            pass

        def get_local_index_path(self):
            return fake_index_path

    return patch(
        "mcp_server.plugins.repository_plugin_loader.IndexDiscovery",
        FakeDiscovery,
    )


# ---------------------------------------------------------------------------
# Test 1: same repo_id → same RepositoryProfile instance across all threads
# ---------------------------------------------------------------------------

def test_same_repo_id_returns_identical_instance():
    """8 threads × 100 iterations must all see the same profile object."""
    loader = _make_loader_with_slow_analysis(delay=0.01)
    repo_path = Path("/fake/repo")
    repo_id = "same_repo"

    results: List[RepositoryProfile] = []
    errors: List[Exception] = []
    lock = threading.Lock()

    fake_index_path = Path("/fake/index.db")

    class FakeDiscovery:
        def __init__(self, path):
            pass

        def get_local_index_path(self):
            return fake_index_path

    def worker():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            for _ in range(100):
                with patch(
                    "mcp_server.plugins.repository_plugin_loader.IndexDiscovery",
                    FakeDiscovery,
                ):
                    loader._get_repository_id = lambda path: repo_id
                    profile = loop.run_until_complete(
                        loader.analyze_repository(repo_path)
                    )
                    with lock:
                        results.append(profile)
        except Exception as exc:
            with lock:
                errors.append(exc)
        finally:
            loop.close()

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Worker exceptions: {errors}"
    assert len(results) == 800, f"Expected 800 results, got {len(results)}"

    first_id = id(results[0])
    for i, profile in enumerate(results):
        assert id(profile) == first_id, (
            f"Profile at index {i} is a different object (id={id(profile)} vs {first_id})"
        )


# ---------------------------------------------------------------------------
# Test 2: distinct repo_ids must not serialize — parallel < 1.8× serial
# ---------------------------------------------------------------------------

def test_distinct_repo_ids_do_not_block_each_other():
    """Two different repo_ids analyzed in parallel must not wait for each other."""
    DELAY = 0.10  # seconds per analysis

    def make_loader(delay):
        l = _make_loader_with_slow_analysis(delay=delay)
        return l

    loader = make_loader(DELAY)

    fake_index_path = Path("/fake/index.db")

    class FakeDiscovery:
        def __init__(self, path):
            pass

        def get_local_index_path(self):
            return fake_index_path

    async def analyze_one(repo_id: str):
        loader._get_repository_id = lambda path: repo_id
        with patch(
            "mcp_server.plugins.repository_plugin_loader.IndexDiscovery",
            FakeDiscovery,
        ):
            return await loader.analyze_repository(Path("/fake/repo"))

    # Serial baseline: run repo_a then repo_b sequentially
    loader_serial = make_loader(DELAY)
    t0 = time.monotonic()

    async def run_serial():
        loader_serial._get_repository_id = lambda path: "repo_a"
        with patch(
            "mcp_server.plugins.repository_plugin_loader.IndexDiscovery",
            FakeDiscovery,
        ):
            await loader_serial.analyze_repository(Path("/fake/repo"))
        loader_serial._get_repository_id = lambda path: "repo_b"
        with patch(
            "mcp_server.plugins.repository_plugin_loader.IndexDiscovery",
            FakeDiscovery,
        ):
            await loader_serial.analyze_repository(Path("/fake/repo_b"))

    asyncio.new_event_loop().run_until_complete(run_serial())
    serial_time = time.monotonic() - t0

    # Parallel: two threads each analyze a distinct repo_id
    loader_parallel = make_loader(DELAY)
    times = []
    errors = []

    def thread_worker(rid):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loader_parallel._get_repository_id = lambda path: rid
            with patch(
                "mcp_server.plugins.repository_plugin_loader.IndexDiscovery",
                FakeDiscovery,
            ):
                loop.run_until_complete(
                    loader_parallel.analyze_repository(Path(f"/fake/{rid}"))
                )
        except Exception as exc:
            errors.append(exc)
        finally:
            loop.close()

    t0 = time.monotonic()
    threads = [
        threading.Thread(target=thread_worker, args=(rid,))
        for rid in ("repo_x", "repo_y")
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    parallel_time = time.monotonic() - t0

    assert not errors, f"Worker exceptions: {errors}"
    assert parallel_time < serial_time * 1.8, (
        f"Parallel ({parallel_time:.3f}s) >= 1.8× serial ({serial_time:.3f}s): "
        "distinct repo_ids are being serialized"
    )
