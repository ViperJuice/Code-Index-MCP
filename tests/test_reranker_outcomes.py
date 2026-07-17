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


# ==========================================================================
# CR2: the synchronous reranker trio (Voyage / FlashRank / CrossEncoder) must
# never log a raw provider exception. A credential embedded in the exception
# message must not reach caplog OR ``last_error``.
# ==========================================================================
import sys

from mcp_server.indexer.reranker import (
    CrossEncoderReranker,
    FlashRankReranker,
    VoyageReranker,
)

_SYNC_SECRET = "sk-SECRET123"
_SYNC_EXC_MSG = f"auth failed Bearer {_SYNC_SECRET}"


def _sync_candidates():
    return [
        {"file": "a.py", "snippet": "alpha", "_rerank_doc": "alpha doc"},
        {"file": "b.py", "snippet": "beta", "_rerank_doc": "beta doc"},
    ]


def test_voyage_sync_rerank_failure_redacts_exception(caplog):
    class _FakeVoyageClient:
        def rerank(self, **kwargs):
            raise RuntimeError(_SYNC_EXC_MSG)

    v = VoyageReranker.__new__(VoyageReranker)
    v._client = _FakeVoyageClient()
    v._model = "rerank-2"
    v.last_error = None

    with caplog.at_level(logging.DEBUG):
        out = v.rerank("secretqueryzz", _sync_candidates(), top_k=2)

    # Falls back to original order; credential never leaks.
    assert [c["file"] for c in out] == ["a.py", "b.py"]
    assert _SYNC_SECRET not in caplog.text
    assert _SYNC_SECRET not in (v.last_error or "")
    assert "[REDACTED]" in (v.last_error or "")


def test_flashrank_sync_rerank_failure_redacts_exception(caplog, monkeypatch):
    class _FakeRerankRequest:
        def __init__(self, **kwargs):
            pass

    class _FakeRanker:
        def rerank(self, request):
            raise RuntimeError(_SYNC_EXC_MSG)

    fake_flashrank = type(sys)("flashrank")
    fake_flashrank.RerankRequest = _FakeRerankRequest
    monkeypatch.setitem(sys.modules, "flashrank", fake_flashrank)

    fr = FlashRankReranker.__new__(FlashRankReranker)
    fr._model_name = "ms-marco"
    fr._ranker = _FakeRanker()  # already "loaded" -> _load() is a no-op
    fr.last_error = None

    with caplog.at_level(logging.DEBUG):
        out = fr.rerank("secretqueryzz", _sync_candidates(), top_k=2)

    assert [c["file"] for c in out] == ["a.py", "b.py"]
    assert _SYNC_SECRET not in caplog.text
    assert _SYNC_SECRET not in (fr.last_error or "")
    assert "[REDACTED]" in (fr.last_error or "")


def test_crossencoder_sync_rerank_failure_redacts_exception(caplog):
    class _FakeModel:
        def predict(self, pairs):
            raise RuntimeError(_SYNC_EXC_MSG)

    ce = CrossEncoderReranker.__new__(CrossEncoderReranker)
    ce._model_name = "cross-encoder"
    ce._model = _FakeModel()  # already "loaded" -> _load() is a no-op
    ce.last_error = None

    with caplog.at_level(logging.DEBUG):
        out = ce.rerank("secretqueryzz", _sync_candidates(), top_k=2)

    assert [c["file"] for c in out] == ["a.py", "b.py"]
    assert _SYNC_SECRET not in caplog.text
    assert _SYNC_SECRET not in (ce.last_error or "")
    assert "[REDACTED]" in (ce.last_error or "")


# ==========================================================================
# CR2: the dispatcher search() paths log query metadata only (query_chars),
# never the raw query body.
# ==========================================================================
def test_dispatcher_search_logs_no_raw_query_body(caplog):
    from pathlib import Path
    from unittest.mock import MagicMock

    from mcp_server.core.repo_context import RepoContext
    from mcp_server.plugins.plugin_set_registry import PluginSetRegistry
    from mcp_server.storage.multi_repo_manager import RepositoryInfo

    query_sentinel = "zzz_raw_query_body_sentinel_zzz"

    sqlite_store = MagicMock()
    sqlite_store.search_symbols_fuzzy.return_value = []
    sqlite_store.search_files_fuzzy.return_value = []

    registry_entry = MagicMock(spec=RepositoryInfo)
    registry_entry.tracked_branch = "main"
    registry_entry.path = Path("/tmp/test-repo")

    ctx = RepoContext(
        repo_id="test-repo-cr2",
        sqlite_store=sqlite_store,
        workspace_root=Path("/tmp/test-repo"),
        tracked_branch="main",
        registry_entry=registry_entry,
    )

    psr = PluginSetRegistry()
    psr._cache[ctx.repo_id] = []
    dispatcher = EnhancedDispatcher([], plugin_set_registry=psr)

    with caplog.at_level(logging.DEBUG):
        list(dispatcher.search(ctx, query_sentinel, fuzzy=True, limit=5))

    # The fuzzy-path log fired (proves we reached an instrumented log line)...
    assert "Using fuzzy trigram search" in caplog.text
    # ...but the raw query body never appears in any dispatcher log.
    assert query_sentinel not in caplog.text


