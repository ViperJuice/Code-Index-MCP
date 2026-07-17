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

### Precondition for a LIVE provider run to count — collection-resident provenance

A live provider run cannot be validated in this offline environment, and its
numbers do **not** count toward the gate until an additional, now-enforced
precondition is met (IF-0-INFERLIVEGATE-1): **the queried Qdrant points must
carry a collection-resident provenance binding that verifies against the frozen
corpus BEFORE any of the arm's metrics are counted.**

This is stronger than a local `.index_metadata.json` sidecar, which the
benchmark cannot bind to the points it actually queries. The semantic-index
**producer** persists an immutable `collection-provenance.v1` manifest *inside
the collection*, and the gate reads it back and verifies it. The manifest binds:

```
collection-provenance.v1 = {
  "provenance_version": "collection-provenance.v1",
  "collection": "…", "indexed_commit": "<git sha>", "corpus_sha256": "<sha|null>",
  "profile_fingerprint": "…", "provider_id": "…", "provider_revision": "…",
  "point_set_id": "…", "written_at": "…"
}
```

The gate's verifier (`verify_collection_provenance`, in
`mcp_server/benchmarks/retrieval_eval_harness.py`) enforces, before counting
`dense` / `hybrid` / `hybrid_rerank`, **exactly** this — no more:

- `provenance_version` is the accepted `collection-provenance.v1` schema, every
  required key is present, and `indexed_commit` / `profile_fingerprint` /
  `provider_revision` are **recorded** (non-empty);
- `indexed_commit` **matches** the frozen corpus commit (`f7c060b…`);
- `corpus_sha256` is **recorded** (a null/absent corpus digest is *unbound*, not
  a mismatch) **and matches** the frozen dataset's corpus
  (`corpus_sha256` `93c894e…` above);
- the recorded `collection` **matches** the run's target collection (the driver
  always supplies it — this rejects a sentinel copied from another collection);
- `profile_fingerprint`, `provider_id`, and `provider_revision` are **value-matched
  only when the run supplies the corresponding expectation** (env
  `EXPECTED_PROFILE_FINGERPRINT`, `SEMANTIC_EMBEDDING_MODEL` → expected
  `provider_id`, `EXPECTED_PROVIDER_REVISION`). Without an expectation they are
  only required to be recorded — the offline gate does not over-tighten; and
- when the run declares an expected `point_set_id`, the collection's
  `point_set_id` **matches** it (so a run never scores a mixed index build).

Identity fields for which no expectation is passed are recorded but **not**
matched — so a collection indexed at the frozen commit/corpus but under a
different embedding model verifies only when the run omits the model expectation;
passing `SEMANTIC_EMBEDDING_MODEL` (the query-side model) rejects it.

Any binding that fails records the affected arm **`not_run`** with a distinct,
per-case reason code — never invented metrics:

| Case | Meaning | `reason_code` |
| --- | --- | --- |
| **missing** | no resident binding was written into the collection (untagged / unreadable sentinel) | `provenance_missing` |
| **tampered** | wrong/absent `provenance_version`, a missing required key, or an empty `indexed_commit` / `profile_fingerprint` / `provider_revision` | `provenance_tampered` |
| **stale** | `indexed_commit`, or a *recorded* `corpus_sha256`, does not match the frozen corpus | `provenance_stale` |
| **corpus-unbound** | `corpus_sha256` is null/absent — the producer wrote a binding but never bound a corpus digest | `provenance_corpus_unbound` |
| **collection-mismatch** | recorded `collection` differs from the run's target collection | `provenance_collection_mismatch` |
| **profile-mismatch** | recorded `profile_fingerprint` differs from the run's expected profile (only when supplied) | `provenance_profile_mismatch` |
| **provider-mismatch** | recorded `provider_id` / `provider_revision` differs from the run's expectation (only when supplied) | `provenance_provider_mismatch` |
| **mixed-run** | `point_set_id` differs from the run's expectation (a mixed index build) | `provenance_mixed_run` |

The provider arms are gated on **both** the live probes (embedding endpoint +
Qdrant, plus the functional `rerank.v1` probe for `hybrid_rerank`) **and**
collection-resident provenance verification. A collection whose binding is
missing, unbound, or mismatched on any enforced field makes
dense/hybrid/hybrid_rerank metrics unattributable to the frozen eval set, so such
a run is **invalid** and its verdict must not be recorded as gate evidence.
Numbers from an unverified live collection are out of contract.

In **this** offline environment the embedding endpoint is down, so the provider
arms never reach provenance verification; the run records
`provenance_verified: "not_applicable"` (evaluated only once the provider is
reachable) and the verdict stays `dark_opt_in`.

### Operator run procedure (live provider)

Only an operator with a reachable, provenance-verified collection may produce
gate-counting numbers. Steps:

> **Never score the live index.** The driver connects to Qdrant on
> `localhost:6333`; the production MCP index lives in the `code-embeddings`
> collection. Point this run at a **dedicated** `SEMANTIC_COLLECTION_NAME`
> (e.g. `inferbound-v10-eval`) so indexing the frozen corpus can never
> overwrite the live index.

