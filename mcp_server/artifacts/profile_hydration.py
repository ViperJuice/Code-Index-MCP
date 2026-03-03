"""Profile hydration coordination for lexical-first startup behavior."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Mapping, Optional


class HydrationState(str, Enum):
    """Hydration status for a semantic profile."""

    AVAILABLE = "available"
    MISSING = "missing"
    INCOMPATIBLE = "incompatible"


class FallbackStrategy(str, Enum):
    """Runtime fallback strategy for search bootstrap."""

    LEXICAL_ONLY = "lexical_only"
    LEXICAL_THEN_SEMANTIC = "lexical_then_semantic"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class ProfileHydrationStatus:
    """Hydration status for an individual semantic profile."""

    profile_id: str
    status: HydrationState
    reason: str
    expected_fingerprint: Optional[str] = None
    discovered_fingerprint: Optional[str] = None

    def to_dict(self) -> Dict[str, Optional[str]]:
        """Serialize status for APIs and diagnostics."""
        return {
            "status": self.status.value,
            "reason": self.reason,
            "expected_fingerprint": self.expected_fingerprint,
            "discovered_fingerprint": self.discovered_fingerprint,
        }


@dataclass(frozen=True)
class ProfileHydrationReport:
    """Aggregate hydration report for runtime profile activation."""

    lexical_available: bool
    fallback_strategy: FallbackStrategy
    branch: Optional[str]
    commit: Optional[str]
    profiles: Dict[str, ProfileHydrationStatus]

    def to_dict(self) -> Dict[str, object]:
        """Serialize report for status payloads."""
        return {
            "lexical_available": self.lexical_available,
            "fallback_strategy": self.fallback_strategy.value,
            "branch": self.branch,
            "commit": self.commit,
            "profiles": {
                profile_id: status.to_dict()
                for profile_id, status in sorted(self.profiles.items())
            },
        }


class ProfileHydrationCoordinator:
    """Coordinate semantic profile hydration with lexical-safe fallback."""

    def __init__(self, prefer_semantic_when_ready: bool = False) -> None:
        self.prefer_semantic_when_ready = prefer_semantic_when_ready

    def from_index_metadata(
        self,
        requested_profiles: Mapping[str, Optional[str]],
        index_metadata: Optional[Mapping[str, object]],
        *,
        lexical_available: bool,
        branch: Optional[str] = None,
        commit: Optional[str] = None,
    ) -> ProfileHydrationReport:
        """Create hydration report from persisted metadata and requested profiles."""
        discovered = self.extract_discovered_profiles(index_metadata)
        effective_branch = branch or self._coerce_str(index_metadata, "branch")
        effective_commit = commit or self._coerce_str(index_metadata, "commit")
        return self.evaluate(
            requested_profiles=requested_profiles,
            discovered_profiles=discovered,
            lexical_available=lexical_available,
            branch=effective_branch,
            commit=effective_commit,
        )

    def evaluate(
        self,
        requested_profiles: Mapping[str, Optional[str]],
        discovered_profiles: Mapping[str, Optional[str]],
        *,
        lexical_available: bool,
        branch: Optional[str] = None,
        commit: Optional[str] = None,
    ) -> ProfileHydrationReport:
        """Evaluate hydration state and choose a safe fallback strategy."""
        statuses: Dict[str, ProfileHydrationStatus] = {}

        for profile_id, expected_fingerprint in requested_profiles.items():
            discovered_fingerprint = discovered_profiles.get(profile_id)

            if discovered_fingerprint is None:
                statuses[profile_id] = ProfileHydrationStatus(
                    profile_id=profile_id,
                    status=HydrationState.MISSING,
                    reason="profile artifact not found",
                    expected_fingerprint=expected_fingerprint,
                )
                continue

            if expected_fingerprint and discovered_fingerprint != expected_fingerprint:
                statuses[profile_id] = ProfileHydrationStatus(
                    profile_id=profile_id,
                    status=HydrationState.INCOMPATIBLE,
                    reason="compatibility fingerprint mismatch",
                    expected_fingerprint=expected_fingerprint,
                    discovered_fingerprint=discovered_fingerprint,
                )
                continue

            statuses[profile_id] = ProfileHydrationStatus(
                profile_id=profile_id,
                status=HydrationState.AVAILABLE,
                reason="profile artifact is compatible",
                expected_fingerprint=expected_fingerprint,
                discovered_fingerprint=discovered_fingerprint,
            )

        fallback = self._choose_fallback(lexical_available, statuses)
        return ProfileHydrationReport(
            lexical_available=lexical_available,
            fallback_strategy=fallback,
            branch=branch,
            commit=commit,
            profiles=statuses,
        )

    def _choose_fallback(
        self,
        lexical_available: bool,
        statuses: Mapping[str, ProfileHydrationStatus],
    ) -> FallbackStrategy:
        """Choose runtime fallback strategy, lexical-first by default."""
        if not lexical_available:
            return FallbackStrategy.UNAVAILABLE

        if not statuses:
            return FallbackStrategy.LEXICAL_ONLY

        all_available = all(
            status.status is HydrationState.AVAILABLE for status in statuses.values()
        )
        if all_available and self.prefer_semantic_when_ready:
            return FallbackStrategy.LEXICAL_THEN_SEMANTIC

        return FallbackStrategy.LEXICAL_ONLY

    @staticmethod
    def extract_discovered_profiles(
        index_metadata: Optional[Mapping[str, object]],
    ) -> Dict[str, Optional[str]]:
        """Extract profile fingerprints from index metadata formats."""
        if not index_metadata:
            return {}

        discovered: Dict[str, Optional[str]] = {}
        semantic_profiles = index_metadata.get("semantic_profiles")
        if isinstance(semantic_profiles, Mapping):
            for profile_id, payload in semantic_profiles.items():
                if not isinstance(profile_id, str):
                    continue
                if isinstance(payload, Mapping):
                    fingerprint = payload.get("compatibility_fingerprint")
                    if isinstance(fingerprint, str) and fingerprint:
                        discovered[profile_id] = fingerprint
                    else:
                        discovered[profile_id] = None
                elif isinstance(payload, str):
                    discovered[profile_id] = payload
                else:
                    discovered[profile_id] = None

        legacy_profile = index_metadata.get("semantic_profile")
        if (
            isinstance(legacy_profile, str)
            and legacy_profile
            and legacy_profile not in discovered
        ):
            fingerprint = index_metadata.get("compatibility_fingerprint")
            discovered[legacy_profile] = (
                fingerprint if isinstance(fingerprint, str) else None
            )

        return discovered

    @staticmethod
    def _coerce_str(
        metadata: Optional[Mapping[str, object]], key: str
    ) -> Optional[str]:
        if not metadata:
            return None
        value = metadata.get(key)
        return value if isinstance(value, str) and value else None
