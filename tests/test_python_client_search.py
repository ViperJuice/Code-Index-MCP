from pathlib import Path

from mcp_server import ClientSearchOptions, open_client
from tests.fixtures.multi_repo import boot_test_server, build_temp_repo


def test_direct_client_search_returns_typed_matches(tmp_path: Path):
    token = "pyclient_typed_search_token"
    repo_path, _ = build_temp_repo(
        tmp_path,
        "pyclient_search_repo",
        seed_files={"seed.py": f"def typed_search_demo():\n    return '{token}'\n"},
    )

    with boot_test_server(tmp_path, [repo_path]):
        with open_client(workspace_root=repo_path, registry_path=tmp_path / "registry.json") as client:
            result = client.search_code(ClientSearchOptions(query=token))

    assert result.index_unavailable is None
    assert result.results
    assert result.results[0].file.endswith("seed.py")
    assert result.results[0].source_metadata is None


def test_direct_client_search_includes_source_metadata_only_when_requested(tmp_path: Path):
    repo_path, repo_id = build_temp_repo(
        tmp_path,
        "pyclient_metadata_repo",
        seed_files={"seed.py": "# TODO: keep metadata\n"},
    )

    with boot_test_server(tmp_path, [repo_path]) as server:
        store = server.store_registry.get(repo_id)
        with store._get_connection() as conn:
            file_row = conn.execute(
                "SELECT id FROM files WHERE relative_path = 'seed.py'"
            ).fetchone()
        store.store_chunk(
            file_id=file_row[0],
            content="# TODO: keep metadata",
            content_start=0,
            content_end=21,
            line_start=1,
            line_end=1,
            chunk_id="seed.py:1",
            node_id="seed.py:1",
            treesitter_file_id="seed.py",
        )
        with store._get_connection() as conn:
            conn.execute("INSERT INTO fts_code (content, file_id) VALUES (?, ?)", ("TODO", file_row[0]))

        with open_client(workspace_root=repo_path, registry_path=tmp_path / "registry.json") as client:
            plain = client.search_code(ClientSearchOptions(query="TODO"))
            enriched = client.search_code(
                ClientSearchOptions(query="TODO", include_source_metadata=True)
            )

    assert plain.results
    assert plain.results[0].source_metadata is None
    assert enriched.results[0].source_metadata is not None
    assert enriched.results[0].source_metadata["records"][0]["category"] == "todo"
