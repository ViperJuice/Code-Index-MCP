"""Amazon S3 artifact provider."""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

from .base import ArtifactRecord


class S3ArtifactProvider:
    """S3 provider placeholder for production remote cache."""

    def __init__(self, bucket: str, prefix: str = ""):
        self.bucket = bucket
        self.prefix = prefix

    def list_artifacts(self, prefixes: Tuple[str, ...]) -> List[ArtifactRecord]:
        raise NotImplementedError("S3 artifact listing not yet implemented")

    def download_artifact(self, artifact_id: str, destination: Path) -> Path:
        raise NotImplementedError("S3 artifact download not yet implemented")

    def upload_artifact(
        self, artifact_name: str, source_paths: List[Path], retention_days: int
    ) -> str:
        raise NotImplementedError("S3 artifact upload not yet implemented")

    def delete_artifact(self, artifact_id: str) -> bool:
        raise NotImplementedError("S3 artifact delete not yet implemented")
