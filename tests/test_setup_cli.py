"""Tests for setup CLI commands."""

from types import SimpleNamespace

from click.testing import CliRunner

from mcp_server.cli.setup_commands import setup


class _FakeReport:
    def __init__(self, overall_ready: bool = True):
        self.overall_ready = overall_ready
        self.can_write_semantic_vectors = overall_ready
        self.strict_mode = False
        self.profiles = SimpleNamespace(status=SimpleNamespace(value="ready"), message="ok")
        self.enrichment = SimpleNamespace(status=SimpleNamespace(value="ready"), message="ok")
        self.embedding = SimpleNamespace(status=SimpleNamespace(value="ready"), message="ok")
        self.qdrant = SimpleNamespace(
            status=SimpleNamespace(value="ready"), message="ok", ok=overall_ready
        )
        self.collection = SimpleNamespace(
            status=SimpleNamespace(value="ready" if overall_ready else "misconfigured"),
            message="ok" if overall_ready else "collection mismatch",
        )
        self.blocker = (
            None
            if overall_ready
            else SimpleNamespace(
                code="collection_missing",
                message="Qdrant collection is missing for the active semantic profile",
                remediation=["Create or hydrate the expected semantic collection before vector writes"],
            )
        )
        self.warnings = [] if overall_ready else ["not ready"]
        self.effective_config = {
            "selected_profile": "oss_high",
            "embedding": {
                "base_url": "http://ai:8001/v1",
                "model": "Qwen/Qwen3-Embedding-8B",
                "api_key_env": "OPENAI_API_KEY",
                "api_key_present": True,
            },
            "enrichment": {
                "base_url": "http://ai:8002/v1",
                "model": "chat",
                "api_key_env": "OPENAI_API_KEY",
                "api_key_present": True,
            },
        }

    def to_dict(self):
        return {
            "overall_ready": self.overall_ready,
            "can_write_semantic_vectors": self.can_write_semantic_vectors,
            "strict_mode": self.strict_mode,
            "qdrant": {"status": "ready" if self.overall_ready else "unreachable"},
            "embedding": {"status": "ready"},
            "profiles": {"status": "ready"},
            "enrichment": {"status": "ready"},
            "collection": {
                "status": "ready" if self.overall_ready else "misconfigured",
                "message": "ok" if self.overall_ready else "collection mismatch",
            },
            "blocker": (
                None
                if self.blocker is None
                else {
                    "code": self.blocker.code,
                    "message": self.blocker.message,
                    "remediation": list(self.blocker.remediation),
                    "can_write_semantic_vectors": False,
                    "failing_checks": [],
                }
            ),
            "warnings": self.warnings,
            "effective_config": self.effective_config,
        }


def test_setup_semantic_help():
    runner = CliRunner()
    result = runner.invoke(setup, ["semantic", "--help"])
    assert result.exit_code == 0
    assert "--autostart-qdrant" in result.output
    assert "--openai-api-base" in result.output


def test_setup_semantic_json_output(monkeypatch):
    runner = CliRunner()

    monkeypatch.setattr(
        "mcp_server.cli.setup_commands.run_semantic_preflight",
        lambda **kwargs: _FakeReport(overall_ready=True),
    )

    result = runner.invoke(setup, ["semantic", "--json", "--dry-run"])
    assert result.exit_code == 0
    assert "overall_ready" in result.output
    assert "can_write_semantic_vectors" in result.output
    assert '"embedding"' in result.output
    assert '"enrichment"' in result.output
    assert '"collection"' in result.output
    assert '"collection_bootstrap"' in result.output


def test_setup_semantic_strict_failure(monkeypatch):
    runner = CliRunner()

    monkeypatch.setattr(
        "mcp_server.cli.setup_commands.run_semantic_preflight",
        lambda **kwargs: _FakeReport(overall_ready=False),
    )

    result = runner.invoke(setup, ["semantic", "--strict", "--dry-run"])
    assert result.exit_code != 0
    assert "Strict semantic setup failed" in result.output


def test_setup_semantic_text_output_names_blocker_and_collection(monkeypatch):
    runner = CliRunner()

    monkeypatch.setattr(
        "mcp_server.cli.setup_commands.run_semantic_preflight",
        lambda **kwargs: _FakeReport(overall_ready=False),
    )

    result = runner.invoke(setup, ["semantic", "--dry-run"])
    assert result.exit_code == 0
    assert "Collection check: misconfigured" in result.output
    assert "Collection bootstrap: dry_run" in result.output
    assert "Semantic write blocker:" in result.output
    assert "collection_missing" in result.output


def test_setup_semantic_bootstraps_missing_collection_when_not_dry_run(monkeypatch):
    runner = CliRunner()
    calls = {"count": 0}

    def _fake_preflight(**kwargs):
        calls["count"] += 1
        return _FakeReport(overall_ready=calls["count"] > 1)

    monkeypatch.setattr("mcp_server.cli.setup_commands.run_semantic_preflight", _fake_preflight)
    monkeypatch.setattr(
        "mcp_server.cli.setup_commands.bootstrap_active_profile_collection",
        lambda **kwargs: SimpleNamespace(
            to_dict=lambda: {
                "status": "created",
                "message": "Created the active semantic collection for the selected profile",
            },
            status="created",
            message="Created the active semantic collection for the selected profile",
        ),
    )

    result = runner.invoke(setup, ["semantic"])

    assert result.exit_code == 0
    assert calls["count"] == 2
    assert "Collection bootstrap: created" in result.output
