"""P20 release-readiness gate."""
import re
from pathlib import Path
import importlib

REPO_ROOT = Path(__file__).parent.parent  # adjust if needed

def test_version_is_rc2():
    mcp = importlib.import_module("mcp_server")
    importlib.reload(mcp)
    assert mcp.__version__ == "1.2.0-rc2"

def test_changelog_has_rc2_section():
    text = (REPO_ROOT / "CHANGELOG.md").read_text()
    assert re.search(r"^## \[1\.2\.0-rc2\] — \d{4}-\d{2}-\d{2}", text, re.M)
    # Must mention all four P20 lanes:
    for label in ("P20 SL-0", "P20 SL-1", "P20 SL-2", "P20 SL-3"):
        assert label in text, f"CHANGELOG missing {label}"

def test_p20_artifacts_exist():
    for path in (
        "tests/integration/multi_repo/conftest.py",
        "tests/integration/obs/test_obs_smoke.py",
        "docs/operations/deployment-runbook.md",
        "tests/test_deployment_runbook_shape.py",
    ):
        assert (REPO_ROOT / path).exists(), f"missing: {path}"
