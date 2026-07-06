from mcp_server.indexing.friction import extract_friction_markers
from mcp_server.indexing.source_metadata import merge_source_metadata


def test_markdown_and_plaintext_markers_are_detected():
    markdown = "<!-- TODO: document gap -->\n\n## Heading\nWISH improve docs"
    plaintext = "WORKAROUND: use the legacy path"

    markdown_markers = extract_friction_markers(markdown)
    plaintext_markers = extract_friction_markers(plaintext)

    assert [marker["category"] for marker in markdown_markers] == ["todo", "wish"]
    assert plaintext_markers[0]["category"] == "workaround"


def test_semantic_metadata_order_is_byte_stable():
    content = "# TODO: one\n# FIXME: two"
    first = merge_source_metadata({}, extract_friction_markers(content))
    second = merge_source_metadata({}, extract_friction_markers(content))

    assert first == second
