"""Multi-repository artifact lifecycle coordination."""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from mcp_server.artifacts.artifact_download import IndexArtifactDownloader
from mcp_server.artifacts.artifact_upload import IndexArtifactUploader
from mcp_server.artifacts.manifest_v2 import WorkspaceArtifactManifest
from mcp_server.artifacts.semantic_profiles import extract_semantic_profile_metadata
from mcp_server.core.errors import record_handled_error
from mcp_server.storage.multi_repo_manager import MultiRepositoryManager, RepositoryInfo


@dataclass
class RepoArtifactLifecycleResult:
    """Outcome for a single repository artifact operation."""

    repository_id: str
    repository_name: str
    action: str
    success: bool
    details: Dict[str, Any]
    error: Optional[str] = None


@contextmanager
def _pushd(path: Path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


class MultiRepoArtifactCoordinator:
    """Coordinate artifact lifecycle across registered repositories."""

    def __init__(self, multi_repo_manager: Optional[MultiRepositoryManager] = None) -> None:
        self.multi_repo_manager = multi_repo_manager or MultiRepositoryManager()

    def _iter_repositories(
        self, repository_ids: Optional[Iterable[str]] = None
    ) -> List[RepositoryInfo]:
        repos = self.multi_repo_manager.list_repositories(active_only=True)
        if repository_ids is None:
            return [repo for repo in repos if repo.artifact_enabled]
        wanted = set(repository_ids)
        return [repo for repo in repos if repo.repository_id in wanted]

    def _read_local_profiles(self, repo_path: Path) -> List[str]:
        metadata_path = repo_path / ".index_metadata.json"
        if not metadata_path.exists():
            return []
        try:
            payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        except Exception as exc:
            record_handled_error(__name__, exc)
            return []
        return sorted(extract_semantic_profile_metadata(payload).keys())

    def build_workspace_manifest(
        self, repository_ids: Optional[Iterable[str]] = None
    ) -> WorkspaceArtifactManifest:
        repos = self._iter_repositories(repository_ids)
        repositories = []
        for repo in repos:
            repositories.append(
                {
                    "repo_id": repo.repository_id,
                    "name": repo.name,
                    "path": str(repo.path),
                    "current_commit": repo.current_commit,
                    "last_published_commit": repo.last_published_commit,
                    "last_recovered_commit": repo.last_recovered_commit,
                    "artifact_backend": repo.artifact_backend,
                    "artifact_health": repo.artifact_health,
                    "available_semantic_profiles": repo.available_semantic_profiles or [],
                }
            )

        workspace_commit = "workspace"
        if repos:
            workspace_commit = "+".join(
                sorted(repo.current_commit or repo.repository_id for repo in repos)
            )
        return WorkspaceArtifactManifest(
            workspace_id="multi-repo-workspace",
            workspace_commit=workspace_commit,
            repositories=repositories,
        )

    def get_workspace_status(
        self, repository_ids: Optional[Iterable[str]] = None
    ) -> List[RepoArtifactLifecycleResult]:
        results = []
        for repo in self._iter_repositories(repository_ids):
            results.append(
                RepoArtifactLifecycleResult(
                    repository_id=repo.repository_id,
                    repository_name=repo.name,
                    action="status",
                    success=True,
                    details={
                        "current_commit": repo.current_commit,
                        "last_published_commit": repo.last_published_commit,
                        "last_recovered_commit": repo.last_recovered_commit,
                        "artifact_backend": repo.artifact_backend,
                        "artifact_health": repo.artifact_health,
                        "available_semantic_profiles": repo.available_semantic_profiles or [],
                    },
                )
            )
        return results

    def publish_workspace(
        self, repository_ids: Optional[Iterable[str]] = None
    ) -> List[RepoArtifactLifecycleResult]:
        results = []
        for repo in self._iter_repositories(repository_ids):
            try:
                with _pushd(repo.path):
                    uploader = IndexArtifactUploader()
                    archive_path, checksum, size = uploader.compress_indexes(
                        Path("index-archive.tar.gz"), secure=True
                    )
                    metadata = uploader.create_metadata(checksum, size, secure=True)
                    uploader.upload_direct(archive_path, metadata)
                    archive_path.unlink(missing_ok=True)

                profiles = self._read_local_profiles(repo.path)
                self.multi_repo_manager.registry.update_artifact_state(
                    repo.repository_id,
                    last_published_commit=repo.current_commit,
                    artifact_backend="local_workspace",
                    artifact_health="prepared",
                    available_semantic_profiles=profiles,
                )
                results.append(
                    RepoArtifactLifecycleResult(
                        repository_id=repo.repository_id,
                        repository_name=repo.name,
                        action="publish",
                        success=True,
                        details={
                            "profiles": profiles,
                            "published_commit": repo.current_commit,
                            "artifact_backend": "local_workspace",
                            "prepared_archive": "index-archive.tar.gz",
                        },
                    )
                )
            except Exception as exc:
                results.append(
                    RepoArtifactLifecycleResult(
                        repository_id=repo.repository_id,
                        repository_name=repo.name,
                        action="publish",
                        success=False,
                        details={},
                        error=str(exc),
                    )
                )
        return results

    def fetch_workspace(
        self, repository_ids: Optional[Iterable[str]] = None
    ) -> List[RepoArtifactLifecycleResult]:
        results = []
        for repo in self._iter_repositories(repository_ids):
            try:
                with _pushd(repo.path):
                    downloader = IndexArtifactDownloader()
                    output_dir = Path("artifact_download")
                    output_dir.mkdir(exist_ok=True)
                    try:
                        result = downloader.download_latest(output_dir=output_dir, backup=True)
                    finally:
                        import shutil

                        shutil.rmtree(output_dir, ignore_errors=True)

                artifact = result.artifact or {}
                profiles = self._read_local_profiles(repo.path)
                self.multi_repo_manager.registry.update_artifact_state(
                    repo.repository_id,
                    last_recovered_commit=artifact.get("workflow_run", {}).get("head_sha")
                    or artifact.get("head_sha")
                    or repo.current_commit,
                    artifact_backend=repo.artifact_backend or "github_actions",
                    artifact_health="ready",
                    available_semantic_profiles=profiles,
                )
                results.append(
                    RepoArtifactLifecycleResult(
                        repository_id=repo.repository_id,
                        repository_name=repo.name,
                        action="fetch",
                        success=True,
                        details={
                            "profiles": profiles,
                            "artifact_name": artifact.get("name"),
                            "artifact_id": artifact.get("id"),
                            "recovered_commit": artifact.get("workflow_run", {}).get("head_sha")
                            or artifact.get("head_sha")
                            or repo.current_commit,
                        },
                    )
                )
            except Exception as exc:
                results.append(
                    RepoArtifactLifecycleResult(
                        repository_id=repo.repository_id,
                        repository_name=repo.name,
                        action="fetch",
                        success=False,
                        details={},
                        error=str(exc),
                    )
                )
        return results

    def reconcile_workspace(
        self, repository_ids: Optional[Iterable[str]] = None
    ) -> List[RepoArtifactLifecycleResult]:
        results = []
        for repo in self._iter_repositories(repository_ids):
            has_local_index = (repo.path / "code_index.db").exists()
            health = "ready" if has_local_index else "missing"
            self.multi_repo_manager.registry.update_artifact_state(
                repo.repository_id,
                artifact_health=health,
                available_semantic_profiles=self._read_local_profiles(repo.path),
            )
            results.append(
                RepoArtifactLifecycleResult(
                    repository_id=repo.repository_id,
                    repository_name=repo.name,
                    action="reconcile",
                    success=True,
                    details={
                        "has_local_index": has_local_index,
                        "artifact_health": health,
                        "current_commit": repo.current_commit,
                        "last_published_commit": repo.last_published_commit,
                        "last_recovered_commit": repo.last_recovered_commit,
                        "available_semantic_profiles": self._read_local_profiles(repo.path),
                    },
                )
            )
        return results
