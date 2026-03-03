"""Tests for Docker-based Qdrant autostart."""

from pathlib import Path

from mcp_server.config.settings import Settings
from mcp_server.setup.qdrant_autostart import ensure_qdrant_running


def test_ensure_qdrant_running_reports_missing_docker(monkeypatch, tmp_path: Path):
    settings = Settings(
        qdrant_host="127.0.0.1",
        qdrant_port=65530,
        qdrant_compose_file=str(tmp_path / "docker-compose.qdrant.yml"),
        semantic_preflight_timeout_seconds=1,
    )
    (tmp_path / "docker-compose.qdrant.yml").write_text(
        "services: {}", encoding="utf-8"
    )

    monkeypatch.setattr(
        "mcp_server.setup.qdrant_autostart.is_docker_available", lambda: False
    )

    result = ensure_qdrant_running(settings)
    assert result.started is False
    assert "Docker is not available" in result.message


def test_ensure_qdrant_running_reports_missing_compose_file(monkeypatch):
    settings = Settings(
        qdrant_host="127.0.0.1",
        qdrant_port=65530,
        qdrant_compose_file="/nonexistent/compose.yml",
        semantic_preflight_timeout_seconds=1,
    )

    monkeypatch.setattr(
        "mcp_server.setup.qdrant_autostart.is_docker_available", lambda: True
    )

    result = ensure_qdrant_running(settings)
    assert result.started is False
    assert "compose file not found" in result.message
