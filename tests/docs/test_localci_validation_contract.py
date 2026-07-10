"""LOCALCI evidence artifact checks."""

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ARTIFACT = REPO / "docs" / "status" / "localci-validation-contract.md"
TESTING_GUIDE = REPO / "docs" / "development" / "TESTING-GUIDE.md"


def test_localci_evidence_artifact_records_contract() -> None:
    text = ARTIFACT.read_text(encoding="utf-8")
    for phrase in (
        "Audit date:",
        "agent-doctor",
        "agent-fast",
        "agent-gate",
        "agent-full",
        "agent-fix",
        "agent-affected",
        "docs-only changes route to `agent-fast`",
        "source, workflow, package, lockfile, or unknown changes route to `agent-gate`",
        "fail-closed",
        "workflow classification",
        "hosted-work reduction summary",
        "Verification commands",
    ):
        assert phrase in text


def test_localci_evidence_artifact_records_non_goals() -> None:
    text = ARTIFACT.read_text(encoding="utf-8")
    for phrase in (
        "No self-hosted runner registration was performed.",
        "No GitHub secret mutation was performed.",
        "No coverage threshold change was performed.",
        "No hosted coverage upload was performed.",
    ):
        assert phrase in text


def test_testing_guide_records_quality_gate_recovery_contract() -> None:
    text = TESTING_GUIDE.read_text(encoding="utf-8")
    for phrase in (
        "uv sync --locked --extra dev --link-mode=copy",
        "make alpha-release-gates",
        "make alpha-mypy-ratchet",
        "config/mypy_baseline.json",
        "@pytest.mark.requires_network",
        "rejects unmarked TCP",
        "not invoked by ordinary pull-request workflows",
        "coverage.xml",
        "htmlcov/",
    ):
        assert phrase in text
