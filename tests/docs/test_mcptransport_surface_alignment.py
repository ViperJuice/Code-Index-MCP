from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DOCS = (
    REPO / "README.md",
    REPO / "docs" / "GETTING_STARTED.md",
    REPO / "docs" / "MCP_CONFIGURATION.md",
)
TEMPLATES = tuple(sorted((REPO / ".mcp.json.templates").glob("*.json")))


def _compact(text: str) -> str:
    return " ".join(text.split())


def test_transport_docs_keep_stdio_primary_and_serve_secondary():
    for path in DOCS:
        text = _compact(path.read_text(encoding="utf-8"))
        assert "mcp-index stdio" in text, path
        assert "mcp-index serve" in text, path
        assert "Streamable HTTP transport" in text, path


def test_transport_docs_do_not_register_fastapi_gateway_as_mcp_client():
    for path in DOCS:
        text = path.read_text(encoding="utf-8")
        assert "uvicorn mcp_server.gateway:app" not in text, path
        assert '"command": "uvicorn"' not in text, path


def test_templates_launch_stdio_and_do_not_suggest_http_registration():
    assert TEMPLATES, "expected repo-shipped .mcp.json templates"

    for path in TEMPLATES:
        text = path.read_text(encoding="utf-8")
        assert "mcp-index" in text, path
        assert "stdio" in text, path
        assert "serve" not in text, path
        assert "http://" not in text, path
        assert "https://" not in text, path
