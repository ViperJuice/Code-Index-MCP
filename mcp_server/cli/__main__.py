"""Entry point for `python -m mcp_server.cli`.

Imports server_commands directly to avoid triggering the circular import chain
that exists when artifact_commands is loaded transitively through __init__.py.
"""
import sys

import click

from mcp_server.cli.server_commands import serve, stdio


@click.group()
def _cli():
    """MCP Server CLI."""


_cli.add_command(serve)
_cli.add_command(stdio)

if __name__ == "__main__":
    _cli()
