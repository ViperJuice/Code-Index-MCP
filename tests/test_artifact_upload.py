"""Tests for P31 artifact upload identity and repo-scoped archive creation."""

from __future__ import annotations

import json
import sqlite3
import tarfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from mcp_server.artifacts.attestation import Attestation
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


def test_build_release_asset_bundle_writes_metadata_checksum_and_attestation(tmp_path: Path):
    archive = tmp_path / "archive.tar.gz"
    archive.write_bytes(b"archive-bytes")
    attestation_path = tmp_path / "archive.tar.gz.attestation.jsonl"
    attestation_path.write_text('{"bundle":1}\n', encoding="utf-8")
    metadata = {
        "checksum": "deadbeef",
        "commit": "abcdef123456",
        "logical_artifact_id": "logical-id",
    }

    bundle = IndexArtifactUploader(repo="owner/repo")._build_release_asset_bundle(
        archive,
        metadata,
        attestation=Attestation(
            bundle_url="https://github.com/owner/repo/attestations/1",
            bundle_path=attestation_path,
            subject_digest="deadbeef",
            signed_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        ),
        bundle_dir=tmp_path / "bundle",
    )

    assert bundle.metadata_path.name == "artifact-metadata.json"
    assert json.loads(bundle.metadata_path.read_text(encoding="utf-8"))["checksum"] == "deadbeef"
    assert bundle.checksum_path.read_text(encoding="utf-8") == "deadbeef  archive.tar.gz\n"
    assert bundle.attestation_path is not None
    assert bundle.attestation_path.read_text(encoding="utf-8") == '{"bundle":1}\n'
    assert [path.name for path in bundle.asset_paths] == [
        "archive.tar.gz",
        "artifact-metadata.json",
        "archive.tar.gz.sha256",
        "archive.tar.gz.attestation.jsonl",
    ]


def test_write_metadata_file_matches_create_metadata_contract(tmp_path: Path):
    index_location = tmp_path / ".mcp-index"
    index_location.mkdir()
    index_path = index_location / "current.db"
    _sqlite_db(index_path)
    (index_location / ".index_metadata.json").write_text(
        json.dumps(
            {
                "semantic_profiles": {
                    "oss_high": {"compatibility_fingerprint": "abc"},
                }
            }
        ),
        encoding="utf-8",
    )

    uploader = IndexArtifactUploader(repo="owner/repo")
    metadata_path = uploader.write_metadata_file(
        checksum="deadbeef",
        size=123,
        output_path=index_location / "artifact-metadata.json",
        repo_id="repo-id",
        tracked_branch="main",
        commit="abcdef123456",
        schema_version="2",
        index_location=index_location,
        index_path=index_path,
    )

    payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert payload["repo_id"] == "repo-id"
    assert payload["tracked_branch"] == "main"
    assert payload["commit"] == "abcdef123456"
    assert payload["schema_version"] == "2"
    assert payload["checksum"] == "deadbeef"
    assert payload["artifact_type"] == "full"
    assert payload["compatibility"]["semantic_profiles"]["oss_high"][
        "compatibility_fingerprint"
    ] == "abc"
    assert payload["manifest_v2"]["repo_id"] == "repo-id"
    assert payload["manifest_v2"]["tracked_branch"] == "main"


def test_upload_direct_uses_explicit_release_tag_and_clobber(tmp_path: Path):
    archive = tmp_path / "archive.tar.gz"
    archive.write_bytes(b"archive-bytes")
    metadata = {
        "checksum": "deadbeef",
        "commit": "abcdef123456",
        "logical_artifact_id": "logical-id",
    }
    uploader = IndexArtifactUploader(repo="owner/repo")

    def side_effect(args, **kwargs):
        if args[:2] == ["gh", "--version"]:
            return MagicMock(returncode=0)
        if args[:4] == ["gh", "release", "view", "sha-tag"]:
            return MagicMock(
                returncode=0,
                stdout=json.dumps(
                    {
                        "assets": [
                            {"name": "archive.tar.gz"},
                            {"name": "artifact-metadata.json"},
                            {"name": "archive.tar.gz.sha256"},
                        ]
                    }
                ),
                stderr="",
            )
        return MagicMock(returncode=0, stdout="", stderr="")

    with patch("subprocess.run", side_effect=side_effect) as mock_run:
        uploader.upload_direct(archive, metadata, release_tag="sha-tag")

    upload_call = next(
        call_args
        for call_args in mock_run.call_args_list
        if call_args.args[0][:3] == ["gh", "release", "upload"]
    )
    assert upload_call.args[0][3] == "sha-tag"
    assert "--clobber" in upload_call.args[0]
    uploaded_names = [Path(arg).name for arg in upload_call.args[0] if str(arg).startswith("/")]
    assert uploaded_names == ["archive.tar.gz", "artifact-metadata.json", "archive.tar.gz.sha256"]
