"""Tests for setup CLI commands."""

from types import SimpleNamespace

from click.testing import CliRunner

from mcp_server.cli.setup_commands import setup


class _FakeReport:
    def __init__(self, overall_ready: bool = True):
        self.overall_ready = overall_ready
        self.strict_mode = False
        self.profiles = SimpleNamespace(status=SimpleNamespace(value="ready"), message="ok")
        self.embedding = SimpleNamespace(status=SimpleNamespace(value="ready"), message="ok")
        self.qdrant = SimpleNamespace(
            status=SimpleNamespace(value="ready"), message="ok", ok=overall_ready
        )
        self.warnings = [] if overall_ready else ["not ready"]
        self.effective_config = {"selected_profile": "legacy-default"}

    def to_dict(self):
        return {
            "overall_ready": self.overall_ready,
            "strict_mode": self.strict_mode,
            "qdrant": {"status": "ready" if self.overall_ready else "unreachable"},
            "embedding": {"status": "ready"},
            "profiles": {"status": "ready"},
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


def test_setup_semantic_strict_failure(monkeypatch):
    runner = CliRunner()

    monkeypatch.setattr(
        "mcp_server.cli.setup_commands.run_semantic_preflight",
        lambda **kwargs: _FakeReport(overall_ready=False),
    )

    result = runner.invoke(setup, ["semantic", "--strict", "--dry-run"])
    assert result.exit_code != 0
    assert "Strict semantic setup failed" in result.output
