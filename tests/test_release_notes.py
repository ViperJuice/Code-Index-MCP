import re
from pathlib import Path


def test_changelog_has_rc1_section():
    """Assert CHANGELOG contains [1.2.0-rc1] with date in YYYY-MM-DD format."""
    changelog_path = Path(__file__).parent.parent / "CHANGELOG.md"
    content = changelog_path.read_text()
    assert re.search(
        r"^## \[1\.2\.0-rc1\] — \d{4}-\d{2}-\d{2}$", content, re.MULTILINE
    ), "CHANGELOG missing [1.2.0-rc1] section with date"


def test_changelog_has_rc5_public_alpha_recut_section():
    """Assert CHANGELOG contains the P34 rc5 public-alpha recut section."""
    changelog_path = Path(__file__).parent.parent / "CHANGELOG.md"
    content = " ".join(changelog_path.read_text().split())
    assert "## [1.2.0-rc5] — 2026-04-23" in content
    for expected in (
        "P27-P33",
        "P34",
        "many unrelated repositories",
        "one registered worktree",
        "tracked/default branch",
        "index_unavailable",
        "safe_fallback",
        "native_search",
    ):
        assert expected in content


def test_changelog_unreleased_empty():
    """Assert [Unreleased] section exists and is empty (no subsections)."""
    changelog_path = Path(__file__).parent.parent / "CHANGELOG.md"
    content = changelog_path.read_text()

    # Find the [Unreleased] header
    unreleased_match = re.search(r"^## \[Unreleased\]$", content, re.MULTILINE)
    assert unreleased_match, "CHANGELOG missing [Unreleased] section"

    # Get position after [Unreleased] header
    start_pos = unreleased_match.end()

    # Find the next ## heading
    next_heading = re.search(r"^## \[", content[start_pos:], re.MULTILINE)
    if next_heading:
        section_content = content[start_pos : start_pos + next_heading.start()]
    else:
        section_content = content[start_pos:]

    # Assert no subsection markers (### Added/Changed/Fixed)
    assert not re.search(
        r"^###\s", section_content, re.MULTILINE
    ), "[Unreleased] section should be empty (no subsections)"


def test_sandbox_has_p18_upgrade_link():
    """Assert docs/security/sandbox.md contains reference to p18-upgrade.md."""
    sandbox_path = Path(__file__).parent.parent / "docs" / "security" / "sandbox.md"
    content = sandbox_path.read_text()
    assert "p18-upgrade.md" in content, "sandbox.md missing link to p18-upgrade.md"
