# Phase roadmap v10

## Context

This roadmap implements GitHub issue #73: a provider-neutral boundary between
**retrieval orchestration** (owned by Code-Index-MCP) and **learned-model
inference** (embedding and reranking, accessed through explicit provider
contracts). It is a service-boundary and correctness effort, not a dependency
on any single inference vendor. Standalone lexical-only operation must remain
dependency-free, and semantic/reranked search must stay experimental and
opt-in until predeclared benchmark gates pass.

This spec was reviewed by a cross-vendor advisor board (Sol/codex red-team,
Grok adversarial, Fable correctness; Gemini leg degraded). The board confirmed
the phase cut, safety-first sequencing, and freeze-before-tune posture, and
surfaced twelve code-verified defects now folded in below (see
`## Panel Review Reconciliation`).

Current local audit findings (verified against the tree):

- `mcp_server/utils/embedding_providers.py:99` (`OpenAICompatibleEmbeddingProvider.embed`)
  runs `del input_type` and returns a bare `List[List[float]]`;
  `VoyageEmbeddingProvider.embed` (`:53`) likewise returns bare vectors. Neither
  the OpenAI-compatible response nor the Voyage response exposes an immutable
  model revision, normalization policy, or role attestation - only a served
  model id, token usage, and vectors.
- `mcp_server/utils/semantic_indexer.py:120` defaults
  `ensure_qdrant_collection(..., allow_recreate=True)`; the runtime path at
  `:1011` passes `allow_recreate=True`; the not-exists branch (`:128`) uses the
  destructive `client.recreate_collection`; the mismatch predicate (`:148`)
  treats an unreadable config (`actual_dimension is None`) as a match; and
  `_ensure_collection` (`:1013`) ignores a `blocked` result and continues. Any
  of these can delete/recreate or silently accept a mismatched live collection
  at ordinary runtime startup. Bootstrap/preflight
  (`mcp_server/setup/semantic_preflight.py:1092`) already fails closed on
  `blocked`, so runtime behavior is inconsistent.
- `mcp_server/utils/semantic_indexer.py:266` calls `_ensure_collection()` inside
  `__init__`, before any successful inference, and metadata-write failures are
  swallowed - so profile metadata is written from local assumption, not from a
  verified server response.
- Credentials leak into on-disk profiles today: `semantic_indexer.py:261` reads
  `openai_api_key` out of `semantic_profile.build_metadata`, and
  `mcp_server/artifacts/semantic_profiles.py:62` serializes `build_metadata`
  verbatim in `to_dict()`.
- There are **three** reranker interfaces: the async `IReranker` in
  `mcp_server/indexer/reranker.py:59`, a duplicate async `IReranker` in
  `mcp_server/interfaces/indexing_interfaces.py:434`, and the sync `Dict`-based
  trio (`VoyageReranker:636`, `FlashRankReranker:673`, `CrossEncoderReranker:719`).
  The dispatcher (`dispatcher_enhanced.py:479`) wires only the sync trio and
  calls it synchronously from `_apply_reranker` (`:1267`), which returns the
  original ordering on failure (`:1292`) - masking a failed rerank as success.
  `hybrid_search.py:22` and `cross_repo_coordinator.py:24` consume the async
  interface instead. There is no `EndpointReranker` and no versioned wire
  contract.
- `dispatcher_enhanced.py:504` sets `_reranker_skips_semantic` and `:1278`
  deliberately skips reranking for semantic results - a policy skip, not a
  failure or a not-configured state.
- Existing benchmark infrastructure (`mcp_server/benchmarks/benchmark_runner.py`,
  `scripts/utilities/benchmark_reranking_comparison.py`) exists but there is no
  frozen, human-reviewed retrieval evaluation set with predeclared gate
  thresholds, per-channel rank/score diagnostics, and egress accounting.
- The support matrix (`docs/SUPPORT_MATRIX.md`) correctly treats semantic
  search and reranking as experimental. This roadmap preserves that posture.

## Architecture North Star

Code-Index-MCP remains the retrieval orchestrator and owns everything except
model execution. Embedding and reranking are reached through versioned,
provenance-bearing contracts, so any conforming provider (fleet-local
ai-stack, commercial Voyage/Cohere, or standalone in-process) is a replaceable
adapter behind one interface.

```text
retrieval orchestration (Code-Index-MCP owns)
  parse -> chunk -> lexical/BM25 -> candidate gen -> fusion -> hydrate -> rank
        |                                   ^                         ^
        v embedding-response.v1             | rerank.v1               |
  [ inference provider boundary ] ----------+-------------------------+
        |                                   |
   embedding provider                  rerank provider
   (ai-stack | Voyage | OpenAI-compat) (ai-stack | Voyage | Cohere v2 | in-proc)
```

