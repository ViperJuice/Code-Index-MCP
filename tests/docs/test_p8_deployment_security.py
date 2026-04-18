"""Tests for P8 SL-2: MCP Access Controls subsection in DEPLOYMENT-GUIDE.md."""
import re
from pathlib import Path

GUIDE = Path(__file__).parent.parent.parent / "docs" / "DEPLOYMENT-GUIDE.md"


def _load_lines():
    return GUIDE.read_text(encoding="utf-8").splitlines()


def _security_section_line_range(lines):
    """Return (start, end) inclusive line indices of the first ## Security-prefixed section."""
    start = None
    for i, line in enumerate(lines):
        if re.match(r"^## Security", line):
            start = i
            break
    assert start is not None, "No '## Security' heading found in DEPLOYMENT-GUIDE.md"
    for i in range(start + 1, len(lines)):
        if re.match(r"^## ", lines[i]):
            return start, i - 1
    return start, len(lines) - 1


def test_security_heading_present():
    lines = _load_lines()
    matches = [l for l in lines if re.match(r"^## Security", l)]
    assert len(matches) >= 1, "Expected at least one '## Security' heading"


def test_mcp_client_secret_in_security_section():
    lines = _load_lines()
    start, end = _security_section_line_range(lines)
    section = "\n".join(lines[start : end + 1])
    assert "MCP_CLIENT_SECRET" in section, (
        "MCP_CLIENT_SECRET not found in the ## Security Best Practices section"
    )


def test_mcp_allowed_roots_in_security_section():
    lines = _load_lines()
    start, end = _security_section_line_range(lines)
    section = "\n".join(lines[start : end + 1])
    assert "MCP_ALLOWED_ROOTS" in section, (
        "MCP_ALLOWED_ROOTS not found in the ## Security Best Practices section"
    )


def test_existing_auth_subsection_unchanged():
    lines = _load_lines()
    headings = [l for l in lines if l.startswith("### ")]
    assert "### 1. Authentication and Authorization" in headings, (
        "Existing '### 1. Authentication and Authorization' heading missing or renamed"
    )


def test_mcp_access_controls_subsection_present():
    lines = _load_lines()
    headings = [l for l in lines if l.startswith("### ")]
    assert "### MCP Access Controls" in headings, (
        "'### MCP Access Controls' subsection not found in DEPLOYMENT-GUIDE.md"
    )


def test_mcp_access_controls_inside_security_section():
    lines = _load_lines()
    start, end = _security_section_line_range(lines)
    section_lines = lines[start : end + 1]
    assert any(l == "### MCP Access Controls" for l in section_lines), (
        "'### MCP Access Controls' is not inside the ## Security Best Practices section"
    )


def test_numbered_subsections_not_removed():
    lines = _load_lines()
    headings = [l for l in lines if l.startswith("### ")]
    for expected in [
        "### 1. Authentication and Authorization",
        "### 2. Input Validation",
        "### 3. Rate Limiting",
        "### 4. Network Security",
    ]:
        assert expected in headings, f"Subsection '{expected}' was removed or renumbered"
