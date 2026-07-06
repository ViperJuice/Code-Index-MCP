from mcp_server.indexing.source_metadata import (
    HISTORY_SOURCE_TYPE,
    SEARCH_SOURCE_METADATA_VERSION,
    build_source_metadata,
    extract_matching_source_metadata,
    merge_source_metadata,
)


def test_build_source_metadata_uses_stable_schema_and_sort_order():
    envelope = build_source_metadata(
        [
            {
                "source_type": "friction",
                "category": "todo",
                "line": 4,
                "description": "later",
                "pattern": "TODO",
            },
            {
                "source_type": "friction",
                "category": "fixme",
                "line": 2,
                "description": "first",
                "pattern": "FIXME",
            },
        ]
    )

    assert envelope == {
        "schema_version": SEARCH_SOURCE_METADATA_VERSION,
        "records": [
            {
                "source_type": "friction",
                "category": "fixme",
                "line": 2,
                "description": "first",
                "pattern": "FIXME",
            },
            {
                "source_type": "friction",
                "category": "todo",
                "line": 4,
                "description": "later",
                "pattern": "TODO",
            },
        ],
    }


def test_merge_source_metadata_preserves_unrelated_metadata_keys():
    merged = merge_source_metadata(
        {"language": "python", "owner": "tests"},
        [
            {
                "source_type": "friction",
                "category": "hack",
                "line": 7,
                "description": "temporary branch",
                "pattern": "HACK",
            }
        ],
    )

    assert merged["language"] == "python"
    assert merged["owner"] == "tests"
    assert merged["source_metadata"]["schema_version"] == SEARCH_SOURCE_METADATA_VERSION


def test_merge_source_metadata_omits_source_metadata_when_no_records_exist():
    merged = merge_source_metadata({"language": "python", "source_metadata": {"stale": True}}, [])

    assert merged == {"language": "python"}


def test_extract_matching_source_metadata_filters_categories():
    metadata = merge_source_metadata(
        {},
        [
            {
                "source_type": "friction",
                "category": "todo",
                "line": 1,
                "description": "todo item",
                "pattern": "TODO",
            },
            {
                "source_type": "friction",
                "category": "fixme",
                "line": 2,
                "description": "fixme item",
                "pattern": "FIXME",
            },
        ],
    )

    filtered = extract_matching_source_metadata(
        metadata,
        source_type="friction",
        friction_categories=["fixme"],
    )

    assert filtered == {
        "schema_version": SEARCH_SOURCE_METADATA_VERSION,
        "records": [
            {
                "source_type": "friction",
                "category": "fixme",
                "line": 2,
                "description": "fixme item",
                "pattern": "FIXME",
            }
        ],
    }


def test_extract_matching_source_metadata_without_source_type_matches_all_records():
    metadata = {
        "source_metadata": {
            "schema_version": SEARCH_SOURCE_METADATA_VERSION,
            "records": [
                {
                    "source_type": "friction",
                    "category": "todo",
                    "line": 1,
                    "description": "todo item",
                    "pattern": "TODO",
                },
                {
                    "source_type": HISTORY_SOURCE_TYPE,
                    "type": "reflection",
                    "repo": "owner/repo",
                    "number": 12,
                    "title": "Reflection issue",
                    "labels": ["reflection"],
                    "state": "closed",
                    "created_at": "2026-07-01T00:00:00Z",
                    "updated_at": "2026-07-02T00:00:00Z",
                    "url": "https://github.com/owner/repo/issues/12",
                    "summary": "Reflection issue",
                    "learnings": [],
                },
            ],
        }
    }

    filtered = extract_matching_source_metadata(metadata)

    assert filtered == metadata["source_metadata"]
