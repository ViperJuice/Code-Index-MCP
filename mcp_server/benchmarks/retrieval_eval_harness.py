"""Frozen retrieval-benchmark harness (BENCHFREEZE, IF-0-BENCHFREEZE-1).

This module provides the *harness* half of the BENCHFREEZE contract: a freeze
gate that binds a run to a signed, checksummed evaluation set, a set of pure
metric functions (nDCG@k / MRR / Recall@k), and a runner that evaluates
retrieval *arms* at multiple candidate depths.

Design constraints:
- **No live model calls.** Each arm is supplied as an injected callable
  ``arm_fn(query) -> ranked_list_of_doc_ids`` so the harness is fully testable
  with fakes and never needs a live index.
- **No dispatcher instrumentation.** Per-channel diagnostics (the lexical rank
  and dense rank of every fused result) are derived purely from the independent
  single-channel arm outputs the harness already collected.
- Stdlib + numpy only.

The frozen dataset / manifest / thresholds live under
``benchmarks/retrieval_eval/`` and are owned/curated by a separate lane; this
module only *reads and verifies* them.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np

# ---------------------------------------------------------------------------
# Protocol constants
# ---------------------------------------------------------------------------

#: Retrieval arms evaluated independently. ``lexical`` and ``dense`` are the
#: single-channel arms from which per-channel diagnostics are derived.
ARMS: Tuple[str, ...] = ("lexical", "dense", "hybrid", "hybrid_rerank")

#: Single-channel arms used for per-channel rank/score attribution.
CHANNEL_ARMS: Tuple[str, ...] = ("lexical", "dense")

#: Candidate depths at which each arm is scored.
DEPTHS: Tuple[int, ...] = (20, 50, 100)

#: Fixed cutoffs the frozen gate thresholds name. ``ndcg@10`` and ``recall@50``
#: are ALWAYS computed at these k's, independent of the candidate depth, so the
#: gate compares like-for-like against ``min_quality.ndcg@10`` / ``recall@50``.
#: (The earlier harness scored ndcg/recall at the candidate depth ``d`` and then
#: mislabeled the depth-20 value as ``ndcg@10`` — this constant removes that
#: ambiguity.)
NDCG_FIXED_K = 10
RECALL_FIXED_K = 50

#: The metric keys carrying the fixed-k values in every depth summary.
NDCG_FIXED_KEY = f"ndcg@{NDCG_FIXED_K}"
RECALL_FIXED_KEY = f"recall@{RECALL_FIXED_K}"

#: Frozen eval file names read by :func:`load_frozen_eval`.
QUERIES_FILE = "queries.jsonl"
CORPUS_FILE = "corpus_manifest.json"
THRESHOLDS_FILE = "gate_thresholds.json"
MANIFEST_FILE = "MANIFEST.json"

#: Query-id splits.
SPLIT_MAIN = "main"
SPLIT_HOLDOUT = "holdout"


class FrozenEvalError(RuntimeError):
    """Raised when the freeze gate refuses to run.

    Refusal causes: missing/unreadable MANIFEST, an unsigned review record, or a
    recorded checksum that does not match the actual file bytes.
    """


class HoldoutViolationError(RuntimeError):
    """Raised when a run that must not touch holdout consumed a holdout id."""


# ---------------------------------------------------------------------------
# Checksums
# ---------------------------------------------------------------------------

def sha256_bytes(data: bytes) -> str:
    """Return the hex sha256 of raw bytes."""
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    """Return the hex sha256 of a file's bytes."""
    return sha256_bytes(Path(path).read_bytes())


# ---------------------------------------------------------------------------
# Frozen eval loading + freeze gate
# ---------------------------------------------------------------------------