Every provider result carries model identity and, per field, either a
server-origin value or an explicit `declared`/`unknown` marker - a provider may
not relabel a configured assumption as provenance. Collection profiles are
derived from successful inference responses and validated before points are
written or queried, and provider or metadata-write failure mutates nothing.
Reranking never silently reports an unchanged ordering as success.

## Assumptions

- Issue #73 is the upstream tracker for this roadmap.
- Standalone lexical-only operation stays dependency-free and is the safe
  default; learned models are opt-in.
- The fleet-local semantic stack uses Qdrant and the OpenAI-compatible endpoint
  (`http://ai:8001/v1`, `oss_high` / Qwen3-Embedding-8B, 4096-d) already
  validated in the v9 pilot. That collection was indexed under pre-provenance
  assumed profiles and needs an explicit reconciliation path (EMBEDPROV).
- Contract vocabulary (rerank outcome states, provenance fields) is defined
  once and reused across safety diagnostics and the wire contracts.

## Non-Goals

- Moving parsing, indexing, Qdrant lifecycle, candidate generation, or fusion
  policy into any inference service.
- Hard-coding Code-Index-MCP to one inference vendor.
- Adding image/multimodal retrieval.
- Enabling semantic or reranked search by default before the benchmark gate
  (INFERGATE) passes.
- Any release dispatch from this roadmap.

## Cross-Cutting Principles

- **No secrets or source text in durable state** (moved from an assumption to an
  owned gate): credentials come only from environment/provider config, never
  from on-disk profile payloads; profiles, index metadata, diagnostics, logs,
  and benchmark artifacts carry IDs/counts/timings/errors and model identity
  only, proven by negative tests.
- Fail closed on collection shape (dimension/distance) or unreadable-config
  mismatch in every runtime and bootstrap path; recreation requires an explicit
  operator action; create-when-absent never uses a delete-then-create primitive.
- Provenance has **per-field authority**: each provenance field is `reported`
  (server-origin), `declared` (config-asserted), or `unknown`; a
  compatibility-critical field that is `unknown` fails closed. Providers never
  present a `declared` value as `reported`.
- Diagnostics must be truthful: distinguish `not_configured`, `attempted`,
  `succeeded`, `failed`, `fallback_applied`, and `skipped_policy`; never mask a
  failed rerank as success; the outcome must attach to the interface the
  dispatcher actually invokes.
- Freeze the retrieval benchmark **and its numeric gate thresholds** before
  tuning fusion weights or choosing a default reranker; do not select or move
  thresholds after results are visible, and keep the holdout blinded from
  tuning.
- Maximize parallel execution within the constraint that two lane agents never
  concurrently write the same file region or the same document.

## Top Interface-Freeze Gates

- IF-0-INFERSAFE-1 - Collection lifecycle contract: creation/reconciliation
  fails closed by default; create-when-absent is non-destructive; unreadable
  config and shape mismatch both yield `blocked`; every normal caller raises on
  `blocked`; recreation is an explicit operator action.
- IF-0-INFERSAFE-2 - Rerank outcome vocabulary: `not_configured`, `attempted`,
  `succeeded`, `failed`, `fallback_applied`, `skipped_policy` (with policy
  identity), carrying failed-provider and fallback-used identity; unchanged
  ordering is never reported as success; the outcome is emitted on the
  dispatcher-invoked reranker path.
- IF-0-INFERSAFE-3 - Secret/text redaction contract: no `*api_key*`/bearer
  material or source/document text survives profile serialization,
  `.index_metadata.json`, diagnostics, logs, or benchmark artifacts.
- IF-0-BENCHFREEZE-1 - Benchmark contract: a frozen, human-reviewed (signed)
  query set, corpus, per-arm run protocol, metric set, per-channel rank/score +
  egress accounting schema, **and a checksummed `gate_thresholds.json`** of
  pass/fail thresholds declared before any provider work.
- IF-0-INFERFREEZE-1 - Embedding response contract: `embedding-response.v1`
  carrying contract/request IDs, provider, served model id + revision, dimension,
  normalization policy, role, processor/prompt-mode id, and per-item
  index/status/error/vector + latency/route metadata, each field tagged
  `reported|declared|unknown`. Frozen as an **additive** schema + compat shim -
  concrete provider signatures are not changed in this phase.
- IF-0-INFERFREEZE-2 - Rerank contract: `rerank.v1` request/response with stable
  candidate IDs, per-candidate status, and validation rejecting missing,
  duplicated, or unknown candidate IDs.
