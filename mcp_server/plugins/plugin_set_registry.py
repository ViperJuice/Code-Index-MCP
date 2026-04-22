"""PluginSetRegistry — IF-0-P3-1 interface freeze.

Per-repo plugin registry. Produces a stable, memory-managed list of plugin
instances scoped to a single ``repo_id``. Repeated calls return the same
instances; evicted entries are reconstructed on demand.

Composes over :class:`MemoryAwarePluginManager` for per-repo cache keying.
Consumed by the dispatcher (SL-6) and by P4's watcher (which calls
:meth:`evict` on repo-removal events).
"""
from __future__ import annotations

import threading
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Protocol, Tuple, runtime_checkable

if TYPE_CHECKING:
    from mcp_server.core.repo_context import RepoContext
    from mcp_server.plugin_base import IPlugin

logger = logging.getLogger(__name__)


@runtime_checkable
class PluginSetRegistryProtocol(Protocol):
    """Per-repo plugin lookup contract."""

    def plugins_for(self, repo_id: str) -> List["IPlugin"]:
        """Return the plugin set bound to ``repo_id``. Stable across calls."""
        ...

    def plugins_for_file(
        self, ctx: "RepoContext", path: Path
    ) -> List[Tuple["IPlugin", float]]:
        """Return plugins capable of handling ``path`` in ``ctx.repo_id``, with scores."""
        ...

    def evict(self, repo_id: str) -> None:
        """Invalidate and release the plugin set for ``repo_id``."""
        ...


class PluginSetRegistry:
    """Per-repo plugin registry backed by MemoryAwarePluginManager.

    Thread-safe via an internal RLock. ``plugins_for(repo_id)`` returns the
    same list instance on every call for the same repo_id until ``evict`` is
    called.  ``plugins_for_file`` scores each plugin by whether its
    ``supports(path)`` method returns True.
    """

    def __init__(self) -> None:
        self._cache: Dict[str, List["IPlugin"]] = {}
        self._lock = threading.RLock()
        self._manager: Optional[object] = None

    def _get_manager(self):
        if self._manager is None:
            from mcp_server.plugins.memory_aware_manager import get_memory_aware_manager
            self._manager = get_memory_aware_manager()
        return self._manager

    def plugins_for(self, repo_id: str) -> List["IPlugin"]:
        """Return a stable, per-repo plugin list.

        The same list instance is returned on every call for the same
        repo_id (identity guarantee). The list is built on first access and
        cached until :meth:`evict` is called.
        """
        with self._lock:
            if repo_id in self._cache:
                return self._cache[repo_id]

            plugins = self._build_plugin_list(repo_id)
            self._cache[repo_id] = plugins
            return plugins

    def _build_plugin_list(self, repo_id: str) -> List["IPlugin"]:
        """Construct the plugin list for a repo_id via the memory manager."""
        from mcp_server.plugins.plugin_factory import PluginFactory, PluginUnavailableError

        languages = PluginFactory.get_supported_languages()
        result: List["IPlugin"] = []

        # Build a lightweight ctx-like object so the manager keys by (repo_id, lang)
        class _Ctx:
            pass

        ctx = _Ctx()
        ctx.repo_id = repo_id  # type: ignore[attr-defined]

        manager = self._get_manager()
        for lang in languages:
            try:
                plugin = manager.get_plugin(lang, ctx)
                if plugin is not None:
                    result.append(plugin)
            except PluginUnavailableError as exc:
                logger.info(
                    "Skipping unavailable plugin for %s: %s",
                    lang,
                    exc.state,
                )
            except Exception:
                logger.exception("Unexpected error loading plugin for %s", lang)

        return result

    def plugins_for_file(
        self, ctx: "RepoContext", path: Path
    ) -> List[Tuple["IPlugin", float]]:
        """Return (plugin, score) pairs for plugins that can handle ``path``.

        Score is 1.0 for a positive ``supports()`` match. Only matching plugins
        are returned.
        """
        plugins = self.plugins_for(ctx.repo_id)
        result: List[Tuple["IPlugin", float]] = []
        for plugin in plugins:
            try:
                if plugin.supports(str(path)):
                    result.append((plugin, 1.0))
            except Exception:
                pass
        return result

    def evict(self, repo_id: str) -> None:
        """Invalidate the cached plugin set for ``repo_id`` only."""
        with self._lock:
            self._cache.pop(repo_id, None)
