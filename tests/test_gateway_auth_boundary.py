"""Representative gateway auth-boundary regressions."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_search_rejects_invalid_bearer(test_client_with_dispatcher: TestClient) -> None:
    response = test_client_with_dispatcher.get(
        "/search?q=test",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert response.status_code == 401


def test_reindex_rejects_readonly_token(test_client_with_dispatcher: TestClient, monkeypatch) -> None:
    import asyncio

    from mcp_server.security import UserRole

    auth_manager = test_client_with_dispatcher.app.state.auth_manager
    readonly_user = asyncio.run(auth_manager.get_user_by_username("pytest_readonly"))
    if readonly_user is None:
        readonly_user = asyncio.run(
            auth_manager.create_user(
                username="pytest_readonly",
                password="PytestReadonly123!",
                email="pytest_readonly@test.local",
                role=UserRole.READONLY,
            )
        )
    token = asyncio.run(auth_manager.create_access_token(readonly_user))
    response = test_client_with_dispatcher.post(
        "/reindex",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
