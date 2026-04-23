"""Factory for selecting configured artifact provider."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from mcp_server.config.settings import get_settings

from .providers.github_actions import GitHubActionsArtifactProvider
from .providers.local_fs import LocalFilesystemArtifactProvider
from .routing_policy import (
    ArtifactRoutingContext,
    ArtifactRoutingDecision,
    ArtifactRoutingPolicy,
)


class ArtifactProviderFactory:
    """Create artifact providers from runtime settings."""

    _SUPPORTED_PROVIDERS = {"github_actions", "local_fs", "auto"}
    _UNIMPLEMENTED_PROVIDERS = {"s3", "gcs", "azure"}

    @staticmethod
    def create(
        repo: str,
        *,
        repo_visibility: Optional[str] = None,
        artifact_size_bytes: Optional[int] = None,
        profile_type: Optional[str] = None,
        provider_override: Optional[str] = None,
    ):
        settings = get_settings()

        decision = ArtifactProviderFactory.explain_selection(
            repo=repo,
            repo_visibility=repo_visibility,
            artifact_size_bytes=artifact_size_bytes,
            profile_type=profile_type,
            provider_override=provider_override,
            settings=settings,
        )
        provider = decision.provider

        if provider == "github_actions":
            return GitHubActionsArtifactProvider(repo)
        if provider == "local_fs":
            return LocalFilesystemArtifactProvider(Path(settings.artifact_local_cache_dir))
        raise ValueError(f"Unsupported artifact provider: {provider}")

    @staticmethod
    def explain_selection(
        repo: str,
        *,
        repo_visibility: Optional[str] = None,
        artifact_size_bytes: Optional[int] = None,
        profile_type: Optional[str] = None,
        provider_override: Optional[str] = None,
        settings=None,
    ) -> ArtifactRoutingDecision:
        """Return explainable provider selection decision."""
        del repo  # Routing is intentionally independent of artifact identity.

        if settings is None:
            settings = get_settings()

        configured_provider = provider_override or getattr(
            settings, "artifact_provider", "github_actions"
        )
        configured_provider = configured_provider.lower()

        if configured_provider in ArtifactProviderFactory._UNIMPLEMENTED_PROVIDERS:
            raise ValueError(
                f"Artifact provider '{configured_provider}' is not implemented and cannot be selected"
            )
        if configured_provider not in ArtifactProviderFactory._SUPPORTED_PROVIDERS:
            raise ValueError(f"Unsupported artifact provider: {configured_provider}")

        if configured_provider != "auto":
            return ArtifactRoutingDecision(
                provider=configured_provider,
                reasons=[f"configured provider override: {configured_provider}"],
            )

        fallback_order_raw = getattr(
            settings,
            "artifact_routing_fallback_order",
            "local_fs,github_actions",
        )
        fallback_order = [p.strip() for p in fallback_order_raw.split(",") if p.strip()]

        policy = ArtifactRoutingPolicy(
            large_artifact_threshold_bytes=getattr(
                settings,
                "artifact_routing_large_threshold_bytes",
                50 * 1024 * 1024,
            ),
            s3_configured=bool(getattr(settings, "artifact_s3_bucket", None)),
            fallback_order=fallback_order,
        )

        context = ArtifactRoutingContext(
            repo_visibility=repo_visibility
            or getattr(settings, "artifact_routing_default_repo_visibility", "private"),
            artifact_size_bytes=(
                artifact_size_bytes
                if artifact_size_bytes is not None
                else getattr(settings, "artifact_routing_default_artifact_size_bytes", 0)
            ),
            profile_type=profile_type
            or getattr(settings, "artifact_routing_default_profile_type", "standard"),
            explicit_override=provider_override if provider_override else None,
        )
        return policy.choose(context)
