"""Contract tests for pytest.mark.requires_gh_auth (SL-2.1).

Verifies:
  1. Marker is declared in pytest.ini (strict-markers compliance).
  2. The conftest hook skips marked tests when env var is unset.
  3. The conftest hook lets marked tests run when RUN_GH_AUTHENTICATED_TESTS=1.

Note: pytester runs an isolated inner pytest that does NOT share our real
conftest.py or pytest.ini.  Tests 2 and 3 replicate the hook pattern and
ini registration inside the inner run — this tests the logic of the hook
implementation, not the live conftest.py fixture.
"""

import pytest

pytest_plugins = "pytester"

# ---------------------------------------------------------------------------
# 1. Marker is registered in the outer pytest.ini
# ---------------------------------------------------------------------------


def test_marker_registered_in_ini(request):
    """requires_gh_auth must appear in the markers block so strict-markers passes."""
    markers_ini = request.config.getini("markers")
    marker_names = [m.split(":")[0].strip() for m in markers_ini]
    assert "requires_gh_auth" in marker_names, (
        "requires_gh_auth not found in pytest.ini markers block — "
        "add it so --strict-markers does not error"
    )


# ---------------------------------------------------------------------------
# 2 & 3. Hook behaviour via pytester
# ---------------------------------------------------------------------------

_CONFTEST = """\
import os
import pytest

def pytest_collection_modifyitems(config, items):
    if os.getenv("RUN_GH_AUTHENTICATED_TESTS") == "1":
        return
    skip_mark = pytest.mark.skip(reason="set RUN_GH_AUTHENTICATED_TESTS=1 to run")
    for item in items:
        if list(item.iter_markers(name="requires_gh_auth")):
            item.add_marker(skip_mark)
"""

_TESTS = """\
import pytest

@pytest.mark.requires_gh_auth
def test_needs_auth():
    pass

def test_no_auth():
    pass
"""

_INI = """\
[pytest]
markers =
    requires_gh_auth: tests requiring live gh CLI auth; set RUN_GH_AUTHENTICATED_TESTS=1 to run
"""


def test_hook_skips_when_env_unset(pytester):
    """When env var is absent the marked test must be skipped, not failed."""
    pytester.makeconftest(_CONFTEST)
    pytester.makefile(".ini", pytest=_INI.strip().split("[pytest]\n", 1)[1])
    pytester.makepyfile(_TESTS)

    # Ensure env var is absent for this inner run
    result = pytester.runpytest("--override-ini=markers=requires_gh_auth: gh auth marker")
    result.assert_outcomes(passed=1, skipped=1)


def test_hook_runs_when_env_set(pytester, monkeypatch):
    """When RUN_GH_AUTHENTICATED_TESTS=1 the marked test must not be skipped."""
    monkeypatch.setenv("RUN_GH_AUTHENTICATED_TESTS", "1")
    pytester.makeconftest(_CONFTEST)
    pytester.makefile(".ini", pytest=_INI.strip().split("[pytest]\n", 1)[1])
    pytester.makepyfile(_TESTS)

    result = pytester.runpytest("--override-ini=markers=requires_gh_auth: gh auth marker")
    result.assert_outcomes(passed=2, skipped=0)
