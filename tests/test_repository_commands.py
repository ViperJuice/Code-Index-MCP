import sqlite3
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from click.testing import CliRunner

from mcp_server.cli.repository_commands import repository
from mcp_server.storage.multi_repo_manager import RepositoryInfo


def _repo_info(tmp_path: Path) -> RepositoryInfo:
    repo_path = tmp_path / "repo"
    repo_path.mkdir(exist_ok=True)
    index_base = repo_path / ".mcp-index"
    index_base.mkdir(exist_ok=True)
    index_path = index_base / "current.db"
    conn = sqlite3.connect(index_path)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS files (id INTEGER PRIMARY KEY, path TEXT, is_deleted BOOLEAN DEFAULT 0)"
    )
    conn.execute("INSERT INTO files (path, is_deleted) VALUES ('README.md', 0)")
    conn.commit()
    conn.close()
    return RepositoryInfo(
        repository_id="repo-1",
        name="repo",
        path=repo_path,
        index_path=index_path,
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
        def register_repository(self, path, auto_sync=True, artifact_enabled=True, priority=0):
            return "repo-1"

        def set_artifact_enabled(self, repo_id, enabled):
            return True

        def get_repository(self, repo_id):
            return _repo_info(tmp_path)

    monkeypatch.setattr("mcp_server.cli.repository_commands.RepositoryRegistry", FakeRegistry)

    result = runner.invoke(repository, ["register", str(repo_path)])

    assert result.exit_code == 0
    assert "Artifact backend: local_workspace" in result.output
    assert "Artifact health: ready" in result.output or "Artifact health: missing" in result.output


def test_list_shows_artifact_readiness_fields(monkeypatch, tmp_path: Path):
    runner = CliRunner()
    repo_info = _repo_info(tmp_path)
    repo_info.last_recovered_commit = "abcdef123456"

    class FakeRegistry:
        def get_all_repositories(self):
            return {"repo-1": repo_info}

    monkeypatch.setattr("mcp_server.cli.repository_commands.RepositoryRegistry", FakeRegistry)

    result = runner.invoke(repository, ["list", "-v"])

    assert result.exit_code == 0
    assert "Artifact backend: local_workspace" in result.output
    assert "Artifact health: ready" in result.output
    assert "Semantic profiles: commercial_high, oss_high" in result.output
    assert "Readiness: ready" in result.output
    assert "Rollout status: ready" in result.output
    assert "Query surface: ready" in result.output


def test_register_surfaces_multiple_worktrees_error(monkeypatch, tmp_path: Path):
    from mcp_server.storage.repository_registry import MultipleWorktreesUnsupportedError

    runner = CliRunner()
    registered = tmp_path / "registered"
    requested = tmp_path / "requested"
    git_common = tmp_path / "common.git"
    requested.mkdir()

    class FakeRegistry:
        def register_repository(self, path, auto_sync=True, artifact_enabled=True, priority=0):
            raise MultipleWorktreesUnsupportedError(
                registered_path=registered,
                requested_path=requested,
                git_common_dir=git_common,
            )

    monkeypatch.setattr("mcp_server.cli.repository_commands.RepositoryRegistry", FakeRegistry)

    result = runner.invoke(repository, ["register", str(requested)])

    assert result.exit_code == 1
    assert "multiple_worktrees_unsupported" in result.output
    assert str(registered.resolve()) in result.output
    assert str(requested.resolve()) in result.output
    assert "unregister" in result.output


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

    monkeypatch.setattr("mcp_server.cli.repository_commands.RepositoryRegistry", FakeRegistry)
    monkeypatch.setattr("mcp_server.cli.repository_commands.click.confirm", lambda prompt: True)

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
        def __init__(self, registry, dispatcher=None, **kwargs):
            pass

        def sync_repository_index(self, repo_id, force_full=False):
            return FakeResult()

    monkeypatch.setattr("mcp_server.cli.repository_commands.RepositoryRegistry", FakeRegistry)
    monkeypatch.setattr("mcp_server.cli.repository_commands.GitAwareIndexManager", FakeIndexManager)
    monkeypatch.setattr(
        "mcp_server.cli.repository_commands.EnhancedDispatcher",
        lambda sqlite_store=None: object(),
    )
    monkeypatch.setattr("mcp_server.cli.repository_commands.SQLiteStore", lambda path: object())

    result = runner.invoke(repository, ["sync"])

    assert result.exit_code == 0
    assert "Downloaded index from artifact" in result.output
    assert "artifact reconcile-workspace" in result.output


def test_status_reports_rollout_and_query_surfaces(monkeypatch, tmp_path: Path):
    runner = CliRunner()
    repo_info = _repo_info(tmp_path)
    repo_info.staleness_reason = "partial_index_failure"

    class FakeRegistry:
        def get_repository_by_path(self, path):
            return repo_info

    class FakeStoreRegistry:
        @classmethod
        def for_registry(cls, registry):
            return object()

    class FakeRepoResolver:
        def __init__(self, registry, store_registry):
            pass

    class FakeIndexManager:
        def __init__(self, registry, repo_resolver=None, store_registry=None):
            pass

        def get_repository_status(self, repo_id):
            return {
                "repo_id": repo_info.repository_id,
                "name": repo_info.name,
                "path": repo_info.path,
                "current_commit": repo_info.current_commit,
                "last_indexed_commit": repo_info.last_indexed_commit,
                "last_indexed": repo_info.last_indexed,
                "needs_update": True,
                "auto_sync": repo_info.auto_sync,
                "artifact_enabled": repo_info.artifact_enabled,
                "artifact_backend": repo_info.artifact_backend,
                "artifact_health": repo_info.artifact_health,
                "index_exists": True,
                "index_size_mb": 0.1,
                "readiness": "stale_commit",
                "ready": False,
                "remediation": "Run reindex to update the repository index to the current commit.",
                "rollout_status": "partial_index_failure",
                "rollout_remediation": "A required incremental mutation failed.",
                "query_status": "index_unavailable",
                "query_remediation": 'Use native search or follow the readiness remediation; query tools stay fail-closed with safe_fallback: "native_search".',
                "staleness_reason": "partial_index_failure",
                "semantic_readiness": "vectors_missing",
                "semantic_ready": False,
                "semantic_remediation": "Run semantic summary/vector generation for the current profile before semantic queries.",
                "features": {
                    "semantic": {
                        "readiness": {
                            "state": "vectors_missing",
                            "ready": False,
                            "code": "vectors_missing",
                            "remediation": "Run semantic summary/vector generation for the current profile before semantic queries.",
                            "evidence": {
                                "profile_id": "oss_high",
                                "collection": "code_index__oss_high__v1",
                                "total_chunks": 12,
                                "summary_count": 11,
                                "missing_summaries": 1,
                                "vector_link_count": 10,
                                "missing_vectors": 2,
                                "matching_collection_links": 9,
                                "collection_mismatches": 1,
                            },
                        },
                        "preflight": {
                            "overall_ready": False,
                            "can_write_semantic_vectors": False,
                            "blocker": {
                                "code": "collection_missing",
                                "message": "Qdrant collection is missing for the active semantic profile",
                                "remediation": ["Create the expected collection"],
                            },
                        }
                    }
                },
            }

    monkeypatch.setattr("mcp_server.cli.repository_commands.RepositoryRegistry", FakeRegistry)
    monkeypatch.setattr("mcp_server.cli.repository_commands.StoreRegistry", FakeStoreRegistry)
    monkeypatch.setattr("mcp_server.cli.repository_commands.RepoResolver", FakeRepoResolver)
    monkeypatch.setattr("mcp_server.cli.repository_commands.GitAwareIndexManager", FakeIndexManager)
    monkeypatch.setattr(
        "mcp_server.cli.repository_commands.reload_settings",
        lambda: SimpleNamespace(
            get_semantic_default_profile=lambda: "oss_high",
            semantic_strict_mode=False,
        ),
    )
    monkeypatch.setattr(
        "mcp_server.cli.repository_commands.run_semantic_preflight",
        lambda **kwargs: SimpleNamespace(
            to_dict=lambda: {
                "overall_ready": False,
                "can_write_semantic_vectors": False,
                "blocker": {
                    "code": "collection_missing",
                    "message": "Qdrant collection is missing for the active semantic profile",
                    "remediation": ["Create the expected collection"],
                },
                "effective_config": {
                    "selected_profile": "oss_high",
                    "collection_name": "code_index__oss_high__v1",
                },
            }
        ),
    )

    result = runner.invoke(repository, ["status"])

    assert result.exit_code == 0
    assert "Rollout status: partial_index_failure" in result.output
    assert "Query surface: index_unavailable" in result.output
    assert 'safe_fallback: "native_search"' in result.output
    assert "Artifact health: ready" in result.output
    assert "Semantic readiness: vectors_missing" in result.output
    assert "Semantic remediation: Run semantic summary/vector generation for the current profile before semantic queries." in result.output
    assert "Semantic Preflight:" in result.output
    assert "Can write semantic vectors: no" in result.output
    assert "collection_missing" in result.output
    assert "Active profile: oss_high" in result.output
    assert "Active collection: code_index__oss_high__v1" in result.output
    assert "Collection bootstrap state: blocked" in result.output
    assert "Semantic Evidence:" in result.output
    assert "Summary-backed chunks: 11" in result.output
    assert "Chunks missing summaries: 1" in result.output
    assert "Vector-linked chunks: 10" in result.output
    assert "Chunks missing vectors: 2" in result.output
    assert "Active collection: code_index__oss_high__v1" in result.output
    assert "Collection-matched links: 9" in result.output
    assert "Collection mismatches: 1" in result.output


def test_status_reports_durable_force_full_exit_trace(monkeypatch, tmp_path: Path):
    runner = CliRunner()
    repo_info = _repo_info(tmp_path)

    class FakeRegistry:
        def get_repository_by_path(self, path):
            return repo_info

    class FakeStoreRegistry:
        @classmethod
        def for_registry(cls, registry):
            return object()

    class FakeRepoResolver:
        def __init__(self, registry, store_registry):
            pass

    class FakeIndexManager:
        def __init__(self, registry, repo_resolver=None, store_registry=None):
            pass

        def get_repository_status(self, repo_id):
            return {
                "repo_id": repo_info.repository_id,
                "name": repo_info.name,
                "path": repo_info.path,
                "current_commit": repo_info.current_commit,
                "last_indexed_commit": repo_info.last_indexed_commit,
                "last_indexed": repo_info.last_indexed,
                "needs_update": True,
                "auto_sync": repo_info.auto_sync,
                "artifact_enabled": repo_info.artifact_enabled,
                "artifact_backend": repo_info.artifact_backend,
                "artifact_health": repo_info.artifact_health,
                "index_exists": True,
                "index_size_mb": 0.1,
                "readiness": "stale_commit",
                "ready": False,
                "remediation": "Run reindex to update the repository index to the current commit.",
                "rollout_status": "partial_index_failure",
                "rollout_remediation": "A required incremental mutation failed.",
                "query_status": "index_unavailable",
                "query_remediation": 'Use native search or follow the readiness remediation; query tools stay fail-closed with safe_fallback: "native_search".',
                "staleness_reason": "partial_index_failure",
                "semantic_readiness": "summaries_missing",
                "semantic_ready": False,
                "semantic_remediation": "Run semantic summary/vector generation for the current profile before semantic queries.",
                "force_full_exit_trace": {
                    "status": "interrupted",
                    "stage": "blocked_summary_call_timeout",
                    "stage_family": "semantic_closeout",
                    "trace_timestamp": "2026-04-29T09:00:00Z",
                    "current_commit": "abcdef123456",
                    "indexed_commit_before": "oldercommit",
                    "last_progress_path": str(repo_info.path / "README.md"),
                    "in_flight_path": str(repo_info.path / "README.md"),
                    "summary_call_timed_out": True,
                    "summary_call_file_path": str(repo_info.path / "README.md"),
                    "summary_call_chunk_ids": ["chunk-1"],
                    "summary_call_timeout_seconds": 30.0,
                    "blocker_source": "summary_call_shutdown",
                },
                "features": {"semantic": {"readiness": {"evidence": {}}, "preflight": {}}},
            }

    monkeypatch.setattr("mcp_server.cli.repository_commands.RepositoryRegistry", FakeRegistry)
    monkeypatch.setattr("mcp_server.cli.repository_commands.StoreRegistry", FakeStoreRegistry)
    monkeypatch.setattr("mcp_server.cli.repository_commands.RepoResolver", FakeRepoResolver)
    monkeypatch.setattr("mcp_server.cli.repository_commands.GitAwareIndexManager", FakeIndexManager)
    monkeypatch.setattr(
        "mcp_server.cli.repository_commands.reload_settings",
        lambda: SimpleNamespace(
            get_semantic_default_profile=lambda: "oss_high",
            semantic_strict_mode=False,
        ),
    )
    monkeypatch.setattr(
        "mcp_server.cli.repository_commands.run_semantic_preflight",
        lambda **kwargs: SimpleNamespace(
            to_dict=lambda: {
                "overall_ready": True,
                "can_write_semantic_vectors": True,
                "effective_config": {
                    "selected_profile": "oss_high",
                    "collection_name": "code_index__oss_high__v1",
                },
            }
        ),
    )

    result = runner.invoke(repository, ["status"])

    assert result.exit_code == 0
    assert "Force-full exit trace:" in result.output
    assert "Trace status: interrupted" in result.output
    assert "Trace stage: blocked_summary_call_timeout" in result.output
    assert "Trace stage family: semantic_closeout" in result.output
    assert "Trace timestamp: 2026-04-29T09:00:00Z" in result.output
    assert "Trace blocker source: summary_call_shutdown" in result.output
    assert "Timed-out summary file:" in result.output
    assert "Timed-out summary timeout: 30.0" in result.output
