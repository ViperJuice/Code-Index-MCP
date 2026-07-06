"""MCPBASE baseline audit contract."""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).parent.parent.parent
AUDIT = REPO / "docs" / "status" / "MCP_BASELINE_COMPATIBILITY_AUDIT.md"


def test_audit_records_frozen_mcp_baseline_facts():
    text = AUDIT.read_text(encoding="utf-8")

    for expected in (
        "`2025-11-25`",
        "`mcp==1.27.0`",
        "`python -m mcp_server.cli.stdio_runner`",
        "`mcp-index serve`",
        "not the repo's MCP Streamable HTTP transport",
    ):
        assert expected in text


def test_audit_records_stable_tool_names_and_no_argument_calls():
    text = AUDIT.read_text(encoding="utf-8")

    for tool_name in (
        "`symbol_lookup`",
        "`search_code`",
        "`get_status`",
        "`list_plugins`",
        "`reindex`",
        "`write_summaries`",
        "`summarize_sample`",
        "`handshake`",
        "`get_status({})`",
        "`list_plugins({})`",
    ):
        assert tool_name in text


def test_audit_records_downstream_phase_deferrals_only():
    text = AUDIT.read_text(encoding="utf-8")

    for phase in ("`MCPMETA`", "`MCPSTRUCT`", "`MCPTASKS`", "`MCPTRANSPORT`", "`MCPAUTH`"):
        assert phase in text

    assert re.search(r"does not change:", text, re.IGNORECASE)
    assert "`structuredContent`" in text
