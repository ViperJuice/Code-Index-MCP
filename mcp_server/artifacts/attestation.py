"""Artifact attestation — gh attestation sign/verify with MCP_ATTESTATION_MODE control."""

from __future__ import annotations

import hashlib
import logging
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from mcp_server.core.errors import ArtifactError

logger = logging.getLogger(__name__)


class AttestationError(ArtifactError):
    pass


@dataclass(frozen=True)
class Attestation:
    bundle_url: str
    bundle_path: Path
    subject_digest: str
    signed_at: datetime


def _sha256_of(path: Path) -> str:
    sha256 = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def _parse_bundle_url(stdout: str) -> str:
    match = re.search(r"https://github\.com/\S+/attestations/\S+", stdout)
    return match.group(0) if match else ""


def attest(artifact_path: Path, *, repo: str, gh_cmd: str = "gh") -> Attestation:
    mode = os.environ.get("MCP_ATTESTATION_MODE", "enforce")
    if mode == "skip":
        return Attestation(
            bundle_url="",
            bundle_path=Path(""),
            subject_digest="",
            signed_at=datetime.now(timezone.utc),
        )
    sidecar = artifact_path.with_suffix(artifact_path.suffix + ".attestation.jsonl")
    result = subprocess.run(
        [gh_cmd, "attestation", "sign", str(artifact_path), "--repo", repo, "--bundle", str(sidecar)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        msg = f"gh attestation sign failed (exit {result.returncode}): {result.stderr.strip()}"
        if mode == "enforce":
            raise AttestationError(msg)
        logger.warning(msg)
        return Attestation(
            bundle_url="",
            bundle_path=sidecar,
            subject_digest=_sha256_of(artifact_path),
            signed_at=datetime.now(timezone.utc),
        )
    bundle_url = _parse_bundle_url(result.stdout) or f"file://{sidecar}"
    return Attestation(
        bundle_url=bundle_url,
        bundle_path=sidecar,
        subject_digest=_sha256_of(artifact_path),
        signed_at=datetime.now(timezone.utc),
    )


def verify_attestation(
    archive_path: Path,
    attestation: Attestation,
    *,
    expected_repo: str,
    gh_cmd: str = "gh",
) -> None:
    mode = os.environ.get("MCP_ATTESTATION_MODE", "enforce")
    if mode == "skip":
        return
    result = subprocess.run(
        [
            gh_cmd, "attestation", "verify", str(archive_path),
            "--bundle", str(attestation.bundle_path),
            "--repo", expected_repo,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        msg = f"gh attestation verify failed (exit {result.returncode}): {result.stderr.strip()}"
        if mode == "enforce":
            raise AttestationError(msg)
        logger.warning(msg)
