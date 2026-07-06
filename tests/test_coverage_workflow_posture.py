"""Coverage workflow posture checks."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
WORKFLOW = REPO / ".github" / "workflows" / "ci-cd-pipeline.yml"


def test_pull_requests_keep_existing_agent_gate_without_coverage_uploads() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "pull_request:" in text
    assert "make agent-gate" in text
    assert "codecov" not in text.lower()
    assert "coverage.xml" not in text
    assert "coverage-report" not in text


def test_no_coverage_specific_hosted_matrix_expansion_is_added() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "matrix:" in text
    assert "coverage" not in text.split("informational-test-cross-platform", maxsplit=1)[0]
