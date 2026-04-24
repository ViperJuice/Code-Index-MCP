"""P23 customer documentation truth checks."""

from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent

SUPPORT_MATRIX = REPO_ROOT / "docs" / "SUPPORT_MATRIX.md"
ACTIVE_DOCS = [
    REPO_ROOT / "README.md",
    REPO_ROOT / "docs" / "GETTING_STARTED.md",
    REPO_ROOT / "docs" / "DOCKER_GUIDE.md",
    REPO_ROOT / "docs" / "MCP_CONFIGURATION.md",
    REPO_ROOT / "docs" / "operations" / "deployment-runbook.md",
    REPO_ROOT / "docs" / "security" / "attestation.md",
    REPO_ROOT / "docs" / "security" / "path-guard.md",
    REPO_ROOT / "docs" / "security" / "sandbox.md",
    REPO_ROOT / "docs" / "security" / "token-scopes.md",
]
AGENT_DOCS = [
    REPO_ROOT / "AGENTS.md",
    REPO_ROOT / "CLAUDE.md",
    REPO_ROOT / "mcp_server" / "AGENTS.md",
]
DOCKER_DOCS = [
    REPO_ROOT / "README.md",
    REPO_ROOT / "docs" / "DOCKER_GUIDE.md",
    REPO_ROOT / "docs" / "MCP_CONFIGURATION.md",
    REPO_ROOT / "docs" / "operations" / "deployment-runbook.md",
]

REQUIRED_SUPPORT_COLUMNS = [
    "Language",
    "Support tier",
    "Runtime behavior",
    "Parser status",
    "Sandbox support",
    "Required extras",
    "Symbol quality",
    "Semantic support",
    "Known limitations",
]

REQUIRED_SURFACE_COLUMNS = [
    "Surface",
    "Support tier",
    "Default posture",
    "Evidence basis",
    "Notes",
]

STALE_STRINGS = [
    "1." + "0.0",
    "1." + "1.0",
    "v1.2.0-" + "rc2",
    "requirements" + ".txt",
    "pip install " + "-r",
    "Production" + "-Ready",
    "fully " + "operational",
    "48-" + "Language Support",
    "complete tree-sitter " + "integration",
]
STALE_IMAGES = [
    "ghcr.io/code-index-mcp/" + "mcp-index",
    "mcp-index:" + "minimal",
    "mcp-index:" + "standard",
    "mcp-index:" + "full",
]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_support_matrix_exists_with_required_columns_once():
    assert SUPPORT_MATRIX.exists(), "docs/SUPPORT_MATRIX.md must exist"
    text = _read(SUPPORT_MATRIX)
    language_header = "| " + " | ".join(REQUIRED_SUPPORT_COLUMNS) + " |"
    surface_header = "| " + " | ".join(REQUIRED_SURFACE_COLUMNS) + " |"
    assert (
        text.count(language_header) == 1
    ), "support matrix must contain one canonical language table"
    assert (
        text.count(surface_header) == 1
    ), "support matrix must contain one canonical surface table"


def test_active_docs_do_not_contain_stale_strings():
    failures = []
    for path in ACTIVE_DOCS + AGENT_DOCS:
        text = _read(path)
        for stale in STALE_STRINGS:
            if stale in text:
                failures.append(f"{path.relative_to(REPO_ROOT)}: {stale}")
    assert failures == []


def test_docker_docs_use_current_image_package_only():
    failures = []
    for path in DOCKER_DOCS:
        text = _read(path)
        for stale in STALE_IMAGES:
            if stale in text:
                failures.append(f"{path.relative_to(REPO_ROOT)}: {stale}")
    assert failures == []
    for path in DOCKER_DOCS:
        assert "ghcr.io/viperjuice/code-index-mcp" in _read(path)


def test_active_release_docs_name_rc6_and_alpha_or_beta_status():
    for path in ACTIVE_DOCS:
        text = _read(path).lower()
        assert "1.2.0-rc6" in text, f"{path.relative_to(REPO_ROOT)} missing 1.2.0-rc6"
        assert ("alpha" in text) or (
            "beta" in text
        ), f"{path.relative_to(REPO_ROOT)} missing alpha/beta status language"


def test_active_docs_link_to_support_matrix_for_language_claims():
    for path in [REPO_ROOT / "README.md", REPO_ROOT / "docs" / "GETTING_STARTED.md"]:
        text = _read(path)
        assert "docs/SUPPORT_MATRIX.md" in text or "SUPPORT_MATRIX.md" in text


def test_agent_docs_point_to_support_matrix_and_current_install_path():
    for path in AGENT_DOCS:
        text = _read(path)
        assert "SUPPORT_MATRIX.md" in text, f"{path.relative_to(REPO_ROOT)} missing support matrix"
        assert "uv sync --locked" in text, f"{path.relative_to(REPO_ROOT)} missing uv sync --locked"


def test_markdown_index_routes_current_support_docs():
    text = _read(REPO_ROOT / "docs" / "MARKDOWN_INDEX.md")
    assert "SUPPORT_MATRIX.md" in text
    assert "HISTORICAL-ARTIFACTS-TRIAGE.md" in text
