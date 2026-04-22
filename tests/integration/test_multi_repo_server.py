"""Multi-repo integration tests — SL-3 exit criteria + SL-1 scoped-handler tests.

Four SL-3 tests verifying repo isolation, branch-switch filtering,
worktree identity, and concurrent DB access under the real in-process server.

Four SL-1 tests verifying repository= scoping for reindex/write_summaries/
summarize_sample handlers.
"""

from __future__ import annotations

import asyncio
import sqlite3
import subprocess
import threading
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.fixtures.multi_repo import boot_test_server, build_temp_repo

# ---------------------------------------------------------------------------
# Test 1: Repository isolation
# ---------------------------------------------------------------------------


class TestRepoIsolation:
    def test_repo_isolation(self, tmp_path):
        """Results from repo A must not bleed into repo B and vice versa."""
        repo_a, _ = build_temp_repo(
            tmp_path,
            "repo_a",
            seed_files={"alpha.py": "def zxqfoo_alpha(): pass\n"},
        )
        repo_b, _ = build_temp_repo(
            tmp_path,
            "repo_b",
            seed_files={"beta.py": "def zxqbar_beta(): pass\n"},
        )

        with boot_test_server(tmp_path, [repo_a, repo_b]) as srv:
            results_a = srv.call_tool(
                "search_code",
                {
                    "query": "zxqfoo_alpha",
                    "repository": str(repo_a),
                },
            )
            results_b = srv.call_tool(
                "search_code",
                {
                    "query": "zxqbar_beta",
                    "repository": str(repo_b),
                },
            )

        def extract_paths(result):
            # search_code returns a plain list when results found, dict when empty/error
            if isinstance(result, list):
                return [r.get("file", r.get("path", "")) for r in result]
            return [r.get("file", r.get("path", "")) for r in result.get("results", [])]

        a_paths = extract_paths(results_a)
        b_paths = extract_paths(results_b)

        # At least one result in each (confirms indexing worked)
        assert len(a_paths) >= 1, f"Expected A results, got: {results_a}"
        assert len(b_paths) >= 1, f"Expected B results, got: {results_b}"

        # A results only contain A paths
        for p in a_paths:
            assert str(repo_b) not in p, f"A-search returned B path: {p}"

        # B results only contain B paths
        for p in b_paths:
            assert str(repo_a) not in p, f"B-search returned A path: {p}"


# ---------------------------------------------------------------------------
# Test 2: Branch-switch is ignored
# ---------------------------------------------------------------------------


class TestBranchSwitchIgnored:
    def test_branch_switch_ignored(self, tmp_path):
        """Non-tracked branch commits must not appear in the index."""
        repo_a, repo_id = build_temp_repo(
            tmp_path,
            "repo_a",
            seed_files={"main_file.py": "def tracked_function(): pass\n"},
        )

        poll_interval = 0.5
        with boot_test_server(
            tmp_path,
            [repo_a],
            enable_watchers=True,
            poll_interval=poll_interval,
        ) as srv:
            # Switch to a feature branch, add a new symbol, commit
            subprocess.run(
                ["git", "checkout", "-b", "feature/noise"],
                cwd=str(repo_a),
                check=True,
                capture_output=True,
            )
            (repo_a / "noise_file.py").write_text("def zxq_noise_only(): pass\n")
            subprocess.run(
                ["git", "add", "noise_file.py"],
                cwd=str(repo_a),
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "commit", "-m", "add noise on feature branch"],
                cwd=str(repo_a),
                check=True,
                capture_output=True,
            )

            # Wait 2x poll interval + safety margin
            time.sleep(poll_interval * 2 + 1.0)

            # Assert directly against SQLite — symbol_lookup falls back to
            # language plugins when a symbol is absent, and the C plugin hangs.
            store = srv.repo_resolver._store_registry.get(repo_id)
            conn = sqlite3.connect(store.db_path)
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT count(*) FROM symbols WHERE name = ?",
                    ("zxq_noise_only",),
                )
                count = cursor.fetchone()[0]
            finally:
                conn.close()

        assert count == 0, f"Expected zxq_noise_only NOT in symbols table, found {count} row(s)"


# ---------------------------------------------------------------------------
# Test 3: Worktree equals main repo
# ---------------------------------------------------------------------------


