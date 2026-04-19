"""Artifact utilities and provider abstractions."""

from .artifact_download import IndexArtifactDownloader
from .freshness import FreshnessVerdict, verify_artifact_freshness
from .artifact_upload import IndexArtifactUploader
from .integrity_gate import (
    ArtifactIntegrityGateResult,
    validate_artifact_integrity,
    validate_required_metadata_fields,
)
from .manifest_v2 import ArtifactManifestV2, ManifestUnit, WorkspaceArtifactManifest
from .profile_hydration import (
    FallbackStrategy,
    HydrationState,
    ProfileHydrationCoordinator,
    ProfileHydrationReport,
    ProfileHydrationStatus,
)
from .secure_export import SecureIndexExporter
from .semantic_namespace import SemanticNamespaceResolver
from .semantic_profiles import SemanticProfile, SemanticProfileRegistry

__all__ = [
    "FreshnessVerdict",
    "verify_artifact_freshness",
    "ArtifactManifestV2",
    "ArtifactIntegrityGateResult",
    "IndexArtifactDownloader",
    "IndexArtifactUploader",
    "FallbackStrategy",
    "HydrationState",
    "ManifestUnit",
    "ProfileHydrationCoordinator",
    "ProfileHydrationReport",
    "ProfileHydrationStatus",
    "SecureIndexExporter",
    "SemanticNamespaceResolver",
    "SemanticProfile",
    "SemanticProfileRegistry",
    "WorkspaceArtifactManifest",
    "validate_artifact_integrity",
    "validate_required_metadata_fields",
]
