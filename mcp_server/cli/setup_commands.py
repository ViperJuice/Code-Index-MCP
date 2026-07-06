"""CLI commands for semantic onboarding and setup."""

from __future__ import annotations

import json
from typing import Optional

import click

from mcp_server.config.settings import reload_settings
from mcp_server.setup.qdrant_autostart import ensure_qdrant_running
from mcp_server.setup.semantic_preflight import (
    bootstrap_active_profile_collection,
    run_semantic_preflight,
    summarize_collection_bootstrap,
)


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

    collection_bootstrap = summarize_collection_bootstrap(report.to_dict(), dry_run=dry_run)
    if (
        not dry_run
        and collection_bootstrap.status == "blocked"
        and report.blocker is not None
        and report.blocker.code == "collection_missing"
    ):
        collection_bootstrap = bootstrap_active_profile_collection(
            settings=settings,
            profile=profile,
            timeout_s=timeout,
        )
        report = run_semantic_preflight(
            settings=settings,
            profile=profile,
            strict=bool(strict),
            timeout_s=timeout,
        )
        if collection_bootstrap.status == "reused" and report.can_write_semantic_vectors:
            collection_bootstrap = summarize_collection_bootstrap(report.to_dict(), dry_run=False)

    output_payload = report.to_dict()
    if qdrant_start is not None:
        output_payload["qdrant_autostart"] = qdrant_start.to_dict()
    output_payload["collection_bootstrap"] = collection_bootstrap.to_dict()

    if json_output:
        click.echo(json.dumps(output_payload, indent=2))
    else:
        click.echo("Semantic Setup Report")
        click.echo("=" * 22)
        click.echo(f"Overall ready: {'yes' if report.overall_ready else 'no'}")
        click.echo(
            "Can write semantic vectors: "
            + ("yes" if report.can_write_semantic_vectors else "no")
        )
        click.echo(f"Strict mode: {'on' if report.strict_mode else 'off'}")
        click.echo(f"Profile check: {report.profiles.status.value} ({report.profiles.message})")
        click.echo(
            f"Enrichment smoke: {report.enrichment.status.value} ({report.enrichment.message})"
        )
        click.echo(f"Embedding check: {report.embedding.status.value} ({report.embedding.message})")
        click.echo(f"Qdrant check: {report.qdrant.status.value} ({report.qdrant.message})")
        click.echo(
            f"Collection check: {report.collection.status.value} ({report.collection.message})"
        )
        click.echo(
            "Collection bootstrap: "
            f"{collection_bootstrap.status} ({collection_bootstrap.message})"
        )

        if qdrant_start is not None:
            click.echo(f"Qdrant autostart: {qdrant_start.message}")

        if report.warnings:
            click.echo("Warnings:")
            for warning in report.warnings:
                click.echo(f"- {warning}")

        if report.blocker is not None:
            click.echo("Semantic write blocker:")
            click.echo(f"- Code: {report.blocker.code}")
            click.echo(f"- Reason: {report.blocker.message}")
            if report.blocker.remediation:
                click.echo("- Remediation:")
                for item in report.blocker.remediation:
                    click.echo(f"  - {item}")

        if not report.can_write_semantic_vectors:
            click.echo("Next steps:")
            click.echo(
                "- Verify the selected profile's enrichment and embedding endpoints, models, and API-key env vars"
            )
            click.echo(
                "- Ensure QDRANT_URL is reachable and the expected collection shape matches the active profile"
            )

    if strict and not report.can_write_semantic_vectors:
        raise click.ClickException("Strict semantic setup failed")
