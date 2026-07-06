from pathlib import Path


def test_friction_status_evidence_covers_required_fields():
    text = Path("docs/status/friction-metadata-search.md").read_text(encoding="utf-8")

    for expected in (
        "Audit date:",
        "Phase plan:",
        "Schema version:",
        "Category vocabulary:",
        "Storage surface:",
        "Search filter surface:",
        "Semantic determinism:",
        "Verification commands:",
        "Non-goals:",
        "HISTORY reuse note:",
    ):
        assert expected in text
