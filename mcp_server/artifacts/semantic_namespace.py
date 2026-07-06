"""Deterministic namespace helpers for semantic collection naming."""

from __future__ import annotations

import hashlib
import re
from urllib.parse import urlsplit
from typing import Optional


class SemanticNamespaceResolver:
    """Resolve profile-isolated semantic collection namespace identifiers."""

    _MAX_COMPONENT_LENGTH = 48
    _INVALID_CHARS = re.compile(r"[^a-z0-9-]+")
    _DASH_RUN = re.compile(r"-{2,}")

    def derive_repo_hash(self, repo_identifier: str) -> str:
        """Derive deterministic short hash for a repository identifier."""
        normalized = (repo_identifier or "").strip() or "unknown-repo"
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12]

    def derive_lineage_id(self, branch: Optional[str], commit: Optional[str]) -> str:
        """Derive deterministic lineage token from branch and commit."""
        branch_token = (branch or "").strip().lower()
        commit_token = (commit or "").strip().lower()

        if not branch_token and not commit_token:
            return "workspace"

        canonical = f"{branch_token}::{commit_token}"
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:12]

    def sanitize_profile_id(self, profile_id: str) -> str:
        """Sanitize profile identifier for safe collection naming."""
        normalized = (profile_id or "").strip().lower().replace("_", "-")
        normalized = self._INVALID_CHARS.sub("-", normalized)
        normalized = self._DASH_RUN.sub("-", normalized)
        normalized = normalized.strip("-")

        if not normalized:
            return "default"

        return normalized[: self._MAX_COMPONENT_LENGTH]

    def resolve_collection_name(
        self,
        repo_identifier: str,
        profile_id: str,
        lineage_id: str,
    ) -> str:
        """Resolve collection name using deterministic namespace contract."""
        repo_hash = self.derive_repo_hash(repo_identifier)
        profile_segment = self.sanitize_profile_id(profile_id)
        lineage_segment = self.sanitize_profile_id(lineage_id)
        return f"ci__{repo_hash}__{profile_segment}__{lineage_segment}"

    def normalize_collection_name(self, collection_name: Optional[str]) -> Optional[str]:
        """Normalize collection identity for deterministic comparisons."""
        if not isinstance(collection_name, str):
            return None
        normalized = collection_name.strip().lower()
        return normalized or None

    def normalize_distance_metric(self, metric: Optional[object]) -> Optional[str]:
        """Normalize distance metric identifiers for deterministic comparisons."""
        if metric is None:
            return None
        value = getattr(metric, "value", metric)
        if not isinstance(value, str):
            value = str(value)
        normalized = value.strip().lower()
        if not normalized:
            return None
        aliases = {
            "cosine": "cosine",
            "dot": "dot",
            "dotproduct": "dot",
            "euclid": "euclidean",
            "euclidean": "euclidean",
            "manhattan": "manhattan",
        }
        return aliases.get(normalized, normalized)

    def normalize_endpoint_identity(self, endpoint: Optional[str]) -> Optional[str]:
        """Normalize endpoint identity without probing network state."""
        if not isinstance(endpoint, str):
            return None
        raw = endpoint.strip()
        if not raw:
            return None
        parsed = urlsplit(raw)
        scheme = parsed.scheme.lower() if parsed.scheme else "http"
        hostname = (parsed.hostname or "").lower()
        if not hostname:
            return raw.rstrip("/") or None
        default_port = 443 if scheme == "https" else 80 if scheme == "http" else None
        port = f":{parsed.port}" if parsed.port and parsed.port != default_port else ""
        path = parsed.path.rstrip("/")
        return f"{scheme}://{hostname}{port}{path}"
