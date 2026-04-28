---
phase_loop_plan_version: 1
phase: SEMCONTRACT
roadmap: specs/phase-plans-v7.md
roadmap_sha256: b8ba13bf3898d59c087f64193fa7415b0f932b34fc002e862d2678d74c1faf0c
---
# SEMCONTRACT: Semantic Readiness Contract

## Context

SEMCONTRACT is the phase-1 contract freeze for the v7 semantic hardening
roadmap. It should define how the repo distinguishes a lexically usable index
from a semantically ready index before SEMCONFIG, SEMPREFLIGHT, and SEMPIPE
change runtime defaults or rebuild vectors.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is present and already staged in this worktree;
  its live SHA matches the required
  `b8ba13bf3898d59c087f64193fa7415b0f932b34fc002e862d2678d74c1faf0c`.
- `plans/phase-plan-v7-SEMCONTRACT.md` did not exist before this planning run.
- `RepositoryReadinessState` currently models only lexical/topology states:
  `ready`, `unregistered_repository`, `missing_index`, `index_empty`,
  `stale_commit`, `wrong_branch`, `index_building`, and
  `unsupported_worktree`. There is no separate semantic readiness vocabulary,
  so a repository can look query-ready even when enriched semantic artifacts do
  not exist.
- `SQLiteStore` already has durable `chunk_summaries` and `semantic_points`
  tables plus `store_chunk_summary(...)`, `get_chunk_summary(...)`, and
  `get_missing_summaries(...)`, but there is no contract helper that answers
  whether summaries, vectors, vector linkages, and profile compatibility are
  jointly sufficient for semantic readiness.
- `build_health_row(...)` already separates rollout/query status from feature
  availability, but its default semantic surface is only
  `features.semantic.status = unavailable` with
  `reason = "runtime_status_unavailable"`. It does not distinguish
  `summaries_missing`, `vectors_missing`, `profile_mismatch`,
  `vector_dimension_mismatch`, or `semantic_stale`.
- `handle_search_code(...)` currently refuses only on lexical readiness. When
  lexical readiness is `ready`, `semantic: true` dispatches straight into the
  search path, and semantic failures can degrade to non-semantic behavior
  without a frozen contract saying whether semantic results were actually
  backed by summary-enriched vectors.
- `SemanticProfileRegistry` currently hashes provider/model/dimension/chunker
  basics into `compatibility_fingerprint`, but it does not freeze enrichment
  model identity, enrichment endpoint identity, prompt-template identity, or
  Qdrant collection identity in that fingerprint.
- `docs/guides/semantic-onboarding.md` still describes the semantic stack in
  generic Docker/vLLM/Voyage terms, and `docs/SUPPORT_MATRIX.md` correctly
  marks semantic search as experimental/provider-dependent but does not yet
  state the v7 rule that lexical readiness does not imply semantic readiness.

Practical planning boundary:

- SEMCONTRACT may add semantic readiness state, compatibility metadata, status
  fields, and docs/tests.
- SEMCONTRACT must not yet rewire the semantic build pipeline, mutate default
  endpoints, rebuild vectors, or change release/dispatch behavior. Those belong
  to later v7 phases.

## Interface Freeze Gates

- [ ] IF-0-SEMCONTRACT-1 - Split readiness contract:
      lexical/topology readiness remains the existing
      `RepositoryReadinessState` surface, while semantic readiness becomes a
      separate serializable contract whose vocabulary includes at least
      `ready`, `enrichment_unavailable`, `summaries_missing`,
      `vectors_missing`, `vector_dimension_mismatch`, `profile_mismatch`, and
      `semantic_stale`.
- [ ] IF-0-SEMCONTRACT-2 - SQLite semantic evidence contract:
      semantic readiness is derived from durable local evidence, not from
      optimistic runtime flags. The deciding evidence must come from
      `code_chunks`, `chunk_summaries`, `semantic_points`, and current profile
      compatibility metadata, with no requirement to rebuild the index during
      classification.
- [ ] IF-0-SEMCONTRACT-3 - Compatibility fingerprint contract:
      semantic profile fingerprints include enrichment model identity,
      enrichment base URL identity, prompt-template hash, embedding model,
      vector dimension, and Qdrant collection identity so downstream phases can
      invalidate stale summaries/vectors deterministically.
- [ ] IF-0-SEMCONTRACT-4 - Status/query surfacing contract:
      status surfaces expose lexical readiness separately from semantic
      readiness, and `search_code(semantic=true)` can report semantic
      not-ready metadata without changing the existing non-semantic
      `index_unavailable` plus `safe_fallback: "native_search"` contract.
