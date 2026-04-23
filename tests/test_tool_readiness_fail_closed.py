"""P28 query fail-closed readiness tests."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from mcp_server.cli.tool_handlers import handle_search_code, handle_symbol_lookup
from mcp_server.health.repository_readiness import (
    RepositoryReadiness,
    RepositoryReadinessState,
)


def _run(coro):
    return asyncio.run(coro)


def _parsed(result) -> dict:
    return json.loads(result[0].text)


def _readiness(state: RepositoryReadinessState, path: Path) -> RepositoryReadiness:
    return RepositoryReadiness(
        state=state,
        repository_id="repo-1",
        repository_name="repo",
        registered_path=str(path.parent / "registered"),
        requested_path=str(path),
        index_path=str(path / ".mcp-index" / "current.db"),
        remediation=f"remediate {state.value}",
    )


class FakeResolver:
    def __init__(self, readiness: RepositoryReadiness, ctx=None):
        self.readiness = readiness
        self.ctx = ctx
        self.resolve_called = False

    def classify(self, path: Path) -> RepositoryReadiness:
        return self.readiness

    def resolve(self, path: Path):
        self.resolve_called = True
        return self.ctx


NON_READY_STATES = [
    RepositoryReadinessState.UNREGISTERED_REPOSITORY,
    RepositoryReadinessState.MISSING_INDEX,
    RepositoryReadinessState.INDEX_EMPTY,
    RepositoryReadinessState.STALE_COMMIT,
    RepositoryReadinessState.WRONG_BRANCH,
    RepositoryReadinessState.INDEX_BUILDING,
    RepositoryReadinessState.UNSUPPORTED_WORKTREE,
]


@pytest.mark.parametrize("state", NON_READY_STATES)
def test_search_code_non_ready_returns_index_unavailable_without_dispatch(
    tmp_path, monkeypatch, state
):
    monkeypatch.setenv("MCP_ALLOWED_ROOTS", str(tmp_path))
    repo = tmp_path / "repo"
    repo.mkdir()
    dispatcher = MagicMock()
    resolver = FakeResolver(_readiness(state, repo))

    result = _run(
        handle_search_code(
            arguments={"query": "Thing", "repository": str(repo)},
            dispatcher=dispatcher,
            repo_resolver=resolver,
        )
    )

    data = _parsed(result)
    assert data["error"] == "Index unavailable"
    assert data["code"] == "index_unavailable"
    assert data["tool"] == "search_code"
    assert data["safe_fallback"] == "native_search"
    assert data["query"] == "Thing"
    assert data["readiness"]["state"] == state.value
    assert data["readiness"]["ready"] is False
    assert data["remediation"] == f"remediate {state.value}"
    dispatcher.search.assert_not_called()
    assert resolver.resolve_called is False


@pytest.mark.parametrize("state", NON_READY_STATES)
def test_symbol_lookup_non_ready_returns_index_unavailable_without_dispatch(
    tmp_path, monkeypatch, state
):
    monkeypatch.setenv("MCP_ALLOWED_ROOTS", str(tmp_path))
    repo = tmp_path / "repo"
    repo.mkdir()
    dispatcher = MagicMock()
    resolver = FakeResolver(_readiness(state, repo))

    result = _run(
        handle_symbol_lookup(
            arguments={"symbol": "Thing", "repository": str(repo)},
            dispatcher=dispatcher,
            repo_resolver=resolver,
        )
    )

    data = _parsed(result)
    assert data["error"] == "Index unavailable"
    assert data["code"] == "index_unavailable"
    assert data["tool"] == "symbol_lookup"
    assert data["safe_fallback"] == "native_search"
    assert data["symbol"] == "Thing"
    assert data["readiness"]["state"] == state.value
    assert data["readiness"]["ready"] is False
    dispatcher.lookup.assert_not_called()
    assert resolver.resolve_called is False


def test_ready_search_miss_keeps_empty_results_with_readiness(tmp_path, monkeypatch):
    monkeypatch.setenv("MCP_ALLOWED_ROOTS", str(tmp_path))
    repo = tmp_path / "repo"
    repo.mkdir()
    ctx = SimpleNamespace(repo_id="repo-1")
    dispatcher = MagicMock()
    dispatcher.search.return_value = []
    resolver = FakeResolver(_readiness(RepositoryReadinessState.READY, repo), ctx=ctx)

    result = _run(
        handle_search_code(
            arguments={"query": "missing", "repository": str(repo)},
            dispatcher=dispatcher,
            repo_resolver=resolver,
        )
    )

    data = _parsed(result)
    assert data["results"] == []
    assert data["query"] == "missing"
    assert data["readiness"]["state"] == "ready"
    assert data["readiness"]["ready"] is True
    assert data.get("code") != "index_unavailable"
    dispatcher.search.assert_called_once()


def test_ready_symbol_miss_keeps_not_found_with_readiness(tmp_path, monkeypatch):
    monkeypatch.setenv("MCP_ALLOWED_ROOTS", str(tmp_path))
    repo = tmp_path / "repo"
    repo.mkdir()
    ctx = SimpleNamespace(repo_id="repo-1")
    dispatcher = MagicMock()
    dispatcher.lookup.return_value = None
    resolver = FakeResolver(_readiness(RepositoryReadinessState.READY, repo), ctx=ctx)

    result = _run(
        handle_symbol_lookup(
            arguments={"symbol": "Missing", "repository": str(repo)},
            dispatcher=dispatcher,
            repo_resolver=resolver,
        )
    )

    data = _parsed(result)
    assert data["result"] == "not_found"
    assert data["symbol"] == "Missing"
    assert data["readiness"]["state"] == "ready"
    assert data["readiness"]["ready"] is True
    assert data.get("code") != "index_unavailable"
    dispatcher.lookup.assert_called_once()


def test_path_sandbox_error_precedes_readiness_gate(tmp_path, monkeypatch):
    allowed = tmp_path / "allowed"
    outside = tmp_path / "outside"
    allowed.mkdir()
    outside.mkdir()
    monkeypatch.setenv("MCP_ALLOWED_ROOTS", str(allowed))
    dispatcher = MagicMock()
    resolver = FakeResolver(_readiness(RepositoryReadinessState.MISSING_INDEX, outside))

    result = _run(
        handle_search_code(
            arguments={"query": "Thing", "repository": str(outside)},
            dispatcher=dispatcher,
            repo_resolver=resolver,
        )
    )

    data = _parsed(result)
    assert data["code"] == "path_outside_allowed_roots"
    dispatcher.search.assert_not_called()
