"""AUTHBOUND OpenAPI metadata tests."""

from __future__ import annotations

from mcp_server.gateway import app

PUBLIC_PATHS = {"/docs", "/redoc", "/openapi.json", "/health", "/ready", "/liveness"}


def test_openapi_declares_http_bearer_security_scheme() -> None:
    schema = app.openapi()
    security_schemes = schema["components"]["securitySchemes"]
    assert "HTTPBearer" in security_schemes
    assert security_schemes["HTTPBearer"]["scheme"] == "bearer"
    assert security_schemes["HTTPBearer"]["type"] == "http"


def test_protected_operations_advertise_bearer_security() -> None:
    schema = app.openapi()
    assert schema["paths"]["/metrics"]["get"]["security"] == [{"HTTPBearer": []}]
    assert schema["paths"]["/search"]["get"]["security"] == [{"HTTPBearer": []}]
    assert schema["paths"]["/reindex"]["post"]["security"] == [{"HTTPBearer": []}]


def test_public_operations_remain_unauthenticated() -> None:
    schema = app.openapi()
    for path in PUBLIC_PATHS:
        operations = schema["paths"].get(path, {})
        for operation in operations.values():
            assert "security" not in operation or operation["security"] == []