- [ ] IF-0-SEMCONTRACT-5 - Documentation contract:
      operator-facing docs state that lexical readiness does not imply semantic
      readiness and preserve semantic search as an experimental/provider-aware
      surface rather than a default-ready claim.

## Lane Index & Dependencies

- SL-0 - Semantic readiness state and SQLite evidence; Depends on: (none); Blocks: SL-2, SL-3; Parallel-safe: no
- SL-1 - Compatibility fingerprint and artifact parity; Depends on: (none); Blocks: SL-2, SL-3; Parallel-safe: yes
- SL-2 - Status and semantic-query surfacing; Depends on: SL-0, SL-1; Blocks: SL-3; Parallel-safe: no
- SL-3 - Docs and contract reducer; Depends on: SL-0, SL-1, SL-2; Blocks: SEMCONFIG; Parallel-safe: no

Lane DAG:

```text
SL-0 ----.
         +--> SL-2 --> SL-3 --> SEMCONFIG
SL-1 ----'
```

## Lanes

### SL-0 - Semantic Readiness State And SQLite Evidence

- **Scope**: Add the semantic readiness vocabulary and the minimal SQLite
  evidence helpers needed to classify semantic readiness without rebuilding the
  indexing pipeline.
- **Owned files**: `mcp_server/health/repository_readiness.py`, `mcp_server/storage/sqlite_store.py`, `tests/test_repository_readiness.py`
- **Interfaces provided**: lexical `RepositoryReadinessState` remains intact for
  topology/query readiness; new serializable semantic readiness payload or
  sibling enum/state surface with states `ready`, `enrichment_unavailable`,
  `summaries_missing`, `vectors_missing`, `vector_dimension_mismatch`,
  `profile_mismatch`, `semantic_stale`; SQLite helper(s) that summarize local
  summary/vector/linkage evidence for a repository/profile without mutating the
  store; IF-0-SEMCONTRACT-1 and IF-0-SEMCONTRACT-2
- **Interfaces consumed**: existing `RepositoryReadiness`,
  `ReadinessClassifier.classify_registered(...)`, `SQLiteStore.get_statistics()`,
  `chunk_summaries`, `semantic_points`, `code_chunks`, and current repo/profile
  metadata exposed through the dispatcher/status path
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend readiness tests so lexical readiness values stay exact and a
    separate semantic readiness vocabulary is serialized instead of overloading
    lexical `state`.
  - test: Add coverage proving an otherwise lexically ready repo with populated
    `code_chunks` but empty `chunk_summaries` reports semantic
    `summaries_missing`, not semantic `ready`.
  - test: Add coverage for `vectors_missing` when summaries exist but
    `semantic_points` are absent, and for `semantic_stale` when stored evidence
    exists but does not match the current compatibility fingerprint.
  - test: Add SQLite helper tests for mixed chunk/summary/vector counts so the
    contract is driven by local rows rather than by process-global feature
    flags.
  - impl: Keep lexical readiness as the existing query/topology gate and add a
    distinct semantic readiness structure rather than redefining `ready` to
    mean both lexical and semantic success.
  - impl: Add store helper(s) that can count missing summaries, missing vector
    linkages, and profile/collection mismatches from existing durable tables
    and metadata without triggering indexing or semantic writes.
  - impl: Make the semantic helper fail closed when the evidence is incomplete:
    if the store cannot prove summaries, vectors, and compatible linkage, the
    semantic state must not be `ready`.
  - impl: Do not add preflight network probes, endpoint defaults, or rebuild
    behavior here; those are later-phase concerns.
  - verify: `uv run pytest tests/test_repository_readiness.py -q --no-cov`

### SL-1 - Compatibility Fingerprint And Artifact Parity

- **Scope**: Expand semantic compatibility fingerprints so downstream phases can
  deterministically tell whether summaries/vectors belong to the current
  enrichment and embedding contract.
- **Owned files**: `mcp_server/artifacts/semantic_profiles.py`, `mcp_server/artifacts/semantic_namespace.py`, `tests/test_semantic_profiles.py`, `tests/test_artifact_integrity_gate.py`
- **Interfaces provided**: `SemanticProfile.compatibility_fingerprint` derived
  from enrichment model identity, enrichment base URL identity, prompt-template
  hash, embedding model identity, vector dimension, and Qdrant collection
  identity; normalized collection/namespace identity rules consumable by
  readiness and artifact integrity checks; IF-0-SEMCONTRACT-3
- **Interfaces consumed**: existing semantic profile payload shape from
  settings/config, current `build_metadata.collection_name`, existing semantic
  profile extraction in artifact compatibility checks, and namespace rules from
  `SemanticNamespaceResolver`
