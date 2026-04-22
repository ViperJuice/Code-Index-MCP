"""Retention policy layer — reads env vars and delegates to the provider."""

from __future__ import annotations

import os
from typing import Optional

from mcp_server.artifacts.providers.github_actions import ReleaseRef, delete_releases_older_than


def _env_int(name: str) -> Optional[int]:
    val = os.environ.get(name)
    if val is None:
        return None
    try:
        return int(val)
    except ValueError:
        return None


def prune_releases(
    repo: str,
    *,
    older_than_days: Optional[int] = None,
    keep_latest_n: Optional[int] = None,
    dry_run: bool = False,
) -> list[ReleaseRef]:
    """Apply retention policy, falling back to env-var defaults."""
    effective_days = (
        older_than_days if older_than_days is not None else _env_int("MCP_ARTIFACT_RETENTION_DAYS")
    )
    effective_count = (
        keep_latest_n if keep_latest_n is not None else _env_int("MCP_ARTIFACT_RETENTION_COUNT")
    )
    return delete_releases_older_than(
        repo,
        older_than_days=effective_days,
        keep_latest_n=effective_count,
        dry_run=dry_run,
    )
