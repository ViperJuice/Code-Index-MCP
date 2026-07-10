"""AUTHBOUND startup wiring tests."""

from __future__ import annotations

import pytest

from mcp_server import gateway


def test_gateway_import_registers_security_middleware_before_startup() -> None:
    middleware_names = [middleware.cls.__name__ for middleware in gateway.app.user_middleware]
    for expected in (
        "SecretRedactionResponseMiddleware",
        "RateLimitMiddleware",
        "AuthenticationMiddleware",
        "AuthorizationMiddleware",
        "RequestValidationMiddleware",
        "SecurityHeadersMiddleware",
        "CORSMiddleware",
    ):
        assert expected in middleware_names


def test_prestartup_registration_does_not_swallow_late_middleware_error() -> None:
    calls: list[str] = []

    class FakeApp:
        def add_middleware(self, middleware_cls, *args, **kwargs) -> None:
            calls.append(middleware_cls.__name__)
            if middleware_cls.__name__ == "AuthorizationMiddleware":
                raise RuntimeError("Cannot add middleware after an application has started")

    with pytest.raises(RuntimeError, match="Cannot add middleware after an application has started"):
        gateway._register_security_middleware(
            FakeApp(),  # type: ignore[arg-type]
            gateway.security_config,
            gateway.auth_manager,
        )

    assert "AuthorizationMiddleware" in calls


def test_secret_redaction_middleware_is_present_even_before_startup_success() -> None:
    middleware_names = [middleware.cls.__name__ for middleware in gateway.app.user_middleware]
    assert "SecretRedactionResponseMiddleware" in middleware_names
