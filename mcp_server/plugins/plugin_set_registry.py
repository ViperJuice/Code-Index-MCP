"""PluginSetRegistry — IF-0-P3-1 interface freeze.

Per-repo plugin registry. Produces a stable, memory-managed list of plugin
instances scoped to a single ``repo_id``. Repeated calls return the same
instances; evicted entries are reconstructed on demand.

Composes over :class:`MemoryAwarePluginManager` for per-repo cache keying.
Consumed by the dispatcher (SL-6) and by P4's watcher (which calls
:meth:`evict` on repo-removal events).
"""

from __future__ import annotations

import logging
import threading
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

    def plugins_for_file(self, ctx: "RepoContext", path: Path) -> List[Tuple["IPlugin", float]]:
        """Return plugins capable of handling ``path`` in ``ctx.repo_id``, with scores."""
        ...

    def evict(self, repo_id: str) -> None:
        """Invalidate and release the plugin set for ``repo_id``."""
        ...

    def resource_snapshot(self):
        """Return worker resource telemetry without allocating plugins."""
        ...

    def loaded_count(self, repo_id: str) -> int:
        """Return the loaded adapter count for one repository."""
        ...

    def shutdown(self) -> None:
        """Close every plugin worker owned by the registry manager."""
        ...


class PluginSetRegistry:
    """Per-repo plugin registry backed by MemoryAwarePluginManager.

    Thread-safe via an internal RLock. ``plugins_for(repo_id)`` returns the
    same list instance on every call for the same repo_id until ``evict`` is
    called.  ``plugins_for_file`` scores each plugin by whether its
    ``supports(path)`` method returns True.
    """

    def __init__(self, manager: Optional[object] = None) -> None:
        self._cache: Dict[str, List["IPlugin"]] = {}
        self._lock = threading.RLock()
        self._manager: Optional[object] = manager

    def _get_manager(self):
        if self._manager is None:
            from mcp_server.plugins.memory_aware_manager import get_memory_aware_manager

            self._manager = get_memory_aware_manager()
        return self._manager

    def _sync_loaded(self, repo_id: str) -> List["IPlugin"]:
        """Drop registry references evicted by the lifecycle manager."""
        plugins = self.plugins_for(repo_id)
        active = self._get_manager().loaded_plugins_for(repo_id)
        active_ids = {id(plugin) for plugin in active}
        plugins[:] = [plugin for plugin in plugins if id(plugin) in active_ids]
        return plugins

    def plugins_for(self, repo_id: str) -> List["IPlugin"]:
        """Return a stable, per-repo plugin list.

        The same list instance is returned on every call for the same
        repo_id (identity guarantee). It contains only plugins already requested
        for that repository and never allocates merely to answer a status read.
        """
        with self._lock:
            if repo_id in self._cache:
                return self._cache[repo_id]

            manager = self._get_manager()
            plugins = list(manager.loaded_plugins_for(repo_id))
            self._cache[repo_id] = plugins
            return plugins

    def plugins_for_file(self, ctx: "RepoContext", path: Path) -> List[Tuple["IPlugin", float]]:
        """Return (plugin, score) pairs for plugins that can handle ``path``.

        Score is 1.0 for a positive ``supports()`` match. Only matching plugins
        are returned.
        """
        from mcp_server.plugins.language_registry import get_language_by_extension
        from mcp_server.plugins.memory_aware_manager import PluginBackpressureError

        plugins = self.plugins_for(ctx.repo_id)
        language = get_language_by_extension(path.suffix.lower())
        if language is not None:
            try:
                plugin = self._get_manager().get_plugin(language, ctx)
            except PluginBackpressureError:
                raise
            except Exception as exc:
                logger.info("Plugin %s unavailable for %s: %s", language, path, exc)
                plugin = None
            if plugin is not None and all(existing is not plugin for existing in plugins):
                bind = getattr(plugin, "bind", None)
                if callable(bind):
                    bind(ctx)
                    confirm_started = getattr(self._get_manager(), "confirm_plugin_started", None)
                    if callable(confirm_started):
                        try:
                            confirm_started(language, ctx)
                        finally:
                            plugins = self._sync_loaded(ctx.repo_id)
                plugins.append(plugin)

        result: List[Tuple["IPlugin", float]] = []
        for plugin in plugins:
            try:
                if plugin.supports(str(path)):
                    confirm_started = getattr(self._get_manager(), "confirm_plugin_started", None)
                    if callable(confirm_started):
                        try:
                            confirm_started(language or getattr(plugin, "language", ""), ctx)
                        finally:
                            plugins = self._sync_loaded(ctx.repo_id)
                    result.append((plugin, 1.0))
            except PluginBackpressureError:
                raise
            except Exception as exc:
                logger.warning("Plugin support probe failed for %s: %s", path, exc)
        return result

    def evict(self, repo_id: str) -> None:
        """Invalidate the cached plugin set for ``repo_id`` only."""
        with self._lock:
            self._cache.pop(repo_id, None)
            self._get_manager().evict_repo(repo_id)

    def resource_snapshot(self):
        """Return worker resource telemetry without creating adapters."""
        return self._get_manager().resource_snapshot()

    def loaded_count(self, repo_id: str) -> int:
        """Return a per-repository adapter count without allocating."""
        with self._lock:
            return len(self._sync_loaded(repo_id))

    def shutdown(self) -> None:
        """Close every manager-owned plugin and clear registry references."""
        with self._lock:
            self._cache.clear()
            self._get_manager().shutdown()
