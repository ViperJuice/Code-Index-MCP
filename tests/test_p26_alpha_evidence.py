"""P26 private-alpha evidence contract tests."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
REQUIRED_FIXTURE_CATEGORIES = {
    "python_repo",
    "typescript_js_repo",
    "mixed_docs_code_repo",
    "multi_repo_workspace",
    "large_ignored_vendor_repo",
}
REQUIRED_MEASUREMENT_FIELDS = {
    "install_time_seconds",
    "first_index_time_seconds",
    "query_latency_p50_ms",
    "query_latency_p95_ms",
    "result_quality_notes",
    "log_noise_classification",
    "branch_default_branch_behavior",
    "rollback_rebuild_behavior",
    "blocker_classification",
}
ISSUE_CLASSIFICATIONS = {
    "public_alpha_blocker",
    "documented_limitation",
    "post_alpha_backlog",
}
FINAL_DECISIONS = {"go", "no_go", "conditional_go"}


def _read(relative_path: str) -> str:
    return (REPO / relative_path).read_text(encoding="utf-8")


def _json(relative_path: str) -> dict:
    return json.loads(_read(relative_path))


def _git_check_ignored(path: str) -> bool:
    result = subprocess.run(
        ["git", "check-ignore", "--quiet", path],
        cwd=REPO,
        check=False,
    )
    return result.returncode == 0


def test_private_alpha_raw_evidence_boundary_is_ignored_only_for_raw_outputs():
    assert _git_check_ignored("private-alpha-evidence/example/raw-evidence.json")
    assert not _git_check_ignored("docs/validation/private-alpha-decision.md")
    assert not _git_check_ignored("docs/validation/private-alpha-evidence.schema.json")


def test_private_alpha_schema_freezes_fixture_and_measurement_contract():
    schema = _json("docs/validation/private-alpha-evidence.schema.json")
    fixture_schema = schema["properties"]["fixtures"]["items"]
    measurement_schema = fixture_schema["properties"]["measurements"]
    issue_schema = schema["properties"]["known_issues"]["items"]

    assert set(fixture_schema["properties"]["category"]["enum"]) == REQUIRED_FIXTURE_CATEGORIES
    assert set(measurement_schema["required"]) >= REQUIRED_MEASUREMENT_FIELDS
    assert set(issue_schema["properties"]["classification"]["enum"]) == ISSUE_CLASSIFICATIONS
    assert set(schema["properties"]["final_decision"]["enum"]) == FINAL_DECISIONS


def test_redacted_private_alpha_json_matches_contract_and_has_no_raw_fields():
    evidence = _json("docs/validation/private-alpha-decision.json")

    assert {fixture["category"] for fixture in evidence["fixtures"]} == REQUIRED_FIXTURE_CATEGORIES
    assert evidence["final_decision"] in FINAL_DECISIONS

    for fixture in evidence["fixtures"]:
        measurements = fixture["measurements"]
        assert set(measurements) >= REQUIRED_MEASUREMENT_FIELDS
        assert measurements["blocker_classification"] in ISSUE_CLASSIFICATIONS
        assert "repo_path" not in fixture
        assert "raw_log" not in fixture
        assert "source_snippet" not in fixture

    for issue in evidence["known_issues"]:
        assert issue["classification"] in ISSUE_CLASSIFICATIONS


def test_private_alpha_harness_entrypoint_and_cli_contract_exist():
    script = REPO / "scripts" / "private_alpha_evidence.py"
    assert script.exists()
    text = script.read_text(encoding="utf-8")

    for flag in (
        "--config",
        "--output-dir",
        "--redacted-md",
        "--redacted-json",
        "private-alpha-evidence",
        "release_smoke.py",
        "public_alpha_blocker",
    ):
        assert flag in text


def test_private_alpha_harness_uses_permission_tolerant_repo_walk():
    script = REPO / "scripts" / "private_alpha_evidence.py"
    text = script.read_text(encoding="utf-8")

    assert "os.walk" in text
    assert "onerror=" in text


def test_private_alpha_committed_artifacts_are_redacted():
    for relative_path in (
        "docs/validation/private-alpha-decision.md",
        "docs/validation/private-alpha-decision.json",
        "docs/benchmarks/private-alpha-summary.md",
    ):
        text = _read(relative_path)
        assert "/home/" not in text
        assert "/Users/" not in text
        assert "source_snippet" not in text
        assert "raw_log" not in text
        assert "secret" not in text.lower()
        assert "token" not in text.lower()
