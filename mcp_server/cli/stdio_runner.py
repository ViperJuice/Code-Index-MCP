"""MCP stdio server runner — IF-0-P2B-3 stub.

SL-2 fills in the body (moves ~800 lines of tool-handler logic out of
``scripts/cli/mcp_server_cli.py`` into ``mcp_server/cli/tool_handlers.py``
and the Server wiring here).

``run()`` is invoked by ``mcp_server.cli.server_commands:stdio`` (added as
a Click subcommand in SL-2) and by ``scripts/cli/mcp_server_cli.py``'s
3-line shim.
"""
from __future__ import annotations


def run() -> None:
    """Boot the MCP stdio server. Raises ``NotImplementedError`` until SL-2."""
    raise NotImplementedError(
        "stdio_runner.run() is an SL-0 stub; SL-2 implements the body."
    )
