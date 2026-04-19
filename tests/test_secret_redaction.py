"""Tests for SecretRedactionResponseMiddleware (SL-4.1 / SL-4.3)."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.responses import JSONResponse, Response


def _make_app_with_redaction():
    from mcp_server.security.security_middleware import SecretRedactionResponseMiddleware

    app = FastAPI()
    app.add_middleware(SecretRedactionResponseMiddleware)

    @app.get("/ok")
    async def ok_endpoint():
        return {"message": "Bearer abc123 is your token"}

    @app.get("/bad")
    async def bad_endpoint():
        return Response(
            content='{"detail": "Bearer abc123 rejected"}',
            status_code=400,
            media_type="application/json",
        )

    @app.get("/server-error")
    async def server_error():
        return Response(
            content='{"error": "JWT_SECRET_KEY=supersecret exposed"}',
            status_code=500,
            media_type="application/json",
        )

    @app.get("/github-token-leak")
    async def github_token():
        return Response(
            content='{"msg": "GITHUB_TOKEN=ghp_abc12345 was used"}',
            status_code=403,
            media_type="application/json",
        )

    return app


def test_4xx_bearer_token_redacted():
    """Bearer tokens in 4xx responses must be redacted."""
    client = TestClient(_make_app_with_redaction(), raise_server_exceptions=False)
    resp = client.get("/bad")
    assert resp.status_code == 400
    body = resp.text
    assert "abc123" not in body
    assert "Bearer [REDACTED]" in body


def test_5xx_jwt_secret_redacted():
    """JWT_SECRET_KEY value in 5xx responses must be redacted."""
    client = TestClient(_make_app_with_redaction(), raise_server_exceptions=False)
    resp = client.get("/server-error")
    assert resp.status_code == 500
    body = resp.text
    assert "supersecret" not in body
    assert "JWT_SECRET_KEY=[REDACTED]" in body


def test_4xx_github_token_redacted():
    """GITHUB_TOKEN value in 4xx responses must be redacted."""
    client = TestClient(_make_app_with_redaction(), raise_server_exceptions=False)
    resp = client.get("/github-token-leak")
    assert resp.status_code == 403
    body = resp.text
    assert "ghp_abc12345" not in body
    assert "GITHUB_TOKEN=[REDACTED]" in body


def test_2xx_body_untouched():
    """2xx responses must not be modified."""
    client = TestClient(_make_app_with_redaction(), raise_server_exceptions=False)
    resp = client.get("/ok")
    assert resp.status_code == 200
    body = resp.text
    assert "Bearer abc123 is your token" in body
