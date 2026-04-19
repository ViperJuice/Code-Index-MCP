"""Sandbox IPC protocol — Envelope Pydantic model + line-framed codec.

Each IPC message is a single UTF-8 JSON line terminated by ``\\n``. Lines are
capped at ``MAX_LINE_BYTES`` (16 MiB). The framing is deliberately minimal:
stdin/stdout of the worker subprocess carry one Envelope per line.
"""

from __future__ import annotations

from typing import IO, Literal, Optional

from pydantic import BaseModel, ValidationError

from mcp_server.core.errors import MCPError

MAX_LINE_BYTES: int = 16 * 1024 * 1024
DEFAULT_TIMEOUT_SECONDS: float = 30.0


class ProtocolError(MCPError):
    """Raised when an envelope line is oversized, malformed, or truncated."""


class Envelope(BaseModel):
    v: Literal[1]
    id: str
    kind: Literal["call", "result", "error", "log"]
    method: str
    payload: dict


def encode(e: Envelope) -> bytes:
    """Serialize an Envelope to a single UTF-8 JSON line ending in ``\\n``."""
    line = e.model_dump_json().encode("utf-8")
    if len(line) + 1 > MAX_LINE_BYTES:
        raise ProtocolError(
            f"envelope too large: {len(line) + 1} > {MAX_LINE_BYTES} bytes"
        )
    return line + b"\n"


def decode(line: bytes) -> Envelope:
    """Validate and parse a single framed envelope line.

    Accepts either a trailing-newline-stripped or raw line. Raises
    :class:`ProtocolError` on oversize or malformed JSON.
    """
    if len(line) > MAX_LINE_BYTES:
        raise ProtocolError(
            f"envelope too large: {len(line)} > {MAX_LINE_BYTES} bytes"
        )
    if line.endswith(b"\n"):
        line = line[:-1]
    try:
        return Envelope.model_validate_json(line)
    except ValidationError as exc:
        raise ProtocolError(f"malformed envelope: {exc}") from exc
    except ValueError as exc:
        raise ProtocolError(f"malformed envelope JSON: {exc}") from exc


def read_envelope(stream: IO[bytes]) -> Optional[Envelope]:
    """Read one line from ``stream`` and decode it; returns None on clean EOF.

    Oversized lines raise :class:`ProtocolError` before decoding.
    """
    line = stream.readline(MAX_LINE_BYTES + 1)
    if not line:
        return None
    if len(line) > MAX_LINE_BYTES and not line.endswith(b"\n"):
        raise ProtocolError("envelope exceeds MAX_LINE_BYTES without newline")
    return decode(line)
