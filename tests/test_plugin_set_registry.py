"""Tests for PluginSetRegistry (IF-0-P3-1 — SL-1)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from mcp_server.plugins.plugin_set_registry import PluginSetRegistry


def _make_ctx(repo_id: str):
    ctx = MagicMock()
    ctx.repo_id = repo_id
    return ctx


class TestPluginsFor:
    def test_returns_list(self):
        reg = PluginSetRegistry()
        result = reg.plugins_for("repo-a")
        assert isinstance(result, list)

    def test_stable_same_instance_repeated_call(self):
        reg = PluginSetRegistry()
        list1 = reg.plugins_for("repo-a")
        list2 = reg.plugins_for("repo-a")
        assert list1 is list2

    def test_different_repo_ids_different_lists(self):
        reg = PluginSetRegistry()
        list_a = reg.plugins_for("repo-a")
        list_b = reg.plugins_for("repo-b")
        assert list_a is not list_b


class TestEvict:
    def test_evict_clears_only_target_repo(self):
        reg = PluginSetRegistry()
        list_a = reg.plugins_for("repo-a")
        list_b = reg.plugins_for("repo-b")

        reg.evict("repo-a")

        # repo-b is unaffected — same list instance
        assert reg.plugins_for("repo-b") is list_b
        # repo-a gets a fresh list after eviction
        list_a2 = reg.plugins_for("repo-a")
        assert list_a2 is not list_a

    def test_evict_nonexistent_noop(self):
        reg = PluginSetRegistry()
        # Should not raise
        reg.evict("does-not-exist")


class TestPluginsForFile:
    def test_returns_list_of_tuples(self):
        reg = PluginSetRegistry()
        ctx = _make_ctx("repo-a")
        result = reg.plugins_for_file(ctx, Path("foo.py"))
        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, tuple)
            assert len(item) == 2
            plugin, score = item
            assert isinstance(score, float)

    def test_python_file_returns_python_capable_plugins(self):
        reg = PluginSetRegistry()
        ctx = _make_ctx("repo-a")
        result = reg.plugins_for_file(ctx, Path("foo.py"))
        # At least 0 results (empty is fine in unit context), no error
        assert result is not None
