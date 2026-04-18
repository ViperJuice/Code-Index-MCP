"""P6B SL-1: Doc alignment tests — verify AGENTS.md and README.md match post-refactor reality."""
import re
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent

AGENTS_MD = REPO_ROOT / "AGENTS.md"
README_MD = REPO_ROOT / "README.md"


def test_no_stale_claims():
    text = AGENTS_MD.read_text()
    stale = [
        "100% production-ready",
        "Phase 1 8/8",
        "NEAR PRODUCTION",
        "100% functional",
        "All Implementation Complete",
    ]
    for phrase in stale:
        assert phrase not in text, f"Stale claim found in AGENTS.md: {phrase!r}"


def test_agents_multi_repo_section():
    text = AGENTS_MD.read_text()
    required_tokens = [
        "RepoContext",
        "StoreRegistry",
        "compute_repo_id",
        "MultiRepositoryWatcher",
        "MCP_ALLOWED_ROOTS",
        "MCP_CLIENT_SECRET",
        "path_outside_allowed_roots",
    ]
    for token in required_tokens:
        assert token in text, f"Required token missing from AGENTS.md: {token!r}"

    headings = [
        line for line in text.splitlines()
        if line.startswith("#")
    ]
    has_multi_repo_heading = any(
        re.search(r"multi.?repo", line, re.IGNORECASE) for line in headings
    )
    assert has_multi_repo_heading, "AGENTS.md missing a heading containing 'multi-repo' or 'multi repo'"


def test_readme_many_repos_section():
    text = README_MD.read_text()
    lines = text.splitlines()

    # Find the heading
    heading_pattern = re.compile(r"^(#{1,6})\s+(.*)", re.IGNORECASE)
    target_line_idx = None
    target_level = None

    for i, line in enumerate(lines):
        m = heading_pattern.match(line)
        if m:
            level = len(m.group(1))
            heading_text = m.group(2)
            if re.search(r"many repos|multi.?repo", heading_text, re.IGNORECASE):
                target_line_idx = i
                target_level = level
                break

    assert target_line_idx is not None, (
        "README.md missing a heading matching 'many repos', 'multi-repo', or 'multi repo'"
    )

    # Collect lines between this heading and the next heading of equal or higher level
    section_lines = []
    for line in lines[target_line_idx + 1:]:
        m = heading_pattern.match(line)
        if m and len(m.group(1)) <= target_level:
            break
        section_lines.append(line)

    section_text = "\n".join(section_lines)
    assert "MCP_ALLOWED_ROOTS" in section_text, (
        "README.md 'many repos' section missing 'MCP_ALLOWED_ROOTS'"
    )
    assert "repository register" in section_text, (
        "README.md 'many repos' section missing 'repository register'"
    )