- IF-0-INFERFREEZE-3 - Provider capability + provenance-validation interface: a
  provider declares role support and per-field provenance authority; a validator
  compares an expected profile against an actual successful inference response
  and fails closed on unknown compatibility-critical fields.
- IF-0-EMBEDPROV-1 - Provenance-validated embedding path: providers emit
  `embedding-response.v1`; server response is attested and the derived profile
  persisted atomically **before** collection create/validate and point writes;
  one-to-one request-index validation prevents vector/chunk misattachment;
  existing collections have a tested reconciliation path.
- IF-0-RERANKEND-1 - Endpoint reranker contract: a unified reranker interface
  with an `EndpointReranker` implementing `rerank.v1` for ai-stack and a
  modernized commercial adapter (Cohere `/v2/rerank`); all consumers
  (dispatcher, hybrid, cross-repo) migrated; in-process rerankers behind an
  explicit standalone profile.
- IF-0-INFERPROFILES-1 - Deployment profile contract: `standalone_local`,
  `fleet_local`, `commercial`, and `lexical_only` profiles with documented
  degradation policy and egress disclosure.
- IF-0-INFERGATE-1 - Rollout gate contract: a verdict evaluated against the
  BENCHFREEZE-frozen thresholds across lexical/dense/hybrid/reranked arms at
  multiple depths, binding dataset/corpus/gate/commit/provider-revision/reviewer
  hashes; reranking stays opt-in until the gate passes.

## Phases

### Phase 1 - Safety, Truthful Diagnostics, And Redaction (INFERSAFE)

**Objective**

Stop the runtime collection-recreation footgun, make reranking outcomes
truthful, and stop credential/text leakage into durable state. This phase owns
the collection-lifecycle + profile-serialization regions and the rerank-outcome
region before any parallel wave extends those files.

**Exit criteria**

- [ ] `ensure_qdrant_collection` defaults fail-closed; the runtime path
      (`semantic_indexer.py:1011`) no longer passes `allow_recreate=True`;
      create-when-absent uses a non-destructive create (not
      `recreate_collection`); an unreadable/unknown config yields `blocked`
      (not `reused`); and `_ensure_collection` (and every normal caller) raises
      an actionable diagnostic on `blocked`, mirroring preflight.
- [ ] Tests cover create-when-absent, refuse-on-shape-mismatch,
      refuse-on-unreadable-config, blocked-raises-at-runtime, and
      explicit-recreate-succeeds.
- [ ] Reranking returns/logs a structured outcome
      (`not_configured|attempted|succeeded|failed|fallback_applied|skipped_policy`)
      on the dispatcher-invoked path; a failed or unchanged ordering is never
      reported as success; fallback names the failed provider and the fallback
      used; the semantic-skip path reports `skipped_policy` with policy identity.
- [ ] Credentials are removed from profile `build_metadata` (secret-reference
      names only); a negative test asserts no `*api_key*`/bearer field or source
      text survives `to_dict()`, artifact export, `.index_metadata.json`,
      diagnostics, or logs.

**Scope notes**

Decompose into **2 file-disjoint lanes**:
- Lane A - collection fail-closed + secret redaction (`semantic_indexer.py`
  lifecycle region + `:261` key read, `semantic_profiles.py`,
  `semantic_preflight.py`). Lane A's collection sub-fix is PR-splittable and
  ships first as the standalone data-loss fix promised on issue #73.
- Lane B - rerank outcome vocabulary + truthful diagnostics (`reranker.py`,
  `dispatcher_enhanced.py` rerank region). Lane B decides how the outcome
  vocabulary attaches to the dispatcher-invoked (currently sync) path; the full
  three-interface consolidation and consumer migration is RERANKEND.

Scope is shape/dimension/distance + redaction + outcome truth only. Profile
*identity* (fingerprint) fail-closed is deferred to EMBEDPROV.

**Non-goals**

- No new provider adapters or wire contracts (INFERFREEZE onward).
- No fusion-weight or default-enablement changes.

**Key files**

- `mcp_server/utils/semantic_indexer.py`
- `mcp_server/artifacts/semantic_profiles.py`
- `mcp_server/setup/semantic_preflight.py`
- `mcp_server/indexer/reranker.py`
- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `tests/test_semantic_indexer_collection_lifecycle.py`
- `tests/test_profile_redaction.py`
- `tests/test_reranker_outcomes.py`

**Depends on**

- (none) - can start immediately.

**Produces**

