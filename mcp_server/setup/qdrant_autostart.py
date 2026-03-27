"""Docker-only Qdrant autostart helpers."""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from mcp_server.config.settings import Settings

from .semantic_preflight import ServiceStatus, check_qdrant


@dataclass(frozen=True)
class QdrantStartResult:
    """Result of attempting local Qdrant startup."""

    started: bool
    already_running: bool
    attempted: bool
    command: List[str]
    message: str
    stderr: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize startup result."""
        return {
            "started": self.started,
            "already_running": self.already_running,
            "attempted": self.attempted,
            "command": self.command,
            "message": self.message,
            "stderr": self.stderr,
        }


def _cmd_available(command: List[str]) -> bool:
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return False
    return result.returncode == 0


def is_docker_available() -> bool:
    """True if docker CLI is installed and responsive."""
    return _cmd_available(["docker", "version"])


def resolve_compose_command() -> List[str]:
    """Resolve docker compose command sequence."""
    if _cmd_available(["docker", "compose", "version"]):
        return ["docker", "compose"]
    if _cmd_available(["docker-compose", "version"]):
        return ["docker-compose"]
    raise RuntimeError(
        "Docker Compose is not available. Install Docker Compose v2 (`docker compose`) "
        "or legacy `docker-compose`."
    )


def start_qdrant_via_compose(compose_file: Path) -> QdrantStartResult:
    """Start qdrant service with docker compose."""
    compose_cmd = resolve_compose_command()
    command = [*compose_cmd, "-f", str(compose_file), "up", "-d", "qdrant"]

    process = subprocess.run(command, capture_output=True, text=True, check=False)
    if process.returncode == 0:
        return QdrantStartResult(
            started=True,
            already_running=("is up-to-date" in (process.stdout or "")),
            attempted=True,
            command=command,
            message="Qdrant container started",
            stderr=(process.stderr or "").strip(),
        )

    return QdrantStartResult(
        started=False,
        already_running=False,
        attempted=True,
        command=command,
        message="Failed to start Qdrant container",
        stderr=(process.stderr or process.stdout or "").strip(),
    )


def wait_for_qdrant_ready(
    qdrant_url: str, timeout_s: float = 20.0, interval_s: float = 1.0
) -> bool:
    """Wait until Qdrant endpoint responds or timeout expires."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        check = check_qdrant(qdrant_url, timeout_s=min(interval_s, 2.0))
        if check.status == ServiceStatus.READY:
            return True
        time.sleep(interval_s)
    return False


def ensure_qdrant_running(settings: Settings) -> QdrantStartResult:
    """Ensure Qdrant is running; attempt docker autostart when unreachable."""
    qdrant_url = f"http://{settings.qdrant_host}:{settings.qdrant_port}"
    current = check_qdrant(qdrant_url, timeout_s=settings.semantic_preflight_timeout_seconds)
    if current.status == ServiceStatus.READY:
        return QdrantStartResult(
            started=True,
            already_running=True,
            attempted=False,
            command=[],
            message="Qdrant already running",
        )

    if not is_docker_available():
        return QdrantStartResult(
            started=False,
            already_running=False,
            attempted=False,
            command=[],
            message="Docker is not available; cannot autostart Qdrant",
        )

    compose_path = Path(settings.qdrant_compose_file)
    if not compose_path.exists():
        return QdrantStartResult(
            started=False,
            already_running=False,
            attempted=False,
            command=[],
            message=f"Qdrant compose file not found: {compose_path}",
        )

    start_result = start_qdrant_via_compose(compose_path)
    if not start_result.started:
        return start_result

    ready = wait_for_qdrant_ready(
        qdrant_url,
        timeout_s=max(float(settings.semantic_preflight_timeout_seconds), 20.0),
        interval_s=1.0,
    )
    if ready:
        return QdrantStartResult(
            started=True,
            already_running=start_result.already_running,
            attempted=True,
            command=start_result.command,
            message="Qdrant is running and healthy",
            stderr=start_result.stderr,
        )

    return QdrantStartResult(
        started=False,
        already_running=False,
        attempted=True,
        command=start_result.command,
        message="Qdrant start was attempted but health check timed out",
        stderr=start_result.stderr,
    )
