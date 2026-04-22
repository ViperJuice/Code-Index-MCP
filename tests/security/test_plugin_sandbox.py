"""SL-1 unit tests — envelope, supervisor, SandboxedPlugin round-trip."""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

from mcp_server.plugins.sandboxed_plugin import SandboxedPlugin
from mcp_server.sandbox.capabilities import CapabilitySet
from mcp_server.sandbox.protocol import (
    MAX_LINE_BYTES,
    Envelope,
    ProtocolError,
    decode,
    encode,
)
from mcp_server.sandbox.supervisor import (
    SandboxCallError,
    SandboxSupervisor,
    SandboxTimeout,
)

# Repo root (ancestor containing mcp_server/ and tests/). Passed to child
# subprocesses as PYTHONPATH so they resolve the worker module plus fixtures.
REPO_ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# protocol — envelope codec
# ---------------------------------------------------------------------------


def test_envelope_roundtrip():
    e = Envelope(v=1, id="abc", kind="call", method="supports", payload={"x": 1})
    line = encode(e)
    assert line.endswith(b"\n")
    e2 = decode(line)
    assert e2 == e


def test_envelope_oversize_rejected():
    huge = "x" * (MAX_LINE_BYTES + 10)
    e = Envelope(v=1, id="a", kind="call", method="m", payload={"s": huge})
    with pytest.raises(ProtocolError):
        encode(e)


def test_envelope_decode_rejects_garbage():
    with pytest.raises(ProtocolError):
        decode(b"not-json-at-all\n")


def test_envelope_decode_rejects_wrong_version():
    with pytest.raises(ProtocolError):
        decode(b'{"v":2,"id":"a","kind":"call","method":"m","payload":{}}\n')


# ---------------------------------------------------------------------------
# supervisor — spawn / call / close against a trivial echo worker
# ---------------------------------------------------------------------------


def _echo_worker_cmd(tmp_path: Path) -> list:
    """Build a worker command that runs an inline echo script.

    The inline script acts as a minimal IPC responder: it reads one envelope
    per line from stdin and writes the same envelope back with kind=result.
    """
    script = textwrap.dedent("""
        import sys, json
        stdin = sys.stdin.buffer
        stdout = sys.stdout.buffer
        while True:
            line = stdin.readline()
            if not line:
                break
            try:
                env = json.loads(line.decode('utf-8'))
            except Exception:
                break
            env['kind'] = 'result'
            env['payload'] = {'echoed': env.get('payload', {})}
            stdout.write((json.dumps(env) + "\\n").encode('utf-8'))
            stdout.flush()
        """)
    path = tmp_path / "echo_worker.py"
    path.write_text(script)
    return [sys.executable, str(path)]


def test_supervisor_spawn_and_close(tmp_path: Path):
    caps = CapabilitySet(fs_read=(), fs_write=(), env_allow=frozenset())
    sup = SandboxSupervisor(_echo_worker_cmd(tmp_path), caps)
    resp = sup.call("ping", {"a": 1}, timeout=5.0)
    assert resp == {"echoed": {"a": 1}}
    sup.close()
    # Proc gone.
    assert sup._proc is None


def test_supervisor_timeout(tmp_path: Path):
    """A worker that never responds triggers SandboxTimeout."""
    script = textwrap.dedent("""
        import sys, time
        # Read one line then sleep forever, never reply.
        sys.stdin.buffer.readline()
        time.sleep(60)
        """)
    path = tmp_path / "sleepy.py"
    path.write_text(script)
    caps = CapabilitySet(fs_read=(), fs_write=(), env_allow=frozenset())
    sup = SandboxSupervisor([sys.executable, str(path)], caps)
    try:
        with pytest.raises(SandboxTimeout):
            sup.call("ping", {}, timeout=0.5)
    finally:
        sup.close()


