"""Tests for mcp_server/indexing/summarization.py — ChunkWriter and LazyChunkWriter."""

import asyncio
import importlib
import json
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from mcp_server.indexing.summarization import (
    ChunkWriter,
    ComprehensiveChunkWriter,
    FileBatchSummarizer,
    LazyChunkWriter,
    SummaryGenerationResult,
)
from mcp_server.config.settings import get_settings
from mcp_server.setup.semantic_preflight import EnrichmentModelResolution
from mcp_server.storage.sqlite_store import SQLiteStore


def _seed_chunk_summary_tables(db_path: Path, tmp_path: Path) -> tuple[SQLiteStore, int]:
    store = SQLiteStore(str(db_path))
    repo_id = store.ensure_repository_row(tmp_path)
    source_file = tmp_path / "sample.py"
    source_file.write_text("def alpha():\n    return 1\n", encoding="utf-8")
    file_id = store.store_file(
        repo_id,
        path=source_file,
        relative_path="sample.py",
        language="python",
        size=source_file.stat().st_size,
        content_hash="content-hash-1",
    )
    return store, file_id


def _store_chunk(
    store: SQLiteStore,
    *,
    file_id: int,
    chunk_id: str,
    content: str,
    line_start: int,
    line_end: int,
    symbol: str | None = None,
) -> None:
    symbol_id = None
    if symbol is not None:
        symbol_id = store.store_symbol(
            file_id=file_id,
            name=symbol,
            kind="function",
            line_start=line_start,
            line_end=line_end,
        )
    store.store_chunk(
        file_id=file_id,
        content=content,
        content_start=0,
        content_end=len(content),
        line_start=line_start,
        line_end=line_end,
        chunk_id=chunk_id,
        node_id=f"node-{chunk_id}",
        treesitter_file_id=f"tree-{chunk_id}",
        symbol_id=symbol_id,
        language="python",
        node_type="function_definition",
    )