- **Parallel-safe**: yes
- **Tasks**:
  - test: Extend semantic profile tests so fingerprint stability still holds
    for the same canonical payload, but any change in enrichment model,
    enrichment base URL identity, prompt-template hash, embedding model,
    vector dimension, or collection name changes the fingerprint.
  - test: Update artifact integrity coverage so semantic profile compatibility
    still accepts any configured matching profile and rejects mismatched
    fingerprints under the expanded contract.
  - test: Add normalization coverage for collection identity and endpoint
    identity so semantically equivalent inputs hash the same way while truly
    different collections/endpoints do not.
  - impl: Extend the canonical fingerprint payload in
    `SemanticProfile.from_dict(...)` to include the frozen semantic inputs above
    without moving endpoint-default selection into this phase.
  - impl: Keep the contract data-driven through profile/build metadata; do not
    rewrite `code-index-mcp.profiles.yaml` defaults or settings parsing here.
  - impl: Reuse `SemanticNamespaceResolver` for deterministic collection
    identity instead of inventing a second naming surface.
  - impl: Preserve current artifact-integrity semantics: this lane tightens what
    a fingerprint means, not when artifacts are downloaded, published, or
    rebuilt.
  - verify: `uv run pytest tests/test_semantic_profiles.py tests/test_artifact_integrity_gate.py -q --no-cov`

### SL-2 - Status And Semantic-Query Surfacing

- **Scope**: Surface the new semantic readiness contract through repo-status and
  tool-handler responses while preserving existing lexical fail-closed behavior.
- **Owned files**: `mcp_server/health/repo_status.py`, `mcp_server/cli/tool_handlers.py`, `tests/test_health_surface.py`, `tests/test_tool_handlers_readiness.py`
- **Interfaces provided**: status rows that expose lexical readiness separately
  from semantic readiness/remediation; semantic feature availability aligned
  with the new readiness vocabulary; `search_code(semantic=true)` refusal or
  metadata path that names semantic-not-ready reasons without changing ordinary
  lexical `index_unavailable` semantics; IF-0-SEMCONTRACT-4
- **Interfaces consumed**: SL-0 semantic readiness payload and SQLite evidence;
  SL-1 expanded compatibility fingerprint semantics; existing
  `build_health_row(...)`, `_index_unavailable_response(...)`, and
  `handle_get_status(...)` response envelopes
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend health-surface tests so repo rows keep existing lexical fields
    and also expose semantic readiness/remediation with a not-ready state when
    summaries or vectors are missing.
  - test: Add `handle_get_status` coverage proving a lexically ready repo can be
    semantically not-ready and that this is visible without collapsing lexical
    readiness to `index_unavailable`.
  - test: Add `handle_search_code` coverage for `semantic=true` where lexical
    readiness is `ready` but semantic readiness is not; assert the response
    includes deterministic semantic readiness metadata and does not masquerade
    as a normal semantic success.
  - test: Preserve current non-semantic refusal behavior for lexical/topology
    failures, including `index_unavailable` and `safe_fallback: "native_search"`.
  - impl: Update `build_health_row(...)` to carry semantic readiness,
    semantic remediation, and semantic feature reasoning as a separate surface
    from lexical/query readiness.
  - impl: Update `handle_get_status(...)` to serialize the new semantic
    readiness structure for each repository row.
  - impl: Update `handle_search_code(...)` only enough to respect the frozen
    semantic readiness contract when `semantic=true`; do not rework dispatcher
    search internals or semantic ranking in this phase.
  - impl: Keep `symbol_lookup`, lexical `search_code`, and existing topology
    fail-closed semantics behaviorally unchanged unless a shared serialization
    helper forces a compatible additive payload change.
  - verify: `uv run pytest tests/test_health_surface.py tests/test_tool_handlers_readiness.py -q --no-cov`

### SL-3 - Docs And Contract Reducer

- **Scope**: Reduce the frozen readiness/fingerprint/query contract into
  operator-facing docs without widening support claims or pulling SEMCONFIG work
  forward.
- **Owned files**: `docs/guides/semantic-onboarding.md`, `docs/SUPPORT_MATRIX.md`, `tests/docs/test_semcontract_contract.py`
- **Interfaces provided**: docs that state lexical readiness does not imply
  semantic readiness; semantic onboarding language aligned with the v7
  semantic-contract model; support-matrix wording that keeps semantic search
  experimental/provider-aware while naming the new readiness distinction;
  IF-0-SEMCONTRACT-5
- **Interfaces consumed**: SL-0 semantic readiness vocabulary and remediation;
  SL-1 fingerprint inputs and collection identity terminology; SL-2 status/query
  surface wording; roadmap SEMCONTRACT exit criteria
