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
| `hybrid_rerank` | **not_run** | No live embedding provider reachable; this is the arm the gate decision hinges on. |

**not_run reason (dense / hybrid / hybrid_rerank):** no live embedding provider
reachable — the embedding endpoint `http://ai:8001/v1` was unreachable at run
time. (Qdrant `localhost:6333` was reachable, but that alone cannot produce
query/corpus embeddings.) Dense and fused arms require embeddings, so they are
recorded `not_run` rather than assigned invented metrics.

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

- code commit (this run): `b299005ffd457b5921e14476c97bde28cde206db`
- corpus commit (pinned, distinct from code commit): `f7c060b4f145516a4629338e078d3b8b9c0c406a`
- provider revision: none — no live embedding/rerank provider was exercised.

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