- IF-0-INFERSAFE-1 - Collection lifecycle contract.
- IF-0-INFERSAFE-2 - Rerank outcome vocabulary.
- IF-0-INFERSAFE-3 - Secret/text redaction contract.

**Spec closeout policy**

- schema: spec_delta_closeout.v1
- expected_decision: no_spec_delta
- target_surfaces: `mcp_server/utils/semantic_indexer.py`,
  `mcp_server/artifacts/semantic_profiles.py`,
  `mcp_server/indexer/reranker.py`, `mcp_server/dispatcher/dispatcher_enhanced.py`
- evidence_paths: collection-lifecycle, redaction, and reranker-outcome tests
- redaction_posture: metadata_only
- blocker_class: contract_bug if any normal runtime path can recreate/accept a
  mismatched collection, if a failed rerank can report success, or if a sentinel
  credential/source text survives into any durable artifact.

### Phase 2 - Frozen Retrieval Benchmark And Gate Thresholds (BENCHFREEZE)

**Objective**

Build and freeze the human-reviewed evaluation set, run protocol, **and the
numeric pass/fail gate thresholds** before any tuning, so the rollout decision
rests on a fixed, pre-committed measure. Runs fully in parallel with INFERSAFE -
it touches only benchmark modules/data.

**Exit criteria**

- [ ] A durable, signed, human-reviewed query set covers exact
      identifiers/symbols, implementation-intent, error/operational symptoms,
      config/doc lookup, architectural/conceptual questions,
      cross-file/cross-repo relationships, and hard negatives.
- [ ] A fixed corpus + run protocol evaluates arms independently (lexical/BM25,
      dense, current hybrid/fusion, hybrid+reranked) at depths 20/50/100.
- [ ] The result schema records nDCG@k, MRR, Recall@k, zero-result/error rates,
      p50/p95 latency, inference cost, egress (did source text leave the host),
      and **per-channel ranks/scores derived from the independent single-channel
      arm runs** (no dispatcher instrumentation required).
- [ ] A checksummed `gate_thresholds.json` declares min quality per arm/depth,
      max p95, max error/zero-result rate, max commercial egress fraction, and
      the pass/fail decision algorithm - hashed before any provider work.
- [ ] A `MANIFEST.json` records dataset/corpus/threshold checksums, the reserved
      holdout IDs, and a signed review record (reviewer, date, dataset
      checksum); the harness refuses to run if the manifest is missing,
      unsigned, or checksum-mismatched.
- [ ] Tests validate the schema, the manifest gate, and a smoke run on a tiny
      fixture corpus.

**Scope notes**

Reuse `benchmark_runner.py` and `benchmark_reranking_comparison.py` where
possible. Decompose into **2 lanes**: dataset/corpus/threshold curation + freeze
(manifest, signatures, holdout reservation), and harness/metrics + per-channel
diagnostics schema.

**Non-goals**

- No tuning of fusion weights or reranker selection (INFERGATE).
- No default-enablement decision.

**Key files**

- `mcp_server/benchmarks/benchmark_runner.py`
- `scripts/utilities/benchmark_reranking_comparison.py`
- `benchmarks/retrieval_eval/` (frozen dataset + `MANIFEST.json` +
  `gate_thresholds.json`)
- `tests/test_retrieval_benchmark_harness.py`

**Depends on**

- (none) - starts immediately, in parallel with INFERSAFE.

**Produces**

- IF-0-BENCHFREEZE-1 - Benchmark contract.

**Spec closeout policy**

- schema: spec_delta_closeout.v1
- expected_decision: no_spec_delta
- target_surfaces: `benchmarks/retrieval_eval/`, benchmark harness modules
- evidence_paths: frozen manifest + gate_thresholds + harness smoke-run output
- redaction_posture: metadata_only
- blocker_class: contract_bug if arms cannot run on identical queries/corpus, if
  per-channel ranks/scores are lost, or if thresholds are not frozen before
  provider work.

### Phase 3 - Provider Contract Interface Freeze (INFERFREEZE)

**Objective**

Define and freeze the versioned wire contracts, per-field provenance authority,
and provenance-validation interface **additively** - new schema modules plus
compatibility shims, with no change to concrete provider signatures - so the
implementation phases proceed in parallel against a stable interface and the
intermediate tree still passes tests.

**Exit criteria**

- [ ] `embedding-response.v1` is defined with the fields in IF-0-INFERFREEZE-1,
      each tagged `reported|declared|unknown`; a compat shim exposes it (e.g.
      `embed_with_provenance()`) while `embed()` still returns
      `List[List[float]]` so `SemanticIndexer._embed_texts` keeps working.
