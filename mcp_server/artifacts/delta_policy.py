"""DeltaPolicy — decides full vs delta artifact strategy (IF-0-P14-4)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal, Optional

ENV_FULL_SIZE_LIMIT: str = "MCP_ARTIFACT_FULL_SIZE_LIMIT"
DEFAULT_FULL_SIZE_LIMIT_BYTES: int = 500 * 1024 * 1024  # 500 MB


@dataclass(frozen=True)
class DeltaDecision:
    strategy: Literal["full", "delta"]
    base_artifact_id: Optional[str]
    reason: str  # "below_limit" | "above_limit_with_base" | "above_limit_no_base"


class DeltaPolicy:
    def __init__(self, limit_bytes: Optional[int] = None) -> None:
        if limit_bytes is not None:
            self._limit_bytes = limit_bytes
        else:
            env_val = os.environ.get(ENV_FULL_SIZE_LIMIT)
            if env_val is not None:
                self._limit_bytes = int(env_val)
            else:
                self._limit_bytes = DEFAULT_FULL_SIZE_LIMIT_BYTES

    def decide(
        self,
        compressed_size_bytes: int,
        previous_artifact_id: Optional[str],
    ) -> DeltaDecision:
        if compressed_size_bytes <= self._limit_bytes:
            return DeltaDecision(
                strategy="full",
                base_artifact_id=None,
                reason="below_limit",
            )
        if previous_artifact_id is not None:
            return DeltaDecision(
                strategy="delta",
                base_artifact_id=previous_artifact_id,
                reason="above_limit_with_base",
            )
        return DeltaDecision(
            strategy="full",
            base_artifact_id=None,
            reason="above_limit_no_base",
        )