@dataclass
class FrozenEval:
    """A verified, frozen evaluation set bound to its manifest checksums."""

    eval_dir: Path
    queries: List[Dict[str, Any]]
    corpus_manifest: Dict[str, Any]
    thresholds: Dict[str, Any]
    manifest: Dict[str, Any]
    #: Checksums copied from MANIFEST, re-verified against file bytes on load.
    dataset_sha256: str
    corpus_sha256: str
    thresholds_sha256: str
    holdout_ids: frozenset = field(default_factory=frozenset)

    def query_ids(self, split: Optional[str] = None) -> List[str]:
        """Return query ids, optionally filtered to a split.

        A query whose ``id`` is in the manifest holdout set (or whose
        ``holdout`` field is ``True``) belongs to the holdout split.
        """
        out: List[str] = []
        for q in self.queries:
            qid = q["id"]
            if split is None:
                out.append(qid)
            elif split == self.query_split(q):
                out.append(qid)
        return out

    def query_split(self, query: Mapping[str, Any]) -> str:
        """Resolve the split of a single query record."""
        if query["id"] in self.holdout_ids:
            return SPLIT_HOLDOUT
        if query.get("holdout") is True:
            return SPLIT_HOLDOUT
        return SPLIT_MAIN

    def checksums(self) -> Dict[str, str]:
        """The bound checksums, for stamping into a result object."""
        return {
            "dataset_sha256": self.dataset_sha256,
            "corpus_sha256": self.corpus_sha256,
            "thresholds_sha256": self.thresholds_sha256,
        }


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def load_frozen_eval(eval_dir: str | Path) -> FrozenEval:
    """Load and *verify* the frozen eval set — the freeze gate.

    Refuses (raises :class:`FrozenEvalError`) if:
      * ``MANIFEST.json`` is missing or unreadable,
      * ``review.signed`` is not exactly ``True``, or
      * any recorded sha256 (``dataset_sha256`` / ``thresholds_sha256`` /
        ``corpus_sha256``) does not match the actual file bytes.
    """
    eval_dir = Path(eval_dir)
    manifest_path = eval_dir / MANIFEST_FILE
    if not manifest_path.is_file():
        raise FrozenEvalError(f"MANIFEST missing: {manifest_path}")

    try:
        manifest = json.loads(manifest_path.read_text())
    except (OSError, ValueError) as exc:
        raise FrozenEvalError(f"MANIFEST unreadable: {manifest_path}: {exc}") from exc

    review = manifest.get("review") or {}
    if review.get("signed") is not True:
        raise FrozenEvalError(
            "freeze gate: review.signed is not true "
            f"(got {review.get('signed')!r})"
        )

    # Verify the byte-checksummed files (dataset + thresholds) against disk.
    # ``corpus_sha256`` is NOT a byte-hash of ``corpus_manifest.json``; it is a
    # digest of the sorted corpus path list, so it is verified separately below.
    expected = {
        "dataset_sha256": eval_dir / QUERIES_FILE,
        "thresholds_sha256": eval_dir / THRESHOLDS_FILE,
    }
    for key, fpath in expected.items():
        recorded = manifest.get(key)
        if not recorded:
            raise FrozenEvalError(f"freeze gate: MANIFEST missing checksum {key!r}")
        if not fpath.is_file():
            raise FrozenEvalError(f"freeze gate: eval file missing: {fpath}")
        actual = sha256_file(fpath)
        if actual != recorded:
            raise FrozenEvalError(
                f"freeze gate: checksum mismatch for {key} "
                f"({fpath.name}): recorded {recorded}, actual {actual}"
            )

    # Cross-check ``corpus_sha256``: MANIFEST.json and corpus_manifest.json must
    # both record the same path-list digest. (corpus_manifest.json's *bytes* are
    # not the digest, so byte-hashing that file would be wrong.)
    corpus_path = eval_dir / CORPUS_FILE
    if not corpus_path.is_file():
        raise FrozenEvalError(f"freeze gate: eval file missing: {corpus_path}")
    corpus_manifest = json.loads(corpus_path.read_text())
    manifest_corpus_sha = manifest.get("corpus_sha256")
    corpus_recorded_sha = corpus_manifest.get("corpus_sha256")
    if not manifest_corpus_sha:
        raise FrozenEvalError("freeze gate: MANIFEST missing checksum 'corpus_sha256'")
    if not corpus_recorded_sha:
        raise FrozenEvalError(
            "freeze gate: corpus_manifest.json missing 'corpus_sha256'"
        )
    if manifest_corpus_sha != corpus_recorded_sha:
        raise FrozenEvalError(
            "freeze gate: corpus_sha256 checksum mismatch: "
            f"MANIFEST {manifest_corpus_sha} != "
            f"corpus_manifest {corpus_recorded_sha}"
        )

    queries = _read_jsonl(eval_dir / QUERIES_FILE)
    thresholds = json.loads((eval_dir / THRESHOLDS_FILE).read_text())
    holdout_ids = frozenset(
        manifest.get("holdout_query_ids") or manifest.get("holdout_ids") or []
    )

    return FrozenEval(
        eval_dir=eval_dir,
        queries=queries,
        corpus_manifest=corpus_manifest,
        thresholds=thresholds,
        manifest=manifest,
        dataset_sha256=manifest["dataset_sha256"],
        corpus_sha256=manifest["corpus_sha256"],
        thresholds_sha256=manifest["thresholds_sha256"],
        holdout_ids=holdout_ids,
    )