class TestChunkWriterInit:
    def test_module_imports_with_default_install_client_dependency(self):
        module = importlib.import_module("mcp_server.indexing.summarization")
        assert hasattr(module, "ChunkWriter")

    def test_defaults_to_empty_summarization_config(self):
        cw = ChunkWriter(db_path="/tmp/test.db", qdrant_client=None)
        assert cw.summarization_config == {}

    def test_stores_provided_summarization_config(self):
        cfg = {"base_url": "http://localhost:8080", "model_name": "my-model"}
        cw = ChunkWriter(db_path="/tmp/test.db", qdrant_client=None, summarization_config=cfg)
        assert cw.summarization_config == cfg

    def test_stores_db_path_and_qdrant_client(self):
        cw = ChunkWriter(db_path="/data/code.db", qdrant_client="fake-client")
        assert cw.db_path == "/data/code.db"
        assert cw.qdrant_client == "fake-client"

    def test_has_direct_api_true_when_base_url_set(self):
        cw = ChunkWriter(
            db_path="/tmp/test.db",
            qdrant_client=None,
            summarization_config={"base_url": "http://localhost:8080"},
        )
        assert cw._has_direct_api() is True

    def test_has_direct_api_true_when_anthropic_api_key_set(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        monkeypatch.delenv("CEREBRAS_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        cw = ChunkWriter(db_path="/tmp/test.db", qdrant_client=None)
        assert cw._has_direct_api() is True

    def test_has_direct_api_true_when_openai_api_key_set(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("CEREBRAS_API_KEY", raising=False)
        monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-test")
        cw = ChunkWriter(db_path="/tmp/test.db", qdrant_client=None)
        assert cw._has_direct_api() is True

    def test_has_direct_api_false_when_no_keys_and_no_base_url(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("CEREBRAS_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        cw = ChunkWriter(db_path="/tmp/test.db", qdrant_client=None)
        assert cw._has_direct_api() is False

    def test_has_sampling_capability_false_when_session_is_none(self):
        cw = ChunkWriter(db_path="/tmp/test.db", qdrant_client=None)
        assert cw._has_sampling_capability() is False

    def test_can_summarize_false_when_no_api_and_no_session(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("CEREBRAS_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        cw = ChunkWriter(db_path="/tmp/test.db", qdrant_client=None)
        assert cw.can_summarize() is False

    def test_can_summarize_true_when_base_url_in_config(self):
        cw = ChunkWriter(
            db_path="/tmp/test.db",
            qdrant_client=None,
            summarization_config={"base_url": "http://vllm:8000"},
        )
        assert cw.can_summarize() is True


class TestLazyChunkWriterInit:
    def test_constructor_without_summarization_config_defaults_to_empty(self):
        lw = LazyChunkWriter(db_path="/tmp/test.db", qdrant_client=None)
        assert lw.summarization_config == {}

    def test_constructor_accepts_summarization_config(self):
        cfg = {"base_url": "http://vllm:8000", "model_name": "qwen"}
        lw = LazyChunkWriter(db_path="/tmp/test.db", qdrant_client=None, summarization_config=cfg)
        assert lw.summarization_config == cfg

    def test_inherits_chunk_writer(self):
        lw = LazyChunkWriter(db_path="/tmp/test.db", qdrant_client=None)
        assert isinstance(lw, ChunkWriter)

    def test_queue_initialized_as_asyncio_queue(self):
        lw = LazyChunkWriter(db_path="/tmp/test.db", qdrant_client=None)
        assert isinstance(lw.queue, asyncio.Queue)

    def test_task_starts_as_none(self):
        lw = LazyChunkWriter(db_path="/tmp/test.db", qdrant_client=None)
        assert lw._task is None

    def test_update_session_replaces_session_attribute(self):
        lw = LazyChunkWriter(db_path="/tmp/test.db", qdrant_client=None)
        mock_session = object()
        lw.update_session(mock_session)
        assert lw.session is mock_session

    def test_enqueue_puts_item_in_queue(self):
        lw = LazyChunkWriter(db_path="/tmp/test.db", qdrant_client=None)
        chunk = {"chunk_id": "foo.py:1", "content": "x = 1", "language": "python"}
        lw.enqueue(chunk)
        assert lw.queue.qsize() == 1

    def test_enqueue_multiple_items(self):
        lw = LazyChunkWriter(db_path="/tmp/test.db", qdrant_client=None)
        for i in range(5):
            lw.enqueue({"chunk_id": f"foo.py:{i}"})
        assert lw.queue.qsize() == 5

    def test_summarization_config_passed_through_to_has_direct_api(self):
        lw = LazyChunkWriter(
            db_path="/tmp/test.db",
            qdrant_client=None,
            summarization_config={"base_url": "http://localhost:11434"},
        )
        assert lw._has_direct_api() is True


@pytest.mark.asyncio
async def test_file_batch_summarizer_persists_authoritative_audit_metadata(tmp_path):
    db_path = tmp_path / "summaries.db"
    store, file_id = _seed_chunk_summary_tables(db_path, tmp_path)
    summarizer = FileBatchSummarizer(
        db_path=str(db_path),
        qdrant_client=None,
        summarization_config={
            "base_url": "http://ai:8002/v1",
            "model_name": "chat",
            "profile_id": "oss_high",
        },
    )

    async def _fake_batch_api(*_args, **_kwargs):
        return [SimpleNamespace(chunk_id="chunk-1", summary="Semantic summary")]

    summarizer._call_batch_api = _fake_batch_api  # type: ignore[method-assign]
    summarizer._profile_model_resolution = EnrichmentModelResolution(
        configured_model="chat",
        effective_model="cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit",
        resolution_strategy="single_served_model_for_chat_alias",
        available_models=["cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit"],
        models_probe_verified=True,
    )
    result = await summarizer.summarize_file_chunks(
        file_id=file_id,
        file_path=str(tmp_path / "sample.py"),
        file_content="def alpha():\n    return 1\n",
        chunks=[
            {
                "chunk_id": "chunk-1",
                "line_start": 1,
                "line_end": 2,
                "node_type": "function_definition",
                "symbol_id": None,
            }
        ],
        symbol_map={},
        persist=True,
    )

    stored = store.get_chunk_summary("chunk-1")
    assert result.summaries_written == 1
    assert result.missing_chunk_ids == []
    assert stored is not None
    assert stored["is_authoritative"] is True
    assert stored["provider_name"] == "openai_compatible"
    assert stored["profile_id"] == "oss_high"
    assert stored["prompt_fingerprint"]
    assert stored["audit_metadata"]["llm_model"] == "cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit"
    assert stored["audit_metadata"]["configured_model_name"] == "chat"
    assert (
        stored["audit_metadata"]["effective_model_name"]
        == "cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit"
    )
    assert stored["audit_metadata"]["model_resolution_strategy"] == "single_served_model_for_chat_alias"


@pytest.mark.asyncio
async def test_file_batch_summarizer_reports_missing_chunks_without_claiming_success(tmp_path):
    db_path = tmp_path / "summaries.db"
    _, file_id = _seed_chunk_summary_tables(db_path, tmp_path)
    summarizer = FileBatchSummarizer(
        db_path=str(db_path),
        qdrant_client=None,
        summarization_config={"base_url": "http://ai:8002/v1", "model_name": "chat"},
    )

    async def _fake_batch_api(*_args, **_kwargs):
        return [SimpleNamespace(chunk_id="chunk-1", summary="Only one summary")]

    summarizer._call_batch_api = _fake_batch_api  # type: ignore[method-assign]
    result = await summarizer.summarize_file_chunks(
        file_id=file_id,
        file_path=str(tmp_path / "sample.py"),
        file_content="def alpha():\n    return 1\n\ndef beta():\n    return 2\n",
        chunks=[
            {"chunk_id": "chunk-1", "line_start": 1, "line_end": 2, "node_type": "function"},
            {"chunk_id": "chunk-2", "line_start": 4, "line_end": 5, "node_type": "function"},
        ],
        symbol_map={},
        persist=True,
    )

    assert result.summaries_written == 1
    assert result.missing_chunk_ids == ["chunk-2"]


@pytest.mark.asyncio
async def test_file_batch_summarizer_uses_profile_batch_recovery_before_topological_fallback_for_large_files(
    tmp_path, monkeypatch
):
    db_path = tmp_path / "summaries.db"
    store, file_id = _seed_chunk_summary_tables(db_path, tmp_path)
    summarizer = FileBatchSummarizer(
        db_path=str(db_path),
        qdrant_client=None,
        summarization_config={"base_url": "http://ai:8002/v1", "model_name": "chat"},
    )
    topological_called = {"value": False}
    profile_batches: list[list[str]] = []

    async def _raise_large(*_args, **_kwargs):
        raise importlib.import_module("mcp_server.indexing.summarization").FileTooLargeError("big")

    async def _fake_profile_batch(file_id, file_path, file_content, chunks, symbol_map):
        del file_id, file_path, file_content, symbol_map
        profile_batches.append([chunk["chunk_id"] for chunk in chunks])
        return [
            SimpleNamespace(chunk_id=chunk["chunk_id"], summary=f"summary for {chunk['chunk_id']}")
            for chunk in chunks
        ]

    async def _should_not_run(*_args, **_kwargs):
        topological_called["value"] = True
        raise AssertionError("topological fallback should not run when bounded profile recovery succeeds")

    monkeypatch.setenv("OPENAI_API_KEY", "dummy-local-key")
    summarizer._call_batch_api = _raise_large  # type: ignore[method-assign]
    summarizer._call_profile_batch_api = _fake_profile_batch  # type: ignore[method-assign]
    summarizer._summarize_topological = _should_not_run  # type: ignore[method-assign]
    result = await summarizer.summarize_file_chunks(
        file_id=file_id,
        file_path=str(tmp_path / "sample.py"),
        file_content="x" * (
            importlib.import_module("mcp_server.indexing.summarization")._BATCH_FILE_SIZE_THRESHOLD
            + 1
        ),
        chunks=[
            {
                "chunk_id": f"chunk-{idx}",
                "line_start": idx,
                "line_end": idx,
                "node_type": "function",
                "language": "markdown",
            }
            for idx in range(1, 67)
        ],
        symbol_map={},
        persist=True,
    )

    assert topological_called["value"] is False
    assert profile_batches == [[f"chunk-{idx}" for idx in range(1, 67)]]
    assert result.summaries_written == 66
    assert result.missing_chunk_ids == []
    stored = store.get_chunk_summary("chunk-1")
    assert stored is not None
    assert stored["is_authoritative"] is True
    assert stored["provider_name"] == "openai_compatible"


@pytest.mark.asyncio
async def test_file_batch_summarizer_tracks_missing_chunks_after_large_file_profile_batch_recovery(
    tmp_path, monkeypatch
):
    db_path = tmp_path / "summaries.db"
    store, file_id = _seed_chunk_summary_tables(db_path, tmp_path)
    summarizer = FileBatchSummarizer(
        db_path=str(db_path),
        qdrant_client=None,
        summarization_config={
            "base_url": "http://ai:8002/v1",
            "model_name": "chat",
            "profile_id": "oss_high",
        },
    )
    summarizer._profile_model_resolution = EnrichmentModelResolution(
        configured_model="chat",
        effective_model="cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit",
        resolution_strategy="single_served_model_for_chat_alias",
        available_models=["cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit"],
        models_probe_verified=True,
    )

    async def _raise_large(*_args, **_kwargs):
        raise importlib.import_module("mcp_server.indexing.summarization").FileTooLargeError("big")

    profile_api_calls: list[list[str]] = []
    chunk_ids = [f"chunk-{idx}" for idx in range(1, 66 + 1)]

    async def _fake_profile_api(_system: str, prompt: str, **_kwargs) -> tuple[str, str]:
        prompt_chunk_ids = re.findall(r"chunk_id: ([^\n]+)", prompt)
        profile_api_calls.append(prompt_chunk_ids)
        if len(profile_api_calls) == 1:
            returned_ids = prompt_chunk_ids[:64]
        else:
            returned_ids = prompt_chunk_ids[:1]
        payload = {
            "summaries": [
                {"chunk_id": chunk_id, "summary": f"Summary for {chunk_id}. Still concise."}
                for chunk_id in returned_ids
            ]
        }
        return json.dumps(payload), "cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit"

    async def _should_not_run(*_args, **_kwargs):
        raise AssertionError("topological fallback should not run when large-file profile batches succeed")

    monkeypatch.setenv("OPENAI_API_KEY", "dummy-local-key")
    summarizer._call_batch_api = _raise_large  # type: ignore[method-assign]
    summarizer._call_profile_api = _fake_profile_api  # type: ignore[method-assign]
    summarizer._summarize_topological = _should_not_run  # type: ignore[method-assign]
    result = await summarizer.summarize_file_chunks(
        file_id=file_id,
        file_path=str(tmp_path / "sample.md"),
        file_content="x"
        * (
            importlib.import_module("mcp_server.indexing.summarization")._BATCH_FILE_SIZE_THRESHOLD
            + 1
        ),
        chunks=[
            {
                "chunk_id": chunk_id,
                "line_start": idx,
                "line_end": idx,
                "node_type": "paragraph",
                "language": "markdown",
            }
            for idx, chunk_id in enumerate(chunk_ids, start=1)
        ],
        symbol_map={},
        persist=True,
    )

    assert profile_api_calls[0] == chunk_ids[:64]
    assert profile_api_calls[1] == chunk_ids[64:]
    assert result.summaries_written == 65
    assert result.missing_chunk_ids == ["chunk-66"]
    stored = store.get_chunk_summary("chunk-1")
    assert stored is not None
    assert stored["is_authoritative"] is True
    assert stored["provider_name"] == "openai_compatible"
    assert stored["profile_id"] == "oss_high"
    assert stored["audit_metadata"]["configured_model_name"] == "chat"
    assert (
        stored["audit_metadata"]["effective_model_name"]
        == "cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit"
    )


@pytest.mark.asyncio
async def test_file_batch_summarizer_falls_back_to_topological_path_when_large_file_profile_recovery_fails(
    tmp_path, monkeypatch
):
    db_path = tmp_path / "summaries.db"
    _, file_id = _seed_chunk_summary_tables(db_path, tmp_path)
    summarizer = FileBatchSummarizer(
        db_path=str(db_path),
        qdrant_client=None,
        summarization_config={"base_url": "http://ai:8002/v1", "model_name": "chat"},
    )
    topological_called = {"value": False}

    async def _raise_large(*_args, **_kwargs):
        raise importlib.import_module("mcp_server.indexing.summarization").FileTooLargeError("big")

    async def _raise_profile(*_args, **_kwargs):
        raise RuntimeError("profile batch failed")

    async def _fake_topological(*args, **kwargs):
        del args, kwargs
        topological_called["value"] = True
        return importlib.import_module("mcp_server.indexing.summarization").SummaryGenerationResult(
            chunks_attempted=2,
            summaries_written=2,
            authoritative_chunks=2,
            missing_chunk_ids=[],
            files_attempted=1,
            files_summarized=1,
        )

    monkeypatch.setenv("OPENAI_API_KEY", "dummy-local-key")
    summarizer._call_batch_api = _raise_large  # type: ignore[method-assign]
    summarizer._call_profile_batch_api = _raise_profile  # type: ignore[method-assign]
    summarizer._summarize_topological = _fake_topological  # type: ignore[method-assign]
    result = await summarizer.summarize_file_chunks(
        file_id=file_id,
        file_path=str(tmp_path / "sample.py"),
        file_content="x" * (
            importlib.import_module("mcp_server.indexing.summarization")._BATCH_FILE_SIZE_THRESHOLD
            + 1
        ),
        chunks=[
            {"chunk_id": "chunk-1", "line_start": 1, "line_end": 2, "node_type": "function"},
            {"chunk_id": "chunk-2", "line_start": 3, "line_end": 4, "node_type": "function"},
        ],
        symbol_map={},
        persist=False,
    )

    assert topological_called["value"] is True
    assert result.summaries_written == 2


@pytest.mark.asyncio
async def test_file_batch_summarizer_preserves_authoritative_metadata_on_batch_runtime_fallback(
    tmp_path, monkeypatch
):
    db_path = tmp_path / "summaries.db"
    store, file_id = _seed_chunk_summary_tables(db_path, tmp_path)
    profile_id = get_settings().get_semantic_default_profile()
    summarizer = FileBatchSummarizer(
        db_path=str(db_path),
        qdrant_client=None,
        summarization_config={
            **get_settings().get_profile_summarization_config(profile_id),
            "profile_id": profile_id,
        },
    )
    summarizer._profile_model_resolution = EnrichmentModelResolution(
        configured_model="chat",
        effective_model="cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit",
        resolution_strategy="single_served_model_for_chat_alias",
        available_models=["cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit"],
        models_probe_verified=True,
    )

    async def _raise_runtime_mismatch(*_args, **_kwargs):
        raise ImportError("generated client 0.220.0 is incompatible with baml-py 0.221.0")

    async def _fake_profile_api(_system: str, _prompt: str, **_kwargs) -> tuple[str, str]:
        return "Recovered authoritative summary", "cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit"

    monkeypatch.setenv("OPENAI_API_KEY", "dummy-local-key")
    summarizer._call_batch_api = _raise_runtime_mismatch  # type: ignore[method-assign]
    summarizer._call_profile_api = _fake_profile_api  # type: ignore[method-assign]
    result = await summarizer.summarize_file_chunks(
        file_id=file_id,
        file_path=str(tmp_path / "sample.py"),
        file_content="def alpha():\n    return 1\n",
        chunks=[
            {
                "chunk_id": "chunk-1",
                "line_start": 1,
                "line_end": 2,
                "node_type": "function_definition",
                "language": "python",
                "symbol_id": None,
            }
        ],
        symbol_map={},
        persist=True,
    )

    stored = store.get_chunk_summary("chunk-1")
    assert result.summaries_written == 1
    assert result.authoritative_chunks == 1
    assert result.missing_chunk_ids == []
    assert stored is not None
    assert stored["summary_text"] == "Recovered authoritative summary"
    assert stored["is_authoritative"] is True
    assert stored["provider_name"] == "openai_compatible"
    assert stored["profile_id"] == profile_id
    assert stored["audit_metadata"]["llm_model"] == "cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit"
    assert stored["audit_metadata"]["configured_model_name"] == "chat"
    assert (
        stored["audit_metadata"]["effective_model_name"]
        == "cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit"
    )


@pytest.mark.asyncio
async def test_file_batch_summarizer_uses_profile_batch_fallback_before_per_chunk_recovery(
    tmp_path, monkeypatch
):
    db_path = tmp_path / "summaries.db"
    store, file_id = _seed_chunk_summary_tables(db_path, tmp_path)
    summarizer = FileBatchSummarizer(
        db_path=str(db_path),
        qdrant_client=None,
        summarization_config={
            "base_url": "http://ai:8002/v1",
            "model_name": "chat",
            "profile_id": "oss_high",
        },
    )

    async def _raise_runtime_mismatch(*_args, **_kwargs):
        raise ImportError("generated client 0.220.0 is incompatible with baml-py 0.221.0")

    async def _fake_profile_api(_system: str, _prompt: str, **_kwargs) -> tuple[str, str]:
        return (
            '{"summaries":['
            '{"chunk_id":"chunk-1","summary":"Summary one. Still concise."},'
            '{"chunk_id":"chunk-2","summary":"Summary two. Still concise."}'
            ']}',
            "cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit",
        )

    async def _should_not_run(*_args, **_kwargs):
        raise AssertionError("per-chunk fallback should not run when profile batch fallback succeeds")

    monkeypatch.setenv("OPENAI_API_KEY", "dummy-local-key")
    summarizer._call_batch_api = _raise_runtime_mismatch  # type: ignore[method-assign]
    summarizer._call_profile_api = _fake_profile_api  # type: ignore[method-assign]
    summarizer._summarize_topological = _should_not_run  # type: ignore[method-assign]

    result = await summarizer.summarize_file_chunks(
        file_id=file_id,
        file_path=str(tmp_path / "sample.py"),
        file_content="def alpha():\n    return 1\n\ndef beta():\n    return 2\n",
        chunks=[
            {
                "chunk_id": "chunk-1",
                "line_start": 1,
                "line_end": 2,
                "node_type": "function_definition",
                "language": "python",
                "symbol_id": None,
            },
            {
                "chunk_id": "chunk-2",
                "line_start": 4,
                "line_end": 5,
                "node_type": "function_definition",
                "language": "python",
                "symbol_id": None,
            },
        ],
        symbol_map={},
        persist=True,
    )

    stored_one = store.get_chunk_summary("chunk-1")
    stored_two = store.get_chunk_summary("chunk-2")
    assert result.summaries_written == 2
    assert result.missing_chunk_ids == []
    assert stored_one is not None
    assert stored_two is not None
    assert stored_one["summary_text"] == "Summary one. Still concise."
    assert stored_two["summary_text"] == "Summary two. Still concise."


def test_default_oss_high_profile_exposes_direct_summarization_config():
    settings = get_settings()
    profile_id = settings.get_semantic_default_profile()
    config = settings.get_profile_summarization_config(profile_id)

    assert profile_id == "oss_high"
    assert config["base_url"] == "http://ai:8002/v1"
    assert config["model_name"] == "chat"


def test_fetch_unsummarized_rows_filters_scope_before_limit(tmp_path):
    db_path = tmp_path / "summaries.db"
    store = SQLiteStore(str(db_path))
    repo_id = store.ensure_repository_row(tmp_path)

    off_scope = tmp_path / "off_scope.py"
    off_scope.write_text("def off_scope():\n    return 0\n", encoding="utf-8")
    off_scope_file_id = store.store_file(
        repo_id,
        path=off_scope,
        relative_path="off_scope.py",
        language="python",
        size=off_scope.stat().st_size,
        content_hash="off-scope-hash",
    )
    _store_chunk(
        store,
        file_id=off_scope_file_id,
        chunk_id="chunk-off-scope",
        content="def off_scope():\n    return 0\n",
        line_start=1,
        line_end=2,
        symbol="off_scope",
    )

    in_scope = tmp_path / "in_scope.py"
    in_scope.write_text("def in_scope():\n    return 1\n", encoding="utf-8")
    in_scope_file_id = store.store_file(
        repo_id,
        path=in_scope,
        relative_path="in_scope.py",
        language="python",
        size=in_scope.stat().st_size,
        content_hash="in-scope-hash",
    )
    _store_chunk(
        store,
        file_id=in_scope_file_id,
        chunk_id="chunk-in-scope",
        content="def in_scope():\n    return 1\n",
        line_start=1,
        line_end=2,
        symbol="in_scope",
    )

    writer = ComprehensiveChunkWriter(
        db_path=str(db_path),
        qdrant_client=None,
        summarization_config={"base_url": "http://ai:8002/v1", "model_name": "chat"},
    )
    rows = writer._fetch_unsummarized_rows(limit=1, target_paths=[in_scope])

    assert len(rows) == 1
    assert rows[0][0] == "chunk-in-scope"
    assert rows[0][9] == str(in_scope)


@pytest.mark.asyncio
async def test_process_scope_drains_multiple_batches_for_target_scope(tmp_path, monkeypatch):
    db_path = tmp_path / "summaries.db"
    store = SQLiteStore(str(db_path))
    repo_id = store.ensure_repository_row(tmp_path)

    target = tmp_path / "target.py"
    target.write_text(
        "def alpha():\n    return 1\n\ndef beta():\n    return 2\n",
        encoding="utf-8",
    )
    file_id = store.store_file(
        repo_id,
        path=target,
        relative_path="target.py",
        language="python",
        size=target.stat().st_size,
        content_hash="target-hash",
    )
    _store_chunk(
        store,
        file_id=file_id,
        chunk_id="chunk-1",
        content="def alpha():\n    return 1\n",
        line_start=1,
        line_end=2,
        symbol="alpha",
    )
    _store_chunk(
        store,
        file_id=file_id,
        chunk_id="chunk-2",
        content="def beta():\n    return 2\n",
        line_start=4,
        line_end=5,
        symbol="beta",
    )

    writer = ComprehensiveChunkWriter(
        db_path=str(db_path),
        qdrant_client=None,
        summarization_config={"base_url": "http://ai:8002/v1", "model_name": "chat"},
    )
    batch_order: list[list[str]] = []

    async def _fake_summarize_file_chunks(**kwargs):
        chunk_ids = [chunk["chunk_id"] for chunk in kwargs["chunks"]]
        batch_order.append(chunk_ids)
        for chunk_id in chunk_ids:
            store.store_chunk_summary(
                chunk_hash=chunk_id,
                file_id=file_id,
                chunk_start=1,
                chunk_end=2,
                summary_text=f"summary for {chunk_id}",
                llm_model="chat",
                is_authoritative=True,
                symbol=None,
                provider_name="openai_compatible",
                profile_id="oss_high",
                prompt_fingerprint="test-fingerprint",
                audit_metadata={"provider_name": "openai_compatible"},
            )
        return SummaryGenerationResult(
            chunks_attempted=len(chunk_ids),
            summaries_written=len(chunk_ids),
            authoritative_chunks=len(chunk_ids),
            missing_chunk_ids=[],
            files_attempted=1,
            files_summarized=1,
        )

    monkeypatch.setattr(writer, "summarize_file_chunks", _fake_summarize_file_chunks)

    result = await writer.process_scope(limit=1, target_paths=[target])

    assert batch_order == [["chunk-1"], ["chunk-2"]]
    assert result.summaries_written == 2
    assert result.authoritative_chunks == 2
    assert result.chunks_attempted == 2
    assert result.missing_chunk_ids == []


@pytest.mark.asyncio
async def test_process_scope_retries_large_file_profile_recovery_until_backlog_is_drained(
    tmp_path, monkeypatch
):
    db_path = tmp_path / "summaries.db"
    store = SQLiteStore(str(db_path))
    repo_id = store.ensure_repository_row(tmp_path)

    target = tmp_path / "target.md"
    target.write_text("x" * 32, encoding="utf-8")
    file_id = store.store_file(
        repo_id,
        path=target,
        relative_path="target.md",
        language="markdown",
        size=target.stat().st_size,
        content_hash="target-hash",
    )
    for idx in range(1, 4):
        _store_chunk(
            store,
            file_id=file_id,
            chunk_id=f"chunk-{idx}",
            content=f"paragraph {idx}",
            line_start=idx,
            line_end=idx,
            symbol=f"chunk_{idx}",
        )

    writer = ComprehensiveChunkWriter(
        db_path=str(db_path),
        qdrant_client=None,
        summarization_config={
            "base_url": "http://ai:8002/v1",
            "model_name": "chat",
            "profile_id": "oss_high",
        },
    )

    async def _raise_large(*_args, **_kwargs):
        raise importlib.import_module("mcp_server.indexing.summarization").FileTooLargeError("big")

    call_index = {"value": 0}
    seen_batches: list[list[str]] = []

    async def _fake_profile_batch(file_id, file_path, file_content, chunks, symbol_map):
        del file_path, file_content, symbol_map
        call_index["value"] += 1
        chunk_ids = [chunk["chunk_id"] for chunk in chunks]
        seen_batches.append(chunk_ids)
        if call_index["value"] == 1:
            chunk_ids = chunk_ids[:1]
        for chunk_id in chunk_ids:
            store.store_chunk_summary(
                chunk_hash=chunk_id,
                file_id=file_id,
                chunk_start=1,
                chunk_end=1,
                summary_text=f"summary for {chunk_id}",
                llm_model="chat",
                is_authoritative=True,
                symbol=None,
                provider_name="openai_compatible",
                profile_id="oss_high",
                prompt_fingerprint="test-fingerprint",
                audit_metadata={"provider_name": "openai_compatible", "profile_id": "oss_high"},
            )
        return [SimpleNamespace(chunk_id=chunk_id, summary=f"summary for {chunk_id}") for chunk_id in chunk_ids]

    async def _should_not_run(*_args, **_kwargs):
        raise AssertionError("topological fallback should not run when large-file profile recovery keeps making progress")

    monkeypatch.setenv("OPENAI_API_KEY", "dummy-local-key")
    monkeypatch.setattr(writer, "_call_batch_api", _raise_large)
    monkeypatch.setattr(writer, "_call_profile_batch_api", _fake_profile_batch)
    monkeypatch.setattr(writer, "_summarize_topological", _should_not_run)

    result = await writer.process_scope(limit=10, target_paths=[target])

    assert seen_batches == [["chunk-1", "chunk-2", "chunk-3"], ["chunk-2", "chunk-3"]]
    assert result.summaries_written == 3
    assert result.authoritative_chunks == 3
    assert result.chunks_attempted == 5
    assert result.missing_chunk_ids == ["chunk-2", "chunk-3"]
