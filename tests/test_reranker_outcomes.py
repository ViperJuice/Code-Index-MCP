"""Unit tests for the truthful rerank outcome vocabulary (INFERSAFE Lane B).

These exercise the dispatcher-invoked (synchronous trio) rerank path via
``EnhancedDispatcher._apply_reranker`` and assert that the structured
``RerankDiagnostics`` recorded on ``_last_rerank_diagnostics`` reports the
correct outcome. A failed rerank, or one that returned the original ordering
unchanged, must NEVER be reported as ``succeeded``.
"""

import logging

from mcp_server.dispatcher.dispatcher_enhanced import EnhancedDispatcher
from mcp_server.indexer.reranker import (
    RerankDiagnostics,
    RerankFallbackSignal,
    RerankOutcome,
)


def _make_dispatcher(reranker, *, reranker_type="voyage", skips_semantic=False):
    """Build a minimal dispatcher with only the reranker wiring populated."""
    d = EnhancedDispatcher.__new__(EnhancedDispatcher)
    d._reranker = reranker
    d._reranker_type = reranker_type
    d._reranker_skips_semantic = skips_semantic
    d._last_rerank_diagnostics = None
    return d


def _candidates():
    return [
        {"file": "a.py", "line": 1, "snippet": "alpha", "score": 0.9},
        {"file": "b.py", "line": 2, "snippet": "beta", "score": 0.8},
        {"file": "c.py", "line": 3, "snippet": "gamma", "score": 0.7},
    ]


class _ReorderReranker:
    """Reranker that genuinely changes the ordering."""

    def rerank(self, query, candidates, top_k):
        return list(reversed(candidates))[:top_k]


class _UnchangedReranker:
    """Reranker that returns the input ordering (masked-failure signature)."""

    def rerank(self, query, candidates, top_k):
        return candidates[:top_k]


class _RaisingReranker:
    """Reranker that raises — models a genuine failure."""

    def rerank(self, query, candidates, top_k):
        raise RuntimeError("provider exploded")


class _FallbackReranker:
    """Reranker that fails over and publishes a fallback signal."""

    def __init__(self):
        self.last_fallback = None

    def rerank(self, query, candidates, top_k):
        self.last_fallback = RerankFallbackSignal(
            failed_provider="voyage", fallback_provider="flashrank"
        )
        return list(reversed(candidates))[:top_k]


def test_not_configured_when_no_reranker():
    d = _make_dispatcher(None)
    out = d._apply_reranker(None, "q", _candidates(), limit=10)
    assert [c["file"] for c in out] == ["a.py", "b.py", "c.py"]
    diag = d._last_rerank_diagnostics
    assert isinstance(diag, RerankDiagnostics)
    assert diag.outcome is RerankOutcome.NOT_CONFIGURED


def test_succeeded_on_real_reorder():
    d = _make_dispatcher(_ReorderReranker())
    out = d._apply_reranker(None, "q", _candidates(), limit=10)
    assert [c["file"] for c in out] == ["c.py", "b.py", "a.py"]
    diag = d._last_rerank_diagnostics
    assert diag.outcome is RerankOutcome.SUCCEEDED
    assert diag.reordered is True
    assert diag.provider == "voyage"


def test_failed_on_exception_not_reported_succeeded():
    d = _make_dispatcher(_RaisingReranker())
    out = d._apply_reranker(None, "q", _candidates(), limit=10)
    # Original ordering preserved on failure.
    assert [c["file"] for c in out] == ["a.py", "b.py", "c.py"]
    diag = d._last_rerank_diagnostics
    assert diag.outcome is RerankOutcome.FAILED
    assert diag.outcome is not RerankOutcome.SUCCEEDED
    assert diag.error and "exploded" in diag.error


def test_unchanged_order_not_reported_succeeded():
    d = _make_dispatcher(_UnchangedReranker())
    out = d._apply_reranker(None, "q", _candidates(), limit=10)
    assert [c["file"] for c in out] == ["a.py", "b.py", "c.py"]
    diag = d._last_rerank_diagnostics
    assert diag.outcome is not RerankOutcome.SUCCEEDED
    assert diag.outcome is RerankOutcome.ATTEMPTED
    assert diag.reordered is False


