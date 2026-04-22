import re
from pathlib import Path


def test_changelog_has_rc1_section():
    """Assert CHANGELOG contains [1.2.0-rc1] with date in YYYY-MM-DD format."""
    changelog_path = Path(__file__).parent.parent / "CHANGELOG.md"
    content = changelog_path.read_text()
    assert re.search(
        r"^## \[1\.2\.0-rc1\] — \d{4}-\d{2}-\d{2}$", content, re.MULTILINE
    ), "CHANGELOG missing [1.2.0-rc1] section with date"


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
