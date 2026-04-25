"""GARECUT post-remediation RC recut contract checks."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).parent.parent.parent

GA_CHECKLIST = REPO / "docs" / "validation" / "ga-readiness-checklist.md"
GA_RC = REPO / "docs" / "validation" / "ga-rc-evidence.md"
GA_FINAL = REPO / "docs" / "validation" / "ga-final-decision.md"
ROADMAP = REPO / "specs" / "phase-plans-v5.md"
WORKFLOW = REPO / ".github" / "workflows" / "release-automation.yml"
RELEASE_METADATA = REPO / "tests" / "test_release_metadata.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_rc7_contract_surfaces_and_workflow_path_are_frozen():
    workflow = _read(WORKFLOW)
    release_metadata = _read(RELEASE_METADATA)

    for expected in ("v1.2.0-rc7", "1.2.0-rc7", "peter-evans/create-pull-request@v8"):
        assert expected in workflow

    for expected in ("v1.2.0-rc7", "1.2.0-rc7", "release_type=custom"):
        assert expected in release_metadata

    assert "peter-evans/create-pull-request@v7" not in workflow
    assert "latest" in workflow


def test_ga_rc_evidence_is_the_canonical_recut_artifact():
    checklist = _read(GA_CHECKLIST)
    evidence = _read(GA_RC)

    assert "docs/validation/ga-rc-evidence.md" in checklist
    assert evidence.startswith("> **Historical artifact")

    for expected in (
        "# GA RC Evidence",
        "plans/phase-plan-v5-garecut.md",
        "v1.2.0-rc7",
        "Release Automation",
        "PyPI",
        "GHCR",
        "prerelease",
        "latest",
    ):
        assert expected in evidence

    assert (
        "blocked before dispatch" in evidence
        or "workflow failed after dispatch" in evidence
        or "recut succeeded" in evidence
    )


def test_final_decision_stays_historical_and_routes_to_the_next_phase_explicitly():
    decision = _read(GA_FINAL)
    roadmap = _read(ROADMAP)

    assert decision.startswith("> **Historical artifact")
    for expected in (
        "# GA Final Decision",
        "cut another RC",
        "GARECUT",
        "v1.2.0-rc7",
        "renewed GAREL",
        "blocked before dispatch",
    ):
        assert expected in decision

    assert "- Final decision: `ship GA`." not in decision
    assert "- Final decision: `defer GA`." not in decision
    assert "### Phase 8 — Post-Remediation RC Recut (GARECUT)" in roadmap
