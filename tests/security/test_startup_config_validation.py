"""P18 SL-1: Tests for validate_production_config + render_validation_errors_to_stderr."""

from __future__ import annotations

import io
import sys
from typing import List
from unittest.mock import patch

import pytest

from mcp_server.config.validation import (
    ValidationError,
    render_validation_errors_to_stderr,
    validate_production_config,
)
from mcp_server.security import SecurityConfig

_JWT_STRONG = "a-very-strong-jwt-secret-key-that-is-at-least-32-chars"
_JWT_WEAK = "secret"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(
    jwt_secret: str = _JWT_STRONG,
    cors_origins: List[str] | None = None,
    rate_limit_requests: int = 100,
) -> SecurityConfig:
    return SecurityConfig(
        jwt_secret_key=jwt_secret,
        jwt_algorithm="HS256",
        access_token_expire_minutes=30,
        cors_origins=cors_origins if cors_origins is not None else ["https://example.com"],
        rate_limit_requests=rate_limit_requests,
    )


# ---------------------------------------------------------------------------
# validate_production_config — production environment
# ---------------------------------------------------------------------------


class TestValidateProductionConfigProd:
    """validate_production_config with environment='production'."""

    def test_weak_jwt_is_fatal_in_production(self) -> None:
        cfg = _make_config(jwt_secret=_JWT_WEAK + "x" * 30)  # long enough to pass model, but in blocklist
        # Use a plainly blocked keyword
        cfg2 = SecurityConfig(
            jwt_secret_key="password" + "x" * 25,  # in blocklist
            cors_origins=["https://example.com"],
        )
        errors = validate_production_config(cfg2, environment="production")
        fatals = [e for e in errors if e.severity == "fatal"]
        assert fatals, "Expected fatal error for blocked JWT keyword"

    def test_very_short_jwt_is_fatal_in_production(self) -> None:
        # SecurityConfig validator rejects <32-char keys; test at 32-char boundary with blocklisted value
        blocked_jwt = "changeme" + "x" * 24  # 32 chars, in blocklist
        cfg = SecurityConfig(
            jwt_secret_key=blocked_jwt,
            cors_origins=["https://example.com"],
        )
        errors = validate_production_config(cfg, environment="production")
        fatals = [e for e in errors if e.severity == "fatal"]
        assert fatals, "Expected fatal for blocked JWT value in prod"

    def test_cors_wildcard_is_fatal_in_production(self) -> None:
        cfg = _make_config(cors_origins=["*"])
        errors = validate_production_config(cfg, environment="production")
        fatals = [e for e in errors if e.severity == "fatal"]
        assert any("cors" in e.code.lower() or "cors" in e.message.lower() for e in fatals), (
            f"Expected CORS-wildcard fatal, got: {errors}"
        )

    def test_high_rate_limit_is_fatal_in_production(self) -> None:
        cfg = _make_config(rate_limit_requests=1001)
        errors = validate_production_config(cfg, environment="production")
        fatals = [e for e in errors if e.severity == "fatal"]
        assert any("rate" in e.code.lower() or "rate" in e.message.lower() for e in fatals), (
            f"Expected rate-limit fatal, got: {errors}"
        )

    def test_missing_admin_password_is_fatal_in_production(self) -> None:
        cfg = _make_config()
        with patch.dict("os.environ", {"DEFAULT_ADMIN_PASSWORD": ""}, clear=False):
            # Unset the var by removing it
            import os
            env_backup = os.environ.pop("DEFAULT_ADMIN_PASSWORD", None)
            try:
                errors = validate_production_config(cfg, environment="production")
            finally:
                if env_backup is not None:
                    os.environ["DEFAULT_ADMIN_PASSWORD"] = env_backup
        fatals = [e for e in errors if e.severity == "fatal"]
        assert any(
            "admin" in e.code.lower() or "admin" in e.message.lower() or "password" in e.message.lower()
            for e in fatals
        ), f"Expected missing-admin-password fatal, got: {errors}"

    def test_weak_admin_password_is_fatal_in_production(self) -> None:
        cfg = _make_config()
        with patch.dict("os.environ", {"DEFAULT_ADMIN_PASSWORD": "admin"}, clear=False):
            errors = validate_production_config(cfg, environment="production")
        fatals = [e for e in errors if e.severity == "fatal"]
        assert any(
            "admin" in e.code.lower() or "password" in e.message.lower()
            for e in fatals
        ), f"Expected weak-admin-password fatal, got: {errors}"

    def test_clean_production_config_returns_no_errors(self) -> None:
        cfg = _make_config()
        with patch.dict("os.environ", {"DEFAULT_ADMIN_PASSWORD": "Str0ng!Admin#Pass9876"}, clear=False):
            errors = validate_production_config(cfg, environment="production")
        assert errors == [], f"Expected no errors for clean config, got: {errors}"


# ---------------------------------------------------------------------------
# validate_production_config — development environment
# ---------------------------------------------------------------------------


class TestValidateProductionConfigDev:
    """In development, weak JWT should be a warn, not fatal."""

    def test_weak_jwt_is_warn_not_fatal_in_development(self) -> None:
        blocked_jwt = "secret" + "x" * 26  # 32 chars, in blocklist
        cfg = SecurityConfig(
            jwt_secret_key=blocked_jwt,
            cors_origins=["*"],
        )
        errors = validate_production_config(cfg, environment="development")
        fatals = [e for e in errors if e.severity == "fatal"]
        warns = [e for e in errors if e.severity == "warn"]
        # In dev, should be warns not fatals
        assert not fatals, f"Expected no fatals in dev, got: {fatals}"
        assert warns, f"Expected at least one warn in dev for weak JWT, got: {errors}"


# ---------------------------------------------------------------------------
# render_validation_errors_to_stderr
# ---------------------------------------------------------------------------


class TestRenderValidationErrors:
    """render_validation_errors_to_stderr output format."""

    def test_fatal_errors_prefixed_with_FATAL(self) -> None:
        errors = [
            ValidationError(code="WEAK_JWT", message="JWT secret is weak", severity="fatal"),
        ]
        buf = io.StringIO()
        with patch("sys.stderr", buf):
            render_validation_errors_to_stderr(errors)
        output = buf.getvalue()
        assert "[FATAL]" in output, f"Expected [FATAL] prefix, got: {output!r}"
        assert "WEAK_JWT" in output
        assert "JWT secret is weak" in output

    def test_warn_errors_prefixed_with_WARN(self) -> None:
        errors = [
            ValidationError(code="CORS_WILD", message="CORS wildcard in staging", severity="warn"),
        ]
        buf = io.StringIO()
        with patch("sys.stderr", buf):
            render_validation_errors_to_stderr(errors)
        output = buf.getvalue()
        assert "[WARN]" in output, f"Expected [WARN] prefix, got: {output!r}"

    def test_each_error_on_separate_line(self) -> None:
        errors = [
            ValidationError(code="E1", message="first", severity="fatal"),
            ValidationError(code="E2", message="second", severity="warn"),
        ]
        buf = io.StringIO()
        with patch("sys.stderr", buf):
            render_validation_errors_to_stderr(errors)
        lines = [ln for ln in buf.getvalue().splitlines() if ln.strip()]
        assert len(lines) == 2, f"Expected 2 lines, got: {lines}"

    def test_empty_errors_writes_nothing(self) -> None:
        buf = io.StringIO()
        with patch("sys.stderr", buf):
            render_validation_errors_to_stderr([])
        assert buf.getvalue() == ""
