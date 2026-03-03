"""Tests for ArtifactManifestV2 contract validation."""

from mcp_server.artifacts.manifest_v2 import ArtifactManifestV2, ManifestUnit


def test_manifest_v2_round_trip_serialization():
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
            ),
            ManifestUnit(
                unit_type="semantic_profile",
                unit_id="semantic-commercial-main-abc123",
                checksum="cafebabe",
                size_bytes=2048,
                profile_id="commercial-high",
                compatibility_fingerprint="0123456789abcdef0123456789abcdef",
            ),
        ],
    )

    payload = manifest.to_dict()
    loaded = ArtifactManifestV2.from_dict(payload)

    assert loaded.logical_artifact_id == manifest.logical_artifact_id
    assert len(loaded.units) == 2


def test_manifest_v2_requires_exactly_one_lexical_unit():
    manifest = ArtifactManifestV2(
        logical_artifact_id="repo-main-abc123",
        repo_id="owner/repo",
        branch="main",
        commit="abc123",
        schema_version="2",
        chunk_schema_version="2.0",
        chunk_identity_algorithm="treesitter_chunk_id_v1",
        units=[],
    )

    try:
        manifest.validate()
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "at least one unit" in str(exc)
