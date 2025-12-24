"""
Integration test to verify SQLiteStore and IndexEngine work together.
"""

import asyncio
from unittest.mock import Mock

import pytest

from mcp_server.core.path_resolver import PathResolver
from mcp_server.indexer.index_engine import IndexEngine
from mcp_server.plugin_system.interfaces import IPluginManager
from mcp_server.storage.sqlite_store import SQLiteStore


@pytest.fixture
def index_engine_with_store(tmp_path):
    """Create an IndexEngine wired to a real SQLiteStore."""
    db_path = tmp_path / "integration.db"
    store = SQLiteStore(str(db_path), path_resolver=PathResolver(repository_root=tmp_path))

    plugin_manager = Mock(spec=IPluginManager)
    plugin = Mock()
    plugin.parse_file.return_value = {
        "language": "python",
        "symbols": [
            {
                "name": "sample",
                "kind": "function",
                "line_start": 1,
                "line_end": 2,
                "signature": "def sample():",
                "documentation": "sample function",
                "metadata": {},
            }
        ],
        "references": [],
        "metadata": {},
    }
    plugin_manager.get_plugin_for_file.return_value = plugin

    engine = IndexEngine(
        plugin_manager=plugin_manager,
        storage=store,
        repository_path=str(tmp_path),
    )

    return engine, store


def test_index_engine_populates_hashes_and_flags(index_engine_with_store, tmp_path):
    """Index a sample file and verify persisted fields."""
    engine, store = index_engine_with_store
    sample_file = tmp_path / "sample.py"
    sample_file.write_text("def sample():\n    return 1\n")

    result = asyncio.run(engine.index_file(str(sample_file)))

    assert result.success is True

    record = store.get_file(str(sample_file), engine._repository_id)
    assert record is not None
    assert record["hash"]
    assert record["content_hash"]
    assert record["relative_path"] == "sample.py"
    assert record["is_deleted"] in (False, 0)
    assert record["deleted_at"] is None