class TestWorktreeEqualsMain:
    def test_worktree_equals_main(self, tmp_path):
        """A git worktree of repo A shares the same repo_id as repo A."""
        from mcp_server.storage.repo_identity import compute_repo_id

        repo_a, _ = build_temp_repo(
            tmp_path,
            "repo_a",
            seed_files={"shared.py": "def zxq_shared_symbol(): pass\n"},
        )

        worktree_path = tmp_path / "repo_a_worktree"
        # "main" is already checked out; create a linked worktree on a detached HEAD
        subprocess.run(
            ["git", "worktree", "add", "--detach", str(worktree_path), "main"],
            cwd=str(repo_a),
            check=True,
            capture_output=True,
        )

        # Confirm compute_repo_id gives the same value for both paths
        main_id = compute_repo_id(repo_a).repo_id
        wt_id = compute_repo_id(worktree_path).repo_id
        assert main_id == wt_id, f"compute_repo_id mismatch: main={main_id} worktree={wt_id}"

        with boot_test_server(tmp_path, [repo_a], extra_roots=[worktree_path]) as srv:
            # Call against the main path
            via_main = srv.call_tool(
                "symbol_lookup",
                {
                    "symbol": "zxq_shared_symbol",
                    "repository": str(repo_a),
                },
            )
            # Call against the worktree path
            via_wt = srv.call_tool(
                "symbol_lookup",
                {
                    "symbol": "zxq_shared_symbol",
                    "repository": str(worktree_path),
                },
            )

        # Both must find the symbol (not "not_found" or "error")
        assert via_main.get("result") != "not_found", f"Main lookup failed: {via_main}"
        assert via_wt.get("result") != "not_found", f"Worktree lookup failed: {via_wt}"


# ---------------------------------------------------------------------------
# Test 4: Concurrent access — no DB lock
# ---------------------------------------------------------------------------


class TestConcurrentNoDbLock:
    def test_concurrent_no_db_lock(self, tmp_path):
        """Concurrent search_code calls across two repos must not hit DB lock."""
        repo_a, _ = build_temp_repo(
            tmp_path,
            "repo_a",
            seed_files={"a.py": "def func_in_a(): pass\n"},
        )
        repo_b, _ = build_temp_repo(
            tmp_path,
            "repo_b",
            seed_files={"b.py": "def func_in_b(): pass\n"},
        )

        errors: list[Exception] = []
        a_results_all: list[list] = []
        b_results_all: list[list] = []

        with boot_test_server(tmp_path, [repo_a, repo_b]) as srv:

            def _extract(r):
                if isinstance(r, list):
                    return r
                return r.get("results", [])

            def search_a():
                local_results = []
                try:
                    for _ in range(10):
                        r = srv.call_tool(
                            "search_code",
                            {
                                "query": "func_in_a",
                                "repository": str(repo_a),
                            },
                        )
                        local_results.extend(_extract(r))
                except sqlite3.OperationalError as e:
                    errors.append(e)
                except Exception as e:
                    if "database is locked" in str(e):
                        errors.append(e)
                a_results_all.append(local_results)

            def search_b():
                local_results = []
                try:
                    for _ in range(10):
                        r = srv.call_tool(
                            "search_code",
                            {
                                "query": "func_in_b",
                                "repository": str(repo_b),
                            },
                        )
                        local_results.extend(_extract(r))
                except sqlite3.OperationalError as e:
                    errors.append(e)
                except Exception as e:
                    if "database is locked" in str(e):
                        errors.append(e)
                b_results_all.append(local_results)

            t1 = threading.Thread(target=search_a)
            t2 = threading.Thread(target=search_b)
            t1.start()
            t2.start()
            t1.join(timeout=30)
            t2.join(timeout=30)

        assert not errors, f"DB lock or errors encountered: {errors}"

        # Cross-contamination check
        a_flat = a_results_all[0] if a_results_all else []
        b_flat = b_results_all[0] if b_results_all else []

        for r in a_flat:
            p = r.get("file", r.get("path", ""))
            assert str(repo_b) not in p, f"Thread 1 (A) returned B path: {p}"

        for r in b_flat:
            p = r.get("file", r.get("path", ""))
            assert str(repo_a) not in p, f"Thread 2 (B) returned A path: {p}"


# ---------------------------------------------------------------------------
# SL-1 Test 5: reindex scoped to a single repo
# ---------------------------------------------------------------------------


class TestReindexScopedToRepo:
    def test_reindex_scoped_to_repo(self, tmp_path):
        """Reindexing repo_b must not touch repo_a's DB."""
        repo_a, repo_id_a = build_temp_repo(
            tmp_path,
            "repo_a",
            seed_files={"a.py": "def func_a(): pass\n"},
        )
        repo_b, repo_id_b = build_temp_repo(
            tmp_path,
            "repo_b",
            seed_files={"b.py": "def func_b(): pass\n"},
        )

        with boot_test_server(tmp_path, [repo_a, repo_b]) as srv:
            db_path_a = srv.store_registry.get(repo_id_a).db_path
            mtime_a_before = Path(db_path_a).stat().st_mtime_ns

            result = srv.call_tool("reindex", {"repository": str(repo_b)})

        assert (
            Path(db_path_a).stat().st_mtime_ns == mtime_a_before
        ), "Reindex of repo_b modified repo_a's DB"
        # reindex returns indexed_files / error key — not a cross-repo error
        assert (
            "error" not in result or result.get("code") != "path_outside_allowed_roots"
        ), f"Unexpected error: {result}"


# ---------------------------------------------------------------------------
# SL-1 Test 6: reindex rejects inconsistent path + repository
# ---------------------------------------------------------------------------


