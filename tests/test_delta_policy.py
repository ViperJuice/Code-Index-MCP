"""Tests for DeltaPolicy decision logic (IF-0-P14-4)."""

from __future__ import annotations

import os

import pytest

from mcp_server.artifacts.delta_policy import (
    DEFAULT_FULL_SIZE_LIMIT_BYTES,
    ENV_FULL_SIZE_LIMIT,
    DeltaDecision,
    DeltaPolicy,
)


def test_decide_below_limit_full():
    policy = DeltaPolicy()
    decision = policy.decide(compressed_size_bytes=100, previous_artifact_id=None)
    assert decision.strategy == "full"
    assert decision.base_artifact_id is None
    assert decision.reason == "below_limit"


def test_decide_below_limit_full_with_prev():
    policy = DeltaPolicy()
    decision = policy.decide(compressed_size_bytes=100, previous_artifact_id="abc123")
    assert decision.strategy == "full"
    assert decision.base_artifact_id is None
    assert decision.reason == "below_limit"


def test_decide_above_limit_delta_when_prev():
    policy = DeltaPolicy(limit_bytes=50)
    decision = policy.decide(compressed_size_bytes=100, previous_artifact_id="abc123")
    assert decision.strategy == "delta"
    assert decision.base_artifact_id == "abc123"
    assert decision.reason == "above_limit_with_base"


def test_decide_above_limit_full_when_no_prev():
    policy = DeltaPolicy(limit_bytes=50)
    decision = policy.decide(compressed_size_bytes=100, previous_artifact_id=None)
    assert decision.strategy == "full"
    assert decision.base_artifact_id is None
    assert decision.reason == "above_limit_no_base"


def test_decide_exactly_at_limit_is_full():
    policy = DeltaPolicy(limit_bytes=100)
    decision = policy.decide(compressed_size_bytes=100, previous_artifact_id="prev")
    assert decision.strategy == "full"
    assert decision.reason == "below_limit"


def test_env_var_sets_limit(monkeypatch):
    monkeypatch.setenv(ENV_FULL_SIZE_LIMIT, "1")
    policy = DeltaPolicy()
    decision = policy.decide(compressed_size_bytes=10, previous_artifact_id="prev")
    assert decision.strategy == "delta"
    assert decision.reason == "above_limit_with_base"


def test_default_limit_is_500mb():
    policy = DeltaPolicy()
    assert policy._limit_bytes == DEFAULT_FULL_SIZE_LIMIT_BYTES


def test_decision_is_frozen():
    decision = DeltaDecision(strategy="full", base_artifact_id=None, reason="below_limit")
    with pytest.raises((AttributeError, TypeError)):
        decision.strategy = "delta"  # type: ignore[misc]
