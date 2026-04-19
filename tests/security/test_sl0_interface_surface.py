"""Pure import + signature tests for SL-0 interface-freeze stubs."""

from __future__ import annotations

import dataclasses
import inspect
import pytest


# ---------------------------------------------------------------------------
# IF-0-P15-1: plugin sandbox
# ---------------------------------------------------------------------------

def test_envelope_importable():
    from mcp_server.sandbox.protocol import Envelope
    assert Envelope is not None


def test_envelope_fields():
    from mcp_server.sandbox.protocol import Envelope
    fields = Envelope.model_fields
    assert set(fields) == {"v", "id", "kind", "method", "payload"}


def test_protocol_constants():
    from mcp_server.sandbox import protocol
    assert protocol.MAX_LINE_BYTES == 16 * 1024 * 1024
    assert protocol.DEFAULT_TIMEOUT_SECONDS == 30.0


def test_capability_set_importable():
    from mcp_server.sandbox.capabilities import CapabilitySet
    assert CapabilitySet is not None


def test_capability_set_defaults():
    dc_fields = {f.name: f for f in dataclasses.fields(__import__(
        "mcp_server.sandbox.capabilities", fromlist=["CapabilitySet"]
    ).CapabilitySet)}
    assert dc_fields["network"].default is False
    assert dc_fields["sqlite"].default == "none"
    assert dc_fields["cpu_seconds"].default == 30
    assert dc_fields["mem_mb"].default == 512


def test_sandbox_supervisor_importable():
    from mcp_server.sandbox.supervisor import SandboxSupervisor
    assert SandboxSupervisor is not None


def test_sandbox_supervisor_call_signature():
    from mcp_server.sandbox.supervisor import SandboxSupervisor
    sig = inspect.signature(SandboxSupervisor.call)
    params = list(sig.parameters)
    assert "method" in params
    assert "payload" in params
    assert "timeout" in params
    assert sig.parameters["timeout"].default == 30.0


def test_sandbox_supervisor_close_signature():
    from mcp_server.sandbox.supervisor import SandboxSupervisor
    sig = inspect.signature(SandboxSupervisor.close)
    assert list(sig.parameters) == ["self"]


def test_worker_main_importable():
    from mcp_server.sandbox.worker_main import main
    assert callable(main)


def test_worker_main_signature():
    from mcp_server.sandbox.worker_main import main
    sig = inspect.signature(main)
    params = sig.parameters
    assert "argv" in params
    assert params["argv"].default is None


def test_sandboxed_plugin_iplugin_mro():
    from mcp_server.plugins.sandboxed_plugin import SandboxedPlugin
    from mcp_server.plugin_base import IPlugin
    assert IPlugin in SandboxedPlugin.__mro__


def test_sandboxed_plugin_init_signature():
    from mcp_server.plugins.sandboxed_plugin import SandboxedPlugin
    sig = inspect.signature(SandboxedPlugin.__init__)
    params = sig.parameters
    assert "plugin_module" in params
    assert "capabilities" in params
    assert "gh_cmd" in params
    assert params["gh_cmd"].default == "python"


# SL-1 filled the SandboxedPlugin body; the stub-stage NotImplementedError
# assertion has been removed. Behavior is covered by
# tests/security/test_plugin_sandbox.py and tests/security/test_malicious_plugin.py.


# ---------------------------------------------------------------------------
# IF-0-P15-2: metrics auth
# ---------------------------------------------------------------------------

def test_require_auth_importable():
    from mcp_server.security.security_middleware import require_auth
    assert callable(require_auth)


def test_require_auth_returns_callable():
    from mcp_server.security.security_middleware import require_auth
    result = require_auth("metrics")
    assert callable(result)


def test_scope_to_permission_keys():
    from mcp_server.security.security_middleware import _SCOPE_TO_PERMISSION
    assert set(_SCOPE_TO_PERMISSION) == {"metrics", "admin", "tools"}


def test_scope_to_permission_values():
    from mcp_server.security.security_middleware import _SCOPE_TO_PERMISSION
    from mcp_server.security.models import Permission
    assert _SCOPE_TO_PERMISSION["metrics"] == Permission.ADMIN
    assert _SCOPE_TO_PERMISSION["admin"] == Permission.ADMIN
    assert _SCOPE_TO_PERMISSION["tools"] == Permission.READ


# ---------------------------------------------------------------------------
# IF-0-P15-3: attestation
# ---------------------------------------------------------------------------

def test_attestation_importable():
    from mcp_server.artifacts.attestation import Attestation
    assert Attestation is not None


