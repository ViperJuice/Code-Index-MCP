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


def _semantic_preflight_ready() -> SimpleNamespace:
    return SimpleNamespace(
        to_dict=lambda: {
            "overall_ready": True,
            "can_write_semantic_vectors": True,
            "effective_config": {
                "selected_profile": "oss_high",
                "collection_name": "code_index__oss_high__v1",
            },
        }
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
    (repo_info.path / ".mcp-index-ignore").write_text("fast_test_results/fast_report_*.md\n")
    (repo_info.path / "ai_docs").mkdir()
    (repo_info.path / "ai_docs" / "pytest_overview.md").write_text("# pytest\n", encoding="utf-8")

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
    assert (
        "Lexical boundary: ignoring generated fast-test reports matching "
        "fast_test_results/fast_report_*.md" in result.output
    )
    assert (
        "Lexical boundary: using bounded Markdown indexing for ai_docs/*_overview.md"
        in result.output
    )
    assert "Force-full exit trace:" in result.output
    assert "Trace status: interrupted" in result.output
    assert "Trace stage: blocked_summary_call_timeout" in result.output
    assert "Trace stage family: semantic_closeout" in result.output
    assert "Trace timestamp: 2026-04-29T09:00:00Z" in result.output
    assert "Trace blocker source: summary_call_shutdown" in result.output
    assert "Timed-out summary file:" in result.output
    assert "Timed-out summary timeout: 30.0" in result.output


def test_status_reports_storage_closeout_restore_context(monkeypatch, tmp_path: Path):
    runner = CliRunner()
    repo_info = _repo_info(tmp_path)
    (repo_info.path / ".mcp-index-ignore").write_text("fast_test_results/fast_report_*.md\n")

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
                "rollout_remediation": "A required semantic closeout mutation failed.",
                "query_status": "index_unavailable",
                "query_remediation": 'Use native search or follow the readiness remediation; query tools stay fail-closed with safe_fallback: "native_search".',
                "staleness_reason": "partial_index_failure",
                "last_sync_error": "disk I/O error [runtime restored via sqlite_restored+qdrant_preserved_empty]",
                "semantic_readiness": "summaries_missing",
                "semantic_ready": False,
                "semantic_remediation": "Run semantic summary/vector generation for the current profile before semantic queries.",
                "force_full_exit_trace": {
                    "status": "completed",
                    "stage": "runtime_restore_completed",
                    "stage_family": "final_closeout",
                    "trace_timestamp": "2026-04-29T12:00:00Z",
                    "current_commit": "abcdef123456",
                    "indexed_commit_before": "oldercommit",
                    "last_progress_path": str(repo_info.path / "mcp_server" / "document_processing" / "__init__.py"),
                    "in_flight_path": str(repo_info.path / "mcp_server" / "document_processing" / "chunk_optimizer.py"),
                    "blocker_source": "storage_closeout",
                    "storage_failure_family": "sqlite_operational",
                    "storage_failure_reason": "disk_io_error",
                    "storage_failure_message": "disk I/O error",
                    "storage_diagnostics": {
                        "status": "degraded",
                        "journal_mode": "WAL",
                        "readonly": True,
                    },
                    "runtime_restore_performed": True,
                    "runtime_restore_mode": "sqlite_restored+qdrant_preserved_empty",
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
    assert "Trace stage: runtime_restore_completed" in result.output
    assert "Trace stage family: final_closeout" in result.output
    assert "Trace blocker source: storage_closeout" in result.output
    assert "Trace storage failure family: sqlite_operational" in result.output
    assert "Trace storage failure reason: disk_io_error" in result.output
    assert "Trace storage failure message: disk I/O error" in result.output
    assert "Trace runtime restore: performed via sqlite_restored+qdrant_preserved_empty" in result.output
    assert "Trace storage diagnostics: status=degraded journal_mode=WAL readonly=True" in result.output


def test_status_reports_missing_force_full_exit_trace(monkeypatch, tmp_path: Path):
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
                "rollout_status": "stale_commit",
                "rollout_remediation": "Run reindex to update the repository index to the current commit.",
                "query_status": "index_unavailable",
                "query_remediation": 'Use native search or follow the readiness remediation; query tools stay fail-closed with safe_fallback: "native_search".',
                "staleness_reason": "stale_commit",
                "semantic_readiness": "summaries_missing",
                "semantic_ready": False,
                "semantic_remediation": "Run semantic summary/vector generation for the current profile before semantic queries.",
                "force_full_exit_trace": None,
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
    assert "Force-full exit trace: missing" in result.output
    assert "Trace status:" not in result.output


def test_status_marks_stale_running_force_full_exit_trace(monkeypatch, tmp_path: Path):
    runner = CliRunner()
    repo_info = _repo_info(tmp_path)
    blocked_test = repo_info.path / "tests" / "test_artifact_publish_race.py"
    blocked_test.parent.mkdir(parents=True)
    blocked_test.write_text("def test_publish_race():\n    assert True\n", encoding="utf-8")

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
                "rollout_status": "stale_commit",
                "rollout_remediation": "Run reindex to update the repository index to the current commit.",
                "query_status": "index_unavailable",
                "query_remediation": 'Use native search or follow the readiness remediation; query tools stay fail-closed with safe_fallback: "native_search".',
                "staleness_reason": "stale_commit",
                "semantic_readiness": "summaries_missing",
                "semantic_ready": False,
                "semantic_remediation": "Run semantic summary/vector generation for the current profile before semantic queries.",
                "force_full_exit_trace": {
                    "status": "running",
                    "stage": "lexical_walking",
                    "stage_family": "lexical",
                    "trace_timestamp": "2020-01-01T00:00:00Z",
                    "current_commit": "abcdef123456",
                    "indexed_commit_before": "oldercommit",
                    "last_progress_path": str(repo_info.path / "tests" / "test_benchmarks.py"),
                    "in_flight_path": str(blocked_test),
                    "blocker_source": "lexical_mutation",
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
    monkeypatch.setenv("MCP_INDEX_LEXICAL_TIMEOUT_SECONDS", "5")

    result = runner.invoke(repository, ["status"])

    assert result.exit_code == 0
    assert "Trace freshness: stale-running snapshot" in result.output
    assert f"Last progress path: {repo_info.path / 'tests' / 'test_benchmarks.py'}" in result.output
    assert f"In-flight path: {blocked_test}" in result.output
    assert (
        "Lexical boundary: using exact bounded Python indexing for "
        "tests/test_artifact_publish_race.py" in result.output
    )
    assert "In-flight path:" in result.output


def test_status_does_not_report_stale_running_for_interrupted_later_test_pair(
    monkeypatch, tmp_path: Path
):
    runner = CliRunner()
    repo_info = _repo_info(tmp_path)
    blocked_test = repo_info.path / "tests" / "test_reindex_resume.py"
    blocked_test.parent.mkdir(parents=True)
    blocked_test.write_text("def test_reindex_resume():\n    assert True\n", encoding="utf-8")
    prior_test = repo_info.path / "tests" / "test_deployment_runbook_shape.py"
    prior_test.write_text("def test_runbook_shape():\n    assert True\n", encoding="utf-8")

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
                "rollout_remediation": "A required lexical mutation failed.",
                "query_status": "index_unavailable",
                "query_remediation": 'Use native search or follow the readiness remediation; query tools stay fail-closed with safe_fallback: "native_search".',
                "staleness_reason": "partial_index_failure",
                "semantic_readiness": "summaries_missing",
                "semantic_ready": False,
                "semantic_remediation": "Run semantic summary/vector generation for the current profile before semantic queries.",
                "force_full_exit_trace": {
                    "status": "interrupted",
                    "stage": "lexical_walking",
                    "stage_family": "lexical",
                    "trace_timestamp": "2020-01-01T00:00:00Z",
                    "current_commit": "abcdef123456",
                    "indexed_commit_before": "oldercommit",
                    "last_progress_path": str(prior_test),
                    "in_flight_path": str(blocked_test),
                    "blocker_source": "lexical_mutation",
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
    monkeypatch.setenv("MCP_INDEX_LEXICAL_TIMEOUT_SECONDS", "5")

    result = runner.invoke(repository, ["status"])

    assert result.exit_code == 0
    assert "Trace status: interrupted" in result.output
    assert "Trace freshness: stale-running snapshot" not in result.output
    assert f"Last progress path: {prior_test}" in result.output
    assert f"In-flight path: {blocked_test}" in result.output


def test_status_reports_exact_visual_report_python_boundary(monkeypatch, tmp_path: Path):
    runner = CliRunner()
    repo_info = _repo_info(tmp_path)
    script = repo_info.path / "scripts" / "create_multi_repo_visual_report.py"
    script.parent.mkdir(parents=True)
    script.write_text("def main():\n    return 1\n", encoding="utf-8")

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
                "rollout_remediation": "A required lexical mutation failed.",
                "query_status": "index_unavailable",
                "query_remediation": 'Use native search or follow the readiness remediation; query tools stay fail-closed with safe_fallback: "native_search".',
                "staleness_reason": "partial_index_failure",
                "semantic_readiness": "summaries_missing",
                "semantic_ready": False,
                "semantic_remediation": "Run semantic summary/vector generation for the current profile before semantic queries.",
                "force_full_exit_trace": {
                    "status": "running",
                    "stage": "lexical_walking",
                    "stage_family": "lexical",
                    "trace_timestamp": "2026-04-29T10:00:00Z",
                    "current_commit": "abcdef123456",
                    "indexed_commit_before": "oldercommit",
                    "last_progress_path": str(script),
                    "in_flight_path": str(script),
                    "blocker_source": "lexical_mutation",
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
    assert (
        "Lexical boundary: using exact bounded Python indexing for "
        "scripts/create_multi_repo_visual_report.py" in result.output
    )
    assert f"Last progress path: {script}" in result.output


def test_status_reports_exact_quick_validation_python_boundary(monkeypatch, tmp_path: Path):
    runner = CliRunner()
    repo_info = _repo_info(tmp_path)
    previous_script = repo_info.path / "scripts" / "rerun_failed_native_tests.py"
    blocked_script = repo_info.path / "scripts" / "quick_mcp_vs_native_validation.py"
    previous_script.parent.mkdir(parents=True)
    previous_script.write_text("def rerun_failed_tests():\n    return []\n", encoding="utf-8")
    blocked_script.write_text("def compare_results():\n    return []\n", encoding="utf-8")

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
                "rollout_remediation": "A required lexical mutation failed.",
                "query_status": "index_unavailable",
                "query_remediation": 'Use native search or follow the readiness remediation; query tools stay fail-closed with safe_fallback: "native_search".',
                "staleness_reason": "partial_index_failure",
                "semantic_readiness": "summaries_missing",
                "semantic_ready": False,
                "semantic_remediation": "Run semantic summary/vector generation for the current profile before semantic queries.",
                "force_full_exit_trace": {
                    "status": "running",
                    "stage": "lexical_walking",
                    "stage_family": "lexical",
                    "trace_timestamp": "2026-04-29T10:00:00Z",
                    "current_commit": "abcdef123456",
                    "indexed_commit_before": "oldercommit",
                    "last_progress_path": str(previous_script),
                    "in_flight_path": str(blocked_script),
                    "blocker_source": "lexical_mutation",
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
    monkeypatch.setenv("MCP_INDEX_LEXICAL_TIMEOUT_SECONDS", "5")

    result = runner.invoke(repository, ["status"])

    assert result.exit_code == 0
    assert "Trace freshness: stale-running snapshot" in result.output
    assert f"Last progress path: {previous_script}" in result.output
    assert f"In-flight path: {blocked_script}" in result.output
    assert (
        "Lexical boundary: using exact bounded Python indexing for "
        "scripts/quick_mcp_vs_native_validation.py" in result.output
    )


def test_status_reports_exact_validate_script_python_boundary(monkeypatch, tmp_path: Path):
    runner = CliRunner()
    repo_info = _repo_info(tmp_path)
    previous_script = repo_info.path / "scripts" / "run_test_batch.py"
    blocked_script = repo_info.path / "scripts" / "validate_mcp_comprehensive.py"
    previous_script.parent.mkdir(parents=True)
    previous_script.write_text("def main():\n    return 1\n", encoding="utf-8")
    blocked_script.write_text("def validate_mcp():\n    return True\n", encoding="utf-8")

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
                "rollout_remediation": "A required lexical mutation failed.",
                "query_status": "index_unavailable",
                "query_remediation": 'Use native search or follow the readiness remediation; query tools stay fail-closed with safe_fallback: "native_search".',
                "staleness_reason": "partial_index_failure",
                "semantic_readiness": "summaries_missing",
                "semantic_ready": False,
                "semantic_remediation": "Run semantic summary/vector generation for the current profile before semantic queries.",
                "force_full_exit_trace": {
                    "status": "interrupted",
                    "stage": "lexical_walking",
                    "stage_family": "lexical",
                    "trace_timestamp": "2026-04-29T10:00:00Z",
                    "current_commit": "abcdef123456",
                    "indexed_commit_before": "oldercommit",
                    "last_progress_path": str(previous_script),
                    "in_flight_path": str(blocked_script),
                    "blocker_source": "lexical_mutation",
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
    monkeypatch.setenv("MCP_INDEX_LEXICAL_TIMEOUT_SECONDS", "5")

    result = runner.invoke(repository, ["status"])

    assert result.exit_code == 0
    assert "Trace status: interrupted" in result.output
    assert f"Last progress path: {previous_script}" in result.output
    assert f"In-flight path: {blocked_script}" in result.output
    assert (
        "Lexical boundary: using exact bounded Python indexing for "
        "scripts/validate_mcp_comprehensive.py" in result.output
    )
    assert "scripts/quick_mcp_vs_native_validation.py" not in result.output


def test_status_reports_exact_artifact_publish_race_python_boundary(
    monkeypatch, tmp_path: Path
):
    runner = CliRunner()
    repo_info = _repo_info(tmp_path)
    blocked_test = repo_info.path / "tests" / "test_artifact_publish_race.py"
    blocked_test.parent.mkdir(parents=True)
    blocked_test.write_text("def test_publish_race():\n    assert True\n", encoding="utf-8")

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
                "rollout_remediation": "A required lexical mutation failed.",
                "query_status": "index_unavailable",
                "query_remediation": 'Use native search or follow the readiness remediation; query tools stay fail-closed with safe_fallback: "native_search".',
                "staleness_reason": "partial_index_failure",
                "semantic_readiness": "summaries_missing",
                "semantic_ready": False,
                "semantic_remediation": "Run semantic summary/vector generation for the current profile before semantic queries.",
                "force_full_exit_trace": {
                    "status": "running",
                    "stage": "lexical_walking",
                    "stage_family": "lexical",
                    "trace_timestamp": "2026-04-29T10:00:00Z",
                    "current_commit": "abcdef123456",
                    "indexed_commit_before": "oldercommit",
                    "last_progress_path": str(repo_info.path / "tests" / "test_benchmarks.py"),
                    "in_flight_path": str(blocked_test),
                    "blocker_source": "lexical_mutation",
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
    assert (
        "Lexical boundary: using exact bounded Python indexing for "
        "tests/test_artifact_publish_race.py" in result.output
    )
    assert f"Last progress path: {repo_info.path / 'tests' / 'test_benchmarks.py'}" in result.output
    assert f"In-flight path: {blocked_test}" in result.output


def test_status_reports_exact_run_reranking_tests_python_boundary(
    monkeypatch, tmp_path: Path
):
    runner = CliRunner()
    repo_info = _repo_info(tmp_path)
    previous_test = repo_info.path / "tests" / "root_tests" / "test_voyage_api.py"
    blocked_test = repo_info.path / "tests" / "root_tests" / "run_reranking_tests.py"
    previous_test.parent.mkdir(parents=True)
    previous_test.write_text("def test_voyage_api():\n    assert True\n", encoding="utf-8")
    blocked_test.write_text("def main():\n    return 1\n", encoding="utf-8")

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
                "rollout_remediation": "A required lexical mutation failed.",
                "query_status": "index_unavailable",
                "query_remediation": 'Use native search or follow the readiness remediation; query tools stay fail-closed with safe_fallback: "native_search".',
                "staleness_reason": "partial_index_failure",
                "semantic_readiness": "summaries_missing",
                "semantic_ready": False,
                "semantic_remediation": "Run semantic summary/vector generation for the current profile before semantic queries.",
                "force_full_exit_trace": {
                    "status": "interrupted",
                    "stage": "lexical_walking",
                    "stage_family": "lexical",
                    "trace_timestamp": "2026-04-29T11:43:19Z",
                    "current_commit": "abcdef123456",
                    "indexed_commit_before": "oldercommit",
                    "last_progress_path": str(previous_test),
                    "in_flight_path": str(blocked_test),
                    "blocker_source": "lexical_mutation",
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
    assert "Trace status: interrupted" in result.output
    assert f"Last progress path: {previous_test}" in result.output
    assert f"In-flight path: {blocked_test}" in result.output
    assert (
        "Lexical boundary: using exact bounded Python indexing for "
        "tests/root_tests/run_reranking_tests.py" in result.output
    )
    assert "tests/test_reindex_resume.py" not in result.output
    assert "scripts/validate_mcp_comprehensive.py" not in result.output


def test_status_reports_exact_script_language_audit_python_boundary(
    monkeypatch, tmp_path: Path
):
    runner = CliRunner()
    repo_info = _repo_info(tmp_path)
    previous_script = repo_info.path / "scripts" / "migrate_large_index_to_multi_repo.py"
    blocked_script = repo_info.path / "scripts" / "check_index_languages.py"
    previous_script.parent.mkdir(parents=True)
    previous_script.write_text(
        "class RepositoryMigration:\n"
        "    pass\n\n"
        "class LargeIndexMigrator:\n"
        "    def migrate_repository(self):\n"
        "        return 'ok'\n\n"
        "def main():\n"
        "    return LargeIndexMigrator()\n",
        encoding="utf-8",
    )
    blocked_script.write_text(
        "print('Checking languages')\n"
        "tables = ['files']\n"
        "for table in tables:\n"
        "    print(table)\n",
        encoding="utf-8",
    )
    later_file = repo_info.path / "docs" / "status" / "semantic_tail.md"
    later_file.parent.mkdir(parents=True)
    later_file.write_text("# Semantic tail\n", encoding="utf-8")

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
                "rollout_remediation": "A required lexical mutation failed.",
                "query_status": "index_unavailable",
                "query_remediation": 'Use native search or follow the readiness remediation; query tools stay fail-closed with safe_fallback: "native_search".',
                "staleness_reason": "partial_index_failure",
                "semantic_readiness": "summaries_missing",
                "semantic_ready": False,
                "semantic_remediation": "Run semantic summary/vector generation for the current profile before semantic queries.",
                "force_full_exit_trace": {
                    "status": "interrupted",
                    "stage": "lexical_walking",
                    "stage_family": "lexical",
                    "trace_timestamp": "2026-04-29T15:03:10Z",
                    "current_commit": "248dd68d06bced46adc2460c44fbcb2d38e72614",
                    "indexed_commit_before": "oldercommit",
                    "last_progress_path": str(blocked_script),
                    "in_flight_path": str(later_file),
                    "blocker_source": "lexical_mutation",
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
    assert (
        "Lexical boundary: using exact bounded Python indexing for "
        "scripts/migrate_large_index_to_multi_repo.py -> "
        "scripts/check_index_languages.py" in result.output
    )
    assert f"Last progress path: {blocked_script}" in result.output
    assert f"In-flight path: {later_file}" in result.output


def test_status_reports_exact_preflight_upgrade_script_boundary(
    monkeypatch, tmp_path: Path
):
    runner = CliRunner()
    repo_info = _repo_info(tmp_path)
    preflight_script = repo_info.path / "scripts" / "preflight_upgrade.sh"
    protocol_script = repo_info.path / "scripts" / "test_mcp_protocol_direct.py"
    later_file = repo_info.path / "docs" / "status" / "semantic_tail.md"
    preflight_script.parent.mkdir(parents=True)
    later_file.parent.mkdir(parents=True)
    preflight_script.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    protocol_script.write_text("async def test_mcp_protocol():\n    return 'ok'\n", encoding="utf-8")
    later_file.write_text("# Semantic tail\n", encoding="utf-8")

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
                "rollout_remediation": "A required lexical mutation failed.",
                "query_status": "index_unavailable",
                "query_remediation": 'Use native search or follow the readiness remediation; query tools stay fail-closed with safe_fallback: "native_search".',
                "staleness_reason": "partial_index_failure",
                "semantic_readiness": "summaries_missing",
                "semantic_ready": False,
                "semantic_remediation": "Run semantic summary/vector generation for the current profile before semantic queries.",
                "force_full_exit_trace": {
                    "status": "interrupted",
                    "stage": "lexical_walking",
                    "stage_family": "lexical",
                    "trace_timestamp": "2026-04-29T17:35:00Z",
                    "current_commit": "dbfd6ccd5577d104313110e40a83c28647385b58",
                    "indexed_commit_before": "oldercommit",
                    "last_progress_path": str(protocol_script),
                    "in_flight_path": str(later_file),
                    "blocker_source": "lexical_mutation",
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
    assert (
        "Lexical boundary: using exact bounded shell/Python indexing for "
        "scripts/preflight_upgrade.sh -> scripts/test_mcp_protocol_direct.py"
        in result.output
    )
    assert f"Last progress path: {protocol_script}" in result.output
    assert f"In-flight path: {later_file}" in result.output
    assert "scripts/validate_mcp_comprehensive.py" not in result.output
    assert "tests/root_tests/run_reranking_tests.py" not in result.output


def test_status_reports_visualization_quick_charts_python_boundary(
    monkeypatch, tmp_path: Path
):
    runner = CliRunner()
    repo_info = _repo_info(tmp_path)
    previous_file = repo_info.path / "mcp_server" / "visualization" / "__init__.py"
    blocked_file = repo_info.path / "mcp_server" / "visualization" / "quick_charts.py"
    previous_file.parent.mkdir(parents=True)
    previous_file.write_text("from .quick_charts import QuickCharts\n", encoding="utf-8")
    blocked_file.write_text("class QuickCharts:\n    pass\n", encoding="utf-8")

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
                "rollout_remediation": "A required lexical mutation failed.",
                "query_status": "index_unavailable",
                "query_remediation": 'Use native search or follow the readiness remediation; query tools stay fail-closed with safe_fallback: "native_search".',
                "staleness_reason": "partial_index_failure",
                "semantic_readiness": "summaries_missing",
                "semantic_ready": False,
                "semantic_remediation": "Run semantic summary/vector generation for the current profile before semantic queries.",
                "force_full_exit_trace": {
                    "status": "interrupted",
                    "stage": "lexical_walking",
                    "stage_family": "lexical",
                    "trace_timestamp": "2026-04-29T12:21:08Z",
                    "current_commit": "ec443d85edd902cdcc018d2103a334abe5235124",
                    "indexed_commit_before": "e2e9519858c3683c06b152c94a99e52098beaec6",
                    "last_progress_path": str(previous_file),
                    "in_flight_path": str(blocked_file),
                    "blocker_source": "lexical_mutation",
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
    assert f"Last progress path: {previous_file}" in result.output
    assert f"In-flight path: {blocked_file}" in result.output
    assert (
        "Lexical boundary: using exact bounded Python indexing for "
        "mcp_server/visualization/quick_charts.py" in result.output
    )
    assert "scripts/validate_mcp_comprehensive.py" not in result.output


def test_status_reports_docs_governance_contract_python_boundary(
    monkeypatch, tmp_path: Path
):
    runner = CliRunner()
    repo_info = _repo_info(tmp_path)
    previous_test = repo_info.path / "tests" / "docs" / "test_mre2e_evidence_contract.py"
    blocked_test = repo_info.path / "tests" / "docs" / "test_gagov_governance_contract.py"
    previous_test.parent.mkdir(parents=True)
    previous_test.write_text("def test_mre2e_contract():\n    assert True\n", encoding="utf-8")
    blocked_test.write_text("def test_gagov_contract():\n    assert True\n", encoding="utf-8")

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
                "rollout_remediation": "A required lexical mutation failed.",
                "query_status": "index_unavailable",
                "query_remediation": 'Use native search or follow the readiness remediation; query tools stay fail-closed with safe_fallback: "native_search".',
                "staleness_reason": "partial_index_failure",
                "semantic_readiness": "summaries_missing",
                "semantic_ready": False,
                "semantic_remediation": "Run semantic summary/vector generation for the current profile before semantic queries.",
                "force_full_exit_trace": {
                    "status": "interrupted",
                    "stage": "lexical_walking",
                    "stage_family": "lexical",
                    "trace_timestamp": "2026-04-29T14:13:50Z",
                    "current_commit": "9138e0b0",
                    "indexed_commit_before": "oldercommit",
                    "last_progress_path": str(previous_test),
                    "in_flight_path": str(blocked_test),
                    "blocker_source": "lexical_mutation",
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
        lambda **kwargs: _semantic_preflight_ready(),
    )

    result = runner.invoke(repository, ["status"])

    assert result.exit_code == 0
    assert f"Last progress path: {previous_test}" in result.output
    assert f"In-flight path: {blocked_test}" in result.output
    assert (
        "Lexical boundary: using exact bounded Python indexing for "
        "tests/docs/test_mre2e_evidence_contract.py -> "
        "tests/docs/test_gagov_governance_contract.py" in result.output
    )
    assert "scripts/validate_mcp_comprehensive.py" not in result.output
    assert "mcp_server/visualization/quick_charts.py" not in result.output


def test_status_reports_exact_devcontainer_json_boundary(monkeypatch, tmp_path: Path):
    runner = CliRunner()
    repo_info = _repo_info(tmp_path)
    config_file = repo_info.path / ".devcontainer" / "devcontainer.json"
    config_file.parent.mkdir(parents=True)
    config_file.write_text('{"name": "devcontainer"}\n', encoding="utf-8")

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
                "rollout_remediation": "A required lexical mutation failed.",
                "query_status": "index_unavailable",
                "query_remediation": 'Use native search or follow the readiness remediation; query tools stay fail-closed with safe_fallback: "native_search".',
                "staleness_reason": "partial_index_failure",
                "semantic_readiness": "summaries_missing",
                "semantic_ready": False,
                "semantic_remediation": "Run semantic summary/vector generation for the current profile before semantic queries.",
                "force_full_exit_trace": {
                    "status": "running",
                    "stage": "lexical_walking",
                    "stage_family": "lexical",
                    "trace_timestamp": "2026-04-29T10:00:00Z",
                    "current_commit": "abcdef123456",
                    "indexed_commit_before": "oldercommit",
                    "last_progress_path": str(repo_info.path / ".devcontainer" / "post_create.sh"),
                    "in_flight_path": str(config_file),
                    "blocker_source": "lexical_mutation",
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
    assert (
        "Lexical boundary: using exact bounded JSON indexing for "
        ".devcontainer/devcontainer.json" in result.output
    )
    assert f"Last progress path: {repo_info.path / '.devcontainer' / 'post_create.sh'}" in result.output
    assert f"In-flight path: {config_file}" in result.output


def test_status_reports_archive_tail_bounded_successor_when_in_flight_is_null(
    monkeypatch, tmp_path: Path
):
    runner = CliRunner()
    repo_info = _repo_info(tmp_path)
    prior_file = (
        repo_info.path
        / "analysis_archive"
        / "scripts_archive"
        / "scripts_test_files"
        / "verify_mcp_fix.py"
    )
    prior_file.parent.mkdir(parents=True)
    prior_file.write_text("def verify_fix():\n    return True\n", encoding="utf-8")
    archive_json = repo_info.path / "analysis_archive" / "semantic_vs_sql_comparison_1750926162.json"
    archive_json.write_text('{"comparison": "archive tail"}\n', encoding="utf-8")

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
                "rollout_remediation": "A required lexical mutation failed.",
                "query_status": "index_unavailable",
                "query_remediation": 'Use native search or follow the readiness remediation; query tools stay fail-closed with safe_fallback: "native_search".',
                "staleness_reason": "partial_index_failure",
                "semantic_readiness": "summaries_missing",
                "semantic_ready": False,
                "semantic_remediation": "Run semantic summary/vector generation for the current profile before semantic queries.",
                "force_full_exit_trace": {
                    "status": "interrupted",
                    "stage": "lexical_walking",
                    "stage_family": "lexical",
                    "trace_timestamp": "2026-04-29T14:10:00Z",
                    "current_commit": "7282e34100000000000000000000000000000000",
                    "indexed_commit_before": "705a506f00000000000000000000000000000000",
                    "last_progress_path": str(archive_json),
                    "in_flight_path": None,
                    "blocker_source": "lexical_mutation",
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
        lambda **kwargs: _semantic_preflight_ready(),
    )

    result = runner.invoke(repository, ["status"])

    assert result.exit_code == 0
    assert (
        "Lexical boundary: using exact bounded JSON indexing for "
        "analysis_archive/semantic_vs_sql_comparison_1750926162.json after "
        "analysis_archive/scripts_archive/scripts_test_files/verify_mcp_fix.py"
    ) in result.output
    assert f"Last progress path: {archive_json}" in result.output
    assert "In-flight path:" not in result.output
    assert (
        "Archive-tail successor: exact bounded JSON indexing preserved lexical progress "
        f"beyond {prior_file}"
    ) in result.output
    assert ".devcontainer/devcontainer.json" not in result.output
    assert "mcp_server/visualization/quick_charts.py" not in result.output
    assert "docs/benchmarks/production_benchmark.md" not in result.output


def test_status_reports_same_devcontainer_relapse_without_older_or_later_boundaries(
    monkeypatch, tmp_path: Path
):
    runner = CliRunner()
    repo_info = _repo_info(tmp_path)
    config_file = repo_info.path / ".devcontainer" / "devcontainer.json"
    config_file.parent.mkdir(parents=True)
    config_file.write_text('{"name": "devcontainer"}\n', encoding="utf-8")

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
                "rollout_remediation": "A required lexical mutation failed.",
                "query_status": "index_unavailable",
                "query_remediation": 'Use native search or follow the readiness remediation; query tools stay fail-closed with safe_fallback: "native_search".',
                "staleness_reason": "partial_index_failure",
                "semantic_readiness": "summaries_missing",
                "semantic_ready": False,
                "semantic_remediation": "Run semantic summary/vector generation for the current profile before semantic queries.",
                "force_full_exit_trace": {
                    "status": "interrupted",
                    "stage": "lexical_walking",
                    "stage_family": "lexical",
                    "trace_timestamp": "2026-04-29T12:21:08Z",
                    "current_commit": "ec443d85edd902cdcc018d2103a334abe5235124",
                    "indexed_commit_before": "e2e9519858c3683c06b152c94a99e52098beaec6",
                    "last_progress_path": str(config_file),
                    "in_flight_path": None,
                    "blocker_source": "lexical_mutation",
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
    assert "Trace status: interrupted" in result.output
    assert "Trace stage: lexical_walking" in result.output
    assert f"Last progress path: {config_file}" in result.output
    assert "In-flight path:" not in result.output
    assert ".devcontainer/post_create.sh" not in result.output
    assert "tests/test_reindex_resume.py" not in result.output
    assert "scripts/validate_mcp_comprehensive.py" not in result.output
    assert "tests/root_tests/run_reranking_tests.py" not in result.output


def test_status_reports_test_workspace_boundary_with_post_devcontainer_later_path(
    monkeypatch, tmp_path: Path
):
    runner = CliRunner()
    repo_info = _repo_info(tmp_path)
    (repo_info.path / ".mcp-index-ignore").write_text(
        "fast_test_results/fast_report_*.md\ntest_workspace/\n",
        encoding="utf-8",
    )
    config_file = repo_info.path / ".devcontainer" / "devcontainer.json"
    config_file.parent.mkdir(parents=True)
    config_file.write_text('{"name": "devcontainer"}\n', encoding="utf-8")
    later_file = repo_info.path / "mcp_server" / "cli" / "repository_commands.py"
    later_file.parent.mkdir(parents=True)
    later_file.write_text("# later included file\n", encoding="utf-8")

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
                "rollout_remediation": "A required lexical mutation failed.",
                "query_status": "index_unavailable",
                "query_remediation": 'Use native search or follow the readiness remediation; query tools stay fail-closed with safe_fallback: "native_search".',
                "staleness_reason": "partial_index_failure",
                "semantic_readiness": "summaries_missing",
                "semantic_ready": False,
                "semantic_remediation": "Run semantic summary/vector generation for the current profile before semantic queries.",
                "force_full_exit_trace": {
                    "status": "interrupted",
                    "stage": "lexical_walking",
                    "stage_family": "lexical",
                    "trace_timestamp": "2026-04-29T12:47:18Z",
                    "current_commit": "26a163da52865a85c4f0c91e657c3f959e26b00e",
                    "indexed_commit_before": "869eea9302c687b7b4b496735de74e85a72e95f0",
                    "last_progress_path": str(later_file),
                    "in_flight_path": None,
                    "blocker_source": "lexical_mutation",
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
        lambda **kwargs: _semantic_preflight_ready(),
    )

    result = runner.invoke(repository, ["status"])

    assert result.exit_code == 0
    assert (
        "Lexical boundary: fixture repositories under test_workspace/ are ignored during "
        "lexical walking" in result.output
    )
    assert (
        "Lexical boundary: using exact bounded JSON indexing for "
        ".devcontainer/devcontainer.json" in result.output
    )
    assert f"Last progress path: {later_file}" in result.output
    assert f"Last progress path: {config_file}" not in result.output


def test_status_reports_exact_jedi_markdown_boundary(monkeypatch, tmp_path: Path):
    runner = CliRunner()
    repo_info = _repo_info(tmp_path)
    jedi_doc = repo_info.path / "ai_docs" / "jedi.md"
    jedi_doc.parent.mkdir(parents=True)
    jedi_doc.write_text("# Jedi\n", encoding="utf-8")

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
                "rollout_remediation": "A required lexical mutation failed.",
                "query_status": "index_unavailable",
                "query_remediation": 'Use native search or follow the readiness remediation; query tools stay fail-closed with safe_fallback: "native_search".',
                "staleness_reason": "partial_index_failure",
                "semantic_readiness": "summaries_missing",
                "semantic_ready": False,
                "semantic_remediation": "Run semantic summary/vector generation for the current profile before semantic queries.",
                "force_full_exit_trace": {
                    "status": "running",
                    "stage": "lexical_walking",
                    "stage_family": "lexical",
                    "trace_timestamp": "2026-04-29T11:00:00Z",
                    "current_commit": "abcdef123456",
                    "indexed_commit_before": "oldercommit",
                    "last_progress_path": str(jedi_doc),
                    "in_flight_path": str(jedi_doc),
                    "blocker_source": "lexical_mutation",
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
    assert (
        "Lexical boundary: using exact bounded Markdown indexing for ai_docs/jedi.md"
        in result.output
    )
    assert f"Last progress path: {jedi_doc}" in result.output


def test_status_reports_exact_validation_markdown_boundaries(monkeypatch, tmp_path: Path):
    runner = CliRunner()
    repo_info = _repo_info(tmp_path)
    ga_doc = repo_info.path / "docs" / "validation" / "ga-closeout-decision.md"
    mre2e_doc = repo_info.path / "docs" / "validation" / "mre2e-evidence.md"
    ga_doc.parent.mkdir(parents=True)
    ga_doc.write_text("# GA Closeout Decision\n", encoding="utf-8")
    mre2e_doc.write_text("# MRE2E Evidence\n", encoding="utf-8")

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
                "rollout_remediation": "A required lexical mutation failed.",
                "query_status": "index_unavailable",
                "query_remediation": 'Use native search or follow the readiness remediation; query tools stay fail-closed with safe_fallback: "native_search".',
                "staleness_reason": "partial_index_failure",
                "semantic_readiness": "summaries_missing",
                "semantic_ready": False,
                "semantic_remediation": "Run semantic summary/vector generation for the current profile before semantic queries.",
                "force_full_exit_trace": {
                    "status": "interrupted",
                    "stage": "lexical_walking",
                    "stage_family": "lexical",
                    "trace_timestamp": "2026-04-29T13:16:25Z",
                    "current_commit": "8f5c5f0a00000000000000000000000000000000",
                    "indexed_commit_before": "26a163da00000000000000000000000000000000",
                    "last_progress_path": str(ga_doc),
                    "in_flight_path": str(mre2e_doc),
                    "blocker_source": "lexical_mutation",
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
    assert (
        "Lexical boundary: using exact bounded Markdown indexing for "
        "docs/validation/ga-closeout-decision.md" in result.output
    )
    assert (
        "Lexical boundary: using exact bounded Markdown indexing for "
        "docs/validation/mre2e-evidence.md" in result.output
    )
    assert f"Last progress path: {ga_doc}" in result.output
    assert f"In-flight path: {mre2e_doc}" in result.output


def test_status_reports_exact_benchmark_markdown_boundary(monkeypatch, tmp_path: Path):
    runner = CliRunner()
    repo_info = _repo_info(tmp_path)
    rerun_doc = (
        repo_info.path
        / "docs"
        / "benchmarks"
        / "mcp_vs_native_benchmark_fullrepo_fireworks_qwen_voyage_local_iter5_rerun.md"
    )
    production_doc = repo_info.path / "docs" / "benchmarks" / "production_benchmark.md"
    rerun_doc.parent.mkdir(parents=True)
    rerun_doc.write_text("# MCP vs Native Benchmark\n", encoding="utf-8")
    production_doc.write_text("# Production Retrieval Benchmark\n", encoding="utf-8")
    later_doc = repo_info.path / "docs" / "status" / "semantic_tail.md"
    later_doc.parent.mkdir(parents=True)
    later_doc.write_text("# Semantic tail\n", encoding="utf-8")

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
                "rollout_remediation": "A required lexical mutation failed.",
                "query_status": "index_unavailable",
                "query_remediation": 'Use native search or follow the readiness remediation; query tools stay fail-closed with safe_fallback: "native_search".',
                "staleness_reason": "partial_index_failure",
                "semantic_readiness": "summaries_missing",
                "semantic_ready": False,
                "semantic_remediation": "Run semantic summary/vector generation for the current profile before semantic queries.",
                "force_full_exit_trace": {
                    "status": "interrupted",
                    "stage": "lexical_walking",
                    "stage_family": "lexical",
                    "trace_timestamp": "2026-04-29T13:34:05Z",
                    "current_commit": "705a506f00000000000000000000000000000000",
                    "indexed_commit_before": "26a163da00000000000000000000000000000000",
                    "last_progress_path": str(production_doc),
                    "in_flight_path": str(later_doc),
                    "blocker_source": "lexical_mutation",
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
    assert (
        "Lexical boundary: using exact bounded Markdown indexing for "
        "docs/benchmarks/mcp_vs_native_benchmark_fullrepo_fireworks_qwen_voyage_local_iter5_rerun.md "
        "-> docs/benchmarks/production_benchmark.md" in result.output
    )
    assert f"Last progress path: {production_doc}" in result.output
    assert f"In-flight path: {later_doc}" in result.output


def test_status_reports_exact_claude_command_markdown_boundary(monkeypatch, tmp_path: Path):
    runner = CliRunner()
    repo_info = _repo_info(tmp_path)
    execute_doc = repo_info.path / ".claude" / "commands" / "execute-lane.md"
    plan_doc = repo_info.path / ".claude" / "commands" / "plan-phase.md"
    later_doc = repo_info.path / "docs" / "status" / "semantic_tail.md"
    execute_doc.parent.mkdir(parents=True)
    execute_doc.write_text("# Execute Lane\n", encoding="utf-8")
    plan_doc.write_text("# Plan Phase\n", encoding="utf-8")
    later_doc.parent.mkdir(parents=True, exist_ok=True)
    later_doc.write_text("# Semantic tail\n", encoding="utf-8")

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
                "rollout_remediation": "A required lexical mutation failed.",
                "query_status": "index_unavailable",
                "query_remediation": 'Use native search or follow the readiness remediation; query tools stay fail-closed with safe_fallback: "native_search".',
                "staleness_reason": "partial_index_failure",
                "semantic_readiness": "summaries_missing",
                "semantic_ready": False,
                "semantic_remediation": "Run semantic summary/vector generation for the current profile before semantic queries.",
                "force_full_exit_trace": {
                    "status": "interrupted",
                    "stage": "lexical_walking",
                    "stage_family": "lexical",
                    "trace_timestamp": "2026-04-29T14:41:32Z",
                    "current_commit": "3dba956300000000000000000000000000000000",
                    "indexed_commit_before": "26a163da00000000000000000000000000000000",
                    "last_progress_path": str(execute_doc),
                    "in_flight_path": str(plan_doc),
                    "blocker_source": "lexical_mutation",
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
    assert (
        "Lexical boundary: using exact bounded Markdown indexing for "
        ".claude/commands/execute-lane.md -> .claude/commands/plan-phase.md"
        in result.output
    )
    assert f"Last progress path: {execute_doc}" in result.output
    assert f"In-flight path: {plan_doc}" in result.output


def test_status_reports_exact_late_v7_phase_plan_markdown_boundary(
    monkeypatch, tmp_path: Path
):
    runner = CliRunner()
    repo_info = _repo_info(tmp_path)
    semsyncfix_doc = repo_info.path / "plans" / "phase-plan-v7-SEMSYNCFIX.md"
    semvisualreport_doc = repo_info.path / "plans" / "phase-plan-v7-SEMVISUALREPORT.md"
    later_doc = repo_info.path / "plans" / "phase-plan-v6-WATCH.md"
    semsyncfix_doc.parent.mkdir(parents=True)
    semsyncfix_doc.write_text("# SEMSYNCFIX\n", encoding="utf-8")
    semvisualreport_doc.write_text("# SEMVISUALREPORT\n", encoding="utf-8")
    later_doc.write_text("# WATCH\n", encoding="utf-8")

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
                "rollout_remediation": "A required lexical mutation failed.",
                "query_status": "index_unavailable",
                "query_remediation": 'Use native search or follow the readiness remediation; query tools stay fail-closed with safe_fallback: "native_search".',
                "staleness_reason": "partial_index_failure",
                "semantic_readiness": "summaries_missing",
                "semantic_ready": False,
                "semantic_remediation": "Run semantic summary/vector generation for the current profile before semantic queries.",
                "force_full_exit_trace": {
                    "status": "interrupted",
                    "stage": "lexical_walking",
                    "stage_family": "lexical",
                    "trace_timestamp": "2026-04-29T16:07:22Z",
                    "current_commit": "fe501b9700000000000000000000000000000000",
                    "indexed_commit_before": "e2e9519800000000000000000000000000000000",
                    "last_progress_path": str(semvisualreport_doc),
                    "in_flight_path": str(later_doc),
                    "blocker_source": "lexical_mutation",
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
    assert (
        "Lexical boundary: using exact bounded Markdown indexing for "
        "plans/phase-plan-v7-SEMSYNCFIX.md -> plans/phase-plan-v7-SEMVISUALREPORT.md"
        in result.output
    )
    assert f"Last progress path: {semvisualreport_doc}" in result.output
    assert f"In-flight path: {later_doc}" in result.output


def test_status_reports_exact_historical_phase_plan_markdown_boundary(
    monkeypatch, tmp_path: Path
):
    runner = CliRunner()
    repo_info = _repo_info(tmp_path)
    watch_doc = repo_info.path / "plans" / "phase-plan-v6-WATCH.md"
    p19_doc = repo_info.path / "plans" / "phase-plan-v1-p19.md"
    later_doc = repo_info.path / "docs" / "status" / "SEMANTIC_DOGFOOD_REBUILD.md"
    watch_doc.parent.mkdir(parents=True)
    later_doc.parent.mkdir(parents=True)
    watch_doc.write_text("# WATCH\n", encoding="utf-8")
    p19_doc.write_text("# P19\n", encoding="utf-8")
    later_doc.write_text("# Evidence\n", encoding="utf-8")

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
                "rollout_remediation": "A required lexical mutation failed.",
                "query_status": "index_unavailable",
                "query_remediation": 'Use native search or follow the readiness remediation; query tools stay fail-closed with safe_fallback: "native_search".',
                "staleness_reason": "partial_index_failure",
                "semantic_readiness": "summaries_missing",
                "semantic_ready": False,
                "semantic_remediation": "Run semantic summary/vector generation for the current profile before semantic queries.",
                "force_full_exit_trace": {
                    "status": "interrupted",
                    "stage": "lexical_walking",
                    "stage_family": "lexical",
                    "trace_timestamp": "2026-04-29T16:18:31Z",
                    "current_commit": "f1ee24f670000000000000000000000000000000",
                    "indexed_commit_before": "fe501b9700000000000000000000000000000000",
                    "last_progress_path": str(p19_doc),
                    "in_flight_path": str(later_doc),
                    "blocker_source": "lexical_mutation",
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
    assert (
        "Lexical boundary: using exact bounded Markdown indexing for "
        "plans/phase-plan-v6-WATCH.md -> plans/phase-plan-v1-p19.md" in result.output
    )
    assert f"Last progress path: {p19_doc}" in result.output
    assert f"In-flight path: {later_doc}" in result.output


def test_status_reports_exact_mixed_version_phase_plan_markdown_boundary(
    monkeypatch, tmp_path: Path
):
    runner = CliRunner()
    repo_info = _repo_info(tmp_path)
    semphasetail_doc = repo_info.path / "plans" / "phase-plan-v7-SEMPHASETAIL.md"
    gagov_doc = repo_info.path / "plans" / "phase-plan-v5-gagov.md"
    later_doc = repo_info.path / "ai_docs" / "celery_overview.md"
    in_flight_doc = repo_info.path / "ai_docs" / "qdrant.md"
    semphasetail_doc.parent.mkdir(parents=True)
    later_doc.parent.mkdir(parents=True)
    semphasetail_doc.write_text("# SEMPHASETAIL\n", encoding="utf-8")
    gagov_doc.write_text("# GAGOV\n", encoding="utf-8")
    later_doc.write_text("# Celery Overview\n", encoding="utf-8")
    in_flight_doc.write_text("# Qdrant\n", encoding="utf-8")

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
                "rollout_remediation": "A required lexical mutation failed.",
                "query_status": "index_unavailable",
                "query_remediation": 'Use native search or follow the readiness remediation; query tools stay fail-closed with safe_fallback: "native_search".',
                "staleness_reason": "partial_index_failure",
                "semantic_readiness": "summaries_missing",
                "semantic_ready": False,
                "semantic_remediation": "Run semantic summary/vector generation for the current profile before semantic queries.",
                "force_full_exit_trace": {
                    "status": "interrupted",
                    "stage": "lexical_walking",
                    "stage_family": "lexical",
                    "trace_timestamp": "2026-04-29T16:42:21Z",
                    "current_commit": "468dee1800000000000000000000000000000000",
                    "indexed_commit_before": "e2e9519800000000000000000000000000000000",
                    "last_progress_path": str(later_doc),
                    "in_flight_path": str(in_flight_doc),
                    "blocker_source": "lexical_mutation",
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
    assert (
        "Lexical boundary: using exact bounded Markdown indexing for "
        "plans/phase-plan-v7-SEMPHASETAIL.md -> plans/phase-plan-v5-gagov.md"
        in result.output
    )
    assert f"Last progress path: {later_doc}" in result.output
    assert f"In-flight path: {in_flight_doc}" in result.output
