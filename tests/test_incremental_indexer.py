from pathlib import Path
from types import SimpleNamespace

import pytest

from mcp_server.core.path_resolver import PathResolver
from mcp_server.core.repo_context import RepoContext
from mcp_server.indexing.change_detector import FileChange
from mcp_server.indexing.incremental_indexer import IncrementalIndexer
from mcp_server.storage.sqlite_store import SQLiteStore


class DummyDispatcher:
    def __init__(self) -> None:
        self.indexed = []
        self.removed = []
        self.moved = []
        self.semantic_rebuilds = []
        self.summary_contract = {"profile_id": "test-profile", "prompt_fingerprint": "prompt-new"}

    def index_file(self, ctx: RepoContext, path: Path) -> None:
        self.ctx = ctx
        self.indexed.append(Path(path))

    def remove_file(self, ctx: RepoContext, path: Path) -> None:
        self.ctx = ctx
        self.removed.append(Path(path))

    def move_file(
        self, ctx: RepoContext, old_path: Path, new_path: Path, content_hash: str
    ) -> None:
        self.ctx = ctx
        self.moved.append((Path(old_path), Path(new_path), content_hash))

    def rebuild_semantic_for_paths(self, ctx: RepoContext, paths):
        self.ctx = ctx
        self.semantic_rebuilds.append([Path(path) for path in paths])
        return {"semantic_stage": "indexed", "semantic_indexed": len(paths)}

    def get_semantic_summary_contract(self, ctx: RepoContext):
        self.ctx = ctx
        return dict(self.summary_contract)


class DummySemanticIndexer:
    def __init__(self) -> None:
        self.semantic_profile = SimpleNamespace(profile_id="test-profile")
        self.cleanup_calls = []

    def delete_stale_vectors(self, profile_id: str, chunk_ids, sqlite_store=None) -> int:
        self.cleanup_calls.append(
            {
                "profile_id": profile_id,
                "chunk_ids": list(chunk_ids),
                "sqlite_store": sqlite_store,
            }
        )
        return len(chunk_ids)

    def cleanup_stale_semantic_artifacts(self, profile_id: str, invalidation, sqlite_store=None):
        self.cleanup_calls.append(
            {
                "profile_id": profile_id,
                "chunk_ids": list(invalidation.get("vector_chunk_ids", [])),
                "summary_chunk_ids_to_delete": list(
                    invalidation.get("summary_chunk_ids_to_delete", [])
                ),
                "summary_chunk_ids_preserved": list(
                    invalidation.get("summary_chunk_ids_preserved", [])
                ),
                "sqlite_store": sqlite_store,
            }
        )
        if sqlite_store is not None:
            sqlite_store.delete_semantic_point_mappings(
                profile_id,
                list(invalidation.get("vector_chunk_ids", [])),
            )
            sqlite_store.delete_chunk_summaries(
                list(invalidation.get("summary_chunk_ids_to_delete", []))
            )
        return {
            "vectors_deleted": len(invalidation.get("vector_chunk_ids", [])),
            "summaries_deleted": len(invalidation.get("summary_chunk_ids_to_delete", [])),
        }


@pytest.fixture
def incremental_indexer(tmp_path: Path):
    repo_path = tmp_path / "repo"
    repo_path.mkdir()

    store = SQLiteStore(str(tmp_path / "code_index.db"), path_resolver=PathResolver(repo_path))
    repo_id = store.create_repository(str(repo_path), "test-repo")

    dispatcher = DummyDispatcher()
    semantic_indexer = DummySemanticIndexer()
    ctx = RepoContext(
        repo_id=repo_id,
        sqlite_store=store,
        workspace_root=repo_path,
        tracked_branch="main",
        registry_entry=SimpleNamespace(repository_id=repo_id, path=repo_path),
    )
    indexer = IncrementalIndexer(
        store=store,
        dispatcher=dispatcher,
        repo_path=repo_path,
        semantic_indexer=semantic_indexer,
        ctx=ctx,
    )  # type: ignore[arg-type]
    indexer._get_repository_id = lambda: repo_id  # type: ignore[method-assign]

    return repo_path, store, dispatcher, indexer, semantic_indexer, ctx


def test_incremental_addition_handles_new_files(incremental_indexer):
    repo_path, _, dispatcher, indexer, _, ctx = incremental_indexer
    new_file = repo_path / "new_file.py"
    new_file.write_text("print('hello')\n")

    stats = indexer.update_from_changes([FileChange("new_file.py", "added")])

    assert stats.files_indexed == 1
    assert stats.errors == 0
    assert dispatcher.indexed == [new_file]
    assert dispatcher.ctx is ctx


def test_dispatcher_without_repo_context_returns_errors(tmp_path: Path):
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    test_file = repo_path / "new_file.py"
    test_file.write_text("print('hello')\n")
    store = SQLiteStore(str(tmp_path / "code_index.db"), path_resolver=PathResolver(repo_path))
    indexer = IncrementalIndexer(store=store, dispatcher=DummyDispatcher(), repo_path=repo_path)

    stats = indexer.update_from_changes([FileChange("new_file.py", "added")])

    assert stats.files_indexed == 0
    assert stats.errors == 1