def test_attestation_fields():
    from mcp_server.artifacts.attestation import Attestation
    field_names = {f.name for f in dataclasses.fields(Attestation)}
    assert field_names == {"bundle_url", "bundle_path", "subject_digest", "signed_at"}


def test_attestation_error_importable():
    from mcp_server.artifacts.attestation import AttestationError
    from mcp_server.core.errors import ArtifactError
    assert issubclass(AttestationError, ArtifactError)


def test_attest_importable():
    from mcp_server.artifacts.attestation import attest
    assert callable(attest)


def test_attest_skip_mode_returns_attestation():
    import os
    from unittest.mock import patch
    from mcp_server.artifacts.attestation import attest, Attestation
    from pathlib import Path
    with patch.dict(os.environ, {"MCP_ATTESTATION_MODE": "skip"}):
        result = attest(Path("/tmp/fake.tar.gz"), repo="org/repo")
    assert isinstance(result, Attestation)


def test_verify_attestation_importable():
    from mcp_server.artifacts.attestation import verify_attestation
    assert callable(verify_attestation)


def test_verify_attestation_skip_mode_no_ops():
    import os
    from unittest.mock import patch
    from mcp_server.artifacts.attestation import verify_attestation, Attestation
    from pathlib import Path
    from datetime import datetime, timezone
    att = Attestation(bundle_url="", bundle_path=Path(""), subject_digest="", signed_at=datetime.now(timezone.utc))
    with patch.dict(os.environ, {"MCP_ATTESTATION_MODE": "skip"}):
        result = verify_attestation(Path("/tmp/fake.tar.gz"), att, expected_repo="org/repo")
    assert result is None


# ---------------------------------------------------------------------------
# IF-0-P15-4: path guard + token validator
# ---------------------------------------------------------------------------

def test_path_traversal_error_importable():
    from mcp_server.security.path_guard import PathTraversalError
    from mcp_server.core.errors import MCPError
    assert issubclass(PathTraversalError, MCPError)


def test_path_traversal_guard_importable():
    from mcp_server.security.path_guard import PathTraversalGuard
    assert PathTraversalGuard is not None


def test_path_traversal_guard_init_works():
    from mcp_server.security.path_guard import PathTraversalGuard
    from pathlib import Path
    # SL-4 filled the body; construction should succeed.
    guard = PathTraversalGuard([Path("/tmp")])
    assert guard is not None


def test_path_traversal_guard_normalize_signature():
    from mcp_server.security.path_guard import PathTraversalGuard
    sig = inspect.signature(PathTraversalGuard.normalize_and_check)
    assert "p" in sig.parameters


def test_insufficient_scopes_error_importable():
    from mcp_server.security.token_validator import InsufficientScopesError
    from mcp_server.core.errors import MCPError
    assert issubclass(InsufficientScopesError, MCPError)


def test_token_validator_importable():
    from mcp_server.security.token_validator import TokenValidator
    assert TokenValidator is not None


def test_token_validator_validate_scopes_signature():
    from mcp_server.security.token_validator import TokenValidator
    sig = inspect.signature(TokenValidator.validate_scopes)
    params = sig.parameters
    assert "required" in params
    assert "token" in params
    assert params["token"].default is None


def test_token_validator_no_token_no_require_flag():
    import os
    from mcp_server.security.token_validator import TokenValidator
    # SL-4 filled the body; with no token and no require flag it should warn and return.
    env_backup = os.environ.pop("GITHUB_TOKEN", None)
    os.environ.pop("MCP_REQUIRE_TOKEN_SCOPES", None)
    try:
        result = TokenValidator.validate_scopes(["contents:read"])
        assert result is None
    finally:
        if env_backup is not None:
            os.environ["GITHUB_TOKEN"] = env_backup


# ---------------------------------------------------------------------------
# Lazy __getattr__ re-exports from mcp_server.sandbox
# ---------------------------------------------------------------------------

def test_sandbox_package_lazy_envelope():
    import mcp_server.sandbox as sandbox_pkg
    Envelope = sandbox_pkg.Envelope
    from mcp_server.sandbox.protocol import Envelope as DirectEnvelope
    assert Envelope is DirectEnvelope


def test_sandbox_package_lazy_capability_set():
    import mcp_server.sandbox as sandbox_pkg
    CapabilitySet = sandbox_pkg.CapabilitySet
    from mcp_server.sandbox.capabilities import CapabilitySet as DirectCapabilitySet
    assert CapabilitySet is DirectCapabilitySet


def test_sandbox_package_lazy_unknown_raises():
    import mcp_server.sandbox as sandbox_pkg
    with pytest.raises(AttributeError):
        _ = sandbox_pkg.NonExistentSymbol
