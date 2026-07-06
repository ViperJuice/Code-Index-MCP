"""LOCALCI agent validation documentation checks."""

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
AGENT_DOC = REPO / "docs" / "development" / "agent-validation.md"
TESTING_GUIDE = REPO / "docs" / "development" / "TESTING-GUIDE.md"
RUNBOOK = REPO / "docs" / "operations" / "user-action-runbook.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_agent_validation_docs_define_all_commands_and_policy() -> None:
    text = _read(AGENT_DOC)
    for command in (
        "agent-doctor",
        "agent-fast",
        "agent-gate",
        "agent-full",
        "agent-fix",
        "agent-affected",
    ):
        assert command in text
    for phrase in (
        "cheap and offline by default",
        "pre-PR gate",
        "AGENT_REMOTE_HOST",
        "Dagger",
        "fail-closed",
        "hosted fallback is not allowed",
    ):
        assert phrase in text


def test_testing_guide_points_to_agent_validation_contract() -> None:
    text = _read(TESTING_GUIDE)
    for phrase in (
        "make agent-fast",
        "make agent-gate",
        "make agent-full",
        "make agent-affected",
    ):
        assert phrase in text


def test_runbook_preserves_p25_actions_and_localci_out_of_scope_items() -> None:
    text = _read(RUNBOOK)
    for phrase in (
        "self-hosted runner registration",
        "GitHub secret changes",
        "manual release dispatch",
        "Require the public alpha gate set before release evidence is accepted",
    ):
        assert phrase in text
