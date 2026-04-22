"""Release metadata assertions for the active v1.2.0-rc4 contract."""

from __future__ import annotations

import subprocess
from pathlib import Path

try:
    import tomllib
except ImportError:  # Python <3.11
    import tomli as tomllib


REPO = Path(__file__).parent.parent
EXPECTED_VERSION = "1.2.0-rc4"
EXPECTED_TAG = "v1.2.0-rc4"


def _read_text(relative_path: str) -> str:
    return (REPO / relative_path).read_text()


def test_runtime_version_matches_rc_contract():
    import mcp_server

    assert mcp_server.__version__ == EXPECTED_VERSION, (
        f"mcp_server.__version__ is {mcp_server.__version__!r}, " f"expected {EXPECTED_VERSION!r}"
    )


def test_pyproject_version_matches_rc_contract():
    with (REPO / "pyproject.toml").open("rb") as f:
        data = tomllib.load(f)

    assert data["project"]["version"] == EXPECTED_VERSION


def test_python_distribution_identity_is_frozen():
    with (REPO / "pyproject.toml").open("rb") as f:
        data = tomllib.load(f)

    assert data["project"]["name"] == "index-it-mcp"
    assert data["project"]["scripts"]["mcp-index"] == "mcp_server.cli:cli"
    assert data["project"]["scripts"]["code-index-mcp"] == "mcp_server.cli:cli"
    assert data["project"]["scripts"]["index-it-mcp"] == "mcp_server.cli:cli"


def test_readme_status_matches_rc_contract():
    readme = _read_text("README.md")

    assert f"**Version**: {EXPECTED_VERSION} (beta)" in readme
    assert "**Python distribution**: `index-it-mcp`" in readme
    assert "**Container image**: `ghcr.io/viperjuice/code-index-mcp`" in readme


def test_changelog_has_rc_contract_section():
    changelog = _read_text("CHANGELOG.md")

    assert f"## [{EXPECTED_VERSION}] — 2026-04-22" in changelog


def test_release_workflow_matches_rc_contract():
    workflow = _read_text(".github/workflows/release-automation.yml")

    assert f"Version to release (e.g., {EXPECTED_TAG})" in workflow
    assert f"default: '{EXPECTED_TAG}'" in workflow
    assert "default: 'custom'" in workflow
    assert f"P21 release contract target: {EXPECTED_TAG}" in workflow
    assert 'grep -q "version = \\"$VERSION_NO_V\\"" pyproject.toml' in workflow
    assert 'grep -q "__version__ = \\"$VERSION_NO_V\\"" mcp_server/__init__.py' in workflow
    assert "Prerelease tags must use release_type=custom" in workflow
    assert "prerelease: ${{ needs.prepare-release.outputs.is_prerelease }}" in workflow
    assert "tags: ${{ needs.prepare-release.outputs.docker_tags }}" in workflow
    assert "No automatic documentation rewrite" in workflow
    assert 'sed -i "s/Latest Version:' not in workflow


def test_release_candidate_tag_is_not_reused_locally():
    result = subprocess.run(
        ["git", "tag", "-l", EXPECTED_TAG],
        capture_output=True,
        text=True,
        check=True,
    )
    if not result.stdout.strip():
        return

    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    tag_commit = subprocess.run(
        ["git", "rev-parse", f"{EXPECTED_TAG}^{{commit}}"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert tag_commit == head, f"{EXPECTED_TAG} exists but points at {tag_commit}, not HEAD"
