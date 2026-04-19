"""GitHub Actions artifact provider implementation."""

from __future__ import annotations

import email.utils
import json
import subprocess
import time
from pathlib import Path
from typing import List, Mapping, Tuple

from mcp_server.core.errors import TerminalArtifactError
from .base import ArtifactRecord

try:
    from mcp_server.metrics.prometheus_exporter import (
        mcp_rate_limit_sleeps_total,
        mcp_artifact_errors_by_class_total,
    )
except ImportError:
    mcp_rate_limit_sleeps_total = None
    mcp_artifact_errors_by_class_total = None


def _parse_retry_after(value: str) -> float:
    """Parse a Retry-After header value (integer seconds or HTTP-date) → seconds."""
    try:
        return float(int(value))
    except ValueError:
        pass
    try:
        dt = email.utils.parsedate_to_datetime(value)
        delay = dt.timestamp() - time.time()
        return max(0.0, delay)
    except Exception:
        return 60.0


def _respect_rate_limit(headers: Mapping[str, str], status_code: int = 200) -> float:
    """Inspect status_code + headers and apply appropriate backoff.

    - 403: raise TerminalArtifactError (forbidden / missing scope)
    - 429: parse Retry-After, sleep (capped at 300s), increment rate-limit counter
    - 200 with low X-RateLimit-Remaining: legacy backoff via reset timestamp
    """
    if status_code == 403:
        if mcp_artifact_errors_by_class_total is not None:
            try:
                mcp_artifact_errors_by_class_total.labels(
                    error_class="TerminalArtifactError"
                ).inc()
            except Exception:
                pass
        raise TerminalArtifactError("forbidden / missing scope (HTTP 403)")

    if status_code == 429:
        retry_after = headers.get("Retry-After")
        if retry_after:
            sleep_s = min(_parse_retry_after(retry_after), 300.0)
        else:
            sleep_s = min(60.0, 300.0)
        time.sleep(sleep_s)
        if mcp_rate_limit_sleeps_total is not None:
            try:
                mcp_rate_limit_sleeps_total.inc()
            except Exception:
                pass
        return sleep_s

    # Legacy path: low X-RateLimit-Remaining on 2xx responses
    remaining = int(headers.get("X-RateLimit-Remaining", "5000"))
    if remaining < 100:
        reset = int(headers.get("X-RateLimit-Reset", str(int(time.time()) + 60)))
        sleep_s = max(0.0, reset - time.time())
        sleep_s = min(sleep_s, 300.0)
        time.sleep(sleep_s)
        return sleep_s
    return 0.0


def _gh_api(gh_cmd: str, path: str, *extra: str) -> Tuple[Mapping[str, str], str]:
    result = subprocess.run(
        [gh_cmd, "api", "--include", path, *extra],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, gh_cmd, result.stdout, result.stderr)
    header_block, _, body = result.stdout.partition("\r\n\r\n")
    if not _:
        # Fallback: some platforms use \n\n
        header_block, _, body = result.stdout.partition("\n\n")
    headers: dict[str, str] = {}
    status_code = 200
    lines = header_block.splitlines()
    if lines:
        status_line = lines[0]
        # Parse "HTTP/1.1 NNN Reason"
        parts = status_line.split(" ", 2)
        if len(parts) >= 2 and parts[1].isdigit():
            status_code = int(parts[1])
    for line in lines[1:]:
        if ": " in line:
            k, v = line.split(": ", 1)
            headers[k] = v
    _respect_rate_limit(headers, status_code=status_code)
    return headers, body


class GitHubActionsArtifactProvider:
    """Artifact provider backed by GitHub Actions artifacts via gh CLI."""

    def __init__(self, repo: str):
        self.repo = repo

    def list_artifacts(self, prefixes: Tuple[str, ...]) -> List[ArtifactRecord]:
        _, body = _gh_api(
            "gh",
            f"/repos/{self.repo}/actions/artifacts",
            "-H",
            "Accept: application/vnd.github+json",
        )
        payload = json.loads(body)

        records: List[ArtifactRecord] = []
        for artifact in payload.get("artifacts", []):
            name = artifact.get("name", "")
            if not name.startswith(prefixes):
                continue
            records.append(
                ArtifactRecord(
                    artifact_id=str(artifact.get("id")),
                    name=name,
                    created_at=artifact.get("created_at", ""),
                    size_bytes=int(artifact.get("size_in_bytes", 0)),
                    metadata={"expires_at": artifact.get("expires_at")},
                )
            )

        records.sort(key=lambda a: a.created_at, reverse=True)
        return records

    def download_artifact(self, artifact_id: str, destination: Path) -> Path:
        # --include is not compatible with --output; skip rate-limit header parsing here.
        destination.mkdir(parents=True, exist_ok=True)
        zip_path = destination / "artifact.zip"
        subprocess.run(
            [
                "gh",
                "api",
                "-H",
                "Accept: application/vnd.github+json",
                f"/repos/{self.repo}/actions/artifacts/{artifact_id}/zip",
                "--output",
                str(zip_path),
            ],
            check=True,
        )
        return zip_path

    def upload_artifact(
        self, artifact_name: str, source_paths: List[Path], retention_days: int
    ) -> str:
        raise NotImplementedError("GitHub artifact upload is handled by Actions workflows")

    def delete_artifact(self, artifact_id: str) -> bool:
        try:
            _gh_api(
                "gh",
                f"/repos/{self.repo}/actions/artifacts/{artifact_id}",
                "-X",
                "DELETE",
                "-H",
                "Accept: application/vnd.github+json",
            )
            return True
        except subprocess.CalledProcessError:
            return False