- [ ] `rerank.v1` request/response is defined with stable candidate IDs,
      per-candidate status, and validation rejecting missing/duplicated/unknown
      IDs; its status vocabulary reuses the INFERSAFE outcome enum.
- [ ] A provider capability declaration (role support + per-field provenance
      authority) and a provenance-validation interface (expected vs actual,
      fail-closed on unknown compatibility-critical fields) exist with tests,
      including a named ai-stack server-side contract expected to emit the
      required metadata.
- [ ] A conformance test suite exists for future adapters; the tree passes with
      no concrete provider signature changed (migration deferred).

**Scope notes**

Additive only. Decompose into **2 lanes** writing disjoint files in a new
contracts module: embedding-response.v1 + provenance-validation interface, and
rerank.v1 + candidate-ID validation. Do not serialize on a shared module - split
the contract files so the two lanes never co-write.

**Non-goals**

- No provider implementation of provenance emission (EMBEDPROV) and no endpoint
  reranker or consumer migration (RERANKEND). No signature migration here.

**Key files**

- `mcp_server/interfaces/inference_contracts.py` (new; embedding schema + shim)
- `mcp_server/interfaces/rerank_contracts.py` (new; rerank schema + validation)
- `tests/test_inference_contracts.py`

**Depends on**

- INFERSAFE Lane B (reuses the frozen rerank outcome vocabulary).

**Produces**

- IF-0-INFERFREEZE-1 - Embedding response contract.
- IF-0-INFERFREEZE-2 - Rerank contract.
- IF-0-INFERFREEZE-3 - Provider capability + provenance-validation interface.

**Spec closeout policy**

- schema: spec_delta_closeout.v1
- expected_decision: no_spec_delta
- target_surfaces: new contract modules under `mcp_server/interfaces/`
- evidence_paths: contract + validation unit tests; green tree with shims
- redaction_posture: metadata_only
- blocker_class: contract_bug if freezing the contract breaks the intermediate
  tree, if role is not preserved end to end, or if per-field authority cannot be
  represented.

### Phase 4 - Provenance-Bearing Embedding Path (EMBEDPROV)

**Objective**

Migrate embedding providers to emit `embedding-response.v1`, preserve role, and
make collection/profile lifecycle provenance-safe: attest the server response,
persist the derived profile atomically, then create/validate the collection and
write points - with nothing mutated on failure. Runs in parallel with RERANKEND
(disjoint files).

**Exit criteria**

- [ ] `VoyageEmbeddingProvider` and `OpenAICompatibleEmbeddingProvider` return
      `embedding-response.v1`; `input_type`/role is preserved (the `del
      input_type` discard is removed); providers without role support declare it.
- [ ] Server-origin values replace assumed profile values **where the provider
      reports them**; unreported fields are explicitly `declared`, never
      silently assumed; compatibility-critical unknowns fail closed.
- [ ] Collection/profile lifecycle is reordered: provider attestation and
      atomic profile persistence happen before collection create/validate and
      point writes; provider or metadata-write failure mutates zero collection
      or metadata state (this reopens the `__init__`/`_ensure_collection`
      lifecycle region INFERSAFE stabilized - INFERSAFE tests are the regression
      guard; sequenced after INFERSAFE, not parallel).
- [ ] Batched indexing validates one-to-one request↔response indices
      (rejecting missing/duplicate/reordered/out-of-range), checks per-vector
      dimension, and applies an explicit atomic/partial-write policy so a
      malformed or partial response can never write a vector under the wrong
      chunk.
- [ ] Existing pre-provenance collections (e.g. the v9 4096-d pilot) have a
      documented, tested reconciliation path (probe-revalidate or explicit
      reindex); the failure diagnostic names the remediation.
- [ ] Query-time provenance/profile-fingerprint is checked for compatibility
      with the indexed vectors and fails closed on mismatch.

**Scope notes**

Owns the embedding provider adapters and the `semantic_indexer.py`
constructor/collection/metadata/profile region and the batch-embed partition
logic. Decompose into **3 lanes**: provider emission + role preservation;
lifecycle reordering + atomic persistence + reconciliation; index-validation +
partial-write policy.

**Non-goals**

- No reranking changes; no default-enablement.

**Key files**

- `mcp_server/utils/embedding_providers.py`
- `mcp_server/utils/semantic_indexer.py` (constructor/lifecycle/profile/batch
  regions)
- `mcp_server/artifacts/semantic_profiles.py` (profile-from-response)
- `tests/test_embedding_provenance.py`

**Depends on**

- INFERFREEZE (implements `embedding-response.v1` + provenance-validation).
- INFERSAFE (reopens the lifecycle region it stabilized).

**Produces**

