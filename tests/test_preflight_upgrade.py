"""Tests for the preflight_env CLI subcommand (SL-4)."""

from pathlib import Path

import pytest
from click.testing import CliRunner

FIXTURES = Path(__file__).parent / "fixtures"


def _get_cli():
    from mcp_server.cli.__main__ import _cli
    return _cli


# (a) No args → usage line printed, non-zero exit
def test_preflight_env_no_args_prints_usage():
    cli = _get_cli()
    runner = CliRunner()
    result = runner.invoke(cli, ["preflight_env"])
    assert result.exit_code != 0
    assert "Usage" in result.output


# (b) Happy-path env → exit 0, no [FATAL]/[WARN] output
def test_preflight_env_happy_path_exits_zero():
    cli = _get_cli()
    runner = CliRunner()
    env_file = FIXTURES / "preflight_happy.env"
    result = runner.invoke(cli, ["preflight_env", str(env_file)])
    assert result.exit_code == 0, f"output={result.output!r}"
    assert "[FATAL]" not in result.output
    assert "[WARN]" not in result.output


# (c) Fatal env → exit 1, [FATAL] on stderr/output
def test_preflight_env_fatal_exits_one():
    cli = _get_cli()
    runner = CliRunner()
    env_file = FIXTURES / "preflight_fatal.env"
    result = runner.invoke(cli, ["preflight_env", str(env_file)])
    assert result.exit_code == 1, f"output={result.output!r}"
    assert "[FATAL]" in result.output


# (d) Warn-only env → exit 0, [WARN] on stderr/output
def test_preflight_env_warn_only_exits_zero(tmp_path):
    """Staging env with weak JWT emits WARN but not FATAL → exit 0."""
    warn_env = tmp_path / "preflight_warn.env"
    # changeme prefix triggers WEAK_JWT_SECRET as 'warn' (staging, not production)
    warn_env.write_text(
        "JWT_SECRET_KEY=changeme_padding_to_32_chars_xxxxxxxxx\n"
        "CORS_ORIGINS=https://example.com\n"
        "RATE_LIMIT_REQUESTS=100\n"
        "MCP_ENVIRONMENT=staging\n"
    )
    cli = _get_cli()
    runner = CliRunner()
    result = runner.invoke(cli, ["preflight_env", str(warn_env)])
    assert result.exit_code == 0, f"output={result.output!r}"
    assert "[WARN]" in result.output
