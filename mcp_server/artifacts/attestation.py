"""Artifact attestation — gh attestation sign/verify with MCP_ATTESTATION_MODE control."""

from __future__ import annotations

import functools
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


def _check_attestation_scope(gh_cmd: str = "gh") -> bool:
    """Return True iff gh auth reports attestations:write scope."""
    result = subprocess.run(
        [gh_cmd, "auth", "status", "--show-token"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return False
    combined = result.stdout + result.stderr
    return "attestations:write" in combined


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
    if not _check_attestation_scope(gh_cmd):
        msg = "ATTESTATION_PREREQ: gh token missing attestations:write scope"
        logger.warning(msg)
        if mode == "enforce":
            raise AttestationError(msg)
        return Attestation(
            bundle_url="",
            bundle_path=Path(""),
            subject_digest=_sha256_of(artifact_path),
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


@functools.lru_cache(maxsize=None)
def probe_gh_attestation_support() -> bool:
    """Return True iff `gh attestation --help` exits 0. Cached per process."""
    try:
        result = subprocess.run(
            ["gh", "attestation", "--help"],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False


def warn_if_gh_attestation_missing() -> None:
    """Log a WARNING if gh attestation is unavailable and mode is enforce."""
    if not probe_gh_attestation_support() and os.environ.get("MCP_ATTESTATION_MODE") == "enforce":
        logger.warning(
            "ATTESTATION_PREREQ: gh attestation subcommand unavailable;"
            " attestation will degrade per MCP_ATTESTATION_MODE"
        )