# ==========================================================================
# INFERPOLISH item 1: the ASYNC BaseReranker trio (Cohere / cross-encoder /
# TF-IDF) rerank() exception paths must route the provider exception through
# ``_redact_error`` before logging -- a credential embedded in the exception
# must never reach caplog.
# ==========================================================================
import asyncio as _asyncio

from mcp_server.indexer.reranker import (
    CohereReranker,
    LocalCrossEncoderReranker,
    SearchResult,
    TFIDFReranker,
)

_ASYNC_SECRET = "sk-ASYNCSECRET789"
_ASYNC_EXC_MSG = f"provider auth failed Bearer {_ASYNC_SECRET}"


def _async_results():
    return [
        SearchResult(
            file_path="a.py",
            start_line=1,
            end_line=1,
            column=0,
            snippet="alpha",
            match_type="semantic",
            score=0.5,
        ),
        SearchResult(
            file_path="b.py",
            start_line=2,
            end_line=2,
            column=0,
            snippet="beta",
            match_type="semantic",
            score=0.4,
        ),
    ]


def test_async_cohere_rerank_failure_redacts_log(caplog):
    r = CohereReranker({})
    r.initialized = True

    class _FakeClient:
        def rerank(self, **kwargs):
            raise RuntimeError(_ASYNC_EXC_MSG)

    r.client = _FakeClient()

    with caplog.at_level(logging.DEBUG):
        result = _asyncio.run(r.rerank("secretqueryzz", _async_results(), top_k=2))

    assert not result.is_success
    assert "Cohere reranking failed" in caplog.text
    assert _ASYNC_SECRET not in caplog.text
    assert "[REDACTED]" in caplog.text


def test_async_crossencoder_rerank_failure_redacts_log(caplog):
    r = LocalCrossEncoderReranker({})
    r.initialized = True

    class _FakeModel:
        def predict(self, pairs):
            raise RuntimeError(_ASYNC_EXC_MSG)

    r.model = _FakeModel()

    with caplog.at_level(logging.DEBUG):
        result = _asyncio.run(r.rerank("secretqueryzz", _async_results(), top_k=2))

    assert not result.is_success
    assert "Cross-encoder reranking failed" in caplog.text
    assert _ASYNC_SECRET not in caplog.text
    assert "[REDACTED]" in caplog.text


def test_async_tfidf_rerank_failure_redacts_log(caplog):
    r = TFIDFReranker({})
    r.initialized = True

    class _FakeVectorizer:
        def fit_transform(self, texts):
            raise RuntimeError(_ASYNC_EXC_MSG)

    r.vectorizer = _FakeVectorizer()

    with caplog.at_level(logging.DEBUG):
        result = _asyncio.run(r.rerank("secretqueryzz", _async_results(), top_k=2))

    assert not result.is_success
    assert "TF-IDF reranking failed" in caplog.text
    assert _ASYNC_SECRET not in caplog.text
    assert "[REDACTED]" in caplog.text


# ==========================================================================
# INFERPOLISH item 3: search_documentation() logs topic metadata only
# (topic_chars), never the raw topic body.
# ==========================================================================
def test_search_documentation_logs_no_raw_topic_body(caplog):
    from unittest.mock import MagicMock

    d = EnhancedDispatcher.__new__(EnhancedDispatcher)
    # search_documentation only touches self.search (mocked empty) before/while
    # logging; no other dispatcher wiring is exercised on this path.
    d.search = MagicMock(return_value=[])

    topic_sentinel = "zzz_raw_topic_body_sentinel_zzz"
    ctx = MagicMock()

    with caplog.at_level(logging.DEBUG):
        list(d.search_documentation(ctx, topic_sentinel, limit=5))

    # The instrumented cross-document log fired...
    assert "Cross-document search" in caplog.text
    # ...but the raw topic body never appears in any dispatcher log.
    assert topic_sentinel not in caplog.text
