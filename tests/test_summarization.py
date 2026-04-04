"""Tests for mcp_server/indexing/summarization.py — ChunkWriter and LazyChunkWriter."""
import asyncio

import pytest

from mcp_server.indexing.summarization import ChunkWriter, LazyChunkWriter


class TestChunkWriterInit:
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
