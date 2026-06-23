"""MCPAUTH regression tests for the local STDIO handshake boundary."""

from __future__ import annotations

import json
import logging
from typing import Any

import mcp.types as types
import pytest

from mcp_server.cli.handshake import HandshakeGate
from mcp_server.cli import stdio_runner


def _payload(result: types.CallToolResult) -> Any:
    assert result.content
    assert isinstance(result.content[0], types.TextContent)
    return json.loads(result.content[0].text)


@pytest.fixture
def restore_stdio_globals():
    saved = {
        "_gate": stdio_runner._gate,
        "_lazy_summarizer": stdio_runner._lazy_summarizer,
        "sqlite_store": stdio_runner.sqlite_store,
        "dispatcher": stdio_runner.dispatcher,
        "initialization_error": stdio_runner.initialization_error,
    }
    yield
    stdio_runner._gate = saved["_gate"]
    stdio_runner._lazy_summarizer = saved["_lazy_summarizer"]
    stdio_runner.sqlite_store = saved["sqlite_store"]
    stdio_runner.dispatcher = saved["dispatcher"]
    stdio_runner.initialization_error = saved["initialization_error"]


@pytest.mark.asyncio
async def test_handshake_tool_logs_redacted_secret(caplog, restore_stdio_globals):
    stdio_runner._gate = HandshakeGate(secret="top-secret")
    stdio_runner._lazy_summarizer = object()
    stdio_runner.sqlite_store = object()
    stdio_runner.initialization_error = None

    with caplog.at_level(logging.INFO, logger="mcp_server.cli.stdio_runner"):
        result = await stdio_runner.call_tool("handshake", {"secret": "top-secret"})

    assert _payload(result) == {"authenticated": True}
    tool_logs = [record.getMessage() for record in caplog.records if "MCP Tool Call" in record.getMessage()]
    assert tool_logs
    assert any("[REDACTED]" in message for message in tool_logs)
    assert all("top-secret" not in message for message in tool_logs)


@pytest.mark.asyncio
async def test_non_handshake_tool_keeps_regular_argument_logging(
    monkeypatch, caplog, restore_stdio_globals
):
    stdio_runner._gate = HandshakeGate(secret="gate-secret")
    assert stdio_runner._gate.verify("gate-secret") is True
    stdio_runner._lazy_summarizer = object()
    stdio_runner.sqlite_store = object()
    stdio_runner.initialization_error = None

    async def fake_search_code(**kwargs):
        return [
            types.TextContent(
                type="text",
                text=stdio_runner.tool_handlers._ensure_response({"results": []}),
            )
        ]

    monkeypatch.setattr(stdio_runner.tool_handlers, "handle_search_code", fake_search_code)

    with caplog.at_level(logging.INFO, logger="mcp_server.cli.stdio_runner"):
        result = await stdio_runner.call_tool("search_code", {"query": "demo"})

    assert _payload(result) == {"results": []}
    tool_logs = [record.getMessage() for record in caplog.records if "MCP Tool Call" in record.getMessage()]
    assert tool_logs
    assert any("demo" in message for message in tool_logs)
