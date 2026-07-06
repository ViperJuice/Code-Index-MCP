import pytest

from mcp_server.indexing.source_metadata import (
    HISTORY_SOURCE_TYPE,
    SEARCH_SOURCE_METADATA_VERSION,
    build_source_metadata,
    extract_matching_source_metadata,
)


def test_history_source_metadata_normalizes_required_fields_and_sorts_labels():
    envelope = build_source_metadata(
        [
            {
                "source_type": HISTORY_SOURCE_TYPE,
                "type": "reflection",
                "repo": "Owner/Repo",
                "number": 42,
                "title": "  Reflection issue  ",
                "labels": ["zeta", "alpha", "alpha"],
                "state": "Closed",
                "created_at": "2026-07-01T00:00:00Z",
                "updated_at": "2026-07-02T00:00:00Z",
                "closed_at": "2026-07-03T00:00:00Z",
                "url": "https://github.com/owner/repo/issues/42",
                "summary": "  Reflection issue  ",
                "learnings": ["Second", "First", "First"],
            }
        ]
    )

    assert envelope == {
        "schema_version": SEARCH_SOURCE_METADATA_VERSION,
        "records": [
            {
                "source_type": HISTORY_SOURCE_TYPE,
                "type": "reflection",
                "repo": "owner/repo",
                "number": 42,
                "title": "Reflection issue",
                "labels": ["alpha", "zeta"],
                "state": "closed",
                "created_at": "2026-07-01T00:00:00Z",
                "updated_at": "2026-07-02T00:00:00Z",
                "closed_at": "2026-07-03T00:00:00Z",
                "url": "https://github.com/owner/repo/issues/42",
                "summary": "Reflection issue",
                "learnings": ["First", "Second"],
            }
        ],
    }


def test_history_source_metadata_defaults_to_empty_learnings_and_no_raw_body():
    envelope = build_source_metadata(
        [
            {
                "source_type": HISTORY_SOURCE_TYPE,
                "type": "issue",
                "repo": "owner/repo",
                "number": 7,
                "title": "History issue",
                "labels": [],
                "state": "open",
                "created_at": "2026-07-01T00:00:00Z",
                "updated_at": "2026-07-02T00:00:00Z",
                "url": "https://github.com/owner/repo/issues/7",
                "summary": "History issue",
                "learnings": [],
            }
        ]
    )

    record = envelope["records"][0]
    assert record["learnings"] == []
    assert "body" not in record


def test_extract_matching_source_metadata_filters_history_records_by_repo_and_label():
    metadata = {
        "source_metadata": {
            "schema_version": SEARCH_SOURCE_METADATA_VERSION,
            "records": [
                {
                    "source_type": HISTORY_SOURCE_TYPE,
                    "type": "reflection",
                    "repo": "owner/repo",
                    "number": 1,
                    "title": "Reflection",
                    "labels": ["reflection", "xg"],
                    "state": "closed",
                    "created_at": "2026-07-01T00:00:00Z",
                    "updated_at": "2026-07-02T00:00:00Z",
                    "url": "https://github.com/owner/repo/issues/1",
                    "summary": "Reflection",
                    "learnings": [],
                },
                {
                    "source_type": HISTORY_SOURCE_TYPE,
                    "type": "issue",
                    "repo": "other/repo",
                    "number": 2,
                    "title": "Other issue",
                    "labels": ["backlog"],
                    "state": "open",
                    "created_at": "2026-07-01T00:00:00Z",
                    "updated_at": "2026-07-02T00:00:00Z",
                    "url": "https://github.com/other/repo/issues/2",
                    "summary": "Other issue",
                    "learnings": [],
                },
            ],
        }
    }

    filtered = extract_matching_source_metadata(
        metadata,
        source_type="history",
        history_labels=["reflection"],
        history_repos=["owner/repo"],
    )

    assert filtered == {
        "schema_version": SEARCH_SOURCE_METADATA_VERSION,
        "records": [metadata["source_metadata"]["records"][0]],
    }


def test_build_source_metadata_rejects_unknown_source_type():
    with pytest.raises(ValueError, match="Unknown source type"):
        build_source_metadata(
            [
                {
                    "source_type": "unknown",
                    "value": "bad",
                }
            ]
        )
