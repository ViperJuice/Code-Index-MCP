"""Tests for semantic index management CLI surfaces."""

from types import SimpleNamespace

from click.testing import CliRunner

from mcp_server.cli.index_management import index


class _FakeReport:
    def __init__(self, *, overall_ready: bool, strict_mode: bool):
        self.overall_ready = overall_ready
        self.strict_mode = strict_mode
        self.can_write_semantic_vectors = overall_ready
        self.profiles = SimpleNamespace(status=SimpleNamespace(value="ready"), message="ok")
        self.enrichment = SimpleNamespace(status=SimpleNamespace(value="ready"), message="ok")
        self.embedding = SimpleNamespace(
            status=SimpleNamespace(value="ready" if overall_ready else "misconfigured"),
            message="ok" if overall_ready else "Embedding dimension mismatch",
        )
        self.qdrant = SimpleNamespace(status=SimpleNamespace(value="ready"), message="ok")
        self.collection = SimpleNamespace(
            status=SimpleNamespace(value="ready" if overall_ready else "misconfigured"),
            message="ok" if overall_ready else "collection mismatch",
        )
        self.blocker = (
            None
            if overall_ready
            else SimpleNamespace(
                code="embedding_dimension_mismatch",
                message="Embedding dimension mismatch",
                remediation=["Repair embedding model selection"],
            )
        )
        self.warnings = [] if overall_ready else ["not ready"]
        self.effective_config = {
            "selected_profile": "oss_high",
            "collection_name": "ci__repo__oss-high__workspace",
        }

    def to_dict(self):
        return {
            "effective_config": self.effective_config,
        }


def test_check_semantic_renders_richer_preflight_state(monkeypatch):
    runner = CliRunner()
    monkeypatch.setattr(
        "mcp_server.cli.index_management.run_semantic_preflight",
        lambda **kwargs: _FakeReport(overall_ready=False, strict_mode=False),
    )

    result = runner.invoke(index, ["check-semantic"])

    assert result.exit_code == 0
    assert "Can write semantic vectors: ❌" in result.output
    assert "Enrichment: ready - ok" in result.output
    assert "Collection: misconfigured - collection mismatch" in result.output
    assert "Semantic write blocker:" in result.output
    assert "embedding_dimension_mismatch" in result.output


def test_check_semantic_fails_predictably_in_strict_mode(monkeypatch):
    runner = CliRunner()
    monkeypatch.setattr(
        "mcp_server.cli.index_management.run_semantic_preflight",
        lambda **kwargs: _FakeReport(overall_ready=False, strict_mode=True),
    )

    result = runner.invoke(index, ["check-semantic"])

    assert result.exit_code != 0
    assert "Strict semantic preflight failed" in result.output
