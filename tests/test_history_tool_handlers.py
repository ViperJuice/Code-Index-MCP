import asyncio
import json
from types import SimpleNamespace
from unittest.mock import MagicMock

from mcp_server.health.repository_readiness import RepositoryReadiness, RepositoryReadinessState


def _run(coro):
    return asyncio.run(coro)


def _parsed(result):
    return json.loads(result[0].text)


class _Resolver:
    def __init__(self, ctx):
        self._ctx = ctx

    def classify(self, _path):
        return RepositoryReadiness(
            state=RepositoryReadinessState.READY,
            repository_id="repo-1",
            repository_name="repo",
            requested_path="/repo",
        )

    def resolve(self, _path):
        return self._ctx


def test_handle_search_code_accepts_history_filters():
    from mcp_server.cli.tool_handlers import handle_search_code

    dispatcher = MagicMock()
    dispatcher.search.return_value = [
        {
            "file": "/repo/.mcp-index/history/owner/repo/issues/1.md",
            "line": 1,
            "snippet": "Reflection issue",
            "source_metadata": {
                "schema_version": "search_source_metadata.v1",
                "records": [
                    {
                        "source_type": "history",
                        "type": "reflection",
                        "repo": "owner/repo",
                        "number": 1,
                        "title": "Reflection issue",
                        "labels": ["reflection"],
                        "state": "closed",
                        "created_at": "2026-07-01T00:00:00Z",
                        "updated_at": "2026-07-02T00:00:00Z",
                        "url": "https://github.com/owner/repo/issues/1",
                        "summary": "Reflection issue",
                        "learnings": [],
                    }
                ],
            },
        }
    ]
    ctx = SimpleNamespace(registry_entry=None, sqlite_store=MagicMock())

    result = _run(
        handle_search_code(
            arguments={
                "query": "reflection",
                "source_type": "history",
                "history_labels": ["reflection"],
                "history_repos": ["owner/repo"],
                "include_source_metadata": True,
            },
            dispatcher=dispatcher,
            repo_resolver=_Resolver(ctx),
        )
    )

    data = _parsed(result)
    assert data["results"][0]["source_metadata"]["records"][0]["repo"] == "owner/repo"
    _, kwargs = dispatcher.search.call_args
    assert kwargs["source_type"] == "history"
    assert kwargs["history_labels"] == ["reflection"]
    assert kwargs["history_repos"] == ["owner/repo"]
    assert kwargs["include_source_metadata"] is True


def test_handle_search_code_rejects_unknown_source_type():
    from mcp_server.cli.tool_handlers import handle_search_code

    result = _run(
        handle_search_code(
            arguments={"query": "history", "source_type": "unknown"},
            dispatcher=MagicMock(),
            repo_resolver=_Resolver(SimpleNamespace(registry_entry=None, sqlite_store=MagicMock())),
        )
    )

    data = _parsed(result)
    assert data["error"] == "Invalid source type"
