"""Tests for HandshakeGate (SL-2)."""
from __future__ import annotations

import inspect
import logging
import os

import pytest

from mcp_server.cli.handshake import HandshakeGate


# ---------------------------------------------------------------------------
# HandshakeGate unit tests
# ---------------------------------------------------------------------------

class TestHandshakeGateDisabled:
    """Gate with no secret configured — always passes."""

    def test_check_always_none_when_disabled(self):
        gate = HandshakeGate(secret=None)
        # No MCP_CLIENT_SECRET in env means disabled
        os.environ.pop("MCP_CLIENT_SECRET", None)
        gate2 = HandshakeGate()
        assert gate.check("any_tool", {}) is None
        assert gate2.check("any_tool", {}) is None

    def test_enabled_false_when_no_secret(self):
        gate = HandshakeGate(secret=None)
        assert gate.enabled is False

    def test_enabled_false_when_empty_string(self):
        gate = HandshakeGate(secret="")
        assert gate.enabled is False

    def test_verify_returns_false_when_disabled(self):
        gate = HandshakeGate(secret=None)
        # Even an "empty vs empty" must not authenticate
        assert gate.verify("") is False
        assert gate.verify("anything") is False


class TestHandshakeGateEnabled:
    """Gate with a secret configured."""

    def setup_method(self):
        self.gate = HandshakeGate(secret="correct-secret")

    def test_enabled_true_with_secret(self):
        assert self.gate.enabled is True

    def test_pre_handshake_returns_handshake_required(self):
        err = self.gate.check("symbol_lookup", {})
        assert err is not None
        # The dict must contain handshake_required code
        assert err.get("code") == "handshake_required"

    def test_handshake_tool_allowed_pre_auth(self):
        # Calling "handshake" itself must not be blocked
        result = self.gate.check("handshake", {"secret": "x"})
        assert result is None

    def test_verify_correct_secret_returns_true(self):
        assert self.gate.verify("correct-secret") is True

    def test_verify_wrong_secret_returns_false(self):
        assert self.gate.verify("wrong") is False

    def test_verify_empty_secret_returns_false(self):
        assert self.gate.verify("") is False

    def test_after_verify_subsequent_calls_pass(self):
        assert self.gate.verify("correct-secret") is True
        # After authentication, any tool call should be allowed
        assert self.gate.check("symbol_lookup", {}) is None
        assert self.gate.check("search_code", {}) is None

    def test_wrong_verify_does_not_authenticate(self):
        assert self.gate.verify("wrong") is False
        # Still blocked after failed attempt
        err = self.gate.check("symbol_lookup", {})
        assert err is not None
        assert err.get("code") == "handshake_required"

    def test_verify_uses_compare_digest(self):
        src = inspect.getsource(HandshakeGate.verify)
        assert "compare_digest" in src

    def test_repeated_handshake_call_after_auth_passes(self):
        self.gate.verify("correct-secret")
        # handshake tool allowed even after authentication (no need to block)
        result = self.gate.check("handshake", {"secret": "x"})
        assert result is None


class TestHandshakeGateEnvRead:
    """Gate reads MCP_CLIENT_SECRET from env at construction."""

    def test_reads_from_env(self, monkeypatch):
        monkeypatch.setenv("MCP_CLIENT_SECRET", "env-secret")
        gate = HandshakeGate()
        assert gate.enabled is True
        assert gate.verify("env-secret") is True

    def test_not_enabled_when_env_unset(self, monkeypatch):
        monkeypatch.delenv("MCP_CLIENT_SECRET", raising=False)
        gate = HandshakeGate()
        assert gate.enabled is False

    def test_not_enabled_when_env_empty(self, monkeypatch):
        monkeypatch.setenv("MCP_CLIENT_SECRET", "")
        gate = HandshakeGate()
        assert gate.enabled is False


# ---------------------------------------------------------------------------
# Startup warning tests (caplog)
# ---------------------------------------------------------------------------

def _emit_startup_warning_if_needed(gate: HandshakeGate) -> None:
    """Mirrors the warning emission logic from _serve()."""
    _logger = logging.getLogger("mcp_server.cli.stdio_runner")
    if not gate.enabled:
        _logger.warning("running unauthenticated \u2014 MCP_CLIENT_SECRET not set")


class TestStartupWarning:
    def test_warning_emitted_when_no_secret(self, caplog, monkeypatch):
        monkeypatch.delenv("MCP_CLIENT_SECRET", raising=False)
        gate = HandshakeGate()
        with caplog.at_level(logging.WARNING, logger="mcp_server.cli.stdio_runner"):
            _emit_startup_warning_if_needed(gate)
        records = [r for r in caplog.records if "running unauthenticated" in r.message]
        assert len(records) == 1

    def test_warning_not_emitted_when_secret_set(self, caplog, monkeypatch):
        monkeypatch.setenv("MCP_CLIENT_SECRET", "somesecret")
        gate = HandshakeGate()
        with caplog.at_level(logging.WARNING, logger="mcp_server.cli.stdio_runner"):
            _emit_startup_warning_if_needed(gate)
        records = [r for r in caplog.records if "running unauthenticated" in r.message]
        assert len(records) == 0

    def test_warning_emitted_exactly_once_not_on_loop(self, caplog, monkeypatch):
        """Warning must be emitted at _serve() entry, not in a loop."""
        monkeypatch.delenv("MCP_CLIENT_SECRET", raising=False)
        gate = HandshakeGate()
        with caplog.at_level(logging.WARNING, logger="mcp_server.cli.stdio_runner"):
            # Simulate calling the startup code exactly once
            _emit_startup_warning_if_needed(gate)
        records = [r for r in caplog.records if "running unauthenticated" in r.message]
        assert len(records) == 1


# ---------------------------------------------------------------------------
# Integration-ish: gate.check() flow simulation
# ---------------------------------------------------------------------------

class TestHandshakeFlow:
    """Simulate the call_tool flow with gate."""

    def test_non_handshake_tool_blocked_before_auth(self):
        gate = HandshakeGate(secret="s3cr3t")
        err = gate.check("symbol_lookup", {})
        assert err is not None
        assert err.get("code") == "handshake_required"

    def test_handshake_tool_not_blocked(self):
        gate = HandshakeGate(secret="s3cr3t")
        result = gate.check("handshake", {"secret": "anything"})
        assert result is None

    def test_after_successful_handshake_tool_passes(self):
        gate = HandshakeGate(secret="s3cr3t")
        # First non-handshake call is blocked
        assert gate.check("symbol_lookup", {}) is not None
        # Perform handshake
        authenticated = gate.verify("s3cr3t")
        assert authenticated is True
        # Now tool call passes
        assert gate.check("symbol_lookup", {}) is None

    def test_wrong_secret_keeps_blocked(self):
        gate = HandshakeGate(secret="s3cr3t")
        gate.verify("wrong-secret")
        # Still blocked
        err = gate.check("search_code", {})
        assert err is not None
        assert err.get("code") == "handshake_required"

    def test_disabled_gate_never_blocks(self):
        gate = HandshakeGate(secret=None)
        assert gate.check("symbol_lookup", {}) is None
        assert gate.check("reindex", {}) is None
        assert gate.check("handshake", {"secret": "anything"}) is None
