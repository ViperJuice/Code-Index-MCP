import json
from pathlib import Path
from types import SimpleNamespace

from click.testing import CliRunner

from mcp_server.cli import cli


def test_history_ingest_wires_filters_and_prints_metadata_only_summary(monkeypatch, tmp_path):
    captured = {}

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "mcp_server.cli.history_commands.get_command_availability",
        lambda _command: SimpleNamespace(available=True, resolved_path="/usr/bin/gh"),
    )

    def _fake_fetch(options):
        captured["options"] = options
        return []

    monkeypatch.setattr("mcp_server.cli.history_commands.fetch_github_issues", _fake_fetch)
    monkeypatch.setattr(
        "mcp_server.cli.history_commands.normalize_github_issue",
        lambda issue, **_kwargs: issue,
    )

    class _FakeStore:
        def __init__(self, _path):
            self.path = _path

        def create_repository(self, _path, _name):
            return 1

        def upsert_history_issue_documents(self, _repository_id, records):
            captured["records"] = records
            return {"stored": len(records), "skipped": 0}

    monkeypatch.setattr("mcp_server.cli.history_commands.SQLiteStore", _FakeStore)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "history",
            "ingest",
            "--repo",
            "owner/repo",
            "--label",
            "phase-complete",
            "--label",
            "reflection",
            "--since",
            "2026-07-01",
            "--until",
            "2026-07-06",
            "--state",
            "closed",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["repo"] == "owner/repo"
    assert payload["filters"]["labels"] == ["phase-complete", "reflection"]
    assert payload["filters"]["since"] == "2026-07-01"
    assert payload["filters"]["until"] == "2026-07-06"
    assert payload["filters"]["state"] == "closed"
    assert payload["redaction_posture"] == "metadata_only"
    assert "token" not in result.output.lower()
    assert captured["options"].repo == "owner/repo"


def test_history_ingest_reports_gh_availability_without_secrets(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "mcp_server.cli.history_commands.get_command_availability",
        lambda _command: SimpleNamespace(available=True, resolved_path="/usr/bin/gh"),
    )
    monkeypatch.setattr("mcp_server.cli.history_commands.fetch_github_issues", lambda _options: [])
    monkeypatch.setattr(
        "mcp_server.cli.history_commands.SQLiteStore",
        lambda _path: SimpleNamespace(
            create_repository=lambda *_args, **_kwargs: 1,
            upsert_history_issue_documents=lambda *_args, **_kwargs: {"stored": 0, "skipped": 0},
        ),
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["history", "ingest", "--repo", "owner/repo"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["gh"]["available"] is True
    assert payload["gh"]["resolved_path"] == "/usr/bin/gh"
