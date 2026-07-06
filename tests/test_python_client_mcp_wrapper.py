import asyncio
import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from mcp_server.client_types import ClientSearchMatch, ClientSearchResult, IndexUnavailable
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


def test_handle_search_code_delegates_normalized_options_to_shared_service():
    from mcp_server.cli.tool_handlers import handle_search_code

    ctx = SimpleNamespace(registry_entry=None, sqlite_store=MagicMock())

    with patch(
        "mcp_server.cli.tool_handlers.execute_search_service",
        return_value=ClientSearchResult(
            query="todo",
            results=(
                ClientSearchMatch(
                    file="/repo/file.py",
                    line=3,
                    snippet="TODO",
                    source_metadata={
                        "schema_version": "search_source_metadata.v1",
                        "records": [{"source_type": "friction", "category": "todo"}],
                    },
                ),
            ),
            include_source_metadata=True,
        ),
    ) as execute_search_service:
        result = _run(
            handle_search_code(
                arguments={
                    "query": "todo",
                    "source_type": "friction",
                    "friction_categories": ["todo"],
                    "include_source_metadata": True,
                },
                dispatcher=MagicMock(),
                repo_resolver=_Resolver(ctx),
            )
        )

    data = _parsed(result)
    assert data["results"][0]["source_metadata"]["records"][0]["category"] == "todo"
    options = execute_search_service.call_args.kwargs["options"]
    assert options.source_type is not None and options.source_type.value == "friction"
    assert options.friction_categories == ("todo",)
    assert options.include_source_metadata is True


def test_handle_search_code_preserves_semantic_metadata_envelope():
    from mcp_server.cli.tool_handlers import handle_search_code

    ctx = SimpleNamespace(registry_entry=None, sqlite_store=MagicMock())
    semantic_result = ClientSearchResult(
        query="semantic intent",
        code="semantic_not_ready",
        message="Semantic search requested, but enriched semantic vectors are not ready.",
        semantic_requested=True,
        semantic_source="semantic",
        semantic_profile_id="oss_high",
        semantic_collection_name="code_index__oss_high__v1",
        semantic_fallback_status="refused_not_ready",
        semantic_readiness={"state": "summaries_missing", "remediation": "reindex"},
    )

    with patch("mcp_server.cli.tool_handlers.execute_search_service", return_value=semantic_result):
        result = _run(
            handle_search_code(
                arguments={"query": "semantic intent", "semantic": True},
                dispatcher=MagicMock(),
                repo_resolver=_Resolver(ctx),
            )
        )

    data = _parsed(result)
    assert data["code"] == "semantic_not_ready"
    assert data["semantic_profile_id"] == "oss_high"


def test_handle_search_code_preserves_index_unavailable_payload():
    from mcp_server.cli.tool_handlers import handle_search_code

    ctx = SimpleNamespace(registry_entry=None, sqlite_store=MagicMock())
    unavailable = ClientSearchResult(
        query="demo",
        code="index_unavailable",
        message="Indexed search is available only when repository readiness is ready.",
        index_unavailable=IndexUnavailable(
            readiness={"state": "stale_commit", "ready": False},
            remediation="Run reindex.",
            message="Indexed search is available only when repository readiness is ready.",
        ),
    )

    with patch("mcp_server.cli.tool_handlers.execute_search_service", return_value=unavailable):
        result = _run(
            handle_search_code(
                arguments={"query": "demo"},
                dispatcher=MagicMock(),
                repo_resolver=_Resolver(ctx),
            )
        )

    data = _parsed(result)
    assert data["code"] == "index_unavailable"
    assert data["safe_fallback"] == "native_search"
