"""PluginSetRegistry — IF-0-P3-1 interface freeze.

Per-repo plugin registry. Produces a stable, memory-managed list of plugin
instances scoped to a single ``repo_id``. Repeated calls return the same
instances; evicted entries are reconstructed on demand.

SL-1 replaces the stub bodies below with a real implementation that composes
over :class:`MemoryAwarePluginManager`. Consumed by the dispatcher (SL-6) and
by P4's watcher (which calls :meth:`evict` on repo-removal events).
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, List, Protocol, Tuple, runtime_checkable

if TYPE_CHECKING:
    from mcp_server.core.repo_context import RepoContext
    from mcp_server.plugin_base import IPlugin


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
    """SL-0 stub. SL-1 replaces with the real impl."""

    def plugins_for(self, repo_id: str) -> List["IPlugin"]:
        raise NotImplementedError("PluginSetRegistry is an SL-0 stub; SL-1 implements.")

    def plugins_for_file(
        self, ctx: "RepoContext", path: Path
    ) -> List[Tuple["IPlugin", float]]:
        raise NotImplementedError("PluginSetRegistry is an SL-0 stub; SL-1 implements.")

    def evict(self, repo_id: str) -> None:
        raise NotImplementedError("PluginSetRegistry is an SL-0 stub; SL-1 implements.")
