from pathlib import Path


def test_public_docs_cover_friction_filters_and_legacy_shape():
    readme = Path("README.md").read_text(encoding="utf-8")
    api_reference = Path("docs/api/API-REFERENCE.md").read_text(encoding="utf-8")
    support_matrix = Path("docs/SUPPORT_MATRIX.md").read_text(encoding="utf-8")
    combined = "\n".join([readme, api_reference, support_matrix])

    for expected in (
        'source_type="friction"',
        "friction_categories",
        "include_source_metadata",
        "legacy result shape",
        "metadata-only validation error",
    ):
        assert expected in combined
