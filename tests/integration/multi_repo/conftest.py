"""
Fixtures for multi-repo live integration tests (IF-0-P20-1).

Spawns ≥2 real uvicorn gateway subprocesses sharing one on-disk registry.
Health polling uses GET /health (no auth required).
"""

from __future__ import annotations

import atexit
import os
import shutil
import signal
import socket
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple

import pytest
import requests

from mcp_server.storage.repository_registry import RepositoryRegistry

# Root of the project tree so gateway subprocess can import mcp_server.
_PROJECT_ROOT = Path(__file__).parents[3]


# ---------------------------------------------------------------------------
# Frozen interface contracts — IF-0-P20-1
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GatewayHandle:
    pid: int
    port: int
    base_url: str  # e.g. "http://127.0.0.1:53412"


@dataclass(frozen=True)
class RepoHandle:
    path: Path
    repo_id: str          # 16-hex sha256 from RepositoryRegistry.register_repository
    sqlite_path: Path     # per-repo SQLite store


@dataclass(frozen=True)
class MultiRepoContext:
    gateways: Tuple[GatewayHandle, ...]  # len == n_gateways, default 2
    registry_path: Path                   # shared across all gateways
    repos: Dict[str, RepoHandle]          # keyed by repo_id; len == n_repos


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

class GatewayBootTimeout(Exception):
    def __init__(self, port: int, stderr: bytes):
        super().__init__(f"Gateway on port {port} did not become healthy in time")
        self.port = port
        self.stderr = stderr


_ADMIN_PASSWORD = "IntegTest!P20xQ9"
_JWT_SECRET = "integration-test-jwt-secret-p20-xQ9zAbCd"


def _alloc_free_ports(n: int):
    ports = []
    for _ in range(n):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        sock.close()
        ports.append(port)
    return ports


def _spawn_gateway(port: int, registry_path: Path, workspace_root: Path) -> Tuple[subprocess.Popen, GatewayHandle]:
    env = {
        **os.environ,
        "MCP_REPO_REGISTRY": str(registry_path),
        "MCP_ALLOWED_ROOTS": str(workspace_root),
        "MCP_ENVIRONMENT": "development",
        "MCP_LOG_FORMAT": "text",
        "DEFAULT_ADMIN_PASSWORD": _ADMIN_PASSWORD,
        "DEFAULT_ADMIN_EMAIL": "admin@test.local",
        "JWT_SECRET_KEY": _JWT_SECRET,
        "ACCESS_TOKEN_EXPIRE_MINUTES": "60",
        # Override .env.native settings that would point to non-existent /workspaces paths
        "MCP_ENABLE_MULTI_REPO": "false",
        "MCP_ENABLE_MULTI_PATH": "false",
        "MCP_INDEX_STORAGE_PATH": str(workspace_root / "indexes"),
        "MCP_WORKSPACE_ROOT": str(workspace_root),
        "SEMANTIC_SEARCH_ENABLED": "false",
    }

    for attempt in range(2):
        try:
            proc = subprocess.Popen(
                ["python", "-m", "uvicorn", "mcp_server.gateway:app",
                 "--host", "127.0.0.1", "--port", str(port)],
                env=env,
                cwd=str(_PROJECT_ROOT),
                start_new_session=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            break
        except OSError as exc:
            if "Errno 98" in str(exc) and attempt == 0:
                # Port in use; wait briefly then retry
                time.sleep(0.5)
                continue
            raise

    # Poll GET /health (no auth required) until 200 or timeout
    deadline = time.monotonic() + 30.0
    url = f"http://127.0.0.1:{port}/health"
    while time.monotonic() < deadline:
        try:
            resp = requests.get(url, timeout=1.0)
            if resp.status_code == 200:
                handle = GatewayHandle(
                    pid=proc.pid,
                    port=port,
                    base_url=f"http://127.0.0.1:{port}",
                )
                return proc, handle
        except requests.ConnectionError:
            pass
        time.sleep(0.25)

    stderr_data = b""
    try:
        proc.kill()
        _, stderr_data = proc.communicate(timeout=5)
    except Exception:
        pass
    raise GatewayBootTimeout(port, stderr_data)


def _terminate_gateway(proc: subprocess.Popen) -> None:
    try:
        pgid = os.getpgid(proc.pid)
        os.killpg(pgid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        try:
            pgid = os.getpgid(proc.pid)
            os.killpg(pgid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait()


# ---------------------------------------------------------------------------
# Fixture factory
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def multi_repo_fixture():
    """
    Factory fixture that yields a callable returning MultiRepoContext.

    Usage:
        ctx = multi_repo_fixture(n_gateways=2, n_repos=2)
    """
    _active_procs = []
    _tmpdir = None

    def factory(n_gateways: int = 2, n_repos: int = 2) -> MultiRepoContext:
        nonlocal _tmpdir

        # Create isolated tmp workspace
        _tmpdir = Path(tempfile.mkdtemp(prefix="mcp_p20_sl1_"))
        registry_path = _tmpdir / "registry" / "registry.json"
        registry_path.parent.mkdir(parents=True)

        # Register backstop so zombies are reaped even on abort
        def _atexit_cleanup():
            for p in _active_procs:
                _terminate_gateway(p)
        atexit.register(_atexit_cleanup)

        # Create repo workspaces and register them BEFORE spawning gateways
        reg = RepositoryRegistry(registry_path=registry_path)
        repos: Dict[str, RepoHandle] = {}
        for i in range(n_repos):
            repo_dir = _tmpdir / f"repo-{i}"
            repo_dir.mkdir()
            # Give each repo at least one file so it's a valid workspace
            (repo_dir / "README.txt").write_text(f"repo-{i} workspace\n")
            repo_id = reg.register_repository(str(repo_dir))
            sqlite_path = repo_dir / ".mcp-index" / "current.db"
            repos[repo_id] = RepoHandle(
                path=repo_dir,
                repo_id=repo_id,
                sqlite_path=sqlite_path,
            )

        # Allocate ports
        ports = _alloc_free_ports(n_gateways)

        # Build a workspace root that covers all repo dirs (comma-sep not needed;
        # MCP_ALLOWED_ROOTS is the common parent)
        workspace_root = _tmpdir

        # Spawn gateways
        gateways = []
        for port in ports:
            proc, handle = _spawn_gateway(port, registry_path, workspace_root)
            _active_procs.append(proc)
            gateways.append(handle)

        return MultiRepoContext(
            gateways=tuple(gateways),
            registry_path=registry_path,
            repos=repos,
        )

    yield factory

    # Teardown: terminate all gateways
    for proc in _active_procs:
        _terminate_gateway(proc)

    if _tmpdir is not None:
        shutil.rmtree(str(_tmpdir), ignore_errors=True)
