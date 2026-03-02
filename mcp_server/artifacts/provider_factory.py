"""Factory for selecting configured artifact provider."""

from __future__ import annotations

from pathlib import Path

from mcp_server.config.settings import get_settings

from .providers.github_actions import GitHubActionsArtifactProvider
from .providers.local_fs import LocalFilesystemArtifactProvider
from .providers.s3 import S3ArtifactProvider


class ArtifactProviderFactory:
    """Create artifact providers from runtime settings."""

    @staticmethod
    def create(repo: str):
        settings = get_settings()
        provider = settings.artifact_provider.lower()

        if provider == "github_actions":
            return GitHubActionsArtifactProvider(repo)
        if provider == "local_fs":
            return LocalFilesystemArtifactProvider(Path(settings.artifact_local_cache_dir))
        if provider == "s3":
            if not settings.artifact_s3_bucket:
                raise ValueError("ARTIFACT_S3_BUCKET is required for s3 provider")
            return S3ArtifactProvider(
                bucket=settings.artifact_s3_bucket,
                prefix=settings.artifact_s3_prefix,
            )

        raise ValueError(f"Unsupported artifact provider: {settings.artifact_provider}")
