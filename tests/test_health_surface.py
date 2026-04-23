"""Tests for IF-0-P10-4 and IF-0-P10-7: multi-repo health surface (SL-4)."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from tests.fixtures.health_repo import make_repo_info

EXPECTED_KEYS = {
    "repo_id",
    "tracked_branch",
    "index_path_exists",
    "git_dir_exists",
    "last_indexed_commit",
    "staleness_reason",
    "readiness",
    "ready",
    "readiness_code",
    "remediation",
    "features",
}


# ---------------------------------------------------------------------------
# build_health_row unit tests
# ---------------------------------------------------------------------------


class TestBuildHealthRow:
    def test_returns_expected_keys(self, tmp_path):
        from mcp_server.health.repo_status import build_health_row

        info = make_repo_info(tmp_path)
        row = build_health_row(info)
        assert set(row.keys()) == EXPECTED_KEYS

    def test_healthy_repo(self, tmp_path):
        from mcp_server.health.repo_status import build_health_row

        info = make_repo_info(tmp_path)
        row = build_health_row(info)
        assert row["staleness_reason"] is None
        assert row["readiness"] == "ready"
        assert row["ready"] is True
        assert row["index_path_exists"] is True
        assert row["git_dir_exists"] is True

    def test_missing_git_dir(self, tmp_path):
        from mcp_server.health.repo_status import build_health_row

        info = make_repo_info(tmp_path, missing_git_dir=True)
        row = build_health_row(info)
        assert row["staleness_reason"] == "missing_git_dir"
        assert row["git_dir_exists"] is False

    def test_missing_index(self, tmp_path):
        from mcp_server.health.repo_status import build_health_row

        info = make_repo_info(tmp_path, missing_index=True)
        row = build_health_row(info)
        assert row["staleness_reason"] == "missing_index"
        assert row["readiness"] == "missing_index"
        assert row["index_path_exists"] is False

    def test_empty_index(self, tmp_path):
        from mcp_server.health.repo_status import build_health_row

        info = make_repo_info(tmp_path, empty_index=True)
        row = build_health_row(info)
        assert row["staleness_reason"] == "index_empty"
        assert row["readiness"] == "index_empty"

    def test_stale_commit(self, tmp_path):
        from mcp_server.health.repo_status import build_health_row

        info = make_repo_info(tmp_path, current_commit="bbbb", last_indexed_commit="aaaa")
        row = build_health_row(info)
        assert row["staleness_reason"] == "stale_commit"
        assert row["readiness"] == "stale_commit"

    def test_wrong_branch(self, tmp_path):
        from mcp_server.health.repo_status import build_health_row

        info = make_repo_info(tmp_path, tracked_branch="main", current_branch="feature")
        row = build_health_row(info)
        assert row["staleness_reason"] == "wrong_branch"
        assert row["readiness"] == "wrong_branch"

    def test_index_building(self, tmp_path):
        from mcp_server.health.repo_status import build_health_row
        from mcp_server.health.repository_readiness import ReadinessClassifier

        info = make_repo_info(tmp_path)
        readiness = ReadinessClassifier.classify_registered(info, indexing_active=True)
        row = build_health_row(info, readiness=readiness)
        assert row["staleness_reason"] == "index_building"
        assert row["readiness"] == "index_building"

    def test_missing_git_dir_takes_priority_over_missing_index(self, tmp_path):
        from mcp_server.health.repo_status import build_health_row

        info = make_repo_info(tmp_path, missing_git_dir=True, missing_index=True)
        row = build_health_row(info)
        assert row["staleness_reason"] == "missing_git_dir"

    def test_repo_id_matches(self, tmp_path):
        from mcp_server.health.repo_status import build_health_row

        info = make_repo_info(tmp_path, repo_id="my-repo")
        row = build_health_row(info)
        assert row["repo_id"] == "my-repo"

    def test_tracked_branch(self, tmp_path):
        from mcp_server.health.repo_status import build_health_row

        info = make_repo_info(tmp_path, tracked_branch="dev")
        row = build_health_row(info)
        assert row["tracked_branch"] == "dev"

    def test_last_indexed_commit_none(self, tmp_path):
        from mcp_server.health.repo_status import build_health_row

        info = make_repo_info(tmp_path)
        row = build_health_row(info)
        assert row["last_indexed_commit"] is None


# ---------------------------------------------------------------------------
# stdio handle_get_status includes repositories
# ---------------------------------------------------------------------------


class TestStdioHandleGetStatusRepositories:
    def _make_registry_mock(self, tmp_path):
        info = make_repo_info(tmp_path, repo_id="repo-a")
        registry = Mock()
        registry.get_all_repositories.return_value = {"repo-a": info}
        return registry

    def _make_resolver_mock(self, tmp_path):
        registry = self._make_registry_mock(tmp_path)
        resolver = Mock()
        resolver._registry = registry
        return resolver

    def test_repositories_key_present(self, tmp_path):
        from mcp_server.cli.tool_handlers import handle_get_status
        from mcp_server.dispatcher.simple_dispatcher import SimpleDispatcher

        dispatcher = SimpleDispatcher()
        resolver = self._make_resolver_mock(tmp_path)

        result = asyncio.new_event_loop().run_until_complete(
            handle_get_status(
                arguments={},
                dispatcher=dispatcher,
                repo_resolver=resolver,
            )
        )
        data = json.loads(result[0].text)
        assert "repositories" in data

    def test_repositories_entries_match_registry(self, tmp_path):
        from mcp_server.cli.tool_handlers import handle_get_status
        from mcp_server.dispatcher.simple_dispatcher import SimpleDispatcher

        dispatcher = SimpleDispatcher()
        resolver = self._make_resolver_mock(tmp_path)

        result = asyncio.new_event_loop().run_until_complete(
            handle_get_status(
                arguments={},
                dispatcher=dispatcher,
                repo_resolver=resolver,
            )
        )
        data = json.loads(result[0].text)
        repos = data["repositories"]
        assert len(repos) == 1
        assert set(repos[0].keys()) == EXPECTED_KEYS
        assert repos[0]["repo_id"] == "repo-a"

    def test_repositories_empty_when_no_registry(self, tmp_path):
        from mcp_server.cli.tool_handlers import handle_get_status
        from mcp_server.dispatcher.simple_dispatcher import SimpleDispatcher

        dispatcher = SimpleDispatcher()

        result = asyncio.new_event_loop().run_until_complete(
            handle_get_status(
                arguments={},
                dispatcher=dispatcher,
                repo_resolver=None,
            )
        )
        data = json.loads(result[0].text)
        assert data["repositories"] == []


# ---------------------------------------------------------------------------
# HTTP gateway.get_status includes repositories
# ---------------------------------------------------------------------------


class TestGatewayGetStatusRepositories:
    def _make_gateway_registry(self, tmp_path):
        info = make_repo_info(tmp_path, repo_id="repo-b")
        registry = Mock()
        registry.get_all_repositories.return_value = {"repo-b": info}
        return registry

    def test_gateway_repositories_key_present(self, tmp_path, monkeypatch):
        try:
            from fastapi.testclient import TestClient

            from mcp_server.gateway import app
        except Exception:
            pytest.skip("FastAPI gateway unavailable")

        import mcp_server.gateway as gateway

        registry = self._make_gateway_registry(tmp_path)
        monkeypatch.setattr(gateway, "_repo_registry", registry, raising=False)

        from mcp_server.dispatcher.simple_dispatcher import SimpleDispatcher

        monkeypatch.setattr(gateway, "dispatcher", SimpleDispatcher())
        for attr in (
            "bm25_indexer",
            "hybrid_search",
            "fuzzy_indexer",
            "semantic_indexer",
            "query_cache",
        ):
            if hasattr(gateway, attr):
                monkeypatch.setattr(gateway, attr, None)

        client = TestClient(app, raise_server_exceptions=True)
        response = client.get("/status", headers={"Authorization": "Bearer testtoken"})
        # May be 401 if auth is required; bypass by monkeypatching require_permission
        if response.status_code == 401:
            # Patch auth
            monkeypatch.setattr(
                "mcp_server.gateway.require_permission",
                lambda perm: lambda: None,
                raising=False,
            )
            response = client.get("/status")

        assert response.status_code == 200
        data = response.json()
        assert "repositories" in data

    def test_gateway_repositories_entries_match_registry(self, tmp_path, monkeypatch):
        try:
            from fastapi.testclient import TestClient

            from mcp_server.gateway import app
        except Exception:
            pytest.skip("FastAPI gateway unavailable")

        import mcp_server.gateway as gateway

        registry = self._make_gateway_registry(tmp_path)
        monkeypatch.setattr(gateway, "_repo_registry", registry, raising=False)

        from mcp_server.dispatcher.simple_dispatcher import SimpleDispatcher

        monkeypatch.setattr(gateway, "dispatcher", SimpleDispatcher())
        for attr in (
            "bm25_indexer",
            "hybrid_search",
            "fuzzy_indexer",
            "semantic_indexer",
            "query_cache",
        ):
            if hasattr(gateway, attr):
                monkeypatch.setattr(gateway, attr, None)

        client = TestClient(app, raise_server_exceptions=True)
        response = client.get("/status", headers={"Authorization": "Bearer testtoken"})
        if response.status_code == 401:
            monkeypatch.setattr(
                "mcp_server.gateway.require_permission",
                lambda perm: lambda: None,
                raising=False,
            )
            response = client.get("/status")

        assert response.status_code == 200
        data = response.json()
        repos = data["repositories"]
        assert isinstance(repos, list)
        assert len(repos) == 1
        assert set(repos[0].keys()) == EXPECTED_KEYS
        assert repos[0]["repo_id"] == "repo-b"
