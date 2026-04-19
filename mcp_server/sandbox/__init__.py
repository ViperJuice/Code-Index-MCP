"""Sandbox package — lazy re-export to avoid eager-import failure during lane fills."""

from __future__ import annotations


def __getattr__(name: str):
    if name == "Envelope":
        from .protocol import Envelope
        return Envelope
    if name == "CapabilitySet":
        from .capabilities import CapabilitySet
        return CapabilitySet
    if name == "SandboxSupervisor":
        from .supervisor import SandboxSupervisor
        return SandboxSupervisor
    if name == "main":
        from .worker_main import main
        return main
    raise AttributeError(f"module 'mcp_server.sandbox' has no attribute {name!r}")
