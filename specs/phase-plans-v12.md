# Phase roadmap v12

## Context

This roadmap folds together two independent bodies of work:

1. **A CRITICAL upstream dependency break + imminent major release (issue #76)** —
   `treesitter-chunker` is publishing **v4**, which redesigns
   `chunk_id`/`node_id`/`definition_id` to be collision-free and deterministic and
   may move import paths (interface consolidation) and re-pin the `tree_sitter`
   ABI. As of 2026-07-12 PyPI's latest is `3.2.2`; **v4 is being pushed now**. The
   repo pins `treesitter-chunker>=3.1.0,<4` (`pyproject.toml:30`), whose `<4`
   ceiling **excludes v4**, and is ABI-paired to 3.x's `tree_sitter>=0.24,<0.25`
   (`pyproject.toml:32`). Two problems compound: (a) the `<4` pin blocks adoption,
   and (b) the `ON CONFLICT(file_id, chunk_id)` upsert into SQLite `code_chunks`
   (`dispatcher_enhanced.py` ~L3389-3396) assumes `chunk_id` is stable across runs,
   so v4's new id scheme causes **silent data corruption** — orphaned/duplicated
   `code_chunks` rows and stale summaries on re-index, with no exception raised.
   We must accommodate v4: bump the pin + ABI, guard the id scheme, and rebuild.

2. **The deferred follow-ups from the provider-neutral inference boundary**
   (issue #73, merged as PR #74 / `specs/phase-plans-v11.md`) plus the Fable
   cross-vendor CR nice-to-haves — redaction completeness, profile-gating
   symmetry, provenance honesty, reconcile diagnostics, async cancellation
   safety, and a provenance-bound live benchmark.

Open GitHub issues as of 2026-07-12: **#76** (folded in below as the first,
highest-priority phase). The inference follow-ups have no open issue; they are the
tech debt recorded on issue #73 / PR #74.

The #74 merge fully redacted the *new* rerank/search paths it introduced, wired
deployment profiles into runtime, and shipped a provenance-bearing embedding and
rerank contract. It deliberately left as follow-ups: (a) redaction of the
*pre-existing* rerank/search log sites, (b) symmetry gaps in the deployment
profile helpers, (c) two provider-provenance honesty gaps, (d) a reconcile
diagnostic that conflates transient faults with shape mismatch, (e) an async
endpoint-transport timeout that can leave a worker running, and (f) a true
live-provider benchmark run (the rollout verdict is `dark_opt_in` only because no
live embedding endpoint was reachable).

Verified follow-up sites on `main` (`f6f4705`):

- Raw exception bodies still logged on the legacy async reranker paths:
  `reranker.py:368` (Cohere), `:510` (cross-encoder), `:641` (TF-IDF); and
  `hybrid_search.py:402` (`Semantic search failed with error: {e}`).
- Cross-document search builds/handles raw `topic` at
  `dispatcher_enhanced.py:3917`; any log of that topic is a raw-body path.
- `settings.py:1119` `learned_models_allowed` returns `True` for an *unknown*
  explicit profile name — asymmetric with `commercial_egress_allowed:1089`,
  which fails closed on unknown.
- `reranker.py:1079` parses `MCP_RERANK_TIMEOUT_S` without the `>=1s` clamp the
  dispatcher applies.
- `embedding_providers.py:130` (`VoyageEmbeddingProvider.embed_with_provenance`)
  reads `response.embeddings` (`:145`) with no arity check vs the requested
  texts; the Cohere v2 rerank adapter presents a config `model_revision` where
  the response supplies none.
- `semantic_indexer.py:1585` `_existing_collection_shape_blocked` treats a
  transient Qdrant read error the same as a real shape mismatch (`blocked`),
  emitting a reindex-suggesting message on a retryable fault.
- `run_inference_gate.py` probes and gates arms correctly but has no live
  collection-provenance verification, so a live run's numbers are not yet
  bindable to the frozen corpus.

## Architecture North Star

Fail closed on a chunker identity-scheme change, and close the inference-boundary
honesty and safety gaps at the edges:

```text
persisted code_chunks               -> reconcile only when the chunker id-scheme matches;
                                       otherwise refuse incremental upsert and rebuild
every rerank/search/hybrid log      -> ids/counts/lengths + redacted errors only
every deployment-profile decision   -> fail closed on unknown/ambiguous profile
every provenance field              -> reported | declared | unknown, never faked
every endpoint transport timeout    -> caller unblocked AND worker cannot publish
live benchmark numbers              -> bound to verified collection provenance
```

The `chunk_id`/`node_id`/`definition_id` values are an upstream identity contract:
Code-Index-MCP must persist the scheme it indexed under and refuse to silently
merge rows produced by a different scheme.

## Assumptions

- `main` (`f6f4705`) is the implementation base; #74 is merged.
- `treesitter-chunker` v4 is not yet on PyPI as of 2026-07-12 (latest `3.2.2`).
  The version-agnostic safety guard + rebuild migration land now; the actual v4
  adoption (real pin bump to a published v4, live migration run, moved-import
  verification) is gated on v4 publishing and is verified against the real v4 (or
  a pinned pre-release) when available — not fabricated beforehand.
- Adopting the id-scheme change requires a full `code_chunks` rebuild; incremental
  upsert cannot bridge it (per issue #76). Upstream keeps re-export shims for the
  moved graph import paths, and v4 re-pins the `tree_sitter` ABI (its exact
  requirement is read from v4's metadata at adoption time).
- The `utils/chunker_adapter.py` `CodeChunk`->symbol path is ID-agnostic and
  unaffected; only the dispatcher `code_chunks` upsert path is exposed.
- INFERPOLISH needs no external services (unit-testable with fakes).
- INFERLIVEGATE requires a reachable embedding endpoint and a populated Qdrant
  collection to produce real numbers; without them it stays `dark_opt_in` and
  only the verification code + procedure land.
- Learned reranking remains opt-in / not default-enabled until INFERLIVEGATE
  produces a passing, provenance-bound run.

## Non-Goals

- No change to the frozen benchmark dataset, thresholds, or the #73 contracts.
- No default-enablement of semantic/reranked search from INFERPOLISH.
- No new provider vendors; no roadmap for the separate v10 hardening work.
- No redesign of chunk identity in this repo — the scheme is upstream's; this
  roadmap only persists, detects, and safely migrates it.
- No release dispatch.

## Cross-Cutting Principles

- Refuse to reconcile persisted `code_chunks` across a chunker id-scheme change;
  rebuild explicitly instead of silently upserting.
- Never log a query, document, candidate body, or unredacted exception message.
- Fail closed on unknown deployment-profile names, symmetrically across helpers.
- A provider may only tag a provenance field `reported` when the server actually
  supplied it; otherwise `declared` or `unknown`.
- A timed-out async transport must not mutate shared reranker state after the
  caller has returned.
- Keep pre-existing green tests green; add a failing-at-base repro for each fix.

## Top Interface-Freeze Gates

- IF-0-CHUNKERSAFE-1 - Chunk identity-scheme guard: the persisted index records
  the chunker identity scheme it was written under; on re-index a scheme mismatch
  refuses incremental `code_chunks` upsert and requires an explicit rebuild, so a
  chunker id-scheme change can never silently orphan/duplicate rows or leave
  dangling summaries.
- IF-0-CHUNKERSAFE-2 - v4 adoption + ABI + graph-import safety: the
  `treesitter-chunker` pin admits v4 and is re-paired to v4's required
  `tree_sitter` ABI; a smoke check proves the graph import shims
  (`chunker.core.chunk_file`, `chunker.graph.xref.build_xref`,
  `chunker.graph.cut.graph_cut`) still resolve under v4; and the live v4
  adoption/migration is verified against a real published v4 (or a pinned
  pre-release) before the ceiling is raised in a shipped release.
- IF-0-INFERPOLISH-1 - Redaction completeness: no raw query/document/candidate
  body or unredacted exception message reaches any rerank, hybrid, or search log
  path (extends #74's redaction to the legacy/pre-existing sites).
- IF-0-INFERPOLISH-2 - Profile-gating symmetry + timeout clamp:
  `learned_models_allowed` fails closed on an unknown explicit profile (mirroring
  `commercial_egress_allowed`); `EndpointReranker`'s timeout env parse clamps to
  the same `>=1s` floor the dispatcher uses.
- IF-0-INFERPOLISH-3 - Provenance honesty + async cancellation safety: the Cohere
  v2 adapter reports `model_revision=None`/`unknown` when the response supplies
  none; Voyage `embed_with_provenance` rejects an arity mismatch; a timed-out
  endpoint transport cannot publish `last_outcome`/`last_diagnostics` after the
  caller returned (per-call generation guard).
- IF-0-INFERLIVEGATE-1 - Provenance-bound live gate: a live provider run verifies
  the live Qdrant collection's indexed commit, corpus checksum, profile
  fingerprint, and provider revision against the frozen corpus before its metrics
  count; the verdict records those bindings, and only a passing bound run may move
  reranking off `dark_opt_in`.

## Phases

### Phase 1 - Treesitter-Chunker v4 Accommodation And Identity-Scheme Safety (CHUNKERSAFE)

**Objective**

Accommodate the imminent `treesitter-chunker` v4 safely (issue #76): raise the
`<4` pin ceiling and re-pair the `tree_sitter` ABI to v4's requirement; persist
the chunker identity scheme the index was built under and refuse to incrementally
reconcile `code_chunks` across a scheme change; provide a tested rebuild
migration; keep the graph imports resilient to v4's interface consolidation; and
verify the live adoption against a real published v4 before raising the ceiling in
a shipped release. CRITICAL — v4's new id scheme is silent data corruption on the
currently-exposed pin. The version-agnostic safety guard lands now; the live v4
adoption is gated on v4 publishing.

**Exit criteria**

- [ ] The persisted index records a chunker identity-scheme marker
      (chunker version + scheme id) alongside `code_chunks`; the marker is written
      on index and read on re-index.
- [ ] On re-index, a scheme-marker mismatch does NOT run the
      `ON CONFLICT(file_id, chunk_id)` incremental upsert
      (`dispatcher_enhanced.py` ~L3363-3446); it fails closed with an actionable
      diagnostic and requires an explicit `code_chunks` rebuild.
- [ ] A tested rebuild migration drops and repopulates `code_chunks` (and
      invalidates dependent summaries read at `cli/tool_handlers.py:1589-1608`)
      when adopting the new scheme; no orphaned or duplicated rows survive, and
      no stale summary keys dangle.
- [ ] The `pyproject.toml` pin admits v4 (raise the `<4` ceiling, e.g.
      `>=3.2.2,<5`) and is re-paired to v4's required `tree_sitter` ABI (replace
      the 3.x `tree_sitter>=0.24,<0.25` note/constraint with v4's), read from v4's
      own metadata — not guessed. A test asserts the pin admits v4 and the ABI
      constraint matches v4's requirement.
- [ ] Live v4 adoption is verified against a real published v4 (or a pinned
      pre-release): a `code_chunks` build under v4 followed by a re-index shows the
      scheme-guard + rebuild path engaging with zero orphaned/dangling rows. If v4
      is not yet available, this criterion is explicitly deferred with the guard,
      prepared pin, and import resilience already landed — no fabricated run.
- [ ] A smoke check verifies the graph import shims
      (`chunker.core.chunk_file`, `chunker.graph.xref.build_xref`,
      `chunker.graph.cut.graph_cut`, imported under try/except at
      `mcp_server/graph/xref_adapter.py:14-15` and
      `mcp_server/utils/semantic_indexer.py:17`) still load after the bump, so a
      moved path is caught instead of silently degrading graph features to
      "unavailable" (the degradation messages live at `gateway.py:2875/2986/3030`).
- [ ] `utils/chunker_adapter.py` is confirmed (by test) ID-agnostic and
      unaffected.

**Scope notes**

Decompose into **2 lanes**: Lane A (version-agnostic, lands now) - scheme marker
+ fail-closed guard + rebuild migration in the dispatcher `code_chunks` path and
`storage/sqlite_store.py` schema; Lane B (v4 adoption, gated on v4 publish) - the
`pyproject.toml` pin-ceiling + `tree_sitter` ABI re-pair, graph-import resilience
(adopt v4's canonical paths, tolerate the re-export shims) + smoke check, the
chunker-adapter-unaffected assertion, the live-v4 migration verification, and
docs. Adopting the new scheme requires a full `code_chunks` rebuild; never
silently incremental-upsert across it. Lane A is safe to land immediately and
protects any 3.2.x or v4 scheme change; Lane B's live verification waits for v4 to
publish. Coordinate the exact `dispatcher_enhanced.py` region (the `code_chunks`
upsert ~L3389-3396) so INFERPOLISH (which owns the rerank/search-log region of
the same file) does not overlap.

**Non-goals**

- No redesign of chunk identity (that is upstream's contract).
- No change to the ID-agnostic `chunker_adapter.py` symbol path.

**Key files**

- `pyproject.toml`
- `mcp_server/dispatcher/dispatcher_enhanced.py` (`code_chunks` upsert region)
- `mcp_server/storage/sqlite_store.py` (schema + scheme marker + migration)
- `mcp_server/graph/xref_adapter.py`, `mcp_server/utils/semantic_indexer.py`
  (graph import shims; `gateway.py` holds the graph-unavailable messages)
- `mcp_server/cli/tool_handlers.py` (chunk readback)
- `mcp_server/utils/chunker_adapter.py` (confirm unaffected)
- `tests/test_chunker_identity_migration.py` (new),
  `tests/test_chunker_graph_imports_smoke.py` (new)

**Depends on**

- (none) - starts first; the critical data-integrity fix, ahead of the inference follow-ups.

**Produces**

- IF-0-CHUNKERSAFE-1 - Chunk identity-scheme guard.
- IF-0-CHUNKERSAFE-2 - Adoption + graph-import safety.

**Spec closeout policy**

- schema: spec_delta_closeout.v1
- expected_decision: no_spec_delta
- target_surfaces: `mcp_server/dispatcher/dispatcher_enhanced.py`,
  `mcp_server/storage/sqlite_store.py`, `pyproject.toml`, `mcp_server/gateway.py`
- evidence_paths: scheme-mismatch fail-closed + rebuild-migration + graph-import
  smoke test output
- redaction_posture: metadata_only
- blocker_class: contract_bug if an id-scheme change can still incrementally
  upsert `code_chunks`, if the rebuild migration leaves orphaned/dangling rows,
  or if a moved graph import path degrades silently.

### Phase 2 - Inference Boundary Polish (INFERPOLISH)

**Objective**

Close the CR nice-to-haves and deferred hygiene items with no behavior change to
the happy path: complete log redaction, make profile gating symmetric, make
provider provenance honest, fix the reconcile diagnostic, and make endpoint
transport timeouts leak-safe.

**Exit criteria**

- [ ] No raw exception body is logged on the legacy async reranker paths
      (`reranker.py:368/510/641`) or the hybrid semantic-failure path
      (`hybrid_search.py:402`); all go through the existing redactor.
- [ ] No raw `topic`/query body is logged on the cross-document / search paths
      (audit `dispatcher_enhanced.py:3917` and siblings); log lengths/ids only.
- [ ] `learned_models_allowed` fails closed on an unknown explicit
      `MCP_DEPLOYMENT_PROFILE`; `EndpointReranker` timeout parse clamps to `>=1s`.
- [ ] Cohere v2 adapter reports `model_revision` as `None`/`unknown` when the
      response lacks one (never a config value tagged as provider-reported);
      `VoyageEmbeddingProvider.embed_with_provenance` raises on an arity mismatch
      between requested texts and returned embeddings.
- [ ] A timed-out endpoint transport cannot mutate shared reranker diagnostics
      after the bridge raised `TimeoutError` (per-call generation guard); the
      leaked worker is logged, not silently swallowed.
- [ ] `_existing_collection_shape_blocked` distinguishes a transient Qdrant read
      error (retryable, non-`blocked`) from a real shape mismatch; the diagnostic
      text matches the actual cause.

**Scope notes**

Decompose into **3 file-disjoint lanes**:
- Lane A - rerank/search logging + async safety + timeout clamp + Cohere
  revision: `mcp_server/indexer/reranker.py`,
  `mcp_server/indexer/hybrid_search.py`,
  `mcp_server/dispatcher/dispatcher_enhanced.py`,
  `mcp_server/dispatcher/cross_repo_coordinator.py`.
- Lane B - provider + indexer honesty: `mcp_server/utils/embedding_providers.py`
  (Voyage arity), `mcp_server/utils/semantic_indexer.py` (reconcile transient
  vs blocked).
- Lane C - profile symmetry: `mcp_server/config/settings.py`
  (`learned_models_allowed` fail-closed).

**Non-goals**

- No default-enablement; no contract or dataset changes.

**Key files**

- `mcp_server/indexer/reranker.py`
- `mcp_server/indexer/hybrid_search.py`
- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/dispatcher/cross_repo_coordinator.py`
- `mcp_server/utils/embedding_providers.py`
- `mcp_server/utils/semantic_indexer.py`
- `mcp_server/config/settings.py`
- `tests/test_reranker_outcomes.py`, `tests/test_rerank_consumer_migration.py`,
  `tests/test_endpoint_reranker.py`, `tests/test_embedding_provider_provenance.py`,
  `tests/test_deployment_profiles.py`, `tests/test_embedding_provenance.py`

**Depends on**

- CHUNKERSAFE (sequenced after it so edits to the shared dispatcher file are serialized — disjoint regions, the code_chunks upsert vs rerank/search logging — and the data-integrity fix lands first; otherwise logically independent).

**Produces**

- IF-0-INFERPOLISH-1 - Redaction completeness.
- IF-0-INFERPOLISH-2 - Profile-gating symmetry + timeout clamp.
- IF-0-INFERPOLISH-3 - Provenance honesty + async cancellation safety.

**Spec closeout policy**

- schema: spec_delta_closeout.v1
- expected_decision: no_spec_delta
- target_surfaces: the rerank/search/provider/settings modules above
- evidence_paths: redaction + symmetry + provenance + async-safety test output
- redaction_posture: metadata_only
- blocker_class: contract_bug if any raw body still reaches a log, if an unknown
  profile fails open, if a config value is reported as provider-origin, or if a
  timed-out worker can still publish reranker state.

### Phase 3 - Provenance-Bound Live Rollout Gate (INFERLIVEGATE)

**Objective**

Make the INFERGATE benchmark able to produce trustworthy live numbers: verify the
live collection's provenance against the frozen corpus before counting metrics,
run the real dense/hybrid/reranked arms when services are reachable, and record a
provenance-bound verdict that can (only then) move reranking off `dark_opt_in`.

**Exit criteria**

- [ ] The gate verifies a live Qdrant collection's indexed commit, corpus
      checksum, profile fingerprint, and provider revision against the frozen
      corpus/`MANIFEST.json` before any arm's metrics are counted; a mismatch
      records the arm `not_run` with a provenance-mismatch reason.
- [ ] When embedding + Qdrant + rerank endpoints are reachable AND provenance
      verifies, the dense/hybrid/hybrid_rerank arms run on real retrieved
      document content and produce metrics bound to the verified collection.
- [ ] The verdict artifact binds indexed-commit + corpus/threshold checksums +
      provider revision + code commit; holdout remains unused for tuning.
- [ ] `INFERENCE_ROLLOUT.md` / `SUPPORT_MATRIX.md` are updated only from a
      passing, provenance-bound run; absent live infra the verdict stays
      `dark_opt_in` and the phase lands the verification code + a documented
      run procedure rather than fabricated numbers.

**Scope notes**

Decompose into **2 lanes**: Lane A - live-collection provenance verification in
`run_inference_gate.py` + real-content arms; then Lane B - verdict binding +
`INFERENCE_ROLLOUT.md`/`SUPPORT_MATRIX.md` reducer and the operator run
procedure. This phase must not flip any default without a passing bound run and
an explicit operator decision.

**Non-goals**

- No fabricated live numbers; no default flip without a passing bound run.

**Key files**

- `benchmarks/retrieval_eval/runs/inferbound-v10/run_inference_gate.py`
- `mcp_server/benchmarks/retrieval_eval_harness.py`
- `docs/status/INFERENCE_ROLLOUT.md`
- `docs/SUPPORT_MATRIX.md`
- `tests/test_retrieval_benchmark_harness.py`,
  `tests/docs/test_inference_rollout_report.py`

**Depends on**

- INFERPOLISH (reuses the completed redaction + honest provenance on the arms).

**Produces**

- IF-0-INFERLIVEGATE-1 - Provenance-bound live gate.

**Spec closeout policy**

- schema: spec_delta_closeout.v1
- expected_decision: roadmap_amendment
- target_surfaces: future roadmap if a passing run proposes default-enablement
- evidence_paths: `docs/status/INFERENCE_ROLLOUT.md` + gate run artifact
- redaction_posture: metadata_only
- blocker_class: contract_bug if metrics can count without verified collection
  provenance, or if the verdict flips a default without a passing bound run.

## Phase Dependency DAG

```text
CHUNKERSAFE ──► INFERPOLISH ──► INFERLIVEGATE
 (wave 1, 2 lanes)  (wave 2, 3 lanes)   (wave 3, 2 lanes)
```

CHUNKERSAFE is CRITICAL and lands first (independent subsystem; also owns the
`code_chunks` region of `dispatcher_enhanced.py`). INFERPOLISH follows to
serialize edits to that file, then INFERLIVEGATE consumes the polished providers.

## Execution Notes

- CHUNKERSAFE is the priority: v4's new id scheme is silent data corruption on
  the currently-exposed pin, so it lands first and can ship as its own PR. Its
  Lane A (version-agnostic scheme guard + rebuild migration) is safe to land
  immediately; Lane B (raise the `<4` ceiling to admit v4, re-pair the
  `tree_sitter` ABI, and verify the live v4 migration) is gated on v4 publishing
  (PyPI latest is `3.2.2` as of 2026-07-12). Do not raise the shipped pin ceiling
  before a real v4 (or pinned pre-release) migration run passes. The guard must
  refuse silent incremental upsert across any scheme change regardless of timing.
- INFERPOLISH's 3 lanes are file-disjoint and run concurrently; it is pure
  hygiene/honesty with no default changes and can land as its own PR. It reopens
  the rerank/search-log region of `dispatcher_enhanced.py` after CHUNKERSAFE has
  finished the `code_chunks` region of the same file.
- INFERLIVEGATE is infra-gated: without a reachable embedding endpoint + a
  populated, provenance-matching collection, it lands the verification code and
  a run procedure and leaves the verdict `dark_opt_in`. Do not fabricate numbers.
- Keep the pre-existing green suite green; capture a failing-at-base repro for
  each fix before implementing it.

## Verification

- `phase-loop validate-roadmap specs/phase-plans-v12.md`
- `uv run --no-sync pytest tests/test_chunker_identity_migration.py tests/test_chunker_graph_imports_smoke.py -q --no-cov`
- `uv run --no-sync pytest tests/test_reranker_outcomes.py tests/test_rerank_consumer_migration.py tests/test_endpoint_reranker.py -q --no-cov`
- `uv run --no-sync pytest tests/test_embedding_provider_provenance.py tests/test_embedding_provenance.py tests/test_deployment_profiles.py -q --no-cov`
- `uv run --no-sync pytest tests/test_retrieval_benchmark_harness.py tests/docs/test_inference_rollout_report.py -q --no-cov`

automation:
  status: ready
  next_skill: claude-plan-phase
  next_command: claude-plan-phase specs/phase-plans-v12.md CHUNKERSAFE
  next_model_hint: claude-opus-4-8
  next_effort_hint: medium
  human_required: false
  verification_status: not_run
  artifact: specs/phase-plans-v12.md
  next_phase: CHUNKERSAFE