- IF-0-EMBEDPROV-1 - Provenance-validated embedding path.

**Spec closeout policy**

- schema: spec_delta_closeout.v1
- expected_decision: no_spec_delta
- target_surfaces: `mcp_server/utils/embedding_providers.py`,
  `mcp_server/utils/semantic_indexer.py`, `mcp_server/artifacts/semantic_profiles.py`
- evidence_paths: provenance round-trip, index-validation, and
  mismatch-fails-closed test output
- redaction_posture: metadata_only
- blocker_class: contract_bug if a profile can be written before attestation, if
  a partial/malformed response can misattach a vector, or if provider failure
  mutates collection state.

### Phase 5 - Provider-Neutral Reranking Endpoint (RERANKEND)

**Objective**

Consolidate the three reranker interfaces into one, add an `EndpointReranker`
implementing `rerank.v1` with ai-stack and a modernized commercial adapter,
migrate every consumer, and demote in-process rerankers to an explicit
standalone profile. Runs in parallel with EMBEDPROV.

**Exit criteria**

- [ ] The async `IReranker` (`reranker.py`), the duplicate `IReranker`
      (`indexing_interfaces.py`), and the sync trio are consolidated into one
      interface (or a documented, tested sync/async adapter); the async/sync
      bridge decision is named and does not call `asyncio.run` inside a live
      event loop.
- [ ] An `EndpointReranker` implements `rerank.v1` with stable candidate IDs
      surviving reordering and per-candidate partial-failure representation;
      missing/duplicated/unknown IDs fail validation; cross-provider scores are
      not assumed comparable.
- [ ] ai-stack and a commercial adapter (Cohere `/v2/rerank`, current model)
      are implementations of the same contract; legacy models remain explicitly
      configurable. In-process FlashRank/cross-encoder is an explicitly selected
      standalone profile, not an implicit default.
- [ ] All consumers are migrated and covered by end-to-end tests through the
      dispatcher, `hybrid_search.py`, and `cross_repo_coordinator.py` routes;
      each reports the INFERSAFE structured outcome; the `_reranker_skips_semantic`
      behavior becomes an explicit capability/`skipped_policy` contract.
- [ ] Failure logs never contain query or document bodies (egress log-capture
      test).

**Scope notes**

Owns `reranker.py`, `indexing_interfaces.py` (reranker region), the dispatcher
endpoint-wiring region, and the two async consumers. Decompose into **2 lanes**:
interface consolidation + `EndpointReranker` + adapters, and consumer migration
(dispatcher/hybrid/cross-repo) + standalone-profile gating. RERANKEND reopens
Lane B's `_apply_reranker` lines; INFERSAFE's outcome tests are the regression
guard (sequenced, not parallel).

**Non-goals**

- No default-enablement of reranking (INFERGATE).

**Key files**

- `mcp_server/indexer/reranker.py`
- `mcp_server/interfaces/indexing_interfaces.py`
- `mcp_server/dispatcher/dispatcher_enhanced.py` (endpoint-wiring region)
- `mcp_server/indexer/hybrid_search.py`
- `mcp_server/dispatcher/cross_repo_coordinator.py`
- `tests/test_endpoint_reranker.py`

**Depends on**

- INFERFREEZE (implements `rerank.v1`).
- INFERSAFE Lane B (reopens the outcome/`_apply_reranker` region).

**Produces**

- IF-0-RERANKEND-1 - Endpoint reranker contract.

**Spec closeout policy**

- schema: spec_delta_closeout.v1
- expected_decision: no_spec_delta
- target_surfaces: reranker interface + all consumers
- evidence_paths: endpoint reranker + partial-failure + 3-route e2e test output
- redaction_posture: metadata_only
- blocker_class: contract_bug if any consumer route bypasses the unified
  interface, if candidate IDs are not stable across reordering, or if partial
  failures cannot be represented per candidate.

### Phase 6 - Deployment Profiles And Lifecycle (INFERPROFILES)

**Objective**

Document and test explicit deployment profiles and degradation policy so
operators can choose an inference posture with clear egress disclosure. Sole
owner of the profiles guide; does **not** write `docs/SUPPORT_MATRIX.md`
(INFERGATE owns the matrix).

**Exit criteria**

- [ ] `standalone_local`, `fleet_local`, `commercial`, and `lexical_only`
      profiles are documented and tested, including which providers each uses.
- [ ] Provider unavailability degrades according to configured policy, with
      diagnostics showing the actual path taken; a fleet model outage never
      corrupts collection metadata or recreates a collection.
- [ ] Commercial embedding/reranking is opt-in and visibly marked as
      source-code egress; `lexical_only` requires no learned-model dependency.
