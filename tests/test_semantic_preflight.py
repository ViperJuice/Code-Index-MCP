"""Tests for semantic preflight readiness checks."""

from mcp_server.config.settings import Settings
from mcp_server.setup.semantic_preflight import (
    ServiceStatus,
    check_openai_compatible,
    check_qdrant,
    run_semantic_preflight,
)


def test_check_qdrant_unreachable_returns_unreachable():
    result = check_qdrant("http://127.0.0.1:65531", timeout_s=0.1)
    assert result.status == ServiceStatus.UNREACHABLE


def test_check_openai_compatible_unreachable_returns_unreachable():
    result = check_openai_compatible("http://127.0.0.1:65532/v1", timeout_s=0.1)
    assert result.status == ServiceStatus.UNREACHABLE


def test_run_semantic_preflight_disabled_returns_disabled_report():
    settings = Settings(semantic_search_enabled=False)
    report = run_semantic_preflight(settings=settings, strict=False)
    assert report.overall_ready is False
    assert report.qdrant.status == ServiceStatus.DISABLED
    assert report.embedding.status == ServiceStatus.DISABLED
