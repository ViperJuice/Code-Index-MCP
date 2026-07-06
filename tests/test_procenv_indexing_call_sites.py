from __future__ import annotations

import sqlite3
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from mcp_server.cli.index_commands import BaseIndexCommand, CreateIndexCommand, SyncIndexCommand
from mcp_server.health import repository_readiness
from mcp_server.indexing.change_detector import ChangeDetector
from mcp_server.indexing.incremental_indexer import IncrementalIndexer
from mcp_server.watcher_multi_repo import GitMonitor, MultiRepositoryHandler


def test_index_command_repo_hash_uses_helper_env(tmp_path: Path) -> None:
    sentinel_env = {"PATH": "/procenv"}
    command = BaseIndexCommand()

    with patch("mcp_server.cli.index_commands.get_full_env", return_value=sentinel_env):
        with patch("mcp_server.cli.index_commands.subprocess.run") as mock_run:
            mock_run.return_value = Mock(stdout="git@example.com/repo.git\n")
            command._get_repo_hash(tmp_path)

    assert mock_run.call_args.kwargs["env"] == sentinel_env


@pytest.mark.asyncio
async def test_create_index_passes_helper_env_to_spawn(tmp_path: Path) -> None:
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    sentinel_env = {"PATH": "/procenv"}
    command = CreateIndexCommand()

    with patch.object(command, "_get_repo_hash", return_value="abc123"):
        with patch("mcp_server.cli.index_commands.get_full_env", return_value=sentinel_env):
            with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_spawn:
                proc = AsyncMock()
                proc.returncode = 0
                proc.communicate.return_value = (b"", b"")
                mock_spawn.return_value = proc

                index_dir = Path.cwd() / ".indexes" / "abc123"
                index_dir.mkdir(parents=True, exist_ok=True)
                index_path = index_dir / "code_index.db"
                index_path.write_text("placeholder", encoding="utf-8")

                with patch.object(command, "_get_index_stats", return_value={}):
                    await command.execute(repo="repo", path=str(repo_path))

    assert mock_spawn.call_args.kwargs["env"] == sentinel_env


@pytest.mark.asyncio
async def test_sync_index_incremental_uses_helper_env_for_git_and_spawn(tmp_path: Path) -> None:
    sentinel_env = {"PATH": "/procenv"}
    command = SyncIndexCommand()
    index_dir = tmp_path / ".mcp-index"
    index_dir.mkdir()
    conn = sqlite3.connect(index_dir / "code_index.db")
    conn.execute("CREATE TABLE files (id INTEGER PRIMARY KEY)")
    conn.commit()
    conn.close()
    (tmp_path / ".mcp-index.json").write_text('{"enabled": true}', encoding="utf-8")

    with patch("mcp_server.utils.index_discovery.Path.cwd", return_value=tmp_path):
        with patch("mcp_server.cli.index_commands.get_full_env", return_value=sentinel_env):
            with patch("mcp_server.cli.index_commands.subprocess.run") as mock_run:
                mock_run.return_value = Mock(stdout="file1.py\n", returncode=0)
                with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_spawn:
                    proc = AsyncMock()
                    proc.returncode = 0
                    proc.communicate.return_value = (b"1 files updated", b"")
                    mock_spawn.return_value = proc

                    await command.execute(repo="repo", incremental=True)

    assert mock_run.call_args.kwargs["env"] == sentinel_env
    assert mock_spawn.call_args.kwargs["env"] == sentinel_env


def test_change_detector_uses_helper_env_for_git_queries(tmp_path: Path) -> None:
    sentinel_env = {"PATH": "/procenv"}
    detector = ChangeDetector(tmp_path)

    with patch("mcp_server.indexing.change_detector.get_full_env", return_value=sentinel_env):
        with patch("mcp_server.indexing.change_detector.subprocess.run") as mock_run:
            mock_run.return_value = Mock(stdout="", returncode=0)
            detector.get_uncommitted_changes()

    assert mock_run.call_args_list[0].kwargs["env"] == sentinel_env
    assert mock_run.call_args_list[1].kwargs["env"] == sentinel_env
    assert mock_run.call_args_list[2].kwargs["env"] == sentinel_env


def test_incremental_indexer_repo_id_uses_helper_env(tmp_path: Path) -> None:
    sentinel_env = {"PATH": "/procenv"}
    indexer = IncrementalIndexer(store=Mock(), dispatcher=Mock(), repo_path=tmp_path)

    with patch("mcp_server.indexing.incremental_indexer.get_full_env", return_value=sentinel_env):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(stdout="git@example.com/repo.git\n")
            indexer._get_repository_id()

    assert mock_run.call_args.kwargs["env"] == sentinel_env


def test_git_monitor_current_commit_uses_helper_env(tmp_path: Path) -> None:
    sentinel_env = {"PATH": "/procenv"}
    monitor = GitMonitor(registry=Mock(), callback=Mock())

    with patch("mcp_server.watcher_multi_repo.get_full_env", return_value=sentinel_env):
        with patch("mcp_server.watcher_multi_repo.subprocess.run") as mock_run:
            mock_run.return_value = Mock(stdout="abc123\n")
            monitor._get_current_commit(str(tmp_path))

    assert mock_run.call_args.kwargs["env"] == sentinel_env


def test_multi_repository_handler_branch_probe_uses_helper_env(tmp_path: Path) -> None:
    sentinel_env = {"PATH": "/procenv"}
    ctx = SimpleNamespace(tracked_branch="main")
    handler = MultiRepositoryHandler(
        repo_id="repo-1",
        repo_path=tmp_path,
        parent_watcher=Mock(dispatcher=Mock(), query_cache=None, path_resolver=None),
        ctx=ctx,
    )

    with patch("mcp_server.watcher_multi_repo.get_full_env", return_value=sentinel_env):
        with patch("mcp_server.watcher_multi_repo.subprocess.run") as mock_run:
            mock_run.return_value = Mock(stdout="main\n", returncode=0)
            handler._get_current_branch()

    assert mock_run.call_args.kwargs["env"] == sentinel_env


def test_repository_readiness_run_git_uses_helper_env(tmp_path: Path) -> None:
    sentinel_env = {"PATH": "/procenv"}

    with patch("mcp_server.health.repository_readiness.get_full_env", return_value=sentinel_env):
        with patch("mcp_server.health.repository_readiness.subprocess.run") as mock_run:
            mock_run.return_value = Mock(stdout="main\n")
            repository_readiness._run_git(["rev-parse", "--abbrev-ref", "HEAD"], tmp_path)

    assert mock_run.call_args.kwargs["env"] == sentinel_env
