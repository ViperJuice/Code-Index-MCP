"""SL-2: tests for /metrics authentication and authorization."""

from __future__ import annotations

import asyncio

import pytest
from fastapi import Depends, FastAPI, Response
from fastapi.responses import PlainTextResponse
from fastapi.testclient import TestClient

from mcp_server.security import (
    AuthManager,
    Permission,
    SecurityConfig,
    User,
    UserRole,
)
from mcp_server.security.security_middleware import (
    AuthenticationMiddleware,
    require_auth,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

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
                username="admin_sl2",
                password="AdminPass123!",
                email="admin_sl2@test.local",
                role=UserRole.ADMIN,
            )
        )
        return loop.run_until_complete(auth_manager.create_access_token(admin))
    finally:
        loop.close()


@pytest.fixture(scope="module")
def readonly_token(auth_manager: AuthManager) -> str:
    loop = asyncio.new_event_loop()
    try:
        ro_user: User = loop.run_until_complete(
            auth_manager.create_user(
                username="readonly_sl2",
                password="ReadOnly123!",
                email="readonly_sl2@test.local",
                role=UserRole.READONLY,
            )
        )
        return loop.run_until_complete(auth_manager.create_access_token(ro_user))
    finally:
        loop.close()


@pytest.fixture(scope="module")
def metrics_app(auth_manager: AuthManager) -> FastAPI:
    """Minimal FastAPI app that mirrors the real gateway's /metrics + /health setup."""
    _app = FastAPI()

    # Wire AuthenticationMiddleware with /metrics NOT excluded (mirrors post-SL-2 state)
    _app.add_middleware(
        AuthenticationMiddleware,
        auth_manager=auth_manager,
        excluded_paths=[
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/refresh",
        ],
    )

    @_app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @_app.get(
        "/metrics",
        response_class=PlainTextResponse,
        dependencies=[Depends(require_auth("metrics"))],
    )
    def metrics() -> str:
        return "# HELP python_gc_objects_collected_total\n# TYPE python_gc_objects_collected_total counter\n"

    @_app.get("/search")
    def search(q: str, _user: User = Depends(require_auth("tools"))) -> dict:
        return {"results": []}

    return _app


@pytest.fixture(scope="module")
def client(metrics_app: FastAPI) -> TestClient:
    return TestClient(metrics_app, raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# (a) Unauthenticated GET /metrics → 401
# ---------------------------------------------------------------------------

def test_metrics_unauthenticated_returns_401(client: TestClient) -> None:
    resp = client.get("/metrics")
    assert resp.status_code == 401, resp.text


# ---------------------------------------------------------------------------
# (b) Admin token → 200 + Prometheus payload
# ---------------------------------------------------------------------------

def test_metrics_admin_returns_200(client: TestClient, admin_token: str) -> None:
    resp = client.get("/metrics", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200, resp.text
    ct = resp.headers.get("content-type", "")
    assert "text/plain" in ct
    assert "# HELP" in resp.text or "# TYPE" in resp.text


# ---------------------------------------------------------------------------
# (c) Read-only token → 403
# ---------------------------------------------------------------------------

def test_metrics_readonly_returns_403(client: TestClient, readonly_token: str) -> None:
    resp = client.get("/metrics", headers={"Authorization": f"Bearer {readonly_token}"})
    assert resp.status_code == 403, resp.text


# ---------------------------------------------------------------------------
# (d) Unaffected routes still work
# ---------------------------------------------------------------------------

def test_health_without_auth_returns_200(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200, resp.text


def test_search_with_admin_token_not_401_or_403(client: TestClient, admin_token: str) -> None:
    resp = client.get("/search?q=foo", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code not in (401, 403), f"Unexpected auth failure: {resp.status_code} {resp.text}"
