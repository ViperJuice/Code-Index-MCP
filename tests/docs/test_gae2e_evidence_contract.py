"""GAE2E evidence contract checks."""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).parent.parent.parent

EVIDENCE = REPO / "docs" / "validation" / "ga-e2e-evidence.md"
CHECKLIST = REPO / "docs" / "validation" / "ga-readiness-checklist.md"
SUPPORT_MATRIX = REPO / "docs" / "SUPPORT_MATRIX.md"
GA_GOVERNANCE_EVIDENCE = REPO / "docs" / "validation" / "ga-governance-evidence.md"
RC5_EVIDENCE = REPO / "docs" / "validation" / "rc5-release-evidence.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_gae2e_evidence_exists_with_historical_banner_and_identity_headers():
    text = _read(EVIDENCE)

    assert text.startswith(
        "> **Historical artifact — as-of 2026-04-18, may not reflect current behavior**"
    )
    for expected in (
        "# GA E2E Evidence",
        "Phase plan: `plans/phase-plan-v5-gae2e.md`",
        "## Summary",
        "## Release-Surface Smoke",
        "## Fresh Repository Durability",
        "## Fail-Closed Readiness Matrix",
        "## Artifact Identity",
        "## Inputs And Posture",
        "## Verification",
    ):
        assert expected in text


def test_gae2e_evidence_records_release_surface_commands_timestamps_and_commit():
    text = _read(EVIDENCE)

    assert re.search(r"- Evidence captured: 2026-04-24T\d{2}:\d{2}:\d{2}Z\.", text)
    assert re.search(r"- Observed commit: `[0-9a-f]{40}`\.", text)
    for expected in (
        "make release-smoke",
        "make release-smoke-container",
        "uv run pytest tests/docs/test_gae2e_evidence_contract.py -v --no-cov",
        "uv run pytest tests/smoke/test_release_smoke_contract.py tests/smoke/test_secondary_tool_readiness_smoke.py -v --no-cov",
        "uv run pytest tests/test_multi_repo_production_matrix.py tests/integration/test_multi_repo_server.py tests/test_multi_repo_failure_matrix.py tests/test_tool_readiness_fail_closed.py tests/test_repository_readiness.py tests/test_git_index_manager.py -v --no-cov",
        "uv run pytest tests/test_release_metadata.py -v --no-cov",
    ):
        assert expected in text


def test_gae2e_evidence_freezes_release_and_readiness_contract_terms():
    text = _read(EVIDENCE)

    for expected in (
        "`index-it-mcp`",
        "`index_it_mcp-1.2.0rc5-py3-none-any.whl`",
        "`index_it_mcp-1.2.0rc5.tar.gz`",
        "`ghcr.io/viperjuice/code-index-mcp:v1.2.0-rc5`",
        "`ghcr.io/viperjuice/code-index-mcp:local-smoke`",
        "`ready`",
        "`index_unavailable`",
        '`safe_fallback: "native_search"`',
        "`unsupported_worktree`",
        "`wrong_branch`",
        "`stale_commit`",
        "`missing_index`",
        "`unregistered_repository`",
        "`path_outside_allowed_roots`",
        "`conflicting_path_and_repository`",
        "`public-alpha`",
        "`GA-supported`",
        "`beta`",
        "`experimental`",
        "`unsupported`",
        "`disabled-by-default`",
    ):
        assert expected in text


def test_gae2e_evidence_references_canonical_upstream_artifacts_without_new_vocabulary():
    checklist = _read(CHECKLIST)
    support_matrix = _read(SUPPORT_MATRIX)
    governance = _read(GA_GOVERNANCE_EVIDENCE)
    rc5 = _read(RC5_EVIDENCE)
    evidence = _read(EVIDENCE)

    assert "docs/validation/ga-e2e-evidence.md" in checklist
    assert "GAE2E" in checklist
    assert "GA-supported" in support_matrix
    assert "enforced via branch protection" in governance
    assert "v1.2.0-rc5" in rc5

    for expected in (
        "docs/validation/ga-readiness-checklist.md",
        "docs/SUPPORT_MATRIX.md",
        "docs/validation/ga-governance-evidence.md",
        "docs/validation/rc5-release-evidence.md",
        "product-level release posture",
        "row-level support tiers",
    ):
        assert expected in evidence

    for forbidden in (
        "ship GA",
        "stable release",
        "Authorization: Bearer",
        "gho_",
    ):
        assert forbidden not in evidence
