"""Tests for PluginFactory.create_plugin_async (SL-3)."""
import asyncio
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mcp_server.plugins.plugin_factory import PluginFactory, SPECIFIC_PLUGINS
from mcp_server.plugin_base import IPlugin


class _MockPlugin(IPlugin):
    """Minimal IPlugin for testing."""
    lang = "python"

    def __init__(self, sqlite_store=None, enable_semantic=True):
        self._ctx = None

    def bind(self, ctx):
        self._ctx = ctx

    def supports(self, path):
        return True

    def indexFile(self, path, content):
        return {"file": str(path), "symbols": [], "language": "python"}

    def getDefinition(self, symbol):
        return None

    def findReferences(self, symbol):
        return []

    def search(self, query, opts=None):
        return []


class _SlowPlugin(_MockPlugin):
    """Plugin whose ctor blocks for 0.2 s — used for non-blocking test."""

    def __init__(self, sqlite_store=None, enable_semantic=True):
        time.sleep(0.2)
        super().__init__(sqlite_store=sqlite_store, enable_semantic=enable_semantic)


def _make_ctx(repo_id="testrepo"):
    ctx = MagicMock()
    ctx.repo_id = repo_id
    return ctx


# ---------------------------------------------------------------------------
# SL-3.1 — RED tests (must fail before implementation, green after)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_plugin_async_returns_bound_plugin():
    """Returned plugin must have bind() called with ctx."""
    ctx = _make_ctx()
    with patch.dict(SPECIFIC_PLUGINS, {"python": _MockPlugin}):
        plugin = await PluginFactory.create_plugin_async("python", ctx)

    assert isinstance(plugin, IPlugin)
    assert plugin._ctx is ctx, "bind(ctx) must be called post-construction"


@pytest.mark.asyncio
async def test_create_plugin_async_same_instance_in_flight():
    """Two concurrent calls for the same (language, repo_id) return the same instance."""
    ctx = _make_ctx(repo_id="repo-cache-test")
    with patch.dict(SPECIFIC_PLUGINS, {"python": _MockPlugin}):
        p1, p2 = await asyncio.gather(
            PluginFactory.create_plugin_async("python", ctx),
            PluginFactory.create_plugin_async("python", ctx),
        )
    assert p1 is p2, "in-flight cache should return the same future/instance"


@pytest.mark.asyncio
async def test_create_plugin_async_does_not_block_event_loop():
    """A slow-ctor plugin must not starve a concurrent asyncio.sleep."""
    ctx = _make_ctx(repo_id="repo-nonblock")
    sleep_done_at = None
    slow_create_done_at = None

    async def run_sleep():
        nonlocal sleep_done_at
        await asyncio.sleep(0.05)
        sleep_done_at = time.monotonic()

    async def run_create():
        nonlocal slow_create_done_at
        with patch.dict(SPECIFIC_PLUGINS, {"python": _SlowPlugin}):
            await PluginFactory.create_plugin_async("python", ctx)
        slow_create_done_at = time.monotonic()

    start = time.monotonic()
    await asyncio.gather(run_sleep(), run_create())

    assert sleep_done_at is not None
    assert slow_create_done_at is not None
    # The sleep (0.05 s) must complete well before the slow ctor (0.2 s) finishes.
    # Allow 0.1 s slack for scheduling jitter.
    assert sleep_done_at < slow_create_done_at, (
        "asyncio.sleep(0.05) should finish before the 0.2 s slow ctor"
    )
    elapsed = sleep_done_at - start
    assert elapsed < 0.15, (
        f"sleep took {elapsed:.3f}s — event loop was probably blocked"
    )
