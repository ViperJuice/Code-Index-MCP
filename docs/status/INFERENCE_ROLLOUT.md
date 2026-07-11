# Inference / Retrieval Rollout Gate — Verdict Report

Phase: **INFERGATE** (roadmap-v10 Phase 7) · Interface: **IF-0-INFERGATE-1**

This report records the retrieval-rollout gate verdict. The verdict is
**computed in code from the BENCHFREEZE-frozen `decision_algorithm`** in
`benchmarks/retrieval_eval/gate_thresholds.json`, not authored here. No
thresholds were changed and no numbers were tuned as part of this phase.

## Verdict

```
verdict: dark_opt_in
```

Allowed enum: `ready` | `dark_opt_in` | `rejected`.

**`dark_opt_in`** — the gate is **NOT passed** due to **insufficient provider
evidence**. Learned reranking (`hybrid_rerank`) therefore **remains DARK /
OPT-IN** and is **not** default-enabled. This is the correct, roadmap-compliant
outcome: reranking stays opt-in until the predeclared gate passes.

### Why `dark_opt_in` and not `rejected`

The frozen `decision_algorithm` decides default-enable-eligibility solely on the
`hybrid_rerank` arm: it must clear ndcg@10, mrr, and recall@50 at **every**
depth (20/50/100) plus the latency/error/zero-result/egress bounds. In this
environment the live embedding endpoint (`http://ai:8001/v1`) is unreachable, so
`hybrid_rerank` (and `dense`/`hybrid`) **could not be run at all**. The
conjunction is unsatisfiable without provider evidence, so the arm is not
default-enable-eligible. Because the target arm was **never measured** (not
measured-and-failed), the honest verdict is `dark_opt_in` (insufficient
evidence), which is distinct from `rejected` (arm ran and missed a threshold).

## Arms: ran vs not_run

| Arm | Status | Notes |
| --- | --- | --- |
| `lexical` | **ran** | BM25-lite over the frozen corpus file **paths + names** (not file contents). Real, reproducible, offline. Zero source-text egress by construction. |
| `dense` | **not_run** | No live embedding provider reachable — see reason below. |
| `hybrid` | **not_run** | No live embedding provider reachable. |
| `hybrid_rerank` | **not_run** | No live embedding provider reachable; and, independently, the rerank endpoint failed its functional probe. This is the arm the gate decision hinges on. |

**not_run reason (dense / hybrid / hybrid_rerank):** no live embedding provider
reachable — the embedding endpoint `http://ai:8001/v1` was unreachable at run
time. (Qdrant `localhost:6333` was reachable, but that alone cannot produce
query/corpus embeddings.) Dense and fused arms require embeddings, so they are
recorded `not_run` rather than assigned invented metrics.

### Provider-run validity (how the arms are gated when services ARE up)

The driver does not treat TCP reachability as sufficient evidence a provider run
is valid. Two hardening rules apply when services come up:

- **Functional rerank probe.** `hybrid_rerank` (the decisive arm) is gated on a
  *functional* `rerank.v1` probe — the driver POSTs a minimal request and
  requires a contract-valid response, not merely an open socket. If the rerank
  endpoint is down or does not speak the wire contract, `hybrid_rerank` is
  recorded **`not_run`** (insufficient evidence) rather than run as an
  arm-with-errors against a dead reranker. `dense`/`hybrid` remain gated on the
  embedding endpoint + Qdrant. The run records three service states:
  `qdrant_localhost_6333`, `embedding_endpoint_<host>_<port>`, and
  `rerank_endpoint_functional`.
- **Reranker candidate text = document content.** When `hybrid_rerank` runs, the
  reranker scores each candidate on the retrieved **document content** (read from
  the pinned corpus commit via `git show <commit>:<path>`, truncated to bound
  request size), not on file paths. Paths are retained only to map the reranked
  order back to corpus doc ids.

In **this** environment the embedding endpoint is down and the functional rerank
probe fails, so all three provider arms stay `not_run` and the verdict stays
`dark_opt_in`. That is the expected offline outcome.

### Precondition for a LIVE provider run to count

A live provider run cannot be validated in this offline environment, and its
numbers do **not** count toward the gate until an additional precondition is
met: **the live Qdrant collection must be verified against the frozen corpus
before scoring.** Specifically, a live run must confirm the collection's indexed
**commit**, **corpus checksum** (`corpus_sha256`), **profile fingerprint**, and
**provider revision** match the frozen corpus this gate binds (`corpus_commit`
`f7c060b…`, `corpus_sha256` above). A collection indexed against a different
commit, corpus, embedding profile, or provider revision would make dense/hybrid/
hybrid_rerank metrics unattributable to the frozen eval set, so such a run is
**invalid** and its verdict must not be recorded as gate evidence. This is a
stated gate precondition, not an implementation detail: numbers from an
unverified live collection are out of contract.

