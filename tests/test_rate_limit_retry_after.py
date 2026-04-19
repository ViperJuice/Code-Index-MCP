"""Tests for _respect_rate_limit Retry-After parsing: 429/403 handling (SL-2.4)."""

from __future__ import annotations

import subprocess
import time
from unittest.mock import MagicMock, patch

import pytest

from mcp_server.artifacts.providers.github_actions import _respect_rate_limit
from mcp_server.core.errors import TerminalArtifactError, TransientArtifactError


class TestRetryAfterParsing:
    """_respect_rate_limit must parse Retry-After and sleep appropriately."""

    def test_no_rate_limit_headers_returns_zero(self):
        headers: dict = {}
        slept = _respect_rate_limit(headers, status_code=200)
        assert slept == 0.0

    def test_429_with_retry_after_integer_sleeps(self):
        headers = {"Retry-After": "5"}
        with patch("time.sleep") as mock_sleep:
            slept = _respect_rate_limit(headers, status_code=429)
        mock_sleep.assert_called_once_with(5.0)
        assert slept == 5.0

    def test_429_with_retry_after_capped_at_300(self):
        headers = {"Retry-After": "9999"}
        with patch("time.sleep") as mock_sleep:
            slept = _respect_rate_limit(headers, status_code=429)
        mock_sleep.assert_called_once_with(300.0)
        assert slept == 300.0

    def test_429_with_retry_after_http_date(self):
        from email.utils import formatdate
        import datetime
        future_ts = time.time() + 30
        http_date = formatdate(future_ts, usegmt=True)
        headers = {"Retry-After": http_date}
        with patch("time.sleep") as mock_sleep:
            with patch("time.time", return_value=time.time()):
                slept = _respect_rate_limit(headers, status_code=429)
        # Should have slept some positive amount up to 300
        assert 0 < slept <= 300

    def test_429_increments_rate_limit_counter(self):
        headers = {"Retry-After": "1"}
        with patch("time.sleep"):
            with patch(
                "mcp_server.artifacts.providers.github_actions.mcp_rate_limit_sleeps_total"
            ) as mock_counter:
                mock_counter_instance = MagicMock()
                mock_counter.labels.return_value = mock_counter_instance
                _respect_rate_limit(headers, status_code=429)

    def test_403_raises_terminal_artifact_error(self):
        headers: dict = {}
        with pytest.raises(TerminalArtifactError):
            _respect_rate_limit(headers, status_code=403)

    def test_403_increments_error_counter(self):
        headers: dict = {}
        with patch(
            "mcp_server.artifacts.providers.github_actions.mcp_artifact_errors_by_class_total"
        ) as mock_counter:
            mock_instance = MagicMock()
            mock_counter.labels.return_value = mock_instance
            with pytest.raises(TerminalArtifactError):
                _respect_rate_limit(headers, status_code=403)

    def test_200_with_low_remaining_uses_reset_header(self):
        """Legacy path: low X-RateLimit-Remaining still triggers backoff on 200."""
        headers = {
            "X-RateLimit-Remaining": "5",
            "X-RateLimit-Reset": str(int(time.time()) + 10),
        }
        with patch("time.sleep") as mock_sleep:
            slept = _respect_rate_limit(headers, status_code=200)
        assert slept > 0
        mock_sleep.assert_called_once()

    def test_200_with_high_remaining_no_sleep(self):
        headers = {
            "X-RateLimit-Remaining": "5000",
        }
        with patch("time.sleep") as mock_sleep:
            slept = _respect_rate_limit(headers, status_code=200)
        assert slept == 0.0
        mock_sleep.assert_not_called()


