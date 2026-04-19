"""GitHub Actions artifact provider implementation."""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import List, Mapping, Tuple

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
