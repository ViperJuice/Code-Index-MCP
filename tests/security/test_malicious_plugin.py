"""SL-1 integration — hostile plugin must not escape the sandbox.

The fixture ``tests.security.fixtures.malicious_plugin`` attempts the
following attacks:

  * ``supports`` → open /etc/passwd for read.
  * ``indexFile`` → open a TCP socket + ``create_connection``.
  * ``getDefinition`` → read ``os.environ["GITHUB_TOKEN"]``; run an
    observe-only subprocess (``sh -c "echo pwned"``). Subprocess is
    policy-allowed (Go plugin needs it); that attack is *expected* to
    succeed and is documented, not defended.
  * ``findReferences`` → Python ``open(host_canary, "w")``. Expected to
    raise :class:`SandboxViolation` inside the worker.
  * ``search`` → ``sqlite3.connect`` on a host path.

The test asserts:

  1. Network, env scrub, SQLite, and Python-level filesystem guards each
     fire for their respective attack.
  2. The host canary file written via Python ``open`` does not exist.
  3. The host's ``GITHUB_TOKEN`` env var is not exposed to the worker.
  4. Subprocess is allowed (echo succeeds) — this is the documented
     userspace-sandbox limitation, not a bug.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from mcp_server.plugins.sandboxed_plugin import SandboxedPlugin
from mcp_server.sandbox.capabilities import CapabilitySet
from mcp_server.sandbox.supervisor import SandboxCallError

REPO_ROOT = Path(__file__).resolve().parents[2]
HOST_CANARY = Path("/tmp/mcp-sandbox-malicious-canary")
HOST_DB = Path("/tmp/mcp-sandbox-host-db.sqlite")


@pytest.fixture(autouse=True)
def _pythonpath_env():
    orig = os.environ.get("PYTHONPATH")
    existing = [p for p in (orig.split(os.pathsep) if orig else []) if p]
    repo = str(REPO_ROOT)
    if repo not in existing:
        existing.insert(0, repo)
    os.environ["PYTHONPATH"] = os.pathsep.join(existing)
    try:
        yield
    finally:
        if orig is None:
            os.environ.pop("PYTHONPATH", None)
        else:
            os.environ["PYTHONPATH"] = orig


@pytest.fixture
def clean_canaries():
    """Remove any canary/DB from prior runs; fail loudly if removal fails."""
    for p in (HOST_CANARY, HOST_DB):
        if p.exists():
            p.unlink()
    yield
    for p in (HOST_CANARY, HOST_DB):
        if p.exists():
            try:
                p.unlink()
            except OSError:
                pass


@pytest.fixture
def locked_down_caps(tmp_path: Path) -> CapabilitySet:
    # Scratch workspace — the worker may write here but NOT to /tmp host paths.
    work = tmp_path / "sandbox-workspace"
    work.mkdir()
    # fs_read must cover the Python stdlib + site-packages + the fixture
    # module — we include the full REPO_ROOT and sys.prefix directories.
    read_roots = (work, REPO_ROOT, Path(sys.prefix), Path(sys.base_prefix))
    return CapabilitySet(
        fs_read=read_roots,
        fs_write=(work,),
        env_allow=frozenset({"PATH", "HOME", "PYTHONPATH", "LANG", "LC_ALL"}),
        network=False,
        sqlite="none",
    )


def test_malicious_plugin_is_contained(
    clean_canaries, locked_down_caps: CapabilitySet, monkeypatch
):
    # Inject a distinctive secret into the host env. The sandbox env_allow
    # does NOT include this key, so the worker should not see it.
    monkeypatch.setenv("GITHUB_TOKEN", "super-secret-host-token-xyz")

    p = SandboxedPlugin(
        "tests.security.fixtures.malicious_plugin",
        locked_down_caps,
        gh_cmd=sys.executable,
    )
    try:
        # 1. supports — tries to read /etc/passwd. Returns True only if the
        #    read succeeded. Under a proper sandbox, False.
        assert p.supports("x.py") is False, "sandbox failed: plugin read /etc/passwd"

        # 2. indexFile — attempts socket.socket() and create_connection.
        #    The smuggled ``symbols`` list tells us which attacks fired.
        shard = p.indexFile("x.py", "content")
        attacks = {a["attack"]: a for a in shard["symbols"]}
        assert (
            attacks["socket"]["succeeded"] is False
        ), f"sandbox failed: socket opened: {attacks['socket']}"
        assert (
            attacks["create_connection"]["succeeded"] is False
        ), f"sandbox failed: create_connection opened: {attacks['create_connection']}"

        # 3. getDefinition — leaked_token must be empty (env scrubbed);
        #    subprocess is policy-allowed so "pwned" appears on stdout.
        defn = p.getDefinition("foo")
        doc = (defn or {}).get("doc", "")
        assert "leaked_token=''" in doc, f"sandbox failed: GITHUB_TOKEN leaked: {defn}"
        assert "subprocess_out='pwned'" in doc, (
            "subprocess should be policy-allowed per P15 spec; got: " + doc
        )

        # 4. findReferences — open(HOST_CANARY, "w") MUST raise
        #    SandboxViolation inside the worker. The fixture smuggles the
        #    exception name back in the single Reference's ``file`` field.
        refs = list(p.findReferences("foo"))
        assert len(refs) == 1, refs
        marker = refs[0].file
        assert (
            "SandboxViolation" in marker
        ), f"sandbox failed: Python open() not guarded: {marker!r}"

        # 5. search — sqlite3.connect(host_db) must be blocked.
        results = list(p.search("anything"))
        snippet = results[0]["snippet"] if results else ""
        assert "sqlite_attack_ok=False" in snippet, f"sandbox failed: sqlite opened: {snippet}"
        assert (
            "SandboxViolation" in snippet
        ), f"sandbox failed: sqlite blocked by wrong exception: {snippet}"
    finally:
        p.close()

    # 6. Canary written via Python ``open`` must not exist (that write path
    #    goes through the FS guard and is blocked). HOST_DB also must not
    #    exist (sqlite=none blocks connect, so no file created).
    assert not HOST_CANARY.exists(), f"sandbox failed: plugin created host canary at {HOST_CANARY}"
    assert not HOST_DB.exists(), f"sandbox failed: plugin created host DB at {HOST_DB}"

    # 7. Host env is unchanged.
    assert os.environ["GITHUB_TOKEN"] == "super-secret-host-token-xyz"
