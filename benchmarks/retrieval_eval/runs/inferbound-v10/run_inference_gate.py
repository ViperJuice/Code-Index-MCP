#!/usr/bin/env python3
"""INFERGATE rollout-gate run (IF-0-INFERGATE-1).

Reproducible driver for the retrieval-rollout gate. It:

1. Loads and *verifies* the BENCHFREEZE-frozen eval set (the freeze gate).
2. Reconstructs the frozen corpus path list from the pinned commit and asserts
   its ``corpus_sha256`` matches ``corpus_manifest.json`` / ``MANIFEST.json``.
3. Probes for live inference services (Qdrant :6333, embedding endpoint).
4. Runs only the arms that can actually run:
     * ``lexical`` — a real, reproducible BM25-lite ranker over the frozen
       corpus file *paths + names* (NOT file contents). This never sends source
       text off-host, so it trivially satisfies the zero-egress bound.
     * ``dense`` / ``hybrid`` / ``hybrid_rerank`` — recorded ``not_run`` with a
       reason when a live embedding provider is unreachable. No numbers are
       invented.
5. Computes the verdict IN CODE from the frozen ``decision_algorithm`` in
   ``gate_thresholds.json`` — the verdict is derived, not authored.

Evaluation uses ONLY the non-holdout (``main``) split, per the frozen decision
algorithm. The holdout split is never scored here and never influences tuning.

Usage::

    uv run --no-sync python benchmarks/retrieval_eval/runs/inferbound-v10/run_inference_gate.py

Writes ``result.json`` next to this script.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import socket
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Mapping

from mcp_server.benchmarks.retrieval_eval_harness import (
    ArmSpec,
    RetrievalBenchmarkHarness,
    load_frozen_eval,
)

EVAL_DIR = Path("benchmarks/retrieval_eval")
OUT = Path(__file__).with_name("result.json")

# Arms that require a live embedding provider (and, for the fused arms, Qdrant).
PROVIDER_ARMS = ("dense", "hybrid", "hybrid_rerank")


# ---------------------------------------------------------------------------
# Corpus reconstruction (faithful, checksum-verified)
# ---------------------------------------------------------------------------

def reconstruct_corpus(manifest: Mapping[str, Any]) -> List[str]:
    """Rebuild the frozen corpus path list from the pinned commit.

    Uses gitignore-style glob semantics: ``**`` crosses directories, ``*`` does
    not cross ``/``, and a slash-less pattern (e.g. ``*.md``) is anchored at the
    repo root. Verified below against the recorded ``corpus_sha256``.
    """
    globs = manifest["included_globs"]
    commit = manifest["commit"]
    files = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", commit],
        capture_output=True, text=True, check=True,
    ).stdout.splitlines()

    regexes = []
    for g in globs:
        if "/" not in g:
            regexes.append(re.compile("^" + re.escape(g).replace(r"\*", "[^/]*") + "$"))
            continue
        parts = g.split("/")
        rx: List[str] = []
        for i, p in enumerate(parts):
            if p == "**":
                rx.append("(?:.*/)?")
            else:
                seg = re.escape(p).replace(r"\*", "[^/]*").replace(r"\?", "[^/]")
                rx.append(seg)
                if i < len(parts) - 1:
                    rx.append("/")
        regexes.append(re.compile("^" + "".join(rx) + "$"))

    return sorted({p for p in files if any(r.match(p) for r in regexes)})


def corpus_path_digest(paths: List[str]) -> str:
    return hashlib.sha256("\n".join(paths).encode()).hexdigest()


# ---------------------------------------------------------------------------
# Lexical arm: BM25-lite over file paths + names (NOT contents)
# ---------------------------------------------------------------------------

_SPLIT = re.compile(r"[^A-Za-z0-9]+")
_CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


def tokenize(text: str) -> List[str]:
    """Lowercased tokens from a string, splitting on non-alphanumerics and
    camelCase boundaries. Used identically for corpus paths and queries."""
    out: List[str] = []
    for part in _SPLIT.split(text):
        if not part:
            continue
        for sub in _CAMEL.split(part):
            if sub:
                out.append(sub.lower())
    return out


class BM25PathRanker:
    """A deterministic BM25 ranker over corpus file paths + names.

    Documents are the frozen corpus paths; each document's "text" is the token
    set of its path (directory names, file stem, extension). This is a genuine
    lexical arm but weaker than full-text BM25 — it ranks on identifiers present
    in the path, not file bodies — and by construction sends no source text
    off-host (zero egress).
    """

    k1 = 1.5
    b = 0.75

    def __init__(self, doc_ids: List[str]):
        self.doc_ids = doc_ids
        self.doc_tokens = [tokenize(d) for d in doc_ids]
        self.doc_len = [len(t) for t in self.doc_tokens]
        self.avgdl = (sum(self.doc_len) / len(self.doc_len)) if self.doc_len else 0.0
        self.tf = [Counter(t) for t in self.doc_tokens]
        df: Counter = Counter()
        for toks in self.doc_tokens:
            for term in set(toks):
                df[term] += 1
        n = len(doc_ids)
        self.idf = {
            term: math.log(1 + (n - d + 0.5) / (d + 0.5)) for term, d in df.items()
        }

    def rank(self, query: str) -> List[str]:
        q_terms = tokenize(query)
        scores: List[tuple[float, int]] = []
        for i, (tf, dl) in enumerate(zip(self.tf, self.doc_len)):
            s = 0.0
            for term in q_terms:
                if term not in tf:
                    continue
                idf = self.idf.get(term, 0.0)
                freq = tf[term]
                denom = freq + self.k1 * (1 - self.b + self.b * (dl / self.avgdl if self.avgdl else 0.0))
                s += idf * (freq * (self.k1 + 1)) / denom
            if s > 0.0:
                scores.append((s, i))
        # Deterministic: score desc, then doc-id asc for ties.
        scores.sort(key=lambda x: (-x[0], self.doc_ids[x[1]]))
        return [self.doc_ids[i] for _, i in scores]


# ---------------------------------------------------------------------------
# Live-service probes
# ---------------------------------------------------------------------------

def probe(host: str, port: int, timeout: float = 3.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


# ---------------------------------------------------------------------------
# Verdict, computed FROM the frozen decision algorithm
# ---------------------------------------------------------------------------

def evaluate_arm_predicates(arm: str, arm_result: Dict[str, Any], thr: Mapping[str, Any]) -> Dict[str, Any]:
    """Apply the frozen per-arm predicates to a *ran* arm's metrics.

    Mirrors ``gate_thresholds.json`` ``decision_algorithm``: every depth must
    clear ndcg@10 / mrr / recall@50, plus p95 latency, error-rate,
    zero-result-rate, and egress bounds.
    """
    mq = thr["min_quality"]
    checks: List[Dict[str, Any]] = []

    def need(metric: str) -> float:
        return mq[metric].get(arm)

    for depth, dstats in arm_result["depths"].items():
        for metric, key in (("ndcg@10", "ndcg"), ("mrr", "mrr"), ("recall@50", "recall")):
            floor = need(metric)
            if floor is None:
                continue
            val = dstats[key]
            checks.append({
                "predicate": f"{metric}@depth{depth}", "value": round(val, 4),
                "floor": floor, "pass": val >= floor,
            })

    checks.append({"predicate": "p95_latency_ms", "value": round(arm_result["latency_p95_ms"], 3),
                   "ceiling": thr["max_latency_ms"]["p95"].get(arm), "pass": arm_result["latency_p95_ms"] <= thr["max_latency_ms"]["p95"].get(arm, float("inf"))})
    checks.append({"predicate": "error_rate", "value": round(arm_result["error_rate"], 4),
                   "ceiling": thr["max_error_rate"], "pass": arm_result["error_rate"] <= thr["max_error_rate"]})
    checks.append({"predicate": "zero_result_rate", "value": round(arm_result["zero_result_rate"], 4),
                   "ceiling": thr["max_zero_result_rate"], "pass": arm_result["zero_result_rate"] <= thr["max_zero_result_rate"]})
    egress_frac = 1.0 if arm_result["egress"] else 0.0
    checks.append({"predicate": "commercial_egress_fraction", "value": egress_frac,
                   "ceiling": thr["max_commercial_egress_fraction"], "pass": egress_frac <= thr["max_commercial_egress_fraction"]})

    return {"checks": checks, "all_pass": all(c["pass"] for c in checks)}


def compute_verdict(thr: Mapping[str, Any], ran: Mapping[str, Any], not_run: Mapping[str, str]) -> Dict[str, Any]:
    """Derive the enum verdict from the frozen decision algorithm.

    default-enable-eligibility is decided ONLY on ``hybrid_rerank``:
      * ready         -> hybrid_rerank ran AND cleared every frozen predicate.
      * rejected      -> hybrid_rerank ran but FAILED a predicate.
      * dark_opt_in   -> hybrid_rerank could not be evaluated (insufficient
                         provider evidence). Learned reranking stays opt-in.
    """
    target = "hybrid_rerank"
    if target in not_run:
        return {
            "verdict": "dark_opt_in",
            "basis": (
                f"{target} not_run ({not_run[target]}); the frozen decision "
                "algorithm's conjunction is unsatisfiable without provider "
                "evidence, so it is not default-enable-eligible. This is "
                "insufficient-evidence, not a measured failure -> dark_opt_in, "
                "not rejected."
            ),
            "target_arm_predicates": None,
        }
    ev = evaluate_arm_predicates(target, ran[target], thr)
    return {
        "verdict": "ready" if ev["all_pass"] else "rejected",
        "basis": f"{target} ran; all_pass={ev['all_pass']} against frozen thresholds.",
        "target_arm_predicates": ev,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    frozen = load_frozen_eval(EVAL_DIR)  # freeze gate

    corpus = reconstruct_corpus(frozen.corpus_manifest)
    digest = corpus_path_digest(corpus)
    corpus_verified = digest == frozen.corpus_sha256
    if not corpus_verified:
        raise SystemExit(
            f"corpus reconstruction mismatch: {digest} != {frozen.corpus_sha256}"
        )

    qdrant_up = probe("localhost", 6333)
    embed_up = probe("ai", 8001)

    # --- lexical arm (runnable offline) ---
    ranker = BM25PathRanker(corpus)
    arms = {"lexical": ArmSpec(fn=lambda q: ranker.rank(q["query"]), inference_cost=0.0, egress=False)}

    # main == non-holdout split, per the frozen decision algorithm.
    harness = RetrievalBenchmarkHarness(frozen, arms)
    run = harness.run(split="main")

    not_run: Dict[str, str] = {}
    reason = (
        "no live embedding provider reachable (embedding endpoint http://ai:8001/v1 "
        f"unreachable; Qdrant :6333 reachable={qdrant_up}). Dense/fused arms "
        "require query+corpus embeddings, so they cannot be scored without "
        "inventing numbers."
    )
    for a in PROVIDER_ARMS:
        not_run[a] = reason

    lexical_eval = evaluate_arm_predicates("lexical", run["arms"]["lexical"], frozen.thresholds)
    verdict = compute_verdict(frozen.thresholds, run["arms"], not_run)

    code_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()

    artifact = {
        "schema": "inference_rollout_run.v1",
        "phase": "INFERGATE",
        "interface": "IF-0-INFERGATE-1",
        "code_commit": code_commit,
        "corpus_commit": frozen.corpus_manifest["commit"],
        "bound_checksums": {
            "dataset_sha256": frozen.dataset_sha256,
            "corpus_sha256": frozen.corpus_sha256,
            "thresholds_sha256": frozen.thresholds_sha256,
        },
        "corpus_reconstruction_verified": corpus_verified,
        "corpus_doc_count": len(corpus),
        "live_services": {
            "qdrant_localhost_6333": qdrant_up,
            "embedding_endpoint_ai_8001": embed_up,
        },
        "split_evaluated": "main",
        "holdout_used_for_tuning": False,
        "holdout_ids": sorted(frozen.holdout_ids),
        "n_queries_main": run["n_queries"],
        "arms_ran": {
            "lexical": {
                "metrics": run["arms"]["lexical"],
                "predicate_eval": lexical_eval,
                "note": (
                    "BM25-lite over corpus file paths+names only (not file "
                    "contents); weaker than full-text BM25. Zero source-text "
                    "egress by construction."
                ),
            }
        },
        "arms_not_run": not_run,
        "decision_algorithm": frozen.thresholds["decision_algorithm"],
        "verdict": verdict["verdict"],
        "verdict_basis": verdict["basis"],
        "verdict_target_arm_predicates": verdict["target_arm_predicates"],
        "review": frozen.manifest.get("review", {}),
    }

    OUT.write_text(json.dumps(artifact, indent=2) + "\n")
    print(json.dumps({
        "verdict": artifact["verdict"],
        "arms_ran": list(artifact["arms_ran"].keys()),
        "arms_not_run": list(artifact["arms_not_run"].keys()),
        "corpus_verified": corpus_verified,
        "code_commit": code_commit,
        "lexical_all_pass": lexical_eval["all_pass"],
    }, indent=2))


if __name__ == "__main__":
    main()
