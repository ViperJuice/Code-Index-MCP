"""README alignment checks for MCPTASKS."""

from __future__ import annotations

from pathlib import Path


README_PATH = Path(__file__).resolve().parents[2] / "README.md"


def test_readme_documents_task_augmented_reindex_and_write_summaries():
    readme = README_PATH.read_text(encoding="utf-8")
    for expected in (
        "execution.taskSupport = \"optional\"",
        "`reindex` and `write_summaries`",
        "`tasks/get`",
        "`tasks/list`",
        "`tasks/result`",
        "`tasks/cancel`",
        "best-effort cancellation",
        "fail synchronously before any task is created",
    ):
        assert expected in readme
