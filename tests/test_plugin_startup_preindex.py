from unittest.mock import patch


def test_python_plugin_skips_preindex_when_env_enabled(monkeypatch):
    from mcp_server.plugins.python_plugin.plugin import Plugin

    monkeypatch.setenv("MCP_SKIP_PLUGIN_PREINDEX", "true")
    with patch.object(Plugin, "_preindex") as mock_preindex:
        Plugin(sqlite_store=None)
    mock_preindex.assert_not_called()


def test_js_plugin_skips_preindex_when_env_enabled(monkeypatch):
    from mcp_server.plugins.js_plugin.plugin import Plugin

    monkeypatch.setenv("MCP_SKIP_PLUGIN_PREINDEX", "true")
    with patch.object(Plugin, "_preindex") as mock_preindex:
        Plugin(sqlite_store=None)
    mock_preindex.assert_not_called()


def test_typescript_plugin_skips_preindex_when_env_enabled(monkeypatch):
    from mcp_server.plugins.typescript_plugin.plugin import Plugin

    monkeypatch.setenv("MCP_SKIP_PLUGIN_PREINDEX", "true")
    with patch.object(Plugin, "_preindex") as mock_preindex:
        Plugin(sqlite_store=None)
    mock_preindex.assert_not_called()
