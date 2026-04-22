from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from mcp_server.plugins.plugin_factory import PluginFactory
from mcp_server.plugins.sandboxed_plugin import SandboxedPlugin
from mcp_server.sandbox.capabilities import CapabilitySet
from mcp_server.sandbox.supervisor import SandboxCallError

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def _pythonpath_env():
    orig = os.environ.get("PYTHONPATH")
    parts = [p for p in (orig.split(os.pathsep) if orig else []) if p]
    if str(REPO_ROOT) not in parts:
        parts.insert(0, str(REPO_ROOT))
    os.environ["PYTHONPATH"] = os.pathsep.join(parts)
    try:
        yield
    finally:
        if orig is None:
            os.environ.pop("PYTHONPATH", None)
        else:
            os.environ["PYTHONPATH"] = orig


def _caps() -> CapabilitySet:
    return CapabilitySet(
        fs_read=(REPO_ROOT,),
        fs_write=(),
        env_allow=frozenset({"PATH", "HOME", "PYTHONPATH", "LANG", "LC_ALL"}),
        network=False,
        sqlite="none",
    )


def test_worker_missing_extra_failure_has_capability_state():
    plugin = SandboxedPlugin(
        "tests.security.fixtures.p24_missing_extra_plugin",
        _caps(),
        gh_cmd=sys.executable,
    )
    try:
        with pytest.raises(SandboxCallError) as exc_info:
            _ = plugin.language
    finally:
        plugin.close()

    details = exc_info.value.details
    assert details["state"] == "missing_extra"
    assert details["missing_extra"] == "p24_missing_extra"
    assert details["required_extras"] == ["p24_missing_extra"]
    assert details["remediation"]


@pytest.mark.parametrize("language", ["c_sharp", "csharp"])
def test_csharp_aliases_construct_in_sandbox(language):
    plugin = PluginFactory.create_plugin(language)
    try:
        assert type(plugin).__name__ == "SandboxedPlugin"
        assert plugin.language == "csharp"
    finally:
        plugin.close()


@pytest.mark.parametrize("language", ["rust", "kotlin"])
def test_specific_plugin_alias_exports_construct_in_sandbox(language):
    plugin = PluginFactory.create_plugin(language)
    try:
        assert type(plugin).__name__ == "SandboxedPlugin"
        assert plugin.language == language
    finally:
        plugin.close()
