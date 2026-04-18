"""P2B bootstrap entry — IF-0-P2B-4 stub.

SL-2 fills in the body. SL-0 only freezes the signature so dispatcher/CLI
lanes can import it without a circular wait.

Contract: ``initialize_stateless_services()`` constructs the process-wide
service pool (``StoreRegistry`` + ``RepoResolver``) and a dispatcher that
takes no per-repo state at init time. Every subsequent MCP tool call
resolves a ``RepoContext`` per-request and threads it through dispatcher
methods. No cwd capture, no preloaded ``sqlite_store``.
"""
from __future__ import annotations

from typing import Tuple

from mcp_server.core.repo_resolver import RepoResolver
from mcp_server.dispatcher.protocol import DispatcherProtocol
from mcp_server.storage.store_registry import StoreRegistry


def initialize_stateless_services() -> Tuple[StoreRegistry, RepoResolver, DispatcherProtocol]:
    """Construct the process-wide service pool.

    Returns a triple of (store registry, repo resolver, dispatcher). The
    dispatcher instance holds no per-repo state; every public method takes
    ``ctx: RepoContext`` — see :class:`DispatcherProtocol`.

    Raises ``NotImplementedError`` until SL-2 lands.
    """
    raise NotImplementedError(
        "initialize_stateless_services() is an SL-0 stub; SL-2 implements the body."
    )
