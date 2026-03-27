from pathlib import Path

from click.testing import CliRunner

from mcp_server.cli.artifact_commands import _run_incremental_reconcile, artifact
from mcp_server.indexing.change_detector import FileChange


def test_artifact_pull_confirms_local_restore(monkeypatch, tmp_path):
    runner = CliRunner()

    def _fake_download_latest(self, output_dir, backup=True, full_only=False):
        Path("code_index.db").write_text("db", encoding="utf-8")

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
    assert "code_index.db" in result.output
    assert "guidance" in result.output


def test_artifact_pull_fails_when_no_index_restored(monkeypatch, tmp_path):
    runner = CliRunner()

    monkeypatch.setattr(
        "mcp_server.cli.artifact_commands.IndexArtifactDownloader.download_latest",
        lambda self, output_dir, backup=True, full_only=False: None,
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

    def _fake_recover(self, branch, commit, output_dir, backup=True):
        Path("artifact-metadata.json").write_text("{}", encoding="utf-8")

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

    def _fake_download_latest(self, output_dir, backup=True, full_only=False):
        Path(".index_metadata.json").write_text("{}", encoding="utf-8")

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
        Path("code_index.db").write_text("db", encoding="utf-8")
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
    Path("code_index.db").write_text("placeholder", encoding="utf-8")
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
