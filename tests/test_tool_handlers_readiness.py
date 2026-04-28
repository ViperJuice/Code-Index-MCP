"""P27 tool-handler readiness plumbing tests."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from mcp_server.health.repository_readiness import (
    RepositoryReadiness,
    RepositoryReadinessState,
    SemanticReadiness,
    SemanticReadinessState,
)
from mcp_server.storage.multi_repo_manager import RepositoryInfo


def _run(coro):
    return asyncio.run(coro)


def _parsed(result) -> dict:
    return json.loads(result[0].text)


def _unsupported(path: Path) -> RepositoryReadiness:
    return RepositoryReadiness(
        state=RepositoryReadinessState.UNSUPPORTED_WORKTREE,
        repository_id="repo-1",
        repository_name="repo",
        registered_path=str(path.parent / "registered"),
        requested_path=str(path),
        remediation="Use the registered path or unregister it before registering another worktree.",
    )


class FakeResolver:
    def __init__(self, readiness: RepositoryReadiness):
        self.readiness = readiness
        self.resolve_called = False

    def classify(self, path: Path) -> RepositoryReadiness:
        return self.readiness

    def resolve(self, path: Path):
        self.resolve_called = True
        return None


def _semantic_not_ready() -> SemanticReadiness:
    return SemanticReadiness(
        state=SemanticReadinessState.SUMMARIES_MISSING,
        profile_id="oss_high",
        remediation="Run semantic summary/vector generation for the current profile before semantic queries.",
    )


def test_search_code_exposes_unsupported_worktree_without_dispatch(tmp_path, monkeypatch):
    from mcp_server.cli.tool_handlers import handle_search_code

    monkeypatch.setenv("MCP_ALLOWED_ROOTS", str(tmp_path))
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    dispatcher = MagicMock()
    resolver = FakeResolver(_unsupported(worktree))

    result = _run(
        handle_search_code(
            arguments={"query": "foo", "repository": str(worktree)},
            dispatcher=dispatcher,
            repo_resolver=resolver,
        )
    )

    data = _parsed(result)
    assert data["code"] == "index_unavailable"
    assert data["safe_fallback"] == "native_search"
    assert data["readiness"]["state"] == "unsupported_worktree"
    dispatcher.search.assert_not_called()
    assert resolver.resolve_called is False


def test_symbol_lookup_exposes_unsupported_worktree_without_dispatch(tmp_path, monkeypatch):
    from mcp_server.cli.tool_handlers import handle_symbol_lookup

    monkeypatch.setenv("MCP_ALLOWED_ROOTS", str(tmp_path))
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    dispatcher = MagicMock()
    resolver = FakeResolver(_unsupported(worktree))

    result = _run(
        handle_symbol_lookup(
            arguments={"symbol": "Thing", "repository": str(worktree)},
            dispatcher=dispatcher,
            repo_resolver=resolver,
        )
    )

    data = _parsed(result)
    assert data["code"] == "index_unavailable"
    assert data["safe_fallback"] == "native_search"
    assert data["readiness"]["state"] == "unsupported_worktree"
    dispatcher.lookup.assert_not_called()
    assert resolver.resolve_called is False


def test_reindex_exposes_unsupported_worktree_without_dispatch(tmp_path, monkeypatch):
    from mcp_server.cli.tool_handlers import handle_reindex

    monkeypatch.setenv("MCP_ALLOWED_ROOTS", str(tmp_path))
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    dispatcher = MagicMock()
    resolver = FakeResolver(_unsupported(worktree))

    result = _run(
        handle_reindex(
            arguments={"path": str(worktree)},
            dispatcher=dispatcher,
            repo_resolver=resolver,
        )
    )

    data = _parsed(result)
    assert data["code"] == "unsupported_worktree"
    dispatcher.index_directory.assert_not_called()
    assert resolver.resolve_called is False


def test_get_status_repository_rows_include_readiness(tmp_path):
    from mcp_server.cli.tool_handlers import handle_get_status
    from mcp_server.dispatcher.simple_dispatcher import SimpleDispatcher

    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    index_path = repo_path / ".mcp-index" / "current.db"
    index_path.parent.mkdir()
    index_path.touch()
    info = RepositoryInfo(
        repository_id="repo-1",
        name="repo",
        path=repo_path,
        index_path=index_path,
        language_stats={},
        total_files=0,
        total_symbols=0,
        indexed_at=datetime.now(),
        tracked_branch="main",
        git_common_dir=str(repo_path / ".git"),
    )
    registry = MagicMock()
    registry.get_all_repositories.return_value = {"repo-1": info}
    resolver = MagicMock()
    resolver._registry = registry

    result = _run(
        handle_get_status(
            arguments={},
            dispatcher=SimpleDispatcher(),
            repo_resolver=resolver,
        )
    )

    repos = _parsed(result)["repositories"]
    assert repos[0]["readiness"] == "index_empty"
    assert repos[0]["ready"] is False
    assert repos[0]["readiness_code"] == "index_empty"
    assert repos[0]["semantic_readiness"] == "enrichment_unavailable"
    assert repos[0]["semantic_ready"] is False


def test_search_code_semantic_not_ready_returns_semantic_metadata(tmp_path, monkeypatch):
    import mcp_server.health.repository_readiness as readiness_module
    from mcp_server.cli.tool_handlers import handle_search_code

    monkeypatch.setenv("MCP_ALLOWED_ROOTS", str(tmp_path))
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    dispatcher = MagicMock()
    ctx = MagicMock()
    ctx.registry_entry = SimpleNamespace(path=worktree)
    ctx.sqlite_store = MagicMock()
    ctx.sqlite_store.get_semantic_readiness_evidence.return_value = {
        "profile_id": "oss_high",
        "collection": "code_index__oss_high__v1",
        "total_chunks": 1,
        "summary_count": 0,
        "missing_summaries": 1,
        "vector_link_count": 0,
        "missing_vectors": 1,
        "matching_collection_links": 0,
        "collection_mismatches": 0,
    }
    resolver = FakeResolver(
        RepositoryReadiness(
            state=RepositoryReadinessState.READY,
            repository_id="repo-1",
            repository_name="repo",
            requested_path=str(worktree),
        )
    )
    resolver.resolve = lambda _path: ctx
    monkeypatch.setattr(
        readiness_module,
        "_current_semantic_profile",
        lambda: MagicMock(
            profile_id="oss_high",
            compatibility_fingerprint="fingerprint-1",
            vector_dimension=4096,
            build_metadata={"collection_name": "code_index__oss_high__v1"},
        ),
    )

    result = _run(
        handle_search_code(
            arguments={"query": "semantic intent", "repository": str(worktree), "semantic": True},
            dispatcher=dispatcher,
            repo_resolver=resolver,
        )
    )

    data = _parsed(result)
    assert data["code"] == "semantic_not_ready"
    assert data["semantic_readiness"]["state"] == "summaries_missing"
    dispatcher.search.assert_not_called()
