"""Release metadata assertions for P20 v1.2.0-rc2 cut."""

from __future__ import annotations

import subprocess


EXPECTED_VERSION = "1.2.0-rc2"
EXPECTED_TAG = "v1.2.0-rc2"


def test_package_version_matches_rc_tag():
    import mcp_server

    assert mcp_server.__version__ == EXPECTED_VERSION, (
        f"mcp_server.__version__ is {mcp_server.__version__!r}, "
        f"expected {EXPECTED_VERSION!r}"
    )


def test_release_candidate_tag_exists_locally():
    result = subprocess.run(
        ["git", "tag", "-l", EXPECTED_TAG],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == EXPECTED_TAG, (
        f"git tag -l {EXPECTED_TAG} returned {result.stdout!r}; "
        f"expected {EXPECTED_TAG!r}"
    )
