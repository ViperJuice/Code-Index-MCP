"""Multi-repository artifact lifecycle coordination."""

from __future__ import annotations

import json
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

    def _read_local_profiles(
        self, repo_path: Path, index_location: Path | str | None = None
    ) -> List[str]:
        metadata_path = (
            Path(index_location) / ".index_metadata.json"
            if index_location is not None
            else repo_path / ".mcp-index" / ".index_metadata.json"
        )
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
                index_location = Path(repo.index_location or repo.index_path.parent)
                archive_path = index_location / "index-archive.tar.gz"
                uploader = IndexArtifactUploader()
                archive_path, checksum, size = uploader.compress_indexes(
                    archive_path,
                    secure=True,
                    repo_path=repo.path,
                    index_location=index_location,
                    index_path=repo.index_path,
                )
                metadata = uploader.create_metadata(
                    checksum,
                    size,
                    secure=True,
                    repo_id=repo.repository_id,
                    tracked_branch=repo.tracked_branch or repo.current_branch or "main",
                    commit=repo.current_commit or "unknown",
                    index_location=index_location,
                    index_path=repo.index_path,
                )
                try:
                    uploader.upload_direct(archive_path, metadata)
                    health = "prepared"
                except Exception:
                    health = "publish_failed"
                    raise
                finally:
                    archive_path.unlink(missing_ok=True)

                profiles = self._read_local_profiles(repo.path, index_location)
                self.multi_repo_manager.registry.update_artifact_state(
                    repo.repository_id,
                    last_published_commit=repo.current_commit,
                    artifact_backend="local_workspace",
                    artifact_health=health,
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
                downloader = IndexArtifactDownloader()
                index_location = Path(repo.index_location or repo.index_path.parent)
                output_dir = index_location / "artifact_download"
                output_dir.mkdir(parents=True, exist_ok=True)
                try:
                    result = downloader.download_latest(
                        output_dir=output_dir,
                        backup=True,
                        repo_id=repo.repository_id,
                        repo_path=repo.path,
                        tracked_branch=repo.tracked_branch or repo.current_branch or "main",
                        target_commit=repo.current_commit,
                        index_location=index_location,
                        index_path=repo.index_path,
                    )
                finally:
                    import shutil

                    shutil.rmtree(output_dir, ignore_errors=True)

                artifact = result.artifact or {}
                profiles = self._read_local_profiles(repo.path, repo.index_location)
                health = "ready" if Path(repo.index_path).exists() else "missing"
                if health != "ready":
                    raise RuntimeError(f"Artifact download did not hydrate {repo.index_path}")
                self.multi_repo_manager.registry.update_artifact_state(
                    repo.repository_id,
                    last_recovered_commit=artifact.get("workflow_run", {}).get("head_sha")
                    or artifact.get("head_sha")
                    or repo.current_commit,
                    artifact_backend=repo.artifact_backend or "github_actions",
                    artifact_health=health,
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
            has_local_index = Path(repo.index_path).exists()
            health = "ready" if has_local_index else "missing"
            self.multi_repo_manager.registry.update_artifact_state(
                repo.repository_id,
                artifact_health=health,
                available_semantic_profiles=self._read_local_profiles(
                    repo.path, repo.index_location
                ),
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
                        "available_semantic_profiles": self._read_local_profiles(
                            repo.path, repo.index_location
                        ),
                    },
                )
            )
        return results
