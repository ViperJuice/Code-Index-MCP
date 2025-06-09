"""
MCP Server CLI utilities.

This package provides command-line tools for managing the MCP server,
including index management, diagnostics, and maintenance operations.
"""

import click
from .index_management import index


@click.group()
@click.version_option()
def cli():
    """MCP Server CLI utilities."""
    pass


# Register command groups
cli.add_command(index)


if __name__ == '__main__':
    cli()