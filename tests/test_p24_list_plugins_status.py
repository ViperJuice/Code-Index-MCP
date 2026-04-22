from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from mcp_server.cli.tool_handlers import handle_get_status, handle_list_plugins


def _json_text(result):
    return json.loads(result[0].text)


@pytest.mark.asyncio
async def test_list_plugins_includes_availability_rows(repo_resolver):
    dispatcher = MagicMock()
    dispatcher.supported_languages.return_value = ["python", "ruby"]
    dispatcher._by_lang = {}

    payload = _json_text(
        await handle_list_plugins(
            arguments={},
            dispatcher=dispatcher,
            repo_resolver=repo_resolver,
        )
    )

    rows = payload["plugin_availability"]
    assert rows
    assert payload["availability_counts"]
    assert {"python", "ruby"} <= {row["language"] for row in rows}
    assert all(
        set(row)
        == {
            "language",
            "state",
            "sandbox_supported",
            "specific_plugin",
            "plugin_module",
            "required_extras",
            "remediation",
            "error_type",
        }
        for row in rows
    )
    assert any(row["language"] == "ruby" and row["state"] == "unsupported" for row in rows)


@pytest.mark.asyncio
async def test_get_status_summarizes_availability_counts(repo_resolver):
    dispatcher = MagicMock()
    dispatcher.get_statistics.return_value = {
        "total_plugins": 0,
        "loaded_languages": [],
        "supported_languages": 0,
        "operations": {},
        "by_language": {},
    }
    dispatcher.health_check.return_value = {"status": "operational"}

    payload = _json_text(
        await handle_get_status(
            arguments={},
            dispatcher=dispatcher,
            repo_resolver=repo_resolver,
        )
    )

    assert payload["plugins"]["availability_counts"]
    assert sum(payload["plugins"]["availability_counts"].values()) > 0
