---
phase_loop_plan_version: 1
phase: SEMQUERY
roadmap: specs/phase-plans-v7.md
roadmap_sha256: b8ba13bf3898d59c087f64193fa7415b0f932b34fc002e862d2678d74c1faf0c
---
# SEMQUERY: Semantic Query Routing and Result Quality

## Context

SEMQUERY is the phase-6 query-surface slice for the v7 semantic hardening
roadmap. SEMINCR froze the mutation/build correctness needed to trust enriched
vectors; this phase must make the query path honor that trust boundary instead
of treating `semantic: true` as a best-effort hint.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is tracked and clean in this worktree, and its
  live SHA matches the required
  `b8ba13bf3898d59c087f64193fa7415b0f932b34fc002e862d2678d74c1faf0c`.
- The checkout is on `main` at `09878ac`, `main...origin/main` is ahead by 6
  commits, and `plans/phase-plan-v7-SEMQUERY.md` did not exist before this
  planning write.
- `plans/phase-plan-v7-SEMCONTRACT.md`,
  `plans/phase-plan-v7-SEMCONFIG.md`,
  `plans/phase-plan-v7-SEMPREFLIGHT.md`,
  `plans/phase-plan-v7-SEMPIPE.md`, and
  `plans/phase-plan-v7-SEMINCR.md` already exist as the upstream v7 planning
  chain. SEMQUERY must consume their semantic-readiness states, active-profile
  metadata, semantic preflight blocker vocabulary, full-build summary-first
  contract, and incremental invalidation guarantees instead of introducing a
  second query-readiness model.
- `handle_search_code(...)` in `mcp_server/cli/tool_handlers.py` already blocks
  registered `semantic: true` requests when
  `ReadinessClassifier.classify_semantic_registered(...)` returns a non-ready
  semantic state, but the ready-path response still serializes as a bare result
  list without explicit semantic source/profile/collection metadata.
- `Dispatcher.search(...)` in
  `mcp_server/dispatcher/dispatcher_enhanced.py` routes ready semantic queries
  straight to `_semantic_indexer.search(query=query, limit=limit)`, but if
  that call raises it currently logs a warning and continues into plugin/BM25
  fallback paths. That behavior can silently turn a `semantic: true` request
  into lexical results.
- `SemanticIndexer.search(...)` and its internal reranking helpers already
  carry useful code-intent heuristics: `_path_score_multiplier(...)`,
  `_looks_like_symbol_precise_query(...)`, and
  `tests/test_benchmark_query_regressions.py` cover implementation-vs-test/doc
  ordering. What is not frozen yet is the phase-specific contract that
  definition-like semantic queries must keep implementation files ahead of
  `plans/`, `docs/`, benchmark fixtures, and test artifacts when the same
  symbol appears in both places.
- `tests/test_tool_handlers_readiness.py` already freezes the explicit
  `semantic_not_ready` refusal for `summaries_missing`, but there is no
  matching ready-path assertion that semantic results expose active profile,
  collection, and source metadata, nor a failure-path assertion that ready
  semantic requests do not silently degrade to lexical answers after a runtime
  semantic-search error.
- `tests/real_world/test_semantic_search.py` still reflects the older
  env-gated semantic surface. SEMQUERY should use it only as a narrow
  environment-backed quality guard for natural-language semantic retrieval, not
  as authority for broader reranker rollout or index-rebuild orchestration.

Practical planning boundary:

- SEMQUERY may tighten semantic result metadata, dispatcher routing, and
  semantic result ordering for code-intent and definition-intent queries; it
  may also update the operator-facing query contract docs and support matrix.
- SEMQUERY must not widen into index rebuild orchestration, semantic summary or
  vector mutation, new embedding models, broad reranker rollout, or dogfood
  evidence collection. Those belong to SEMPIPE, SEMINCR, and SEMDOGFOOD.

## Interface Freeze Gates

- [ ] IF-0-SEMQUERY-1 - Ready semantic routing contract: registered
      `semantic: true` queries for semantically ready repositories use the
      active profile's semantic index/Qdrant collection and return results that
      remain identifiable as semantic-path output end to end.
- [ ] IF-0-SEMQUERY-2 - No-silent-fallback contract: if a registered
      `semantic: true` request is not semantically ready or the semantic path
      fails at runtime, the response is an explicit semantic refusal/failure;
      it must not silently return BM25, plugin, or other lexical fallback
      results for that same request.
