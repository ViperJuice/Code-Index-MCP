from __future__ import annotations

import logging

import pytest

from mcp_server.plugins.plugin_factory import (
    PluginFactory,
    PluginUnavailableError,
)

P24_FIELDS = {
    "language",
    "state",
    "sandbox_supported",
    "specific_plugin",
    "plugin_module",
    "availability_basis",
    "activation_mode",
    "required_extras",
    "remediation",
    "error_type",
}


def test_availability_has_one_stable_row_per_supported_language():
    rows = PluginFactory.get_plugin_availability(sandbox_enabled=True)
    languages = PluginFactory.get_supported_languages()

    assert [row["language"] for row in rows] == languages
    assert all(set(row) == P24_FIELDS for row in rows)
    assert {row["state"] for row in rows} <= {
        "enabled",
        "unsupported",
        "missing_extra",
        "disabled",
        "load_error",
    }


@pytest.mark.parametrize("language", ["ruby", "json"])
def test_registry_only_sandbox_languages_are_unsupported(language):
    row = PluginFactory.get_plugin_availability(language, sandbox_enabled=True)

    assert row["state"] == "unsupported"
    assert row["sandbox_supported"] is False
    assert row["error_type"] == "SandboxUnsupported"

    with pytest.raises(PluginUnavailableError) as exc_info:
        PluginFactory.create_plugin(language)
    assert exc_info.value.state == "unsupported"


def test_missing_optional_dependency_is_machine_readable(monkeypatch):
    import mcp_server.plugins.plugin_factory as plugin_factory

    def fake_find_spec(name: str):
        if name == "javalang":
            return None
        return object()

    monkeypatch.setattr(plugin_factory.importlib.util, "find_spec", fake_find_spec)

    row = PluginFactory.get_plugin_availability("java", sandbox_enabled=True)

    assert row["state"] == "missing_extra"
    assert row["availability_basis"] == "specific_plugin"
    assert row["activation_mode"] == "extra_required"
    assert row["required_extras"] == ["javalang"]
    assert row["error_type"] == "MissingOptionalDependency"
    assert "uv sync --locked --extra java" in row["remediation"]


def test_availability_rows_expose_default_activation_and_basis_facts():
    python_row = PluginFactory.get_plugin_availability("python", sandbox_enabled=True)
    ruby_row = PluginFactory.get_plugin_availability("ruby", sandbox_enabled=True)

    assert python_row["availability_basis"] == "specific_plugin"
    assert python_row["activation_mode"] == "default"
    assert ruby_row["availability_basis"] == "registry_only"
    assert ruby_row["activation_mode"] == "disabled_by_default"


def test_create_all_plugins_quietly_skips_expected_unavailable(caplog):
    caplog.set_level(logging.ERROR)

    plugins = PluginFactory.create_all_plugins()

    assert "ruby" not in plugins
    assert not [
        record for record in caplog.records if "Failed to create plugin" in record.getMessage()
    ]
