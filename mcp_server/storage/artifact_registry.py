"""
Artifact registry for published index artifacts.

This module provides a lightweight, file-backed registry that tracks
published index artifacts by repository, model, and version. It is used
by the dispatcher, CLI tools, and discovery utilities to locate and
reuse existing indexes without re-downloading or rebuilding them.
"""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp_server.core.path_utils import PathUtils

logger = logging.getLogger(__name__)


@dataclass
class ArtifactRecord:
    """Represents a single index artifact entry."""

    repo_id: str
    model: str
    version: str
    path: Path
    commit: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    size_bytes: int = 0
    source: str = "local"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert record to a JSON-serializable dictionary."""
        return {
            "repo_id": self.repo_id,
            "model": self.model,
            "version": self.version,
            "path": str(self.path),
            "commit": self.commit,
            "created_at": self.created_at.isoformat(),
            "size_bytes": self.size_bytes,
            "source": self.source,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ArtifactRecord":
        """Create a record from serialized data."""
        return cls(
            repo_id=data["repo_id"],
            model=data["model"],
            version=data["version"],
            path=Path(data["path"]),
            commit=data.get("commit"),
            created_at=datetime.fromisoformat(data["created_at"])
            if isinstance(data.get("created_at"), str)
            else datetime.utcnow(),
            size_bytes=data.get("size_bytes", 0),
            source=data.get("source", "local"),
            metadata=data.get("metadata", {}),
        )


class ArtifactRegistry:
    """File-backed catalog of index artifacts."""

    def __init__(self, registry_path: Optional[Path] = None):
        self.registry_path = registry_path or PathUtils.get_index_storage_path() / "artifact_registry.json"
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._records: Dict[str, ArtifactRecord] = {}
        self._load()

    def _record_key(self, repo_id: str, model: str, version: str) -> str:
        return f"{repo_id}:{model}:{version}"

    def _load(self) -> None:
        """Load registry data from disk."""
        if not self.registry_path.exists():
            return

        try:
            with open(self.registry_path, "r") as f:
                data = json.load(f)

            for key, record_data in data.items():
                try:
                    self._records[key] = ArtifactRecord.from_dict(record_data)
                except Exception as e:
                    logger.warning(f"Skipping invalid artifact record {key}: {e}")
        except Exception as e:
            logger.error(f"Failed to load artifact registry: {e}")
            self._records = {}

    def _save(self) -> None:
        """Persist registry data to disk."""
        with self._lock:
            try:
                serialized = {key: record.to_dict() for key, record in self._records.items()}
                temp_path = self.registry_path.with_suffix(".tmp")
                with open(temp_path, "w") as f:
                    json.dump(serialized, f, indent=2)
                temp_path.replace(self.registry_path)
            except Exception as e:
                logger.error(f"Failed to save artifact registry: {e}")

    def _calculate_size(self, path: Path) -> int:
        """Calculate total size of a file or directory in bytes."""
        if not path.exists():
            return 0

        if path.is_file():
            return path.stat().st_size

        total = 0
        for item in path.rglob("*"):
            if item.is_file():
                total += item.stat().st_size
        return total

    def add_or_update(
        self,
        repo_id: str,
        model: str,
        version: str,
        path: Path,
        commit: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        source: str = "local",
    ) -> ArtifactRecord:
        """Add or update an artifact record."""
        record = ArtifactRecord(
            repo_id=repo_id,
            model=model,
            version=version,
            path=path.resolve(),
            commit=commit,
            size_bytes=self._calculate_size(path),
            source=source,
            metadata=metadata or {},
        )

        with self._lock:
            self._records[self._record_key(repo_id, model, version)] = record
            self._save()

        return record

    def list_records(self, repo_id: Optional[str] = None, model: Optional[str] = None) -> List[ArtifactRecord]:
        """List artifacts, optionally filtering by repo or model."""
        with self._lock:
            records = list(self._records.values())

        if repo_id:
            records = [r for r in records if r.repo_id == repo_id]
        if model:
            records = [r for r in records if r.model == model]

        return sorted(records, key=lambda r: r.created_at, reverse=True)

    def find_best_match(self, repo_id: str, model: Optional[str] = None) -> Optional[ArtifactRecord]:
        """Find the best artifact for the repo/model pair."""
        candidates = self.list_records(repo_id=repo_id)
        if model:
            model_matches = [c for c in candidates if c.model == model]
            if model_matches:
                candidates = model_matches

        return candidates[0] if candidates else None

    def get_record(self, repo_id: str, model: str, version: str) -> Optional[ArtifactRecord]:
        """Retrieve a specific artifact record."""
        return self._records.get(self._record_key(repo_id, model, version))

