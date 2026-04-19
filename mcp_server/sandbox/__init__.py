"""Sandbox package — lazy re-export to avoid eager-import failure during lane fills."""

from __future__ import annotations


def __getattr__(name: str):
    if name == "Envelope":
        from .protocol import Envelope
        return Envelope
    if name == "ProtocolError":
        from .protocol import ProtocolError
        return ProtocolError
    if name == "CapabilitySet":
        from .capabilities import CapabilitySet
        return CapabilitySet
    if name == "SandboxViolation":
        from .capabilities import SandboxViolation
        return SandboxViolation
    if name == "DEFAULT_DENY":
        from .capabilities import DEFAULT_DENY
        return DEFAULT_DENY
    if name == "SandboxSupervisor":
        from .supervisor import SandboxSupervisor
        return SandboxSupervisor
    if name == "SandboxCallError":
        from .supervisor import SandboxCallError
        return SandboxCallError
    if name == "SandboxTimeout":
        from .supervisor import SandboxTimeout
        return SandboxTimeout
    if name == "main":
        from .worker_main import main
        return main
    raise AttributeError(f"module 'mcp_server.sandbox' has no attribute {name!r}")
