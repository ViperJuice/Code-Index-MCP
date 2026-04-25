"""P25 release checklist documentation tests."""

from pathlib import Path

REPO = Path(__file__).parent.parent.parent
RUNBOOK = REPO / "docs" / "operations" / "deployment-runbook.md"
USER_ACTIONS = REPO / "docs" / "operations" / "user-action-runbook.md"
RELEASE_GOVERNANCE = REPO / "docs" / "validation" / "release-governance-evidence.md"

REQUIRED_GATES = [
    "Alpha Gate - Dependency Sync",
    "Alpha Gate - Format And Lint",
    "Alpha Gate - Unit And Release Smoke",
    "Alpha Gate - Integration Smoke",
    "Alpha Gate - Production Multi-Repo Matrix",
    "Alpha Gate - Docker Build And Smoke",
    "Alpha Gate - Docs Truth",
    "Alpha Gate - Required Gates Passed",
]


def test_deployment_runbook_maps_each_required_alpha_gate():
    text = RUNBOOK.read_text(encoding="utf-8")

    assert "## Public Alpha Release Gate Checklist" in text
    for gate in REQUIRED_GATES:
        assert gate in text
    assert (
        "| Required job | Operator decision | Command/workflow source | Block/fallback behavior |"
        in text
    )


def test_user_action_runbook_names_each_required_alpha_gate():
    text = USER_ACTIONS.read_text(encoding="utf-8")

    assert "Require the public alpha gate set before release evidence is accepted" in text
    for gate in REQUIRED_GATES:
        assert gate in text


def test_attestation_prerequisite_and_private_alpha_fallback_documented():
    text = USER_ACTIONS.read_text(encoding="utf-8")

    assert "ATTESTATION_GH_TOKEN" in text
    assert "Settings -> Actions -> General -> Artifact attestations" in text
    assert "private-alpha" in text
    assert "informational skipped/warn" in text


def test_release_governance_policy_documented_in_operator_runbooks():
    for path in (RUNBOOK, USER_ACTIONS):
        text = path.read_text(encoding="utf-8")

        assert "Release Governance and Channel Policy" in text, path
        for expected in (
            "manual enforcement",
            "branch protection",
            "ruleset",
            "v1.2.0-rc8",
            "v2.15.0-alpha.1",
            "GitHub Latest",
            "auto_merge=false",
            "Docker latest",
            "GACLOSE",
        ):
            assert expected in text, f"{path} missing {expected!r}"


def test_release_governance_evidence_records_policy_metadata():
    text = RELEASE_GOVERNANCE.read_text(encoding="utf-8")

    for expected in (
        "Repository: `ViperJuice/Code-Index-MCP`",
        "Default branch: `main`",
        "Branch protection: `not protected`",
        "Repository rulesets: `none`",
        "manual enforcement",
        "v1.2.0-rc5",
        "v2.15.0-alpha.1",
        "GitHub Latest",
        "auto_merge=false",
        "Docker latest",
        "Policy accepted by: `repository operator`",
    ):
        assert expected in text
