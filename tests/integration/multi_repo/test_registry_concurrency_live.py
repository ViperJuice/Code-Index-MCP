"""
SL-1.1: Registry concurrency load test.

2 multiprocessing.Process writers × 100 register_repository calls each
to a shared registry; post-run registry must have 200 distinct repo_ids.
"""

import multiprocessing
import tempfile
from pathlib import Path

import pytest

from mcp_server.storage.repository_registry import RepositoryRegistry


def _writer(registry_path: Path, start_idx: int, count: int) -> None:
    """Register `count` distinct repo paths starting at `start_idx`."""
    reg = RepositoryRegistry(registry_path=registry_path)
    for i in range(start_idx, start_idx + count):
        repo_dir = registry_path.parent / f"repo-{i}"
        repo_dir.mkdir(parents=True, exist_ok=True)
        reg.register_repository(str(repo_dir))


def test_concurrent_writers_200_distinct_repo_ids():
    """Two concurrent processes each register 100 repos; final count must be ≥200."""
    with tempfile.TemporaryDirectory(prefix="mcp_p20_sl1_conc_") as tmpdir:
        registry_path = Path(tmpdir) / "registry.json"

        p1 = multiprocessing.Process(target=_writer, args=(registry_path, 0, 100))
        p2 = multiprocessing.Process(target=_writer, args=(registry_path, 100, 100))

        p1.start()
        p2.start()
        p1.join(timeout=60)
        p2.join(timeout=60)

        assert p1.exitcode == 0, f"Writer-1 exited with code {p1.exitcode}"
        assert p2.exitcode == 0, f"Writer-2 exited with code {p2.exitcode}"

        final_reg = RepositoryRegistry(registry_path=registry_path)
        # Must have received all 200 registrations with distinct repo_ids
        repo_ids = set(final_reg._registry.keys())
        assert len(repo_ids) >= 200, (
            f"Expected ≥200 distinct repo_ids, got {len(repo_ids)}"
        )
