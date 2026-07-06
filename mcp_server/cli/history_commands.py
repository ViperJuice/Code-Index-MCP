"""CLI commands for metadata-only GitHub issue history ingestion."""

from __future__ import annotations

import json
from pathlib import Path

import click

from mcp_server.indexing.github_issues import (
    GitHubIssueFetchOptions,
    fetch_github_issues,
    normalize_github_issue,
)
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.utils.subprocess_env import get_command_availability


@click.group()
def history() -> None:
    """Manage metadata-only historical issue ingestion."""


@history.command("ingest")
@click.option("--repo", "github_repo", required=True, help="GitHub owner/repo to ingest from.")
@click.option("--label", "labels", multiple=True, help="Repeatable GitHub label allowlist.")
@click.option("--since", help="Inclusive updated-date lower bound (YYYY-MM-DD).")
@click.option("--until", help="Inclusive updated-date upper bound (YYYY-MM-DD).")
@click.option(
    "--state",
    type=click.Choice(["open", "closed", "all"], case_sensitive=False),
    default="all",
    show_default=True,
    help="Issue state filter passed to gh issue list.",
)
@click.option(
    "--include-body-learnings",
    is_flag=True,
    default=False,
    help="Allow body-derived learning extraction without persisting raw issue bodies.",
)
def ingest_history(
    github_repo: str,
    labels: tuple[str, ...],
    since: str | None,
    until: str | None,
    state: str,
    include_body_learnings: bool,
) -> None:
    """Fetch GitHub issues through gh and store metadata-only history documents."""
    availability = get_command_availability("gh")
    options = GitHubIssueFetchOptions(
        repo=github_repo,
        labels=tuple(labels),
        since=since,
        until=until,
        state=state.lower(),
        include_body_learnings=include_body_learnings,
    )

    raw_issues = fetch_github_issues(options)
    normalized_records = [
        normalize_github_issue(
            issue,
            repo=github_repo,
            include_body_learnings=include_body_learnings,
        )
        for issue in raw_issues
    ]

    index_path = Path(".mcp-index") / "current.db"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    store = SQLiteStore(str(index_path))
    repo_root = Path.cwd().resolve()
    repository_id = store.create_repository(str(repo_root), repo_root.name)
    write_summary = store.upsert_history_issue_documents(repository_id, normalized_records)

    click.echo(
        json.dumps(
            {
                "repo": github_repo,
                "filters": {
                    "labels": list(labels),
                    "since": since,
                    "until": until,
                    "state": state.lower(),
                },
                "gh": {
                    "available": availability.available,
                    "resolved_path": availability.resolved_path,
                },
                "include_body_learnings": include_body_learnings,
                "fetched_count": len(raw_issues),
                "stored_count": write_summary["stored"],
                "skipped_count": write_summary["skipped"],
                "storage_surface": ".mcp-index/current.db",
                "redaction_posture": "metadata_only",
            },
            indent=2,
        )
    )
