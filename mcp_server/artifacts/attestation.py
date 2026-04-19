"""Artifact attestation stubs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from mcp_server.core.errors import ArtifactError


class AttestationError(ArtifactError):
    pass


@dataclass(frozen=True)
class Attestation:
    bundle_url: str
    bundle_path: Path
    subject_digest: str
    signed_at: datetime


def attest(artifact_path: Path, *, repo: str, gh_cmd: str = "gh") -> Attestation:
    raise NotImplementedError("filled by SL-3")


def verify_attestation(
    archive_path: Path,
    attestation: Attestation,
    *,
    expected_repo: str,
    gh_cmd: str = "gh",
) -> None:
    raise NotImplementedError("filled by SL-3")