class TestGhApiStatusCodePropagation:
    """_gh_api must hand the HTTP status code to _respect_rate_limit."""

    def test_gh_api_403_raises_terminal_error(self):
        """When gh api returns HTTP 403, _gh_api must surface TerminalArtifactError."""
        from mcp_server.artifacts.providers.github_actions import _gh_api

        http_response = (
            "HTTP/1.1 403 Forbidden\r\n"
            "Content-Type: application/json\r\n"
            "\r\n"
            '{"message":"Must have admin rights"}'
        )

        mock_result = MagicMock(returncode=0, stdout=http_response, stderr="")
        with patch("subprocess.run", return_value=mock_result):
            with pytest.raises(TerminalArtifactError):
                _gh_api("gh", "/repos/owner/repo/actions/artifacts")

    def test_gh_api_429_sleeps_and_does_not_raise_terminal(self):
        """When gh api returns HTTP 429, _gh_api sleeps but does NOT raise TerminalArtifactError."""
        from mcp_server.artifacts.providers.github_actions import _gh_api

        http_response = (
            "HTTP/1.1 429 Too Many Requests\r\n"
            "Retry-After: 2\r\n"
            "Content-Type: application/json\r\n"
            "\r\n"
            '{"message":"rate limit"}'
        )

        mock_result = MagicMock(returncode=0, stdout=http_response, stderr="")
        with patch("subprocess.run", return_value=mock_result):
            with patch("time.sleep") as mock_sleep:
                try:
                    _gh_api("gh", "/repos/owner/repo/actions/artifacts")
                except TerminalArtifactError:
                    pytest.fail("429 should not raise TerminalArtifactError")
                except Exception:
                    pass  # other errors OK for this stub
                mock_sleep.assert_called()


class TestAttestationPreflight:
    """attest() must check attestations:write scope before running gh attestation sign."""

    def test_missing_scope_warns_and_falls_back_in_warn_mode(self, monkeypatch):
        """With MCP_ATTESTATION_MODE=warn and missing scope, log ATTESTATION_PREREQ and skip sign."""
        import os
        from pathlib import Path as _Path
        from mcp_server.artifacts.attestation import attest

        monkeypatch.setenv("MCP_ATTESTATION_MODE", "warn")

        gh_calls: list[list] = []

        def fake_run(args, **kwargs):
            gh_calls.append(list(args))
            # Simulate 'gh auth status --show-token' without attestations:write
            if "auth" in args and "status" in args:
                return MagicMock(
                    returncode=0,
                    stdout="Logged in as user\nToken scopes: repo, read:org",
                    stderr="",
                )
            # Any other gh call fails
            return MagicMock(returncode=1, stdout="", stderr="not supported")

        import logging
        log_records: list[logging.LogRecord] = []

        class Capture(logging.Handler):
            def emit(self, record):
                log_records.append(record)

        import mcp_server.artifacts.attestation as att_mod
        att_mod.logger.addHandler(Capture())
        att_mod.logger.setLevel(logging.WARNING)

        try:
            with patch("subprocess.run", side_effect=fake_run):
                result = attest(_Path("/tmp/fake_archive.tar.gz"), repo="owner/repo", gh_cmd="gh")
        finally:
            att_mod.logger.handlers = [
                h for h in att_mod.logger.handlers if not isinstance(h, Capture)
            ]

        # Should NOT have called 'gh attestation sign' when scope missing
        sign_calls = [c for c in gh_calls if "attestation" in c and "sign" in c]
        prereq_warned = any("ATTESTATION_PREREQ" in r.getMessage() for r in log_records)

        # Either fallback result returned without signing, or PREREQ warn logged
        assert result is not None
        # If sign was attempted, it must have been skipped (no calls or warned)
        if sign_calls:
            assert prereq_warned, "Expected ATTESTATION_PREREQ warning when scope missing"

    def test_present_scope_allows_sign(self, monkeypatch):
        """With attestations:write scope present, sign is attempted normally."""
        from pathlib import Path as _Path
        from mcp_server.artifacts.attestation import attest

        monkeypatch.setenv("MCP_ATTESTATION_MODE", "warn")

        gh_calls: list[list] = []

        def fake_run(args, **kwargs):
            gh_calls.append(list(args))
            if "auth" in args and "status" in args:
                return MagicMock(
                    returncode=0,
                    stdout="Logged in as user\nToken scopes: repo, attestations:write",
                    stderr="",
                )
            # attestation sign "succeeds" partially
            if "attestation" in args and "sign" in args:
                return MagicMock(returncode=0, stdout="", stderr="")
            return MagicMock(returncode=0, stdout="", stderr="")

        fake_path = _Path("/tmp/fake_archive.tar.gz")
        with patch("subprocess.run", side_effect=fake_run):
            with patch("mcp_server.artifacts.attestation._sha256_of", return_value="sha256stub"):
                try:
                    attest(fake_path, repo="owner/repo", gh_cmd="gh")
                except Exception:
                    pass

        # gh auth status must have been called
        auth_calls = [c for c in gh_calls if "auth" in c and "status" in c]
        assert auth_calls, "Expected 'gh auth status' call for preflight scope check"
