"""P28 slash-command readiness handoff checks."""

from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
COMMANDS = [
    REPO_ROOT / ".claude" / "commands" / "mcp-tools.md",
    REPO_ROOT / ".claude" / "commands" / "search-code.md",
    REPO_ROOT / ".claude" / "commands" / "find-symbol.md",
    REPO_ROOT / ".claude" / "commands" / "verify-mcp.md",
]


def _combined_text() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in COMMANDS)


def test_command_docs_name_readiness_fallback_contract():
    text = _combined_text()
    for expected in ("ready", "index_unavailable", "safe_fallback", "native_search"):
        assert expected in text


def test_each_command_doc_mentions_ready_or_index_unavailable():
    for path in COMMANDS:
        text = path.read_text(encoding="utf-8")
        assert ("ready" in text) or ("index_unavailable" in text), path


def test_command_docs_remove_unconditional_mcp_first_language():
    text = _combined_text()
    forbidden = (
        "Never use grep",
        "MCP-First: Enabled",
        "Fall back to Grep ONLY",
    )
    for phrase in forbidden:
        assert phrase not in text
