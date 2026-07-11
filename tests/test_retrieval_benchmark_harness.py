"""Tests for the frozen retrieval-benchmark harness (BENCHFREEZE)."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import pytest

from mcp_server.benchmarks.retrieval_eval_harness import (
    ARMS,
    DEPTHS,
    ArmSpec,
    FrozenEvalError,
    HoldoutViolationError,
    RetrievalBenchmarkHarness,
    assert_no_holdout,
    load_frozen_eval,
    ndcg_at_k,
    percentile,
    recall_at_k,
    reciprocal_rank,
)

# ---------------------------------------------------------------------------
# Metric correctness on hand-computed tiny inputs
# ---------------------------------------------------------------------------

# Fixture ranking used across metric tests:
#   ranked = [d2, d1, d3], relevant (binary) = {d1, d3}
#   ranks (1-indexed): d2=1 (irrelevant), d1=2 (relevant), d3=3 (relevant)
RANKED = ["d2", "d1", "d3"]
RELEVANT_IDS = {"d1", "d3"}
RELEVANCE = {"d1": 1.0, "d3": 1.0}


def test_ndcg_hand_computed():
    # gains (binary rel=1 -> 2**1-1 = 1) discounted by log2(rank+1):
    #   d2 rank1: rel 0                -> 0
    #   d1 rank2: 1 / log2(3)          -> 0.63092975
    #   d3 rank3: 1 / log2(4) = 1/2    -> 0.5
    # DCG = 1.13092975
    dcg = 1.0 / math.log2(3) + 1.0 / math.log2(4)
    # IDCG: ideal order puts both relevant first:
    #   rank1: 1/log2(2)=1 ; rank2: 1/log2(3)
    idcg = 1.0 / math.log2(2) + 1.0 / math.log2(3)
    expected = dcg / idcg
    assert ndcg_at_k(RANKED, RELEVANCE, 3) == pytest.approx(expected)
    assert ndcg_at_k(RANKED, RELEVANCE, 3) == pytest.approx(0.6934264, abs=1e-6)


def test_ndcg_perfect_and_empty():
    # perfect ordering -> 1.0
    assert ndcg_at_k(["d1", "d3", "d2"], RELEVANCE, 3) == pytest.approx(1.0)
    # no relevant docs at all -> 0.0 (no attainable gain)
    assert ndcg_at_k(RANKED, {}, 3) == 0.0
    # empty ranking -> 0.0
    assert ndcg_at_k([], RELEVANCE, 3) == 0.0


def test_ndcg_graded():
    # graded relevance exercises the 2**rel - 1 gain
    ranked = ["a", "b", "c"]
    rel = {"a": 3.0, "b": 2.0, "c": 0.0}
    dcg = (2**3 - 1) / math.log2(2) + (2**2 - 1) / math.log2(3)
    idcg = dcg  # already ideal ordering
    assert ndcg_at_k(ranked, rel, 3) == pytest.approx(dcg / idcg)
    assert ndcg_at_k(ranked, rel, 3) == pytest.approx(1.0)


def test_mrr_hand_computed():
    # first relevant (d1) is at 1-indexed rank 2 -> 1/2
    assert reciprocal_rank(RANKED, RELEVANT_IDS) == pytest.approx(0.5)
    # first relevant at rank 1
    assert reciprocal_rank(["d1", "d2"], RELEVANT_IDS) == pytest.approx(1.0)
    # no relevant present -> 0
    assert reciprocal_rank(["x", "y"], RELEVANT_IDS) == 0.0


def test_recall_hand_computed():
    # top-2 = {d2, d1}; intersect relevant = {d1} -> 1/2
    assert recall_at_k(RANKED, RELEVANT_IDS, 2) == pytest.approx(0.5)
    # top-3 recovers both -> 1.0
    assert recall_at_k(RANKED, RELEVANT_IDS, 3) == pytest.approx(1.0)
    # k=1 recovers neither -> 0.0
    assert recall_at_k(RANKED, RELEVANT_IDS, 1) == 0.0
    # no relevant defined -> 0.0
    assert recall_at_k(RANKED, set(), 3) == 0.0


def test_percentile():
    assert percentile([], 95) == 0.0
    assert percentile([10.0], 50) == pytest.approx(10.0)
    assert percentile([1.0, 2.0, 3.0, 4.0], 50) == pytest.approx(2.5)


# ---------------------------------------------------------------------------
# Freeze gate (load_frozen_eval)
# ---------------------------------------------------------------------------

def _write_eval_dir(tmp_path: Path, *, signed=True, break_checksum=None, omit_manifest=False) -> Path:
    """Fabricate a frozen eval dir; optionally break the gate."""
    eval_dir = tmp_path / "retrieval_eval"
    eval_dir.mkdir()

    # Real dataset schema: id / relevant_doc_ids / holdout (boolean).
    queries = [
        {"id": "q1", "query": "find the parser", "category": "exact_identifier",
         "relevant_doc_ids": ["docA"], "hard_negative_doc_ids": ["docB"], "holdout": False},
        {"id": "q2", "query": "error on startup", "category": "concept",
         "relevant_doc_ids": ["docB"], "hard_negative_doc_ids": ["docA"], "holdout": False},
        {"id": "h1", "query": "held out", "category": "exact_identifier",
         "relevant_doc_ids": ["docA"], "hard_negative_doc_ids": [], "holdout": True},
    ]
    queries_bytes = ("\n".join(json.dumps(q) for q in queries) + "\n").encode()
    (eval_dir / "queries.jsonl").write_bytes(queries_bytes)

    # ``corpus_sha256`` is a path-list digest recorded in BOTH corpus_manifest.json
    # and MANIFEST.json (and must be equal); it is NOT a byte-hash of this file.
    corpus_sha = "c" * 64
    corpus = {
        "repo": "test-repo",
        "doc_count": 2,
        "corpus_sha256": corpus_sha,
        "corpus_sha256_algorithm": "sha256 of sorted included relative paths",
    }
    corpus_bytes = json.dumps(corpus).encode()
    (eval_dir / "corpus_manifest.json").write_bytes(corpus_bytes)

    thresholds = {"version": "gate.v1", "min_ndcg": {"lexical": {"20": 0.1}}, "max_p95_ms": 500}
    thresholds_bytes = json.dumps(thresholds).encode()
    (eval_dir / "gate_thresholds.json").write_bytes(thresholds_bytes)

    def sha(b: bytes) -> str:
        return hashlib.sha256(b).hexdigest()

    manifest = {
        "version": "manifest.v1",
        "dataset_sha256": sha(queries_bytes),
        "corpus_sha256": corpus_sha,
        "thresholds_sha256": sha(thresholds_bytes),
        "holdout_query_ids": ["h1"],
        "review": {"signed": signed, "reviewer": "alice", "date": "2026-07-01"},
    }
    if break_checksum:
        # For dataset_sha256/thresholds_sha256 this breaks the byte-hash check;
        # for corpus_sha256 it makes MANIFEST.corpus_sha256 != corpus_manifest.
        manifest[break_checksum] = "0" * 64  # wrong sha

    if not omit_manifest:
        (eval_dir / "MANIFEST.json").write_text(json.dumps(manifest))
    return eval_dir


def test_load_frozen_eval_ok(tmp_path):
    frozen = load_frozen_eval(_write_eval_dir(tmp_path))
    assert len(frozen.queries) == 3
    assert frozen.holdout_ids == frozenset({"h1"})
    assert frozen.query_ids("main") == ["q1", "q2"]
    assert frozen.query_ids("holdout") == ["h1"]
    assert set(frozen.checksums()) == {"dataset_sha256", "corpus_sha256", "thresholds_sha256"}


def test_load_frozen_eval_refuses_missing_manifest(tmp_path):
    eval_dir = _write_eval_dir(tmp_path, omit_manifest=True)
    with pytest.raises(FrozenEvalError, match="MANIFEST missing"):
        load_frozen_eval(eval_dir)


def test_load_frozen_eval_refuses_unsigned(tmp_path):
    eval_dir = _write_eval_dir(tmp_path, signed=False)
    with pytest.raises(FrozenEvalError, match="signed"):
        load_frozen_eval(eval_dir)


@pytest.mark.parametrize("bad", ["dataset_sha256", "corpus_sha256", "thresholds_sha256"])
def test_load_frozen_eval_refuses_checksum_mismatch(tmp_path, bad):
    eval_dir = _write_eval_dir(tmp_path, break_checksum=bad)
    with pytest.raises(FrozenEvalError, match="checksum mismatch"):
        load_frozen_eval(eval_dir)


# ---------------------------------------------------------------------------
# Holdout safety
# ---------------------------------------------------------------------------

def test_assert_no_holdout():
    assert_no_holdout(["q1", "q2"], ["h1"])  # ok
    with pytest.raises(HoldoutViolationError, match="h1"):
        assert_no_holdout(["q1", "h1"], ["h1"])


# ---------------------------------------------------------------------------
# Smoke run over a 2-query fake corpus
# ---------------------------------------------------------------------------

def _fake_arms():
    # lexical arm: ranks docA first for q1, docB first for q2
    lexical_map = {
        "q1": [("docA", 5.0), ("docC", 2.0)],
        "q2": [("docB", 3.0), ("docC", 1.0)],
    }
    # dense arm: different ordering / scores
    dense_map = {
        "q1": [("docC", 0.9), ("docA", 0.8)],
        "q2": [("docB", 0.7), ("docC", 0.4)],
    }
    # hybrid arm: fuses (docA/docB first) — plain id list (no scores)
    hybrid_map = {
        "q1": ["docA", "docC"],
        "q2": ["docB", "docC"],
    }

    def make(map_):
        def fn(query):
            return map_[query["id"]]
        return fn

    return {
        "lexical": ArmSpec(make(lexical_map), inference_cost=0.0, egress=False),
        "dense": ArmSpec(make(dense_map), inference_cost=0.001, egress=True),
        "hybrid": ArmSpec(make(hybrid_map), inference_cost=0.001, egress=True),
    }


def test_smoke_run_full_schema(tmp_path):
    frozen = load_frozen_eval(_write_eval_dir(tmp_path))
    harness = RetrievalBenchmarkHarness(frozen, _fake_arms(), depths=[20, 50])
    result = harness.run(split="main")

    # Top-level schema + bound checksums (traceability to frozen dataset).
    assert result["schema"] == "retrieval_eval_result.v1"
    assert result["split"] == "main"
    assert result["consumed_query_ids"] == ["q1", "q2"]
    assert result["n_queries"] == 2
    for key in ("dataset_sha256", "corpus_sha256", "thresholds_sha256"):
        assert result[key] == frozen.checksums()[key]
    assert result["review"]["reviewer"] == "alice"
    assert result["holdout_ids"] == ["h1"]

    # Per-arm metrics + latency + cost/egress accounting.
    for arm in ("lexical", "dense", "hybrid"):
        arm_res = result["arms"][arm]
        assert set(arm_res) >= {
            "egress",
            "inference_cost",
            "error_rate",
            "zero_result_rate",
            "latency_p50_ms",
            "latency_p95_ms",
            "depths",
        }
        for depth in ("20", "50"):
            m = arm_res["depths"][depth]
            assert set(m) >= {"ndcg", "mrr", "recall", "zero_result_rate", "error_rate"}
    assert result["arms"]["dense"]["egress"] is True
    assert result["arms"]["lexical"]["egress"] is False

    # lexical arm perfectly ranks the single relevant doc first for both queries.
    assert result["arms"]["lexical"]["depths"]["20"]["mrr"] == pytest.approx(1.0)
    assert result["arms"]["lexical"]["depths"]["20"]["ndcg"] == pytest.approx(1.0)

    # Per-channel diagnostics for the fused (hybrid) arm are DERIVED from the
    # single-channel arms. docA for q1: lexical rank 1, dense rank 2.
    pc = result["per_channel"]["hybrid"]["q1"]["docA"]
    assert pc["lexical_rank"] == 1
    assert pc["dense_rank"] == 2
    assert pc["lexical_score"] == pytest.approx(5.0)
    assert pc["dense_score"] == pytest.approx(0.8)
    # docC for q1: lexical rank 2, dense rank 1
    pc_c = result["per_channel"]["hybrid"]["q1"]["docC"]
    assert pc_c["lexical_rank"] == 2
    assert pc_c["dense_rank"] == 1

    # Result must be JSON-serializable.
    json.dumps(result)


def test_run_error_and_zero_result_rates(tmp_path):
    frozen = load_frozen_eval(_write_eval_dir(tmp_path))

    def boom(query):
        if query["id"] == "q1":
            raise RuntimeError("arm exploded")
        return []  # zero results for q2

    arms = {"lexical": ArmSpec(boom)}
    harness = RetrievalBenchmarkHarness(frozen, arms, depths=[20])
    result = harness.run(split="main")
    arm_res = result["arms"]["lexical"]
    assert arm_res["error_rate"] == pytest.approx(0.5)  # 1 of 2 raised
    assert arm_res["zero_result_rate"] == pytest.approx(0.5)  # 1 of 2 empty


def test_arm_and_depth_constants():
    assert ARMS == ("lexical", "dense", "hybrid", "hybrid_rerank")
    assert DEPTHS == (20, 50, 100)


# ---------------------------------------------------------------------------
# Real committed dataset (benchmarks/retrieval_eval) — the frozen contract
# ---------------------------------------------------------------------------

def test_load_frozen_eval_real_dataset():
    """The harness loads and runs against the ACTUAL committed dataset."""
    frozen = load_frozen_eval("benchmarks/retrieval_eval")

    # Split sizes per the frozen contract: 50 queries, 10 held out.
    assert len(frozen.query_ids()) == 50
    assert len(frozen.query_ids("holdout")) == 10
    assert len(frozen.query_ids("main")) == 40

    # Trivial arms: map each query to a ranked list of its relevant doc ids.
    def perfect(query):
        return list(query["relevant_doc_ids"])

    arms = {name: ArmSpec(perfect) for name in ARMS}
    harness = RetrievalBenchmarkHarness(frozen, arms, depths=list(DEPTHS))
    result = harness.run(split="main")

    # Full result schema.
    assert result["schema"] == "retrieval_eval_result.v1"
    assert result["split"] == "main"
    assert result["n_queries"] == 40
    assert len(result["consumed_query_ids"]) == 40
    assert len(result["holdout_ids"]) == 10
    for key in ("dataset_sha256", "corpus_sha256", "thresholds_sha256"):
        assert result[key] == frozen.checksums()[key]

    for name in ARMS:
        assert name in result["arms"]
        arm_res = result["arms"][name]
        assert set(arm_res) >= {
            "egress",
            "inference_cost",
            "error_rate",
            "zero_result_rate",
            "latency_p50_ms",
            "latency_p95_ms",
            "depths",
        }
        for depth in DEPTHS:
            m = arm_res["depths"][str(depth)]
            assert set(m) >= {"ndcg", "mrr", "recall", "zero_result_rate", "error_rate"}

    # Result must be JSON-serializable.
    json.dumps(result)
