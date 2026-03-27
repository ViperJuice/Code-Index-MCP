"""CLI commands for semantic onboarding and setup."""

from __future__ import annotations

import json
from typing import Optional

import click

from mcp_server.config.settings import reload_settings
from mcp_server.setup.qdrant_autostart import ensure_qdrant_running
from mcp_server.setup.semantic_preflight import run_semantic_preflight


@click.group()
def setup():
    """Setup and onboarding commands."""


@setup.command("semantic")
@click.option(
    "--autostart-qdrant/--no-autostart-qdrant",
    default=True,
    show_default=True,
    help="Automatically start local Qdrant via Docker when unreachable.",
)
@click.option(
    "--strict/--no-strict",
    default=None,
    help="Override strict semantic readiness behavior for this run.",
)
@click.option("--qdrant-url", default=None, help="Override Qdrant URL (http://host:6333).")
@click.option(
    "--openai-api-base",
    default=None,
    help="Override OpenAI-compatible embeddings base URL.",
)
@click.option("--profile", default=None, help="Target semantic profile ID for validation.")
@click.option("--timeout", default=None, type=float, help="Preflight timeout in seconds.")
@click.option("--dry-run", is_flag=True, help="Run checks without starting containers.")
@click.option("--json", "json_output", is_flag=True, help="Emit JSON output.")
def setup_semantic(
    autostart_qdrant: bool,
    strict: Optional[bool],
    qdrant_url: Optional[str],
    openai_api_base: Optional[str],
    profile: Optional[str],
    timeout: Optional[float],
    dry_run: bool,
    json_output: bool,
):
    """Validate semantic setup and bootstrap local Qdrant.

    Examples:
    - `python scripts/cli/mcp_cli.py setup semantic`
    - `python scripts/cli/mcp_cli.py setup semantic --openai-api-base http://127.0.0.1:8001/v1`
    - `python scripts/cli/mcp_cli.py setup semantic --strict --json`
    """
    settings = reload_settings()

    if qdrant_url:
        if "://" in qdrant_url:
            host_port = qdrant_url.split("://", 1)[1]
        else:
            host_port = qdrant_url
        if ":" in host_port:
            host, port = host_port.rsplit(":", 1)
            settings.qdrant_host = host
            try:
                settings.qdrant_port = int(port)
            except ValueError:
                raise click.ClickException(f"Invalid --qdrant-url port: {port}")

    if openai_api_base:
        settings.openai_api_base = openai_api_base

    if strict is None:
        strict = settings.semantic_strict_mode

    settings.semantic_autostart_qdrant = autostart_qdrant

    report = run_semantic_preflight(
        settings=settings,
        profile=profile,
        strict=bool(strict),
        timeout_s=timeout,
    )

    qdrant_start = None
    if (
        autostart_qdrant
        and not dry_run
        and report.qdrant.status.value != "ready"
        and settings.semantic_search_enabled
    ):
        qdrant_start = ensure_qdrant_running(settings)
        report = run_semantic_preflight(
            settings=settings,
            profile=profile,
            strict=bool(strict),
            timeout_s=timeout,
        )

    output_payload = report.to_dict()
    if qdrant_start is not None:
        output_payload["qdrant_autostart"] = qdrant_start.to_dict()

    if json_output:
        click.echo(json.dumps(output_payload, indent=2))
    else:
        click.echo("Semantic Setup Report")
        click.echo("=" * 22)
        click.echo(f"Overall ready: {'yes' if report.overall_ready else 'no'}")
        click.echo(f"Strict mode: {'on' if report.strict_mode else 'off'}")
        click.echo(f"Profile check: {report.profiles.status.value} ({report.profiles.message})")
        click.echo(f"Embedding check: {report.embedding.status.value} ({report.embedding.message})")
        click.echo(f"Qdrant check: {report.qdrant.status.value} ({report.qdrant.message})")

        if qdrant_start is not None:
            click.echo(f"Qdrant autostart: {qdrant_start.message}")

        if report.warnings:
            click.echo("Warnings:")
            for warning in report.warnings:
                click.echo(f"- {warning}")

        if not report.overall_ready:
            click.echo("Next steps:")
            click.echo("- Verify OPENAI_API_BASE or VOYAGE_API_KEY for the selected profile")
            click.echo("- Ensure QDRANT_URL is reachable or rerun setup with autostart enabled")

    if strict and not report.overall_ready:
        raise click.ClickException("Strict semantic setup failed")
