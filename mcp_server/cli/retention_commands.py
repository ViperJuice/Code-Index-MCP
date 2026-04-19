"""CLI commands for release retention / pruning."""

from __future__ import annotations

from typing import Optional

import click

from mcp_server.artifacts.retention import prune_releases


@click.group()
def retention():
    """Manage release retention for index artifact releases."""


@retention.command("prune")
@click.option("--repo", required=True, envvar="MCP_ARTIFACT_REPO", help="GitHub repo (owner/repo)")
@click.option(
    "--older-than-days",
    type=int,
    default=None,
    envvar="MCP_ARTIFACT_RETENTION_DAYS",
    help="Delete releases older than N days",
)
@click.option(
    "--keep-latest-n",
    type=int,
    default=None,
    envvar="MCP_ARTIFACT_RETENTION_COUNT",
    help="Keep the N most recent releases regardless of age",
)
@click.option("--dry-run", is_flag=True, help="List candidates without deleting")
def prune(
    repo: str,
    older_than_days: Optional[int],
    keep_latest_n: Optional[int],
    dry_run: bool,
) -> None:
    """Prune old releases according to retention policy."""
    if older_than_days is None and keep_latest_n is None:
        click.echo(
            "No retention criteria specified. Use --older-than-days and/or --keep-latest-n.",
            err=True,
        )
        raise click.Abort()

    label = "Candidates" if dry_run else "Deleted"
    try:
        refs = prune_releases(
            repo,
            older_than_days=older_than_days,
            keep_latest_n=keep_latest_n,
            dry_run=dry_run,
        )
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        raise click.Abort()

    if not refs:
        click.echo(f"{label}: none")
        return

    click.echo(f"{label} ({len(refs)}):")
    for ref in refs:
        click.echo(f"  {ref.tag_name}  created={ref.created_at}")
