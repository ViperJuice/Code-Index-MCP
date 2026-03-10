"""CLI preflight checks for safe MCP usage."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import List, Optional

import click

from .artifact_commands import (
    _get_artifact_identity,
    _get_git_ref_info,
    _get_local_drift,
    _verify_local_index_restored,
)


@dataclass
class PreflightCheck:
    level: str
    message: str
    command: Optional[str] = None


@dataclass
class PreflightResult:
    status: str
    checks: List[PreflightCheck]


def _get_upstream_ref() -> Optional[str]:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except Exception:
        return None


def _get_ahead_behind(upstream_ref: str) -> tuple[int, int]:
    try:
        result = subprocess.run(
            ["git", "rev-list", "--left-right", "--count", f"HEAD...{upstream_ref}"],
            capture_output=True,
            text=True,
            check=True,
        )
        ahead_str, behind_str = result.stdout.strip().split()
        return int(ahead_str), int(behind_str)
    except Exception:
        return 0, 0


def run_preflight() -> PreflightResult:
    checks: List[PreflightCheck] = []
    git_info = _get_git_ref_info()
    artifact_identity = _get_artifact_identity()

    if not git_info.get("head"):
        checks.append(
            PreflightCheck(
                level="warning",
                message="Not inside a git repository or git metadata is unavailable.",
            )
        )
        return PreflightResult(status="warning", checks=checks)

    upstream_ref = _get_upstream_ref()
    if upstream_ref:
        ahead, behind = _get_ahead_behind(upstream_ref)
        if behind > 0:
            checks.append(
                PreflightCheck(
                    level="warning",
                    message=f"Current branch is behind {upstream_ref} by {behind} commit(s).",
                    command="git pull --rebase",
                )
            )
        elif ahead > 0:
            checks.append(
                PreflightCheck(
                    level="info",
                    message=f"Current branch is ahead of {upstream_ref} by {ahead} commit(s).",
                )
            )
    else:
        checks.append(
            PreflightCheck(
                level="info",
                message="No upstream remote is configured for the current branch.",
            )
        )

    if not _verify_local_index_restored():
        checks.append(
            PreflightCheck(
                level="warning",
                message="Local runtime index files are missing.",
                command="mcp-index artifact pull --latest",
            )
        )
    else:
        artifact_commit = artifact_identity.get("commit")
        head = git_info.get("head")
        if artifact_commit and head and artifact_commit != head:
            checks.append(
                PreflightCheck(
                    level="warning",
                    message="Restored artifact commit differs from local HEAD.",
                    command="mcp-index artifact sync",
                )
            )
        detector, changes = _get_local_drift()
        if changes:
            mode = (
                "incremental reconcile"
                if detector.should_use_incremental(changes)
                else "rebuild"
            )
            checks.append(
                PreflightCheck(
                    level="warning",
                    message=f"Local runtime index has drift relative to the working tree ({len(changes)} change(s)).",
                    command=(
                        "mcp-index artifact sync"
                        if mode == "incremental reconcile"
                        else "mcp-index index rebuild --force"
                    ),
                )
            )

    status = "ready"
    if any(check.level == "warning" for check in checks):
        status = "warning"
    return PreflightResult(status=status, checks=checks)


def format_preflight_report(result: PreflightResult) -> List[str]:
    if not result.checks:
        return [
            "✅ Preflight ready: repo, artifact baseline, and local runtime state look current."
        ]

    lines = [f"Preflight status: {result.status}"]
    for check in result.checks:
        prefix = {"info": "ℹ️", "warning": "⚠️", "error": "❌"}.get(check.level, "-")
        lines.append(f"{prefix} {check.message}")
        if check.command:
            lines.append(f"   Next: {check.command}")
    return lines


def run_startup_preflight() -> PreflightResult:
    return run_preflight()


@click.command("preflight")
def preflight() -> None:
    """Check repository and artifact readiness before starting MCP."""
    for line in format_preflight_report(run_preflight()):
        click.echo(line)
