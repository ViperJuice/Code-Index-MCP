"""GASUPPORT support-tier and docs contract checks."""

from __future__ import annotations

from pathlib import Path

from mcp_server.cli.stdio_runner import _build_tool_list
from mcp_server.plugins.plugin_factory import PluginFactory

REPO = Path(__file__).parent.parent.parent

SUPPORT_MATRIX = REPO / "docs" / "SUPPORT_MATRIX.md"
SECONDARY_TOOL_EVIDENCE = REPO / "docs" / "validation" / "secondary-tool-readiness-evidence.md"

PUBLIC_DOCS = [
    REPO / "README.md",
    REPO / "docs" / "GETTING_STARTED.md",
    REPO / "docs" / "MCP_CONFIGURATION.md",
    REPO / "docs" / "DOCKER_GUIDE.md",
]

ALLOWED_TIERS = {
    "GA-supported",
    "beta",
    "experimental",
    "unsupported",
    "disabled-by-default",
}

FORBIDDEN_PUBLIC_PHRASES = [
    "Works with all 48 supported languages",
    "works with all 48 supported languages",
    "universal language/runtime support",
    "unrestricted multi-worktree",
    "unrestricted multi-branch",
    "indexes every branch",
]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def _parse_table(text: str, header: str) -> list[list[str]]:
    lines = text.splitlines()
    try:
        start = lines.index(header)
    except ValueError as exc:
        raise AssertionError(f"missing table header: {header}") from exc

    rows: list[list[str]] = []
    for line in lines[start + 2 :]:
        if not line.startswith("|"):
            break
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        rows.append(cells)
    return rows


def test_support_matrix_assigns_exactly_one_supported_tier_to_every_language_and_surface():
    text = _read(SUPPORT_MATRIX)

    language_rows = _parse_table(
        text,
        "| Language | Support tier | Runtime behavior | Parser status | Sandbox support | Required extras | Symbol quality | Semantic support | Known limitations |",
    )
    surface_rows = _parse_table(
        text,
        "| Surface | Support tier | Default posture | Evidence basis | Notes |",
    )

    assert language_rows, "language support table must not be empty"
    assert surface_rows, "surface support table must not be empty"
    expected_doc_languages = set(PluginFactory.get_supported_languages()) - {"csharp"}
    assert len(language_rows) == len(expected_doc_languages)

    for row in language_rows:
        assert row[1] in ALLOWED_TIERS, row

    for row in surface_rows:
        assert row[1] in ALLOWED_TIERS, row


def test_support_matrix_grounds_language_claims_in_machine_checkable_plugin_facts():
    rows = PluginFactory.get_plugin_availability()
    assert rows
    assert all("availability_basis" in row and "activation_mode" in row for row in rows)
    assert any(
        row["state"] == "unsupported"
        and row["sandbox_supported"] is False
        and row["activation_mode"] == "disabled_by_default"
        for row in rows
    )
    assert any(
        row["state"] == "missing_extra"
        and row["availability_basis"] == "specific_plugin"
        and row["activation_mode"] == "extra_required"
        for row in rows
    )

    text = _normalized(SUPPORT_MATRIX)
    for expected in (
        "plugin_availability",
        "availability_basis",
        "activation_mode",
        "specific_plugin",
        "registry-only",
        "sandbox_supported",
        "required_extras",
    ):
        assert expected in text


def test_public_docs_route_support_claims_to_matrix_and_checklist_without_blanket_language():
    failures = []
    for path in PUBLIC_DOCS:
        text = _read(path)
        lowered = text.lower()

        if "SUPPORT_MATRIX.md" not in text:
            failures.append(f"{path.relative_to(REPO)} missing support matrix reference")
        if "ga-readiness-checklist" not in lowered:
            failures.append(f"{path.relative_to(REPO)} missing GA checklist reference")
        if "stdio" not in lowered:
            failures.append(f"{path.relative_to(REPO)} missing STDIO posture")
        if "fastapi" not in lowered:
            failures.append(f"{path.relative_to(REPO)} missing FastAPI posture")
        for phrase in FORBIDDEN_PUBLIC_PHRASES:
            if phrase in text:
                failures.append(f"{path.relative_to(REPO)} contains forbidden phrase {phrase!r}")

    assert failures == []


def test_secondary_tool_readiness_evidence_stays_evidence_only():
    text = _normalized(SUPPORT_MATRIX)
    assert SECONDARY_TOOL_EVIDENCE.exists()
    assert "secondary-tool-readiness-evidence.md" in text
    assert "readiness evidence" in text
    assert "support expansion" in text


def test_list_plugins_surface_exposes_support_fact_wording():
    tool = {tool.name: tool for tool in _build_tool_list()}["list_plugins"]
    for expected in ("machine-readable", "specific-plugin", "registry-only", "activation"):
        assert expected in tool.description
