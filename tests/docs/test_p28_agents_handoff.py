"""P28 AGENTS readiness handoff checks."""

from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
AGENTS_MD = REPO_ROOT / "AGENTS.md"


def _text() -> str:
    return AGENTS_MD.read_text(encoding="utf-8")


def test_agents_mcp_strategy_names_readiness_contract():
    text = _text()
    for expected in ("ready", "index_unavailable", "safe_fallback", "native_search", "reindex"):
        assert expected in text


def test_agents_removes_unconditional_search_language():
    text = _text()
    forbidden = (
        "ALWAYS USE MCP TOOLS FIRST",
        "Fall back to Grep ONLY if this returns 0 results",
        "Fall back to Grep ONLY if this returns not_found",
        "[USE BEFORE GREP]",
    )
    for phrase in forbidden:
        assert phrase not in text