1. **Index the frozen corpus with a provenance-writing producer.** Index the
   corpus **at the frozen commit** (`corpus_manifest.json` → `commit`
   `f7c060b`; use a worktree/checkout at that revision so the file set and the
   producer's recorded `indexed_commit` match the frozen contract) into the
   dedicated collection. A normal full build now binds the corpus automatically:
   `index_files_batch` computes `corpus_sha256` from the sorted+deduped indexed
   relative paths (the same recipe as `corpus_manifest.json`) and writes the
   `collection-provenance.v1` sentinel into the collection — recording
   `indexed_commit`, the full `corpus_sha256`, the embedding `profile_fingerprint`,
   `provider_id` / `provider_revision`, and a `point_set_id`. (Incremental
   mutations after the build deliberately invalidate the sentinel, so the scored
   collection must come from one clean full build, not an incrementally-patched
   index.)
2. **Bring up the live services.** Qdrant on `localhost:6333`, the OpenAI-compatible
   embedding endpoint, and (for `hybrid_rerank`) a `rerank.v1` endpoint. Export:
   - `SEMANTIC_COLLECTION_NAME` — the collection to score;
   - `SEMANTIC_EMBEDDING_HOST` / `SEMANTIC_EMBEDDING_PORT` / `SEMANTIC_EMBEDDING_BASE_URL`;
   - `SEMANTIC_EMBEDDING_MODEL`, `SEMANTIC_VECTOR_DIMENSION`, `OPENAI_API_KEY`;
   - `RERANK_ENDPOINT_URL`;
   - `EXPECTED_POINT_SET_ID` — the build id this run intends to score (enables the
     mixed-run check);
   - optional identity expectations that tighten the gate when supplied:
     `SEMANTIC_EMBEDDING_MODEL` is matched against the recorded `provider_id`
     (rejects a collection embedded under a different model), and
     `EXPECTED_PROFILE_FINGERPRINT` / `EXPECTED_PROVIDER_ID` /
     `EXPECTED_PROVIDER_REVISION` match the corresponding recorded fields. The
     run's target `SEMANTIC_COLLECTION_NAME` is always matched against the
     recorded `collection`. Expectations that are not supplied are only required
     to be recorded, not matched.
3. **Run the gate driver:**
   ```
   uv run --no-sync python benchmarks/retrieval_eval/runs/inferbound-v10/run_inference_gate.py
   ```
   The driver reads the collection's resident provenance, verifies it against the
   frozen corpus, and only then scores the provider arms. If verification fails,
   the arms are recorded `not_run` with the matching `provenance_mismatch` reason
   and the verdict stays `dark_opt_in`.
4. **Only a verified, passing run may move a default.** Update
   `INFERENCE_ROLLOUT.md` / `SUPPORT_MATRIX.md` off `dark_opt_in` **only** from a
   run where `provenance_verified: true`, the `hybrid_rerank` arm ran and cleared
   every frozen predicate, and the holdout was not used for tuning. No default is
   flipped here.

### Scaffolding verification (2026-07-17)

The gate machinery this procedure relies on was exercised end-to-end on the
current host; only the two live provider services are absent, so the verdict
cannot move here. What was verified:

- **Frozen contract intact.** `dataset_sha256` and `thresholds_sha256` recompute
  to the values recorded in `MANIFEST.json`; the driver's own corpus
  reconstruction verifies (`corpus_reconstruction_verified: true`, 872 docs at
  commit `f7c060b`).
- **Offline gate is honest.** Re-running the driver on this host reproduces the
  committed artifact: the lexical arm runs, `dense` / `hybrid` / `hybrid_rerank`
  record `not_run` with truthful `embedding endpoint … unreachable` reasons,
  `provenance_verified: not_applicable`, verdict `dark_opt_in`.
- **Provenance write → read → verify round-trips against live Qdrant.** Using a
  throwaway collection (never `code-embeddings`), the producer's
  `write_collection_provenance` persisted a `collection-provenance.v1` sentinel
  bound to the frozen `corpus_sha256` and commit; the gate's module-level
  `read_collection_provenance` round-tripped it; `verify_collection_provenance`
  returned **verified** against the frozen corpus; and every tampered manifest
  mapped to its exact reason code (`stale` for a wrong commit or corpus,
  `corpus_unbound` for a null corpus, `tampered` for a bad version, `missing`
  for an absent sentinel, `collection_mismatch` for the wrong collection).

**What remains to produce counting numbers on this host:** a reachable
OpenAI-compatible embedding endpoint (`SEMANTIC_EMBEDDING_HOST:PORT`, currently
`ai:8001` unreachable) and a `rerank.v1` endpoint, plus one clean full index of
the frozen corpus into a dedicated collection. Qdrant on `localhost:6333` is
already up. With those two services present, this procedure runs unchanged and
the driver will score the provider arms.

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
