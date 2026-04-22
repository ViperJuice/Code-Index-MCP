"""Tests for SL-3 retention janitor: delete_releases_older_than + CLI prune."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, call, patch

import pytest

from mcp_server.artifacts.providers.github_actions import (
    ReleaseRef,
    delete_releases_older_than,
)
from mcp_server.core.errors import TerminalArtifactError, TransientArtifactError


def _make_release(tag: str, days_ago: int, is_latest: bool = False, is_draft: bool = False) -> dict:
    dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return {
        "tagName": tag,
        "createdAt": dt.isoformat(),
        "isLatest": is_latest,
        "isDraft": is_draft,
    }


def _gh_list_output(releases: list[dict]) -> str:
    return json.dumps(releases)


class TestDeleteReleasesOlderThan:
    """Tests for delete_releases_older_than respecting age + count filters."""

    def _patch_run(self, list_output: str, delete_returncode: int = 0):
        def side_effect(cmd, **kwargs):
            result = MagicMock()
            if "list" in cmd:
                result.returncode = 0
                result.stdout = list_output
                result.stderr = ""
            elif "delete" in cmd:
                result.returncode = delete_returncode
                result.stdout = ""
                result.stderr = "" if delete_returncode == 0 else "HTTP 403: Forbidden"
            else:
                result.returncode = 0
                result.stdout = ""
                result.stderr = ""
            return result

        return patch("subprocess.run", side_effect=side_effect)

    def test_age_filter_deletes_old_releases(self):
        releases = [
            _make_release("v1.0.0", days_ago=60),
            _make_release("v2.0.0", days_ago=10),
        ]
        with self._patch_run(_gh_list_output(releases)):
            deleted = delete_releases_older_than("owner/repo", older_than_days=30)
        assert len(deleted) == 1
        assert deleted[0].tag_name == "v1.0.0"

    def test_keep_latest_n_filter(self):
        releases = [
            _make_release("v1.0.0", days_ago=100),
            _make_release("v2.0.0", days_ago=80),
            _make_release("v3.0.0", days_ago=60),
            _make_release("v4.0.0", days_ago=40),
            _make_release("v5.0.0", days_ago=20),
        ]
        with self._patch_run(_gh_list_output(releases)):
            deleted = delete_releases_older_than("owner/repo", keep_latest_n=3)
        assert len(deleted) == 2
        deleted_tags = {r.tag_name for r in deleted}
        assert "v1.0.0" in deleted_tags
        assert "v2.0.0" in deleted_tags

    def test_combined_age_and_keep_latest(self):
        releases = [
            _make_release("v1.0.0", days_ago=100),
            _make_release("v2.0.0", days_ago=60),
            _make_release("v3.0.0", days_ago=10),
        ]
        with self._patch_run(_gh_list_output(releases)):
            deleted = delete_releases_older_than("owner/repo", older_than_days=30, keep_latest_n=2)
        # v3.0.0 is within 30 days, protected
        # v2.0.0 and v3.0.0 are newest 2, so v2.0.0 is kept by keep_latest_n
        # Only v1.0.0 is old AND not in the newest 2
        assert len(deleted) == 1
        assert deleted[0].tag_name == "v1.0.0"

    def test_protects_is_latest_release(self):
        releases = [
            _make_release("v1.0.0", days_ago=100, is_latest=True),
            _make_release("v2.0.0", days_ago=60),
        ]
        with self._patch_run(_gh_list_output(releases)):
            deleted = delete_releases_older_than("owner/repo", older_than_days=30)
        assert all(r.tag_name != "v1.0.0" for r in deleted)

    def test_protects_index_latest_pointer(self):
        releases = [
            _make_release("index-latest", days_ago=100),
            _make_release("v2.0.0", days_ago=60),
        ]
        with self._patch_run(_gh_list_output(releases)):
            deleted = delete_releases_older_than("owner/repo", older_than_days=30)
        assert all(r.tag_name != "index-latest" for r in deleted)

    def test_dry_run_returns_candidates_without_mutation(self):
        releases = [
            _make_release("v1.0.0", days_ago=60),
            _make_release("v2.0.0", days_ago=10),
        ]
        run_calls = []

        def side_effect(cmd, **kwargs):
            run_calls.append(cmd)
            result = MagicMock()
            result.returncode = 0
            result.stdout = _gh_list_output(releases)
            result.stderr = ""
            return result

        with patch("subprocess.run", side_effect=side_effect):
            candidates = delete_releases_older_than("owner/repo", older_than_days=30, dry_run=True)

        assert len(candidates) == 1
        assert candidates[0].tag_name == "v1.0.0"
        # No delete call should have been made
        for c in run_calls:
            assert "delete" not in c

    def test_no_params_returns_empty(self):
        releases = [
            _make_release("v1.0.0", days_ago=60),
        ]
        with self._patch_run(_gh_list_output(releases)):
            deleted = delete_releases_older_than("owner/repo")
        assert deleted == []

    def test_403_raises_terminal_error(self):
        releases = [_make_release("v1.0.0", days_ago=60)]

        def side_effect(cmd, **kwargs):
            result = MagicMock()
            if "list" in cmd:
                result.returncode = 0
                result.stdout = _gh_list_output(releases)
                result.stderr = ""
            elif "delete" in cmd:
                result.returncode = 1
                result.stdout = ""
                result.stderr = "HTTP 403: Forbidden"
            return result

        with patch("subprocess.run", side_effect=side_effect):
            with pytest.raises(TerminalArtifactError):
                delete_releases_older_than("owner/repo", older_than_days=30)

    def test_429_raises_transient_error(self):
        releases = [_make_release("v1.0.0", days_ago=60)]

        def side_effect(cmd, **kwargs):
            result = MagicMock()
            if "list" in cmd:
                result.returncode = 0
                result.stdout = _gh_list_output(releases)
                result.stderr = ""
            elif "delete" in cmd:
                result.returncode = 1
                result.stdout = ""
                result.stderr = "HTTP 429: rate limit exceeded"
            return result

        with patch("subprocess.run", side_effect=side_effect):
            with pytest.raises(TransientArtifactError):
                delete_releases_older_than("owner/repo", older_than_days=30)

    def test_returns_release_refs(self):
        releases = [_make_release("v1.0.0", days_ago=60)]
        with self._patch_run(_gh_list_output(releases)):
            deleted = delete_releases_older_than("owner/repo", older_than_days=30)
        assert len(deleted) == 1
        ref = deleted[0]
        assert isinstance(ref, ReleaseRef)
        assert ref.tag_name == "v1.0.0"
        assert ref.is_latest is False
        assert ref.is_draft is False


class TestRetentionCLI:
    """CLI dry-run smoke tests."""

    def test_cli_dry_run_exits_zero(self):
        from click.testing import CliRunner

        from mcp_server.cli.retention_commands import retention

        releases = [_make_release("v1.0.0", days_ago=60)]

        def side_effect(cmd, **kwargs):
            result = MagicMock()
            result.returncode = 0
            result.stdout = _gh_list_output(releases)
            result.stderr = ""
            return result

        runner = CliRunner()
        with patch("subprocess.run", side_effect=side_effect):
            result = runner.invoke(
                retention,
                ["prune", "--repo", "owner/repo", "--dry-run", "--older-than-days", "30"],
            )
        assert result.exit_code == 0

    def test_cli_help_exits_zero(self):
        from click.testing import CliRunner

        from mcp_server.cli.retention_commands import retention

        runner = CliRunner()
        result = runner.invoke(retention, ["prune", "--help"])
        assert result.exit_code == 0
        assert "--dry-run" in result.output
        assert "--repo" in result.output
