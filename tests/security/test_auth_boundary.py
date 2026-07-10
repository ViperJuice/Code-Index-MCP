"""AUTHBOUND boundary tests for validated JWT-only protected routes."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from mcp_server.security import (
    AuthManager,
    Permission,
    SecurityConfig,
    User,
    UserRole,
    require_permission,
    require_role,
)
from mcp_server.security.security_middleware import AuthenticationMiddleware

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
def token_users(auth_manager: AuthManager) -> dict[str, User]:
    loop = asyncio.new_event_loop()
    try:
        admin = loop.run_until_complete(
            auth_manager.create_user(
                username="authbound_admin",
                password="AuthboundAdmin123!",
                email="authbound_admin@test.local",
                role=UserRole.ADMIN,
            )
        )
        readonly = loop.run_until_complete(
            auth_manager.create_user(
                username="authbound_readonly",
                password="AuthboundReadonly123!",
                email="authbound_readonly@test.local",
                role=UserRole.READONLY,
            )
        )
        inactive = loop.run_until_complete(
            auth_manager.create_user(
                username="authbound_inactive",
                password="AuthboundInactive123!",
                email="authbound_inactive@test.local",
                role=UserRole.USER,
            )
        )
        inactive.is_active = False
        return {"admin": admin, "readonly": readonly, "inactive": inactive}
    finally:
        loop.close()


@pytest.fixture(scope="module")
def boundary_app(auth_manager: AuthManager) -> FastAPI:
    app = FastAPI()
    app.state.auth_manager = auth_manager
    app.add_middleware(AuthenticationMiddleware, auth_manager=auth_manager)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/admin", dependencies=[Depends(require_role(UserRole.ADMIN))])
    def admin_route() -> dict[str, bool]:
        return {"ok": True}

    @app.post("/mutate", dependencies=[Depends(require_permission(Permission.WRITE))])
    def mutate_route() -> dict[str, bool]:
        return {"ok": True}

    @app.get("/read", dependencies=[Depends(require_permission(Permission.READ))])
    def read_route() -> dict[str, bool]:
        return {"ok": True}

    return app


@pytest.fixture(scope="module")
def client(boundary_app: FastAPI) -> TestClient:
    return TestClient(boundary_app, raise_server_exceptions=False)


def _encode(payload: dict, secret: str = _JWT_SECRET, algorithm: str = "HS256") -> str:
    return jwt.encode(payload, secret, algorithm=algorithm)


def _payload_for(user: User, **overrides: object) -> dict[str, object]:
    now = datetime.now(timezone.utc)
    payload: dict[str, object] = {
        "user_id": user.id,
        "username": user.username,
        "role": user.role.value,
        "permissions": [permission.value for permission in user.permissions],
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=30)).timestamp()),
        "type": "access",
    }
    payload.update(overrides)
    return payload


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_access_token(auth_manager: AuthManager, user: User) -> str:
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(auth_manager.create_access_token(user))
    finally:
        loop.close()


def test_missing_bearer_rejected(client: TestClient) -> None:
    response = client.get("/admin")
    assert response.status_code == 401


def test_malformed_bearer_rejected(client: TestClient) -> None:
    response = client.get("/admin", headers={"Authorization": "Token invalid"})
    assert response.status_code == 401


def test_arbitrary_bearer_token_rejected(client: TestClient) -> None:
    response = client.get("/admin", headers=_auth_header("test-token"))
    assert response.status_code == 401
    assert "fallback-user" not in response.text


def test_forged_signature_rejected(client: TestClient, token_users: dict[str, User]) -> None:
    token = _encode(_payload_for(token_users["admin"]), secret="different-secret-value-12345678901234567890")
    response = client.get("/admin", headers=_auth_header(token))
    assert response.status_code == 401


def test_wrong_algorithm_rejected(client: TestClient, token_users: dict[str, User]) -> None:
    token = _encode(_payload_for(token_users["admin"]), algorithm="HS384")
    response = client.get("/admin", headers=_auth_header(token))
    assert response.status_code == 401


def test_none_algorithm_rejected(client: TestClient, token_users: dict[str, User]) -> None:
    token = jwt.encode(_payload_for(token_users["admin"]), key="", algorithm="none")
    response = client.get("/admin", headers=_auth_header(token))
    assert response.status_code == 401


def test_expired_token_rejected(client: TestClient, token_users: dict[str, User]) -> None:
    now = datetime.now(timezone.utc)
    token = _encode(
        _payload_for(
            token_users["admin"],
            iat=int((now - timedelta(hours=2)).timestamp()),
            exp=int((now - timedelta(hours=1)).timestamp()),
        )
    )
    response = client.get("/admin", headers=_auth_header(token))
    assert response.status_code == 401


def test_missing_subject_rejected(client: TestClient, token_users: dict[str, User]) -> None:
    payload = _payload_for(token_users["admin"])
    del payload["user_id"]
    token = _encode(payload)
    response = client.get("/admin", headers=_auth_header(token))
    assert response.status_code == 401


def test_unknown_user_rejected(client: TestClient, token_users: dict[str, User]) -> None:
    token = _encode(_payload_for(token_users["admin"], user_id="missing-user-id"))
    response = client.get("/admin", headers=_auth_header(token))
    assert response.status_code == 401


def test_inactive_user_rejected(client: TestClient, token_users: dict[str, User]) -> None:
    token = _create_access_token(auth_manager=client.app.state.auth_manager, user=token_users["inactive"])
    response = client.get("/admin", headers=_auth_header(token))
    assert response.status_code == 401


def test_invalid_role_claim_rejected(client: TestClient, token_users: dict[str, User]) -> None:
    token = _encode(_payload_for(token_users["admin"], role="superuser"))
    response = client.get("/admin", headers=_auth_header(token))
    assert response.status_code == 401


def test_invalid_permission_claim_rejected(client: TestClient, token_users: dict[str, User]) -> None:
    token = _encode(_payload_for(token_users["admin"], permissions=["read", "root"]))
    response = client.get("/admin", headers=_auth_header(token))
    assert response.status_code == 401


def test_low_privilege_token_gets_403(client: TestClient, auth_manager: AuthManager, token_users: dict[str, User]) -> None:
    token = _create_access_token(auth_manager, token_users["readonly"])
    response = client.post("/mutate", headers=_auth_header(token))
    assert response.status_code == 403


def test_valid_token_uses_persisted_permissions(client: TestClient, token_users: dict[str, User]) -> None:
    forged_admin_claims = _encode(
        _payload_for(
            token_users["readonly"],
            role=UserRole.ADMIN.value,
            permissions=[permission.value for permission in Permission],
        )
    )
    response = client.get("/admin", headers=_auth_header(forged_admin_claims))
    assert response.status_code == 403


def test_readonly_token_can_access_read_endpoint(client: TestClient, auth_manager: AuthManager, token_users: dict[str, User]) -> None:
    token = _create_access_token(auth_manager, token_users["readonly"])
    response = client.get("/read", headers=_auth_header(token))
    assert response.status_code == 200
