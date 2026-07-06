"""MCPAUTH regression tests for the HTTP admin/debug auth boundary."""

from __future__ import annotations

import asyncio

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from starlette.responses import Response

from mcp_server.security import AuthManager, SecurityConfig, User, UserRole, require_auth
from mcp_server.security.security_middleware import (
    AuthenticationMiddleware,
    SecretRedactionResponseMiddleware,
)

_JWT_SECRET = "test-secret-key-at-least-32-characters-long"


@pytest.fixture(scope="module")
def security_config() -> SecurityConfig:
    return SecurityConfig(
        jwt_secret_key=_JWT_SECRET,
        jwt_algorithm="HS256",
        access_token_expire_minutes=30,
    )


@pytest.fixture(scope="module")
def auth_manager(security_config: SecurityConfig) -> AuthManager:
    return AuthManager(security_config)


@pytest.fixture(scope="module")
def admin_token(auth_manager: AuthManager) -> str:
    loop = asyncio.new_event_loop()
    try:
        admin: User = loop.run_until_complete(
            auth_manager.create_user(
                username="admin_mcpauth_boundary",
                password="AdminPass123!",
                email="admin_mcpauth_boundary@test.local",
                role=UserRole.ADMIN,
            )
        )
        return loop.run_until_complete(auth_manager.create_access_token(admin))
    finally:
        loop.close()


@pytest.fixture(scope="module")
def boundary_app(auth_manager: AuthManager) -> FastAPI:
    app = FastAPI()
    app.add_middleware(SecretRedactionResponseMiddleware)
    app.add_middleware(
        AuthenticationMiddleware,
        auth_manager=auth_manager,
        excluded_paths=["/docs", "/redoc", "/openapi.json", "/health", "/leaky-error"],
    )

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/admin-only", dependencies=[Depends(require_auth("admin"))])
    def admin_only() -> dict:
        return {"ok": True}

    @app.get("/leaky-error")
    def leaky_error() -> Response:
        return Response(
            content=(
                '{"detail":"MCP_CLIENT_SECRET=stdiosecret rejected; '
                'Bearer admin-token should not leak"}'
            ),
            status_code=401,
            media_type="application/json",
        )

    return app


@pytest.fixture(scope="module")
def client(boundary_app: FastAPI) -> TestClient:
    return TestClient(boundary_app, raise_server_exceptions=False)


def test_admin_route_requires_bearer_auth_not_handshake(client: TestClient) -> None:
    resp = client.get("/admin-only")
    assert resp.status_code == 401
    assert "Missing authentication token" in resp.text
    assert "handshake" not in resp.text


def test_admin_route_accepts_valid_bearer_token(client: TestClient, admin_token: str) -> None:
    resp = client.get("/admin-only", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


def test_http_error_redacts_stdio_secret_and_bearer_value(client: TestClient) -> None:
    resp = client.get("/leaky-error")
    assert resp.status_code == 401
    body = resp.text
    assert "stdiosecret" not in body
    assert "admin-token" not in body
    assert "MCP_CLIENT_SECRET=[REDACTED]" in body
    assert "Bearer [REDACTED]" in body
