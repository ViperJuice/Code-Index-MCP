from pathlib import Path


def test_pyclient_docs_cover_supported_local_contract():
    readme = Path("README.md").read_text(encoding="utf-8")
    api_reference = Path("docs/api/API-REFERENCE.md").read_text(encoding="utf-8")
    support_matrix = Path("docs/SUPPORT_MATRIX.md").read_text(encoding="utf-8")
    status_note = Path("docs/status/python-client-api.md").read_text(encoding="utf-8")
    combined = "\n".join([readme, api_reference, support_matrix, status_note])

    for expected in (
        "mcp_server.client",
        "IndexItClient",
        "ClientSearchOptions",
        "search_code",
        "symbol_lookup",
        "reindex",
        "get_status",
        'source_type="friction"',
        'source_type="history"',
        "index_unavailable",
        "native_search",
        "no remote service client",
    ):
        assert expected in combined
