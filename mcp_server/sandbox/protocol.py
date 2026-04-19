"""Sandbox IPC protocol — Envelope Pydantic model."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

MAX_LINE_BYTES: int = 16 * 1024 * 1024
DEFAULT_TIMEOUT_SECONDS: float = 30.0


class Envelope(BaseModel):
    v: Literal[1]
    id: str
    kind: Literal["call", "result", "error", "log"]
    method: str
    payload: dict
