from pathlib import Path


def test_public_docs_cover_history_ingest_filters_and_legacy_shape():
    readme = Path("README.md").read_text(encoding="utf-8")
    api_reference = Path("docs/api/API-REFERENCE.md").read_text(encoding="utf-8")
    support_matrix = Path("docs/SUPPORT_MATRIX.md").read_text(encoding="utf-8")
    combined = "\n".join([readme, api_reference, support_matrix])

    for expected in (
        "mcp-index history ingest",
        'source_type="history"',
        "history_labels",
        "history_repos",
        "include_source_metadata",
        "fixture-backed",
        "legacy result shape",
    ):
        assert expected in combined