- **Parallel-safe**: no
- **Tasks**:
  - test: Add a docs-contract test that requires semantic docs to distinguish
    lexical readiness from semantic readiness and to name semantic search as
    not ready when summaries/vectors/fingerprint compatibility are missing.
  - test: Require the support matrix to preserve semantic search as an
    experimental/provider-dependent surface instead of implying default-ready
    behavior.
  - impl: Update `docs/guides/semantic-onboarding.md` so it describes the v7
    readiness split, the role of summaries and vector linkage, and the meaning
    of semantic-not-ready states without yet changing the default endpoint
    configuration text that belongs to SEMCONFIG.
  - impl: Update `docs/SUPPORT_MATRIX.md` so semantic search claims explicitly
    depend on semantic readiness, not only on lexical repository readiness or
    installed extras.
  - impl: Keep this lane a reducer: do not change endpoint defaults, provider
    setup instructions, or multi-repo support posture beyond the new readiness
    distinction.
  - verify: `uv run pytest tests/docs/test_semcontract_contract.py -q --no-cov`
  - verify: `rg -n "lexical readiness|semantic readiness|summaries_missing|vectors_missing|profile_mismatch|experimental|provider-dependent" docs/guides/semantic-onboarding.md docs/SUPPORT_MATRIX.md tests/docs/test_semcontract_contract.py`

## Verification

Planning-only run: do not execute these during plan creation. Run them during
`codex-execute-phase` or manual SEMCONTRACT execution.

Lane-specific checks:

```bash
uv run pytest tests/test_repository_readiness.py -q --no-cov
uv run pytest tests/test_semantic_profiles.py tests/test_artifact_integrity_gate.py -q --no-cov
uv run pytest tests/test_health_surface.py tests/test_tool_handlers_readiness.py -q --no-cov
uv run pytest tests/docs/test_semcontract_contract.py -q --no-cov
rg -n "semantic readiness|summaries_missing|vectors_missing|vector_dimension_mismatch|profile_mismatch|semantic_stale|compatibility_fingerprint" \
  mcp_server/health/repository_readiness.py \
  mcp_server/storage/sqlite_store.py \
  mcp_server/artifacts/semantic_profiles.py \
  mcp_server/artifacts/semantic_namespace.py \
  mcp_server/health/repo_status.py \
  mcp_server/cli/tool_handlers.py \
  docs/guides/semantic-onboarding.md \
  docs/SUPPORT_MATRIX.md \
  tests/test_repository_readiness.py \
  tests/test_semantic_profiles.py \
  tests/test_artifact_integrity_gate.py \
  tests/test_health_surface.py \
  tests/test_tool_handlers_readiness.py \
  tests/docs/test_semcontract_contract.py
```

Whole-phase regression commands:

```bash
uv run pytest \
  tests/test_repository_readiness.py \
  tests/test_semantic_profiles.py \
  tests/test_artifact_integrity_gate.py \
  tests/test_health_surface.py \
  tests/test_tool_handlers_readiness.py \
  tests/docs/test_semcontract_contract.py \
  -q --no-cov
git status --short -- specs/phase-plans-v7.md plans/phase-plan-v7-SEMCONTRACT.md
```

## Acceptance Criteria

- [ ] Lexical/topology readiness remains the current fail-closed query contract,
      while semantic readiness is exposed as a separate deterministic state
      surface.
- [ ] Semantic readiness distinguishes at least `ready`,
      `enrichment_unavailable`, `summaries_missing`, `vectors_missing`,
      `vector_dimension_mismatch`, `profile_mismatch`, and `semantic_stale`.
- [ ] Semantic readiness is driven by durable evidence from
      `code_chunks`, `chunk_summaries`, `semantic_points`, and current profile
      compatibility metadata rather than by optimistic runtime flags alone.
- [ ] Compatibility fingerprints include enrichment model identity, enrichment
      endpoint identity, prompt-template hash, embedding model, vector
      dimension, and collection identity.
- [ ] Tests prove that an otherwise lexically ready index with empty
      `chunk_summaries` is semantically not ready.
- [ ] Status/query surfaces can show semantic not-ready metadata without
      regressing existing lexical `index_unavailable` plus
      `safe_fallback: "native_search"` behavior for non-semantic failures.
- [ ] Documentation states that lexical readiness does not imply semantic
      readiness and keeps semantic search within the existing
      experimental/provider-dependent posture.
- [ ] SEMCONTRACT stays contract-focused: no endpoint-default rewrite, no full
      semantic rebuild, no vector ranking changes, and no release workflow
      changes.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v7-SEMCONTRACT.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMCONTRACT.md
  artifact_state: staged
```
