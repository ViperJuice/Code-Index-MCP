"""P22 release smoke contract tests."""

from __future__ import annotations

import re
from pathlib import Path

try:
    import tomllib
except ImportError:  # Python <3.11
    import tomli as tomllib


REPO = Path(__file__).resolve().parents[2]
GHCR_IMAGE = "ghcr.io/viperjuice/code-index-mcp"
HELPER_PATHS = (
    "scripts/install-mcp-docker.sh",
    "scripts/install-mcp-docker.ps1",
    "scripts/setup-mcp-json.sh",
    "scripts/setup-mcp-json.ps1",
    "scripts/build-images.sh",
)
IMAGE_CONTRACT_PATHS = (
    ".github/workflows/ci-cd-pipeline.yml",
    ".github/workflows/release-automation.yml",
    ".github/workflows/container-registry.yml",
    "README.md",
    "docker/README.md",
    *HELPER_PATHS,
)


def _read(relative_path: str) -> str:
    return (REPO / relative_path).read_text(encoding="utf-8")


def test_release_smoke_entrypoints_exist():
    script = REPO / "scripts/release_smoke.py"
    assert script.exists(), "scripts/release_smoke.py is required"
    text = script.read_text(encoding="utf-8")
    for mode in ("--wheel", "--stdio", "--container", "--all"):
        assert mode in text
    for contract in ("get_status", "index_unavailable", "safe_fallback", "native_search"):
        assert contract in text
    assert "unregistered_repository" in text

    makefile = _read("Makefile")
    assert re.search(r"^release-smoke:", makefile, re.MULTILINE)
    assert re.search(r"^release-smoke-container:", makefile, re.MULTILINE)
    assert "scripts/release_smoke.py --wheel --stdio" in makefile
    assert "scripts/release_smoke.py --container" in makefile


def test_pyproject_has_console_script_and_build_dependency():
    with (REPO / "pyproject.toml").open("rb") as f:
        data = tomllib.load(f)

    scripts = data["project"]["scripts"]
    assert scripts["mcp-index"] == "mcp_server.cli:cli"

    dev_deps = data["project"]["optional-dependencies"]["dev"]
    assert any(dep.startswith("build>=") for dep in dev_deps)


def test_workflows_reuse_shared_release_smoke_commands():
    workflows = {
        path.name: path.read_text(encoding="utf-8")
        for path in (REPO / ".github/workflows").glob("*.yml")
    }

    assert "make release-smoke" in workflows["ci-cd-pipeline.yml"]
    assert "make release-smoke" in workflows["release-automation.yml"]
    assert "make release-smoke-container" in workflows["container-registry.yml"]
    assert "pip install build wheel" not in workflows["release-automation.yml"]


def test_ghcr_image_name_is_frozen_across_release_surfaces():
    stale_patterns = (
        "ghcr.io/code-index-mcp/mcp-index",
        "IMAGE_NAME: ${{ github.repository }}",
        "DOCKER_IMAGE_NAME: ${{ github.repository }}",
    )
    offenders: dict[str, list[str]] = {}
    missing: list[str] = []

    for relative_path in IMAGE_CONTRACT_PATHS:
        text = _read(relative_path)
        hits = [pattern for pattern in stale_patterns if pattern in text]
        if hits:
            offenders[relative_path] = hits
        if relative_path not in HELPER_PATHS and GHCR_IMAGE not in text:
            missing.append(relative_path)

    assert offenders == {}
    assert missing == []


def test_docs_and_helpers_do_not_reference_retired_image_variants():
    stale = {}
    for relative_path in ("README.md", "docker/README.md", *HELPER_PATHS):
        text = _read(relative_path)
        hits = re.findall(r"mcp-index:(?:minimal|standard)", text)
        if hits:
            stale[relative_path] = hits

    assert stale == {}
