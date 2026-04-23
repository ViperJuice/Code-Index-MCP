"""Tests for artifact provider factory."""

import pytest

from mcp_server.artifacts import provider_factory
from mcp_server.artifacts.provider_factory import ArtifactProviderFactory


def test_factory_creates_local_provider(monkeypatch):
    """Factory should create local filesystem provider when configured."""

    class DummySettings:
        artifact_provider = "local_fs"
        artifact_local_cache_dir = ".indexes/artifacts"
        artifact_s3_bucket = None
        artifact_s3_prefix = "mcp-index"

    monkeypatch.setattr(provider_factory, "get_settings", lambda: DummySettings())
    provider = ArtifactProviderFactory.create("owner/repo")
    assert provider.__class__.__name__ == "LocalFilesystemArtifactProvider"


def test_factory_auto_policy_public_small_routes_to_github(monkeypatch):
    """Factory should use policy routing when provider is auto."""

    class DummySettings:
        artifact_provider = "auto"
        artifact_local_cache_dir = ".indexes/artifacts"
        artifact_s3_bucket = "bucket-name"
        artifact_s3_prefix = "mcp-index"
        artifact_routing_default_repo_visibility = "private"
        artifact_routing_default_artifact_size_bytes = 0
        artifact_routing_default_profile_type = "standard"
        artifact_routing_large_threshold_bytes = 1024
        artifact_routing_fallback_order = "local_fs,github_actions"

    monkeypatch.setattr(provider_factory, "get_settings", lambda: DummySettings())
    provider = ArtifactProviderFactory.create(
        "owner/repo",
        repo_visibility="public",
        artifact_size_bytes=128,
        profile_type="standard",
    )
    assert provider.__class__.__name__ == "GitHubActionsArtifactProvider"


def test_factory_auto_policy_private_skips_unimplemented_s3(monkeypatch):
    """Factory should not route to unimplemented s3 for private artifacts."""

    class DummySettings:
        artifact_provider = "auto"
        artifact_local_cache_dir = ".indexes/artifacts"
        artifact_s3_bucket = "bucket-name"
        artifact_s3_prefix = "mcp-index"
        artifact_routing_default_repo_visibility = "private"
        artifact_routing_default_artifact_size_bytes = 0
        artifact_routing_default_profile_type = "standard"
        artifact_routing_large_threshold_bytes = 1024
        artifact_routing_fallback_order = "local_fs,github_actions"

    monkeypatch.setattr(provider_factory, "get_settings", lambda: DummySettings())
    provider = ArtifactProviderFactory.create(
        "owner/repo",
        repo_visibility="private",
        artifact_size_bytes=128,
        profile_type="standard",
    )
    assert provider.__class__.__name__ == "LocalFilesystemArtifactProvider"


def test_factory_explicit_s3_raises_not_implemented(monkeypatch):
    """Explicit s3 selection should fail deterministically until implemented."""

    class DummySettings:
        artifact_provider = "s3"
        artifact_local_cache_dir = ".indexes/artifacts"
        artifact_s3_bucket = "bucket-name"
        artifact_s3_prefix = "mcp-index"
        artifact_routing_default_repo_visibility = "private"
        artifact_routing_default_artifact_size_bytes = 0
        artifact_routing_default_profile_type = "standard"
        artifact_routing_large_threshold_bytes = 1024
        artifact_routing_fallback_order = "local_fs,github_actions"

    monkeypatch.setattr(provider_factory, "get_settings", lambda: DummySettings())
    with pytest.raises(ValueError, match="not implemented"):
        ArtifactProviderFactory.create("owner/repo")


def test_factory_explain_selection_includes_reason(monkeypatch):
    """Factory should provide explainable routing reasons."""

    class DummySettings:
        artifact_provider = "auto"
        artifact_local_cache_dir = ".indexes/artifacts"
        artifact_s3_bucket = None
        artifact_s3_prefix = "mcp-index"
        artifact_routing_default_repo_visibility = "private"
        artifact_routing_default_artifact_size_bytes = 0
        artifact_routing_default_profile_type = "standard"
        artifact_routing_large_threshold_bytes = 1024
        artifact_routing_fallback_order = "local_fs,github_actions"

    monkeypatch.setattr(provider_factory, "get_settings", lambda: DummySettings())
    decision = ArtifactProviderFactory.explain_selection(
        "owner/repo",
        repo_visibility="private",
        artifact_size_bytes=2048,
        profile_type="standard",
    )

    assert decision.provider == "local_fs"
    assert "fallback route: local_fs" in decision.explain()
