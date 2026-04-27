from click.testing import CliRunner

from mcp_server.cli.preflight_commands import PreflightResult, preflight, run_preflight


class _NoRegisteredRepo:
    def get_repository_by_path(self, path):
        return None


def test_preflight_reports_ready_state(monkeypatch):
    runner = CliRunner()
    monkeypatch.setattr(
        "mcp_server.cli.preflight_commands.run_preflight",
        lambda: PreflightResult(status="ready", checks=[]),
    )

    result = runner.invoke(preflight)

    assert result.exit_code == 0
    assert "Preflight ready" in result.output


def test_preflight_warns_when_behind_remote(monkeypatch):
    runner = CliRunner()
    monkeypatch.setattr(
        "mcp_server.cli.preflight_commands._get_git_ref_info",
        lambda: {"head": "abc", "branch": "main"},
    )
    monkeypatch.setattr(
        "mcp_server.cli.preflight_commands._get_artifact_identity",
        lambda: {"commit": "abc"},
    )
    monkeypatch.setattr(
        "mcp_server.cli.preflight_commands._get_upstream_ref",
        lambda: "origin/main",
    )
    monkeypatch.setattr(
        "mcp_server.cli.preflight_commands._get_ahead_behind",
        lambda upstream: (0, 5),
    )
    monkeypatch.setattr(
        "mcp_server.cli.preflight_commands._verify_local_index_restored",
        lambda: True,
    )
    monkeypatch.setattr(
        "mcp_server.cli.preflight_commands._get_local_drift",
        lambda: (
            type("Detector", (), {"should_use_incremental": lambda self, changes: True})(),
            [],
        ),
    )
    monkeypatch.setattr("mcp_server.cli.preflight_commands.RepositoryRegistry", _NoRegisteredRepo)

    result = runner.invoke(preflight)

    assert result.exit_code == 0
    assert "behind origin/main by 5 commit(s)" in result.output
    assert "git pull --rebase" in result.output


def test_preflight_warns_when_runtime_files_missing(monkeypatch):
    runner = CliRunner()
    monkeypatch.setattr(
        "mcp_server.cli.preflight_commands._get_git_ref_info",
        lambda: {"head": "abc", "branch": "main"},
    )
    monkeypatch.setattr(
        "mcp_server.cli.preflight_commands._get_artifact_identity",
        lambda: {"commit": None},
    )
    monkeypatch.setattr(
        "mcp_server.cli.preflight_commands._get_upstream_ref",
        lambda: None,
    )
    monkeypatch.setattr(
        "mcp_server.cli.preflight_commands._verify_local_index_restored",
        lambda: False,
    )
    monkeypatch.setattr("mcp_server.cli.preflight_commands.RepositoryRegistry", _NoRegisteredRepo)

    result = runner.invoke(preflight)

    assert result.exit_code == 0
    assert "Local runtime index files are missing" in result.output
    assert "mcp-index artifact pull --latest" in result.output


def test_preflight_warns_when_artifact_differs_from_head(monkeypatch):
    runner = CliRunner()
    monkeypatch.setattr(
        "mcp_server.cli.preflight_commands._get_git_ref_info",
        lambda: {"head": "head123", "branch": "main"},
    )
    monkeypatch.setattr(
        "mcp_server.cli.preflight_commands._get_artifact_identity",
        lambda: {"commit": "artifact123"},
    )
    monkeypatch.setattr(
        "mcp_server.cli.preflight_commands._get_upstream_ref",
        lambda: None,
    )
    monkeypatch.setattr(
        "mcp_server.cli.preflight_commands._verify_local_index_restored",
        lambda: True,
    )
    monkeypatch.setattr(
        "mcp_server.cli.preflight_commands._get_local_drift",
        lambda: (
            type("Detector", (), {"should_use_incremental": lambda self, changes: True})(),
            [],
        ),
    )
    monkeypatch.setattr("mcp_server.cli.preflight_commands.RepositoryRegistry", _NoRegisteredRepo)

    result = runner.invoke(preflight)

    assert result.exit_code == 0
    assert "Restored artifact commit differs from local HEAD" in result.output
    assert "mcp-index artifact sync" in result.output


def test_preflight_handles_no_remote(monkeypatch):
    runner = CliRunner()
    monkeypatch.setattr(
        "mcp_server.cli.preflight_commands._get_git_ref_info",
        lambda: {"head": "abc", "branch": "main"},
    )
    monkeypatch.setattr(
        "mcp_server.cli.preflight_commands._get_artifact_identity",
        lambda: {"commit": "abc"},
    )
    monkeypatch.setattr(
        "mcp_server.cli.preflight_commands._get_upstream_ref",
        lambda: None,
    )
    monkeypatch.setattr(
        "mcp_server.cli.preflight_commands._verify_local_index_restored",
        lambda: True,
    )
    monkeypatch.setattr(
        "mcp_server.cli.preflight_commands._get_local_drift",
        lambda: (
            type("Detector", (), {"should_use_incremental": lambda self, changes: True})(),
            [],
        ),
    )
    monkeypatch.setattr("mcp_server.cli.preflight_commands.RepositoryRegistry", _NoRegisteredRepo)

    result = runner.invoke(preflight)

    assert result.exit_code == 0
    assert "No upstream remote is configured" in result.output


def test_preflight_warns_when_registered_repo_index_is_empty(monkeypatch):
    monkeypatch.setattr(
        "mcp_server.cli.preflight_commands._get_git_ref_info",
        lambda: {"head": "abc", "branch": "main"},
    )
    monkeypatch.setattr(
        "mcp_server.cli.preflight_commands._get_artifact_identity",
        lambda: {"commit": "abc"},
    )
    monkeypatch.setattr("mcp_server.cli.preflight_commands._get_upstream_ref", lambda: None)
    monkeypatch.setattr(
        "mcp_server.cli.preflight_commands._verify_local_index_restored",
        lambda: True,
    )
    monkeypatch.setattr(
        "mcp_server.cli.preflight_commands._get_local_drift",
        lambda: (
            type("Detector", (), {"should_use_incremental": lambda self, changes: True})(),
            [],
        ),
    )

    class FakeRegistry:
        def get_repository_by_path(self, path):
            return object()

    readiness = type(
        "Readiness",
        (),
        {
            "ready": False,
            "state": type("State", (), {"value": "index_empty"})(),
            "remediation": "Run reindex to populate the repository index.",
        },
    )()
    monkeypatch.setattr("mcp_server.cli.preflight_commands.RepositoryRegistry", FakeRegistry)
    monkeypatch.setattr(
        "mcp_server.cli.preflight_commands.ReadinessClassifier.classify_registered",
        lambda repo_info, requested_path=None: readiness,
    )

    result = run_preflight()

    assert result.status == "warning"
    assert any("readiness is index_empty" in check.message for check in result.checks)
