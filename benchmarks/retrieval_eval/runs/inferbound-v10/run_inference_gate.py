#!/usr/bin/env python3
"""INFERGATE rollout-gate run (IF-0-INFERGATE-1).

Reproducible driver for the retrieval-rollout gate. It:

1. Loads and *verifies* the BENCHFREEZE-frozen eval set (the freeze gate).
2. Reconstructs the frozen corpus path list from the pinned commit and asserts
   its ``corpus_sha256`` matches ``corpus_manifest.json`` / ``MANIFEST.json``.
3. Probes for live inference services: Qdrant :6333 (TCP), the embedding
   endpoint (TCP), and — crucially — a *functional* rerank probe that POSTs a
   minimal ``rerank.v1`` request and requires a contract-valid response. TCP
   reachability alone is not enough for the reranker.
4. Runs only the arms that can actually run:
     * ``lexical`` — a real, reproducible BM25-lite ranker over the frozen
       corpus file *paths + names* (NOT file contents). This never sends source
       text off-host, so it trivially satisfies the zero-egress bound.
     * ``dense`` / ``hybrid`` — recorded ``not_run`` with a reason when the live
       embedding provider or Qdrant is unreachable.
     * ``hybrid_rerank`` — additionally gated on the functional rerank probe: if
       the rerank endpoint is down (or not speaking ``rerank.v1``) it is recorded
       ``not_run`` rather than run as an arm-with-errors, so the gate's decisive
       arm is never scored against a dead reranker. When it *does* run, the
       reranker candidate text is the retrieved **document content** (loaded from
       the pinned corpus commit), not just file paths. No numbers are invented.
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
import os
import re
import socket
import subprocess
from collections import Counter
from functools import lru_cache
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


@lru_cache(maxsize=None)
def load_doc_content(commit: str, path: str, max_chars: int = 4000) -> str:
    """Read a corpus document's *content* from the pinned corpus commit.

    Used as reranker candidate text so ``hybrid_rerank`` reranks on real document
    bodies, not file paths. Content is read from ``git show <commit>:<path>`` so
    it comes from the exact frozen corpus revision (not the working tree), and is
    truncated to bound the request size. Memoized so repeated candidates across
    queries do not re-shell out.
    """
    try:
        out = subprocess.run(
            ["git", "show", f"{commit}:{path}"],
            capture_output=True, text=True, check=True,
        ).stdout
    except subprocess.CalledProcessError:
        return ""
    return out[:max_chars]


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


def rerank_probe(rerank_url: str, timeout: float = 5.0) -> bool:
    """Functional probe of the RERANK endpoint (not a bare TCP connect).

    POSTs a minimal, well-formed ``rerank.v1`` request (one candidate) and
    requires a *contract-valid* response that echoes the candidate id. A rerank
    endpoint that is TCP-reachable but does not actually speak ``rerank.v1``
    (wrong shape, error status, dropped candidate) fails this probe, so
    ``hybrid_rerank`` is never scored against a reranker that cannot serve the
    contract. All imports are lazy so the offline down-path stays dependency-free.
    """
    import json as _json
    import urllib.request as _urlreq

    from mcp_server.interfaces.rerank_contracts import (
        RerankCandidate,
        RerankRequest,
        RerankResponse,
        validate_rerank_response,
    )

    request = RerankRequest(
        request_id="probe-rerank",
        query="rerank endpoint health probe",
        candidates=[
            RerankCandidate(candidate_id="cand-0", text="rerank endpoint health probe candidate")
        ],
        top_k=1,
    )
    try:
        body = _json.dumps(request.to_dict()).encode()
        req = _urlreq.Request(
            rerank_url, data=body, headers={"Content-Type": "application/json"}
        )
        with _urlreq.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - operator endpoint
            raw = _json.loads(resp.read().decode())
        response = RerankResponse.from_dict(raw)
        validate_rerank_response(request, response)
        return True
    except Exception:  # noqa: BLE001 - any failure means "not functionally up"
        return False


def not_run_reason(embed_up: bool, qdrant_up: bool, host: str, port: int) -> str:
    """Truthful, probe-derived reason string for the arms that could not run.

    The reason names *which* service was unreachable (never a hardcoded claim),
    so the artifact never asserts a service is down when a probe says it is up.
    """
    missing: List[str] = []
    if not embed_up:
        missing.append(f"embedding endpoint {host}:{port} unreachable")
    if not qdrant_up:
        missing.append("Qdrant localhost:6333 unreachable")
    return (
        "live inference services not fully reachable "
        f"({'; '.join(missing) or 'no service reachable'}). "
        "Dense/fused arms require query+corpus embeddings"
        + (" and a Qdrant vector search" if not qdrant_up else "")
        + ", so they cannot be scored without inventing numbers "
        f"(probe state: embedding_up={embed_up}, qdrant_up={qdrant_up})."
    )


def rerank_not_run_reason(rerank_url: str) -> str:
    """Reason for ``hybrid_rerank`` when embeddings+Qdrant are up but the rerank
    endpoint fails its functional probe.

    Recorded as ``not_run`` (not a ran-arm-with-errors) so the gate's decisive
    arm is never scored against a reranker that cannot serve ``rerank.v1``.
    """
    return (
        "embedding endpoint and Qdrant are reachable, but the rerank endpoint "
        f"{rerank_url} did not pass the functional rerank.v1 probe (endpoint down "
        "or not speaking the rerank wire contract). hybrid_rerank is the arm the "
        "gate decision hinges on, so it is recorded not_run rather than run with "
        "errors — no invented rerank scores."
    )


def build_provider_arms(
    corpus: List[str],
    ranker: "BM25PathRanker",
    *,
    embed_base_url: str,
    embed_model: str,
    embed_api_key: str,
    embed_dim: int,
    qdrant_host: str,
    qdrant_port: int,
    collection: str,
    rerank_url: str,
    corpus_commit: str,
    top_k: int,
    include_rerank: bool = True,
) -> Dict[str, ArmSpec]:
    """Construct the LIVE ``dense`` / ``hybrid`` / ``hybrid_rerank`` arms.

    Every embedding/qdrant/reranker import happens lazily inside this function so
    the offline down-path (this environment) never touches those optional heavy
    dependencies — the driver still imports and produces an artifact when the
    services are down. This is only called when BOTH the embedding endpoint and
    Qdrant probes report up.

    * ``dense`` — embed the query via the OpenAI-compatible provider, then Qdrant
      vector search; map hits back to corpus-relative doc ids.
    * ``hybrid`` — reciprocal-rank fusion of the lexical and dense rankings.
    * ``hybrid_rerank`` — the hybrid candidates reranked via ``EndpointReranker``
      over the ``rerank.v1`` wire contract, using each candidate's **document
      content** (from the pinned corpus commit) as the reranker text — not the
      file path. Only constructed when ``include_rerank`` is True (i.e. the
      functional rerank probe passed).

    All arms are private-endpoint (non-commercial) egress: ``egress=False``.
    """
    import json as _json
    import urllib.request as _urlreq

    from qdrant_client import QdrantClient

    from mcp_server.indexer.reranker import (
        EndpointReranker,
        SearchResult,
        run_coroutine_sync,
    )
    from mcp_server.utils.embedding_providers import create_embedding_provider

    provider = create_embedding_provider(
        "openai_compatible",
        embed_model,
        embed_dim,
        api_key=embed_api_key,
        base_url=embed_base_url,
    )
    client = QdrantClient(host=qdrant_host, port=qdrant_port)

    def _embed_query(text: str) -> List[float]:
        return provider.embed([text], input_type="query")[0]

    def _dense_hits(text: str, limit: int) -> List[tuple]:
        vector = _embed_query(text)
        hits = client.search(collection_name=collection, query_vector=vector, limit=limit)
        out: List[tuple] = []
        for hit in hits:
            payload = dict(getattr(hit, "payload", None) or {})
            doc = payload.get("relative_path") or payload.get("file")
            if doc:
                out.append((doc, float(getattr(hit, "score", 0.0))))
        return out

    def dense_arm(query: Mapping[str, Any]) -> List[tuple]:
        return _dense_hits(query["query"], top_k)

    def _rrf(rankings: List[List[str]], k: int = 60) -> List[str]:
        scores: Dict[str, float] = {}
        for ranking in rankings:
            for rank, doc in enumerate(ranking):
                scores[doc] = scores.get(doc, 0.0) + 1.0 / (k + rank + 1)
        return [d for d, _ in sorted(scores.items(), key=lambda x: (-x[1], x[0]))]

    def hybrid_arm(query: Mapping[str, Any]) -> List[str]:
        lex = ranker.rank(query["query"])[:top_k]
        dense = [doc for doc, _ in _dense_hits(query["query"], top_k)]
        return _rrf([lex, dense])

    arms: Dict[str, ArmSpec] = {
        "dense": ArmSpec(fn=dense_arm, inference_cost=0.0, egress=False),
        "hybrid": ArmSpec(fn=hybrid_arm, inference_cost=0.0, egress=False),
    }

    if include_rerank:
        def _transport(request: Dict[str, Any]) -> Dict[str, Any]:
            body = _json.dumps(request).encode()
            req = _urlreq.Request(
                rerank_url, data=body, headers={"Content-Type": "application/json"}
            )
            with _urlreq.urlopen(req, timeout=30) as resp:  # noqa: S310 - operator endpoint
                return _json.loads(resp.read().decode())

        reranker = EndpointReranker(_transport, provider="endpoint")

        def hybrid_rerank_arm(query: Mapping[str, Any]) -> List[str]:
            fused = hybrid_arm(query)[:top_k]
            results = []
            for doc in fused:
                # Reranker candidate text is the retrieved DOCUMENT CONTENT (read
                # from the pinned corpus commit), not the file path. file_path is
                # kept for mapping the reranked order back to corpus doc ids.
                content = load_doc_content(corpus_commit, doc)
                results.append(
                    SearchResult(
                        file_path=doc,
                        start_line=1,
                        end_line=1,
                        column=0,
                        snippet=content or doc,
                        match_type="semantic",
                        score=0.0,
                        context=None,
                    )
                )
            outcome = run_coroutine_sync(reranker.rerank(query["query"], results, top_k=top_k))
            rr = getattr(outcome, "data", outcome)
            return [item.original_result.file_path for item in rr.results]

        arms["hybrid_rerank"] = ArmSpec(fn=hybrid_rerank_arm, inference_cost=0.0, egress=False)

    return arms


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
        # Compare like-for-like: the gate names FIXED-k metrics (ndcg@10 /
        # recall@50), so read those exact keys from the summary rather than the
        # candidate-depth values. mrr is depth-independent.
        for metric in ("ndcg@10", "mrr", "recall@50"):
            floor = need(metric)
            if floor is None:
                continue
            val = dstats[metric]
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
    embed_host = os.environ.get("SEMANTIC_EMBEDDING_HOST", "ai")
    embed_port = int(os.environ.get("SEMANTIC_EMBEDDING_PORT", "8001"))
    embed_up = probe(embed_host, embed_port)
    rerank_url = os.environ.get(
        "RERANK_ENDPOINT_URL", f"http://{embed_host}:{embed_port}/rerank"
    )
    # Functional (not TCP-only) rerank probe: the reranker must actually serve
    # the rerank.v1 wire contract for hybrid_rerank to be eligible to run.
    rerank_up = rerank_probe(rerank_url)

    # --- lexical arm (runnable offline) ---
    ranker = BM25PathRanker(corpus)
    arms: Dict[str, ArmSpec] = {
        "lexical": ArmSpec(fn=lambda q: ranker.rank(q["query"]), inference_cost=0.0, egress=False)
    }

    # --- provider arms: dense/hybrid RUN iff the embedding endpoint AND Qdrant
    # are both reachable; hybrid_rerank ADDITIONALLY requires the functional
    # rerank probe to pass. Any arm that cannot run gets a truthful, probe-derived
    # not_run reason. Arms are never unconditionally marked not_run.
    not_run: Dict[str, str] = {}
    provider_ready = embed_up and qdrant_up           # dense + hybrid
    rerank_ready = provider_ready and rerank_up        # hybrid_rerank
    if provider_ready:
        base_url = os.environ.get("SEMANTIC_EMBEDDING_BASE_URL") or os.environ.get(
            "OPENAI_API_BASE", f"http://{embed_host}:{embed_port}/v1"
        )
        try:
            arms.update(
                build_provider_arms(
                    corpus,
                    ranker,
                    embed_base_url=base_url,
                    embed_model=os.environ.get("SEMANTIC_EMBEDDING_MODEL", "voyage-code-3"),
                    embed_api_key=os.environ.get("OPENAI_API_KEY", "vllm-local"),
                    embed_dim=int(os.environ.get("SEMANTIC_VECTOR_DIMENSION", "1024")),
                    qdrant_host="localhost",
                    qdrant_port=6333,
                    collection=os.environ.get("SEMANTIC_COLLECTION_NAME", "code-embeddings"),
                    rerank_url=rerank_url,
                    corpus_commit=frozen.corpus_manifest["commit"],
                    top_k=100,
                    include_rerank=rerank_ready,
                )
            )
        except Exception as exc:  # noqa: BLE001 - honest failure record, not invented metrics
            reason = (
                "embedding endpoint and Qdrant probes reported up, but live "
                f"provider/reranker construction failed: {type(exc).__name__}: {exc}"
            )
            for a in PROVIDER_ARMS:
                not_run[a] = reason
        else:
            # dense/hybrid ran; hybrid_rerank only if the functional rerank probe
            # passed. Otherwise record it not_run (dead reranker != ran-with-errors).
            if not rerank_ready:
                not_run["hybrid_rerank"] = rerank_not_run_reason(rerank_url)
    else:
        reason = not_run_reason(embed_up, qdrant_up, embed_host, embed_port)
        for a in PROVIDER_ARMS:
            not_run[a] = reason

    # main == non-holdout split, per the frozen decision algorithm.
    harness = RetrievalBenchmarkHarness(frozen, arms)
    run = harness.run(split="main")

    arm_notes = {
        "lexical": (
            "BM25-lite over corpus file paths+names only (not file contents); "
            "weaker than full-text BM25. Zero source-text egress by construction."
        ),
        "dense": (
            "Dense retrieval: query embedded via the private OpenAI-compatible "
            "endpoint, then Qdrant vector search. Private-endpoint (non-commercial) "
            "egress."
        ),
        "hybrid": "Reciprocal-rank fusion of the lexical and dense rankings.",
        "hybrid_rerank": (
            "Hybrid candidates reranked via EndpointReranker (rerank.v1), using "
            "retrieved DOCUMENT CONTENT (from the pinned corpus commit) as the "
            "reranker candidate text, not file paths. Gated on a functional "
            "rerank.v1 endpoint probe. Private-endpoint (non-commercial) egress."
        ),
    }
    arms_ran = {
        name: {
            "metrics": metrics,
            "predicate_eval": evaluate_arm_predicates(name, metrics, frozen.thresholds),
            "note": arm_notes.get(name, ""),
        }
        for name, metrics in run["arms"].items()
    }
    lexical_eval = arms_ran["lexical"]["predicate_eval"]
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
            f"embedding_endpoint_{embed_host}_{embed_port}": embed_up,
            "rerank_endpoint_functional": rerank_up,
        },
        "split_evaluated": "main",
        "holdout_used_for_tuning": False,
        "holdout_ids": sorted(frozen.holdout_ids),
        "n_queries_main": run["n_queries"],
        "arms_ran": arms_ran,
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
