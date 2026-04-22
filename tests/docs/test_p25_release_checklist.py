"""P25 release checklist documentation tests."""

from pathlib import Path

REPO = Path(__file__).parent.parent.parent
RUNBOOK = REPO / "docs" / "operations" / "deployment-runbook.md"
USER_ACTIONS = REPO / "docs" / "operations" / "user-action-runbook.md"

REQUIRED_GATES = [
    "Alpha Gate - Dependency Sync",
    "Alpha Gate - Format And Lint",
    "Alpha Gate - Unit And Release Smoke",
    "Alpha Gate - Integration Smoke",
    "Alpha Gate - Docker Build And Smoke",
    "Alpha Gate - Docs Truth",
    "Alpha Gate - Required Gates Passed",
]


def test_deployment_runbook_maps_each_required_alpha_gate():
    text = RUNBOOK.read_text(encoding="utf-8")

    assert "## Public Alpha Release Gate Checklist" in text
    for gate in REQUIRED_GATES:
        assert gate in text
    assert "| Required job | Operator decision | Command/workflow source | Block/fallback behavior |" in text


def test_attestation_prerequisite_and_private_alpha_fallback_documented():
    text = USER_ACTIONS.read_text(encoding="utf-8")

    assert "ATTESTATION_GH_TOKEN" in text
    assert "Settings -> Actions -> General -> Artifact attestations" in text
    assert "private-alpha" in text
    assert "informational skipped/warn" in text
