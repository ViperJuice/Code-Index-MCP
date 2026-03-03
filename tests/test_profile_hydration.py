"""Tests for lexical-first semantic profile hydration coordination."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from mcp_server.artifacts.profile_hydration import (
    HydrationState,
    ProfileHydrationCoordinator,
)
from mcp_server.utils.index_discovery import IndexDiscovery


def _create_minimal_index(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("CREATE TABLE files (id INTEGER PRIMARY KEY, path TEXT)")
        conn.execute("CREATE TABLE symbols (id INTEGER PRIMARY KEY, name TEXT)")
        conn.execute("CREATE TABLE repositories (id INTEGER PRIMARY KEY, path TEXT)")
        conn.commit()
    finally:
        conn.close()


def test_hydration_defaults_to_lexical_first_even_when_semantic_available() -> None:
    coordinator = ProfileHydrationCoordinator()

    report = coordinator.evaluate(
        requested_profiles={"legacy-default": "abc123"},
        discovered_profiles={"legacy-default": "abc123"},
        lexical_available=True,
    )

    assert report.fallback_strategy.value == "lexical_only"
    assert report.profiles["legacy-default"].status is HydrationState.AVAILABLE


def test_missing_profile_is_non_fatal_with_lexical_fallback() -> None:
    coordinator = ProfileHydrationCoordinator()

    report = coordinator.evaluate(
        requested_profiles={"commercial-high": "deadbeef"},
        discovered_profiles={},
        lexical_available=True,
    )

    assert report.lexical_available is True
    assert report.fallback_strategy.value == "lexical_only"
    assert report.profiles["commercial-high"].status is HydrationState.MISSING


def test_incompatible_profile_is_flagged() -> None:
    coordinator = ProfileHydrationCoordinator()

    report = coordinator.evaluate(
        requested_profiles={"commercial-high": "expected"},
        discovered_profiles={"commercial-high": "actual"},
        lexical_available=True,
    )

    assert report.profiles["commercial-high"].status is HydrationState.INCOMPATIBLE
    assert (
        report.profiles["commercial-high"].reason
        == "compatibility fingerprint mismatch"
    )


def test_index_discovery_exposes_profile_hydration_from_metadata(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "repo"
    workspace.mkdir(parents=True)
    (workspace / ".mcp-index.json").write_text(
        json.dumps({"enabled": True}), encoding="utf-8"
    )

    db_path = workspace / ".mcp-index" / "code_index.db"
    _create_minimal_index(db_path)

    metadata = {
        "branch": "main",
        "commit": "0123456789abcdef",
        "semantic_profile": "legacy-default",
        "compatibility_fingerprint": "abc123",
    }
    (workspace / ".mcp-index" / ".index_metadata.json").write_text(
        json.dumps(metadata),
        encoding="utf-8",
    )

    discovery = IndexDiscovery(workspace)
    hydration = discovery.get_profile_hydration_status(
        requested_profiles={"legacy-default": "abc123"}
    )

    assert hydration["lexical_available"] is True
    assert hydration["branch"] == "main"
    assert hydration["commit"] == "0123456789abcdef"
    assert hydration["profiles"]["legacy-default"]["status"] == "available"
