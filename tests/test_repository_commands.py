from datetime import datetime
from pathlib import Path

from click.testing import CliRunner

from mcp_server.cli.repository_commands import repository
from mcp_server.storage.multi_repo_manager import RepositoryInfo


def _repo_info(tmp_path: Path) -> RepositoryInfo:
    repo_path = tmp_path / "repo"
    repo_path.mkdir(exist_ok=True)
    index_base = repo_path / ".mcp-index"
    index_base.mkdir(exist_ok=True)
    return RepositoryInfo(
        repository_id="repo-1",
        name="repo",
        path=repo_path,
        index_path=index_base / "current.db",
        language_stats={"python": 1},
        total_files=1,
        total_symbols=1,
        indexed_at=datetime.now(),
        current_commit="abcdef123456",
        current_branch="main",
        artifact_enabled=True,
        artifact_backend="local_workspace",
        artifact_health="ready",
        available_semantic_profiles=["commercial_high", "oss_high"],
        index_location=str(index_base),
    )


def test_register_sets_local_first_defaults(monkeypatch, tmp_path: Path):
    runner = CliRunner()
    repo_path = tmp_path / "repo"
    repo_path.mkdir()

    class FakeRegistry:
        def register_repository(
            self, path, auto_sync=True, artifact_enabled=True, priority=0
        ):
            return "repo-1"

        def set_artifact_enabled(self, repo_id, enabled):
            return True

        def get_repository(self, repo_id):
            return _repo_info(tmp_path)

    monkeypatch.setattr(
        "mcp_server.cli.repository_commands.RepositoryRegistry", FakeRegistry
    )

    result = runner.invoke(repository, ["register", str(repo_path)])

    assert result.exit_code == 0
    assert "Artifact backend: local_workspace" in result.output
    assert (
        "Artifact health: ready" in result.output
        or "Artifact health: missing" in result.output
    )


def test_list_shows_artifact_readiness_fields(monkeypatch, tmp_path: Path):
    runner = CliRunner()
    repo_info = _repo_info(tmp_path)
    repo_info.last_recovered_commit = "abcdef123456"

    class FakeRegistry:
        def get_all_repositories(self):
            return {"repo-1": repo_info}

    monkeypatch.setattr(
        "mcp_server.cli.repository_commands.RepositoryRegistry", FakeRegistry
    )

    result = runner.invoke(repository, ["list", "-v"])

    assert result.exit_code == 0
    assert "Artifact backend: local_workspace" in result.output
    assert "Artifact health: ready" in result.output
    assert "Semantic profiles: commercial_high, oss_high" in result.output


def test_unregister_removes_repo_from_registry(monkeypatch, tmp_path: Path):
    runner = CliRunner()
    repo_info = _repo_info(tmp_path)

    class FakeRegistry:
        def get_repository(self, repo_id):
            return repo_info

        def get_all_repositories(self):
            return {"repo-1": repo_info}

        def unregister_repository(self, repo_id):
            return True

    monkeypatch.setattr(
        "mcp_server.cli.repository_commands.RepositoryRegistry", FakeRegistry
    )
    monkeypatch.setattr(
        "mcp_server.cli.repository_commands.click.confirm", lambda prompt: True
    )

    result = runner.invoke(repository, ["unregister", "repo-1"])

    assert result.exit_code == 0
    assert "Unregistered repository: repo" in result.output


def test_sync_guidance_matches_local_first_workflow(monkeypatch, tmp_path: Path):
    runner = CliRunner()
    repo_info = _repo_info(tmp_path)

    class FakeRegistry:
        def get_repository_by_path(self, path):
            return repo_info

        def get_repository(self, repo_id):
            return repo_info

        def update_current_commit(self, repo_id):
            return None

    class FakeResult:
        action = "downloaded"
        error = None

    class FakeIndexManager:
        def __init__(self, registry, dispatcher=None):
            pass

        def sync_repository_index(self, repo_id, force_full=False):
            return FakeResult()

    monkeypatch.setattr(
        "mcp_server.cli.repository_commands.RepositoryRegistry", FakeRegistry
    )
    monkeypatch.setattr(
        "mcp_server.cli.repository_commands.GitAwareIndexManager", FakeIndexManager
    )
    monkeypatch.setattr(
        "mcp_server.cli.repository_commands.EnhancedDispatcher",
        lambda sqlite_store=None: object(),
    )
    monkeypatch.setattr(
        "mcp_server.cli.repository_commands.SQLiteStore", lambda path: object()
    )

    result = runner.invoke(repository, ["sync"])

    assert result.exit_code == 0
    assert "Downloaded index from artifact" in result.output
    assert "artifact reconcile-workspace" in result.output
