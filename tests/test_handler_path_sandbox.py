"""SL-1 — Handler-level path sandbox tests.

Tests that search_code, symbol_lookup, and summarize_sample reject
repository/path args that lie outside MCP_ALLOWED_ROOTS, and that
write_summaries (no path args) is unaffected.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _first_text(result) -> str:
    return result[0].text


def _parsed(result) -> dict:
    return json.loads(_first_text(result))


def _run(coro):
    return asyncio.run(coro)


def _mock_dispatcher():
    d = MagicMock()
    d.search.return_value = iter([])
    d.lookup.return_value = None
    return d


def _mock_resolver(ctx=None):
    r = MagicMock()
    r.resolve.return_value = ctx
    return r


# ---------------------------------------------------------------------------
# _looks_like_path unit tests
# ---------------------------------------------------------------------------


class TestLooksLikePath:
    def test_absolute_unix_path(self):
        from mcp_server.cli.tool_handlers import _looks_like_path

        assert _looks_like_path("/tmp/foo") is True

    def test_relative_with_separator(self):
        from mcp_server.cli.tool_handlers import _looks_like_path

        assert _looks_like_path("./foo") is True

    def test_windows_style_path(self):
        from mcp_server.cli.tool_handlers import _looks_like_path

        assert _looks_like_path("C:\\foo\\bar") is True

    def test_plain_repo_name(self):
        from mcp_server.cli.tool_handlers import _looks_like_path

        assert _looks_like_path("my-repo") is False

    def test_plain_repo_name_with_dots(self):
        from mcp_server.cli.tool_handlers import _looks_like_path

        assert _looks_like_path("my.repo.name") is False

    def test_empty_string(self):
        from mcp_server.cli.tool_handlers import _looks_like_path

        assert _looks_like_path("") is False

    def test_existing_filesystem_entity(self, tmp_path):
        from mcp_server.cli.tool_handlers import _looks_like_path

        # tmp_path exists and has '/' in it, so both conditions fire
        assert _looks_like_path(str(tmp_path)) is True

    def test_nonexistent_no_separator(self):
        from mcp_server.cli.tool_handlers import _looks_like_path

        # no separator, doesn't exist → False
        assert _looks_like_path("nonexistent-repo-xyz") is False

    def test_subdir_path(self):
        from mcp_server.cli.tool_handlers import _looks_like_path

        assert _looks_like_path("some/sub/dir") is True


# ---------------------------------------------------------------------------
# search_code guard
# ---------------------------------------------------------------------------


class TestSearchCodePathSandbox:
    def test_rejects_path_outside_allowed_roots(self, tmp_path, monkeypatch):
        from mcp_server.cli.tool_handlers import handle_search_code

        allowed = tmp_path / "allowed"
        allowed.mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()

        monkeypatch.setenv("MCP_ALLOWED_ROOTS", str(allowed))

        result = _run(
            handle_search_code(
                arguments={"query": "foo", "repository": str(outside)},
                dispatcher=_mock_dispatcher(),
                repo_resolver=_mock_resolver(),
            )
        )
        data = _parsed(result)
        assert "path_outside_allowed_roots" in json.dumps(
            data
        ), f"Expected path_outside_allowed_roots in response; got: {data}"

    def test_accepts_path_inside_allowed_roots(self, tmp_path, monkeypatch):
        from mcp_server.cli.tool_handlers import handle_search_code

        allowed = tmp_path / "allowed"
        allowed.mkdir()
        subdir = allowed / "sub"
        subdir.mkdir()

        monkeypatch.setenv("MCP_ALLOWED_ROOTS", str(allowed))

        result = _run(
            handle_search_code(
                arguments={"query": "foo", "repository": str(subdir)},
                dispatcher=_mock_dispatcher(),
                repo_resolver=_mock_resolver(),
            )
        )
        data = _parsed(result)
        assert "path_outside_allowed_roots" not in json.dumps(
            data
        ), f"Should not reject path inside allowed roots; got: {data}"

    def test_accepts_path_inside_second_os_pathsep_root(self, tmp_path, monkeypatch):
        from mcp_server.cli.tool_handlers import handle_search_code

        root_a = tmp_path / "repo-a"
        root_b = tmp_path / "repo-b"
        root_a.mkdir()
        root_b.mkdir()
        subdir = root_b / "sub"
        subdir.mkdir()

        monkeypatch.setenv("MCP_ALLOWED_ROOTS", os.pathsep.join([str(root_a), str(root_b)]))

        result = _run(
            handle_search_code(
                arguments={"query": "foo", "repository": str(subdir)},
                dispatcher=_mock_dispatcher(),
                repo_resolver=_mock_resolver(),
            )
        )
        data = _parsed(result)
        assert "path_outside_allowed_roots" not in json.dumps(
            data
        ), f"Should not reject path inside second allowed root; got: {data}"

    def test_repo_name_passes_through_guard(self, tmp_path, monkeypatch):
        """A plain repo name (no separator) must not be rejected by the path guard."""
        from mcp_server.cli.tool_handlers import handle_search_code

        # Narrow allowed roots to tmp_path — repo name has no separator so guard is bypassed
        monkeypatch.setenv("MCP_ALLOWED_ROOTS", str(tmp_path))

        result = _run(
            handle_search_code(
                arguments={"query": "foo", "repository": "registered-name"},
                dispatcher=_mock_dispatcher(),
                repo_resolver=_mock_resolver(),
            )
        )
        data = _parsed(result)
        assert "path_outside_allowed_roots" not in json.dumps(
            data
        ), f"Repo name should bypass path guard; got: {data}"

    def test_no_repository_arg_bypasses_guard(self, tmp_path, monkeypatch):
        """No repository arg → guard not applicable (falls back to workspace root)."""
        from mcp_server.cli.tool_handlers import handle_search_code

        monkeypatch.setenv("MCP_ALLOWED_ROOTS", str(tmp_path))

        result = _run(
            handle_search_code(
                arguments={"query": "foo"},
                dispatcher=_mock_dispatcher(),
                repo_resolver=_mock_resolver(),
            )
        )
        data = _parsed(result)
        assert "path_outside_allowed_roots" not in json.dumps(data)


# ---------------------------------------------------------------------------
# symbol_lookup guard
# ---------------------------------------------------------------------------


class TestSymbolLookupPathSandbox:
    def test_rejects_path_outside_allowed_roots(self, tmp_path, monkeypatch):
        from mcp_server.cli.tool_handlers import handle_symbol_lookup

        allowed = tmp_path / "allowed"
        allowed.mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()

        monkeypatch.setenv("MCP_ALLOWED_ROOTS", str(allowed))

        result = _run(
            handle_symbol_lookup(
                arguments={"symbol": "MyClass", "repository": str(outside)},
                dispatcher=_mock_dispatcher(),
                repo_resolver=_mock_resolver(),
            )
        )
        data = _parsed(result)
        assert "path_outside_allowed_roots" in json.dumps(
            data
        ), f"Expected path_outside_allowed_roots in response; got: {data}"

    def test_accepts_path_inside_allowed_roots(self, tmp_path, monkeypatch):
        from mcp_server.cli.tool_handlers import handle_symbol_lookup

        allowed = tmp_path / "allowed"
        allowed.mkdir()
        subdir = allowed / "sub"
        subdir.mkdir()

        monkeypatch.setenv("MCP_ALLOWED_ROOTS", str(allowed))

        result = _run(
            handle_symbol_lookup(
                arguments={"symbol": "MyClass", "repository": str(subdir)},
                dispatcher=_mock_dispatcher(),
                repo_resolver=_mock_resolver(),
            )
        )
        data = _parsed(result)
        assert "path_outside_allowed_roots" not in json.dumps(data)

    def test_repo_name_passes_through_guard(self, tmp_path, monkeypatch):
        """A plain repo name bypasses the path guard."""
        from mcp_server.cli.tool_handlers import handle_symbol_lookup

        monkeypatch.setenv("MCP_ALLOWED_ROOTS", str(tmp_path))

        result = _run(
            handle_symbol_lookup(
                arguments={"symbol": "MyClass", "repository": "registered-name"},
                dispatcher=_mock_dispatcher(),
                repo_resolver=_mock_resolver(),
            )
        )
        data = _parsed(result)
        assert "path_outside_allowed_roots" not in json.dumps(data)

    def test_no_repository_arg_bypasses_guard(self, tmp_path, monkeypatch):
        from mcp_server.cli.tool_handlers import handle_symbol_lookup

        monkeypatch.setenv("MCP_ALLOWED_ROOTS", str(tmp_path))

        result = _run(
            handle_symbol_lookup(
                arguments={"symbol": "MyClass"},
                dispatcher=_mock_dispatcher(),
                repo_resolver=_mock_resolver(),
            )
        )
        data = _parsed(result)
        assert "path_outside_allowed_roots" not in json.dumps(data)


# ---------------------------------------------------------------------------
# summarize_sample guard
# ---------------------------------------------------------------------------


class TestSummarizeSamplePathSandbox:
    def _make_lazy_summarizer(self):
        ls = MagicMock()
        ls.can_summarize.return_value = True
        ls._get_model_name.return_value = "test-model"
        return ls

    def _make_sqlite_store(self, db_path: Path):
        s = MagicMock()
        s.db_path = str(db_path)
        return s

    def test_rejects_path_outside_allowed_roots(self, tmp_path, monkeypatch):
        from mcp_server.cli.tool_handlers import handle_summarize_sample

        allowed = tmp_path / "allowed"
        allowed.mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()

        monkeypatch.setenv("MCP_ALLOWED_ROOTS", str(allowed))

        db_file = tmp_path / "test.db"
        db_file.touch()

        result = _run(
            handle_summarize_sample(
                arguments={"paths": [str(outside / "file.py")]},
                dispatcher=_mock_dispatcher(),
                repo_resolver=_mock_resolver(),
                sqlite_store=self._make_sqlite_store(db_file),
                lazy_summarizer=self._make_lazy_summarizer(),
            )
        )
        data = _parsed(result)
        assert "path_outside_allowed_roots" in json.dumps(
            data
        ), f"Expected path_outside_allowed_roots in response; got: {data}"

    def test_rejects_any_bad_path_in_list(self, tmp_path, monkeypatch):
        """Even one outside path in the list triggers rejection."""
        from mcp_server.cli.tool_handlers import handle_summarize_sample

        allowed = tmp_path / "allowed"
        allowed.mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()

        monkeypatch.setenv("MCP_ALLOWED_ROOTS", str(allowed))

        db_file = tmp_path / "test.db"
        db_file.touch()

        good_path = str(allowed / "good.py")
        bad_path = str(outside / "bad.py")

        result = _run(
            handle_summarize_sample(
                arguments={"paths": [good_path, bad_path]},
                dispatcher=_mock_dispatcher(),
                repo_resolver=_mock_resolver(),
                sqlite_store=self._make_sqlite_store(db_file),
                lazy_summarizer=self._make_lazy_summarizer(),
            )
        )
        data = _parsed(result)
        assert "path_outside_allowed_roots" in json.dumps(data)

    def test_accepts_paths_inside_allowed_roots(self, tmp_path, monkeypatch):
        """Paths within allowed roots pass the guard (downstream errors are fine)."""
        import sqlite3 as _sqlite3
        from unittest.mock import patch

        from mcp_server.cli.tool_handlers import handle_summarize_sample

        allowed = tmp_path / "allowed"
        allowed.mkdir()

        monkeypatch.setenv("MCP_ALLOWED_ROOTS", str(allowed))

        db_file = tmp_path / "test.db"
        db_file.touch()

        inside_path = str(allowed / "somefile.py")

        # Stub out sqlite3.connect so no real DB is needed — we only care that the
        # path guard does NOT trigger; downstream behavior is out of scope here.
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.execute.return_value.fetchall.return_value = []

        with patch("sqlite3.connect", return_value=mock_conn):
            result = _run(
                handle_summarize_sample(
                    arguments={"paths": [inside_path]},
                    dispatcher=_mock_dispatcher(),
                    repo_resolver=_mock_resolver(),
                    sqlite_store=self._make_sqlite_store(db_file),
                    lazy_summarizer=self._make_lazy_summarizer(),
                )
            )
        data = _parsed(result)
        assert "path_outside_allowed_roots" not in json.dumps(data)

    def test_no_paths_arg_bypasses_guard(self, tmp_path, monkeypatch):
        """No paths arg → guard not applicable (random sample from DB)."""
        from unittest.mock import patch

        from mcp_server.cli.tool_handlers import handle_summarize_sample

        monkeypatch.setenv("MCP_ALLOWED_ROOTS", str(tmp_path / "narrow"))

        db_file = tmp_path / "test.db"
        db_file.touch()

        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.execute.return_value.fetchall.return_value = []

        with patch("sqlite3.connect", return_value=mock_conn):
            result = _run(
                handle_summarize_sample(
                    arguments={},
                    dispatcher=_mock_dispatcher(),
                    repo_resolver=_mock_resolver(),
                    sqlite_store=self._make_sqlite_store(db_file),
                    lazy_summarizer=self._make_lazy_summarizer(),
                )
            )
        data = _parsed(result)
        assert "path_outside_allowed_roots" not in json.dumps(data)


# ---------------------------------------------------------------------------
# reindex — unchanged (already guarded, just verify pass-through)
# ---------------------------------------------------------------------------


class TestReindexUnchanged:
    def test_reindex_still_guards_via_existing_mechanism(self, tmp_path, monkeypatch):
        """handle_reindex is already guarded; verify it still rejects outside paths."""
        from mcp_server.cli.tool_handlers import handle_reindex

        allowed = tmp_path / "allowed"
        allowed.mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()

        monkeypatch.setenv("MCP_ALLOWED_ROOTS", str(allowed))

        result = _run(
            handle_reindex(
                arguments={"path": str(outside)},
                dispatcher=_mock_dispatcher(),
                repo_resolver=_mock_resolver(),
            )
        )
        data = _parsed(result)
        # reindex uses "Path outside allowed roots" — slightly different wording, that's OK
        dumped = json.dumps(data).lower()
        assert (
            "outside" in dumped or "allowed" in dumped
        ), f"Expected outside-allowed indication in reindex response; got: {data}"


# ---------------------------------------------------------------------------
# write_summaries — no path args, must not be guarded
# ---------------------------------------------------------------------------


class TestWriteSummariesUnguarded:
    def test_write_summaries_not_rejected_by_path_guard(self, tmp_path, monkeypatch):
        """write_summaries has no path args — narrow MCP_ALLOWED_ROOTS must not block it."""
        from unittest.mock import patch

        from mcp_server.cli.tool_handlers import handle_write_summaries

        monkeypatch.setenv("MCP_ALLOWED_ROOTS", str(tmp_path / "narrow"))

        lazy_summarizer = MagicMock()
        lazy_summarizer.can_summarize.return_value = True
        lazy_summarizer._get_model_name.return_value = "test-model"

        db_file = tmp_path / "test.db"
        db_file.touch()
        sqlite_store = MagicMock()
        sqlite_store.db_path = str(db_file)

        mock_writer = MagicMock()
        mock_writer.process_all = AsyncMock(return_value=0)

        with (
            patch("mcp_server.cli.tool_handlers.handle_write_summaries.__module__"),
            patch(
                "mcp_server.indexing.summarization.ComprehensiveChunkWriter",
                return_value=mock_writer,
            ),
        ):
            result = _run(
                handle_write_summaries(
                    arguments={"limit": 1},
                    dispatcher=_mock_dispatcher(),
                    repo_resolver=_mock_resolver(),
                    sqlite_store=sqlite_store,
                    lazy_summarizer=lazy_summarizer,
                )
            )
        data = _parsed(result)
        assert "path_outside_allowed_roots" not in json.dumps(
            data
        ), f"write_summaries should not be path-guarded; got: {data}"
