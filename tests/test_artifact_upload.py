"""Tests for P31 artifact upload identity and repo-scoped archive creation."""

from __future__ import annotations

import json
import sqlite3
import tarfile
from pathlib import Path

from mcp_server.artifacts.artifact_upload import IndexArtifactUploader
from mcp_server.artifacts.manifest_v2 import LEXICAL_ONLY_SEMANTIC_PROFILE_HASH


def _sqlite_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        conn.execute("CREATE TABLE files (id INTEGER PRIMARY KEY, relative_path TEXT)")
        conn.execute("CREATE TABLE symbols (id INTEGER PRIMARY KEY, file_id INTEGER)")
        conn.commit()
    finally:
        conn.close()


def test_compress_indexes_uses_repo_scoped_current_db(tmp_path: Path):
    repo_path = tmp_path / "repo"
    index_location = repo_path / ".mcp-index"
    _sqlite_db(index_location / "current.db")
    (index_location / ".index_metadata.json").write_text(
        json.dumps({"semantic_profiles": {}}), encoding="utf-8"
    )
    (repo_path / "code_index.db").write_text("legacy", encoding="utf-8")

    uploader = IndexArtifactUploader(repo="owner/repo")
    archive, checksum, size = uploader.compress_indexes(
        tmp_path / "archive.tar.gz",
        secure=True,
        repo_path=repo_path,
        index_location=index_location,
        index_path=index_location / "current.db",
    )

    assert archive.exists()
    assert checksum
    assert size > 0
    with tarfile.open(archive, "r:gz") as tar:
        names = tar.getnames()
    assert "current.db" in names
    assert "code_index.db" not in names
    assert ".index_metadata.json" in names


def test_create_metadata_includes_full_p31_identity(tmp_path: Path):
    index_location = tmp_path / ".mcp-index"
    index_location.mkdir()
    (index_location / ".index_metadata.json").write_text(
        json.dumps(
            {
                "semantic_profiles": {
                    "oss_high": {"compatibility_fingerprint": "abc"},
                    "commercial_high": {"compatibility_fingerprint": "def"},
                }
            }
        ),
        encoding="utf-8",
    )

    metadata = IndexArtifactUploader(repo="owner/repo").create_metadata(
        checksum="deadbeef",
        size=123,
        repo_id="repo-id",
        tracked_branch="main",
        commit="abcdef123456",
        schema_version="2",
        index_location=index_location,
    )

    assert metadata["repo_id"] == "repo-id"
    assert metadata["tracked_branch"] == "main"
    assert metadata["branch"] == "main"
    assert metadata["commit"] == "abcdef123456"
    assert metadata["schema_version"] == "2"
    assert metadata["semantic_profile_hash"] != LEXICAL_ONLY_SEMANTIC_PROFILE_HASH
    assert metadata["checksum"] == "deadbeef"
    assert metadata["artifact_type"] == "full"
    assert metadata["manifest_v2"]["repo_id"] == "repo-id"
    assert metadata["manifest_v2"]["tracked_branch"] == "main"


def test_create_metadata_uses_lexical_only_profile_hash_when_no_profiles(tmp_path: Path):
    metadata = IndexArtifactUploader(repo="owner/repo").create_metadata(
        checksum="deadbeef",
        size=123,
        repo_id="repo-id",
        tracked_branch="main",
        commit="abcdef123456",
        schema_version="2",
        index_location=tmp_path / ".mcp-index",
    )

    assert metadata["semantic_profile_hash"] == LEXICAL_ONLY_SEMANTIC_PROFILE_HASH
