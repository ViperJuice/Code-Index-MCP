"""Coverage evidence artifact checks."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ARTIFACT = REPO / "docs" / "status" / "coverage-evidence.md"


def test_coverage_evidence_artifact_records_required_metadata() -> None:
    text = ARTIFACT.read_text(encoding="utf-8")
    for phrase in (
        "Audit date:",
        "Baseline command:",
        "coverage.xml generation:",
        "Terminal missing-line summary:",
        "Existing threshold posture:",
        "Guard result:",
        "Workflow upload decision:",
        "README badge decision:",
        "Verification commands",
    ):
        assert phrase in text


def test_coverage_evidence_artifact_records_threshold_decision() -> None:
    text = ARTIFACT.read_text(encoding="utf-8")
    assert "--cov-fail-under=80 enforced" in text or "threshold ramp deferred" in text