# ---------------------------------------------------------------------------
# Metrics (pure functions)
# ---------------------------------------------------------------------------

def _gain(rel: float) -> float:
    """Exponential relevance gain ``2**rel - 1`` (binary rel reduces to 1)."""
    return (2.0 ** float(rel)) - 1.0


def dcg_at_k(ranked_ids: Sequence[str], relevance: Mapping[str, float], k: int) -> float:
    """Discounted cumulative gain over the top ``k`` of ``ranked_ids``.

    ``relevance`` maps doc-id -> graded relevance; unlisted docs are 0.
    """
    total = 0.0
    for i, doc_id in enumerate(ranked_ids[:k]):
        rel = relevance.get(doc_id, 0.0)
        if rel:
            total += _gain(rel) / np.log2(i + 2)  # rank i -> log2(i+2)
    return float(total)


def ndcg_at_k(ranked_ids: Sequence[str], relevance: Mapping[str, float], k: int) -> float:
    """Normalized DCG@k. Returns 0.0 when there is no attainable gain."""
    ideal_order = sorted(relevance.values(), reverse=True)
    idcg = 0.0
    for i, rel in enumerate(ideal_order[:k]):
        if rel:
            idcg += _gain(rel) / np.log2(i + 2)
    if idcg <= 0.0:
        return 0.0
    return dcg_at_k(ranked_ids, relevance, k) / idcg


def reciprocal_rank(ranked_ids: Sequence[str], relevant_ids: Iterable[str]) -> float:
    """Reciprocal rank of the first relevant doc (1-indexed); 0 if none."""
    relevant = set(relevant_ids)
    for i, doc_id in enumerate(ranked_ids):
        if doc_id in relevant:
            return 1.0 / (i + 1)
    return 0.0


def recall_at_k(ranked_ids: Sequence[str], relevant_ids: Iterable[str], k: int) -> float:
    """Fraction of relevant docs retrieved in the top ``k``."""
    relevant = set(relevant_ids)
    if not relevant:
        return 0.0
    hits = sum(1 for doc_id in ranked_ids[:k] if doc_id in relevant)
    return hits / len(relevant)


def percentile(values: Sequence[float], p: float) -> float:
    """The ``p``-th percentile (p in [0,100]); 0.0 for an empty input."""
    if not values:
        return 0.0
    return float(np.percentile(np.asarray(values, dtype=float), p))


# ---------------------------------------------------------------------------
# Arm output normalization + per-channel diagnostics
# ---------------------------------------------------------------------------

def _normalize_ranking(raw: Any) -> Tuple[List[str], Dict[str, float]]:
    """Normalize an arm's raw output into ``(ranked_ids, scores)``.

    Accepts either a list of doc-ids, or a list of ``(doc_id, score)`` pairs /
    ``{"doc_id":..., "score":...}`` dicts. Scores are optional.
    """
    ranked: List[str] = []
    scores: Dict[str, float] = {}
    for item in raw:
        if isinstance(item, Mapping):
            doc_id = item["doc_id"]
            if "score" in item and item["score"] is not None:
                scores[doc_id] = float(item["score"])
        elif isinstance(item, (tuple, list)):
            doc_id = item[0]
            if len(item) > 1 and item[1] is not None:
                scores[doc_id] = float(item[1])
        else:
            doc_id = item
        ranked.append(doc_id)
    return ranked, scores


@dataclass
class _ChannelRun:
    """A single-channel arm's per-query ranking, used for diagnostics."""

    ranks: Dict[str, int]  # doc_id -> 1-indexed rank
    scores: Dict[str, float]


def _per_channel_diagnostics(
    fused_ids: Sequence[str],
    channels: Mapping[str, _ChannelRun],
) -> Dict[str, Dict[str, Any]]:
    """For each fused doc, attach its rank/score in each single-channel arm.

    The "lexical rank" of a fused result is simply its rank in the lexical arm's
    output — derived, not instrumented.
    """
    out: Dict[str, Dict[str, Any]] = {}
    for doc_id in fused_ids:
        entry: Dict[str, Any] = {}
        for chan in CHANNEL_ARMS:
            run = channels.get(chan)
            if run is None:
                entry[f"{chan}_rank"] = None
                entry[f"{chan}_score"] = None
            else:
                entry[f"{chan}_rank"] = run.ranks.get(doc_id)
                entry[f"{chan}_score"] = run.scores.get(doc_id)
        out[doc_id] = entry
    return out


# ---------------------------------------------------------------------------
# Holdout safety
# ---------------------------------------------------------------------------

