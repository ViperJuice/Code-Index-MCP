"""Tests for artifact provider factory."""

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
