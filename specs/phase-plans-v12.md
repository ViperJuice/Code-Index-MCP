# Phase roadmap v12

## Context

This roadmap folds together two independent bodies of work:

1. **A CRITICAL upstream dependency break + imminent major release (issue #76)** —
   `treesitter-chunker` is publishing **v4**, which redesigns
   `chunk_id`/`node_id`/`definition_id` to be collision-free and deterministic,
   may move import paths (interface consolidation), and re-pins the `tree_sitter`
   ABI. As of 2026-07-12 PyPI's latest is `3.2.2`; **v4 is being pushed now**. The
   repo pins `treesitter-chunker>=3.1.0,<4` (`pyproject.toml:30`), whose `<4`
   ceiling **excludes v4**, jointly ABI-paired to `tree-sitter>=0.24,<0.25` and
   `tree-sitter-language-pack>=0.9,<1.0` (`pyproject.toml:32-40`).

   **The real corruption mechanism (corrected after review):** every live write
   path is delete-then-store *per file* (`dispatcher_enhanced.py:3321`->`3469`;
   plugins call `delete_chunks_for_file` then `store_chunk`), so same-file
   orphan/duplicate rows do **not** occur. The hazard is **mixed-scheme rows
   across files that are not re-indexed after the bump**, plus **cross-table
   staleness**: `chunk_id` also keys `chunk_summaries` (`chunk_hash`),
   `semantic_points` `(profile_id, chunk_id)->point_id`, and the remote Qdrant
   points derived from it. A re-index under v4's scheme leaves the un-reindexed
   files, their summaries, and their vectors keyed under the old scheme — a
   silent, mixed-scheme index with dangling summaries/vectors and no exception.

   `code_chunks` is written from **three** upsert sites, not one:
   `sqlite_store.store_chunk` (`:1115`), `store_chunks_batch` (`:1334`), and the
   dispatcher's raw `conn.execute` (`:3396`); the plugin path
   (`python_plugin/plugin.py:244`, `plugin_semantic.py:208`,
   `generic_treesitter_plugin.py:255`) writes via `store_chunk`, bypassing the
   dispatcher entirely. `code_chunks` also holds non-chunker history/document
   rows a source re-index cannot recreate.

2. **The deferred follow-ups from the provider-neutral inference boundary**
   (issue #73, merged as PR #74 / `specs/phase-plans-v11.md`) plus the Fable
   cross-vendor CR nice-to-haves — redaction completeness, profile-gating
   symmetry, provenance honesty, reconcile diagnostics, async cancellation
   safety, and a provenance-bound live benchmark.

Open GitHub issues as of 2026-07-12: **#76** (folded in below as the first,
highest-priority phase). The inference follow-ups have no open issue; they are the
tech debt recorded on issue #73 / PR #74. This roadmap was reviewed by a
cross-vendor advisor board (Sol/codex, Grok, Gemini, Fable); Phase 1 is rewritten
to reflect their findings, and Phases 2-3 site citations were confirmed accurate.

## Architecture North Star

Fail closed on a chunker identity-scheme change at a single central choke point,
and close the inference-boundary honesty and safety gaps at the edges:

```text
persisted code_chunks/summaries/    -> written+read only when the persisted chunker
  semantic_points/vectors              id-scheme matches the active one; else refuse
                                       (reads AND writes) and rebuild atomically
every rerank/search/hybrid log      -> ids/counts/lengths + redacted errors only
every deployment-profile decision   -> fail closed on unknown/ambiguous profile
every provenance field              -> reported | declared | unknown, never faked
every endpoint transport timeout    -> caller unblocked AND worker cannot publish
live benchmark numbers              -> bound to collection-resident provenance
```

The `chunk_id`/`node_id`/`definition_id` scheme is an upstream identity contract.
Code-Index-MCP already models it as `chunk_identity_algorithm`
(`manifest_v2.py:99`, hardcoded `treesitter_chunk_id_v1` at
`artifact_upload.py:191`) and `SemanticProfile.chunker_version`/
`chunk_schema_version` (`semantic_profiles.py:36-37`). The scheme guard must reuse
that contract, not invent a parallel marker, and keep the SQLite marker and the
Qdrant/profile fingerprint coherent.

## Assumptions

- `main` (`f6f4705`) is the implementation base; #74 is merged.
- `treesitter-chunker` v4 is not yet on PyPI as of 2026-07-12 (latest `3.2.2`).
  The version-agnostic safety guard + rebuild migration land now; the actual v4
  adoption (pin/ABI bump to a published v4, live migration run, moved-import and
  API-shape verification) is gated on v4 publishing and verified against the real
  v4 (or a pinned pre-release) — not fabricated beforehand.
- The exposed surface is NOT "only the dispatcher upsert": three `code_chunks`
  upsert sites plus the plugin `store_chunk` path write it, and reads
  (`tool_handlers.py:1587`, `summarization.py:1079`) bypass any single writer.
- Adopting the id-scheme change requires a full rebuild of `code_chunks` AND its
  dependent stores (`chunk_summaries`, `semantic_points`, remote Qdrant vectors);
  synthetic non-chunker rows in `code_chunks` must be preserved.
- The `tree_sitter` ABI is a three-package joint window; a `>=3.2.2,<5` range is
  unsatisfiable with a single static `tree-sitter`/`tree-sitter-language-pack`
  pin (3.x needs `<0.25`, 4.x will need `>=0.25`), so adoption raises the floor to
  `>=4,<5`.
- `utils/chunker_adapter.py` is ID-agnostic, but it and the plugins depend on the
  v4-mutable `CodeChunk` surface (`chunk.__dict__`, `byte_start`,
  `parent_chunk_id`, metadata keys) and the `chunk_text` import; "unaffected" is
  only true for id fields.

## Non-Goals

- No change to the frozen benchmark dataset, thresholds, or the #73 contracts.
- No default-enablement of semantic/reranked search from INFERPOLISH.
- No new provider vendors; no roadmap for the separate v10 hardening work.
- No redesign of chunk identity in this repo — the scheme is upstream's; this
  roadmap only persists, detects, and safely migrates it.
- No raising of the shipped `treesitter-chunker` pin ceiling before a real v4
  migration + API-contract run passes. No release dispatch.

## Cross-Cutting Principles

- Enforce the chunker id-scheme match at a single central choke point covering
  every `code_chunks` writer AND every scheme-dependent reader; refuse rather
  than silently mix schemes.
- A missing scheme marker over a non-empty scheme-dependent index is
  `incompatible` (fail closed), not "assume match".
- Rebuild invalidates every dependent store and flips the marker only in the same
  transaction as completed repopulation; a crash leaves the old coherent index or
  a blocked/resumable state, never a half-rebuilt "ready" one.
- Never log a query, document, candidate body, or unredacted exception message.
- Fail closed on unknown deployment-profile names, symmetrically.
- A provider may only tag a provenance field `reported` when the server supplied
  it; live benchmark numbers bind to collection-resident provenance.
- Keep the pre-existing green suite green; capture a failing-at-base repro for
  each fix before implementing it.

## Top Interface-Freeze Gates

- IF-0-CHUNKERSAFE-1 - Central id-scheme guard + coherent rebuild: the chunker
  identity scheme (reusing `chunk_identity_algorithm` / `chunker_version`) is
  persisted per-DB and enforced at a single choke point across ALL `code_chunks`
  writers (`sqlite_store.store_chunk`/`store_chunks_batch`, the dispatcher raw
  SQL, the plugin path) and all scheme-dependent readers; a mismatch or a
  missing-marker-over-nonempty-index refuses reads and writes and requires a
  rebuild. The rebuild atomically invalidates `code_chunks` + `chunk_summaries` +
  `semantic_points` + remote Qdrant vectors keyed by old ids, preserves synthetic
  non-chunker rows, and flips the marker only on successful repopulation;
  readiness reports non-`ready`/`rebuilding` while tripped.
- IF-0-CHUNKERSAFE-2 - v4 adoption, ABI window, import + API contract: the pin
  floor is raised to a real published v4 (`>=4,<5`) and the `tree_sitter` /
  `tree-sitter-language-pack` / `tree-sitter-languages` joint window is re-solved
  at the resolver level (`uv lock` succeeds with v4 + the full grammar matrix); a
  grep-derived smoke check proves EVERY `chunker` import used in `mcp_server/`
  resolves under v4 (incl. `chunk_text`, `CodeChunk`, `graph_cut`); the
  dispatcher's silent zero-chunk fallback is promoted to a loud diagnostic; and a
  real-v4 functional contract test covers the call shapes and `CodeChunk`
  attribute/metadata surface the callers depend on.
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
- IF-0-INFERLIVEGATE-1 - Collection-resident provenance-bound gate: the semantic
  index PRODUCER persists an immutable collection/run manifest binding collection
  identity, corpus checksum, indexed commit, profile fingerprint, provider
  revision, and point-set id; a live provider run counts an arm's metrics only
  when the queried live collection's resident provenance verifies against the
  frozen corpus, and only a passing bound run may move reranking off
  `dark_opt_in`.

## Phases

### Phase 1 - Treesitter-Chunker v4 Accommodation And Identity-Scheme Safety (CHUNKERSAFE)

**Objective**

Accommodate the imminent `treesitter-chunker` v4 safely (issue #76): persist the
chunker identity scheme (reusing the existing `chunk_identity_algorithm` /
`chunker_version` contract), enforce it at a single central choke point across
every `code_chunks` writer and every scheme-dependent reader, provide an atomic
rebuild that invalidates all dependent stores, and — gated on v4 publishing —
raise the pin/ABI window and verify the moved imports and `CodeChunk` API surface
against a real v4. CRITICAL: a mixed-scheme index is silent data corruption.

**Exit criteria**

Lane A (version-agnostic, lands now):

- [ ] A per-DB chunker identity-scheme marker is persisted (in `index_config` or
      equivalent) using a defined `scheme_id` (e.g.
      `getattr(chunker, "CHUNK_ID_SCHEME", f"treesitter_chunk_id_v{major}")`) and
      reconciled with `chunk_identity_algorithm` (`manifest_v2.py:99`) and the
      semantic-profile `chunker_version`/`compatibility_fingerprint` so the SQLite
      marker and the Qdrant/profile fingerprint stay coherent.
- [ ] The scheme match is enforced at a single central choke point covering ALL
      writers — `sqlite_store.store_chunk` (`:1115`), `store_chunks_batch`
      (`:1334`), the dispatcher raw upsert (`:3396`), and the plugin
      `delete_chunks_for_file`+`store_chunk` path — and all scheme-dependent
      readers (`tool_handlers.py:1587`, `summarization.py:1079`). Compatibility is
      established when the repository context is opened.
- [ ] A missing marker over a non-empty scheme-dependent index is treated as
      `incompatible` (fail closed on reads AND writes) until an explicit rebuild;
      an empty index stamps the current scheme on first successful build. A
      v3-unmarked -> current-scheme fixture test proves no read/delete/upsert
      occurs while incompatible.
- [ ] A rebuild migration invalidates `code_chunks` **and** `chunk_summaries`
      **and** `semantic_points` **and** the remote Qdrant vectors keyed by old
      `chunk_id`/`:part:`/`:file-summary` ids (reusing `delete_stale_vectors` /
      `cleanup_stale_semantic_artifacts`), scoped by repository/profile, while
      PRESERVING synthetic non-chunker rows in `code_chunks`. No orphaned/dangling
      summary, mapping, or vector survives (asserted by SQL/point-count tests).
- [ ] The rebuild is atomic/resumable: the scheme marker flips in the same
      transaction as completed repopulation; `repository_readiness` reports
      non-`ready`/`rebuilding` while the guard is tripped (not table-presence-only
      `ready`); an interrupted-rebuild test leaves the old coherent index or a
      blocked/resumable state, never a half-populated "ready" DB.
- [ ] `update_chunk_token_count` and any other `chunk_id`-only writes are scoped
      by `file_id`; `:part:` `LIKE` matching escapes/asserts the id charset so v4
      ids containing `%`/`_` cannot mis-match.

Lane B (gated on v4 publishing; deferral is tracked, not silent):

- [ ] `pyproject.toml` raises the pin floor to a real published v4 (`>=4,<5`) and
      re-solves the `tree_sitter`/`tree-sitter-language-pack`/`tree-sitter-languages`
      joint window; the test is resolver-level (`uv lock` succeeds with v4 + the
      full grammar matrix), not a specifier-string assertion.
- [ ] A grep-derived smoke check proves EVERY `chunker` import in `mcp_server/`
      resolves under v4 — `chunk_text` (`dispatcher_enhanced.py:3363`, plugins),
      `chunk_file` (`xref_adapter.py:14`, `semantic_indexer.py:17`), `CodeChunk`
      (`chunker_adapter.py:8`), `build_xref`, `graph_cut`
      (`graph/context_selector.py:21`) — and the dispatcher's silent
      `shard_chunks=[]` zero-chunk fallback (`:3362-3368`) is promoted to a loud
      diagnostic / fail-closed signal.
- [ ] A real-v4 functional contract test covers the call shapes callers depend on
      (`chunk.__dict__`, `chunk.chunk_id/node_id/definition_id/parent_chunk_id/
      byte_start/byte_end/start_line/end_line/node_type/metadata`, metadata keys
      `name/signature/exports/docstring/kind`) and asserts nonempty chunks +
      working xref/graph-cut; a `CodeChunk` shape-contract test guards field
      renames/slots.
- [ ] If v4 is not yet available, Lane B is deferred to a tracked follow-up
      artifact (issue/phase `CHUNKERV4LIVE`) with an owner — not an open-ended
      "deferred" checkbox. Lane A ships without raising the shipped pin ceiling.

**Scope notes**

Decompose into **2 lanes**: Lane A (version-agnostic, lands now) - central scheme
guard + marker + atomic rebuild across all writers/readers and dependent stores.
Lane B (v4 adoption, gated on v4 publish) - pin/ABI joint-window re-solve,
grep-derived import smoke + loud zero-chunk fallback, and the real-v4 API contract
test. Prefer unifying the three duplicated upsert SQL blocks behind the storage
choke point before adding the guard, so the check lives in one place. Coordinate
the `dispatcher_enhanced.py` regions so INFERPOLISH (rerank/search-log region) does
not overlap the `code_chunks` region.

**Non-goals**

- No redesign of chunk identity (upstream's contract).
- No change to the ID-agnostic parts of `chunker_adapter.py`.

**Key files**

- `pyproject.toml`
- `mcp_server/storage/sqlite_store.py` (upserts `:1115`/`:1334`, `index_config`,
  `semantic_points`, `chunk_summaries`, `update_chunk_token_count`, migration)
- `mcp_server/dispatcher/dispatcher_enhanced.py` (`code_chunks` upsert `:3396`,
  `_clear_file_index_rows`, `chunk_text` fallback `:3362-3368`)
- `mcp_server/plugins/python_plugin/plugin.py`,
  `mcp_server/plugins/python_plugin/plugin_semantic.py`,
  `mcp_server/plugins/generic_treesitter_plugin.py` (direct `store_chunk` path)
- `mcp_server/graph/xref_adapter.py`, `mcp_server/graph/context_selector.py`,
  `mcp_server/utils/semantic_indexer.py`, `mcp_server/utils/chunker_adapter.py`
  (chunker imports + `CodeChunk` surface)
- `mcp_server/indexing/incremental_indexer.py` (`:part:` LIKE derivation),
  `mcp_server/health/repository_readiness.py` (rebuilding state),
  `mcp_server/artifacts/manifest_v2.py`, `mcp_server/artifacts/semantic_profiles.py`
  (identity contract reconciliation)
- `tests/test_chunker_identity_migration.py` (new),
  `tests/test_chunker_v4_contract.py` (new; Lane B),
  `tests/test_chunker_graph_imports_smoke.py` (new)

**Depends on**

- (none) - starts first; the critical data-integrity fix, ahead of the inference follow-ups.

**Produces**

- IF-0-CHUNKERSAFE-1 - Central id-scheme guard + coherent rebuild.
- IF-0-CHUNKERSAFE-2 - v4 adoption, ABI window, import + API contract.

**Spec closeout policy**

- schema: spec_delta_closeout.v1
- expected_decision: no_spec_delta
- target_surfaces: `mcp_server/storage/sqlite_store.py`,
  `mcp_server/dispatcher/dispatcher_enhanced.py`, the plugin store paths,
  `pyproject.toml`
- evidence_paths: central-guard fail-closed, cross-store rebuild, interrupted-
  rebuild, and (Lane B) resolver + import + API-contract test output
- redaction_posture: metadata_only
- blocker_class: contract_bug if any `code_chunks` writer or scheme-dependent
  reader can act across a scheme mismatch, if the rebuild leaves dangling
  summaries/mappings/vectors or drops synthetic rows, if a half-rebuilt index
  reads `ready`, or if a v4 import/API move degrades silently.

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
- [ ] No raw `topic`/query body is logged on the cross-document / search paths;
      log lengths/ids only.
- [ ] `learned_models_allowed` fails closed on an unknown explicit
      `MCP_DEPLOYMENT_PROFILE`; `EndpointReranker` timeout parse clamps to `>=1s`.
- [ ] Cohere v2 adapter reports `model_revision` as `None`/`unknown` when the
      response lacks one; `VoyageEmbeddingProvider.embed_with_provenance` raises
      on an arity mismatch.
- [ ] A timed-out endpoint transport cannot mutate shared reranker diagnostics
      after the bridge raised `TimeoutError` (per-call generation guard).
- [ ] `_existing_collection_shape_blocked` distinguishes a transient Qdrant read
      error (retryable) from a real shape mismatch; the diagnostic matches cause.

**Scope notes**

Decompose into **3 file-disjoint lanes**: Lane A - `reranker.py`,
`hybrid_search.py`, `dispatcher_enhanced.py` (rerank/search-log region),
`cross_repo_coordinator.py`; Lane B - `embedding_providers.py`,
`semantic_indexer.py`; Lane C - `settings.py`.

**Non-goals**

- No default-enablement; no contract or dataset changes.

**Key files**

- `mcp_server/indexer/reranker.py`, `mcp_server/indexer/hybrid_search.py`,
  `mcp_server/dispatcher/dispatcher_enhanced.py`,
  `mcp_server/dispatcher/cross_repo_coordinator.py`,
  `mcp_server/utils/embedding_providers.py`, `mcp_server/utils/semantic_indexer.py`,
  `mcp_server/config/settings.py`
- `tests/test_reranker_outcomes.py`, `tests/test_rerank_consumer_migration.py`,
  `tests/test_endpoint_reranker.py`, `tests/test_embedding_provider_provenance.py`,
  `tests/test_deployment_profiles.py`, `tests/test_embedding_provenance.py`

**Depends on**

- CHUNKERSAFE (Lane A only — the version-agnostic guard; this phase does not wait
  on the v4-publish-gated Lane B, and is sequenced after Lane A so edits to
  `dispatcher_enhanced.py` are serialized, disjoint regions: the `code_chunks`
  upsert vs rerank/search logging).

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

### Phase 3 - Collection-Resident Provenance-Bound Live Rollout Gate (INFERLIVEGATE)

**Objective**

Make the INFERGATE benchmark able to produce trustworthy live numbers: have the
semantic index PRODUCER persist collection-resident provenance, verify a live
collection's provenance against the frozen corpus before counting metrics, run the
real dense/hybrid/reranked arms when services are reachable, and record a
provenance-bound verdict that can (only then) move reranking off `dark_opt_in`.

**Exit criteria**

- [ ] The semantic index producer persists an immutable collection/run manifest
      binding collection identity, complete corpus checksum, indexed commit,
      profile fingerprint, provider revision, and point-set/build id — not only
      the local `.index_metadata.json` (`semantic_indexer.py:1256-1304`) the
      benchmark cannot bind to the queried points.
- [ ] The gate counts an arm's metrics only when the live Qdrant collection's
      resident provenance verifies against the frozen corpus/`MANIFEST.json`; a
      missing/stale/mixed-run/tampered binding records the arm `not_run` with a
      provenance-mismatch reason (tested for each case).
- [ ] When embedding + Qdrant + rerank endpoints are reachable AND provenance
      verifies, the arms run on real retrieved document content and produce
      metrics bound to the verified collection; holdout stays unused for tuning.
- [ ] `INFERENCE_ROLLOUT.md` / `SUPPORT_MATRIX.md` are updated only from a
      passing, provenance-bound run; absent live infra the verdict stays
      `dark_opt_in` and the phase lands the producer manifest + verification code
      + run procedure rather than fabricated numbers.

**Scope notes**

Decompose into **2 lanes**: Lane A - collection-resident provenance in the
producer (`semantic_indexer.py`) + verification in `run_inference_gate.py` +
real-content arms; then Lane B - verdict binding + `INFERENCE_ROLLOUT.md`/
`SUPPORT_MATRIX.md` reducer + operator run procedure. No default flip without a
passing bound run.

**Non-goals**

- No fabricated live numbers; no default flip without a passing bound run.

**Key files**

- `mcp_server/utils/semantic_indexer.py` (collection-resident provenance producer)
- `benchmarks/retrieval_eval/runs/inferbound-v10/run_inference_gate.py`
- `mcp_server/benchmarks/retrieval_eval_harness.py`
- `docs/status/INFERENCE_ROLLOUT.md`, `docs/SUPPORT_MATRIX.md`
- `tests/test_retrieval_benchmark_harness.py`,
  `tests/docs/test_inference_rollout_report.py`

**Depends on**

- INFERPOLISH (reuses the completed redaction + honest provenance on the arms).

This phase and the chunker phase's Lane B both touch `semantic_indexer.py`, but
Lane B is externally gated (v4 publish), so they do not run concurrently.

**Produces**

- IF-0-INFERLIVEGATE-1 - Collection-resident provenance-bound gate.

**Spec closeout policy**

- schema: spec_delta_closeout.v1
- expected_decision: roadmap_amendment
- target_surfaces: future roadmap if a passing run proposes default-enablement
- evidence_paths: `docs/status/INFERENCE_ROLLOUT.md` + gate run artifact
- redaction_posture: metadata_only
- blocker_class: contract_bug if metrics can count without verified
  collection-resident provenance, or if the verdict flips a default without a
  passing bound run.

## Phase Dependency DAG

```text
CHUNKERSAFE ──► INFERPOLISH ──► INFERLIVEGATE
 (wave 1)          (wave 2)         (wave 3)
   Lane A: version-agnostic guard (lands now)   INFERPOLISH depends on Lane A only
   Lane B: v4 adoption (gated on v4 publish; tracked as CHUNKERV4LIVE if deferred)
```

CHUNKERSAFE Lane A is CRITICAL and lands first. INFERPOLISH depends only on Lane A
(not the externally gated Lane B) and reopens the rerank/search-log region of the
shared dispatcher file after Lane A finishes the `code_chunks` region.
INFERLIVEGATE consumes the polished providers; it and CHUNKERSAFE Lane B both
touch `semantic_indexer.py` but never run concurrently (Lane B is gated).

## Execution Notes

- CHUNKERSAFE Lane A is the priority: a mixed-scheme index across un-reindexed
  files is silent data corruption. It lands first and can ship as its own PR. The
  guard must be central (one choke point across all writers + readers), the
  rebuild must clear all dependent stores atomically, and the missing-marker case
  must fail closed.
- CHUNKERSAFE Lane B is gated on v4 publishing (PyPI latest is `3.2.2` as of
  2026-07-12). Do not raise the shipped pin ceiling before a real v4 (or pinned
  pre-release) migration + import + API-contract run passes; if v4 is not out,
  track the deferral as `CHUNKERV4LIVE`.
- INFERPOLISH's 3 lanes are file-disjoint and run concurrently once Lane A lands.
- INFERLIVEGATE is infra-gated: without a reachable embedding endpoint + a
  populated, provenance-matching collection, it lands the producer manifest +
  verification code + run procedure and leaves the verdict `dark_opt_in`.
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
