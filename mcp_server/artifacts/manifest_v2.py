"""Manifest v2 schema for lexical + semantic profile artifact units."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class ManifestUnit:
    """Single logical artifact unit reference."""

    unit_type: str
    unit_id: str
    checksum: str
    size_bytes: int
    profile_id: Optional[str] = None
    compatibility_fingerprint: Optional[str] = None
    transport_ref: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize manifest unit."""
        return {
            "unit_type": self.unit_type,
            "unit_id": self.unit_id,
            "checksum": self.checksum,
            "size_bytes": self.size_bytes,
            "profile_id": self.profile_id,
            "compatibility_fingerprint": self.compatibility_fingerprint,
            "transport_ref": self.transport_ref,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class ArtifactManifestV2:
    """Top-level manifest contract for composable index artifacts."""

    logical_artifact_id: str
    repo_id: str
    branch: str
    commit: str
    schema_version: str
    chunk_schema_version: str
    chunk_identity_algorithm: str
    units: List[ManifestUnit]
    manifest_version: str = "2"

    def validate(self) -> None:
        """Validate manifest invariants required for reliable consumption."""
        if not self.units:
            raise ValueError("Manifest v2 requires at least one unit")

        lexical_units = [u for u in self.units if u.unit_type == "lexical"]
        if len(lexical_units) != 1:
            raise ValueError("Manifest v2 requires exactly one lexical unit")

        seen_ids = set()
        for unit in self.units:
            if unit.unit_id in seen_ids:
                raise ValueError(f"Duplicate manifest unit id: {unit.unit_id}")
            seen_ids.add(unit.unit_id)

            if unit.size_bytes < 0:
                raise ValueError(
                    f"Invalid unit size for {unit.unit_id}: {unit.size_bytes}"
                )

            if unit.unit_type == "semantic_profile":
                if not unit.profile_id:
                    raise ValueError(
                        f"semantic_profile unit missing profile_id: {unit.unit_id}"
                    )
                if not unit.compatibility_fingerprint:
                    raise ValueError(
                        f"semantic_profile unit missing compatibility_fingerprint: {unit.unit_id}"
                    )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize manifest to JSON-compatible dictionary."""
        self.validate()
        return {
            "manifest_version": self.manifest_version,
            "logical_artifact_id": self.logical_artifact_id,
            "repo_id": self.repo_id,
            "branch": self.branch,
            "commit": self.commit,
            "schema_version": self.schema_version,
            "chunk_schema_version": self.chunk_schema_version,
            "chunk_identity_algorithm": self.chunk_identity_algorithm,
            "units": [unit.to_dict() for unit in self.units],
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "ArtifactManifestV2":
        """Create and validate manifest from JSON payload."""
        units = [ManifestUnit(**unit) for unit in payload.get("units", [])]
        manifest = cls(
            manifest_version=str(payload.get("manifest_version", "2")),
            logical_artifact_id=payload["logical_artifact_id"],
            repo_id=payload["repo_id"],
            branch=payload["branch"],
            commit=payload["commit"],
            schema_version=payload["schema_version"],
            chunk_schema_version=payload["chunk_schema_version"],
            chunk_identity_algorithm=payload["chunk_identity_algorithm"],
            units=units,
        )
        manifest.validate()
        return manifest


@dataclass(frozen=True)
class WorkspaceArtifactManifest:
    """Manifest describing a workspace composed of multiple repository artifacts."""

    workspace_id: str
    workspace_commit: str
    repositories: List[Dict[str, Any]]
    manifest_version: str = "1"

    def validate(self) -> None:
        """Validate workspace manifest invariants."""
        if not self.repositories:
            raise ValueError("Workspace manifest requires at least one repository")

        seen_ids = set()
        for repo in self.repositories:
            repo_id = repo.get("repo_id")
            if not repo_id:
                raise ValueError("Workspace manifest repository entry missing repo_id")
            if repo_id in seen_ids:
                raise ValueError(f"Duplicate workspace repository id: {repo_id}")
            seen_ids.add(repo_id)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize workspace manifest."""
        self.validate()
        return {
            "manifest_version": self.manifest_version,
            "workspace_id": self.workspace_id,
            "workspace_commit": self.workspace_commit,
            "repositories": self.repositories,
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "WorkspaceArtifactManifest":
        """Create workspace manifest from JSON payload."""
        manifest = cls(
            manifest_version=str(payload.get("manifest_version", "1")),
            workspace_id=payload["workspace_id"],
            workspace_commit=payload["workspace_commit"],
            repositories=list(payload.get("repositories", [])),
        )
        manifest.validate()
        return manifest
