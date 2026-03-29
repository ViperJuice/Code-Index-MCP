"""Skip all real-world tests unless explicitly opted in via environment variable."""

import os

import pytest


def pytest_collection_modifyitems(config, items):
    """Skip real-world tests unless RUN_REAL_WORLD_TESTS=1 is set."""
    if os.getenv("RUN_REAL_WORLD_TESTS", "0") == "1":
        return
    skip_marker = pytest.mark.skip(
        reason="Real-world tests skipped; set RUN_REAL_WORLD_TESTS=1 to run"
    )
    for item in items:
        if "real_world" in str(item.fspath):
            item.add_marker(skip_marker)
