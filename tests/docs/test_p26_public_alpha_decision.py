"""P26 public-alpha decision documentation checks."""

from __future__ import annotations

import json
import re
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
DECISION_MD = REPO / "docs" / "validation" / "private-alpha-decision.md"
DECISION_JSON = REPO / "docs" / "validation" / "private-alpha-decision.json"
CLASSIFICATIONS = {
    "public_alpha_blocker",
    "documented_limitation",
    "post_alpha_backlog",
}
DECISIONS = {"go", "no_go", "conditional_go"}
FIXTURE_CATEGORIES = {
    "python_repo",
    "typescript_js_repo",
    "mixed_docs_code_repo",
    "multi_repo_workspace",
    "large_ignored_vendor_repo",
}


def _read(relative_path: str) -> str:
    return (REPO / relative_path).read_text(encoding="utf-8")


def _decision_json() -> dict:
    return json.loads(DECISION_JSON.read_text(encoding="utf-8"))


def test_decision_record_classifies_known_issues_and_records_one_decision():
    md = DECISION_MD.read_text(encoding="utf-8")
    evidence = _decision_json()

    for classification in CLASSIFICATIONS:
        assert classification in md

    assert evidence["final_decision"] in DECISIONS
    assert len(re.findall(r"^Final decision:", md, flags=re.MULTILINE)) == 1
    assert sum(f"Final decision: `{decision}`" in md for decision in DECISIONS) == 1

    for issue in evidence["known_issues"]:
        assert issue["classification"] in CLASSIFICATIONS


def test_decision_record_names_required_fixture_categories_and_measurements():
    md = DECISION_MD.read_text(encoding="utf-8")
    evidence = _decision_json()

    assert {fixture["category"] for fixture in evidence["fixtures"]} == FIXTURE_CATEGORIES
    for category in FIXTURE_CATEGORIES:
        assert category in md

    for required in (
        "install time",
        "first index time",
        "p50",
        "p95",
        "result quality",
        "log noise",
        "branch/default-branch behavior",
        "rollback/rebuild behavior",
        "blocker classification",
    ):
        assert required in md.lower()


def test_runbooks_document_private_alpha_go_no_go_procedure():
    surfaces = "\n".join(
        [
            _read("docs/operations/deployment-runbook.md"),
            _read("docs/operations/user-action-runbook.md"),
        ]
    )

    for required in (
        "scripts/private_alpha_evidence.py",
        "private-alpha-evidence/",
        "docs/validation/private-alpha-decision.md",
        "public_alpha_blocker",
        "documented_limitation",
        "post_alpha_backlog",
        "go/no-go",
    ):
        assert required in surfaces

    for category in FIXTURE_CATEGORIES:
        assert category in surfaces


def test_public_alpha_release_surfaces_include_required_truth_fields():
    surfaces = {
        "README.md": _read("README.md"),
        "CHANGELOG.md": _read("CHANGELOG.md"),
    }

    for relative_path, text in surfaces.items():
        lower = text.lower()
        assert "docs/validation/private-alpha-decision.md" in text
        assert "docs/SUPPORT_MATRIX.md" in text
        assert "public alpha" in lower
        assert "beta" in lower
        assert "rollback" in lower
        assert "release-smoke" in lower or "docker" in lower
        assert "uv sync --locked" in text or "ghcr.io/viperjuice/code-index-mcp" in text
