from pathlib import Path
from subprocess import CompletedProcess

from click.testing import CliRunner

from mcp_server.cli.artifact_commands import artifact


def test_artifact_pull_confirms_local_restore(monkeypatch, tmp_path):
    runner = CliRunner()

    def _fake_run(cmd, capture_output=True, text=True):
        Path("code_index.db").write_text("db", encoding="utf-8")
        return CompletedProcess(cmd, 0, stdout="downloaded\n", stderr="")

    monkeypatch.setattr("mcp_server.cli.artifact_commands.subprocess.run", _fake_run)
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

    def _fake_run(cmd, capture_output=True, text=True):
        return CompletedProcess(cmd, 0, stdout="downloaded\n", stderr="")

    monkeypatch.setattr("mcp_server.cli.artifact_commands.subprocess.run", _fake_run)
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

    def _fake_run(cmd, capture_output=True, text=True):
        Path("artifact-metadata.json").write_text("{}", encoding="utf-8")
        return CompletedProcess(cmd, 0, stdout="recovered\n", stderr="")

    monkeypatch.setattr("mcp_server.cli.artifact_commands.subprocess.run", _fake_run)

    with runner.isolated_filesystem(temp_dir=str(tmp_path)):
        result = runner.invoke(artifact, ["recover", "--branch", "main"])

    assert result.exit_code == 0
    assert "Local index files restored" in result.output
    assert "artifact-metadata.json" in result.output
    assert "Git drift could not be determined" in result.output


def test_artifact_sync_bootstraps_local_indexes(monkeypatch, tmp_path):
    runner = CliRunner()

    def _fake_run(cmd, capture_output=True, text=True):
        Path(".index_metadata.json").write_text("{}", encoding="utf-8")
        return CompletedProcess(cmd, 0, stdout="downloaded\n", stderr="")

    monkeypatch.setattr("mcp_server.cli.artifact_commands.subprocess.run", _fake_run)
    monkeypatch.setattr(
        "mcp_server.cli.artifact_commands._print_reconcile_guidance",
        lambda: print("guidance"),
    )

    with runner.isolated_filesystem(temp_dir=str(tmp_path)):
        result = runner.invoke(artifact, ["sync"])

    assert result.exit_code == 0
    assert "Indexes synchronized!" in result.output
    assert ".index_metadata.json" in result.output
    assert "guidance" in result.output


def test_artifact_sync_reports_existing_local_drift(monkeypatch, tmp_path):
    runner = CliRunner()

    def _fake_run(cmd, capture_output=True, text=True):
        return CompletedProcess(
            cmd,
            0,
            stdout="Available Index Artifacts:\nindex-main 10MB\n",
            stderr="",
        )

    monkeypatch.setattr("mcp_server.cli.artifact_commands.subprocess.run", _fake_run)
    monkeypatch.setattr(
        "mcp_server.cli.artifact_commands._print_reconcile_guidance",
        lambda: print("guidance"),
    )

    with runner.isolated_filesystem(temp_dir=str(tmp_path)):
        Path("code_index.db").write_text("db", encoding="utf-8")
        result = runner.invoke(artifact, ["sync"])

    assert result.exit_code == 0
    assert "guidance" in result.output
    assert "Remote artifacts available" in result.output
