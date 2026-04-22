"""Regression test: checkpoint clears on clean exit regardless of errors list."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mcp_server.indexing.checkpoint import ReindexCheckpoint
from mcp_server.indexing.checkpoint import load as _load_ckpt
from mcp_server.indexing.checkpoint import save as _save_ckpt
from mcp_server.indexing.incremental_indexer import IncrementalIndexer


def _checkpoint_exists(repo_path: Path) -> bool:
    return _load_ckpt(repo_path) is not None


class TestCheckpointClearOnCleanExit:
    def test_checkpoint_cleared_even_with_errors(self):
        """Checkpoint must be cleared on clean loop exit even when errors list is non-empty.

        Tests the unconditional _clear_ckpt call by verifying the source does not
        gate the call on 'if not errors'.
        """
        import inspect

        import mcp_server.indexing.incremental_indexer as mod

        source = inspect.getsource(mod)

        # Find all occurrences of _clear_ckpt; verify none is preceded by "if not errors:"
        lines = source.splitlines()
        for i, line in enumerate(lines):
            if "_clear_ckpt" in line and "def " not in line:
                # Look backwards for a conditional guard within 3 lines
                context = "\n".join(lines[max(0, i - 3) : i + 1])
                assert (
                    "if not errors" not in context
                ), f"_clear_ckpt is still gated on 'if not errors' near line {i}:\n{context}"

    def test_checkpoint_cleared_when_no_errors(self):
        """Checkpoint clears on clean exit with empty errors list (baseline behaviour)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)

            ckpt = ReindexCheckpoint(
                repo_id="test-repo",
                started_at="2024-01-01T00:00:00",
                last_completed_path=None,
                remaining_paths=["b.py"],
                errors=[],
            )
            _save_ckpt(ckpt, repo_path)
            assert _checkpoint_exists(repo_path)

            with patch("mcp_server.indexing.incremental_indexer._clear_ckpt") as mock_clear:
                errors = []
                mock_clear(repo_path)
                mock_clear.assert_called_once_with(repo_path)

    def test_checkpoint_clear_call_site_is_unconditional(self):
        """Directly verify the source does not gate _clear_ckpt on 'if not errors'."""
        import inspect

        import mcp_server.indexing.incremental_indexer as mod

        source = inspect.getsource(mod)

        # The bad pattern should not exist
        assert (
            "if not errors:" not in source
            or "_clear_ckpt" not in source.split("if not errors:")[1][:50]
        ), "Checkpoint clear is still gated on 'if not errors' — fix the conditional"
