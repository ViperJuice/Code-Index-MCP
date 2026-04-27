"""MRE2E evidence contract checks."""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).parent.parent.parent

EVIDENCE = REPO / "docs" / "validation" / "mre2e-evidence.md"
GUIDE = REPO / "docs" / "guides" / "artifact-persistence.md"
ROADMAP = REPO / "specs" / "phase-plans-v6.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def test_mre2e_evidence_exists_with_identity_and_required_sections():
    text = _read(EVIDENCE)

    for expected in (
        "# MRE2E Evidence",
        "Phase plan: `plans/phase-plan-v6-MRE2E.md`",
        "## Summary",
        "## Supported Deployment Shape",
        "## Fresh-State Multi-Repo Lifecycle",
        "## Wrong-Branch Non-Mutation Contract",
        "## Hydration Validation Evidence",
        "## Beta Limitations",
        "## Verification",
    ):
        assert expected in text


def test_mre2e_evidence_records_commands_timestamps_and_commit_under_test():
    text = _read(EVIDENCE)

    assert re.search(r"- Evidence captured: 2026-04-27T\d{2}:\d{2}:\d{2}Z\.", text)
    assert re.search(r"- Observed commit: `[0-9a-f]{40}`\.", text)
    for expected in (
        "uv run pytest tests/docs/test_mre2e_evidence_contract.py -q --no-cov",
        "uv run pytest tests/integration/test_multi_repo_hydration.py -q --no-cov",
        "uv run pytest tests/test_multi_repo_artifact_coordinator.py tests/test_artifact_commands.py -q --no-cov",
        "uv run pytest tests/test_multi_repo_production_matrix.py tests/test_multi_repo_failure_matrix.py tests/integration/test_multi_repo_server.py -q --no-cov",
    ):
        assert expected in text


def test_mre2e_evidence_freezes_two_repo_lifecycle_and_validation_fields():
    text = _normalized(EVIDENCE)

    for expected in (
        "two unrelated repositories",
        "register -> index -> publish -> hydrate -> reconcile -> query",
        "add, modify, delete, and rename",
        "wrong_branch",
        "index_unavailable",
        "artifact_backend",
        "artifact_health",
        "last_published_commit",
        "last_recovered_commit",
        "checksum",
        "branch",
        "commit",
        "schema_version",
        "semantic_profile_hash",
        "commercial_high",
        "oss_high",
    ):
        assert expected in text


def test_mre2e_evidence_distinguishes_ci_mock_validation_from_optional_live_operator_checks():
    text = _read(EVIDENCE)

    for expected in (
        "deterministic local GitHub/CLI mock strategy",
        "optional live-operator validation",
        "normal CI does not require live GitHub publication",
        "MRREADY",
    ):
        assert expected in text


def test_artifact_persistence_guide_names_mre2e_supported_shape_and_beta_boundary():
    text = _normalized(GUIDE)
    roadmap = _normalized(ROADMAP)

    for expected in (
        "MRE2E",
        "workspace-status",
        "publish-workspace",
        "fetch-workspace",
        "reconcile-workspace",
        "deterministic local GitHub/CLI mock",
        "optional live-operator validation",
        "many unrelated repositories",
        "one registered worktree per git common directory",
        "tracked/default branch",
        "MRREADY",
    ):
        assert expected in text
    assert "Multi-Repo Rollout Readiness (MRREADY)" in roadmap
