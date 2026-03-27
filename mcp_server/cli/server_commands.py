"""Server startup CLI commands."""

from __future__ import annotations

import os

import click


def _default_host() -> str:
    return os.getenv("MCP_SERVER_HOST", "127.0.0.1")


def _default_port() -> int:
    try:
        return int(os.getenv("MCP_SERVER_PORT", "8765"))
    except ValueError:
        return 8765


@click.command("serve")
@click.option("--host", default=_default_host, show_default="env MCP_SERVER_HOST or 127.0.0.1")
@click.option(
    "--port",
    default=_default_port,
    type=int,
    show_default="env MCP_SERVER_PORT or 8765",
)
@click.option("--reload", is_flag=True, help="Enable auto-reload for development")
def serve(host: str, port: int, reload: bool) -> None:
    """Start the MCP HTTP server with configurable host and port."""
    import uvicorn
    from pathlib import Path

    os.environ.setdefault("MCP_INDEX_STORAGE_PATH", str(Path.home() / ".mcp" / "indexes"))
    os.environ.setdefault("MCP_SKIP_PLUGIN_PREINDEX", "true")

    click.echo(f"Starting MCP server on http://{host}:{port}")
    uvicorn.run("mcp_server.gateway:app", host=host, port=port, reload=reload)
