"""GitHub Actions artifact provider implementation."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import List, Tuple

from .base import ArtifactRecord


class GitHubActionsArtifactProvider:
    """Artifact provider backed by GitHub Actions artifacts via gh CLI."""

    def __init__(self, repo: str):
        self.repo = repo

    def list_artifacts(self, prefixes: Tuple[str, ...]) -> List[ArtifactRecord]:
        result = subprocess.run(
            [
                "gh",
                "api",
                "-H",
                "Accept: application/vnd.github+json",
                f"/repos/{self.repo}/actions/artifacts",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        payload = json.loads(result.stdout)

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
        result = subprocess.run(
            [
                "gh",
                "api",
                "-X",
                "DELETE",
                "-H",
                "Accept: application/vnd.github+json",
                f"/repos/{self.repo}/actions/artifacts/{artifact_id}",
            ],
            capture_output=True,
        )
        return result.returncode == 0
