"""PUBNAME public documentation contract checks."""

from __future__ import annotations

from pathlib import Path


REPO = Path(__file__).resolve().parents[2]


def _read(relative_path: str) -> str:
    return (REPO / relative_path).read_text(encoding="utf-8")


def _normalized(relative_path: str) -> str:
    return " ".join(_read(relative_path).replace(">", " ").split())


def test_public_install_docs_use_source_or_local_wheel_proof():
    for relative_path in ("README.md", "docs/GETTING_STARTED.md"):
        text = _read(relative_path)
        assert "pip install index-it-mcp==1.3.0" not in text, relative_path
        assert "uv sync --locked" in text, relative_path

    readme = _read("README.md")
    getting_started = _read("docs/GETTING_STARTED.md")
    assert "dist/index_it_mcp-1.3.0-py3-none-any.whl" in readme
    assert "dist/index_it_mcp-1.3.0-py3-none-any.whl" in getting_started
    assert "July 6, 2026" in readme
    assert "July 6, 2026" in getting_started


def test_public_docs_do_not_treat_code_index_mcp_as_python_install_name():
    for relative_path in (
        "README.md",
        "docs/GETTING_STARTED.md",
        "docs/SUPPORT_MATRIX.md",
        "docs/DOCKER_GUIDE.md",
        "docs/MCP_CONFIGURATION.md",
    ):
        text = _read(relative_path)
        assert "pip install code-index-mcp" not in text, relative_path
        assert "code-index-mcp==" not in text, relative_path


def test_public_docs_classify_non_distribution_code_index_mcp_surfaces():
    readme = _normalized("README.md")
    docker_guide = _normalized("docs/DOCKER_GUIDE.md")
    mcp_config = _normalized("docs/MCP_CONFIGURATION.md")

    assert "client-local MCP server ID" in readme
    assert "repo-shipped profile filename" in readme
    assert "container naming surface" in docker_guide
    assert "not the canonical Python distribution name" in mcp_config
