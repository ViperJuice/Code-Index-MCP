"""Tests for artifact recovery selection behavior."""

from mcp_server.artifacts.artifact_download import IndexArtifactDownloader


def test_find_best_artifact_prefers_default_branch_over_pr(monkeypatch):
    """Default branch artifacts should be preferred over PR artifacts."""
    monkeypatch.setattr(IndexArtifactDownloader, "_detect_repository", lambda self: "owner/repo")
    downloader = IndexArtifactDownloader(repo=None)

    artifacts = [
        {
            "id": 1,
            "name": "mcp-index-pr-99",
            "created_at": "2026-03-02T00:00:00Z",
        },
        {
            "id": 2,
            "name": "mcp-index-aaaaaaaa",
            "created_at": "2026-03-01T00:00:00Z",
        },
    ]

    selected = downloader.find_best_artifact(artifacts)
    assert selected is not None
    assert selected["id"] == 2


def test_find_recovery_artifact_prefers_promoted(monkeypatch):
    """Recovery selection should prefer promoted artifacts among matches."""
    monkeypatch.setattr(IndexArtifactDownloader, "_detect_repository", lambda self: "owner/repo")
    downloader = IndexArtifactDownloader(repo=None)

    artifacts = [
        {
            "id": 10,
            "name": "index-main-1234abcd-20260302",
            "workflow_run": {"head_branch": "main", "head_sha": "1234abcd"},
            "created_at": "2026-03-02T00:00:00Z",
        },
        {
            "id": 11,
            "name": "index-main-1234abcd-promoted",
            "workflow_run": {"head_branch": "main", "head_sha": "1234abcd"},
            "created_at": "2026-03-01T00:00:00Z",
        },
    ]

    selected = downloader.find_recovery_artifact(artifacts, branch="main", commit="1234abcd")
    assert selected is not None
    assert selected["id"] == 11
