from mcp_server.indexing.friction import extract_friction_markers


def test_language_comment_syntaxes_produce_expected_categories():
    fixtures = {
        "python": "# TODO: python",
        "javascript": "// FIXME: javascript",
        "typescript": "/* HACK typescript */",
        "shell": "# WORKAROUND: shell",
    }

    observed = {
        name: extract_friction_markers(content)[0]["category"] for name, content in fixtures.items()
    }

    assert observed == {
        "python": "todo",
        "javascript": "fixme",
        "typescript": "hack",
        "shell": "workaround",
    }
