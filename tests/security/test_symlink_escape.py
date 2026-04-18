"""Tests for symlink-escape hardening in path_allowlist."""
import os
from pathlib import Path

import pytest

from mcp_server.security.path_allowlist import path_within_allowed, resolve_allowed_roots


def test_symlink_escape_returns_false(tmp_path):
    allowed_root = tmp_path / "allowed_root"
    allowed_root.mkdir()
    link = allowed_root / "link_to_passwd"
    link.symlink_to("/etc/passwd")
    result = path_within_allowed(link, roots=(allowed_root,))
    assert result is False


def test_real_file_inside_root_returns_true(tmp_path):
    allowed_root = tmp_path / "allowed_root"
    allowed_root.mkdir()
    real_file = allowed_root / "real_file.txt"
    real_file.write_text("hello")
    result = path_within_allowed(real_file, roots=(allowed_root,))
    assert result is True


def test_candidate_outside_roots_returns_false(tmp_path):
    allowed_root = tmp_path / "allowed_root"
    allowed_root.mkdir()
    outside = tmp_path / "other" / "file.txt"
    result = path_within_allowed(outside, roots=(allowed_root,))
    assert result is False


def test_resolve_allowed_roots_caches(tmp_path):
    resolve_allowed_roots.cache_clear()
    raw = (str(tmp_path),)
    first = resolve_allowed_roots(raw)
    second = resolve_allowed_roots(raw)
    assert first is second


def test_resolve_allowed_roots_cache_clear(tmp_path):
    resolve_allowed_roots.cache_clear()
    raw = (str(tmp_path),)
    first = resolve_allowed_roots(raw)
    resolve_allowed_roots.cache_clear()
    second = resolve_allowed_roots(raw)
    assert first is not second
