import pytest
import time
from typing import Any, cast

from mcp_server.indexer.hybrid_search import HybridSearch, HybridSearchConfig
from mcp_server.storage.sqlite_store import SQLiteStore
from mcp_server.utils.fuzzy_indexer import FuzzyIndexer


class _SemanticStub:
    def __init__(self) -> None:
        self.is_available = True
        self.connection_mode = "test"

    def validate_connection(self) -> bool:
        return True

    def search(self, query: str, limit: int = 20):
        return [
            {
                "relative_path": "mcp_server/cli/setup_commands.py",
                "score": 0.91,
                "content": f"match for {query}",
            }
        ][:limit]


class _FuzzyStub:
    def search(self, query: str, limit: int = 20):
        return [
            {
                "file": "mcp_server/setup/semantic_preflight.py",
                "snippet": f"fuzzy hit {query}",
            }
        ][:limit]


class _BM25Stub:
    def search(self, query: str, limit: int = 20, **kwargs):
        return [
            {
                "filepath": "mcp_server/cli/setup_commands.py",
                "score": 42.0,
                "snippet": f"bm25 hit {query}",
            }
        ][:limit]


class _SlowSemanticStub(_SemanticStub):
    def search(self, query: str, limit: int = 20):
        time.sleep(0.2)
        return super().search(query, limit)


def test_classic_search_code_fts_handles_string_file_ids(temp_db_path):
    store = SQLiteStore(str(temp_db_path))
    repo_id = store.create_repository("/repo", "repo")
    store.store_file(
        repository_id=repo_id,
        path="/repo/mcp_server/setup/semantic_preflight.py",
        relative_path="mcp_server/setup/semantic_preflight.py",
        language="python",
    )

    with store._get_connection() as conn:
        conn.execute(
            "INSERT INTO fts_code (content, file_id) VALUES (?, ?)",
            (
                "semantic preflight readiness checks",
                "mcp_server/setup/semantic_preflight.py",
            ),
        )

    results = store.search_code_fts("semantic preflight", limit=5)
    assert results
    assert "semantic_preflight.py" in str(results[0].get("file_path", ""))


@pytest.mark.asyncio
async def test_hybrid_handles_sparse_branch_payloads(temp_db_path):
    store = SQLiteStore(str(temp_db_path))

    hybrid = HybridSearch(
        storage=store,
        bm25_indexer=None,
        semantic_indexer=cast(Any, _SemanticStub()),
        fuzzy_indexer=_FuzzyStub(),
        config=HybridSearchConfig(
            enable_bm25=False,
            enable_semantic=True,
            enable_fuzzy=True,
            cache_results=False,
            parallel_execution=True,
            individual_limit=5,
            final_limit=5,
        ),
    )

    results = await hybrid.search(
        "how does semantic setup validate qdrant and embedding readiness",
        limit=5,
    )

    assert results
    assert results[0].get("filepath")


@pytest.mark.asyncio
async def test_hybrid_parallel_timeout_preserves_partial_results(temp_db_path):
    store = SQLiteStore(str(temp_db_path))

    hybrid = HybridSearch(
        storage=store,
        bm25_indexer=cast(Any, _BM25Stub()),
        semantic_indexer=cast(Any, _SlowSemanticStub()),
        fuzzy_indexer=None,
        config=HybridSearchConfig(
            enable_bm25=True,
            enable_semantic=True,
            enable_fuzzy=False,
            cache_results=False,
            parallel_execution=True,
            parallel_timeout_seconds=0.05,
            individual_limit=5,
            final_limit=5,
        ),
    )

    results = await hybrid.search("semantic setup", limit=5)

    assert results
    assert any("setup_commands.py" in str(r.get("filepath", "")) for r in results)


def test_rrf_prefers_best_rank_for_result_metadata(temp_db_path):
    store = SQLiteStore(str(temp_db_path))
    hybrid = HybridSearch(storage=store, config=HybridSearchConfig())

    from mcp_server.indexer.hybrid_search import SearchResult

    result_lists = [
        [
            SearchResult(
                doc_id="doc-1",
                filepath="mcp_server/cli/setup_commands.py",
                score=0.1,
                snippet="rank-1",
                metadata={"origin": "bm25"},
                source="bm25",
            )
        ],
        [
            SearchResult(
                doc_id="doc-1",
                filepath="README.md",
                score=999.0,
                snippet="rank-5",
                metadata={"origin": "semantic"},
                source="semantic",
            )
        ],
    ]

    fused = hybrid._reciprocal_rank_fusion(result_lists)

    assert fused
    assert fused[0].filepath == "mcp_server/cli/setup_commands.py"
