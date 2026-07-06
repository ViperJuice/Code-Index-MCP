from mcp_server import (
    ClientReindexResult,
    ClientSearchOptions,
    ClientSearchResult,
    ClientStatusResult,
    ClientSymbolResult,
    IndexItClient,
    IndexUnavailable,
    open_client,
)


def test_public_client_exports_are_available_from_mcp_server():
    assert open_client is not None
    assert IndexItClient is not None
    assert ClientSearchOptions is not None
    assert ClientSearchResult is not None
    assert ClientSymbolResult is not None
    assert ClientReindexResult is not None
    assert ClientStatusResult is not None
    assert IndexUnavailable is not None


def test_client_search_options_freeze_source_filters():
    options = ClientSearchOptions(
        query="todo",
        repository="/repo",
        source_type="friction",  # type: ignore[arg-type]
        friction_categories=("todo",),
        history_labels=("reflection", "reflection"),
        history_repos=("owner/repo", "owner/repo"),
        include_source_metadata=True,
    )

    assert options.source_type is not None and options.source_type.value == "friction"
    assert options.friction_categories == ("todo",)
    assert options.history_labels == ("reflection",)
    assert options.history_repos == ("owner/repo",)
    assert options.include_source_metadata is True


def test_invalid_source_type_fails_before_dispatch():
    try:
        ClientSearchOptions(query="demo", source_type="unknown")  # type: ignore[arg-type]
    except ValueError as exc:
        assert "'unknown'" in str(exc)
    else:
        raise AssertionError("expected invalid source type to fail")


def test_distribution_identity_and_client_import_path_stay_separate():
    import importlib.metadata

    assert importlib.metadata.metadata("index-it-mcp")["Name"] == "index-it-mcp"
    assert IndexItClient.__module__ == "mcp_server.client"
