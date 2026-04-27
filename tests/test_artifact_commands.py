from datetime import datetime
from pathlib import Path

from click.testing import CliRunner

from mcp_server.artifacts.multi_repo_artifact_coordinator import MultiRepoArtifactCoordinator
from mcp_server.cli.artifact_commands import _run_incremental_reconcile, artifact
from mcp_server.indexing.change_detector import FileChange
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
        current_commit="current-commit",
        tracked_branch="main",
        current_branch="main",
        artifact_enabled=True,
        active=True,
    )


def test_artifact_pull_confirms_local_restore(monkeypatch, tmp_path):
    runner = CliRunner()

    def _fake_download_latest(self, output_dir, backup=True, full_only=False, **kwargs):
        Path(".mcp-index").mkdir(exist_ok=True)
        Path(".mcp-index/current.db").write_text("db", encoding="utf-8")
        return type("Result", (), {"validation_reasons": []})()

    monkeypatch.setattr(
        "mcp_server.cli.artifact_commands.IndexArtifactDownloader.download_latest",
        _fake_download_latest,
    )
    monkeypatch.setattr(
        "mcp_server.cli.artifact_commands.IndexArtifactDownloader._detect_repository",
        lambda self: "owner/repo",
    )
    monkeypatch.setattr(
        "mcp_server.cli.artifact_commands._print_reconcile_guidance",
        lambda: print("guidance"),
    )

    with runner.isolated_filesystem(temp_dir=str(tmp_path)):
        result = runner.invoke(artifact, ["pull", "--latest"])

    assert result.exit_code == 0
    assert "Local index files restored" in result.output
    assert "current.db" in result.output
    assert "guidance" in result.output


def test_artifact_pull_fails_when_no_index_restored(monkeypatch, tmp_path):
    runner = CliRunner()

    monkeypatch.setattr(
        "mcp_server.cli.artifact_commands.IndexArtifactDownloader.download_latest",
        lambda self, output_dir, backup=True, full_only=False, **kwargs: None,
    )
    monkeypatch.setattr(
        "mcp_server.cli.artifact_commands.IndexArtifactDownloader._detect_repository",
        lambda self: "owner/repo",
    )
    monkeypatch.setattr(
        "mcp_server.cli.artifact_commands._print_reconcile_guidance",
        lambda: print("guidance"),
    )

    with runner.isolated_filesystem(temp_dir=str(tmp_path)):
        result = runner.invoke(artifact, ["pull", "--latest"])

    assert result.exit_code != 0
    assert "no local index files were restored" in result.output.lower()


def test_artifact_recover_confirms_local_restore(monkeypatch, tmp_path):
    runner = CliRunner()

    def _fake_recover(self, branch, commit, output_dir, backup=True, **kwargs):
        Path(".mcp-index").mkdir(exist_ok=True)
        Path(".mcp-index/artifact-metadata.json").write_text("{}", encoding="utf-8")
        return type("Result", (), {"validation_reasons": []})()

    monkeypatch.setattr(
        "mcp_server.cli.artifact_commands.IndexArtifactDownloader.recover",
        _fake_recover,
    )
    monkeypatch.setattr(
        "mcp_server.cli.artifact_commands.IndexArtifactDownloader._detect_repository",
        lambda self: "owner/repo",
    )

    with runner.isolated_filesystem(temp_dir=str(tmp_path)):
        result = runner.invoke(artifact, ["recover", "--branch", "main"])

    assert result.exit_code == 0
    assert "Local index files restored" in result.output
    assert "artifact-metadata.json" in result.output
    assert "Git drift could not be determined" in result.output


def test_artifact_sync_bootstraps_local_indexes(monkeypatch, tmp_path):
    runner = CliRunner()

    def _fake_download_latest(self, output_dir, backup=True, full_only=False, **kwargs):
        Path(".mcp-index").mkdir(exist_ok=True)
        Path(".mcp-index/.index_metadata.json").write_text("{}", encoding="utf-8")

    monkeypatch.setattr(
        "mcp_server.cli.artifact_commands.IndexArtifactDownloader.download_latest",
        _fake_download_latest,
    )
    monkeypatch.setattr(
        "mcp_server.cli.artifact_commands.IndexArtifactDownloader._detect_repository",
        lambda self: "owner/repo",
    )
    monkeypatch.setattr(
        "mcp_server.cli.artifact_commands._print_reconcile_guidance",
        lambda: print("guidance"),
    )
    monkeypatch.setattr(
        "mcp_server.cli.artifact_commands._get_local_drift",
        lambda: (
            type("Detector", (), {"should_use_incremental": lambda self, changes: False})(),
            [],
        ),
    )

    with runner.isolated_filesystem(temp_dir=str(tmp_path)):
        result = runner.invoke(artifact, ["sync"])

    assert result.exit_code == 0
    assert "Indexes synchronized!" in result.output
    assert ".index_metadata.json" in result.output
    assert "guidance" in result.output


