"""Sandbox capability set — frozen dataclass defining resource limits."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import FrozenSet, Literal, Tuple


@dataclass(frozen=True)
class CapabilitySet:
    fs_read: Tuple[Path, ...]
    fs_write: Tuple[Path, ...]
    env_allow: FrozenSet[str]
    network: bool = False
    sqlite: Literal["none", "readonly"] = "none"
    cpu_seconds: int = 30
    mem_mb: int = 512
