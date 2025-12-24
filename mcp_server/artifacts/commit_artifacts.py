"""Commit-based artifact management for index synchronization.

This module manages index artifacts tied to specific git commits,
enabling efficient sharing and synchronization of indexes.
"""

import json
import logging
import os
import shutil
import tarfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class CommitArtifact:
    """Represents an index artifact for a specific commit."""

    def __init__(self, repo_id: str, commit: str, metadata: Optional[Dict[str, Any]] = None):
        self.repo_id = repo_id
        self.commit = commit
        self.short_commit = commit[:8] if commit else ""
        self.metadata = metadata or {}
        self.artifact_name = f"{repo_id}-{self.short_commit}-index.tar.gz"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "repo_id": self.repo_id,
            "commit": self.commit,
            "artifact_name": self.artifact_name,
            "metadata": self.metadata,
        }


class CommitArtifactManager:
    """Manages index artifacts tied to git commits."""

    def __init__(self, artifacts_dir: str = ".indexes/artifacts"):
        self.artifacts_dir = Path(artifacts_dir)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.artifacts_dir / "artifacts.json"
        self.artifacts_metadata = self._load_metadata()

    def _load_metadata(self) -> Dict[str, Dict[str, Any]]:
        """Load artifacts metadata from disk."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load artifacts metadata: {e}")
        return {}

    def _save_metadata(self) -> None:
        """Save artifacts metadata to disk."""
        try:
            with open(self.metadata_file, "w") as f:
                json.dump(self.artifacts_metadata, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save artifacts metadata: {e}")

    def create_commit_artifact(self, repo_id: str, commit: str, index_path: Path) -> Optional[Path]:
        """Create artifact for specific commit.

        Args:
            repo_id: Repository ID
            commit: Git commit SHA
            index_path: Path to index directory

        Returns:
            Path to created artifact or None
        """
        if not index_path.exists():
            logger.error(f"Index path does not exist: {index_path}")
            return None

        artifact = CommitArtifact(repo_id, commit)
        artifact_path = self.artifacts_dir / artifact.artifact_name

        try:
            # Create metadata for artifact
            metadata = {
                "repo_id": repo_id,
                "commit": commit,
                "created": datetime.now().isoformat(),
                "compatible_with": self._get_compatibility_info(),
                "index_stats": self._get_index_stats(index_path),
            }

            # Create temporary directory for artifact contents
            temp_dir = self.artifacts_dir / f"temp_{repo_id}_{commit[:8]}"
            temp_dir.mkdir(exist_ok=True)

            try:
                # Copy index files
                self._copy_index_files(index_path, temp_dir)

                # Add metadata
                metadata_path = temp_dir / "artifact-metadata.json"
                with open(metadata_path, "w") as f:
                    json.dump(metadata, f, indent=2)

                # Create tarball
                with tarfile.open(artifact_path, "w:gz", compresslevel=9) as tar:
                    for item in temp_dir.iterdir():
                        tar.add(item, arcname=item.name)

                # Update artifacts metadata
                self.artifacts_metadata[artifact.artifact_name] = metadata
                self._save_metadata()

                logger.info(f"Created artifact: {artifact.artifact_name}")
                return artifact_path

            finally:
                # Clean up temp directory
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)

        except Exception as e:
            logger.error(f"Failed to create artifact: {e}")
            if artifact_path.exists():
                artifact_path.unlink()
            return None

    def extract_commit_artifact(self, repo_id: str, commit: str, target_path: Path) -> bool:
        """Extract artifact for specific commit.

        Args:
            repo_id: Repository ID
            commit: Git commit SHA
            target_path: Path to extract to

        Returns:
            True if successful
        """
        artifact = CommitArtifact(repo_id, commit)
        artifact_path = self.artifacts_dir / artifact.artifact_name

        if not artifact_path.exists():
            logger.error(f"Artifact not found: {artifact.artifact_name}")
            return False

        try:
            # Create target directory
            target_path.mkdir(parents=True, exist_ok=True)

            # Extract artifact
            with tarfile.open(artifact_path, "r:gz") as tar:
                tar.extractall(target_path)

            logger.info(f"Extracted artifact: {artifact.artifact_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to extract artifact: {e}")
            return False

    def list_artifacts(self, repo_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List available artifacts.

        Args:
            repo_id: Optional repository ID to filter by

        Returns:
            List of artifact metadata
        """
        artifacts = []

        for artifact_name, metadata in self.artifacts_metadata.items():
            if repo_id and metadata.get("repo_id") != repo_id:
                continue

            artifact_path = self.artifacts_dir / artifact_name
            if artifact_path.exists():
                metadata["size_mb"] = artifact_path.stat().st_size / (1024 * 1024)
                artifacts.append(metadata)

        # Sort by creation date, newest first
        artifacts.sort(key=lambda x: x.get("created", ""), reverse=True)

        return artifacts

    def cleanup_old_artifacts(self, repo_id: str, keep_last: int = 5) -> int:
        """Remove old commit artifacts, keeping only recent ones.

        Args:
            repo_id: Repository ID
            keep_last: Number of artifacts to keep

        Returns:
            Number of artifacts removed
        """
        # Get artifacts for this repo
        repo_artifacts = [
            (name, meta)
            for name, meta in self.artifacts_metadata.items()
            if meta.get("repo_id") == repo_id
        ]

        # Sort by creation date
        repo_artifacts.sort(key=lambda x: x[1].get("created", ""), reverse=True)

        removed = 0

        # Remove old artifacts
        for artifact_name, metadata in repo_artifacts[keep_last:]:
            artifact_path = self.artifacts_dir / artifact_name
            if artifact_path.exists():
                try:
                    artifact_path.unlink()
                    del self.artifacts_metadata[artifact_name]
                    removed += 1
                    logger.info(f"Removed old artifact: {artifact_name}")
                except Exception as e:
                    logger.error(f"Failed to remove artifact {artifact_name}: {e}")

        if removed > 0:
            self._save_metadata()

        return removed

    def get_artifact_info(self, repo_id: str, commit: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific artifact.

        Args:
            repo_id: Repository ID
            commit: Git commit SHA

        Returns:
            Artifact metadata or None
        """
        artifact = CommitArtifact(repo_id, commit)
        return self.artifacts_metadata.get(artifact.artifact_name)

    def has_artifact(self, repo_id: str, commit: str) -> bool:
        """Check if artifact exists for commit.

        Args:
            repo_id: Repository ID
            commit: Git commit SHA

        Returns:
            True if artifact exists
        """
        artifact = CommitArtifact(repo_id, commit)
        artifact_path = self.artifacts_dir / artifact.artifact_name
        return artifact_path.exists()

    def _get_compatibility_info(self) -> Dict[str, Any]:
        """Get compatibility information for artifact."""
        return {
            "mcp_version": "1.0.0",  # TODO: Get from package
            "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}",
            "index_schema_version": "1.0",
        }

    def _get_index_stats(self, index_path: Path) -> Dict[str, Any]:
        """Get statistics about the index."""
        stats = {"files": 0, "size_mb": 0}

        # Count database files
        db_files = list(index_path.glob("*.db"))
        stats["files"] = len(db_files)

        # Calculate total size
        total_size = 0
        for db_file in db_files:
            total_size += db_file.stat().st_size

        stats["size_mb"] = total_size / (1024 * 1024)

        return stats

    def _copy_index_files(self, source: Path, target: Path) -> None:
        """Copy index files to target directory.

        Args:
            source: Source index directory
            target: Target directory
        """
        # Copy database files
        for db_file in source.glob("*.db"):
            shutil.copy2(db_file, target / db_file.name)

        # Copy metadata files
        for json_file in source.glob("*.json"):
            shutil.copy2(json_file, target / json_file.name)

        # Copy vector index if present
        vector_dir = source / "vector_index.qdrant"
        if vector_dir.exists():
            shutil.copytree(vector_dir, target / "vector_index.qdrant")

    def get_latest_artifact(self, repo_id: str) -> Optional[str]:
        """Get the latest artifact commit for a repository.

        Args:
            repo_id: Repository ID

        Returns:
            Commit SHA of latest artifact or None
        """
        repo_artifacts = [
            meta for meta in self.artifacts_metadata.values() if meta.get("repo_id") == repo_id
        ]

        if not repo_artifacts:
            return None

        # Sort by creation date
        repo_artifacts.sort(key=lambda x: x.get("created", ""), reverse=True)

        return repo_artifacts[0].get("commit")
