from mcp_server.indexing.friction import extract_friction_markers


def test_extract_friction_markers_covers_comment_styles_and_references():
    content = "\n".join(
        [
            "# TODO: add retries #123",
            "// FIXME handle cache miss",
            "/* HACK temporary parser bridge */",
            "<!-- WORKAROUND: doc path https://example.com/issue -->",
            "WISH support repo labels",
            "EXTRACTION HINT: index this section",
        ]
    )

    markers = extract_friction_markers(content)

    assert [marker["category"] for marker in markers] == [
        "todo",
        "fixme",
        "hack",
        "workaround",
        "wish",
        "extraction_hint",
    ]
    assert markers[0]["line"] == 1
    assert markers[0]["reference"] == "#123"
    assert markers[3]["reference"] == "https://example.com/issue"
    assert markers[5]["description"] == "index this section"


def test_extract_friction_markers_is_case_insensitive_and_trims_description():
    markers = extract_friction_markers("  // todo   :   keep legacy shape   ")

    assert markers == [
        {
            "source_type": "friction",
            "category": "todo",
            "line": 1,
            "description": "keep legacy shape",
            "pattern": "TODO",
        }
    ]