## Metrics produced (lexical arm only)

Evaluated on the **non-holdout (`main`) split only** — 40 queries — against the
frozen corpus (872 documents). Numbers are reported **as-is**; the ranker was
**not** iterated to clear any threshold.

The gate compares against **fixed-k** metrics — the exact cutoffs the frozen
thresholds name (`ndcg@10`, `recall@50`), computed at k=10 / k=50 **independent
of the candidate depth**. (An earlier harness scored ndcg/recall at the
candidate depth `d` and then labeled the depth-20 value `ndcg@10`; the fixed-k
metrics below remove that mislabeling and are what the gate now reads.)

| Metric (fixed-k) | Value | Floor (lexical) | Clears |
| --- | --- | --- | --- |
| ndcg@10 | 0.3699 | 0.30 | yes |
| recall@50 | 0.6875 | 0.60 | yes |
| mrr | 0.3290 | 0.35 | **no** |

Per-depth diagnostics are retained under their **true** names (`ndcg@d` /
`recall@d`) — never relabeled as the fixed-k metrics:

| Candidate depth d | ndcg@d | recall@d |
| --- | --- | --- |
| 20 | 0.3838 | 0.6125 |
| 50 | 0.4011 | 0.6875 |
| 100 | 0.4035 | 0.7000 |

p95 latency: 0.86 ms · error rate: 0.0 · zero-result rate: 0.0 · commercial
egress fraction: 0.0.

The lexical arm clears its frozen ndcg@10 (0.3699 ≥ 0.30) and recall@50
(0.6875 ≥ 0.60) floors and all operational/egress bounds, but its mrr (0.329) is
**below** the lexical mrr floor (0.35). This is reported honestly and **does not
move the verdict** —
the gate decision is about `hybrid_rerank` default-enablement, not the lexical
arm, and the lexical arm ranks path tokens only (weaker than full-text BM25).

## Bound hashes (traceability)

Frozen-dataset checksums, copied from
`benchmarks/retrieval_eval/MANIFEST.json` and re-verified against file bytes by
the freeze gate (`load_frozen_eval`):

- `dataset_sha256`: `62263e2d2ddcedea2e464cc56d913d3ed64117232d093e31b6f8e9a7e378100d`
- `corpus_sha256`: `93c894e1435f55ff0ce56c13a78a7c7be18a55e0e8a83816eb357ac13a22e089`
- `thresholds_sha256`: `3587b91d8d8ac6ef35f224768fcd64b812558fd4d7c275f19e7190c69499cf36`

The frozen corpus path list was independently **reconstructed from the pinned
corpus commit and its digest matched `corpus_sha256`** (872 docs), confirming
the lexical arm ran against the real frozen corpus.

- code commit (this run): `6cb4d7163141a3601323a72482044b3fe47ae935`
- corpus commit (pinned, distinct from code commit): `f7c060b4f145516a4629338e078d3b8b9c0c406a`
- provider revision: none — no live embedding/rerank provider was exercised.

The code commit above is stamped by the driver at generation time
(`git rev-parse HEAD`), so `result.json` records the exact revision that produced
the numbers. Note a deliberate **one-commit lag**: committing this report/driver
change itself advances `HEAD`, so the recorded run commit trails live `HEAD` by
(at most) the single commit that carries this update. The contract test therefore
asserts the report records *a* valid 40-hex code commit, **not** equality with
live `HEAD` (which moves the moment this fix lands). Re-running the driver after
this commit re-stamps the recorded commit to the then-current `HEAD`.

## Holdout

**The holdout split was NOT used for tuning, threshold selection, weight
fitting, or reranker selection.** Only the non-holdout `main` split was scored;
no thresholds were authored or changed in this phase. Holdout ids (reserved):
`AC-03`, `CD-04`, `CD-06`, `CF-03`, `EI-05`, `EO-04`, `HN-02`, `HN-06`,
`II-04`, `II-07`.

## Reviewer

- Frozen dataset review: **roadmap-v10 board** (signed, 2026-07-11) — carried
  from `MANIFEST.json`.
- INFERGATE verdict reviewer: **_pending sign-off_** — this report records a
  machine-derived `dark_opt_in` verdict; a reviewer must confirm before any
  future default-enablement decision. No default-enablement is made here.

## Reproduce

```
uv run --no-sync python benchmarks/retrieval_eval/runs/inferbound-v10/run_inference_gate.py
```

Driver and machine-readable artifact:
`benchmarks/retrieval_eval/runs/inferbound-v10/run_inference_gate.py` and
`benchmarks/retrieval_eval/runs/inferbound-v10/result.json`.
