import json


def test_store_chunk_enriches_metadata_and_preserves_existing_keys(sqlite_store):
    repo_id = sqlite_store.create_repository("/repo", "repo")
    file_id = sqlite_store.store_file(repo_id, "/repo/file.py", "file.py", language="python")

    sqlite_store.store_chunk(
        file_id=file_id,
        content="# TODO: tighten typing",
        content_start=0,
        content_end=22,
        line_start=10,
        line_end=10,
        chunk_id="chunk-1",
        node_id="node-1",
        treesitter_file_id="ts-1",
        metadata={"language": "python"},
    )

    chunk = sqlite_store.get_chunk_by_chunk_id("chunk-1", file_id=file_id)
    stored_metadata = json.loads(chunk["metadata"])
    assert stored_metadata["language"] == "python"
    assert stored_metadata["source_metadata"]["records"][0]["line"] == 10


def test_store_chunks_batch_and_source_metadata_search_use_existing_schema(sqlite_store):
    repo_id = sqlite_store.create_repository("/repo", "repo")
    file_id = sqlite_store.store_file(repo_id, "/repo/file.py", "file.py", language="python")

    stored = sqlite_store.store_chunks_batch(
        [
            {
                "file_id": file_id,
                "content": "# FIXME: batch item",
                "content_start": 0,
                "content_end": 20,
                "line_start": 3,
                "line_end": 3,
                "chunk_id": "chunk-1",
                "node_id": "node-1",
                "treesitter_file_id": "ts-1",
            },
            {
                "file_id": file_id,
                "content": "plain chunk",
                "content_start": 21,
                "content_end": 31,
                "line_start": 5,
                "line_end": 5,
                "chunk_id": "chunk-2",
                "node_id": "node-2",
                "treesitter_file_id": "ts-2",
            },
        ]
    )

    assert stored == 2
    results = sqlite_store.search_chunks_by_source_metadata(
        source_type="friction",
        friction_categories=["fixme"],
        limit=10,
    )
    assert len(results) == 1
    assert results[0]["file"] == "/repo/file.py"
    assert results[0]["source_metadata"]["records"][0]["category"] == "fixme"
