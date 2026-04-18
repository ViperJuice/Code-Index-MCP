"""P7 / SL-1 — Doc Truth alignment checks.

Tests verify that AGENTS.md and specs/active/architecture.md match the
post-P7 reality: STDIO primary, FastAPI secondary admin surface, beta status
admonition, and MultiRepositoryWatcher present in the L3 diagram.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
AGENTS_MD = REPO_ROOT / "AGENTS.md"
ARCH_MD = REPO_ROOT / "specs" / "active" / "architecture.md"


def _agents_text() -> str:
    return AGENTS_MD.read_text(encoding="utf-8")


def _arch_text() -> str:
    return ARCH_MD.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Stale-claim greps — must return zero matches
# ---------------------------------------------------------------------------

def test_no_fully_operational():
    """'Fully operational' (any capitalisation) must not appear in AGENTS.md."""
    text = _agents_text()
    matches = re.findall(r"fully operational", text, re.IGNORECASE)
    assert matches == [], f"Found stale claim(s): {matches}"


def test_no_production_ready():
    """'Production-ready' must not appear in AGENTS.md."""
    text = _agents_text()
    matches = re.findall(r"production-ready", text, re.IGNORECASE)
    assert matches == [], f"Found stale claim(s): {matches}"


def test_no_100_percent_implemented():
    """'100% implemented' must not appear in AGENTS.md."""
    text = _agents_text()
    matches = re.findall(r"100% implemented", text, re.IGNORECASE)
    assert matches == [], f"Found stale claim(s): {matches}"


# ---------------------------------------------------------------------------
# FastAPI-primary framing greps — must return zero matches
# ---------------------------------------------------------------------------

def test_no_fastapi_primary_framing():
    """'FastAPI gateway with all endpoints' must not appear in AGENTS.md."""
    text = _agents_text()
    matches = re.findall(r"FastAPI gateway with all endpoints", text)
    assert matches == [], f"Found FastAPI-primary framing: {matches}"


def test_no_app_get_symbol_or_search():
    r"""@app.get("/(symbol|search)") must not appear in AGENTS.md."""
    text = _agents_text()
    matches = re.findall(r'@app\.get\("/(symbol|search)"\)', text)
    assert matches == [], f"Found FastAPI-primary code example: {matches}"


# ---------------------------------------------------------------------------
# Positive checks — required content must be present
# ---------------------------------------------------------------------------

def test_stdio_present():
    """STDIO must be mentioned at least once in AGENTS.md."""
    text = _agents_text()
    assert "STDIO" in text, "STDIO not found in AGENTS.md"


def test_repo_context_present():
    """RepoContext must appear in the Multi-Repo section."""
    text = _agents_text()
    assert "RepoContext" in text, "RepoContext not found in AGENTS.md"


def test_store_registry_present():
    """StoreRegistry must appear in the Multi-Repo section."""
    text = _agents_text()
    assert "StoreRegistry" in text, "StoreRegistry not found in AGENTS.md"


def test_mcp_allowed_roots_present():
    """MCP_ALLOWED_ROOTS must appear in the Multi-Repo section."""
    text = _agents_text()
    assert "MCP_ALLOWED_ROOTS" in text, "MCP_ALLOWED_ROOTS not found in AGENTS.md"


def test_beta_admonition_present():
    """Exactly one beta status admonition must be present naming STDIO primary and FastAPI secondary."""
    text = _agents_text()
    # Look for lines that contain "Beta" along with either "STDIO" or "FastAPI" in context
    # The admonition should mention beta status for multi-repo/STDIO context
    beta_lines = [line for line in text.splitlines() if "Beta" in line and ("STDIO" in line or "FastAPI" in line or "beta" in line.lower())]
    # We require at least one such admonition line
    assert len(beta_lines) >= 1, "No beta status admonition found naming STDIO/FastAPI context"
    # The admonition block: find the single > [!NOTE] / > **Beta** style block
    # Count distinct admonition blocks (contiguous lines starting with "> ")
    # Pattern: find blocks that contain "Beta" and "STDIO"
    admonition_blocks = re.findall(
        r"(?:^>.*\n)+",
        text,
        re.MULTILINE,
    )
    beta_stdio_blocks = [b for b in admonition_blocks if "Beta" in b and "STDIO" in b]
    assert len(beta_stdio_blocks) == 1, (
        f"Expected exactly 1 beta+STDIO admonition block, found {len(beta_stdio_blocks)}: {beta_stdio_blocks}"
    )


# ---------------------------------------------------------------------------
# architecture.md L3 checks
# ---------------------------------------------------------------------------

def test_l3_contains_multi_repo_watcher():
    """L3 Component Diagram must contain a MultiRepositoryWatcher component node."""
    text = _arch_text()
    # Find the L3 section (after "Level 3")
    l3_match = re.search(r"Level 3.*?```mermaid(.*?)```", text, re.DOTALL | re.IGNORECASE)
    assert l3_match, "Level 3 mermaid block not found in architecture.md"
    l3_block = l3_match.group(1)
    assert "MultiRepositoryWatcher" in l3_block, (
        "MultiRepositoryWatcher not found in L3 Component Diagram"
    )


def test_l3_multi_repo_watcher_has_rel_edge():
    """MultiRepositoryWatcher must have at least one Rel(...) edge in the L3 diagram."""
    text = _arch_text()
    l3_match = re.search(r"Level 3.*?```mermaid(.*?)```", text, re.DOTALL | re.IGNORECASE)
    assert l3_match, "Level 3 mermaid block not found in architecture.md"
    l3_block = l3_match.group(1)
    # Find Rel(...) lines that involve multi_repo_watcher
    rel_lines = re.findall(
        r"Rel\([^)]*multi_repo_watcher[^)]*\)",
        l3_block,
    )
    assert len(rel_lines) >= 1, (
        f"No Rel(...) edge found for multi_repo_watcher in L3 diagram. Block:\n{l3_block}"
    )