- [ ] The profiles guide keeps semantic/reranked search marked experimental
      (matrix wording deferred to INFERGATE's verdict).

**Scope notes**

Depends on both provider phases so profiles reference real adapters. Decompose
into **2 lanes**: profile config + degradation policy tests, and operator
profiles-guide docs.

**Non-goals**

- No default-enablement (INFERGATE). No edits to `docs/SUPPORT_MATRIX.md`.

**Key files**

- `mcp_server/config/settings.py`
- `docs/guides/inference-profiles.md` (new)
- `tests/test_deployment_profiles.py`

**Depends on**

- EMBEDPROV
- RERANKEND

**Produces**

- IF-0-INFERPROFILES-1 - Deployment profile contract.

**Spec closeout policy**

- schema: spec_delta_closeout.v1
- expected_decision: no_spec_delta
- target_surfaces: config + profiles guide
- evidence_paths: profile degradation test output
- redaction_posture: metadata_only
- blocker_class: contract_bug if a provider outage can corrupt collection
  metadata or if commercial egress is not clearly disclosed.

### Phase 7 - Benchmark Rollout Gate (INFERGATE)

**Objective**

Run the frozen benchmark across all arms on the real providers, evaluate against
the pre-frozen thresholds, and produce a truthful default-enablement verdict.
Sole owner of `docs/SUPPORT_MATRIX.md`. Reranking stays opt-in until the gate
passes.

**Exit criteria**

- [ ] The frozen BENCHFREEZE set is run across lexical, dense, hybrid, and
      hybrid+reranked arms at depths 20/50/100 using EMBEDPROV/RERANKEND
      providers, with the profiles from INFERPROFILES.
- [ ] The verdict is computed by the `gate_thresholds.json` decision algorithm
      frozen in BENCHFREEZE (not thresholds authored here); the report binds
      dataset, corpus, gate, code-commit, provider-revision, and
      reviewer-approval hashes, and records that the holdout was not used for
      tuning.
- [ ] Artifacts include quality (nDCG@k, MRR, Recall@k), latency (p50/p95),
      error/zero-result rates, cost, egress accounting, and per-channel
      rank/score diagnostics.
- [ ] The verdict records ready / still-dark-opt-in / rejected with reasons tied
      to the artifacts; `docs/SUPPORT_MATRIX.md` is updated to match; learned
      reranking stays opt-in unless the gate passes; no default is flipped
      without an explicit operator decision.

**Scope notes**

Reducer phase; decompose into 2 lanes run sequentially (disjoint ownership): Lane A benchmark execution + artifact capture, then Lane B gate evaluation + verdict; Lane B owns `docs/SUPPORT_MATRIX.md`.
Benchmark execution precedes gate evaluation within the phase.

**Non-goals**

- No release dispatch; no silent default flip.

**Key files**

- `benchmarks/retrieval_eval/` (run artifacts)
- `docs/status/INFERENCE_ROLLOUT.md` (new verdict report)
- `docs/SUPPORT_MATRIX.md`
- `tests/docs/test_inference_rollout_report.py`

**Depends on**

- INFERPROFILES
- EMBEDPROV
- RERANKEND
- BENCHFREEZE

**Produces**

- IF-0-INFERGATE-1 - Rollout gate contract.

**Spec closeout policy**

- schema: spec_delta_closeout.v1
- expected_decision: roadmap_amendment
- target_surfaces: future roadmap if the gate exposes new blockers
- evidence_paths: `docs/status/INFERENCE_ROLLOUT.md` + benchmark artifacts
- redaction_posture: metadata_only
- blocker_class: contract_bug if the verdict is not computed from the
  pre-frozen thresholds or cannot be substantiated from the artifacts.

## Phase Dependency DAG

```text
INFERSAFE ───────────────► INFERFREEZE ─┬──► EMBEDPROV ─┐
   (wave 1, parallel)        (wave 2)    └──► RERANKEND ─┴──► INFERPROFILES ──► INFERGATE
                                                              (wave 4)          (wave 5)
BENCHFREEZE ──────────────────────────────────────────────────────────────────►┘
   (wave 1, parallel)                                              (INFERGATE also needs BENCHFREEZE)
```

Execution waves (each wave runs its phases concurrently):

- Wave 1: INFERSAFE ∥ BENCHFREEZE   (INFERSAFE 2 lanes; BENCHFREEZE 2 lanes)
- Wave 2: INFERFREEZE               (additive freeze; unblocks the provider wave)
- Wave 3: EMBEDPROV ∥ RERANKEND     (disjoint files; 3 and 2 lanes)
- Wave 4: INFERPROFILES             (consumes both provider phases)
- Wave 5: INFERGATE                 (needs INFERPROFILES + providers + BENCHFREEZE)

## Panel Review Reconciliation

Cross-vendor board (2026-07-11): Sol/codex DISAGREE, Grok PARTIALLY AGREE, Fable
PARTIALLY AGREE, Gemini DEGRADED. All confirmed the architecture; the following
code-verified fixes were folded in before plan-phase:

1. Credential leak (`semantic_indexer.py:261` + `semantic_profiles.py:62`) now
   owned by INFERSAFE Lane A with a negative test (IF-0-INFERSAFE-3).
2. `SUPPORT_MATRIX.md` dual-write resolved: INFERGATE depends on INFERPROFILES
   and solely owns the matrix (waves 4 then 5).
3. Gate thresholds predeclared and checksummed in BENCHFREEZE, not authored in
   INFERGATE.
4. INFERFREEZE made additive-only (schema + compat shim); signature migration
   deferred to EMBEDPROV/RERANKEND so the intermediate tree stays green.
5. RERANKEND expanded to consolidate all three reranker interfaces and migrate
   every consumer (dispatcher, hybrid_search, cross_repo_coordinator), with the
   async/sync bridge named.
6. EMBEDPROV expanded to own constructor/collection/metadata lifecycle ordering
   (attest → persist → create/validate → write; failure mutates nothing) and an
   existing-collection reconciliation path.
7. Per-field provenance authority (`reported|declared|unknown`) added because
   generic provider APIs cannot supply immutable revision/normalization.
8. Embedding one-to-one request-index validation added to prevent vector/chunk
   misattachment on partial failure.
9. `ensure_qdrant_collection` fixes made explicit: non-destructive create,
   unreadable-config-fails-closed, blocked-raises-at-runtime.
10. `skipped_policy` added to the outcome enum before the freeze.
11. INFERSAFE mismatch narrowed to shape (dimension/distance); profile-fingerprint
    fail-closed deferred to EMBEDPROV.
12. BENCHFREEZE `MANIFEST.json` with signed human-review + holdout IDs makes
    "human-reviewed"/holdout-unused machine-checkable.

## Execution Notes

- INFERSAFE and BENCHFREEZE start immediately and in parallel; they share no
  files. INFERSAFE Lane A's collection sub-fix is the ship-first data-loss fix.
- Parallelism is bounded by two hot files. `semantic_indexer.py` is touched by
  INFERSAFE (lifecycle + key-read) and EMBEDPROV (lifecycle reorder + batch);
  `dispatcher_enhanced.py` by INFERSAFE (outcome region) and RERANKEND (endpoint
  wiring). INFERSAFE is sequenced first so it stabilizes both regions; EMBEDPROV
  and RERANKEND knowingly reopen those regions and rely on INFERSAFE's tests as
  regression guards. Before wave 3, plan-phase must publish a symbol/line-level
  ownership table (the wave-3 region split is prose here, not yet symbol-frozen).
- Issue #73 proposed EMBEDPROV before RERANKEND serially. This roadmap runs them
  in parallel because the additive INFERFREEZE removes the wire-level coupling
  and their key-file sets are disjoint (embedding stack vs rerank stack, no
  cross-import). If plan-phase finds a shared candidate/score dict-shape change,
  fall back to the issue's serial order.
- BENCHFREEZE freezes thresholds before any provider work; INFERGATE only
  evaluates against them. Keep learned reranking dark/opt-in until the gate
  passes; do not flip any default from within this roadmap.

## Verification

- `phase-loop validate-roadmap specs/phase-plans-v11.md`
- `uv run pytest tests/test_semantic_indexer_collection_lifecycle.py tests/test_profile_redaction.py tests/test_reranker_outcomes.py -q --no-cov`
- `uv run pytest tests/test_retrieval_benchmark_harness.py -q --no-cov`
- `uv run pytest tests/test_inference_contracts.py -q --no-cov`
- `uv run pytest tests/test_embedding_provenance.py tests/test_endpoint_reranker.py -q --no-cov`
- `uv run pytest tests/test_deployment_profiles.py tests/docs/test_inference_rollout_report.py -q --no-cov`

automation:
  status: ready
  next_skill: claude-plan-phase
  next_command: claude-plan-phase specs/phase-plans-v11.md INFERSAFE
  next_model_hint: claude-opus-4-8
  next_effort_hint: medium
  human_required: false
  verification_status: not_run
  artifact: specs/phase-plans-v11.md
  next_phase: INFERSAFE
