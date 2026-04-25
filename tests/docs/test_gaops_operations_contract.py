"""GAOPS operational readiness contract checks."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).parent.parent.parent

CHECKLIST = REPO / "docs" / "validation" / "ga-readiness-checklist.md"
GA_GOVERNANCE = REPO / "docs" / "validation" / "ga-governance-evidence.md"
GA_E2E = REPO / "docs" / "validation" / "ga-e2e-evidence.md"
GA_OPS = REPO / "docs" / "validation" / "ga-operations-evidence.md"
DEPLOYMENT_RUNBOOK = REPO / "docs" / "operations" / "deployment-runbook.md"
USER_ACTION_RUNBOOK = REPO / "docs" / "operations" / "user-action-runbook.md"
OBSERVABILITY = REPO / "docs" / "operations" / "observability-verification.md"
DEPLOYMENT_GUIDE = REPO / "docs" / "DEPLOYMENT-GUIDE.md"
PRODUCTION_GUIDE = REPO / "docs" / "PRODUCTION_DEPLOYMENT_GUIDE.md"
PREFLIGHT_SCRIPT = REPO / "scripts" / "preflight_upgrade.sh"

RUNBOOK_HEADINGS = [
    "## GAOPS Operator Procedure Contract",
    "### Deployment preflight",
    "### Deployment qualification",
    "### Rollback and containment",
    "### Index rebuild and readiness remediation",
    "### Incident response",
    "### Support triage boundary",
]

USER_ACTION_HEADINGS = [
    "### 3.10 Phase GAOPS - GA Operational Readiness",
    "#### Before GAOPS",
    "#### During GAOPS",
    "#### After GAOPS",
]

FORBIDDEN_GUIDE_CLAIMS = [
    "blue-green deployment",
    "kubernetes",
    "helm",
    "docker swarm",
    "multi-region",
]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def test_gaops_runbooks_define_operator_sections_and_canonical_sources():
    runbook = _read(DEPLOYMENT_RUNBOOK)
    user_actions = _read(USER_ACTION_RUNBOOK)

    for heading in RUNBOOK_HEADINGS:
        assert heading in runbook

    for heading in USER_ACTION_HEADINGS:
        assert heading in user_actions

    for path in (DEPLOYMENT_RUNBOOK, USER_ACTION_RUNBOOK):
        text = _read(path)
        for expected in (
            "docs/validation/ga-readiness-checklist.md",
            "docs/validation/ga-governance-evidence.md",
            "docs/validation/ga-e2e-evidence.md",
            "docs/validation/ga-operations-evidence.md",
            "local-first",
            "index rebuild",
            "incident response",
            "support triage",
            "v1.2.0-rc8",
        ):
            assert expected in text, f"{path.relative_to(REPO)} missing {expected!r}"


def test_observability_doc_and_preflight_script_share_the_same_operator_contract():
    observability = _read(OBSERVABILITY)
    script = _read(PREFLIGHT_SCRIPT)

    assert "./scripts/preflight_upgrade.sh /path/to/staging.env" in observability
    assert "Authorization: Bearer <token>" in observability
    assert "metadata-only" in observability
    assert "CI-validated" in observability
    assert "/metrics endpoint requires ADMIN-level authentication" in observability
    assert 'exec "$PYTHON" -m mcp_server.cli preflight_env "$1"' in script
    assert "Usage: ./scripts/preflight_upgrade.sh <env_file_path>" in script

    assert "bash scripts/preflight_upgrade.sh" not in _read(DEPLOYMENT_RUNBOOK)


def test_deployment_guides_route_readers_to_supported_local_first_surfaces_only():
    for path in (DEPLOYMENT_GUIDE, PRODUCTION_GUIDE):
        text = _read(path)
        lowered = text.lower()

        for expected in (
            "docs/validation/ga-readiness-checklist.md",
            "docs/operations/deployment-runbook.md",
            "docs/operations/observability-verification.md",
            "docs/validation/ga-operations-evidence.md",
            "local-first",
            "supported deployment surfaces",
            "operator-owned",
            "rollback",
            "observability",
        ):
            assert expected in text, f"{path.relative_to(REPO)} missing {expected!r}"

        for forbidden in FORBIDDEN_GUIDE_CLAIMS:
            assert forbidden not in lowered, f"{path.relative_to(REPO)} contains {forbidden!r}"


def test_gaops_evidence_artifact_exists_and_records_validation_modes():
    checklist = _read(CHECKLIST)
    governance = _read(GA_GOVERNANCE)
    e2e = _read(GA_E2E)
    text = _read(GA_OPS)

    assert "docs/validation/ga-operations-evidence.md" in checklist
    assert "enforced via branch protection" in governance
    assert "ready" in e2e

    for expected in (
        "# GA Operations Evidence",
        "## Summary",
        "## Procedure Validation Matrix",
        "## Supported Deployment Surface",
        "## Remaining Limitations",
        "## Verification",
        "plans/phase-plan-v5-gaops.md",
        "docs/validation/ga-readiness-checklist.md",
        "docs/validation/ga-governance-evidence.md",
        "docs/validation/ga-e2e-evidence.md",
        "`local`",
        "`CI`",
        "`metadata-only`",
        "`deployment preflight`",
        "`deployment qualification`",
        "`rollback`",
        "`index rebuild`",
        "`incident response`",
        "`support triage`",
    ):
        assert expected in text

    for forbidden in ("ship GA", "Authorization: Bearer", "gho_", '"password":'):
        assert forbidden not in text


def test_gaops_artifacts_keep_historical_banner_and_local_first_vocabulary():
    for path in (GA_OPS, GA_GOVERNANCE, GA_E2E):
        assert _read(path).startswith("> **Historical artifact"), path

    combined = "\n".join(
        [
            _normalized(DEPLOYMENT_RUNBOOK),
            _normalized(USER_ACTION_RUNBOOK),
            _normalized(DEPLOYMENT_GUIDE),
            _normalized(PRODUCTION_GUIDE),
            _normalized(OBSERVABILITY),
            _normalized(GA_OPS),
        ]
    )

    for expected in (
        "one registered worktree per git common directory",
        "tracked/default branch",
        'safe_fallback: "native_search"',
        "public-alpha",
        "beta",
        "GA",
        "experimental",
        "unsupported",
        "disabled-by-default",
        "metadata-only",
    ):
        assert expected in combined
