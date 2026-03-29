"""Skip document performance tests unless explicitly opted in via environment variable."""

import os
import pytest


def pytest_collection_modifyitems(config, items):
    """Skip document performance tests unless RUN_PERFORMANCE_TESTS=1 is set."""
    if os.getenv("RUN_PERFORMANCE_TESTS", "0") == "1":
        return
    skip_marker = pytest.mark.skip(
        reason="Performance tests skipped; set RUN_PERFORMANCE_TESTS=1 to run"
    )
    for item in items:
        if "performance" in str(item.fspath) and "document" in str(item.fspath):
            item.add_marker(skip_marker)
