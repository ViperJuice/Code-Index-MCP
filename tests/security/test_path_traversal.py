"""Tests for PathTraversalGuard."""

from __future__ import annotations

from pathlib import Path

import pytest

from mcp_server.security.path_guard import PathTraversalError, PathTraversalGuard


def test_traversal_attempt_raises(tmp_path):
    guard = PathTraversalGuard([tmp_path])
    with pytest.raises(PathTraversalError):
        guard.normalize_and_check("../../etc/passwd")


def test_allowed_path_returns_resolved(tmp_path):
    allowed = tmp_path / "ok.txt"
    allowed.touch()
    guard = PathTraversalGuard([tmp_path])
    result = guard.normalize_and_check(allowed)
    assert result == allowed.resolve()


def test_empty_roots_denies(tmp_path):
    guard = PathTraversalGuard([])
    with pytest.raises(PathTraversalError):
        guard.normalize_and_check(tmp_path / "ok.txt")


def test_subdir_allowed(tmp_path):
    subdir = tmp_path / "sub"
    subdir.mkdir()
    guard = PathTraversalGuard([tmp_path])
    result = guard.normalize_and_check(subdir / "file.py")
    assert str(result).startswith(str(tmp_path.resolve()))


def test_sibling_root_denied(tmp_path):
    root_a = tmp_path / "a"
    root_b = tmp_path / "b"
    root_a.mkdir()
    root_b.mkdir()
    guard = PathTraversalGuard([root_a])
    with pytest.raises(PathTraversalError):
        guard.normalize_and_check(root_b / "secret.txt")


def test_normalize_result_drops_traversal_hit(tmp_path, monkeypatch):
    """_normalize_search_result returns None for a path-traversal hit when MCP_ALLOWED_ROOTS is set."""
    import os

    monkeypatch.setenv("MCP_ALLOWED_ROOTS", str(tmp_path))

    # Import after env is set so _get_path_guard reads fresh env.
    from mcp_server.gateway import _normalize_search_result

    raw = {"file": "../../../etc/passwd", "line": 1, "snippet": "root:x"}
    result = _normalize_search_result(raw)
    assert result is None


def test_normalize_result_allows_valid_path(tmp_path, monkeypatch):
    """_normalize_search_result keeps hits within MCP_ALLOWED_ROOTS."""
    monkeypatch.setenv("MCP_ALLOWED_ROOTS", str(tmp_path))

    allowed_file = tmp_path / "foo.py"
    allowed_file.touch()

    from mcp_server.gateway import _normalize_search_result

    raw = {"file": str(allowed_file), "line": 1, "snippet": "x = 1"}
    result = _normalize_search_result(raw)
    assert result is not None
    assert "foo.py" in result["file"]
