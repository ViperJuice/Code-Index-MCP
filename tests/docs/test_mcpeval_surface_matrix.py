"""MCPEVAL compatibility-matrix alignment checks."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
README = REPO / "README.md"
GETTING_STARTED = REPO / "docs" / "GETTING_STARTED.md"
CONFIG = REPO / "docs" / "MCP_CONFIGURATION.md"
SUPPORT_MATRIX = REPO / "docs" / "SUPPORT_MATRIX.md"
EVALUATION = REPO / "docs" / "status" / "MCP_COMPATIBILITY_EVALUATION.md"


def test_evaluation_matrix_names_current_client_and_transport_surfaces() -> None:
    text = EVALUATION.read_text(encoding="utf-8")
    for expected in (
        "Official Python MCP SDK over STDIO",
        "Claude Code over STDIO",
        "Cursor or another editor that launches STDIO MCP servers",
        "FastAPI admin/debug HTTP gateway",
        "Streamable HTTP MCP",
    ):
        assert expected in text


def test_public_docs_keep_stdio_primary_and_fastapi_non_mcp() -> None:
    evaluation_text = EVALUATION.read_text(encoding="utf-8")
    support_text = SUPPORT_MATRIX.read_text(encoding="utf-8")
    getting_started_text = GETTING_STARTED.read_text(encoding="utf-8")
    config_text = CONFIG.read_text(encoding="utf-8")
    readme_text = README.read_text(encoding="utf-8")

    assert "Full compatibility with Claude Code and other MCP clients" not in readme_text
    assert "MCP compatibility matrix" in readme_text
    assert "FastAPI is the admin/debug HTTP surface" in evaluation_text
    assert "Streamable HTTP MCP" in evaluation_text
    assert "Client and transport compatibility" in support_text
    assert "official Python SDK smoke" in getting_started_text
    assert "not the repo's MCP Streamable HTTP transport" in config_text
