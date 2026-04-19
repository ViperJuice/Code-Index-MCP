"""Tests for gh api rate-limit backoff in GitHubActionsArtifactProvider."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from mcp_server.artifacts.providers.github_actions import (
    GitHubActionsArtifactProvider,
    _respect_rate_limit,
)


def _make_run_result(header_block: str, body: str, returncode: int = 0) -> MagicMock:
    result = MagicMock()
    result.returncode = returncode
    result.stdout = header_block + "\r\n\r\n" + body
    result.stderr = ""
    return result


def test_rate_limit_remaining_low_sleeps():
    """When X-RateLimit-Remaining is 50, time.sleep should be called."""
    future_reset = str(int(time.time()) + 30)
    header_block = (
        "HTTP/1.1 200 OK\r\n"
        f"X-RateLimit-Remaining: 50\r\n"
        f"X-RateLimit-Reset: {future_reset}"
    )
    body = '{"artifacts": []}'
    fake_result = _make_run_result(header_block, body)

    with patch("subprocess.run", return_value=fake_result), \
         patch("time.sleep") as mock_sleep:
        provider = GitHubActionsArtifactProvider("org/repo")
        provider.list_artifacts(prefixes=("code-index-",))

    mock_sleep.assert_called_once()
    args, _ = mock_sleep.call_args
    assert args[0] > 0


def test_rate_limit_remaining_high_no_sleep():
    """When X-RateLimit-Remaining is 5000, time.sleep should NOT be called."""
    header_block = (
        "HTTP/1.1 200 OK\r\n"
        "X-RateLimit-Remaining: 5000"
    )
    body = '{"artifacts": []}'
    fake_result = _make_run_result(header_block, body)

    with patch("subprocess.run", return_value=fake_result), \
         patch("time.sleep") as mock_sleep:
        provider = GitHubActionsArtifactProvider("org/repo")
        provider.list_artifacts(prefixes=("code-index-",))

    mock_sleep.assert_not_called()


def test_respect_rate_limit_no_header_no_sleep():
    """Missing header defaults to 5000 — no sleep."""
    with patch("time.sleep") as mock_sleep:
        _respect_rate_limit({})
    mock_sleep.assert_not_called()


def test_respect_rate_limit_returns_sleep_duration():
    future_reset = str(int(time.time()) + 10)
    headers = {"X-RateLimit-Remaining": "50", "X-RateLimit-Reset": future_reset}
    with patch("time.sleep"):
        duration = _respect_rate_limit(headers)
    assert duration > 0


def test_respect_rate_limit_caps_at_300s():
    """Sleep is capped at 300 seconds even if reset is far in future."""
    far_future = str(int(time.time()) + 3600)
    headers = {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": far_future}
    with patch("time.sleep") as mock_sleep:
        duration = _respect_rate_limit(headers)
    assert duration == 300.0
    mock_sleep.assert_called_once_with(300.0)


def test_delete_artifact_rate_limit_applied():
    """delete_artifact also goes through _gh_api and obeys rate-limit."""
    future_reset = str(int(time.time()) + 5)
    header_block = (
        "HTTP/1.1 204 No Content\r\n"
        f"X-RateLimit-Remaining: 50\r\n"
        f"X-RateLimit-Reset: {future_reset}"
    )
    fake_result = _make_run_result(header_block, "")

    with patch("subprocess.run", return_value=fake_result), \
         patch("time.sleep") as mock_sleep:
        provider = GitHubActionsArtifactProvider("org/repo")
        result = provider.delete_artifact("12345")

    assert result is True
    mock_sleep.assert_called_once()
