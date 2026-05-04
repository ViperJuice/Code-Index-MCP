"""MCPEVAL evidence reducer contract tests."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
EVALUATION = REPO / "docs" / "status" / "MCP_COMPATIBILITY_EVALUATION.md"


def test_mcpeval_evaluation_doc_has_required_sections() -> None:
    text = EVALUATION.read_text(encoding="utf-8")
    for expected in (
        "## Scope",
        "## Observed client evidence",
        "## Compatibility matrix",
        "## Prompt-pack coverage",
        "## Unsupported or deferred surfaces",
        "## Verification commands",
    ):
        assert expected in text


def test_mcpeval_evaluation_doc_points_to_phase_owned_evidence() -> None:
    text = EVALUATION.read_text(encoding="utf-8")
    for expected in (
        "tests/smoke/test_mcpeval_sdk_surface.py",
        "docs/evaluations/mcpeval-prompt-pack.md",
        "index_unavailable",
        'safe_fallback: "native_search"',
        "tasks/get",
        "tasks/result",
        "MCP_CLIENT_SECRET",
    ):
        assert expected in text
