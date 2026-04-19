"""Tests for dependency-aware search via DependencyGraphAnalyzer (IF-0-P14-2 — SL-2.1)."""

from pathlib import Path
from typing import List, Optional
from unittest.mock import MagicMock

import pytest

from mcp_server.dependency_graph.aggregator import DependencyGraphAnalyzer


# ---------------------------------------------------------------------------
# Minimal RepositoryInfo stub (mirrors the real dataclass API we need)
# ---------------------------------------------------------------------------


def _make_repo_info(repo_id: str, name: str, path: Path) -> MagicMock:
    info = MagicMock()
    info.repository_id = repo_id
    info.name = name
    info.path = path
    return info


def _make_manager(repos: list) -> MagicMock:
    mgr = MagicMock()
    mgr.list_repositories.return_value = repos
    mgr.get_repository_info.side_effect = lambda rid: next(
        (r for r in repos if r.repository_id == rid), None
    )
    return mgr


# ---------------------------------------------------------------------------
# test_three_repo_dep_graph_nonempty
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_three_repo_dep_graph_nonempty(tmp_path: Path) -> None:
    """Three repos each containing a manifest that references another repo's name."""
    repo_a = tmp_path / "repo_a"
    repo_b = tmp_path / "repo_b"
    repo_c = tmp_path / "repo_c"
    for d in (repo_a, repo_b, repo_c):
        d.mkdir()

    # repo_a: Python, depends on "repo-b" (registered name)
    (repo_a / "requirements.txt").write_text("repo-b\n")

    # repo_b: npm, depends on "repo-c" (registered name)
    (repo_b / "package.json").write_text(
        '{"name": "repo-b", "dependencies": {"repo-c": "1.0"}}'
    )

    # repo_c: Go, depends on "repo_a" module path (registered name)
    (repo_c / "go.mod").write_text(
        "module repo_c\n\ngo 1.21\n\nrequire repo_a v0.1.0\n"
    )

    repos = [
        _make_repo_info("id-a", "repo-b", repo_a),   # repo_a is named "repo-b" for py lookup
        _make_repo_info("id-b", "repo-c", repo_b),   # repo_b is named "repo-c" for npm lookup
        _make_repo_info("id-c", "repo_a", repo_c),   # repo_c is named "repo_a" for go lookup
    ]
    # Adjust: let's use cleaner distinct names
    # repo_a (Python) depends on package "lib-b"
    # repo_b (npm) depends on package "lib-c"
    # repo_c (Go) depends on module "lib-a"
    repo_a2 = tmp_path / "repo_a2"
    repo_b2 = tmp_path / "repo_b2"
    repo_c2 = tmp_path / "repo_c2"
    for d in (repo_a2, repo_b2, repo_c2):
        d.mkdir()

    (repo_a2 / "requirements.txt").write_text("lib-b\nlib-c\n")
    (repo_b2 / "package.json").write_text(
        '{"name": "lib-b", "dependencies": {"lib-c": "1.0"}}'
    )
    (repo_c2 / "go.mod").write_text(
        "module lib-c\n\ngo 1.21\n\nrequire lib-a v0.1.0\n"
    )

    repos2 = [
        _make_repo_info("id-a2", "lib-b", repo_b2),
        _make_repo_info("id-b2", "lib-c", repo_c2),
        _make_repo_info("id-c2", "lib-a", repo_a2),  # lib-a maps to repo_a2 path
    ]

    mgr = _make_manager(repos2)
    analyzer = DependencyGraphAnalyzer(mgr)

    # repo_a2 depends on lib-b (id-a2) and lib-c (id-b2)
    deps_a = await analyzer.analyze("id-c2")
    assert len(deps_a) > 0, "repo_a2 must resolve at least one dependency"

    # repo_b2 depends on lib-c (id-b2)
    deps_b = await analyzer.analyze("id-a2")
    assert len(deps_b) > 0, "repo_b2 must resolve at least one dependency"


# ---------------------------------------------------------------------------
# test_unresolved_package_dropped
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unresolved_package_dropped(tmp_path: Path) -> None:
    """Packages not owned by any registered repo are silently dropped."""
    repo_x = tmp_path / "repo_x"
    repo_x.mkdir()

    # depends on "known-lib" and "unknown-lib"
    (repo_x / "requirements.txt").write_text("known-lib\nunknown-lib\n")

    known_repo = _make_repo_info("id-known", "known-lib", tmp_path / "known_repo")
    mgr = _make_manager([known_repo, _make_repo_info("id-x", "repo-x", repo_x)])
    analyzer = DependencyGraphAnalyzer(mgr)

    deps = await analyzer.analyze("id-x")
    assert "id-known" in deps
    assert len(deps) == 1, "unknown-lib must be silently dropped"
