"""Coverage command contract checks."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MAKEFILE = REPO / "Makefile"


def _read_makefile() -> str:
    return MAKEFILE.read_text(encoding="utf-8")


def test_makefile_exposes_coverage_targets() -> None:
    text = _read_makefile()
    for target in ("coverage:", "coverage-baseline:", "coverage-artifact-guard:"):
        assert target in text


def test_coverage_commands_emit_terminal_and_xml_reports_without_forcing_80() -> None:
    text = _read_makefile()
    assert "$(UV_RUN) --extra dev pytest" in text
    assert "--cov=mcp_server" in text
    assert "--cov-report=term-missing" in text
    assert "--cov-report=xml" in text
    assert "--cov-fail-under=80" not in text


def test_agent_validation_surface_owns_guard_and_coverage_generation() -> None:
    text = _read_makefile()
    assert "agent-fast-local: alpha-dependency-sync coverage-artifact-guard" in text
    assert "agent-gate-local: agent-fast-local" in text
    assert "agent-full-local: agent-gate-local coverage" in text
