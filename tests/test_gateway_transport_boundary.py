from __future__ import annotations

from fastapi.routing import APIRoute

from mcp_server.gateway import app


def test_gateway_exposes_admin_routes_but_no_mcp_transport_endpoint():
    paths = {route.path for route in app.routes if isinstance(route, APIRoute)}

    for expected in ("/symbol", "/search", "/status", "/plugins", "/reindex"):
        assert expected in paths

    for disallowed in ("/mcp", "/messages", "/sse"):
        assert disallowed not in paths


def test_gateway_metadata_keeps_fastapi_admin_positioning():
    assert app.title == "MCP Server"
    assert "Code Index MCP Server" in (app.description or "")
