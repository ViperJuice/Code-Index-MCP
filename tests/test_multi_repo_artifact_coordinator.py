from datetime import datetime
from pathlib import Path

from click.testing import CliRunner

from mcp_server.artifacts.manifest_v2 import WorkspaceArtifactManifest
from mcp_server.artifacts.multi_repo_artifact_coordinator import (
    MultiRepoArtifactCoordinator,
)
from mcp_server.cli.artifact_commands import artifact
from mcp_server.storage.multi_repo_manager import MultiRepositoryManager, RepositoryInfo


def _repo_info(repo_id: str, path: Path) -> RepositoryInfo:
    return RepositoryInfo(
        repository_id=repo_id,
        name=path.name,
        path=path,
        index_path=path / ".mcp-index" / "current.db",
        language_stats={},
        total_files=0,
        total_symbols=0,
        indexed_at=datetime.now(),
        current_commit=f"commit-{repo_id}",
        artifact_enabled=True,
        active=True,
    )


def test_workspace_manifest_roundtrip():
    manifest = WorkspaceArtifactManifest(
        workspace_id="ws",
        workspace_commit="abc",
        repositories=[{"repo_id": "r1", "name": "repo1"}],
    )
    payload = manifest.to_dict()
    restored = WorkspaceArtifactManifest.from_dict(payload)
    assert restored.workspace_id == "ws"
    assert restored.repositories[0]["repo_id"] == "r1"


def test_repository_registry_persists_artifact_state(tmp_path: Path):
    manager = MultiRepositoryManager(central_index_path=tmp_path / "registry.json")
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    repo_info = _repo_info("repo-1", repo_path)
    manager.registry.register(repo_info)

    manager.registry.update_artifact_state(
        "repo-1",
        last_published_commit="abc123",
        last_recovered_commit="def456",
        available_semantic_profiles=["commercial_high", "oss_high"],
        artifact_backend="github_actions",
        artifact_health="ready",
    )

    reloaded = MultiRepositoryManager(central_index_path=tmp_path / "registry.json")

    # The registry _load() re-keys legacy ids to the canonical sha256 derived
    # from the resolved path, so look the repo up by its new canonical id.
    all_repos = reloaded.registry.list_all()
    assert len(all_repos) == 1, "expected exactly one repository in the reloaded registry"
    stored = all_repos[0]
    assert stored is not None
    assert stored.last_published_commit == "abc123"
    assert stored.last_recovered_commit == "def456"
    assert stored.available_semantic_profiles == ["commercial_high", "oss_high"]
    assert stored.artifact_backend == "github_actions"
    assert stored.artifact_health == "ready"


def test_coordinator_fetch_updates_registry(monkeypatch, tmp_path: Path):
    manager = MultiRepositoryManager(central_index_path=tmp_path / "registry.json")
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    repo_info = _repo_info("repo-1", repo_path)
    manager.registry.register(repo_info)

    (repo_path / ".index_metadata.json").write_text(
        '{"semantic_profiles": {"commercial_high": {}, "oss_high": {}}}',
        encoding="utf-8",
    )

    def _fake_download_latest(self, output_dir, backup=True, full_only=False):
        (repo_path / "code_index.db").write_text("db", encoding="utf-8")
        return type("Result", (), {"artifact": {"head_sha": "recover123"}})()

    monkeypatch.setattr(
        "mcp_server.artifacts.multi_repo_artifact_coordinator.IndexArtifactDownloader.download_latest",
        _fake_download_latest,
    )
    monkeypatch.setattr(
        "mcp_server.artifacts.multi_repo_artifact_coordinator.IndexArtifactDownloader._detect_repository",
        lambda self: "owner/repo",
    )

    coordinator = MultiRepoArtifactCoordinator(manager)
    results = coordinator.fetch_workspace(["repo-1"])

    assert results[0].success is True
    stored = manager.get_repository_info("repo-1")
    assert stored is not None
    assert stored.last_recovered_commit == "recover123"
    assert stored.available_semantic_profiles == ["commercial_high", "oss_high"]
    assert stored.artifact_health == "ready"


def test_reconcile_workspace_marks_missing_or_ready(tmp_path: Path):
    manager = MultiRepositoryManager(central_index_path=tmp_path / "registry.json")
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    repo_info = _repo_info("repo-1", repo_path)
    manager.registry.register(repo_info)

    coordinator = MultiRepoArtifactCoordinator(manager)
    results = coordinator.reconcile_workspace(["repo-1"])
    assert results[0].details["artifact_health"] == "missing"

    (repo_path / "code_index.db").write_text("db", encoding="utf-8")
    results = coordinator.reconcile_workspace(["repo-1"])
    assert results[0].details["artifact_health"] == "ready"


def test_publish_workspace_uses_local_first_wording(monkeypatch, tmp_path: Path):
    manager = MultiRepositoryManager(central_index_path=tmp_path / "registry.json")
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    repo_info = _repo_info("repo-1", repo_path)
    manager.registry.register(repo_info)

    (repo_path / ".index_metadata.json").write_text(
        '{"semantic_profiles": {"commercial_high": {}, "oss_high": {}}}',
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "mcp_server.artifacts.multi_repo_artifact_coordinator.IndexArtifactUploader.compress_indexes",
        lambda self, output_path, secure=True: (Path(output_path), "checksum", 123),
    )
    monkeypatch.setattr(
        "mcp_server.artifacts.multi_repo_artifact_coordinator.IndexArtifactUploader.create_metadata",
        lambda self, checksum, size, secure=True: {"ok": True},
    )
    monkeypatch.setattr(
        "mcp_server.artifacts.multi_repo_artifact_coordinator.IndexArtifactUploader.upload_direct",
        lambda self, archive_path, metadata: None,
    )
    monkeypatch.setattr(
        "mcp_server.artifacts.multi_repo_artifact_coordinator.IndexArtifactUploader._detect_repository",
        lambda self: "owner/repo",
    )

    results = MultiRepoArtifactCoordinator(manager).publish_workspace(["repo-1"])
    assert results[0].success is True
    assert results[0].details["artifact_backend"] == "local_workspace"
    assert results[0].details["prepared_archive"] == "index-archive.tar.gz"


def test_workspace_status_cli_reports_registered_repositories(monkeypatch, tmp_path: Path):
    runner = CliRunner()
    manager = MultiRepositoryManager(central_index_path=tmp_path / "registry.json")
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    repo_info = _repo_info("repo-1", repo_path)
    repo_info.available_semantic_profiles = ["commercial_high", "oss_high"]
    repo_info.artifact_health = "ready"
    manager.registry.register(repo_info)

    monkeypatch.setattr(
        "mcp_server.cli.artifact_commands.MultiRepoArtifactCoordinator",
        lambda: MultiRepoArtifactCoordinator(manager),
    )

    result = runner.invoke(artifact, ["workspace-status"])

    assert result.exit_code == 0
    assert "Workspace manifest" in result.output
    assert "repo-1" in result.output
    assert "commercial_high" in result.output
