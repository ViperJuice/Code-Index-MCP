"""Tests for ArtifactManifestV2 contract validation."""

import pytest

from mcp_server.artifacts.manifest_v2 import (
    LEXICAL_ONLY_SEMANTIC_PROFILE_HASH,
    ArtifactManifestV2,
    ManifestUnit,
    build_logical_artifact_id,
    build_semantic_profile_hash,
)


def test_manifest_v2_round_trip_serialization():
    manifest = ArtifactManifestV2(
        logical_artifact_id="repo-main-abc123",
        repo_id="owner/repo",
        branch="main",
        tracked_branch="main",
        commit="abc123",
        schema_version="2",
        semantic_profile_hash=build_semantic_profile_hash(
            {
                "commercial-high": {
                    "compatibility_fingerprint": "0123456789abcdef0123456789abcdef"
                }
            }
        ),
        checksum="deadbeef",
        artifact_type="full",
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
    assert loaded.repo_id == "owner/repo"
    assert loaded.tracked_branch == "main"
    assert loaded.commit == "abc123"
    assert loaded.schema_version == "2"
    assert loaded.semantic_profile_hash == manifest.semantic_profile_hash
    assert loaded.checksum == "deadbeef"
    assert len(loaded.units) == 2


def test_manifest_v2_requires_exactly_one_lexical_unit():
    manifest = ArtifactManifestV2(
        logical_artifact_id="repo-main-abc123",
        repo_id="owner/repo",
        branch="main",
        tracked_branch="main",
        commit="abc123",
        schema_version="2",
        semantic_profile_hash=LEXICAL_ONLY_SEMANTIC_PROFILE_HASH,
        checksum="deadbeef",
        artifact_type="full",
        chunk_schema_version="2.0",
        chunk_identity_algorithm="treesitter_chunk_id_v1",
        units=[],
    )

    with pytest.raises(ValueError) as exc:
        manifest.validate()
    assert "at least one unit" in str(exc.value)


def test_semantic_profile_hash_is_deterministic_and_order_independent():
    profiles_a = {
        "b": {"compatibility_fingerprint": "fingerprint-b"},
        "a": {"compatibility_fingerprint": "fingerprint-a"},
    }
    profiles_b = {
        "a": {"compatibility_fingerprint": "fingerprint-a"},
        "b": {"compatibility_fingerprint": "fingerprint-b"},
    }
    changed = {
        "a": {"compatibility_fingerprint": "fingerprint-a"},
        "b": {"compatibility_fingerprint": "changed"},
    }

    assert build_semantic_profile_hash(profiles_a) == build_semantic_profile_hash(profiles_b)
    assert build_semantic_profile_hash(profiles_a) != build_semantic_profile_hash(changed)
    assert build_semantic_profile_hash({}) == LEXICAL_ONLY_SEMANTIC_PROFILE_HASH


@pytest.mark.parametrize(
    "field",
    ["repo_id", "checksum", "semantic_profile_hash"],
)
def test_manifest_v2_rejects_missing_required_identity_field(field):
    payload = ArtifactManifestV2(
        logical_artifact_id=build_logical_artifact_id(
            "owner/repo", "main", "abc123", LEXICAL_ONLY_SEMANTIC_PROFILE_HASH
        ),
        repo_id="owner/repo",
        branch="main",
        tracked_branch="main",
        commit="abc123",
        schema_version="2",
        semantic_profile_hash=LEXICAL_ONLY_SEMANTIC_PROFILE_HASH,
        checksum="deadbeef",
        artifact_type="full",
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
    ).to_dict()
    payload.pop(field)

    with pytest.raises((KeyError, ValueError)):
        ArtifactManifestV2.from_dict(payload)


def test_manifest_v2_accepts_legacy_branch_alias_but_requires_some_branch():
    payload = ArtifactManifestV2(
        logical_artifact_id=build_logical_artifact_id(
            "owner/repo", "main", "abc123", LEXICAL_ONLY_SEMANTIC_PROFILE_HASH
        ),
        repo_id="owner/repo",
        branch="main",
        tracked_branch="main",
        commit="abc123",
        schema_version="2",
        semantic_profile_hash=LEXICAL_ONLY_SEMANTIC_PROFILE_HASH,
        checksum="deadbeef",
        artifact_type="full",
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
    ).to_dict()
    payload.pop("tracked_branch")
    assert ArtifactManifestV2.from_dict(payload).canonical_tracked_branch == "main"

    payload.pop("branch")
    with pytest.raises(KeyError):
        ArtifactManifestV2.from_dict(payload)


def test_manifest_v2_rejects_malformed_semantic_profile_hash():
    manifest = ArtifactManifestV2(
        logical_artifact_id="repo-main-abc123",
        repo_id="owner/repo",
        branch="main",
        tracked_branch="main",
        commit="abc123",
        schema_version="2",
        semantic_profile_hash="not-a-hash",
        checksum="deadbeef",
        artifact_type="full",
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

    with pytest.raises(ValueError, match="semantic_profile_hash"):
        manifest.validate()