def test_supervisor_worker_exited(tmp_path: Path):
    """Worker that exits before responding surfaces SandboxCallError."""
    script = textwrap.dedent("""
        import sys
        sys.exit(3)
        """)
    path = tmp_path / "die.py"
    path.write_text(script)
    caps = CapabilitySet(fs_read=(), fs_write=(), env_allow=frozenset())
    sup = SandboxSupervisor([sys.executable, str(path)], caps)
    try:
        with pytest.raises((SandboxCallError, SandboxTimeout)):
            sup.call("ping", {}, timeout=2.0)
    finally:
        sup.close()


# ---------------------------------------------------------------------------
# SandboxedPlugin — end-to-end with the mock plugin fixture
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _pythonpath_env():
    """Ensure the worker subprocess can import tests.security.fixtures.*."""
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


def _caps_for_mock() -> CapabilitySet:
    # Generous caps so the mock plugin imports cleanly; keep env_allow loose
    # enough that PATH/HOME/PYTHONPATH reach the child.
    return CapabilitySet(
        fs_read=(REPO_ROOT,),
        fs_write=(),
        env_allow=frozenset({"PATH", "HOME", "PYTHONPATH", "LANG", "LC_ALL"}),
        network=True,  # mock does no network; keep caps unchanged for speed
        sqlite="none",
    )


def test_sandboxed_plugin_supports_roundtrip():
    p = SandboxedPlugin(
        "tests.security.fixtures.mock_plugin",
        _caps_for_mock(),
        gh_cmd=sys.executable,
    )
    try:
        assert p.supports("x.py") is True
    finally:
        p.close()


def test_sandboxed_plugin_indexfile_roundtrip():
    p = SandboxedPlugin(
        "tests.security.fixtures.mock_plugin",
        _caps_for_mock(),
        gh_cmd=sys.executable,
    )
    try:
        shard = p.indexFile("x.py", "print(1)")
        assert shard["file"] == "x.py"
        assert shard["language"] == "mock"
        assert shard["symbols"] == [{"name": "echo", "len": len("print(1)")}]
    finally:
        p.close()


def test_sandboxed_plugin_find_references_roundtrip():
    p = SandboxedPlugin(
        "tests.security.fixtures.mock_plugin",
        _caps_for_mock(),
        gh_cmd=sys.executable,
    )
    try:
        refs = list(p.findReferences("foo"))
        assert len(refs) == 1
        assert refs[0].file == "mock.py"
        assert refs[0].start_line == 1
    finally:
        p.close()


def test_sandboxed_plugin_language_cached():
    p = SandboxedPlugin(
        "tests.security.fixtures.mock_plugin",
        _caps_for_mock(),
        gh_cmd=sys.executable,
    )
    try:
        assert p.language == "mock"
        assert p.language == "mock"  # cached; no second IPC call
    finally:
        p.close()


# ---------------------------------------------------------------------------
# PluginFactory sandbox opt-in surface
# ---------------------------------------------------------------------------


def test_plugin_factory_sandbox_on_by_default():
    """Default behavior is sandbox-on after SL-5 flip. DISABLE=1 is required to turn it off."""
    from mcp_server.plugins.plugin_factory import PluginFactory

    # Clear any stray env that a parallel test might have set.
    os.environ.pop("MCP_PLUGIN_SANDBOX_ENABLED", None)
    os.environ.pop("MCP_PLUGIN_SANDBOX_DISABLE", None)
    try:
        p = PluginFactory.create_plugin("python")
        # SL-5: default-on means no-cap path still returns SandboxedPlugin.
        assert type(p).__name__ == "SandboxedPlugin"
    finally:
        if hasattr(p, "close"):
            p.close()


def test_plugin_factory_sandbox_opt_in_via_capabilities():
    """Passing capabilities= must flip the factory to SandboxedPlugin."""
    from mcp_server.plugins.plugin_factory import PluginFactory

    caps = CapabilitySet(
        fs_read=(REPO_ROOT,),
        fs_write=(),
        env_allow=frozenset({"PATH", "HOME", "PYTHONPATH"}),
        network=True,
        sqlite="none",
    )
    p = PluginFactory.create_plugin("python", capabilities=caps)
    try:
        assert type(p).__name__ == "SandboxedPlugin"
    finally:
        if hasattr(p, "close"):
            p.close()
