"""Local filesystem artifact provider."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import List, Tuple

from .base import ArtifactRecord


class LocalFilesystemArtifactProvider:
    """Provider storing artifacts on local filesystem."""

    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def list_artifacts(self, prefixes: Tuple[str, ...]) -> List[ArtifactRecord]:
        records: List[ArtifactRecord] = []
        for file_path in self.root_dir.glob("*.zip"):
            name = file_path.stem
            if not name.startswith(prefixes):
                continue
            stat = file_path.stat()
            records.append(
                ArtifactRecord(
                    artifact_id=name,
                    name=name,
                    created_at=str(int(stat.st_mtime)),
                    size_bytes=stat.st_size,
                )
            )
        records.sort(key=lambda a: a.created_at, reverse=True)
        return records

    def download_artifact(self, artifact_id: str, destination: Path) -> Path:
        source = self.root_dir / f"{artifact_id}.zip"
        if not source.exists():
            raise FileNotFoundError(f"Artifact not found: {artifact_id}")
        destination.mkdir(parents=True, exist_ok=True)
        target = destination / "artifact.zip"
        shutil.copy2(source, target)
        return target

    def upload_artifact(
        self, artifact_name: str, source_paths: List[Path], retention_days: int
    ) -> str:
        # Local provider stores only first payload path as zip artifact.
        if not source_paths:
            raise ValueError("source_paths is required")
        source = source_paths[0]
        target = self.root_dir / f"{artifact_name}.zip"
        shutil.copy2(source, target)
        return artifact_name

    def delete_artifact(self, artifact_id: str) -> bool:
        path = self.root_dir / f"{artifact_id}.zip"
        if not path.exists():
            return False
        path.unlink()
        return True
