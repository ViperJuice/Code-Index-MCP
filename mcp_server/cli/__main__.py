"""Entry point for `python -m mcp_server.cli`.

Imports server_commands directly to avoid triggering the circular import chain
that exists when artifact_commands is loaded transitively through __init__.py.
"""

import click

from mcp_server.cli.preflight_commands import preflight_env
from mcp_server.cli.retention_commands import retention
from mcp_server.cli.server_commands import serve, stdio


@click.group()
def _cli():
    """MCP Server CLI."""


_cli.add_command(serve)
_cli.add_command(stdio)
_cli.add_command(retention)
_cli.add_command(preflight_env)

if __name__ == "__main__":
    _cli()
