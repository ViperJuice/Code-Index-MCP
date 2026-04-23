"""P33 fail-closed multi-repo regression matrix."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from mcp_server.artifacts.artifact_download import IndexArtifactDownloader
from mcp_server.watcher.ref_poller import RefPoller
from tests.fixtures.multi_repo import boot_test_server, build_production_matrix, git


def _assert_index_unavailable(payload: dict, state: str) -> None:
    assert payload["error"] == "Index unavailable"
    assert payload["code"] == "index_unavailable"
    assert payload["safe_fallback"] == "native_search"
    assert payload["readiness"]["state"] == state
    assert payload["readiness"]["ready"] is False


def _sqlite_symbol_paths(server, repo_id: str, symbol: str) -> list[str]:
    store = server.store_registry.get(repo_id)
    with store._get_connection() as conn:
        return [
            row[0]
            for row in conn.execute(
                """
                SELECT COALESCE(f.relative_path, f.path)
                FROM symbols s
                JOIN files f ON s.file_id = f.id
                WHERE s.name = ?
                  AND (f.is_deleted = 0 OR f.is_deleted IS NULL)
                ORDER BY f.relative_path
                """,
                (symbol,),
            ).fetchall()
        ]


def test_same_repo_linked_worktree_fails_closed_for_queries_and_reindex(tmp_path: Path):
    matrix = build_production_matrix(tmp_path)
    linked = matrix.linked_worktree()

    with boot_test_server(
        tmp_path,
        matrix.repos,
        extra_roots=[linked.worktree_path],
    ) as server:
        search = server.call_tool(
            "search_code",
            {
                "query": matrix.alpha.token,
                "repository": str(linked.worktree_path),
                "semantic": False,
            },
        )
        lookup = server.call_tool(
            "symbol_lookup",
            {"symbol": matrix.alpha.symbol, "repository": str(linked.worktree_path)},
        )
        reindex = server.call_tool("reindex", {"repository": str(linked.worktree_path)})

        _assert_index_unavailable(search, "unsupported_worktree")
        _assert_index_unavailable(lookup, "unsupported_worktree")
        assert reindex["code"] == "unsupported_worktree"
        assert reindex["readiness"]["state"] == "unsupported_worktree"
        assert reindex["results"] == []
        assert reindex["readiness"]["registered_path"] == str(linked.source_path.resolve())


def test_wrong_branch_stale_commit_and_missing_index_do_not_return_empty_results(
    tmp_path: Path,
):
    matrix = build_production_matrix(tmp_path)

    with boot_test_server(tmp_path, matrix.repos) as server:
        matrix.alpha.checkout_new_branch("p33-feature")
        server.registry.update_git_state(matrix.alpha.repo_id)
        wrong_branch = server.call_tool(
            "search_code",
            {
                "query": matrix.alpha.token,
                "repository": str(matrix.alpha.path),
                "semantic": False,
            },
        )
        _assert_index_unavailable(wrong_branch, "wrong_branch")

        matrix.alpha.checkout("main")
        server.registry.update_git_state(matrix.alpha.repo_id)
        matrix.alpha.write_file("stale.py", "def p33_stale_token():\n    return 'stale'\n")
        matrix.alpha.commit_all("make index stale")
        server.registry.update_git_state(matrix.alpha.repo_id)
        stale = server.call_tool(
            "symbol_lookup",
            {"symbol": "p33_stale_token", "repository": str(matrix.alpha.path)},
        )
        _assert_index_unavailable(stale, "stale_commit")

        server.seed_repo_index(matrix.alpha.repo_id, matrix.alpha.path)
        Path(matrix.alpha.path / ".mcp-index" / "current.db").unlink()
        missing = server.call_tool(
            "search_code",
            {
                "query": matrix.alpha.token,
                "repository": str(matrix.alpha.path),
                "semantic": False,
            },
        )
        _assert_index_unavailable(missing, "missing_index")


def test_incremental_repair_revert_rename_and_delete_match_durable_index(tmp_path: Path):
    matrix = build_production_matrix(tmp_path)

    with boot_test_server(tmp_path, matrix.repos) as server:
        renamed_token = "p33_alpha_renamed_token"
        matrix.alpha.write_file(
            "alpha.py",
            f"class {matrix.alpha.symbol}Renamed:\n"
            f"    marker = '{renamed_token}'\n\n"
            f"def {renamed_token}():\n"
            f"    return '{renamed_token}'\n",
        )
        matrix.alpha.rename_file("alpha.py", "renamed_alpha.py", "rename alpha evidence")
        server.seed_repo_index(matrix.alpha.repo_id, matrix.alpha.path)

        renamed = server.call_tool(
            "symbol_lookup",
            {"symbol": renamed_token, "repository": str(matrix.alpha.path)},
        )
        old_token = server.call_tool(
            "symbol_lookup",
            {"symbol": matrix.alpha.token, "repository": str(matrix.alpha.path)},
        )
        assert renamed["symbol"] == renamed_token
        assert "renamed_alpha.py" in renamed["defined_in"]
        assert old_token["result"] == "not_found"

        matrix.alpha.delete_file("renamed_alpha.py", "delete renamed alpha evidence")
        server.seed_repo_index(matrix.alpha.repo_id, matrix.alpha.path)
        assert _sqlite_symbol_paths(server, matrix.alpha.repo_id, renamed_token) == []

        matrix.alpha.write_file(
            "renamed_alpha.py",
            f"class {matrix.alpha.symbol}Restored:\n"
            f"    marker = '{renamed_token}'\n\n"
            f"def {renamed_token}():\n"
            f"    return '{renamed_token}'\n",
        )
        matrix.alpha.commit_all("restore renamed alpha evidence")
        server.seed_repo_index(matrix.alpha.repo_id, matrix.alpha.path)
        assert _sqlite_symbol_paths(server, matrix.alpha.repo_id, renamed_token) == [
            "renamed_alpha.py"
        ]


def test_force_push_ref_movement_queues_full_rescan_instead_of_incremental_sync():
    repo = SimpleNamespace(
        repository_id="repo-p33",
        path="/tmp/p33-repo",
        tracked_branch="main",
        last_indexed_commit="old-sha",
    )
    manager = MagicMock()
    poller = RefPoller(
        registry=MagicMock(list_all=MagicMock(return_value=[repo])),
        git_index_manager=manager,
        dispatcher=MagicMock(),
        repo_resolver=MagicMock(),
        interval_seconds=60,
    )

    def fake_run(cmd, **kwargs):
        result = MagicMock()
        result.returncode = 1
        return result

    with (
        patch.object(poller, "_current_branch", return_value="main"),
        patch.object(poller, "_read_ref", return_value="new-sha"),
        patch("subprocess.run", side_effect=fake_run),
    ):
        poller._poll_one(repo)

    manager.enqueue_full_rescan.assert_called_once_with("repo-p33")
    manager.sync_repository_index.assert_not_called()


def test_wrong_artifact_identity_is_rejected_without_unsafe_override():
    downloader = IndexArtifactDownloader(repo="owner/repo")
    reasons = downloader.validate_artifact_identity(
        {
            "repo_id": "other-repo",
            "tracked_branch": "feature",
            "commit": "old-commit",
            "schema_version": "2",
            "semantic_profile_hash": "wrong-profile",
        },
        repo_id="expected-repo",
        tracked_branch="main",
        target_commit="new-commit",
        semantic_profile_hash="lexical-only",
    )

    assert any("repo_id mismatch" in reason for reason in reasons)
    assert any("tracked_branch mismatch" in reason for reason in reasons)
    assert any("commit mismatch" in reason for reason in reasons)
    assert any("semantic_profile_hash mismatch" in reason for reason in reasons)
