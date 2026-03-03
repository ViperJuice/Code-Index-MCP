"""Tests for artifact integrity gate validation and downloader integration."""

import hashlib
import importlib.util
from pathlib import Path

import pytest

from mcp_server.artifacts.integrity_gate import validate_artifact_integrity
from mcp_server.artifacts.manifest_v2 import ArtifactManifestV2, ManifestUnit


def _load_downloader_class():
    module_path = (
        Path(__file__).parent.parent / "scripts" / "index-artifact-download.py"
    )
    spec = importlib.util.spec_from_file_location(
        "index_artifact_download", module_path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.IndexArtifactDownloader


def _write_archive(tmp_path: Path, payload: bytes = b"index-archive") -> Path:
    archive_path = tmp_path / "artifact.tar.gz"
    archive_path.write_bytes(payload)
    return archive_path


def _base_metadata(checksum: str) -> dict:
    return {
        "checksum": checksum,
        "commit": "0123456789abcdef",
        "branch": "main",
        "timestamp": "2026-03-03T00:00:00Z",
        "compatibility": {
            "schema_version": "2",
            "embedding_model": "voyage-code-3",
        },
    }


def test_integrity_gate_passes_valid_metadata_and_checksum(tmp_path: Path):
    archive_path = _write_archive(tmp_path)
    checksum = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    metadata = _base_metadata(checksum)

    result = validate_artifact_integrity(metadata=metadata, archive_path=archive_path)

    assert result.passed is True
    assert result.reasons == []
    assert result.expected_checksum == checksum
    assert result.actual_checksum == checksum


def test_integrity_gate_fails_on_missing_required_metadata_key(tmp_path: Path):
    archive_path = _write_archive(tmp_path)
    checksum = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    metadata = _base_metadata(checksum)
    metadata.pop("commit")

    result = validate_artifact_integrity(metadata=metadata, archive_path=archive_path)

    assert result.passed is False
    assert "missing key: commit" in result.reasons


def test_integrity_gate_prefers_checksum_sidecar_when_present(tmp_path: Path):
    archive_path = _write_archive(tmp_path)
    checksum = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    metadata = _base_metadata("wrong-checksum")
    checksum_path = tmp_path / "artifact.sha256"
    checksum_path.write_text(f"{checksum} artifact.tar.gz\n")

    result = validate_artifact_integrity(
        metadata=metadata,
        archive_path=archive_path,
        checksum_path=checksum_path,
    )

    assert result.passed is True
    assert result.expected_checksum == checksum


def test_integrity_gate_validates_optional_manifest_v2_payload(tmp_path: Path):
    archive_path = _write_archive(tmp_path)
    checksum = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    manifest = ArtifactManifestV2(
        logical_artifact_id="repo-main-abc123",
        repo_id="owner/repo",
        branch="main",
        commit="abc123",
        schema_version="2",
        chunk_schema_version="2.0",
        chunk_identity_algorithm="treesitter_chunk_id_v1",
        units=[
            ManifestUnit(
                unit_type="lexical",
                unit_id="lexical-main-abc123",
                checksum="deadbeef",
                size_bytes=1024,
            )
        ],
    )
    metadata = _base_metadata(checksum)
    metadata["manifest_v2"] = manifest.to_dict()

    result = validate_artifact_integrity(metadata=metadata, archive_path=archive_path)

    assert result.passed is True
    assert result.manifest_v2_validated is True


def test_integrity_gate_fails_for_invalid_manifest_v2_payload(tmp_path: Path):
    archive_path = _write_archive(tmp_path)
    checksum = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    metadata = _base_metadata(checksum)
    metadata["manifest_v2"] = {"repo_id": "owner/repo"}

    result = validate_artifact_integrity(metadata=metadata, archive_path=archive_path)

    assert result.passed is False
    assert any(reason.startswith("invalid manifest_v2:") for reason in result.reasons)


def test_downloader_run_integrity_gate_reuses_shared_gate(tmp_path: Path):
    IndexArtifactDownloader = _load_downloader_class()
    downloader = IndexArtifactDownloader(repo="owner/repo")

    archive_path = _write_archive(tmp_path)
    checksum = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    metadata = _base_metadata(checksum)

    result = downloader._run_integrity_gate(
        metadata=metadata,
        archive_path=archive_path,
        checksum_path=None,
    )

    assert result.passed is True


def test_downloader_run_integrity_gate_fails_closed(tmp_path: Path):
    IndexArtifactDownloader = _load_downloader_class()
    downloader = IndexArtifactDownloader(repo="owner/repo")

    archive_path = _write_archive(tmp_path)
    checksum = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    metadata = _base_metadata(checksum)
    metadata.pop("branch")

    with pytest.raises(ValueError, match="Artifact integrity gate failed"):
        downloader._run_integrity_gate(
            metadata=metadata,
            archive_path=archive_path,
            checksum_path=None,
        )
