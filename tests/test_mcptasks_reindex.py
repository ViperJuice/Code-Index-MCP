"""Task-backed reindex tests."""

from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from mcp_server.cli.task_reindex import run_reindex_task
from mcp_server.storage.mcp_task_registry import MCPTaskRegistry
from mcp.types import TaskMetadata


class _FakeTask:
    def __init__(self, task_id: str) -> None:
        self.task_id = task_id
        self._cancelled = False

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled

    def request_cancellation(self) -> None:
        self._cancelled = True


class _FakeDispatcher:
    def __init__(self, *, cancel_on_start: bool = False) -> None:
        self.cancel_on_start = cancel_on_start

    def index_directory(self, ctx, target_path, recursive=True, progress_callback=None, cancel_check=None):
        files = sorted(path for path in target_path.rglob("*.py"))
        if self.cancel_on_start and cancel_check is not None and cancel_check():
            return {
                "cancelled": True,
                "indexed_files": 0,
                "ignored_files": 0,
                "failed_files": 0,
                "total_files": len(files),
                "by_language": {"python": len(files)},
                "semantic_indexed": 0,
                "semantic_failed": 0,
                "semantic_skipped": 0,
                "semantic_blocked": 0,
                "semantic_stage": "cancelled",
                "summaries_written": 0,
                "summary_chunks_attempted": 0,
                "summary_missing_chunks": 0,
                "total_embedding_units": 0,
                "semantic_error": None,
                "semantic_blocker": None,
                "semantic_paths_queued": 0,
                "semantic_indexer_present": False,
            }
        for file_path in files:
            if progress_callback is not None:
                progress_callback(
                    {
                        "stage": "lexical_walking",
                        "last_progress_path": str(file_path),
                        "semantic_stage": "not_run",
                    }
                )
        return {
            "indexed_files": len(files),
            "ignored_files": 0,
            "failed_files": 0,
            "total_files": len(files),
            "by_language": {"python": len(files)},
            "semantic_indexed": 0,
            "semantic_failed": 0,
            "semantic_skipped": 0,
            "semantic_blocked": 0,
            "semantic_stage": "skipped",
            "summaries_written": 0,
            "summary_chunks_attempted": 0,
            "summary_missing_chunks": 0,
            "total_embedding_units": 0,
            "semantic_error": None,
            "semantic_blocker": None,
            "semantic_paths_queued": len(files),
            "semantic_indexer_present": False,
        }


@pytest.mark.asyncio
async def test_run_reindex_task_returns_merge_payload_and_clears_checkpoint(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "a.py").write_text("print('a')\n", encoding="utf-8")
    (repo / "b.py").write_text("print('b')\n", encoding="utf-8")

    registry = MCPTaskRegistry()
    task_state = await registry.create_task(TaskMetadata())
    task = _FakeTask(task_state.taskId)
    active_store = MagicMock()
    active_store.ensure_repository_row.return_value = "repo-row"
    active_store.rebuild_fts_code.return_value = 2
    ctx = SimpleNamespace(repo_id="repo-1", workspace_root=repo)

    result = await run_reindex_task(
        task=task,
        registry=registry,
        dispatcher=_FakeDispatcher(),
        ctx=ctx,
        active_store=active_store,
        target_path=repo,
        requested_path=None,
    )

    payload = result.structuredContent
    assert payload["mode"] == "merge"
    assert payload["mutation_performed"] is True
    assert payload["indexed_files"] == 2
    assert payload["durable_files"] == 2
    assert not (repo / ".reindex-state").exists()


@pytest.mark.asyncio
async def test_run_reindex_task_marks_terminal_payload_cancelled(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "a.py").write_text("print('a')\n", encoding="utf-8")

    registry = MCPTaskRegistry()
    task_state = await registry.create_task(TaskMetadata())
    await registry.request_cancellation(task_state.taskId)
    task = _FakeTask(task_state.taskId)
    active_store = MagicMock()
    active_store.ensure_repository_row.return_value = "repo-row"
    ctx = SimpleNamespace(repo_id="repo-1", workspace_root=repo)

    result = await run_reindex_task(
        task=task,
        registry=registry,
        dispatcher=_FakeDispatcher(cancel_on_start=True),
        ctx=ctx,
        active_store=active_store,
        target_path=repo,
        requested_path=None,
    )

    payload = result.structuredContent
    assert payload["cancelled"] is True
    record = await registry.get_record(task_state.taskId)
    assert record.task.status == "cancelled"
    assert record.terminal_result is not None
