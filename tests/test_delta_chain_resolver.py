"""Tests for resolving full+delta artifact chains."""

from mcp_server.artifacts.delta_resolver import resolve_delta_chain


def test_resolve_delta_chain_from_full_and_two_deltas():
    artifacts = [
        {
            "id": "1",
            "artifact_type": "full",
            "target_commit": "aaaa",
            "created_at": "2026-03-01T00:00:00Z",
        },
        {
            "id": "2",
            "artifact_type": "delta",
            "base_commit": "aaaa",
            "target_commit": "bbbb",
            "created_at": "2026-03-02T00:00:00Z",
        },
        {
            "id": "3",
            "artifact_type": "delta",
            "base_commit": "bbbb",
            "target_commit": "cccc",
            "created_at": "2026-03-03T00:00:00Z",
        },
    ]

    chain = resolve_delta_chain(artifacts, "cccc")
    assert [item["id"] for item in chain] == ["1", "2", "3"]


def test_resolve_delta_chain_fails_without_base_full():
    artifacts = [
        {
            "id": "2",
            "artifact_type": "delta",
            "base_commit": "aaaa",
            "target_commit": "bbbb",
            "created_at": "2026-03-02T00:00:00Z",
        }
    ]

    try:
        resolve_delta_chain(artifacts, "bbbb")
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "No delta artifact found targeting commit aaaa" in str(exc)
