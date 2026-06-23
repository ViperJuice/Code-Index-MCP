"""MCPTASKS protocol contract checks."""

from __future__ import annotations

import mcp.types as types
from mcp.server import Server

from mcp_server.cli.stdio_runner import _build_tool_list
from mcp_server.storage.mcp_task_registry import MCPTaskRegistry


def _tool_map():
    return {tool.name: tool for tool in _build_tool_list()}


def test_only_reindex_and_write_summaries_opt_into_task_augmented_execution():
    tools = _tool_map()
    assert tools["reindex"].execution is not None
    assert tools["reindex"].execution.taskSupport == "optional"
    assert tools["write_summaries"].execution is not None
    assert tools["write_summaries"].execution.taskSupport == "optional"
    for tool_name in (
        "symbol_lookup",
        "search_code",
        "get_status",
        "list_plugins",
        "summarize_sample",
        "handshake",
    ):
        assert tools[tool_name].execution is None


def test_server_capabilities_advertise_sdk_task_surface_when_enabled():
    server = Server("mcptasks-test")
    registry = MCPTaskRegistry()
    server.experimental.enable_tasks(store=registry)

    capabilities = server.create_initialization_options().capabilities
    assert capabilities.tasks is not None
    assert capabilities.tasks.list is not None
    assert capabilities.tasks.cancel is not None
    assert capabilities.tasks.requests is not None
    assert capabilities.tasks.requests.tools is not None
    assert capabilities.tasks.requests.tools.call is not None


def test_call_tool_request_params_expose_task_metadata_field():
    params = types.CallToolRequestParams(name="reindex", arguments={}, task=types.TaskMetadata())
    assert params.task is not None