def test_artifact_sync_reports_existing_local_drift(monkeypatch, tmp_path):
    runner = CliRunner()
    monkeypatch.setattr(
        "mcp_server.cli.artifact_commands._print_reconcile_guidance",
        lambda: print("guidance"),
    )
    monkeypatch.setattr(
        "mcp_server.cli.artifact_commands._get_local_drift",
        lambda: (
            type("Detector", (), {"should_use_incremental": lambda self, changes: False})(),
            [object()],
        ),
    )

    with runner.isolated_filesystem(temp_dir=str(tmp_path)):
        Path(".mcp-index").mkdir(exist_ok=True)
        Path(".mcp-index/current.db").write_text("db", encoding="utf-8")
        result = runner.invoke(artifact, ["sync"])

    assert result.exit_code == 0
    assert "guidance" in result.output
    assert "too large for automatic incremental sync" in result.output.lower()


def test_incremental_reconcile_uses_python_plugin_without_preindex(monkeypatch, tmp_path):
    calls = []

    class FakePythonPlugin:
        lang = "python"

        def __init__(self, sqlite_store=None, preindex=True):
            calls.append(preindex)

        def supports(self, path):
            return True

        def indexFile(self, path, content):
            return {"file": str(path), "symbols": [], "language": "python"}

    monkeypatch.chdir(tmp_path)
    Path(".mcp-index").mkdir(exist_ok=True)
    Path(".mcp-index/current.db").write_text("placeholder", encoding="utf-8")
    monkeypatch.setattr("mcp_server.cli.artifact_commands.SQLiteStore", lambda path: object())
    monkeypatch.setattr("mcp_server.cli.artifact_commands.PythonPlugin", FakePythonPlugin)
    monkeypatch.setattr(
        "mcp_server.cli.artifact_commands.EnhancedDispatcher",
        lambda **kwargs: object(),
    )

    class FakeIndexer:
        def __init__(self, store, dispatcher, repo_path):
            pass

        def update_from_changes(self, changes):
            return type(
                "Stats",
                (),
                {
                    "files_indexed": 1,
                    "files_removed": 0,
                    "files_moved": 0,
                    "files_skipped": 0,
                    "errors": 0,
                },
            )()

    monkeypatch.setattr("mcp_server.cli.artifact_commands.IncrementalIndexer", FakeIndexer)

    result = _run_incremental_reconcile([FileChange("mcp_server/example.py", "modified")])

    assert result is True
    assert calls == [False]


def test_workspace_fetch_cli_prints_validation_truth(monkeypatch, tmp_path):
    runner = CliRunner()
    manager = MultiRepositoryManager(central_index_path=tmp_path / "registry.json")
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    repo_info = _repo_info("repo-1", repo_path)
    manager.registry.register(repo_info)

    (repo_path / ".mcp-index").mkdir(exist_ok=True)
    (repo_path / ".mcp-index" / "current.db").write_text("db", encoding="utf-8")
    (repo_path / ".mcp-index" / "artifact-metadata.json").write_text(
        '{"commit":"recover123","tracked_branch":"main","branch":"main","checksum":"checksum-123","schema_version":"2","semantic_profile_hash":"'
        + ("a" * 64)
        + '"}',
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "mcp_server.cli.artifact_commands.MultiRepoArtifactCoordinator",
        lambda: MultiRepoArtifactCoordinator(manager),
    )
    monkeypatch.setattr(
        "mcp_server.artifacts.multi_repo_artifact_coordinator.IndexArtifactDownloader.download_latest",
        lambda self, output_dir, backup=True, full_only=False, **kwargs: type(
            "Result",
            (),
            {
                "artifact": {"head_sha": "recover123", "id": 23, "name": "repo-artifact"},
                "validation_reasons": [],
            },
        )(),
    )
    monkeypatch.setattr(
        "mcp_server.artifacts.multi_repo_artifact_coordinator.IndexArtifactDownloader._detect_repository",
        lambda self: "owner/repo",
    )

    result = runner.invoke(artifact, ["fetch-workspace", "--repository", "repo-1"])

    assert result.exit_code == 0
    assert "validation_status: passed" in result.output
    assert "last_recovered_commit: recover123" in result.output
    assert "schema_version" in result.output
