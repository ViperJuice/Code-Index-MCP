from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DECISION = REPO / "docs" / "validation" / "mcp-transport-decision.md"


def _compact(text: str) -> str:
    return " ".join(text.split())


def test_decision_record_freezes_v8_stdio_only_transport_position():
    text = _compact(DECISION.read_text(encoding="utf-8"))

    for expected in (
        "Remote MCP transport is deferred in v8.",
        "`mcp-index stdio`",
        "`mcp-index serve`",
        "admin/debug HTTP surface",
        "not this repository's MCP Streamable HTTP transport",
    ):
        assert expected in text


def test_decision_record_lists_future_remote_transport_prerequisites():
    text = _compact(DECISION.read_text(encoding="utf-8"))

    for expected in (
        "distinct Streamable HTTP endpoint",
        "separate routing and lifecycle",
        "transport-specific tests",
        "client smokes",
        "`MCPAUTH`",
        'no remote MCP auth is implemented',
    ):
        assert expected in text
