"""Shape test for docs/operations/deployment-runbook.md (IF-0-P20-2)."""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
RUNBOOK = REPO_ROOT / "docs" / "operations" / "deployment-runbook.md"
STAGES = ["dev", "staging", "canary", "full-prod"]
H4_REQUIRED = ["Pass criteria", "Bake window", "Rollback trigger", "Rollback procedure"]


def _load():
    assert RUNBOOK.exists(), f"Runbook not found: {RUNBOOK}"
    return RUNBOOK.read_text()


def test_runbook_exists():
    assert RUNBOOK.exists()


def test_top_level_headings():
    text = _load()
    assert re.search(r"^## Stages$", text, re.MULTILINE), "Missing '## Stages'"


def test_all_stages_present():
    text = _load()
    for stage in STAGES:
        assert re.search(
            rf"^### Stage: {re.escape(stage)}$", text, re.MULTILINE
        ), f"Missing '### Stage: {stage}'"


def _stage_body(text: str, stage: str) -> str:
    """Extract markdown between ### Stage: <stage> and next ### Stage: or ## heading."""
    pattern = rf"^### Stage: {re.escape(stage)}$(.*?)(?=^### Stage:|^## |\Z)"
    m = re.search(pattern, text, re.MULTILINE | re.DOTALL)
    assert m, f"Could not locate stage block for '{stage}'"
    return m.group(1)


def test_each_stage_has_required_h4s():
    text = _load()
    for stage in STAGES:
        body = _stage_body(text, stage)
        for h4 in H4_REQUIRED:
            assert re.search(
                rf"^#### {re.escape(h4)}$", body, re.MULTILINE
            ), f"Stage '{stage}' missing H4 '#### {h4}'"


def test_preflight_script_referenced():
    text = _load()
    assert (
        "scripts/preflight_upgrade.sh" in text
    ), "Runbook must reference scripts/preflight_upgrade.sh"


def test_preflight_script_exists_on_disk():
    script = REPO_ROOT / "scripts" / "preflight_upgrade.sh"
    assert script.exists(), f"scripts/preflight_upgrade.sh not found at {script}"
