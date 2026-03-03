"""Tests for semantic profile registry behavior."""

from mcp_server.artifacts.semantic_profiles import SemanticProfileRegistry


def _sample_profiles():
    return {
        "commercial-high": {
            "provider": "voyage",
            "model_name": "voyage-code-3",
            "model_version": "2025-01",
            "vector_dimension": 1024,
            "distance_metric": "cosine",
            "normalization_policy": "provider-default",
            "chunk_schema_version": "2.0",
            "chunker_version": "treesitter-chunker@2.x",
        },
        "oss-high": {
            "provider": "sentence_transformers",
            "model_name": "intfloat/e5-large-v2",
            "model_version": "hf-rev-sha",
            "vector_dimension": 1024,
            "distance_metric": "cosine",
            "normalization_policy": "l2",
            "chunk_schema_version": "2.0",
            "chunker_version": "treesitter-chunker@2.x",
        },
    }


def test_registry_uses_configured_default_profile():
    registry = SemanticProfileRegistry.from_raw(_sample_profiles(), "oss-high")
    assert registry.get().profile_id == "oss-high"


def test_fingerprint_is_stable_for_same_profile_payload():
    profiles = _sample_profiles()
    r1 = SemanticProfileRegistry.from_raw(profiles, "commercial-high")
    r2 = SemanticProfileRegistry.from_raw(profiles, "commercial-high")

    assert (
        r1.get("commercial-high").compatibility_fingerprint
        == r2.get("commercial-high").compatibility_fingerprint
    )


def test_missing_required_profile_field_raises_value_error():
    profiles = _sample_profiles()
    del profiles["commercial-high"]["model_name"]

    try:
        SemanticProfileRegistry.from_raw(profiles, "commercial-high")
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "missing required fields" in str(exc)