def assert_no_holdout(consumed_query_ids: Iterable[str], holdout_ids: Iterable[str]) -> None:
    """Assert a (tuning) run did not consume any reserved holdout id.

    Raises :class:`HoldoutViolationError` naming the offending ids.
    """
    consumed = set(consumed_query_ids)
    leaked = sorted(consumed & set(holdout_ids))
    if leaked:
        raise HoldoutViolationError(
            f"tuning run touched reserved holdout ids: {leaked}"
        )


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

@dataclass
class ArmSpec:
    """An injected arm: its result callable plus cost/egress accounting.

    ``fn`` maps a query record (dict) to a ranked list of doc-ids (or
    ``(doc_id, score)`` pairs). ``inference_cost`` and ``egress`` are supplied by
    the caller — the harness never infers them.
    """

    fn: Callable[[Mapping[str, Any]], Any]
    inference_cost: float = 0.0
    egress: bool = False


class RetrievalBenchmarkHarness:
    """Evaluates injected arms over a frozen eval set at multiple depths.

    The harness performs no live retrieval; it calls each :class:`ArmSpec.fn`
    and scores the returned ranking. Per-channel diagnostics for fused arms are
    derived from the ``lexical`` and ``dense`` single-channel arms.
    """

    def __init__(self, frozen: FrozenEval, arms: Mapping[str, ArmSpec], depths: Sequence[int] = DEPTHS):
        self.frozen = frozen
        self.arms = dict(arms)
        self.depths = list(depths)

    # -- query relevance helpers -------------------------------------------

    @staticmethod
    def _relevance(query: Mapping[str, Any]) -> Dict[str, float]:
        """Graded relevance map for a query.

        Supports ``relevant`` as a {doc_id: grade} map, or ``relevant_doc_ids`` /
        ``relevant_ids`` as a list of doc ids (each graded 1).
        """
        rel = query.get("relevant")
        if isinstance(rel, Mapping):
            return {k: float(v) for k, v in rel.items()}
        ids = (
            query.get("relevant_doc_ids")
            or query.get("relevant_ids")
            or (list(rel) if rel else [])
        )
        return {doc_id: 1.0 for doc_id in ids}

    # -- the run -----------------------------------------------------------

    def run(self, split: Optional[str] = SPLIT_MAIN) -> Dict[str, Any]:
        """Run every configured arm at every depth over ``split``.

        Returns a JSON-serializable result object carrying per-arm/per-depth
        metrics, latency percentiles, cost/egress, per-channel diagnostics, the
        consumed query-id split, and the bound MANIFEST checksums.
        """
        queries = [q for q in self.frozen.queries if split is None or self.frozen.query_split(q) == split]
        consumed_ids = [q["id"] for q in queries]

        # Pass 1: run single-channel arms and cache per-query rankings so fused
        # arms can attribute per-channel ranks without any instrumentation.
        channel_cache: Dict[str, Dict[str, _ChannelRun]] = {c: {} for c in CHANNEL_ARMS}

        arm_results: Dict[str, Any] = {}
        per_channel: Dict[str, Dict[str, Any]] = {}

        # Order arms so single-channel arms run before fused arms.
        ordered = [a for a in ARMS if a in self.arms] + [a for a in self.arms if a not in ARMS]

        for arm_name in ordered:
            spec = self.arms[arm_name]
            depth_stats = {d: _DepthAccumulator(depth=d) for d in self.depths}
            latencies: List[float] = []
            errors = 0
            zero_results = 0

            for query in queries:
                qid = query["id"]
                relevance = self._relevance(query)
                relevant_ids = set(relevance.keys())

                t0 = time.perf_counter()
                try:
                    raw = spec.fn(query)
                except Exception:  # noqa: BLE001 - error rate is a measured metric
                    errors += 1
                    latencies.append((time.perf_counter() - t0) * 1000.0)
                    for d in self.depths:
                        depth_stats[d].add_error()
                    continue
                latencies.append((time.perf_counter() - t0) * 1000.0)

                ranked_ids, scores = _normalize_ranking(raw)
                if not ranked_ids:
                    zero_results += 1

                # Cache single-channel rankings for later fused attribution.
                if arm_name in CHANNEL_ARMS:
                    ranks = {doc_id: i + 1 for i, doc_id in enumerate(ranked_ids)}
                    channel_cache[arm_name][qid] = _ChannelRun(ranks=ranks, scores=scores)

                # Per-channel diagnostics for fused arms.
                if arm_name not in CHANNEL_ARMS and any(channel_cache[c] for c in CHANNEL_ARMS):
                    channels = {c: channel_cache[c].get(qid) for c in CHANNEL_ARMS}
                    channels = {c: r for c, r in channels.items() if r is not None}
                    if channels:
                        per_channel.setdefault(arm_name, {})[qid] = _per_channel_diagnostics(ranked_ids, channels)

                # Fixed-k metrics named by the frozen thresholds: computed ONCE
                # per query at their fixed cutoff, independent of candidate depth.
                ndcg_fixed = ndcg_at_k(ranked_ids, relevance, NDCG_FIXED_K)
                recall_fixed = recall_at_k(ranked_ids, relevant_ids, RECALL_FIXED_K)
                rr = reciprocal_rank(ranked_ids, relevant_ids)

                for d in self.depths:
                    depth_stats[d].add(
                        ndcg_fixed=ndcg_fixed,
                        recall_fixed=recall_fixed,
                        ndcg_depth=ndcg_at_k(ranked_ids, relevance, d),
                        recall_depth=recall_at_k(ranked_ids, relevant_ids, d),
                        rr=rr,
                        zero_result=(len(ranked_ids) == 0),
                    )

            n = len(queries)
            arm_results[arm_name] = {
                "egress": bool(spec.egress),
                "inference_cost": float(spec.inference_cost),
                "error_rate": (errors / n) if n else 0.0,
                "zero_result_rate": (zero_results / n) if n else 0.0,
                "latency_p50_ms": percentile(latencies, 50),
                "latency_p95_ms": percentile(latencies, 95),
                "depths": {str(d): depth_stats[d].summary() for d in self.depths},
            }

        result: Dict[str, Any] = {
            "schema": "retrieval_eval_result.v1",
            "split": split,
            "consumed_query_ids": consumed_ids,
            "n_queries": len(queries),
            "arms": arm_results,
            "per_channel": per_channel,
            "holdout_ids": sorted(self.frozen.holdout_ids),
            # Bound checksums make a result traceable to the frozen dataset.
            **self.frozen.checksums(),
            "review": self.frozen.manifest.get("review", {}),
        }
        return result


