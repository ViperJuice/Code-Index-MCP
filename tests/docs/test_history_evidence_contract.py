from pathlib import Path


def test_history_status_evidence_covers_required_fields():
    text = Path("docs/status/historical-issue-context.md").read_text(encoding="utf-8")

    for expected in (
        "Audit date:",
        "Phase plan:",
        "Schema version:",
        "Normalized issue fields:",
        "Fetcher filters:",
        "Dedupe rule:",
        "Redaction posture:",
        "Verification commands:",
        "Non-goals:",
        "PYCLIENT reuse note:",
    ):
        assert expected in text
