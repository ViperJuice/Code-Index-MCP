"""Azure Blob artifact provider placeholder."""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

from .base import ArtifactRecord


class AzureBlobArtifactProvider:
    """Azure Blob provider placeholder for future implementation."""

    def __init__(self, container: str, prefix: str = ""):
        self.container = container
        self.prefix = prefix

    def list_artifacts(self, prefixes: Tuple[str, ...]) -> List[ArtifactRecord]:
        raise NotImplementedError("Azure artifact listing not yet implemented")

    def download_artifact(self, artifact_id: str, destination: Path) -> Path:
        raise NotImplementedError("Azure artifact download not yet implemented")

    def upload_artifact(
        self, artifact_name: str, source_paths: List[Path], retention_days: int
    ) -> str:
        raise NotImplementedError("Azure artifact upload not yet implemented")

    def delete_artifact(self, artifact_id: str) -> bool:
        raise NotImplementedError("Azure artifact delete not yet implemented")