- [ ] IF-0-SEMQUERY-3 - Semantic response metadata contract: ready semantic
      responses expose source, profile, collection, and fallback/refusal
      status; explicit lexical requests keep the existing lexical/symbol
      behavior unchanged when `semantic: false`.
- [ ] IF-0-SEMQUERY-4 - Definition-intent ranking contract: definition-like or
      symbol-precise semantic queries demote `plans/`, `docs/`, benchmark
      artifacts, and tests beneath implementation paths when both mention the
      same symbol or near-exact identifier.
- [ ] IF-0-SEMQUERY-5 - Phase boundary contract: SEMQUERY changes query
      routing, query metadata, and ranking only. It does not rebuild indexes
      except in tests, change semantic build-time contracts, or broaden into a
      general reranker deployment phase.

## Lane Index & Dependencies

- SL-0 - Semantic result metadata and relevance guards; Depends on: (none); Blocks: SL-1, SL-2, SL-3; Parallel-safe: no
- SL-1 - Dispatcher semantic-only routing and failure semantics; Depends on: SL-0; Blocks: SL-2, SL-3; Parallel-safe: no
- SL-2 - Tool-handler response contract and readiness surfacing; Depends on: SL-0, SL-1; Blocks: SL-3; Parallel-safe: no
- SL-3 - Docs and support-matrix reducer; Depends on: SL-0, SL-1, SL-2; Blocks: SEMDOGFOOD; Parallel-safe: no

Lane DAG:

```text
SL-0 --> SL-1 --> SL-2 --> SL-3 --> SEMDOGFOOD
   \         \        \
    `--------->--------> contract inputs only
```

## Lanes

### SL-0 - Semantic Result Metadata And Relevance Guards

- **Scope**: Normalize the semantic-indexer result payload and freeze the
  ranking heuristics that keep enriched semantic queries pointed at code rather
  than plans, docs, tests, or benchmark artifacts for definition-like intents.
- **Owned files**: `mcp_server/utils/semantic_indexer.py`, `tests/test_benchmark_query_regressions.py`, `tests/real_world/test_semantic_search.py`
- **Interfaces provided**: IF-0-SEMQUERY-1 semantic-result payload fields;
  IF-0-SEMQUERY-3 source/profile/collection metadata for ready semantic hits;
  IF-0-SEMQUERY-4 semantic reranking/path-prior contract for code-intent and
  symbol-precise queries
- **Interfaces consumed**: SEMCONTRACT semantic readiness vocabulary;
  SEMCONFIG active semantic profile metadata; SEMPREFLIGHT normalized collection
  identity; existing `SemanticIndexer.search(...)`, `query(...)`,
  `_rerank_query_results(...)`, `_path_score_multiplier(...)`, and benchmark
  regression fixtures
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_benchmark_query_regressions.py` so semantic
    reranking explicitly proves implementation files beat `plans/`, `docs/`,
    benchmark fixtures, and tests for symbol-precise queries such as
    `class SemanticIndexer`.
  - test: Add coverage proving ready semantic results retain stable metadata
    for the active profile and collection rather than returning anonymous
    semantic hits.
  - test: Narrow `tests/real_world/test_semantic_search.py` to an
    environment-backed semantic-quality check that asserts the semantic path
    remains semantic-source-backed when the local semantic environment is
    provisioned, without turning this phase into a broad end-to-end rebuild.
  - impl: Update `SemanticIndexer.search(...)` / `query(...)` result shaping so
    ready semantic hits include stable fields consumed upstream such as source,
    profile, collection, and any already-available symbol/path metadata.
  - impl: Tighten semantic reranking/path priors for definition-like and
    code-intent queries so close semantic scores do not let phase plans,
    support docs, benchmark fixtures, or tests outrank implementation files.
  - impl: Keep this lane limited to semantic retrieval metadata and ordering.
    Do not introduce lexical fallback behavior or semantic-build mutations
    here.
  - verify: `uv run pytest tests/test_benchmark_query_regressions.py -q --no-cov`
  - verify: `SEMANTIC_SEARCH_ENABLED=true uv run pytest tests/real_world/test_semantic_search.py -q --no-cov`

### SL-1 - Dispatcher Semantic-Only Routing And Failure Semantics

- **Scope**: Make the dispatcher honor `semantic: true` as a semantic-only
  contract for semantically ready registered repositories instead of silently
  degrading to lexical/plugin fallback when the semantic path raises.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `tests/test_dispatcher.py`
