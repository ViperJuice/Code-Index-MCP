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


def test_handle_search_code_passes_source_filters():
    from mcp_server.cli.tool_handlers import handle_search_code

    dispatcher = MagicMock()
    dispatcher.search.return_value = [
        {
            "file": "/repo/file.py",
            "line": 3,
            "snippet": "TODO",
            "source_metadata": {
                "schema_version": "search_source_metadata.v1",
                "records": [
                    {
                        "source_type": "friction",
                        "category": "todo",
                        "line": 3,
                        "description": "todo",
                        "pattern": "TODO",
                    }
                ],
            },
        }
    ]
    ctx = SimpleNamespace(registry_entry=None, sqlite_store=MagicMock())

    result = _run(
        handle_search_code(
            arguments={
                "query": "todo",
                "source_type": "friction",
                "friction_categories": ["todo"],
                "include_source_metadata": True,
            },
            dispatcher=dispatcher,
            repo_resolver=_Resolver(ctx),
        )
    )

    data = _parsed(result)
    assert data["results"][0]["source_metadata"]["records"][0]["category"] == "todo"
    dispatcher.search.assert_called_once()
    _, kwargs = dispatcher.search.call_args
    assert kwargs["source_type"] == "friction"
    assert kwargs["friction_categories"] == ["todo"]
    assert kwargs["include_source_metadata"] is True


def test_handle_search_code_rejects_unknown_friction_category():
    from mcp_server.cli.tool_handlers import handle_search_code

    result = _run(
        handle_search_code(
            arguments={"query": "todo", "friction_categories": ["bad-category"]},
            dispatcher=MagicMock(),
            repo_resolver=_Resolver(SimpleNamespace(registry_entry=None, sqlite_store=MagicMock())),
        )
    )

    data = _parsed(result)
    assert data["error"] == "Invalid friction categories"
    assert "allowed_categories" in data
