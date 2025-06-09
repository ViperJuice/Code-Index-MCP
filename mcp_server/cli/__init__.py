"""
MCP Server CLI utilities.

This package provides command-line tools for managing the MCP server,
including index management, diagnostics, and maintenance operations.
"""

import click
from .index_management import index
from .artifact_commands import artifact


@click.group()
@click.version_option()
def cli():
    """MCP Server CLI utilities."""
    pass


# Register command groups
cli.add_command(index)
cli.add_command(artifact)


if __name__ == '__main__':
    cli()