"""Credential redaction tests for semantic profile serialization.

Ensures no ``*api_key*``/bearer secret VALUE survives any serialization path
(``SemanticProfile.to_dict`` and the registry export used for artifacts), while
secret-REFERENCE names (e.g. an env var name) are preserved.
"""

import json

from mcp_server.artifacts.semantic_profiles import (
    SemanticProfile,
    SemanticProfileRegistry,
)

SENTINEL = "SENTINEL_SECRET_VALUE_do_not_leak_0xDEADBEEF"


def _payload_with_secret() -> dict:
    return {
        "provider": "openai_compatible",
        "model_name": "Qwen/Qwen3-Embedding-8B",
        "model_version": "vllm-local",
        "vector_dimension": 8,
        "distance_metric": "cosine",
        "normalization_policy": "none",
        "chunk_schema_version": "2.1",
        "chunker_version": "treesitter-v3",
        "build_metadata": {
            "collection_name": "semantic-oss-high",
            # Raw secret values that must never survive serialization.
            "openai_api_key": SENTINEL,
            "OPENAI_API_KEY": SENTINEL,
            "authorization": f"Bearer {SENTINEL}",
            "service_bearer_token": SENTINEL,
            "aws_secret_access_key": SENTINEL,
            "nested": {"api_key": SENTINEL, "harmless": "keep-me"},
            # Secret REFERENCE (an env var name) - must be preserved verbatim.
            "openai_api_key_env": "OPENAI_API_KEY",
        },
    }


def test_to_dict_redacts_secret_values():
    profile = SemanticProfile.from_dict("oss-high", _payload_with_secret())
    serialized = profile.to_dict()

    blob = json.dumps(serialized)
    assert SENTINEL not in blob

    build_metadata = serialized["build_metadata"]
    assert build_metadata["openai_api_key"] == "***redacted***"
    assert build_metadata["OPENAI_API_KEY"] == "***redacted***"
    assert build_metadata["authorization"] == "***redacted***"
    assert build_metadata["service_bearer_token"] == "***redacted***"
    assert build_metadata["aws_secret_access_key"] == "***redacted***"
    assert build_metadata["nested"]["api_key"] == "***redacted***"


def test_to_dict_preserves_non_secret_and_reference_fields():
    profile = SemanticProfile.from_dict("oss-high", _payload_with_secret())
    build_metadata = profile.to_dict()["build_metadata"]

    # Secret-REFERENCE names (env var names) are kept, not the secret value.
    assert build_metadata["openai_api_key_env"] == "OPENAI_API_KEY"
    # Ordinary config survives untouched.
    assert build_metadata["collection_name"] == "semantic-oss-high"
    assert build_metadata["nested"]["harmless"] == "keep-me"


def test_registry_export_redacts_secret_values():
    registry = SemanticProfileRegistry.from_raw(
        {"oss-high": _payload_with_secret()}, "oss-high"
    )

    blob = json.dumps(registry.to_dict())
    assert SENTINEL not in blob

    exported = registry.to_dict()["semantic_profiles"]["oss-high"]["build_metadata"]
    assert exported["openai_api_key"] == "***redacted***"
    assert exported["openai_api_key_env"] == "OPENAI_API_KEY"


def test_profile_without_build_metadata_serializes_cleanly():
    payload = _payload_with_secret()
    payload.pop("build_metadata")
    profile = SemanticProfile.from_dict("oss-high", payload)

    # Should not raise; redaction tolerates the auto-populated metadata.
    blob = json.dumps(profile.to_dict())
    assert SENTINEL not in blob
