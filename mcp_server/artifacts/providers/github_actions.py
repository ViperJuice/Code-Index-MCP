"""GitHub Actions artifact provider implementation."""

from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Mapping, Optional, Tuple

from mcp_server.core.errors import TerminalArtifactError, TransientArtifactError

from .base import ArtifactRecord


def _respect_rate_limit(headers: Mapping[str, str]) -> float:
    remaining = int(headers.get("X-RateLimit-Remaining", "5000"))
    if remaining < 100:
        reset = int(headers.get("X-RateLimit-Reset", str(int(time.time()) + 60)))
        sleep_s = max(0.0, reset - time.time())
        sleep_s = min(sleep_s, 300.0)
        time.sleep(sleep_s)
        return sleep_s
    return 0.0


def _gh_api(gh_cmd: str, path: str, *extra: str) -> Tuple[Mapping[str, str], str]:
    result = subprocess.run(
        [gh_cmd, "api", "--include", path, *extra],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, gh_cmd, result.stdout, result.stderr)
    header_block, _, body = result.stdout.partition("\r\n\r\n")
    if not _:
        # Fallback: some platforms use \n\n
        header_block, _, body = result.stdout.partition("\n\n")
    headers: dict[str, str] = {}
    for line in header_block.splitlines()[1:]:
        if ": " in line:
            k, v = line.split(": ", 1)
            headers[k] = v
    _respect_rate_limit(headers)
    return headers, body


class GitHubActionsArtifactProvider:
    """Artifact provider backed by GitHub Actions artifacts via gh CLI."""

    def __init__(self, repo: str):
        self.repo = repo

    def list_artifacts(self, prefixes: Tuple[str, ...]) -> List[ArtifactRecord]:
        _, body = _gh_api(
            "gh",
            f"/repos/{self.repo}/actions/artifacts",
            "-H",
            "Accept: application/vnd.github+json",
        )
        payload = json.loads(body)

        records: List[ArtifactRecord] = []
        for artifact in payload.get("artifacts", []):
            name = artifact.get("name", "")
            if not name.startswith(prefixes):
                continue
            records.append(
                ArtifactRecord(
                    artifact_id=str(artifact.get("id")),
                    name=name,
                    created_at=artifact.get("created_at", ""),
                    size_bytes=int(artifact.get("size_in_bytes", 0)),
                    metadata={"expires_at": artifact.get("expires_at")},
                )
            )

        records.sort(key=lambda a: a.created_at, reverse=True)
        return records

    def download_artifact(self, artifact_id: str, destination: Path) -> Path:
        # --include is not compatible with --output; skip rate-limit header parsing here.
        destination.mkdir(parents=True, exist_ok=True)
        zip_path = destination / "artifact.zip"
        subprocess.run(
            [
                "gh",
                "api",
                "-H",
                "Accept: application/vnd.github+json",
                f"/repos/{self.repo}/actions/artifacts/{artifact_id}/zip",
                "--output",
                str(zip_path),
            ],
            check=True,
        )
        return zip_path

    def upload_artifact(
        self, artifact_name: str, source_paths: List[Path], retention_days: int
    ) -> str:
        raise NotImplementedError("GitHub artifact upload is handled by Actions workflows")

    def delete_artifact(self, artifact_id: str) -> bool:
        try:
            _gh_api(
                "gh",
                f"/repos/{self.repo}/actions/artifacts/{artifact_id}",
                "-X",
                "DELETE",
                "-H",
                "Accept: application/vnd.github+json",
            )
            return True
        except subprocess.CalledProcessError:
            return False


# ---------------------------------------------------------------------------
# SL-3: Retention janitor — EOF append region
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReleaseRef:
    tag_name: str
    created_at: str  # ISO-8601
    is_latest: bool
    is_draft: bool


_PROTECTED_TAGS = frozenset({"index-latest"})


def delete_releases_older_than(
    repo: str,
    *,
    older_than_days: Optional[int] = None,
    keep_latest_n: Optional[int] = None,
    dry_run: bool = False,
) -> list[ReleaseRef]:
    """Delete (or list, if dry_run) releases matching retention criteria.

    Protection order:
      1. isLatest=True releases and tags in _PROTECTED_TAGS are never deleted.
      2. Age filter: drop releases created more than older_than_days ago.
      3. Keep-latest-N: from remaining candidates, preserve the newest N.
    Returns the set of deleted (or candidate-if-dry_run) releases.
    Raises TerminalArtifactError on 403, TransientArtifactError on 429.
    """
    if older_than_days is None and keep_latest_n is None:
        return []

    result = subprocess.run(
        [
            "gh",
            "release",
            "list",
            "--repo",
            repo,
            "--json",
            "tagName,createdAt,isLatest,isDraft",
            "--limit",
            "1000",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        stderr = result.stderr or ""
        if "403" in stderr:
            raise TerminalArtifactError(f"gh release list failed (403): {stderr}")
        if "429" in stderr:
            raise TransientArtifactError(f"gh release list rate-limited (429): {stderr}")
        raise RuntimeError(f"gh release list failed: {stderr}")

    releases_raw: list[dict] = json.loads(result.stdout)

    all_refs = [
        ReleaseRef(
            tag_name=r["tagName"],
            created_at=r["createdAt"],
            is_latest=r["isLatest"],
            is_draft=r["isDraft"],
        )
        for r in releases_raw
    ]

    # Step 1: Remove protected releases (pointers + isLatest)
    candidates = [
        ref
        for ref in all_refs
        if not ref.is_latest and ref.tag_name not in _PROTECTED_TAGS
    ]

    # Step 2: Age filter
    if older_than_days is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
        candidates = [
            ref
            for ref in candidates
            if datetime.fromisoformat(ref.created_at.replace("Z", "+00:00")) < cutoff
        ]

    # Step 3: Keep-latest-N (sorted newest-first; protect the newest N)
    if keep_latest_n is not None and keep_latest_n > 0:
        # Sort all non-protected refs by date descending to determine "newest N"
        non_protected = sorted(
            [ref for ref in all_refs if not ref.is_latest and ref.tag_name not in _PROTECTED_TAGS],
            key=lambda r: r.created_at,
            reverse=True,
        )
        protected_by_count = {ref.tag_name for ref in non_protected[:keep_latest_n]}
        candidates = [ref for ref in candidates if ref.tag_name not in protected_by_count]

    if dry_run:
        return candidates

    deleted: list[ReleaseRef] = []
    for ref in candidates:
        del_result = subprocess.run(
            ["gh", "release", "delete", ref.tag_name, "--repo", repo, "--yes"],
            capture_output=True,
            text=True,
        )
        if del_result.returncode != 0:
            stderr = del_result.stderr or ""
            if "403" in stderr:
                raise TerminalArtifactError(
                    f"gh release delete {ref.tag_name} failed (403): {stderr}"
                )
            if "429" in stderr:
                _respect_rate_limit(
                    {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": str(int(time.time()) + 60)}
                )
                raise TransientArtifactError(
                    f"gh release delete {ref.tag_name} rate-limited (429): {stderr}"
                )
            raise RuntimeError(f"gh release delete {ref.tag_name} failed: {stderr}")
        deleted.append(ref)

    return deleted
