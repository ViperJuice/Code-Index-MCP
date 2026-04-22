"""Tests for artifact attestation — attest() and verify_attestation() (SL-2.2)."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mcp_server.artifacts.attestation import (
    Attestation,
    AttestationError,
    attest,
    verify_attestation,
)

FAKE_ARCHIVE = Path("/tmp/fake_archive.tar.gz")
REPO = "owner/repo"


@pytest.fixture(autouse=True)
def _stub_sha256(monkeypatch):
    monkeypatch.setattr("mcp_server.artifacts.attestation._sha256_of", lambda p: "sha256stub")


class TestAttestSkipMode:
    def test_skip_mode_returns_empty_attestation(self, monkeypatch):
        monkeypatch.setenv("MCP_ATTESTATION_MODE", "skip")
        result = attest(FAKE_ARCHIVE, repo=REPO)
        assert result.bundle_url == ""
        assert result.subject_digest == ""

    def test_skip_mode_no_subprocess(self, monkeypatch):
        monkeypatch.setenv("MCP_ATTESTATION_MODE", "skip")
        with patch("subprocess.run") as mock_run:
            attest(FAKE_ARCHIVE, repo=REPO)
        mock_run.assert_not_called()


class TestAttestEnforceMode:
    def test_enforce_mode_raises_on_sign_failure(self, monkeypatch):
        monkeypatch.setenv("MCP_ATTESTATION_MODE", "enforce")

        def fake_run(args, **kwargs):
            if "auth" in args and "status" in args:
                return MagicMock(returncode=0, stdout="attestations:write", stderr="")
            return MagicMock(returncode=1, stdout="", stderr="signing failed")

        with patch("subprocess.run", side_effect=fake_run):
            with pytest.raises(AttestationError):
                attest(FAKE_ARCHIVE, repo=REPO)

    def test_enforce_mode_returns_attestation_on_success(self, monkeypatch):
        monkeypatch.setenv("MCP_ATTESTATION_MODE", "enforce")

        def fake_run(args, **kwargs):
            if "auth" in args and "status" in args:
                return MagicMock(returncode=0, stdout="attestations:write", stderr="")
            return MagicMock(
                returncode=0,
                stdout="https://github.com/owner/repo/attestations/abc123",
                stderr="",
            )

        with patch("subprocess.run", side_effect=fake_run):
            result = attest(FAKE_ARCHIVE, repo=REPO)

        assert "github.com" in result.bundle_url
        assert result.subject_digest == "sha256stub"


class TestAttestWarnMode:
    def test_warn_mode_logs_on_sign_failure(self, monkeypatch, caplog):
        monkeypatch.setenv("MCP_ATTESTATION_MODE", "warn")
        import logging

        def fake_run(args, **kwargs):
            if "auth" in args and "status" in args:
                return MagicMock(returncode=0, stdout="attestations:write", stderr="")
            return MagicMock(returncode=1, stdout="", stderr="not supported")

        with patch("subprocess.run", side_effect=fake_run):
            with caplog.at_level(logging.WARNING, logger="mcp_server.artifacts.attestation"):
                result = attest(FAKE_ARCHIVE, repo=REPO)

        assert result is not None
        assert any("failed" in r.message.lower() for r in caplog.records)


class TestVerifyAttestation:
    def test_skip_mode_no_verify(self, monkeypatch):
        monkeypatch.setenv("MCP_ATTESTATION_MODE", "skip")
        att = Attestation(
            bundle_url="",
            bundle_path=Path("/tmp/fake.jsonl"),
            subject_digest="sha256stub",
            signed_at=datetime.now(timezone.utc),
        )
        with patch("subprocess.run") as mock_run:
            verify_attestation(FAKE_ARCHIVE, att, expected_repo=REPO)
        mock_run.assert_not_called()

    def test_enforce_mode_raises_on_verify_failure(self, monkeypatch):
        monkeypatch.setenv("MCP_ATTESTATION_MODE", "enforce")
        att = Attestation(
            bundle_url="https://github.com/owner/repo/attestations/1",
            bundle_path=Path("/tmp/fake.jsonl"),
            subject_digest="sha256stub",
            signed_at=datetime.now(timezone.utc),
        )
        with patch(
            "subprocess.run",
            return_value=MagicMock(returncode=1, stdout="", stderr="verify failed"),
        ):
            with pytest.raises(AttestationError):
                verify_attestation(FAKE_ARCHIVE, att, expected_repo=REPO)

    def test_warn_mode_logs_on_verify_failure(self, monkeypatch, caplog):
        monkeypatch.setenv("MCP_ATTESTATION_MODE", "warn")
        import logging

        att = Attestation(
            bundle_url="https://github.com/owner/repo/attestations/1",
            bundle_path=Path("/tmp/fake.jsonl"),
            subject_digest="sha256stub",
            signed_at=datetime.now(timezone.utc),
        )
        with patch(
            "subprocess.run", return_value=MagicMock(returncode=1, stdout="", stderr="fail")
        ):
            with caplog.at_level(logging.WARNING, logger="mcp_server.artifacts.attestation"):
                verify_attestation(FAKE_ARCHIVE, att, expected_repo=REPO)

        assert any(r.levelno >= logging.WARNING for r in caplog.records)
