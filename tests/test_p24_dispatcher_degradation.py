from __future__ import annotations

import logging

from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher


def test_sandbox_unsupported_file_is_quiet_skip(tmp_path, repo_ctx, caplog):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    source = source_dir / "sample.rb"
    source.write_text("puts 'hello'\n", encoding="utf-8")

    dispatcher = EnhancedDispatcher(
        enable_advanced_features=False,
        semantic_search_enabled=False,
        memory_aware=False,
    )

    caplog.set_level(logging.ERROR)
    stats = dispatcher.index_directory(repo_ctx, source_dir, recursive=False)

    assert stats["failed_files"] == 0
    assert not [
        record
        for record in caplog.records
        if "Failed to index" in record.getMessage()
        or "Error loading plugin" in record.getMessage()
    ]