def test_incremental_modification_without_hash(incremental_indexer):
    repo_path, store, dispatcher, indexer, semantic_indexer, ctx = incremental_indexer
    existing_file = repo_path / "existing.py"
    existing_file.write_text("value = 1\n")

    repo_id = indexer._get_repository_id()
    file_id = store.store_file(repo_id, existing_file, language="python")
    store.store_chunk(
        file_id=file_id,
        content="value = 1",
        content_start=0,
        content_end=9,
        line_start=1,
        line_end=1,
        chunk_id="chunk-existing-1",
        node_id="node-existing-1",
        treesitter_file_id="ts-existing-1",
    )
    store.upsert_semantic_point(
        profile_id="test-profile",
        chunk_id="chunk-existing-1",
        point_id=9001,
        collection="code-index",
    )

    with store._get_connection() as conn:
        conn.execute("UPDATE files SET content_hash = NULL WHERE id = ?", (file_id,))

    existing_file.write_text("value = 2\n")

    stats = indexer.update_from_changes([FileChange("existing.py", "modified")])

    assert stats.files_indexed == 1
    assert stats.errors == 0
    assert dispatcher.indexed[-1] == existing_file
    assert dispatcher.ctx is ctx
    assert semantic_indexer.cleanup_calls[-1]["chunk_ids"] == ["chunk-existing-1"]


def test_incremental_deletion_handles_missing_files(incremental_indexer):
    repo_path, store, dispatcher, indexer, semantic_indexer, ctx = incremental_indexer
    removed_file = repo_path / "removed.py"
    removed_file.write_text("# to be removed\n")

    repo_id = indexer._get_repository_id()
    file_id = store.store_file(repo_id, removed_file, language="python")
    store.store_chunk(
        file_id=file_id,
        content="# to be removed",
        content_start=0,
        content_end=15,
        line_start=1,
        line_end=1,
        chunk_id="chunk-removed-1",
        node_id="node-removed-1",
        treesitter_file_id="ts-removed-1",
    )
    store.upsert_semantic_point(
        profile_id="test-profile",
        chunk_id="chunk-removed-1",
        point_id=9002,
        collection="code-index",
    )

    removed_file.unlink()
    stats = indexer.update_from_changes([FileChange("removed.py", "deleted")])

    assert stats.files_removed == 1
    assert stats.errors == 0
    assert dispatcher.removed == [repo_path / "removed.py"]
    assert dispatcher.ctx is ctx
    assert semantic_indexer.cleanup_calls[-1]["chunk_ids"] == ["chunk-removed-1"]


def test_incremental_cleanup_includes_split_semantic_chunk_ids(incremental_indexer):
    repo_path, store, dispatcher, indexer, semantic_indexer, ctx = incremental_indexer
    existing_file = repo_path / "split.py"
    existing_file.write_text("value = 1\n")

    repo_id = indexer._get_repository_id()
    file_id = store.store_file(repo_id, existing_file, language="python")
    store.store_chunk(
        file_id=file_id,
        content="value = 1",
        content_start=0,
        content_end=9,
        line_start=1,
        line_end=1,
        chunk_id="chunk-split-1",
        node_id="node-split-1",
        treesitter_file_id="ts-split-1",
    )
    store.upsert_semantic_point(
        profile_id="test-profile",
        chunk_id="chunk-split-1",
        point_id=9101,
        collection="code-index",
    )
    store.upsert_semantic_point(
        profile_id="test-profile",
        chunk_id="chunk-split-1:part:1:3",
        point_id=9102,
        collection="code-index",
    )
    store.upsert_semantic_point(
        profile_id="test-profile",
        chunk_id="chunk-split-1:part:2:3",
        point_id=9103,
        collection="code-index",
    )
    store.upsert_semantic_point(
        profile_id="test-profile",
        chunk_id="split.py:file-summary",
        point_id=9104,
        collection="code-index",
    )

    with store._get_connection() as conn:
        conn.execute("UPDATE files SET content_hash = NULL WHERE id = ?", (file_id,))

    existing_file.write_text("value = 2\n")

    stats = indexer.update_from_changes([FileChange("split.py", "modified")])

    assert stats.files_indexed == 1
    assert stats.errors == 0
    assert dispatcher.indexed[-1] == existing_file
    assert dispatcher.ctx is ctx
    assert semantic_indexer.cleanup_calls[-1]["chunk_ids"] == [
        "chunk-split-1",
        "chunk-split-1:part:1:3",
        "chunk-split-1:part:2:3",
        "split.py:file-summary",
    ]


def test_prompt_fingerprint_drift_forces_reindex_even_when_file_hash_is_unchanged(
    incremental_indexer,
):
    repo_path, store, dispatcher, indexer, semantic_indexer, ctx = incremental_indexer
    existing_file = repo_path / "prompt_drift.py"
    existing_file.write_text("value = 1\n")

    repo_id = indexer._get_repository_id()
    file_id = store.store_file(repo_id, existing_file, language="python")
    store.store_chunk(
        file_id=file_id,
        content="value = 1",
        content_start=0,
        content_end=9,
        line_start=1,
        line_end=1,
        chunk_id="chunk-drift-1",
        node_id="node-drift-1",
        treesitter_file_id="ts-drift-1",
    )
    store.store_chunk_summary(
        chunk_hash="chunk-drift-1",
        file_id=file_id,
        chunk_start=0,
        chunk_end=9,
        summary_text="stale summary",
        llm_model="chat",
        is_authoritative=True,
        profile_id="test-profile",
        prompt_fingerprint="prompt-old",
        audit_metadata={"profile_id": "test-profile", "prompt_fingerprint": "prompt-old"},
    )

    stats = indexer.update_from_changes([FileChange("prompt_drift.py", "modified")])

    assert stats.files_indexed == 1
    assert stats.errors == 0
    assert dispatcher.indexed[-1] == existing_file
    assert semantic_indexer.cleanup_calls[-1]["summary_chunk_ids_to_delete"] == ["chunk-drift-1"]
