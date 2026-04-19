"""Tests for ref-poller edge cases: detached HEAD, force-push, branch-rename."""

import subprocess
import threading
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from mcp_server.watcher.ref_poller import RefPoller


def _make_registry(repos):
    registry = MagicMock()
    registry.list_all.return_value = repos
    return registry


def _make_repo(repo_id="repo1", path="/tmp/fake_repo", tracked_branch="main", last_indexed_commit="abc123"):
    return SimpleNamespace(
        repository_id=repo_id,
        path=path,
        tracked_branch=tracked_branch,
        last_indexed_commit=last_indexed_commit,
    )


def _make_poller(repos, git_index_manager=None):
    registry = _make_registry(repos)
    if git_index_manager is None:
        git_index_manager = MagicMock()
    poller = RefPoller(
        registry=registry,
        git_index_manager=git_index_manager,
        dispatcher=MagicMock(),
        repo_resolver=MagicMock(),
        interval_seconds=60,
    )
    return poller, git_index_manager


class TestDetachedHead:
    def test_detached_head_fires_enqueue_full_rescan(self):
        """When _read_ref returns None (detached HEAD), enqueue_full_rescan should fire."""
        repo = _make_repo()
        poller, gim = _make_poller([repo])

        # Record prior attached state, then simulate detached
        poller._last_branch_state["repo1"] = "attached"

        with patch.object(poller, "_read_ref", return_value=None):
            poller._poll_one(repo)

        gim.enqueue_full_rescan.assert_called_once_with("repo1")
        gim.sync_repository_index.assert_not_called()

    def test_detached_head_no_rescan_if_was_already_detached(self):
        """Repeated detached state should not fire enqueue_full_rescan again."""
        repo = _make_repo()
        poller, gim = _make_poller([repo])

        poller._last_branch_state["repo1"] = "detached"

        with patch.object(poller, "_read_ref", return_value=None):
            poller._poll_one(repo)

        gim.enqueue_full_rescan.assert_not_called()

    def test_first_poll_with_detached_head_fires_rescan(self):
        """No prior state + detached HEAD → fires enqueue_full_rescan (treat unknown as attached)."""
        repo = _make_repo()
        poller, gim = _make_poller([repo])
        # No entry in _last_branch_state

        with patch.object(poller, "_read_ref", return_value=None):
            poller._poll_one(repo)

        gim.enqueue_full_rescan.assert_called_once_with("repo1")


class TestForcePush:
    def test_force_push_fires_enqueue_full_rescan(self):
        """Non-ancestor tip SHA triggers enqueue_full_rescan instead of sync."""
        repo = _make_repo(last_indexed_commit="old_sha")
        poller, gim = _make_poller([repo])

        new_tip = "new_sha"

        def fake_run(cmd, **kwargs):
            result = MagicMock()
            result.returncode = 1  # not an ancestor
            return result

        with patch.object(poller, "_read_ref", return_value=new_tip), \
             patch("subprocess.run", side_effect=fake_run):
            poller._poll_one(repo)

        gim.enqueue_full_rescan.assert_called_once_with("repo1")
        gim.sync_repository_index.assert_not_called()

    def test_normal_advance_calls_sync(self):
        """Ancestor relationship (normal fast-forward) calls sync_repository_index."""
        repo = _make_repo(last_indexed_commit="old_sha")
        poller, gim = _make_poller([repo])

        new_tip = "new_sha"

        def fake_run(cmd, **kwargs):
            result = MagicMock()
            result.returncode = 0  # is an ancestor (normal advance)
            return result

        with patch.object(poller, "_read_ref", return_value=new_tip), \
             patch("subprocess.run", side_effect=fake_run):
            poller._poll_one(repo)

        gim.sync_repository_index.assert_called_once_with("repo1")
        gim.enqueue_full_rescan.assert_not_called()

    def test_no_action_when_tip_unchanged(self):
        """Same SHA as last_indexed_commit → no calls."""
        repo = _make_repo(last_indexed_commit="abc123")
        poller, gim = _make_poller([repo])

        with patch.object(poller, "_read_ref", return_value="abc123"), \
             patch("subprocess.run") as mock_run:
            poller._poll_one(repo)

        gim.sync_repository_index.assert_not_called()
        gim.enqueue_full_rescan.assert_not_called()
        mock_run.assert_not_called()


class TestBranchRename:
    def test_branch_renamed_fires_enqueue_full_rescan(self):
        """When tracked branch ref disappears, enqueue_full_rescan fires."""
        repo = _make_repo(tracked_branch="main", last_indexed_commit="abc123")
        poller, gim = _make_poller([repo])
        poller._last_branch_state["repo1"] = "attached"

        # main ref returns None (branch disappeared), fallbacks also None
        with patch.object(poller, "_read_ref", return_value=None):
            poller._poll_one(repo)

        gim.enqueue_full_rescan.assert_called_once_with("repo1")
