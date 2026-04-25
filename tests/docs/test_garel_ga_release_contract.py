"""GAREL GA decision and release contract checks."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).parent.parent.parent

GA_CHECKLIST = REPO / "docs" / "validation" / "ga-readiness-checklist.md"
GA_GOVERNANCE = REPO / "docs" / "validation" / "ga-governance-evidence.md"
GA_E2E = REPO / "docs" / "validation" / "ga-e2e-evidence.md"
GA_OPS = REPO / "docs" / "validation" / "ga-operations-evidence.md"
GA_RC = REPO / "docs" / "validation" / "ga-rc-evidence.md"
GA_FINAL = REPO / "docs" / "validation" / "ga-final-decision.md"
GA_RELEASE = REPO / "docs" / "validation" / "ga-release-evidence.md"
ROADMAP = REPO / "specs" / "phase-plans-v5.md"
WORKFLOW = REPO / ".github" / "workflows" / "release-automation.yml"
README = REPO / "README.md"
GETTING_STARTED = REPO / "docs" / "GETTING_STARTED.md"
MCP_CONFIGURATION = REPO / "docs" / "MCP_CONFIGURATION.md"
DOCKER_GUIDE = REPO / "docs" / "DOCKER_GUIDE.md"
SUPPORT_MATRIX = REPO / "docs" / "SUPPORT_MATRIX.md"
DEPLOYMENT_RUNBOOK = REPO / "docs" / "operations" / "deployment-runbook.md"
USER_ACTION_RUNBOOK = REPO / "docs" / "operations" / "user-action-runbook.md"

PUBLIC_SURFACES = (
    README,
    GETTING_STARTED,
    MCP_CONFIGURATION,
    DOCKER_GUIDE,
    SUPPORT_MATRIX,
    DEPLOYMENT_RUNBOOK,
    USER_ACTION_RUNBOOK,
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_final_decision_exists_and_cites_all_ga_inputs():
    checklist = _read(GA_CHECKLIST)
    governance = _read(GA_GOVERNANCE)
    e2e = _read(GA_E2E)
    ops = _read(GA_OPS)
    rc = _read(GA_RC)
    decision = _read(GA_FINAL)

    assert decision.startswith("> **Historical artifact")
    assert "docs/validation/ga-final-decision.md" in checklist
    assert "enforced via branch protection" in governance
    assert "ready" in e2e
    assert "plans/phase-plan-v5-gaops.md" in ops
    assert "follow-up RC soak succeeded" in rc

    for expected in (
        "# GA Final Decision",
        "## Summary",
        "## Decision Inputs",
        "## Workflow Runtime Disposition",
        "## Final Decision",
        "## Next Scope",
        "## Verification",
        "cut another RC",
        "docs/validation/ga-readiness-checklist.md",
        "docs/validation/ga-governance-evidence.md",
        "docs/validation/ga-e2e-evidence.md",
        "docs/validation/ga-operations-evidence.md",
        "docs/validation/ga-rc-evidence.md",
        "v1.2.0-rc7",
        "v1.2.0-rc8",
        "peter-evans/create-pull-request@v8",
        "softprops/action-gh-release@v3",
        "Node 20",
        "specs/phase-plans-v5.md",
        "GARECUT",
    ):
        assert expected in decision

    assert "- Final decision: `ship GA`." not in decision
    assert "- Final decision: `defer GA`." not in decision


def test_non_ship_decision_keeps_ga_release_evidence_absent_and_public_surfaces_pre_ga():
    decision = _read(GA_FINAL)

    assert "ga-release-evidence.md`" in decision
    assert "remains intentionally absent" in decision
    assert not GA_RELEASE.exists()

    combined = "\n".join(_read(path) for path in PUBLIC_SURFACES).lower()
    for expected in ("public-alpha", "beta", "github latest", "docker `latest`"):
        assert expected in combined

    for forbidden in ("ship ga", "generally available"):
        assert forbidden not in combined


def test_workflow_runtime_warning_is_remediated_before_any_future_ga_dispatch():
    workflow = _read(WORKFLOW)
    decision = _read(GA_FINAL)
    roadmap = _read(ROADMAP)

    assert "peter-evans/create-pull-request@v8" in workflow
    assert "peter-evans/create-pull-request@v7" not in workflow
    assert "softprops/action-gh-release@v3" in workflow
    assert "softprops/action-gh-release@v2" not in workflow
    assert "the immediate next step is rerunning GARECUT" in decision.replace("\n", " ")
    assert "Current recut outcome: `blocked before dispatch`" in decision
    assert "### Phase 8 — Post-Remediation RC Recut (GARECUT)" in roadmap
    assert "softprops/action-gh-release@v3" in roadmap
