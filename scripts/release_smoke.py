#!/usr/bin/env python3
"""Release smoke checks for wheel, lexical MCP, and production container paths."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import venv
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

REPO = Path(__file__).resolve().parents[1]
IMAGE = "ghcr.io/viperjuice/code-index-mcp:local-smoke"


def _run(cmd: list[str], *, cwd: Path = REPO, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(cmd), flush=True)
    run_env = os.environ.copy()
    if env:
        run_env.update(env)
    subprocess.run(cmd, cwd=str(cwd), env=run_env, check=True)


def _venv_bin(root: Path, name: str) -> Path:
    if os.name == "nt":
        return root / "Scripts" / f"{name}.exe"
    return root / "bin" / name


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def smoke_wheel() -> None:
    with tempfile.TemporaryDirectory(prefix="mcp-release-wheel-") as tmp:
        root = Path(tmp)
        dist = root / "dist"
        venv_dir = root / "venv"
        dist.mkdir()

        _run([sys.executable, "-m", "build", "--wheel", "--outdir", str(dist)])
        wheels = sorted(dist.glob("index_it_mcp-*.whl"))
        if not wheels:
            raise RuntimeError(f"No index_it_mcp wheel produced in {dist}")

        venv.EnvBuilder(with_pip=True, clear=True).create(venv_dir)
        python = _venv_bin(venv_dir, "python")
        mcp_index = _venv_bin(venv_dir, "mcp-index")
        _run(
            [str(python), "-m", "pip", "install", str(wheels[-1])],
            env={"PIP_DISABLE_PIP_VERSION_CHECK": "1"},
        )
        _run([str(mcp_index), "--help"])


def smoke_stdio() -> None:
    sys.path.insert(0, str(REPO))
    from tests.fixtures.multi_repo import boot_test_server, build_temp_repo

    source = """
class SmokeWidget:
    pass


def release_smoke_token():
    return "p22 lexical smoke"
"""
    with tempfile.TemporaryDirectory(prefix="mcp-release-stdio-") as tmp:
        tmp_path = Path(tmp)
        repo_path, _ = build_temp_repo(
            tmp_path,
            "fixture_repo",
            seed_files={"smoke.py": source.lstrip()},
        )
        old_qdrant_path = os.environ.get("QDRANT_PATH")
        old_semantic_enabled = os.environ.get("SEMANTIC_SEARCH_ENABLED")
        os.environ["QDRANT_PATH"] = str(tmp_path / "missing-vector-index.qdrant")
        os.environ["SEMANTIC_SEARCH_ENABLED"] = "false"
        try:
            with boot_test_server(tmp_path, [repo_path]) as server:
                search = server.call_tool(
                    "search_code",
                    {
                        "query": "release_smoke_token",
                        "repository": str(repo_path),
                        "semantic": False,
                        "limit": 5,
                    },
                )
                if not isinstance(search, list) or not search:
                    raise AssertionError(f"search_code did not return results: {search!r}")

                lookup = server.call_tool(
                    "symbol_lookup",
                    {"symbol": "release_smoke_token", "repository": str(repo_path)},
                )
                if lookup.get("symbol") != "release_smoke_token":
                    raise AssertionError(f"symbol_lookup failed: {lookup!r}")
        finally:
            if old_qdrant_path is None:
                os.environ.pop("QDRANT_PATH", None)
            else:
                os.environ["QDRANT_PATH"] = old_qdrant_path
            if old_semantic_enabled is None:
                os.environ.pop("SEMANTIC_SEARCH_ENABLED", None)
            else:
                os.environ["SEMANTIC_SEARCH_ENABLED"] = old_semantic_enabled


def _poll_health(port: int, *, timeout: float = 60.0) -> None:
    deadline = time.monotonic() + timeout
    url = f"http://127.0.0.1:{port}/health"
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urlopen(url, timeout=2.0) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if payload.get("status") == "healthy":
                return
        except (OSError, URLError, json.JSONDecodeError) as exc:
            last_error = exc
        time.sleep(1.0)
    raise RuntimeError(f"Container health check did not pass: {last_error}")


def smoke_container() -> None:
    if shutil.which("docker") is None:
        raise RuntimeError("docker is required for --container smoke")

    _run(["docker", "build", "-f", "docker/dockerfiles/Dockerfile.production", "-t", IMAGE, "."])
    _run(["docker", "run", "--rm", IMAGE, "mcp-index", "--help"])

    port = _free_port()
    container_id = subprocess.check_output(
        [
            "docker",
            "run",
            "-d",
            "--rm",
            "-p",
            f"127.0.0.1:{port}:8000",
            "-e",
            "MCP_ENVIRONMENT=development",
            "-e",
            "JWT_SECRET_KEY=p22-release-smoke-jwt-secret-key-00000000",
            "-e",
            "DEFAULT_ADMIN_PASSWORD=p22-release-smoke-admin-password-00000000",
            "-e",
            "DEFAULT_ADMIN_EMAIL=admin@localhost",
            "-e",
            "CORS_ORIGINS=http://localhost",
            IMAGE,
        ],
        cwd=str(REPO),
        text=True,
    ).strip()
    try:
        _poll_health(port)
    finally:
        subprocess.run(
            ["docker", "stop", container_id],
            cwd=str(REPO),
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--wheel",
        action="store_true",
        help="Build wheel, install it in a fresh venv, and run mcp-index --help",
    )
    parser.add_argument(
        "--stdio",
        action="store_true",
        help="Run lexical search_code and symbol_lookup against a fixture repo",
    )
    parser.add_argument(
        "--container", action="store_true", help="Build and smoke the production container image"
    )
    parser.add_argument(
        "--all", action="store_true", help="Run wheel, stdio, and container smoke checks"
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.all:
        args.wheel = args.stdio = args.container = True
    if not (args.wheel or args.stdio or args.container):
        raise SystemExit("Choose at least one of --wheel, --stdio, --container, or --all")

    if args.wheel:
        smoke_wheel()
    if args.stdio:
        smoke_stdio()
    if args.container:
        smoke_container()


if __name__ == "__main__":
    main()