def test_fallback_applied_names_providers():
    d = _make_dispatcher(_FallbackReranker())
    out = d._apply_reranker(None, "q", _candidates(), limit=10)
    assert [c["file"] for c in out] == ["c.py", "b.py", "a.py"]
    diag = d._last_rerank_diagnostics
    assert diag.outcome is RerankOutcome.FALLBACK_APPLIED
    assert diag.failed_provider == "voyage"
    assert diag.fallback_provider == "flashrank"


def test_skipped_policy_on_semantic_skip_path():
    # A text reranker on the pure-vector semantic path is skipped by policy.
    d = _make_dispatcher(
        _ReorderReranker(), reranker_type="flashrank", skips_semantic=True
    )
    out = d._apply_reranker(None, "q", _candidates(), limit=10, semantic_source=True)
    # Ordering untouched; reranker never ran.
    assert [c["file"] for c in out] == ["a.py", "b.py", "c.py"]
    diag = d._last_rerank_diagnostics
    assert diag.outcome is RerankOutcome.SKIPPED_POLICY
    assert diag.policy == "flashrank"


def test_diagnostics_carry_no_document_text():
    # The redaction contract: diagnostics record ids/counts/providers only.
    d = _make_dispatcher(_ReorderReranker())
    d._apply_reranker(None, "secret query text", _candidates(), limit=10)
    payload = str(d._last_rerank_diagnostics.to_dict())
    assert "alpha" not in payload
    assert "secret query text" not in payload


class _LastErrorReranker:
    """Sync reranker that swallows a provider failure: it returns the original
    order but publishes the reason via ``last_error`` (a masked failure)."""

    def __init__(self, error="provider timed out"):
        self.last_error = error

    def rerank(self, query, candidates, top_k):
        return candidates[:top_k]


class _SecretRaisingReranker:
    """Raising reranker whose exception message carries a credential."""

    SECRET = "sk-abcdef123456"

    def rerank(self, query, candidates, top_k):
        raise RuntimeError(f"auth rejected bearer {self.SECRET}")


def test_last_error_reports_failed_not_attempted():
    # A swallowed failure (original order + last_error) is FAILED, not the
    # benign ATTEMPTED no-op it was previously misreported as.
    d = _make_dispatcher(_LastErrorReranker())
    out = d._apply_reranker(None, "q", _candidates(), limit=10)
    assert [c["file"] for c in out] == ["a.py", "b.py", "c.py"]
    diag = d._last_rerank_diagnostics
    assert diag.outcome is RerankOutcome.FAILED
    assert diag.outcome is not RerankOutcome.ATTEMPTED
    assert diag.error and "timed out" in diag.error


def test_last_error_exception_text_is_redacted():
    secret = "api_key=SECRETTOKEN123"
    d = _make_dispatcher(_LastErrorReranker(error=f"auth failed {secret}"))
    d._apply_reranker(None, "q", _candidates(), limit=10)
    diag = d._last_rerank_diagnostics
    assert diag.outcome is RerankOutcome.FAILED
    assert "SECRETTOKEN123" not in (diag.error or "")
    assert "[REDACTED]" in (diag.error or "")


def test_failure_redacts_exception_and_leaks_no_query_or_candidate_text(caplog):
    d = _make_dispatcher(_SecretRaisingReranker())
    with caplog.at_level(logging.DEBUG):
        d._apply_reranker(None, "secretqueryzz", _candidates(), limit=10)
    diag = d._last_rerank_diagnostics
    assert diag.outcome is RerankOutcome.FAILED
    # Exception credential is redacted in diagnostics and logs.
    assert _SecretRaisingReranker.SECRET not in (diag.error or "")
    assert "[REDACTED]" in (diag.error or "")
    assert _SecretRaisingReranker.SECRET not in caplog.text
    # No query or candidate document/snippet text reaches the logs.
    assert "secretqueryzz" not in caplog.text
    assert "alpha" not in caplog.text
