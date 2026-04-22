"""Fixture-name contract for SL-4 — IF-0-P2B shared test scaffolding.

SL-0 declares the names so SL-4's conftest work has a stable target and
SL-3's gateway tests can import them without depending on SL-4's merge.

The fixture bodies are implemented in SL-4's ``tests/conftest.py``. Importing
this module yields the canonical names as a tuple so tests and lint rules
can reference them symbolically.
"""

from __future__ import annotations

from typing import Tuple

#: Canonical names of the P2B test fixtures. Referenced by SL-4's conftest
#: implementation and by any downstream lane that wants to introspect the
#: fixture surface without depending on pytest internals.
FIXTURE_NAMES: Tuple[str, ...] = (
    "repo_ctx",
    "store_registry",
    "repo_resolver",
    "dispatcher_factory",
)
