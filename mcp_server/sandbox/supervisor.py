"""Sandbox supervisor — manages worker subprocess lifecycle."""

from __future__ import annotations

from typing import List

from mcp_server.sandbox.capabilities import CapabilitySet


class SandboxSupervisor:
    def __init__(self, worker_cmd: List[str], capabilities: CapabilitySet) -> None:
        raise NotImplementedError("filled by SL-1")

    def call(self, method: str, payload: dict, *, timeout: float = 30.0) -> dict:
        raise NotImplementedError("filled by SL-1")

    def close(self) -> None:
        raise NotImplementedError("filled by SL-1")
