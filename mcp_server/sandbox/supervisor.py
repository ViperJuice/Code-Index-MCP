"""Sandbox supervisor — manages a worker subprocess lifecycle over JSON-line IPC."""

from __future__ import annotations

import logging
import selectors
import subprocess
import uuid
from typing import List, Optional

from mcp_server.core.errors import MCPError
from mcp_server.sandbox.capabilities import CapabilitySet
from mcp_server.sandbox.protocol import (
    DEFAULT_TIMEOUT_SECONDS,
    Envelope,
    ProtocolError,
    decode,
    encode,
)

logger = logging.getLogger(__name__)


class SandboxCallError(MCPError):
    """Raised on the host when the worker returns an error envelope."""

    def __init__(self, payload: dict):
        self.error_type = payload.get("type", "Unknown")
        self.error_message = payload.get("message", "")
        super().__init__(f"{self.error_type}: {self.error_message}", details=payload)


class SandboxTimeout(MCPError):
    """Raised when the worker does not respond within the call timeout."""


class SandboxSupervisor:
    def __init__(self, worker_cmd: List[str], capabilities: CapabilitySet) -> None:
        self._worker_cmd = list(worker_cmd)
        self._capabilities = capabilities
        self._proc: Optional[subprocess.Popen] = None

    def _ensure_spawned(self) -> None:
        if self._proc is not None and self._proc.poll() is None:
            return
        # Spawn with empty env by default — caps_apply scrubs anyway, but
        # keeping the parent env to PATH-resolve ``python`` saves headaches.
        self._proc = subprocess.Popen(
            self._worker_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
        )

    def _read_line_with_timeout(self, timeout: float) -> bytes:
        """Block up to ``timeout`` s for one line from the worker's stdout."""
        assert self._proc is not None and self._proc.stdout is not None
        sel = selectors.DefaultSelector()
        sel.register(self._proc.stdout, selectors.EVENT_READ)
        try:
            events = sel.select(timeout)
            if not events:
                # Timeout — kill the worker to reclaim resources.
                try:
                    self._proc.kill()
                except Exception:
                    pass
                raise SandboxTimeout(
                    f"worker did not respond within {timeout:.1f}s"
                )
        finally:
            sel.close()

        line = self._proc.stdout.readline()
        if not line:
            # Worker died; include stderr for diagnostics.
            stderr_tail = b""
            try:
                if self._proc.stderr is not None:
                    stderr_tail = self._proc.stderr.read() or b""
            except Exception:
                pass
            raise SandboxCallError(
                {
                    "type": "WorkerExited",
                    "message": f"worker exited: {stderr_tail[-512:]!r}",
                }
            )
        return line

    def call(
        self,
        method: str,
        payload: dict,
        *,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> dict:
        self._ensure_spawned()
        assert self._proc is not None and self._proc.stdin is not None

        call_id = uuid.uuid4().hex
        env = Envelope(v=1, id=call_id, kind="call", method=method, payload=payload)

        try:
            self._proc.stdin.write(encode(env))
            self._proc.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            raise SandboxCallError(
                {"type": "WriteFailed", "message": f"worker stdin closed: {exc}"}
            ) from exc

        line = self._read_line_with_timeout(timeout)
        try:
            resp = decode(line)
        except ProtocolError as exc:
            raise SandboxCallError(
                {"type": "ProtocolError", "message": str(exc)}
            ) from exc

        if resp.kind == "error":
            raise SandboxCallError(resp.payload)
        if resp.kind != "result":
            raise SandboxCallError(
                {
                    "type": "UnexpectedKind",
                    "message": f"expected result envelope, got {resp.kind!r}",
                }
            )
        return resp.payload

    def close(self) -> None:
        if self._proc is None:
            return
        proc = self._proc
        self._proc = None

        if proc.poll() is not None:
            return

        # Polite close: send a ``close`` envelope and give it 2s.
        try:
            if proc.stdin is not None and not proc.stdin.closed:
                try:
                    proc.stdin.write(
                        encode(
                            Envelope(
                                v=1,
                                id=uuid.uuid4().hex,
                                kind="call",
                                method="close",
                                payload={},
                            )
                        )
                    )
                    proc.stdin.flush()
                except (BrokenPipeError, OSError):
                    pass
        except Exception:
            pass

        try:
            proc.wait(timeout=2.0)
            return
        except subprocess.TimeoutExpired:
            pass

        try:
            proc.terminate()
            proc.wait(timeout=1.0)
            return
        except (subprocess.TimeoutExpired, OSError):
            pass

        try:
            proc.kill()
            proc.wait(timeout=1.0)
        except Exception:
            pass
