"""Semantic profile registry and compatibility fingerprinting."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Mapping, Optional


@dataclass(frozen=True)
class SemanticProfile:
    """Immutable semantic profile definition."""

    profile_id: str
    provider: str
    model_name: str
    model_version: str
    vector_dimension: int
    distance_metric: str
    normalization_policy: str
    chunk_schema_version: str
    chunker_version: str
    compatibility_fingerprint: str
    reranker_defaults: Optional[Dict[str, Any]] = None
    build_metadata: Optional[Dict[str, Any]] = None

    @classmethod
    def from_dict(
        cls,
        profile_id: str,
        payload: Mapping[str, Any],
        *,
        created_at: Optional[str] = None,
        tool_version: str = "unknown",
    ) -> "SemanticProfile":
        """Build profile from config payload and derive compatibility fingerprint."""
        required = [
            "provider",
            "model_name",
            "model_version",
            "vector_dimension",
            "distance_metric",
            "normalization_policy",
            "chunk_schema_version",
            "chunker_version",
        ]
        missing = [key for key in required if key not in payload]
        if missing:
            raise ValueError(
                f"Profile '{profile_id}' missing required fields: {', '.join(sorted(missing))}"
            )

        vector_dimension = int(payload["vector_dimension"])
        if vector_dimension <= 0:
            raise ValueError(f"Profile '{profile_id}' vector_dimension must be > 0")

        canonical = {
            "profile_id": profile_id,
            "provider": str(payload["provider"]),
            "model_name": str(payload["model_name"]),
            "model_version": str(payload["model_version"]),
            "vector_dimension": vector_dimension,
            "distance_metric": str(payload["distance_metric"]),
            "normalization_policy": str(payload["normalization_policy"]),
            "chunk_schema_version": str(payload["chunk_schema_version"]),
            "chunker_version": str(payload["chunker_version"]),
        }

        fingerprint = _compute_compatibility_fingerprint(canonical)

        metadata = payload.get("build_metadata") or {}
        metadata.setdefault(
            "created_at", created_at or datetime.now(timezone.utc).isoformat()
        )
        metadata.setdefault("tool_version", tool_version)

        return cls(
            profile_id=profile_id,
            provider=canonical["provider"],
            model_name=canonical["model_name"],
            model_version=canonical["model_version"],
            vector_dimension=canonical["vector_dimension"],
            distance_metric=canonical["distance_metric"],
            normalization_policy=canonical["normalization_policy"],
            chunk_schema_version=canonical["chunk_schema_version"],
            chunker_version=canonical["chunker_version"],
            compatibility_fingerprint=fingerprint,
            reranker_defaults=payload.get("reranker_defaults"),
            build_metadata=metadata,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize profile for manifests and status endpoints."""
        return {
            "profile_id": self.profile_id,
            "provider": self.provider,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "vector_dimension": self.vector_dimension,
            "distance_metric": self.distance_metric,
            "normalization_policy": self.normalization_policy,
            "chunk_schema_version": self.chunk_schema_version,
            "chunker_version": self.chunker_version,
            "compatibility_fingerprint": self.compatibility_fingerprint,
            "reranker_defaults": self.reranker_defaults,
            "build_metadata": self.build_metadata,
        }


class SemanticProfileRegistry:
    """Registry containing named semantic profiles and default selection."""

    def __init__(
        self,
        profiles: Mapping[str, Mapping[str, Any]],
        default_profile: Optional[str] = None,
        *,
        created_at: Optional[str] = None,
        tool_version: str = "unknown",
    ) -> None:
        if not profiles:
            raise ValueError("Semantic profile registry requires at least one profile")

        self._profiles: Dict[str, SemanticProfile] = {}
        for profile_id, payload in profiles.items():
            if profile_id in self._profiles:
                raise ValueError(f"Duplicate semantic profile ID: {profile_id}")
            self._profiles[profile_id] = SemanticProfile.from_dict(
                profile_id,
                payload,
                created_at=created_at,
                tool_version=tool_version,
            )

        self.default_profile = default_profile or next(iter(self._profiles.keys()))
        if self.default_profile not in self._profiles:
            raise ValueError(
                f"Default semantic profile '{self.default_profile}' is not defined"
            )

    @classmethod
    def from_config_file(
        cls,
        config_path: Path,
        *,
        tool_version: str = "unknown",
    ) -> "SemanticProfileRegistry":
        """Load registry from .mcp-index.json style config file."""
        payload = json.loads(config_path.read_text(encoding="utf-8"))
        profiles = payload.get("semantic_profiles") or {}
        default_profile = payload.get("semantic_default_profile")
        return cls(profiles, default_profile, tool_version=tool_version)

    @classmethod
    def from_raw(
        cls,
        profiles: Mapping[str, Mapping[str, Any]],
        default_profile: Optional[str] = None,
        *,
        tool_version: str = "unknown",
    ) -> "SemanticProfileRegistry":
        """Build registry from in-memory profile payloads."""
        return cls(profiles, default_profile, tool_version=tool_version)

    def get(self, profile_id: Optional[str] = None) -> SemanticProfile:
        """Get profile by ID, defaulting to configured default profile."""
        resolved = profile_id or self.default_profile
        if resolved not in self._profiles:
            raise KeyError(f"Unknown semantic profile '{resolved}'")
        return self._profiles[resolved]

    def list(self) -> Dict[str, SemanticProfile]:
        """Return copy of profile map."""
        return dict(self._profiles)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize registry for diagnostics and manifests."""
        return {
            "semantic_default_profile": self.default_profile,
            "semantic_profiles": {
                profile_id: profile.to_dict()
                for profile_id, profile in self._profiles.items()
            },
        }


def _compute_compatibility_fingerprint(canonical_payload: Mapping[str, Any]) -> str:
    """Compute deterministic compatibility fingerprint for a profile."""
    raw = json.dumps(canonical_payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]
