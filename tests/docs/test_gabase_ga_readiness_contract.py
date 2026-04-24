"""GABASE GA-readiness checklist contract checks."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).parent.parent.parent

CHECKLIST = REPO / "docs" / "validation" / "ga-readiness-checklist.md"
SUPPORT_MATRIX = REPO / "docs" / "SUPPORT_MATRIX.md"
DEPLOYMENT_RUNBOOK = REPO / "docs" / "operations" / "deployment-runbook.md"
USER_ACTION_RUNBOOK = REPO / "docs" / "operations" / "user-action-runbook.md"

PUBLIC_DOCS = [
    REPO / "README.md",
    REPO / "docs" / "GETTING_STARTED.md",
    REPO / "docs" / "MCP_CONFIGURATION.md",
    REPO / "docs" / "DOCKER_GUIDE.md",
]

REQUIRED_SECTIONS = [
    "## Release boundary",
    "## Support tiers",
    "## Required gates",
    "## Evidence map",
    "## Rollback expectations",
    "## Non-GA surfaces",
]

INPUT_EVIDENCE = [
    "docs/validation/rc5-release-evidence.md",
    "docs/validation/release-governance-evidence.md",
    "docs/validation/secondary-tool-readiness-evidence.md",
    "docs/validation/ga-closeout-decision.md",
]

REFRESH_EVIDENCE = {
    "docs/validation/ga-governance-evidence.md": "GAGOV",
    "docs/validation/ga-e2e-evidence.md": "GAE2E",
    "docs/validation/ga-operations-evidence.md": "GAOPS",
    "docs/validation/ga-rc-evidence.md": "GARC",
    "docs/validation/ga-final-decision.md": "GAREL",
    "docs/validation/ga-release-evidence.md": "GAREL",
}

TIER_LABELS = [
    "public-alpha",
    "beta",
    "GA",
    "experimental",
    "unsupported",
    "disabled-by-default",
]

TOPOLOGY_TERMS = [
    "one registered worktree per git common directory",
    "tracked/default branch",
    "index_unavailable",
    'safe_fallback: "native_search"',
]

FORBIDDEN_PUBLIC_LAUNCH_PHRASES = [
    "ship GA",
    "generally available",
]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def test_checklist_exists_with_required_sections_and_baseline():
    text = _read(CHECKLIST)

    for heading in REQUIRED_SECTIONS:
        assert heading in text

    for expected in (
        "v1.2.0-rc5",
        "v1.2.0-rc6",
        "canonical GABASE checklist",
    ):
        assert expected in text


def test_checklist_freezes_tier_labels_and_topology_constraints():
    text = _normalized(CHECKLIST)

    for label in TIER_LABELS:
        assert label in text

    for term in TOPOLOGY_TERMS:
        assert term in text


def test_checklist_distinguishes_input_and_refresh_evidence():
    text = _read(CHECKLIST)

    assert "### Input evidence" in text
    assert "### Refresh evidence required before a GA ship decision" in text

    for relative in INPUT_EVIDENCE:
        assert relative in text

    for relative, phase in REFRESH_EVIDENCE.items():
        assert relative in text
        assert phase in text


def test_public_docs_remain_pre_ga_and_route_to_canonical_artifacts():
    failures = []
    for path in PUBLIC_DOCS:
        text = _read(path)
        lowered = text.lower()

        if "1.2.0-rc6" not in text:
            failures.append(f"{path.relative_to(REPO)} missing rc6 baseline")
        if ("public-alpha" not in lowered) and ("beta" not in lowered):
            failures.append(f"{path.relative_to(REPO)} missing public-alpha/beta language")
        if "ga-readiness-checklist" not in text:
            failures.append(f"{path.relative_to(REPO)} missing checklist reference")
        if "SUPPORT_MATRIX.md" not in text:
            failures.append(f"{path.relative_to(REPO)} missing support matrix reference")
        for phrase in FORBIDDEN_PUBLIC_LAUNCH_PHRASES:
            if phrase in text:
                failures.append(
                    f"{path.relative_to(REPO)} contains forbidden launch phrase {phrase!r}"
                )

    assert failures == []


def test_support_matrix_and_runbooks_share_tier_labels_and_topology_language():
    for path in (SUPPORT_MATRIX, DEPLOYMENT_RUNBOOK, USER_ACTION_RUNBOOK):
        text = _normalized(path)
        for label in TIER_LABELS:
            assert label in text, f"{path.relative_to(REPO)} missing {label!r}"
        for term in TOPOLOGY_TERMS:
            assert term in text, f"{path.relative_to(REPO)} missing {term!r}"


def test_runbooks_point_future_ga_work_to_checklist_and_refresh_artifacts():
    for path in (DEPLOYMENT_RUNBOOK, USER_ACTION_RUNBOOK):
        text = _read(path)
        for expected in (
            "ga-readiness-checklist.md",
            "GAGOV",
            "GAE2E",
            "GAOPS",
            "GARC",
            "GAREL",
            "v1.2.0-rc6",
            "manual enforcement",
        ):
            assert expected in text, f"{path.relative_to(REPO)} missing {expected!r}"