- **Interfaces provided**: IF-0-SEMQUERY-1 dispatcher routing to the active
  semantic path; IF-0-SEMQUERY-2 runtime semantic failure semantics for ready
  repositories; preserved lexical/symbol routing for `semantic: false`
- **Interfaces consumed**: SL-0 semantic result metadata and ranking contract;
  existing `Dispatcher.search(...)`, `_get_semantic_indexer(ctx)`,
  `_apply_reranker(...)`, symbol-route/BM25 logic, and plugin fallback paths
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` so ready semantic searches prove
    `Dispatcher.search(...)` calls the semantic path, preserves semantic result
    metadata, and does not fall through to BM25 or plugin search if the
    semantic call fails.
  - test: Add regression coverage proving existing symbol-route and lexical
    behavior for `semantic: false` remain unchanged after the semantic-only
    failure path is introduced.
  - test: Add semantic-query ordering coverage that exercises
    implementation-vs-plan/doc/test ranking through the dispatcher surface, not
    only the lower-level semantic-indexer helper.
  - impl: Refactor the semantic branch in `Dispatcher.search(...)` so a ready
    semantic request either returns semantic-path results or surfaces a
    dedicated semantic failure that callers can serialize explicitly.
  - impl: Preserve plugin/BM25 fallback for the non-semantic and no-store/no-
    semantic-indexer contexts that already rely on it; the no-silent-fallback
    rule applies only to the registered-ready `semantic: true` route.
  - impl: Keep this lane bounded to dispatcher behavior. Do not mutate
    readiness classification, semantic summaries, or vector build contracts.
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov`

### SL-2 - Tool-Handler Response Contract And Readiness Surfacing

- **Scope**: Expose the semantic query contract at the MCP tool boundary so
  callers can distinguish ready semantic hits, semantic refusals, and semantic
  runtime failures without inferring that from missing results.
- **Owned files**: `mcp_server/cli/tool_handlers.py`, `mcp_server/health/repository_readiness.py`, `tests/test_tool_handlers_readiness.py`
- **Interfaces provided**: IF-0-SEMQUERY-2 tool-level semantic refusal/failure
  responses; IF-0-SEMQUERY-3 semantic response metadata envelope for ready
  results; unchanged lexical response behavior for `semantic: false`
