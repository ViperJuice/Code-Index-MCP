"""P28 STDIO readiness handoff tests."""

from __future__ import annotations

from mcp_server.cli.stdio_runner import _SERVER_INSTRUCTIONS, _build_tool_list


def _tools_by_name():
    return {tool.name: tool for tool in _build_tool_list()}


def test_server_instructions_are_readiness_gated():
    text = _SERVER_INSTRUCTIONS
    for expected in ("readiness", "ready", "index_unavailable", "native_search", "reindex"):
        assert expected in text


def test_query_tool_descriptions_are_readiness_gated():
    tools = _tools_by_name()
    for tool_name in ("search_code", "symbol_lookup"):
        description = tools[tool_name].description
        for expected in (
            "readiness",
            "ready",
            "index_unavailable",
            "native_search",
            "reindex",
        ):
            assert expected in description


def test_query_tool_descriptions_remove_unconditional_mcp_first_language():
    tools = _tools_by_name()
    forbidden = (
        "[USE BEFORE GREP]",
        "ALWAYS use",
        "Fall back to Grep ONLY",
        "0 results",
        "returns not_found",
    )
    for tool_name in ("search_code", "symbol_lookup"):
        description = tools[tool_name].description
        for phrase in forbidden:
            assert phrase not in description


def test_query_repository_inputs_remain_optional():
    tools = _tools_by_name()
    for tool_name in ("search_code", "symbol_lookup"):
        schema = tools[tool_name].inputSchema
        assert "repository" in schema["properties"]
        assert "repository" not in schema.get("required", [])


def test_secondary_tool_descriptions_are_readiness_gated_without_native_fallback():
    tools = _tools_by_name()
    for tool_name in ("reindex", "write_summaries", "summarize_sample"):
        description = tools[tool_name].description
        assert "readiness" in description
        assert "ready" in description
        assert "structured readiness refusal" in description
        assert "native_search" not in description
        assert "safe_fallback" not in description


def test_list_plugins_description_mentions_machine_readable_support_facts():
    description = _tools_by_name()["list_plugins"].description
    for expected in ("machine-readable", "specific-plugin", "registry-only", "activation"):
        assert expected in description


def test_no_argument_tools_preserve_empty_object_contract():
    tools = _tools_by_name()
    for tool_name in ("get_status", "list_plugins"):
        schema = tools[tool_name].inputSchema
        assert schema["type"] == "object"
        assert schema["properties"] == {}
        assert schema.get("required", []) == []
