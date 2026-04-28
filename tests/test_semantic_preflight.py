"""Tests for semantic preflight readiness checks."""

from types import SimpleNamespace
from unittest.mock import patch

from mcp_server.config.settings import Settings
from mcp_server.setup.semantic_preflight import (
    ServiceStatus,
    check_openai_compatible,
    check_qdrant,
    run_semantic_preflight,
)


def _ready_check(name: str) -> SimpleNamespace:
    return SimpleNamespace(
        ok=True,
        name=name,
        message="ok",
        status=ServiceStatus.READY,
        details={},
        fixes=[],
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


def test_run_semantic_preflight_prefers_profile_embedding_endpoint_over_global_fallback():
    settings = Settings(
        semantic_search_enabled=True,
        openai_api_base="http://global-fallback:9000/v1",
        semantic_profiles_json="""
        {
          "oss_high": {
            "provider": "openai_compatible",
            "model_name": "Qwen/Qwen3-Embedding-8B",
            "build_metadata": {
              "embedding_api_base": "http://profile-embed:8001/v1",
              "embedding_model_name": "Qwen/Qwen3-Embedding-8B",
              "embedding_api_key_env": "EMBEDDING_KEY",
              "enrichment_api_base": "http://profile-enrich:8002/v1",
              "enrichment_model_name": "chat",
              "enrichment_api_key_env": "ENRICHMENT_KEY"
            }
          }
        }
        """,
        semantic_default_profile="oss_high",
    )

    with (
        patch("mcp_server.setup.semantic_preflight.check_profile_registry") as check_profiles,
        patch("mcp_server.setup.semantic_preflight.check_openai_compatible") as check_embedding,
        patch("mcp_server.setup.semantic_preflight.check_qdrant") as check_qdrant_probe,
    ):
        check_profiles.return_value = _ready_check("semantic_profiles")
        check_embedding.return_value = _ready_check("embedding_openai_compatible")
        check_qdrant_probe.return_value = _ready_check("qdrant")

        report = run_semantic_preflight(settings=settings, strict=False)

    check_embedding.assert_called_once_with("http://profile-embed:8001/v1", timeout_s=10.0)
    assert report.effective_config["embedding"]["base_url"] == "http://profile-embed:8001/v1"
    assert report.effective_config["enrichment"]["base_url"] == "http://profile-enrich:8002/v1"


def test_run_semantic_preflight_reports_redacted_config_only(monkeypatch):
    monkeypatch.setenv("EMBEDDING_KEY", "embed-secret")
    monkeypatch.setenv("ENRICHMENT_KEY", "enrich-secret")
    settings = Settings(
        semantic_search_enabled=True,
        semantic_profiles_json="""
        {
          "oss_high": {
            "provider": "openai_compatible",
            "model_name": "Qwen/Qwen3-Embedding-8B",
            "build_metadata": {
              "embedding_api_base": "http://profile-embed:8001/v1",
              "embedding_model_name": "Qwen/Qwen3-Embedding-8B",
              "embedding_api_key_env": "EMBEDDING_KEY",
              "enrichment_api_base": "http://profile-enrich:8002/v1",
              "enrichment_model_name": "chat",
              "enrichment_api_key_env": "ENRICHMENT_KEY"
            }
          }
        }
        """,
        semantic_default_profile="oss_high",
    )

    with (
        patch("mcp_server.setup.semantic_preflight.check_profile_registry") as check_profiles,
        patch("mcp_server.setup.semantic_preflight.check_openai_compatible") as check_embedding,
        patch("mcp_server.setup.semantic_preflight.check_qdrant") as check_qdrant_probe,
    ):
        check_profiles.return_value = _ready_check("semantic_profiles")
        check_embedding.return_value = _ready_check("embedding_openai_compatible")
        check_qdrant_probe.return_value = _ready_check("qdrant")

        report = run_semantic_preflight(settings=settings, strict=False)

    assert report.effective_config["embedding"]["api_key_env"] == "EMBEDDING_KEY"
    assert report.effective_config["embedding"]["api_key_present"] is True
    assert report.effective_config["enrichment"]["api_key_env"] == "ENRICHMENT_KEY"
    assert report.effective_config["enrichment"]["api_key_present"] is True
    payload = str(report.to_dict())
    assert "embed-secret" not in payload
    assert "enrich-secret" not in payload