- **Interfaces consumed**: SL-0 semantic result metadata; SL-1 dedicated
  dispatcher semantic failure contract; existing `handle_search_code(...)`,
  `_semantic_not_ready_response(...)`, `ReadinessClassifier`, and
  `SemanticReadiness.to_dict()`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_tool_handlers_readiness.py` so ready semantic
    responses include explicit metadata for source, profile, collection,
    `semantic_requested`, and refusal/fallback status instead of returning only
    a bare result array.
  - test: Add coverage for semantic refusal states beyond
    `summaries_missing`, including vectors missing and wrong collection
    dimension/profile mismatch, while preserving the existing
    `semantic_not_ready` response code.
  - test: Add coverage proving an explicit lexical request
    (`semantic: false`) still uses the current lexical/symbol response shape
    and does not gain semantic refusal metadata.
  - test: Add a ready-runtime-failure regression proving a semantic dispatcher
    error is serialized as a semantic-specific failure response rather than an
    empty or lexical result set.
  - impl: Update `handle_search_code(...)` to return a semantic-aware envelope
    for `semantic: true` results while preserving the current response shape
    for non-semantic requests.
  - impl: Thread any needed collection/profile/dimension fields through
    `SemanticReadiness` serialization so refusal payloads and ready payloads
    speak the same semantic vocabulary.
  - impl: Keep this lane at the query surface only. Do not rebuild the index
    or alter the underlying semantic build/preflight phases.
  - verify: `uv run pytest tests/test_tool_handlers_readiness.py -q --no-cov`

### SL-3 - Docs And Support-Matrix Reducer

- **Scope**: Reduce the semantic query contract into user-facing docs and the
  support matrix so semantic beta claims match the actual refusal/ready-path
  behavior without widening into SEMDOGFOOD evidence.
- **Owned files**: `docs/guides/semantic-onboarding.md`, `docs/SUPPORT_MATRIX.md`, `tests/docs/test_semquery_contract.py`
- **Interfaces provided**: concise user/operator documentation that
  `semantic: true` uses enriched vectors only when semantic readiness is ready,
  returns an explicit refusal or semantic failure otherwise, and surfaces
  source/profile/collection metadata on ready semantic responses
- **Interfaces consumed**: SL-0 semantic result metadata vocabulary; SL-1
  no-silent-fallback dispatcher contract; SL-2 MCP response envelope; roadmap
  SEMQUERY exit criteria
- **Parallel-safe**: no
- **Tasks**:
  - test: Add `tests/docs/test_semquery_contract.py` asserting the docs state
    that `semantic: true` is semantic-only for ready repositories, does not
    silently degrade to lexical answers, and exposes source/profile/collection
    metadata on ready responses.
  - test: Require `docs/SUPPORT_MATRIX.md` to reflect the current semantic
    query posture and beta limits without claiming SEMDOGFOOD evidence ahead of
    the next phase.
  - impl: Update `docs/guides/semantic-onboarding.md` with the semantic query
    contract and the distinction between semantic refusal, semantic runtime
    failure, and explicit lexical queries.
  - impl: Update `docs/SUPPORT_MATRIX.md` so customer-facing semantic support
    language matches the `semantic: true` query contract frozen in this phase.
  - impl: Keep docs bounded to query routing/metadata. Do not add dogfood
    readiness claims or index-rebuild instructions that belong to SEMDOGFOOD.
  - verify: `uv run pytest tests/docs/test_semquery_contract.py -q --no-cov`
  - verify: `rg -n "semantic: true|semantic_not_ready|semantic failure|profile|collection|fallback" docs/guides/semantic-onboarding.md docs/SUPPORT_MATRIX.md tests/docs/test_semquery_contract.py`

## Verification

Planning-only run: do not execute these during plan creation. Run them during
`codex-execute-phase` or manual SEMQUERY execution.

Lane-specific checks:

```bash
uv run pytest tests/test_benchmark_query_regressions.py -q --no-cov
SEMANTIC_SEARCH_ENABLED=true uv run pytest tests/real_world/test_semantic_search.py -q --no-cov
uv run pytest tests/test_dispatcher.py -q --no-cov
uv run pytest tests/test_tool_handlers_readiness.py -q --no-cov
uv run pytest tests/docs/test_semquery_contract.py -q --no-cov
rg -n "semantic_not_ready|semantic failure|collection|profile|semantic_requested|source|class SemanticIndexer|phase-plan-v7" \
  mcp_server/utils/semantic_indexer.py \
  mcp_server/dispatcher/dispatcher_enhanced.py \
  mcp_server/cli/tool_handlers.py \
  mcp_server/health/repository_readiness.py \
  docs/guides/semantic-onboarding.md \
  docs/SUPPORT_MATRIX.md \
  tests/test_benchmark_query_regressions.py \
  tests/test_dispatcher.py \
  tests/test_tool_handlers_readiness.py \
  tests/real_world/test_semantic_search.py \
  tests/docs/test_semquery_contract.py
```

Whole-phase regression commands:

```bash
uv run pytest \
  tests/test_benchmark_query_regressions.py \
  tests/test_dispatcher.py \
  tests/test_tool_handlers_readiness.py \
  tests/docs/test_semquery_contract.py \
  -q --no-cov
SEMANTIC_SEARCH_ENABLED=true uv run pytest tests/real_world/test_semantic_search.py -q --no-cov
git status --short -- specs/phase-plans-v7.md plans/phase-plan-v7-SEMQUERY.md
```

## Acceptance Criteria

- [ ] Registered `semantic: true` queries for semantically ready repositories
      use the active profile's semantic collection/index path rather than
      lexical fallback.
- [ ] `semantic: true` does not silently return lexical results when semantic
      readiness is unavailable or when the ready semantic path fails at
      runtime.
- [ ] Ready semantic responses expose source, profile, collection, and
      fallback/refusal metadata in a stable machine-readable shape.
- [ ] Lexical and symbol query behavior remains unchanged for
      `semantic: false`.
- [ ] Definition-like and symbol-precise semantic queries keep implementation
      files ahead of phase plans, docs, benchmark artifacts, and tests when
      the same identifier appears in both places.
- [ ] Tests cover semantic-ready routing, summaries missing, vectors missing,
      wrong collection dimension/profile mismatch, explicit lexical requests,
      and semantic runtime failure without lexical degradation.
- [ ] SEMQUERY stays bounded to query routing, response metadata, and result
      quality. It does not rebuild indexes except in tests, mutate semantic
      build contracts, or broaden into general reranker rollout.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v7-SEMQUERY.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMQUERY.md
  artifact_state: staged
```
