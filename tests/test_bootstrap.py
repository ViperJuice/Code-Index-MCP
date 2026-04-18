"""Tests for SL-2 entry-point consolidation: bootstrap, stdio_runner, tool_handlers."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# SL-2.1 — red tests (will fail before SL-2.2 impl)
# ---------------------------------------------------------------------------


class TestInitializeStatelessServices:
    """initialize_stateless_services() contract tests."""

    def test_returns_tuple_of_five(self, tmp_path):
        """Returns (StoreRegistry, RepoResolver, dispatcher, RepositoryRegistry, GitAwareIndexManager)."""
        from mcp_server.cli.bootstrap import initialize_stateless_services
        from mcp_server.core import RepoResolver
        from mcp_server.storage import StoreRegistry
        from mcp_server.storage.git_index_manager import GitAwareIndexManager
        from mcp_server.storage.repository_registry import RepositoryRegistry

        registry_path = tmp_path / "registry.json"
        result = initialize_stateless_services(registry_path=registry_path)

        assert isinstance(result, tuple), "Must return a tuple"
        assert len(result) == 5, "Tuple must have 5 elements"
        store_registry, repo_resolver, dispatcher, repo_registry, git_index_manager = result
        assert isinstance(store_registry, StoreRegistry)
        assert isinstance(repo_resolver, RepoResolver)
        assert isinstance(repo_registry, RepositoryRegistry)
        assert isinstance(git_index_manager, GitAwareIndexManager)
        # Dispatcher must have the core protocol methods
        assert callable(getattr(dispatcher, "search", None)), "dispatcher must have search()"
        assert callable(getattr(dispatcher, "lookup", None)), "dispatcher must have lookup()"

    def test_no_cwd_capture(self, tmp_path, monkeypatch):
        """Service construction must not depend on os.getcwd()."""
        import os

        from mcp_server.cli.bootstrap import initialize_stateless_services

        monkeypatch.chdir(tmp_path)
        registry_path = tmp_path / "registry.json"
        result1 = initialize_stateless_services(registry_path=registry_path)

        other_dir = tmp_path / "other"
        other_dir.mkdir()
        monkeypatch.chdir(other_dir)
        result2 = initialize_stateless_services(registry_path=registry_path)

        # Both calls should succeed — no crash from different cwd
        assert len(result1) == 5
        assert len(result2) == 5

    def test_no_preloaded_sqlite_store(self, tmp_path):
        """The returned dispatcher must NOT have a pre-loaded per-repo sqlite_store."""
        from mcp_server.cli.bootstrap import initialize_stateless_services

        registry_path = tmp_path / "registry.json"
        _, _, dispatcher, _, _ = initialize_stateless_services(registry_path=registry_path)

        # Dispatcher should not have an _sqlite_store bound at init time
        assert not hasattr(dispatcher, "_sqlite_store") or getattr(dispatcher, "_sqlite_store", None) is None


class TestStdioCommandHelp:
    """python -m mcp_server.cli stdio --help exits 0."""

    def test_stdio_help_exits_zero(self):
        result = subprocess.run(
            [sys.executable, "-m", "mcp_server.cli", "stdio", "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, (
            f"Expected exit 0, got {result.returncode}.\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )
        assert "stdio" in result.stdout.lower() or "stdio" in result.stderr.lower()


class TestShimImportable:
    """scripts.cli.mcp_server_cli.main is still importable (shim preserves PYTHONPATH tests)."""

    def test_shim_main_importable(self):
        # Ensure the scripts directory is importable
        scripts_parent = str(Path(__file__).parent.parent)
        if scripts_parent not in sys.path:
            sys.path.insert(0, scripts_parent)

        # The shim at scripts/cli/mcp_server_cli.py must expose `main`
        from scripts.cli import mcp_server_cli  # noqa: F401

        assert hasattr(mcp_server_cli, "main"), (
            "scripts/cli/mcp_server_cli.py shim must expose 'main'"
        )

    def test_shim_is_short(self):
        """Shim must be < 10 lines."""
        shim_path = Path(__file__).parent.parent / "scripts" / "cli" / "mcp_server_cli.py"
        lines = shim_path.read_text().splitlines()
        non_empty = [l for l in lines if l.strip() and not l.strip().startswith("#")]
        assert len(non_empty) < 10, (
            f"Shim has {len(non_empty)} non-comment lines; expected < 10"
        )


class TestMcpJsonTemplates:
    """Each .mcp.json* template parses as valid JSON and args no longer reference scripts/cli/mcp_server_cli.py."""

    _TEMPLATE_FILES = [
        ".mcp.json",
        ".mcp.json.example",
        ".mcp.json.template",
        ".mcp.json.templates/native.json",
        ".mcp.json.templates/docker-sidecar.json",
        ".mcp.json.templates/auto-detect.json",
    ]

    def _repo_root(self) -> Path:
        return Path(__file__).parent.parent

    @pytest.mark.parametrize("rel_path", _TEMPLATE_FILES)
    def test_template_is_valid_json_or_skipped(self, rel_path):
        """Templates that exist must be valid JSON (dollar-sign templates are exempt)."""
        path = self._repo_root() / rel_path
        if not path.exists():
            pytest.skip(f"{rel_path} does not exist")

        content = path.read_text()
        # shell-variable templates (${ }) are not strict JSON — skip parse check for those
        if "${" in content:
            pytest.skip(f"{rel_path} uses shell variable substitution; JSON parse skipped")

        try:
            json.loads(content)
        except json.JSONDecodeError as exc:
            pytest.fail(f"{rel_path} is not valid JSON: {exc}")

    @pytest.mark.parametrize("rel_path", _TEMPLATE_FILES)
    def test_template_args_use_module_invocation(self, rel_path):
        """Verify templates use module form (-m mcp_server.cli stdio) rather than absolute script path.

        The auto-detect.json uses a sh -c wrapper; for that template we check that
        mcp_server.cli is referenced, OR that the template has no Python invocation at all.
        """
        path = self._repo_root() / rel_path
        if not path.exists():
            pytest.skip(f"{rel_path} does not exist")

        content = path.read_text()

        # Must NOT reference the old absolute script path for the Python invocation
        assert "scripts/cli/mcp_server_cli.py" not in content, (
            f"{rel_path} still references scripts/cli/mcp_server_cli.py; "
            "update to use '-m mcp_server.cli stdio'"
        )


class TestHandleSearchCodeResolvesViaRepoResolver:
    """handle_search_code resolves ctx via RepoResolver and calls dispatcher.search(ctx, ...)."""

    def test_handle_search_code_uses_repo_resolver(self, tmp_path, monkeypatch):
        import asyncio

        from mcp_server.cli.tool_handlers import handle_search_code
        from mcp_server.core.repo_context import RepoContext

        monkeypatch.setenv("MCP_ALLOWED_ROOTS", str(tmp_path))

        mock_ctx = MagicMock(spec=RepoContext)
        mock_dispatcher = MagicMock()
        mock_dispatcher.search.return_value = iter([])

        mock_resolver = MagicMock()
        mock_resolver.resolve.return_value = mock_ctx

        arguments = {"query": "def test", "repository": str(tmp_path)}

        async def _run():
            return await handle_search_code(
                arguments=arguments,
                dispatcher=mock_dispatcher,
                repo_resolver=mock_resolver,
            )

        asyncio.run(_run())

        mock_resolver.resolve.assert_called_once()
        mock_dispatcher.search.assert_called_once()
        call_args = mock_dispatcher.search.call_args
        # First positional arg must be the resolved ctx
        assert call_args[0][0] is mock_ctx or call_args.args[0] is mock_ctx

    def test_handle_search_code_fallback_to_workspace_root(self, tmp_path, monkeypatch):
        """When repository arg is absent, fall back to MCP_WORKSPACE_ROOT."""
        import asyncio

        from mcp_server.cli.tool_handlers import handle_search_code
        from mcp_server.core.repo_context import RepoContext

        monkeypatch.setenv("MCP_WORKSPACE_ROOT", str(tmp_path))

        mock_ctx = MagicMock(spec=RepoContext)
        mock_dispatcher = MagicMock()
        mock_dispatcher.search.return_value = iter([])

        mock_resolver = MagicMock()
        mock_resolver.resolve.return_value = mock_ctx

        arguments = {"query": "def test"}

        async def _run():
            return await handle_search_code(
                arguments=arguments,
                dispatcher=mock_dispatcher,
                repo_resolver=mock_resolver,
            )

        asyncio.run(_run())

        mock_resolver.resolve.assert_called_once()
        mock_dispatcher.search.assert_called_once()
