"""SL-4.1 — Fixture contract tests.

Verifies that the P2B shared fixtures behave correctly before the
rest of the test suite depends on them.
"""
from __future__ import annotations

import pytest

from mcp_server.core.repo_context import RepoContext
from mcp_server.dispatcher.protocol import DispatcherProtocol
from mcp_server.storage.sqlite_store import SQLiteStore


class TestRepoCtxFixture:
    """repo_ctx fixture must return a fully hydrated RepoContext."""

    def test_returns_repo_context_type(self, repo_ctx):
        assert isinstance(repo_ctx, RepoContext)

    def test_has_live_sqlite_store(self, repo_ctx):
        assert isinstance(repo_ctx.sqlite_store, SQLiteStore)

    def test_has_repo_id(self, repo_ctx):
        assert repo_ctx.repo_id
        assert isinstance(repo_ctx.repo_id, str)

    def test_has_workspace_root(self, repo_ctx):
        from pathlib import Path

        assert isinstance(repo_ctx.workspace_root, Path)

    def test_has_registry_entry(self, repo_ctx):
        assert repo_ctx.registry_entry is not None


class TestStoreRegistryFixture:
    """store_registry fixture must shut down cleanly."""

    def test_shuts_down_cleanly(self, store_registry):
        # shutdown() is called by the fixture teardown; calling it again
        # should be idempotent and not raise.
        store_registry.shutdown()


class TestDispatcherFactoryFixture:
    """dispatcher_factory() must return a DispatcherProtocol instance."""

    def test_produces_dispatcher_protocol(self, dispatcher_factory):
        d = dispatcher_factory()
        assert isinstance(d, DispatcherProtocol)

    def test_is_runtime_checkable(self, dispatcher_factory):
        from typing import runtime_checkable

        d = dispatcher_factory()
        # runtime_checkable is applied at class definition time; just verify
        # isinstance works (it would raise TypeError if not checkable).
        assert isinstance(d, DispatcherProtocol)
