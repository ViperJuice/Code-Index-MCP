"""Deterministic routing policy for artifact backend selection."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence


_SENSITIVE_PROFILE_TYPES = {
    "sensitive",
    "confidential",
    "restricted",
    "secret",
    "pii",
}


@dataclass(frozen=True)
class ArtifactRoutingContext:
    """Inputs used to deterministically select an artifact backend."""

    repo_visibility: str
    artifact_size_bytes: int
    profile_type: str = "standard"
    explicit_override: Optional[str] = None


@dataclass(frozen=True)
class ArtifactRoutingDecision:
    """Routing outcome with explainability metadata."""

    provider: str
    reasons: List[str] = field(default_factory=list)

    def explain(self) -> str:
        """Return a human-readable explanation."""
        return " | ".join(self.reasons)

    def to_dict(self) -> dict:
        """Return serializable explanation payload."""
        return {
            "provider": self.provider,
            "reasons": list(self.reasons),
            "explanation": self.explain(),
        }


class ArtifactRoutingPolicy:
    """Select providers using deterministic routing rules."""

    def __init__(
        self,
        *,
        large_artifact_threshold_bytes: int,
        s3_configured: bool,
        fallback_order: Sequence[str] = ("local_fs", "github_actions"),
    ):
        self.large_artifact_threshold_bytes = max(0, large_artifact_threshold_bytes)
        self.s3_configured = s3_configured
        self.fallback_order = tuple(fallback_order)

    def choose(self, context: ArtifactRoutingContext) -> ArtifactRoutingDecision:
        """Choose a backend for the provided context."""
        explicit = (context.explicit_override or "").strip().lower()
        if explicit:
            return ArtifactRoutingDecision(
                provider=explicit,
                reasons=[f"explicit override requested: {explicit}"],
            )

        visibility = (context.repo_visibility or "private").strip().lower()
        profile_type = (context.profile_type or "standard").strip().lower()
        is_sensitive = profile_type in _SENSITIVE_PROFILE_TYPES
        is_large = context.artifact_size_bytes > self.large_artifact_threshold_bytes
        is_private = visibility == "private" or is_sensitive

        if visibility == "public" and not is_large and not is_sensitive:
            return ArtifactRoutingDecision(
                provider="github_actions",
                reasons=[
                    "public repository",
                    f"artifact size <= {self.large_artifact_threshold_bytes} bytes",
                    "profile type is non-sensitive",
                    "default route: github_actions",
                ],
            )

        if is_private or is_large:
            reasons = [
                "private/sensitive profile or large artifact requires durable backend"
            ]
            if self.s3_configured:
                reasons.append("s3 is configured")
                reasons.append("default route: s3")
                return ArtifactRoutingDecision(provider="s3", reasons=reasons)

            fallback = self._pick_fallback()
            reasons.append("s3 not configured")
            reasons.append(f"fallback route: {fallback}")
            return ArtifactRoutingDecision(provider=fallback, reasons=reasons)

        return ArtifactRoutingDecision(
            provider="github_actions",
            reasons=["default route: github_actions"],
        )

    def _pick_fallback(self) -> str:
        for provider in self.fallback_order:
            normalized = provider.strip().lower()
            if normalized in {"local_fs", "github_actions"}:
                return normalized
        return "local_fs"
