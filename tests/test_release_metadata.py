"""Release metadata assertions for the prepared stable v1.2.0 contract.

Historical GARC soak target: v1.2.0-rc6.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

try:
    import tomllib
except ImportError:  # Python <3.11
    import tomli as tomllib


REPO = Path(__file__).parent.parent
EXPECTED_VERSION = "1.2.0"
EXPECTED_TAG = "v1.2.0"
GA_RC_EVIDENCE = REPO / "docs" / "validation" / "ga-rc-evidence.md"
DOCKER_INSTALLERS = (
    "scripts/install-mcp-docker.sh",
    "scripts/install-mcp-docker.ps1",
)


def _read_text(relative_path: str) -> str:
    return (REPO / relative_path).read_text()


def test_runtime_version_matches_stable_contract():
    import mcp_server

    assert mcp_server.__version__ == EXPECTED_VERSION, (
        f"mcp_server.__version__ is {mcp_server.__version__!r}, " f"expected {EXPECTED_VERSION!r}"
    )


def test_pyproject_version_matches_stable_contract():
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


def test_readme_distribution_identity_remains_stable():
    readme = _read_text("README.md")

    assert "**Python distribution**: `index-it-mcp`" in readme
    assert "**Container image**: `ghcr.io/viperjuice/code-index-mcp`" in readme


def test_changelog_has_stable_contract_section():
    changelog = _read_text("CHANGELOG.md")

    assert f"## [{EXPECTED_VERSION}] — 2026-04-25" in changelog


def test_release_workflow_matches_rc_contract():
    workflow = _read_text(".github/workflows/release-automation.yml")

    assert f"Version to release (e.g., {EXPECTED_TAG})" in workflow
    assert f"default: '{EXPECTED_TAG}'" in workflow
    assert "default: 'custom'" in workflow
    assert f"GAREL stable release contract target: {EXPECTED_TAG}" in workflow
    assert (
        'gh workflow run "Release Automation" -f version=v1.2.0 -f release_type=custom -f auto_merge=false'
        in workflow
    )
    assert "peter-evans/create-pull-request@v8" in workflow
    assert "softprops/action-gh-release@v3" in workflow
    assert "peter-evans/create-pull-request@v7" not in workflow
    assert "softprops/action-gh-release@v2" not in workflow
    assert 'grep -q "version = \\"$VERSION_NO_V\\"" pyproject.toml' in workflow
    assert 'grep -q "__version__ = \\"$VERSION_NO_V\\"" mcp_server/__init__.py' in workflow
    assert "Stable tags still use release_type=custom" in workflow
    assert "prerelease: ${{ needs.prepare-release.outputs.is_prerelease }}" in workflow
    assert "tags: ${{ needs.prepare-release.outputs.docker_tags }}" in workflow
    assert "No automatic documentation rewrite" in workflow
    assert 'sed -i "s/Latest Version:' not in workflow


def test_release_tag_is_not_reused_locally():
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
    if tag_commit == head:
        return

    evidence = GA_RC_EVIDENCE.read_text(encoding="utf-8")
    assert EXPECTED_TAG in evidence or "v1.2.0-rc8" in evidence
    assert tag_commit in evidence, f"{EXPECTED_TAG} exists but points at undocumented {tag_commit}"


def test_installers_and_download_helper_match_stable_identity_contract():
    for relative_path in DOCKER_INSTALLERS:
        text = _read_text(relative_path)
        assert EXPECTED_TAG in text
        assert "local-smoke" in text
        assert "ghcr.io/viperjuice/code-index-mcp" in text
        assert "latest" in text

    shell = _read_text("scripts/install-mcp-docker.sh")
    powershell = _read_text("scripts/install-mcp-docker.ps1")
    download_helper = _read_text("scripts/download-release.py")

    assert 'MCP_VARIANT="${MCP_VARIANT:-v1.2.0}"' in shell
    assert 'param(\n    [string]$Variant = "v1.2.0"' in powershell
    assert 'IF "%MCP_VARIANT%"=="" SET MCP_VARIANT=v1.2.0' in powershell

    for expected in (
        "index_it_mcp-",
        "asset_kind",
        "wheel",
        "sdist",
        "CHANGELOG",
        "sbom",
        "ViperJuice/Code-Index-MCP",
    ):
        assert expected in download_helper
