"""
Index Manager for MCP Storage

Provides centralized index management functionality for the MCP server.
This is a minimal implementation to support IndexDiscovery operations.
"""

import hashlib
import json
import logging
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class IndexManifest:
    """Manifest metadata describing a SQLite index."""

    schema_version: str
    embedding_model: str
    creation_commit: Optional[str]
    content_hash: str
    created_at: Optional[str] = None
    stable_id_version: Optional[str] = None
    token_model: Optional[str] = None
    total_chunks: Optional[int] = None
    total_tokens: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize manifest to dictionary."""
        return {
            "schema_version": self.schema_version,
            "embedding_model": self.embedding_model,
            "creation_commit": self.creation_commit,
            "content_hash": self.content_hash,
            "created_at": self.created_at,
            "stable_id_version": self.stable_id_version,
            "token_model": self.token_model,
            "total_chunks": self.total_chunks,
            "total_tokens": self.total_tokens,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IndexManifest":
        """Create manifest from dictionary data."""
        return cls(
            schema_version=data.get("schema_version", ""),
            embedding_model=data.get("embedding_model", ""),
            creation_commit=data.get("creation_commit"),
            content_hash=data.get("content_hash", ""),
            created_at=data.get("created_at"),
            stable_id_version=data.get("stable_id_version"),
            token_model=data.get("token_model"),
            total_chunks=data.get("total_chunks"),
            total_tokens=data.get("total_tokens"),
        )


class IndexManager:
    """Manages index storage and retrieval for MCP operations."""

    MANIFEST_SUFFIX = ".manifest.json"

    def __init__(self, storage_strategy: str = "inline"):
        """
        Initialize index manager.

        Args:
            storage_strategy: Strategy for index storage ('inline', 'centralized', etc.)
        """
        self.storage_strategy = storage_strategy
        self.base_storage_path = self._get_base_storage_path()

    def _get_base_storage_path(self) -> Path:
        """Get the base path for index storage based on strategy."""
        if self.storage_strategy == "centralized":
            # Check environment variable first
            env_path = os.environ.get("MCP_INDEX_STORAGE_PATH")
            if env_path:
                return Path(env_path)

            # Default centralized locations
            centralized_paths = [
                Path.home() / ".mcp" / "indexes",
                Path("/tmp/mcp-indexes"),
                Path.cwd() / ".indexes",
            ]

            for path in centralized_paths:
                if path.exists() or path.parent.exists():
                    return path

            # Default to first option
            return centralized_paths[0]
        else:
            # For inline storage, use current directory
            return Path.cwd() / ".mcp-index"

    def get_current_index_path(self, workspace_root: Path) -> Optional[Path]:
        """
        Get the path to the current index for a workspace.

        Args:
            workspace_root: Root directory of the workspace

        Returns:
            Path to the current index, or None if not found
        """
        # Priority search paths in order
        search_paths = [
            # First check data directory (where our actual index is)
            workspace_root / "data" / "code_index.db",
            workspace_root / "data" / "current.db",
            # Then check centralized storage if enabled
            (
                self.base_storage_path / "code_index.db"
                if self.storage_strategy == "centralized"
                else None
            ),
            (
                self.base_storage_path / "current.db"
                if self.storage_strategy == "centralized"
                else None
            ),
            # For centralized with repo ID
            None,  # Will be filled below
            None,  # Will be filled below
            # Finally check legacy inline storage
            workspace_root / ".mcp-index" / "code_index.db",
            workspace_root / ".mcp-index" / "current.db",
        ]

        # Add centralized with repo ID paths
        if self.storage_strategy == "centralized":
            repo_id = self._get_repo_identifier(workspace_root)
            if repo_id:
                search_paths[4] = self.base_storage_path / repo_id / "current.db"
                search_paths[5] = self.base_storage_path / repo_id / "code_index.db"

        # Search all paths
        for path in search_paths:
            if path and path.exists() and self._validate_index(path):
                logger.info(f"Found valid index at: {path}")
                return path

        logger.warning(
            f"No valid index found in {len([p for p in search_paths if p])} searched locations"
        )
        return None

    def _get_repo_identifier(self, workspace_root: Path) -> Optional[str]:
        """Get repository identifier for workspace."""
        try:
            # Try to get git remote URL
            import subprocess

            result = subprocess.run(
                ["git", "config", "--get", "remote.origin.url"],
                capture_output=True,
                text=True,
                cwd=str(workspace_root),
                check=False,
            )
            if result.returncode == 0 and result.stdout.strip():
                url = result.stdout.strip()
                # Create hash from URL
                return hashlib.sha256(url.encode()).hexdigest()[:12]
        except Exception:
            pass

        # Fall back to directory name hash
        return hashlib.sha256(str(workspace_root).encode()).hexdigest()[:12]

    def _validate_index(self, index_path: Path) -> bool:
        """Validate that an index file is a valid SQLite database."""
        try:
            conn = sqlite3.connect(str(index_path))
            # Check for expected tables
            cursor = conn.execute(
                """
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name IN ('files', 'symbols', 'bm25_content')
            """
            )
            tables = {row[0] for row in cursor.fetchall()}
            conn.close()

            # Must have at least files table
            return "files" in tables
        except Exception as e:
            logger.debug(f"Index validation failed for {index_path}: {e}")
            return False

    def list_available_indexes(self) -> List[Dict[str, Any]]:
        """List all available indexes in the storage system."""
        indexes = []

        if self.storage_strategy == "centralized" and self.base_storage_path.exists():
            # Look for indexes in centralized storage
            for repo_dir in self.base_storage_path.iterdir():
                if repo_dir.is_dir():
                    for db_file in repo_dir.glob("*.db"):
                        if self._validate_index(db_file):
                            indexes.append(
                                {
                                    "path": str(db_file),
                                    "repo_id": repo_dir.name,
                                    "size": db_file.stat().st_size,
                                    "modified": db_file.stat().st_mtime,
                                    "storage_type": "centralized",
                                }
                            )

        return indexes

    def create_index_symlink(self, source_path: Path, target_path: Path) -> bool:
        """Create a symlink from target to source index."""
        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            if target_path.exists():
                target_path.unlink()
            target_path.symlink_to(source_path)
            logger.info(f"Created index symlink: {target_path} -> {source_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to create symlink: {e}")
            return False

    def compute_content_hash(self, index_path: Path) -> str:
        """Compute SHA256 hash for a SQLite index file."""
        sha256 = hashlib.sha256()
        with open(index_path, "rb") as index_file:
            for chunk in iter(lambda: index_file.read(1024 * 1024), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _get_manifest_path(self, index_path: Path) -> Path:
        """Return the manifest path that sits next to an index file."""
        return index_path.with_name(f"{index_path.name}{self.MANIFEST_SUFFIX}")

    def get_manifest_path(self, index_path: Path) -> Path:
        """Public helper for determining manifest path for an index file."""
        return self._get_manifest_path(index_path)

    def write_index_manifest(
        self,
        index_path: Path,
        schema_version: str,
        embedding_model: str,
        creation_commit: Optional[str] = None,
        content_hash: Optional[str] = None,
    ) -> Path:
        """Write a manifest describing the given index file."""
        manifest_path = self._get_manifest_path(index_path)
        manifest = IndexManifest(
            schema_version=schema_version,
            embedding_model=embedding_model,
            creation_commit=creation_commit,
            content_hash=content_hash or self.compute_content_hash(index_path),
            created_at=datetime.utcnow().isoformat() + "Z",
        )
        manifest_path.write_text(json.dumps(manifest.to_dict(), indent=2))
        logger.info("Wrote index manifest to %s", manifest_path)
        return manifest_path

    def read_index_manifest(self, index_path: Path) -> Optional[IndexManifest]:
        """Read manifest next to an index path if available."""
        manifest_path = self._get_manifest_path(index_path)
        if not manifest_path.exists():
            return None

        try:
            raw = json.loads(manifest_path.read_text())
            return IndexManifest.from_dict(raw)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load manifest %s: %s", manifest_path, exc)
            return None

    def select_best_index(
        self,
        candidates: List[Dict[str, Any]],
        requested_schema_version: Optional[str] = None,
        requested_embedding_model: Optional[str] = None,
    ) -> Optional[Path]:
        """Select the best index candidate based on requested schema/model preferences."""
        if not candidates:
            return None

        exact_matches: List[Dict[str, Any]] = []
        schema_matches: List[Dict[str, Any]] = []
        model_matches: List[Dict[str, Any]] = []
        fallback: List[Dict[str, Any]] = []

        for candidate in candidates:
            manifest: Optional[IndexManifest] = candidate.get("manifest")
            if manifest:
                schema_ok = (
                    requested_schema_version is None
                    or manifest.schema_version == requested_schema_version
                )
                model_ok = (
                    requested_embedding_model is None
                    or manifest.embedding_model == requested_embedding_model
                )

                if schema_ok and model_ok:
                    exact_matches.append(candidate)
                    continue

                if schema_ok:
                    schema_matches.append(candidate)
                    continue

                if model_ok:
                    model_matches.append(candidate)
                    continue

            fallback.append(candidate)

        if exact_matches:
            return exact_matches[0]["path"]

        if schema_matches:
            if requested_embedding_model:
                logger.warning(
                    "Using index with schema match but different embedding model: requested=%s, found=%s",
                    requested_embedding_model,
                    (
                        schema_matches[0]["manifest"].embedding_model
                        if schema_matches[0].get("manifest")
                        else "unknown"
                    ),
                )
            return schema_matches[0]["path"]

        if model_matches:
            if requested_schema_version:
                logger.warning(
                    "Using index with embedding model match but schema mismatch: requested=%s, found=%s",
                    requested_schema_version,
                    (
                        model_matches[0]["manifest"].schema_version
                        if model_matches[0].get("manifest")
                        else "unknown"
                    ),
                )
            return model_matches[0]["path"]

        if fallback:
            logger.warning("No manifest match found; falling back to first valid index candidate")
            return fallback[0]["path"]

        return None