@dataclass
class _DepthAccumulator:
    """Accumulates metric values for one candidate depth across queries.

    Two families of metric are tracked and reported under EXPLICIT, distinct
    keys so nothing is mislabeled:

    * Fixed-k metrics named by the frozen gate thresholds — ``ndcg@10`` and
      ``recall@50`` — computed at their fixed cutoff regardless of this
      accumulator's candidate ``depth``. These are what the gate compares
      against ``min_quality.ndcg@10`` / ``recall@50``.
    * Per-depth metrics — ``ndcg@{depth}`` and ``recall@{depth}`` — the quality
      at this accumulator's candidate depth, kept for diagnostics.

    ``mrr`` is depth-independent (reciprocal rank scans the full ranking).
    """

    depth: int
    ndcg_fixed: List[float] = field(default_factory=list)
    recall_fixed: List[float] = field(default_factory=list)
    ndcg_depth: List[float] = field(default_factory=list)
    recall_depth: List[float] = field(default_factory=list)
    rrs: List[float] = field(default_factory=list)
    zero_results: int = 0
    errors: int = 0

    def add(
        self,
        ndcg_fixed: float,
        recall_fixed: float,
        ndcg_depth: float,
        recall_depth: float,
        rr: float,
        zero_result: bool,
    ) -> None:
        self.ndcg_fixed.append(ndcg_fixed)
        self.recall_fixed.append(recall_fixed)
        self.ndcg_depth.append(ndcg_depth)
        self.recall_depth.append(recall_depth)
        self.rrs.append(rr)
        if zero_result:
            self.zero_results += 1

    def add_error(self) -> None:
        self.errors += 1

    def summary(self) -> Dict[str, float]:
        def mean(xs: List[float]) -> float:
            return float(np.mean(xs)) if xs else 0.0

        scored = len(self.ndcg_fixed)
        total = scored + self.errors
        return {
            # Fixed-k metrics the gate thresholds name (depth-independent).
            NDCG_FIXED_KEY: mean(self.ndcg_fixed),
            RECALL_FIXED_KEY: mean(self.recall_fixed),
            # Per-depth metrics at this accumulator's candidate depth.
            f"ndcg@{self.depth}": mean(self.ndcg_depth),
            f"recall@{self.depth}": mean(self.recall_depth),
            "mrr": mean(self.rrs),
            "zero_result_rate": (self.zero_results / total) if total else 0.0,
            "error_rate": (self.errors / total) if total else 0.0,
            "n_scored": scored,
        }
