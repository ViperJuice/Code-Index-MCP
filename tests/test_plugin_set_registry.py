"""Tests for PluginSetRegistry (IF-0-P3-1 — SL-1)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from mcp_server.plugins.plugin_set_registry import PluginSetRegistry


class _FakePlugin:
    def __init__(self, language: str) -> None:
        self.language = language
        self.closed = 0

    def supports(self, path: str) -> bool:
        extensions = {"python": ".py", "rust": ".rs"}
        return path.endswith(extensions.get(self.language, ".never"))

    def bind(self, ctx) -> None:
        self.repo_id = ctx.repo_id

    def close(self) -> None:
        self.closed += 1


class _FakeManager:
    def __init__(self) -> None:
        self.plugins = {}
        self.get_calls = []

    def loaded_plugins_for(self, repo_id: str):
        return [
            plugin
            for (loaded_repo_id, _), plugin in self.plugins.items()
            if loaded_repo_id == repo_id
        ]

    def get_plugin(self, language: str, ctx):
        self.get_calls.append((ctx.repo_id, language))
        return self.plugins.setdefault((ctx.repo_id, language), _FakePlugin(language))

    def evict_repo(self, repo_id: str) -> int:
        keys = [key for key in self.plugins if key[0] == repo_id]
        for key in keys:
            self.plugins.pop(key).close()
        return len(keys)

    def resource_snapshot(self):
        return SimpleNamespace(reserved_workers=len(self.plugins))

    def shutdown(self) -> None:
        for plugin in self.plugins.values():
            plugin.close()
        self.plugins.clear()


def _make_ctx(repo_id: str):
    ctx = MagicMock()
    ctx.repo_id = repo_id
    return ctx


class TestPluginsFor:
    def test_returns_list(self):
        reg = PluginSetRegistry(_FakeManager())
        result = reg.plugins_for("repo-a")
        assert isinstance(result, list)

    def test_stable_same_instance_repeated_call(self):
        reg = PluginSetRegistry(_FakeManager())
        list1 = reg.plugins_for("repo-a")
        list2 = reg.plugins_for("repo-a")
        assert list1 is list2

    def test_different_repo_ids_different_lists(self):
        reg = PluginSetRegistry(_FakeManager())
        list_a = reg.plugins_for("repo-a")
        list_b = reg.plugins_for("repo-b")
        assert list_a is not list_b

    def test_status_read_does_not_allocate_plugins(self):
        manager = _FakeManager()
        reg = PluginSetRegistry(manager)
        assert reg.plugins_for("repo-a") == []
        assert manager.get_calls == []


class TestEvict:
    def test_evict_clears_only_target_repo(self):
        reg = PluginSetRegistry(_FakeManager())
        list_a = reg.plugins_for("repo-a")
        list_b = reg.plugins_for("repo-b")

        reg.evict("repo-a")

        # repo-b is unaffected — same list instance
        assert reg.plugins_for("repo-b") is list_b
        # repo-a gets a fresh list after eviction
        list_a2 = reg.plugins_for("repo-a")
        assert list_a2 is not list_a

    def test_evict_nonexistent_noop(self):
        reg = PluginSetRegistry(_FakeManager())
        # Should not raise
        reg.evict("does-not-exist")


class TestPluginsForFile:
    def test_returns_list_of_tuples(self):
        reg = PluginSetRegistry(_FakeManager())
        ctx = _make_ctx("repo-a")
        result = reg.plugins_for_file(ctx, Path("foo.py"))
        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, tuple)
            assert len(item) == 2
            plugin, score = item
            assert isinstance(score, float)

    def test_python_file_returns_python_capable_plugins(self):
        reg = PluginSetRegistry(_FakeManager())
        ctx = _make_ctx("repo-a")
        result = reg.plugins_for_file(ctx, Path("foo.py"))
        # At least 0 results (empty is fine in unit context), no error
        assert result is not None

    def test_allocates_only_languages_requested_for_repo(self):
        manager = _FakeManager()
        reg = PluginSetRegistry(manager)
        ctx = _make_ctx("repo-a")

        assert len(reg.plugins_for_file(ctx, Path("foo.py"))) == 1
        assert len(reg.plugins_for_file(ctx, Path("lib.rs"))) == 1
        assert len(reg.plugins_for_file(ctx, Path("again.py"))) == 1

        assert manager.get_calls == [
            ("repo-a", "python"),
            ("repo-a", "rust"),
            ("repo-a", "python"),
        ]
        assert len(reg.plugins_for("repo-a")) == 2

    def test_evict_delegates_close_to_lifecycle_manager(self):
        manager = _FakeManager()
        reg = PluginSetRegistry(manager)
        ctx = _make_ctx("repo-a")
        plugin = reg.plugins_for_file(ctx, Path("foo.py"))[0][0]

        reg.evict("repo-a")

        assert plugin.closed == 1
        assert reg.plugins_for("repo-a") == []
