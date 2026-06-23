"""MCPEVAL prompt-pack contract tests."""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PROMPT_PACK = REPO / "docs" / "evaluations" / "mcpeval-prompt-pack.md"


def test_prompt_pack_contains_at_least_ten_prompts_with_expected_answers() -> None:
    text = PROMPT_PACK.read_text(encoding="utf-8")
    prompts = re.findall(r"^## Prompt \d+", text, flags=re.MULTILINE)
    constraints = text.count("**Expected answer constraints**")

    assert len(prompts) >= 10
    assert constraints == len(prompts)


def test_prompt_pack_covers_required_mcpeval_topics() -> None:
    text = PROMPT_PACK.read_text(encoding="utf-8")
    for expected in (
        "search_code",
        "symbol_lookup",
        "get_status",
        "index_unavailable",
        'safe_fallback: "native_search"',
        "repository",
        "unsupported_worktree",
        "semantic_not_ready",
        "tasks/get",
        "tasks/result",
        "Streamable HTTP",
        "MCP_CLIENT_SECRET",
    ):
        assert expected in text
