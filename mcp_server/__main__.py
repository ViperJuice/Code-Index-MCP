#!/usr/bin/env python3
"""
Main entry point for running MCP server with different transports.
"""

import sys
import asyncio
import click
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mcp_server.cli.index_commands import index


@click.group(invoke_without_command=True)
@click.option('--transport', type=click.Choice(['stdio', 'websocket']), default='stdio', help='Transport protocol to use')
@click.option('--host', default='localhost', help='Host for WebSocket transport')
@click.option('--port', default=8765, type=int, help='Port for WebSocket transport')
@click.pass_context
def cli(ctx, transport: str, host: str, port: int):
    """MCP Server - Model Context Protocol server for code intelligence."""
    # If no subcommand, run the server
    if ctx.invoked_subcommand is None:
        if transport == "stdio":
            # Run stdio server
            from mcp_server.stdio_server import main as stdio_main
            asyncio.run(stdio_main())
        else:
            # Run WebSocket server
            print(f"WebSocket server not yet implemented. Use stdio transport.")
            sys.exit(1)


# Add subcommands
cli.add_command(index)


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()