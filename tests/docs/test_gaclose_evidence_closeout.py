"""GACLOSE evidence closeout documentation checks."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).parent.parent.parent

DECISION = REPO / "docs" / "validation" / "ga-closeout-decision.md"
RC5_EVIDENCE = REPO / "docs" / "validation" / "rc5-release-evidence.md"
RELGOV_EVIDENCE = REPO / "docs" / "validation" / "release-governance-evidence.md"
TOOLRDY_EVIDENCE = REPO / "docs" / "validation" / "secondary-tool-readiness-evidence.md"
SUPPORT_MATRIX = REPO / "docs" / "SUPPORT_MATRIX.md"
TRIAGE = REPO / "docs" / "HISTORICAL-ARTIFACTS-TRIAGE.md"

PUBLIC_ALPHA_VERSION = "1.2.0-rc5"
PUBLIC_ALPHA_TAG = "v1.2.0-rc5"
CURRENT_STABLE_VERSION = "1.2.0"
HISTORICAL_PUBLIC_ALPHA_VERSION = "1.2.0-rc8"
HISTORICAL_BANNER = "> **Historical artifact — as-of 2026-04-18, may not reflect current behavior**"

PUBLIC_SURFACES = [
    "README.md",
    "docs/GETTING_STARTED.md",
    "docs/DOCKER_GUIDE.md",
    "docs/MCP_CONFIGURATION.md",
    "CHANGELOG.md",
]

ALLOWED_DECISIONS = [
    "stay on RC/public-alpha",
    "cut a follow-up RC",
    "start a GA hardening roadmap",
]


def _read(relative: str | Path) -> str:
    path = REPO / relative if isinstance(relative, str) else relative
    return path.read_text(encoding="utf-8")


def _normalized(relative: str | Path) -> str:
    return " ".join(_read(relative).split())


def test_decision_artifact_links_prerequisite_evidence_and_verification():
    assert DECISION.exists(), "GACLOSE decision artifact must exist"
    text = _read(DECISION)

    for path in (RC5_EVIDENCE, RELGOV_EVIDENCE, TOOLRDY_EVIDENCE):
        assert path.exists(), f"missing prerequisite evidence: {path.relative_to(REPO)}"
        assert str(path.relative_to(REPO)) in text

    for expected in (
        "RC5 Release Evidence",
        "Release Governance Evidence",
        "Secondary Tool Readiness Evidence",
        "2026-04-24",
        "v1.2.0-rc5",
        "make alpha-production-matrix",
        "Result: passed",
    ):
        assert expected in text


def test_decision_artifact_states_exactly_one_allowed_decision():
    text = _read(DECISION)
    matches = [decision for decision in ALLOWED_DECISIONS if decision in text]

    assert matches == ["stay on RC/public-alpha"]
    assert "Final decision: `stay on RC/public-alpha`" in text
    assert "Next command: `codex-phase-roadmap-builder specs/phase-plans-v4.md`" in text


def test_active_release_surfaces_are_stable_prepared_and_not_latest_driven():
    failures = []
    for relative in PUBLIC_SURFACES:
        text = _read(relative)
        if CURRENT_STABLE_VERSION not in text:
            failures.append(f"{relative}: missing {CURRENT_STABLE_VERSION}")
        if relative == "CHANGELOG.md" and HISTORICAL_PUBLIC_ALPHA_VERSION not in text:
            failures.append(f"{relative}: missing historical {HISTORICAL_PUBLIC_ALPHA_VERSION}")
        if relative != "CHANGELOG.md" and "1.2.0-rc4" in text:
            failures.append(f"{relative}: active RC4 version reference")
        if "v1.2.0-rc4" in text:
            failures.append(f"{relative}: active RC4 tag reference")
        if "Download latest release" in text:
            failures.append(f"{relative}: latest-release download wording")
        if "GitHub Latest" in text and "not the RC policy source" not in text:
            failures.append(f"{relative}: GitHub Latest without RC policy disclaimer")

    assert failures == []


def test_support_matrix_freezes_claim_tiers_and_topology_limits():
    text = _normalized(SUPPORT_MATRIX)

    for expected in (
        "Claim tiers",
        "public-alpha",
        "Beta",
        "GA",
        "GA-supported",
        "not a GA support claim",
        "one registered worktree per git common directory",
        "tracked/default branch",
        "index_unavailable",
        'safe_fallback: "native_search"',
    ):
        assert expected in text

    for forbidden in (
        "unrestricted multi-worktree",
        "unrestricted multi-branch",
        "indexes every branch",
        "universal language/runtime support",
    ):
        assert forbidden not in text


def test_operator_runbooks_link_gaclose_prerequisites_and_decision_options():
    for relative in (
        "docs/operations/deployment-runbook.md",
        "docs/operations/user-action-runbook.md",
    ):
        text = _read(relative)
        normalized = " ".join(text.split())
        for expected in (
            "GACLOSE",
            "docs/validation/rc5-release-evidence.md",
            "docs/validation/release-governance-evidence.md",
            "docs/validation/secondary-tool-readiness-evidence.md",
            "docs/validation/ga-closeout-decision.md",
            "make alpha-production-matrix",
            "stay on RC/public-alpha",
            "cut a follow-up RC",
            "start a GA hardening roadmap",
            "manual enforcement",
        ):
            assert expected in normalized, f"{relative} missing {expected!r}"


def test_validation_artifacts_have_historical_banner_and_triage_rows():
    for path in (RC5_EVIDENCE, RELGOV_EVIDENCE, TOOLRDY_EVIDENCE, DECISION):
        text = _read(path)
        assert text.startswith(HISTORICAL_BANNER), path.relative_to(REPO)
        assert str(path.relative_to(REPO)) in _read(TRIAGE)

    decision_text = _read(DECISION)
    for forbidden in ("BEGIN PRIVATE KEY", "ghp_", "op://", "MCP_CLIENT_SECRET="):
        assert forbidden not in decision_text
