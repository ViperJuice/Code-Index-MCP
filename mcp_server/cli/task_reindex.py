"""Task-backed reindex execution helpers."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import anyio
import mcp.types as types
from mcp.server.experimental.task_context import ServerTaskContext

from mcp_server.indexing.checkpoint import ReindexCheckpoint, clear as clear_checkpoint, save
from mcp_server.storage.mcp_task_registry import MCPTaskRegistry


def _call_tool_result(payload: dict[str, Any], *, is_error: bool = False) -> types.CallToolResult:
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=json.dumps(payload, indent=2))],
        structuredContent=payload,
        isError=is_error,
    )


def _record_reindexed_files(active_store: Any, workspace_root: Path, target_path: Path) -> int:
    if active_store is None:
        return 0

    repo_row = active_store.ensure_repository_row(workspace_root)
    if target_path.is_file():
        paths = [target_path]
    else:
        paths = [
            path
            for path in target_path.rglob("*")
            if path.is_file() and ".git" not in path.parts and ".mcp-index" not in path.parts
        ]

    recorded = 0
    for file_path in paths:
        try:
            relative_path = file_path.relative_to(workspace_root).as_posix()
        except ValueError:
            relative_path = file_path.name
        try:
            active_store.store_file(
                repo_row,
                path=file_path,
                relative_path=relative_path,
                language=file_path.suffix.lstrip(".") or None,
                size=file_path.stat().st_size,
            )
            recorded += 1
        except Exception:
            continue
    return recorded


def _candidate_checkpoint_paths(target_path: Path, workspace_root: Path) -> list[str]:
    if target_path.is_file():
        return [target_path.relative_to(workspace_root).as_posix()]
    candidates: list[str] = []
    for path in target_path.rglob("*"):
        if not path.is_file() or ".git" in path.parts or ".mcp-index" in path.parts:
            continue
        try:
            candidates.append(path.relative_to(workspace_root).as_posix())
        except ValueError:
            continue
    return candidates


def _save_checkpoint(
    *,
    ctx: Any,
    pending_paths: list[str],
    last_completed_path: str,
) -> None:
    save(
        ReindexCheckpoint(
            repo_id=ctx.repo_id,
            started_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            last_completed_path=last_completed_path,
            remaining_paths=pending_paths,
        ),
        ctx.workspace_root,
    )


async def run_reindex_task(
    *,
    task: ServerTaskContext,
    registry: MCPTaskRegistry,
    dispatcher: Any,
    ctx: Any,
    active_store: Any,
    target_path: Path,
    requested_path: str | None,
) -> types.CallToolResult:
    repository_scope = str(ctx.workspace_root) if ctx is not None else str(target_path)
    await registry.bind_task(
        task.task_id,
        tool_name="reindex",
        repository=repository_scope,
    )

    if ctx is None:
        raise RuntimeError("Task-backed reindex requires a repository context")

    pending_paths = _candidate_checkpoint_paths(target_path, ctx.workspace_root)
    last_completed_path = ""
    _save_checkpoint(ctx=ctx, pending_paths=pending_paths, last_completed_path=last_completed_path)

    loop = asyncio.get_running_loop()

    async def cancel_observer() -> None:
        while not task.is_cancelled:
            if await registry.is_cancellation_requested(task.task_id):
                task.request_cancellation()
                return
            await anyio.sleep(0.1)

    def publish_progress(progress: dict[str, Any]) -> None:
        nonlocal last_completed_path, pending_paths

        progress_path = progress.get("last_progress_path")
        if progress_path:
            progress_file = Path(progress_path)
            try:
                last_completed_path = progress_file.relative_to(ctx.workspace_root).as_posix()
            except ValueError:
                last_completed_path = progress_file.name
            if last_completed_path in pending_paths:
                pending_paths = pending_paths[pending_paths.index(last_completed_path) + 1 :]
            _save_checkpoint(
                ctx=ctx,
                pending_paths=pending_paths,
                last_completed_path=last_completed_path,
            )

        status_message = (
            f"Reindex {progress.get('stage', 'working')}"
            + (f": {progress_path}" if progress_path else "")
        )
        asyncio.run_coroutine_threadsafe(
            registry.record_progress(
                task.task_id,
                status_message=status_message,
                progress=progress,
            ),
            loop,
        )

    def do_work() -> dict[str, Any]:
        if requested_path and target_path.is_file():
            dispatcher.index_file(ctx, target_path)
            durable_files = _record_reindexed_files(active_store, ctx.workspace_root, target_path)
            return {
                "path": str(target_path),
                "mode": "file",
                "indexed_files": 1,
                "durable_files": durable_files,
                "mutation_performed": True,
                "message": f"Reindexed file: {requested_path}",
            }

        return dispatcher.index_directory(
            ctx,
            target_path,
            recursive=True,
            progress_callback=publish_progress,
            cancel_check=lambda: task.is_cancelled,
        )

    try:
        async with anyio.create_task_group() as tg:
            tg.start_soon(cancel_observer)
            outcome = await asyncio.to_thread(do_work)
            tg.cancel_scope.cancel()
    except Exception:
        if ctx is not None:
            _save_checkpoint(
                ctx=ctx,
                pending_paths=pending_paths,
                last_completed_path=last_completed_path,
            )
        raise

    if requested_path and target_path.is_file():
        clear_checkpoint(ctx.workspace_root)
        return _call_tool_result(outcome)

    if outcome.get("cancelled") or task.is_cancelled:
        payload = {
            "path": str(target_path),
            "mode": "merge",
            "mutation_performed": False,
            "indexed_files": outcome.get("indexed_files"),
            "ignored_files": outcome.get("ignored_files"),
            "failed_files": outcome.get("failed_files"),
            "total_files": outcome.get("total_files"),
            "by_language": outcome.get("by_language"),
            "lexical_rows": None,
            "durable_files": None,
            "semantic_indexed": outcome.get("semantic_indexed"),
            "semantic_failed": outcome.get("semantic_failed"),
            "semantic_skipped": outcome.get("semantic_skipped"),
            "semantic_blocked": outcome.get("semantic_blocked"),
            "semantic_stage": outcome.get("semantic_stage"),
            "summaries_written": outcome.get("summaries_written"),
            "summary_chunks_attempted": outcome.get("summary_chunks_attempted"),
            "summary_missing_chunks": outcome.get("summary_missing_chunks"),
            "total_embedding_units": outcome.get("total_embedding_units"),
            "semantic_error": outcome.get("semantic_error"),
            "semantic_blocker": outcome.get("semantic_blocker"),
            "semantic_paths_queued": outcome.get("semantic_paths_queued"),
            "semantic_indexer_present": outcome.get("semantic_indexer_present"),
            "merge_note": "Reindex cancelled at a safe boundary before final closeout.",
            "cancelled": True,
        }
        result = _call_tool_result(payload)
        await registry.store_result(task.task_id, result)
        await registry.update_task(
            task.task_id,
            status="cancelled",
            status_message="Cancelled at a safe lexical or semantic boundary.",
        )
        return result

    clear_checkpoint(ctx.workspace_root)
    durable_files = _record_reindexed_files(active_store, ctx.workspace_root, target_path)
    lexical_rows = active_store.rebuild_fts_code() if active_store else 0
    return _call_tool_result(
        {
            "path": str(target_path),
            "mode": "merge",
            "mutation_performed": True,
            "indexed_files": outcome.get("indexed_files"),
            "ignored_files": outcome.get("ignored_files"),
            "failed_files": outcome.get("failed_files"),
            "total_files": outcome.get("total_files"),
            "by_language": outcome.get("by_language"),
            "lexical_rows": lexical_rows,
            "durable_files": durable_files,
            "semantic_indexed": outcome.get("semantic_indexed"),
            "semantic_failed": outcome.get("semantic_failed"),
            "semantic_skipped": outcome.get("semantic_skipped"),
            "semantic_blocked": outcome.get("semantic_blocked"),
            "semantic_stage": outcome.get("semantic_stage"),
            "summaries_written": outcome.get("summaries_written"),
            "summary_chunks_attempted": outcome.get("summary_chunks_attempted"),
            "summary_missing_chunks": outcome.get("summary_missing_chunks"),
            "total_embedding_units": outcome.get("total_embedding_units"),
            "semantic_error": outcome.get("semantic_error"),
            "semantic_blocker": outcome.get("semantic_blocker"),
            "semantic_paths_queued": outcome.get("semantic_paths_queued"),
            "semantic_indexer_present": outcome.get("semantic_indexer_present"),
            "merge_note": (
                "Changed/new files updated; deleted files are not purged — "
                "FileWatcher handles those on next change, or reindex again after deletions."
            ),
        }
    )
