"""P33 production multi-repo isolation matrix."""

from __future__ import annotations

from pathlib import Path

from tests.fixtures.multi_repo import boot_test_server, build_production_matrix


def _result_files(search_response) -> set[str]:
    rows = search_response if isinstance(search_response, list) else search_response["results"]
    return {str(row.get("file", "")) for row in rows}


def test_unrelated_repositories_remain_isolated_across_query_status_and_mutation(tmp_path: Path):
    matrix = build_production_matrix(tmp_path)

    with boot_test_server(tmp_path, matrix.repos) as server:
        alpha_search = server.call_tool(
            "search_code",
            {
                "query": matrix.alpha.token,
                "repository": str(matrix.alpha.path),
                "semantic": False,
            },
        )
        beta_search = server.call_tool(
            "search_code",
            {
                "query": matrix.beta.token,
                "repository": str(matrix.beta.path),
                "semantic": False,
            },
        )

        assert alpha_search
        assert beta_search
        assert all(matrix.alpha.path.name in file for file in _result_files(alpha_search))
        assert all(matrix.beta.path.name in file for file in _result_files(beta_search))

        alpha_miss = server.call_tool(
            "symbol_lookup",
            {"symbol": matrix.beta.symbol, "repository": str(matrix.alpha.path)},
        )
        beta_miss = server.call_tool(
            "symbol_lookup",
            {"symbol": matrix.alpha.symbol, "repository": str(matrix.beta.path)},
        )
        assert alpha_miss["result"] == "not_found"
        assert beta_miss["result"] == "not_found"
        assert alpha_miss["readiness"]["state"] == "ready"
        assert beta_miss["readiness"]["state"] == "ready"

        alpha_lookup = server.call_tool(
            "symbol_lookup",
            {"symbol": matrix.alpha.symbol, "repository": str(matrix.alpha.path)},
        )
        beta_lookup = server.call_tool(
            "symbol_lookup",
            {"symbol": matrix.beta.symbol, "repository": str(matrix.beta.path)},
        )
        assert alpha_lookup["symbol"] == matrix.alpha.symbol
        assert beta_lookup["symbol"] == matrix.beta.symbol
        assert matrix.alpha.path.name in alpha_lookup["defined_in"]
        assert matrix.beta.path.name in beta_lookup["defined_in"]

        status = server.call_tool("get_status", {})
        rows = {row["repo_id"]: row for row in status["repositories"]}
        assert set(rows) == {matrix.alpha.repo_id, matrix.beta.repo_id}
        for row in rows.values():
            assert row["readiness"] == "ready"
            assert row["ready"] is True
            assert row["features"]["lexical"]["status"] == "available"
            assert {"semantic", "graph", "plugins", "cross_repo"} <= set(row["features"])

        new_token = "p33_alpha_after_reindex_token"
        matrix.alpha.write_file(
            "alpha_extra.py",
            f"def {new_token}():\n    return '{new_token}'\n",
        )
        matrix.alpha.commit_all("add alpha-only token")
        server.seed_repo_index(matrix.alpha.repo_id, matrix.alpha.path)

        repaired = server.call_tool(
            "search_code",
            {"query": new_token, "repository": str(matrix.alpha.path), "semantic": False},
        )
        beta_still_isolated = server.call_tool(
            "search_code",
            {"query": matrix.beta.token, "repository": str(matrix.beta.path), "semantic": False},
        )
        assert repaired
        assert beta_still_isolated
        assert all(matrix.beta.path.name in file for file in _result_files(beta_still_isolated))

        watched_file = matrix.alpha.write_file(
            "watcher_event.py",
            "def p33_watcher_event_token():\n    return 'watcher'\n",
        )
        matrix.alpha.commit_all("add watcher-style event")
        server.seed_repo_index(matrix.alpha.repo_id, matrix.alpha.path)
        watched_hit = server.call_tool(
            "search_code",
            {
                "query": "p33_watcher_event_token",
                "repository": str(matrix.alpha.path),
                "semantic": False,
            },
        )
        assert watched_hit

        watched_file.unlink()
        matrix.alpha.commit_all("remove watcher-style event")
        server.seed_repo_index(matrix.alpha.repo_id, matrix.alpha.path)
        watched_removed = server.call_tool(
            "symbol_lookup",
            {"symbol": "p33_watcher_event_token", "repository": str(matrix.alpha.path)},
        )
        assert watched_removed["result"] == "not_found"