class TestReindexRejectsInconsistentPathAndRepository:
    def test_reindex_rejects_inconsistent_path_and_repository(self, tmp_path):
        """Passing path=repo_a + repository=repo_b must fail with structured error."""
        repo_a, repo_id_a = build_temp_repo(
            tmp_path,
            "repo_a",
            seed_files={"a.py": "def func_a(): pass\n"},
        )
        repo_b, repo_id_b = build_temp_repo(
            tmp_path,
            "repo_b",
            seed_files={"b.py": "def func_b(): pass\n"},
        )

        with boot_test_server(tmp_path, [repo_a, repo_b]) as srv:
            db_path_a = srv.store_registry.get(repo_id_a).db_path
            db_path_b = srv.store_registry.get(repo_id_b).db_path
            mtime_a_before = Path(db_path_a).stat().st_mtime_ns
            mtime_b_before = Path(db_path_b).stat().st_mtime_ns

            result = srv.call_tool(
                "reindex",
                {
                    "path": str(repo_a),
                    "repository": str(repo_b),
                },
            )

        assert (
            result.get("code") == "conflicting_path_and_repository"
        ), f"Expected conflicting_path_and_repository, got: {result}"
        assert Path(db_path_a).stat().st_mtime_ns == mtime_a_before, "repo_a DB was modified"
        assert Path(db_path_b).stat().st_mtime_ns == mtime_b_before, "repo_b DB was modified"


# ---------------------------------------------------------------------------
# SL-1 Test 7: write_summaries scoped to a single repo
# ---------------------------------------------------------------------------


class TestWriteSummariesScopedToRepo:
    def test_write_summaries_scoped_to_repo(self, tmp_path):
        """write_summaries with repository=repo_b must not write summaries for repo_a files."""
        repo_a, repo_id_a = build_temp_repo(
            tmp_path,
            "repo_a",
            seed_files={"a.py": "def func_a(): pass\n"},
        )
        repo_b, repo_id_b = build_temp_repo(
            tmp_path,
            "repo_b",
            seed_files={"b.py": "def func_b(): pass\n"},
        )

        mock_lazy_summarizer = MagicMock()
        mock_lazy_summarizer.can_summarize.return_value = True
        mock_lazy_summarizer._get_model_name.return_value = "test-model"

        mock_writer = MagicMock()
        mock_writer.process_all = AsyncMock(return_value=0)

        with boot_test_server(tmp_path, [repo_a, repo_b]) as srv:
            store_b = srv.store_registry.get(repo_id_b)

            from mcp_server.cli import tool_handlers

            loop = asyncio.new_event_loop()
            try:
                with patch(
                    "mcp_server.indexing.summarization.ComprehensiveChunkWriter",
                    return_value=mock_writer,
                ):
                    result = loop.run_until_complete(
                        tool_handlers.handle_write_summaries(
                            arguments={"repository": str(repo_b)},
                            dispatcher=srv.dispatcher,
                            repo_resolver=srv.repo_resolver,
                            sqlite_store=store_b,
                            lazy_summarizer=mock_lazy_summarizer,
                        )
                    )
            finally:
                loop.close()

        result_data = __import__("json").loads(result[0].text)
        # Should not return an error about sqlite_store missing or unavailable
        assert (
            "error" not in result_data or result_data.get("error") != "sqlite_store not initialized"
        ), f"Expected write_summaries to run, got: {result_data}"
        mock_writer.process_all.assert_called_once()


# ---------------------------------------------------------------------------
# SL-1 Test 8: summarize_sample scoped to a single repo
# ---------------------------------------------------------------------------


class TestSummarizeSampleScopedToRepo:
    def test_summarize_sample_scoped_to_repo(self, tmp_path):
        """summarize_sample with repository=repo_b must only process repo_b files."""
        repo_a, repo_id_a = build_temp_repo(
            tmp_path,
            "repo_a",
            seed_files={"a.py": "def func_a(): pass\n"},
        )
        repo_b, repo_id_b = build_temp_repo(
            tmp_path,
            "repo_b",
            seed_files={"b.py": "def func_b(): pass\n"},
        )

        mock_lazy_summarizer = MagicMock()
        mock_lazy_summarizer.can_summarize.return_value = True
        mock_lazy_summarizer._get_model_name.return_value = "test-model"

        with boot_test_server(tmp_path, [repo_a, repo_b]) as srv:
            store_b = srv.store_registry.get(repo_id_b)

            from mcp_server.cli import tool_handlers

            loop = asyncio.new_event_loop()
            try:
                result = loop.run_until_complete(
                    tool_handlers.handle_summarize_sample(
                        arguments={"repository": str(repo_b), "n": 1},
                        dispatcher=srv.dispatcher,
                        repo_resolver=srv.repo_resolver,
                        sqlite_store=store_b,
                        lazy_summarizer=mock_lazy_summarizer,
                    )
                )
            finally:
                loop.close()

        result_data = __import__("json").loads(result[0].text)
        # All file_path entries in result must be under repo_b
        for file_entry in result_data.get("files", []):
            fp = file_entry.get("file_path", "")
            if fp and not file_entry.get("error"):
                assert (
                    str(repo_b) in fp
                ), f"summarize_sample returned file from outside repo_b: {fp}"
