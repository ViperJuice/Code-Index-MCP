from pathlib import Path

import pytest

from mcp_server.core.path_resolver import PathResolver
from mcp_server.indexing.change_detector import FileChange
from mcp_server.indexing.incremental_indexer import IncrementalIndexer
from mcp_server.storage.sqlite_store import SQLiteStore


class DummyDispatcher:
    def __init__(self) -> None:
        self.indexed = []
        self.removed = []
        self.moved = []

    def index_file(self, path: Path) -> None:
        self.indexed.append(Path(path))

    def remove_file(self, path: Path) -> None:
        self.removed.append(Path(path))

    def move_file(self, old_path: Path, new_path: Path, content_hash: str) -> None:
        self.moved.append((Path(old_path), Path(new_path), content_hash))


@pytest.fixture
def incremental_indexer(tmp_path: Path):
    repo_path = tmp_path / "repo"
    repo_path.mkdir()

    store = SQLiteStore(str(tmp_path / "code_index.db"), path_resolver=PathResolver(repo_path))
    repo_id = store.create_repository(str(repo_path), "test-repo")

    dispatcher = DummyDispatcher()
    indexer = IncrementalIndexer(store=store, dispatcher=dispatcher, repo_path=repo_path)
    indexer._get_repository_id = lambda: repo_id  # type: ignore[method-assign]

    return repo_path, store, dispatcher, indexer


def test_incremental_addition_handles_new_files(incremental_indexer):
    repo_path, _, dispatcher, indexer = incremental_indexer
    new_file = repo_path / "new_file.py"
    new_file.write_text("print('hello')\n")

    stats = indexer.update_from_changes([FileChange("new_file.py", "added")])

    assert stats.files_indexed == 1
    assert stats.errors == 0
    assert dispatcher.indexed == [new_file]


def test_incremental_modification_without_hash(incremental_indexer):
    repo_path, store, dispatcher, indexer = incremental_indexer
    existing_file = repo_path / "existing.py"
    existing_file.write_text("value = 1\n")

    repo_id = indexer._get_repository_id()
    file_id = store.store_file(repo_id, existing_file, language="python")
    with store._get_connection() as conn:
        conn.execute("UPDATE files SET content_hash = NULL WHERE id = ?", (file_id,))

    existing_file.write_text("value = 2\n")

    stats = indexer.update_from_changes([FileChange("existing.py", "modified")])

    assert stats.files_indexed == 1
    assert stats.errors == 0
    assert dispatcher.indexed[-1] == existing_file


def test_incremental_deletion_handles_missing_files(incremental_indexer):
    repo_path, store, dispatcher, indexer = incremental_indexer
    removed_file = repo_path / "removed.py"
    removed_file.write_text("# to be removed\n")

    repo_id = indexer._get_repository_id()
    store.store_file(repo_id, removed_file, language="python")

    removed_file.unlink()
    stats = indexer.update_from_changes([FileChange("removed.py", "deleted")])

    assert stats.files_removed == 1
    assert stats.errors == 0
    assert dispatcher.removed == [repo_path / "removed.py"]
