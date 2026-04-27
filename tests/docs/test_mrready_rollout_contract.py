"""MRREADY rollout contract checks."""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).parent.parent.parent

READINESS_NOTE = REPO / "docs" / "validation" / "mrready-rollout-readiness.md"
MRE2E = REPO / "docs" / "validation" / "mre2e-evidence.md"
README = REPO / "README.md"
AGENTS = REPO / "AGENTS.md"
GUIDE = REPO / "docs" / "guides" / "artifact-persistence.md"
DEPLOY = REPO / "docs" / "operations" / "deployment-runbook.md"
USER = REPO / "docs" / "operations" / "user-action-runbook.md"
RETENTION = REPO / "docs" / "operations" / "artifact-retention.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def test_mrready_readiness_note_exists_with_required_sections():
    text = _read(READINESS_NOTE)

    for expected in (
        "# MRREADY Rollout Readiness",
        "Phase plan: `plans/phase-plan-v6-MRREADY.md`",
        "## Verdict",
        "## Rollout Status Contract",
        "## Operator Command Set",
        "## Recovery Mapping",
        "## Beta Boundary",
        "## Verification",
    ):
        assert expected in text


def test_mrready_readiness_note_records_commit_commands_and_controlled_rollout_verdict():
    text = _read(READINESS_NOTE)

    assert re.search(r"- Evidence captured: 2026-04-27T\d{2}:\d{2}:\d{2}Z\.", text)
    assert re.search(r"- Observed commit: `[0-9a-f]{40}`\.", text)
    assert "docs/validation/mre2e-evidence.md" in text
    assert "controlled rollout only" in text
    for expected in (
        "uv run pytest tests/docs/test_mrready_rollout_contract.py -q --no-cov",
        "uv run pytest tests/test_git_index_manager.py tests/test_health_surface.py tests/test_repository_commands.py tests/test_multi_repo_artifact_coordinator.py tests/test_artifact_commands.py -q --no-cov",
        "mcp-index repository list -v",
        "mcp-index repository status",
        "mcp-index artifact workspace-status",
    ):
        assert expected in text


def test_mrready_docs_freeze_rollout_status_vocabulary_and_query_boundary():
    text = _normalized(READINESS_NOTE)

    for expected in (
        "ready",
        "local_only",
        "publish_failed",
        "wrong_branch",
        "partial_index_failure",
        "index_unavailable",
        'safe_fallback: "native_search"',
        "rollout status",
        "query surface",
    ):
        assert expected in text


def test_public_docs_and_runbooks_reference_mrready_status_and_recovery_surfaces():
    for path in (README, AGENTS, GUIDE, DEPLOY, USER, RETENTION):
        text = _normalized(path)
        for expected in (
            "MRREADY",
            "workspace-status",
            "repository list -v",
            "index_unavailable",
        ):
            assert expected in text, path

    deploy_text = _normalized(DEPLOY)
    for expected in (
        "local_only",
        "publish_failed",
        "partial_index_failure",
        "controlled rollout",
    ):
        assert expected in deploy_text


def test_mrready_note_routes_recovery_through_runbooks_and_retention_guidance():
    text = _read(READINESS_NOTE)
    for expected in (
        "docs/operations/deployment-runbook.md",
        "docs/operations/user-action-runbook.md",
        "docs/operations/artifact-retention.md",
    ):
        assert expected in text
    assert "MRE2E" in _read(MRE2E)
