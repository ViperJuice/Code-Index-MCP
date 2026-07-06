from pathlib import Path


def test_public_docs_distinguish_python_client_from_mcp_tools():
    readme = Path("README.md").read_text(encoding="utf-8")
    api_reference = Path("docs/api/API-REFERENCE.md").read_text(encoding="utf-8")
    support_matrix = Path("docs/SUPPORT_MATRIX.md").read_text(encoding="utf-8")
    combined = "\n".join([readme, api_reference, support_matrix])

    for expected in (
        "index-it-mcp",
        "Python client",
        "MCP tools remain the preferred LLM surface",
        "local programmatic API",
        "STDIO runner",
    ):
        assert expected in combined
