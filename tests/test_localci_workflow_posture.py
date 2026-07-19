"""LOCALCI workflow posture checks."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
WORKFLOWS = REPO / ".github" / "workflows"
EXPECTED_CLASSIFICATIONS = {
    "ci-cd-pipeline.yml": "protected-evidence",
    "container-registry.yml": "protected-evidence",
    "index-artifact-management.yml": "manual-only",
    "index-management.yml": "manual-only",
    "lockfile-check.yml": "retired",
    "maintenance.yml": "offloaded",
    "mcp-index.yml": "manual-only",
    "release-automation.yml": "manual-only",
    "sign-published-image.yml": "manual-only",
}


def _read(name: str) -> str:
    return (WORKFLOWS / name).read_text(encoding="utf-8")


def test_every_workflow_has_a_localci_classification() -> None:
    for name, classification in EXPECTED_CLASSIFICATIONS.items():
        first_line = _read(name).splitlines()[0]
        assert first_line == f"# localci-workflow-classification: {classification}"


def test_ci_workflows_use_agent_contract_or_reduced_triggers() -> None:
    ci = _read("ci-cd-pipeline.yml")
    release = _read("release-automation.yml")
    lockfile = _read("lockfile-check.yml")
    index_management = _read("index-management.yml")
    mcp_index = _read("mcp-index.yml")

    assert "make agent-gate" in ci
    assert "make alpha-format-lint" not in ci
    assert "make alpha-unit-release-smoke" not in ci
    assert "make alpha-integration-smoke" not in ci
    assert "make alpha-production-matrix" not in ci
    assert "make agent-gate" in release
    assert "make release-smoke-container" in release
    assert "pull_request:" not in lockfile
    assert "push:" not in lockfile
    assert "pull_request:" not in index_management
    assert "push:" not in index_management
    assert "pull_request:" not in mcp_index
    assert "push:" not in mcp_index


def test_expanded_local_quality_gate_does_not_add_pull_request_compute() -> None:
    pull_request_workflows = {
        name: _read(name) for name in EXPECTED_CLASSIFICATIONS if "pull_request:" in _read(name)
    }

    for text in pull_request_workflows.values():
        assert "alpha-release-gates" not in text
        assert "alpha-mypy-ratchet" not in text

    ci = pull_request_workflows["ci-cd-pipeline.yml"]
    assert ci.count("matrix:") == 1
    matrix_job = ci[ci.index("informational-test-cross-platform:") :]
    assert "if: github.event_name == 'workflow_dispatch'" in matrix_job
