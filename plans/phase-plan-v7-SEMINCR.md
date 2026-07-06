---
phase_loop_plan_version: 1
phase: SEMINCR
roadmap: specs/phase-plans-v7.md
roadmap_sha256: b8ba13bf3898d59c087f64193fa7415b0f932b34fc002e862d2678d74c1faf0c
---
# SEMINCR: Incremental Semantic Invalidation and Watcher Repair

## Context

SEMINCR is the phase-5 mutation-repair slice for the v7 semantic hardening
roadmap. SEMPIPE froze the summary-first full semantic build contract; this
phase must carry the same contract through modify/delete/rename flows and the
watcher-triggered dispatcher entry points so incremental mutations cannot leave
stale summaries or stale vectors behind.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is tracked and clean in this worktree, and its
  live SHA matches the required
  `b8ba13bf3898d59c087f64193fa7415b0f932b34fc002e862d2678d74c1faf0c`.
- The checkout is on `main` at `5473778`, the worktree is clean before writing
  this plan, and `main...origin/main` is ahead by 5 commits.
- `plans/phase-plan-v7-SEMCONTRACT.md`,
  `plans/phase-plan-v7-SEMCONFIG.md`,
  `plans/phase-plan-v7-SEMPREFLIGHT.md`, and
  `plans/phase-plan-v7-SEMPIPE.md` already exist as the upstream v7 planning
  chain. SEMINCR must consume the split semantic-readiness model, the selected
  semantic profile metadata, the structured semantic preflight blocker, and the
  summary-first full-build helper from those phases instead of inventing a
  second mutation pipeline.
- `IncrementalIndexer` currently cleans up stale vectors through
  `_cleanup_stale_vectors(...)` and reindexes files through
  `dispatcher.index_file(ctx, full_path)`, but it has no frozen summary
  invalidation helper for prompt-fingerprint/profile-fingerprint/content-hash
  changes. Summary reuse versus regeneration is therefore implicit rather than
  contract-driven.
- `SQLiteStore.chunk_summaries` persists `profile_id`, `prompt_fingerprint`,
  and `audit_metadata`, but the store surface only exposes point-mapping
  cleanup and point-free readiness evidence. There is no targeted
  per-file/per-chunk invalidation helper that answers which authoritative
  summaries can be preserved on rename and which must be deleted before the
  next semantic rebuild.
- `SQLiteStore.move_file(...)` only updates file paths plus `file_moves`
  history. It does not currently freeze whether a same-content rename should
  preserve file-linked summaries, whether a fingerprint change should invalidate
  them, or how derived file-summary chunk ids should be rotated.
- `SemanticIndexer.delete_stale_vectors(...)` already removes Qdrant points and
  `semantic_points` mappings for chunk ids, but it does not also invalidate the
  corresponding authoritative summary rows or re-run strict semantic indexing
  through the same ordered helper used by `EnhancedDispatcher.index_directory(...)`.
- `EnhancedDispatcher.index_directory(...)` now runs lexical persistence,
  authoritative summary generation, semantic preflight, and strict batch
  embedding in order for full sync. Incremental mutation paths do not yet
  clearly reuse that same semantic-build helper, which risks drift between full
  and incremental semantics.
- `mcp_server/watcher/file_watcher.py` still uses the legacy single-repo
  `_Handler` path that calls `dispatcher.remove_file(path)`,
  `dispatcher.index_file(path)`, and `dispatcher.move_file(...)` without a
  `RepoContext`. That no longer matches the ctx-aware `EnhancedDispatcher`
  mutation signatures and is the concrete source of the roadmap's watcher
  argument-error exit criterion.
- `mcp_server/watcher_multi_repo.py` already routes mutations through
  `RepoContext`, branch guards, gitignore filtering, and success-only
  `mark_repository_changed(...)` behavior. SEMINCR should align single-repo
  watcher behavior with that contract rather than weaken the multi-repo path.
- Existing targeted tests cover vector cleanup split chunk ids
  (`tests/test_incremental_indexer.py`), Qdrant mapping deletion
  (`tests/test_semantic_stale_vector_cleanup.py`), and watcher branch/gitignore
  filters (`tests/test_watcher_multi_repo.py`), but they do not yet freeze
  prompt-change summary invalidation, rename preserve-versus-invalidate rules,
  or the repaired single-repo watcher mutation signature.

Practical planning boundary:

- SEMINCR may add targeted summary/vector invalidation helpers, rewire
  incremental mutation flows to reuse the SEMPIPE semantic-build helper, repair
  watcher entry points, and update the semantic onboarding contract if the
  operator-facing mutation story changes.
- SEMINCR must not widen into semantic query routing/ranking, new watcher
  backends, multi-branch topology expansion, or dogfood rebuild evidence.
  Those belong to SEMQUERY and SEMDOGFOOD.

## Interface Freeze Gates

- [ ] IF-0-SEMINCR-1 - Changed-chunk invalidation contract: when chunk content,
      prompt fingerprint, enrichment model/profile fingerprint, or semantic
      build metadata changes, the affected authoritative summaries and semantic
      point mappings are invalidated before incremental semantic rebuild runs.
- [ ] IF-0-SEMINCR-2 - Shared rebuild contract: incremental add/modify/rename
      paths reuse the same ordered semantic helper semantics frozen in SEMPIPE:
      lexical/chunk persistence first, authoritative summary generation second,
      semantic preflight gate third, strict embedding/upsert fourth.
- [ ] IF-0-SEMINCR-3 - Delete and rename cleanup contract: deleted chunks
      remove `chunk_summaries`, `semantic_points`, and Qdrant points; renames
      preserve existing summaries only when content hash and semantic
      fingerprint still match, otherwise they invalidate and regenerate them.
- [ ] IF-0-SEMINCR-4 - Watcher mutation contract: file watcher reindex/remove
      paths use ctx-aware dispatcher calls, no longer raise
      `EnhancedDispatcher.remove_file()` or `index_file()` argument errors, and
      keep branch/gitignore/success-only mutation semantics aligned with the
      multi-repo watcher path.
- [ ] IF-0-SEMINCR-5 - Phase boundary contract: SEMINCR changes mutation
      durability and watcher repair only. It must not change semantic query
      routing, silently fall back from `semantic: true` to lexical results, or
      broaden into full dogfood rebuild proof.

## Lane Index & Dependencies

- SL-0 - Semantic invalidation primitives and rename evidence; Depends on: (none); Blocks: SL-1, SL-2, SL-3; Parallel-safe: no
- SL-1 - Incremental mutation rebuild orchestration; Depends on: SL-0; Blocks: SL-2, SL-3; Parallel-safe: no
- SL-2 - Watcher ctx-repair and mutation entry points; Depends on: SL-0, SL-1; Blocks: SL-3; Parallel-safe: no
- SL-3 - Docs and contract reducer; Depends on: SL-0, SL-1, SL-2; Blocks: SEMQUERY; Parallel-safe: no

Lane DAG:

```text
SL-0 --> SL-1 --> SL-2 --> SL-3 --> SEMQUERY
   \         \
    `---------> contract inputs only
```

## Lanes

### SL-0 - Semantic Invalidation Primitives And Rename Evidence

- **Scope**: Add the store/indexer helpers that can prove which summaries and
  semantic vectors must be deleted or preserved across modify/delete/rename
  mutations before higher-level incremental orchestration runs.
- **Owned files**: `mcp_server/storage/sqlite_store.py`, `mcp_server/utils/semantic_indexer.py`, `tests/test_semantic_stale_vector_cleanup.py`, `tests/test_sqlite_store.py`
- **Interfaces provided**: IF-0-SEMINCR-1; IF-0-SEMINCR-3 primitive cleanup
  helpers; a structured invalidation result keyed by file/chunk/profile that
  distinguishes deleted summaries, deleted point mappings, preserved summaries,
  and regenerated-file-summary requirements
- **Interfaces consumed**: SEMPIPE summary audit metadata and strict semantic
  build contract; existing `chunk_summaries`, `semantic_points`,
  `SQLiteStore.move_file(...)`, `SQLiteStore.get_chunk_summary(...)`,
  `SemanticIndexer.delete_stale_vectors(...)`, and file-summary chunk-id rules
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_sqlite_store.py` so targeted invalidation helpers
    prove authoritative summaries are deleted when prompt fingerprint, profile
    fingerprint, or source chunk identity changes, while same-fingerprint
    rename cases can preserve eligible rows.
  - test: Extend `tests/test_semantic_stale_vector_cleanup.py` so stale-vector
    cleanup covers the paired SQLite mapping deletion plus any required summary
    invalidation/file-summary rotation for rename and delete flows.
  - test: Add coverage proving file-summary chunk ids are rotated or invalidated
    when a file path changes, rather than leaving orphaned semantic mappings
    behind.
  - impl: Add narrow store helpers that can delete or preserve
    `chunk_summaries` deterministically for a file/chunk set using stored
    `profile_id`, `prompt_fingerprint`, and audit metadata rather than blunt
    whole-table cleanup.
  - impl: Teach semantic cleanup helpers to return structured invalidation
    details that higher layers can consume when deciding whether a rename is
    same-content preservation or stale-summary invalidation.
  - impl: Keep the cleanup surface local and deterministic. Do not start
    rebuilding vectors or generating summaries in this lane.
  - verify: `uv run pytest tests/test_semantic_stale_vector_cleanup.py tests/test_sqlite_store.py -q --no-cov`

### SL-1 - Incremental Mutation Rebuild Orchestration

- **Scope**: Rewire incremental add/modify/delete/rename flows so they reuse
  the SEMPIPE semantic-build helper, invalidate stale summary/vector evidence
  first, and then regenerate summaries before strict re-embedding.
- **Owned files**: `mcp_server/indexing/incremental_indexer.py`, `mcp_server/dispatcher/dispatcher_enhanced.py`, `mcp_server/storage/git_index_manager.py`, `tests/test_incremental_indexer.py`, `tests/test_dispatcher.py`, `tests/test_git_index_manager.py`
- **Interfaces provided**: IF-0-SEMINCR-2; IF-0-SEMINCR-3 orchestration
  portion; additive incremental/full-sync semantic mutation stats that
  distinguish invalidated summaries, summaries regenerated, semantic vectors
  rewritten, semantic vectors deleted, and semantic rebuild blocked-by-preflight
- **Interfaces consumed**: SL-0 invalidation primitives; SEMPIPE ordered
  summary-first semantic helper and semantic-stage stats; SEMPREFLIGHT
  structured blocker contract; existing checkpointing and two-phase mutation
  behavior in `IncrementalIndexer`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_incremental_indexer.py` so modify flows delete
    stale summaries/vectors before reindex, prompt-fingerprint changes force
    summary regeneration, and same-content rename cases preserve only the
    compatible semantic evidence.
  - test: Add coverage for delete and rename mutations proving
    `chunk_summaries`, `semantic_points`, Qdrant point ids, and file-summary
    chunk ids are cleaned up or regenerated according to the new contract.
  - test: Extend `tests/test_dispatcher.py` so the incremental semantic path
    reuses the same summary-first strict semantic helper as full sync instead
    of calling an unrelated per-file semantic flow.
  - test: Extend `tests/test_git_index_manager.py` so incremental sync
    reporting surfaces semantic invalidation/regeneration outcomes additively
    without regressing lexical durability semantics.
  - impl: Extract or expose the SEMPIPE semantic-build sequence from
    `EnhancedDispatcher.index_directory(...)` as a shared helper consumable by
    incremental mutation paths.
  - impl: Update `IncrementalIndexer` modify/delete/rename flows so they call
    SL-0 invalidation first, then reindex/rebuild through the shared helper
    rather than directly drifting into ad hoc semantic cleanup plus lexical
    reindex.
  - impl: Preserve checkpointing, two-phase mutation safety, and lexical
    durability. This lane changes semantic mutation correctness, not the
    tracked-branch or artifact-sync policy.
  - impl: Keep semantic query routing unchanged; this lane must not leak
    SEMQUERY behavior forward.
  - verify: `uv run pytest tests/test_incremental_indexer.py tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov`

### SL-2 - Watcher Ctx-Repair And Mutation Entry Points

- **Scope**: Repair watcher-triggered mutation entry points so they call the
  ctx-aware dispatcher safely and preserve the same mutation semantics for
  single-repo and multi-repo watcher paths.
- **Owned files**: `mcp_server/watcher/file_watcher.py`, `mcp_server/watcher_multi_repo.py`, `tests/test_watcher.py`, `tests/test_watcher_multi_repo.py`
- **Interfaces provided**: IF-0-SEMINCR-4; watcher event handling that routes
  create/modify/delete/move through ctx-aware dispatcher calls without
  argument-shape regressions; success-only mutation signaling that remains
  compatible with tracked-branch and gitignore filtering
- **Interfaces consumed**: SL-0 invalidation semantics; SL-1 shared
  incremental semantic rebuild helper; existing `_Handler`,
  `MultiRepositoryHandler`, branch guards, gitignore filters, and mutation
  result/status contracts
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_watcher.py` so the single-repo watcher path proves
    `remove_file`, `index_file`, and `move_file` are called with the correct
    `RepoContext`-aware dispatcher shape and no longer raise argument errors.
  - test: Keep `tests/test_watcher_multi_repo.py` focused on branch/gitignore
    filtering and successful mutation truth, while adding regression coverage
    that watcher-triggered rename/remove flows preserve the same semantic
    cleanup contract as direct incremental indexing.
  - test: Add coverage proving watcher-triggered reindex first invalidates
    stale summaries/vectors and then rebuilds through the shared summary-first
    semantic path instead of bypassing it.
  - impl: Refactor `mcp_server/watcher/file_watcher.py` so its handler uses a
    resolved `RepoContext` or a narrow adapter layer rather than the legacy
    bare-path dispatcher signature.
  - impl: Align watcher remove/move/reindex flows with the mutation contract
    from SL-1 while preserving debounce behavior and excluding non-code paths.
  - impl: Do not introduce a new watcher backend or broaden into topology
    changes; keep this lane limited to mutation correctness and signature
    repair.
  - verify: `uv run pytest tests/test_watcher.py tests/test_watcher_multi_repo.py -q --no-cov`

### SL-3 - Docs And Contract Reducer

- **Scope**: Reduce the SEMINCR mutation contract into the operator-facing
  semantic guide and a narrow docs contract test without widening into query
  quality or dogfood rebuild work.
- **Owned files**: `docs/guides/semantic-onboarding.md`, `tests/docs/test_semincr_contract.py`
- **Interfaces provided**: concise operator-facing documentation that semantic
  incremental sync and watcher-triggered repairs preserve the same
  summary-first semantic contract as full sync; a docs contract test that
  freezes the phase boundary and the repaired watcher semantics
- **Interfaces consumed**: SL-0 invalidation vocabulary; SL-1 shared rebuild
  semantics; SL-2 watcher repair wording; roadmap SEMINCR exit criteria
- **Parallel-safe**: no
- **Tasks**:
  - test: Add `tests/docs/test_semincr_contract.py` asserting the docs state
    that changed chunks invalidate stale semantic evidence before re-embedding,
    deletes remove summaries plus vectors, and watcher-triggered mutation uses
    the same summary-first contract as full sync.
  - test: Require the docs contract to keep SEMINCR out of semantic query
    routing/ranking and dogfood rebuild claims.
  - impl: Update `docs/guides/semantic-onboarding.md` only as needed to explain
    the incremental mutation guarantee for semantic indexing, not to restate
    SEMQUERY or SEMDOGFOOD behavior early.
  - impl: Keep docs concise and contract-level. Do not add new operator
    workflow steps unless execution proves they are necessary.
  - verify: `uv run pytest tests/docs/test_semincr_contract.py -q --no-cov`

## Verification

Lane-specific checks:

```bash
uv run pytest tests/test_semantic_stale_vector_cleanup.py tests/test_sqlite_store.py -q --no-cov
uv run pytest tests/test_incremental_indexer.py tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov
uv run pytest tests/test_watcher.py tests/test_watcher_multi_repo.py -q --no-cov
uv run pytest tests/docs/test_semincr_contract.py -q --no-cov
rg -n "chunk_summaries|semantic_points|prompt_fingerprint|audit_metadata|delete_stale_vectors|index_directory|index_file\\(|remove_file\\(|move_file\\(|RepoContext|semantic_error|semantic_blocked" \
  mcp_server/storage/sqlite_store.py \
  mcp_server/utils/semantic_indexer.py \
  mcp_server/indexing/incremental_indexer.py \
  mcp_server/dispatcher/dispatcher_enhanced.py \
  mcp_server/storage/git_index_manager.py \
  mcp_server/watcher/file_watcher.py \
  mcp_server/watcher_multi_repo.py \
  docs/guides/semantic-onboarding.md \
  tests/test_sqlite_store.py \
  tests/test_semantic_stale_vector_cleanup.py \
  tests/test_incremental_indexer.py \
  tests/test_dispatcher.py \
  tests/test_git_index_manager.py \
  tests/test_watcher.py \
  tests/test_watcher_multi_repo.py \
  tests/docs/test_semincr_contract.py
```

Whole-phase regression commands:

```bash
uv run pytest \
  tests/test_semantic_stale_vector_cleanup.py \
  tests/test_sqlite_store.py \
  tests/test_incremental_indexer.py \
  tests/test_dispatcher.py \
  tests/test_git_index_manager.py \
  tests/test_watcher.py \
  tests/test_watcher_multi_repo.py \
  tests/docs/test_semincr_contract.py \
  -q --no-cov
git status --short -- specs/phase-plans-v7.md plans/phase-plan-v7-SEMINCR.md
```

## Acceptance Criteria

- [ ] Changed chunks invalidate stale authoritative summaries when chunk
      content, prompt fingerprint, enrichment contract/profile fingerprint, or
      equivalent semantic build metadata changes.
- [ ] Incremental modify/add/rename flows regenerate summaries before strict
      re-embedding and do so through the same ordered semantic helper used by
      full sync.
- [ ] Deleted chunks remove `chunk_summaries`, `semantic_points`, and Qdrant
      points where applicable.
- [ ] Rename behavior preserves existing summaries only when content hash and
      semantic fingerprint still match; otherwise the stale semantic evidence
      is invalidated and rebuilt.
- [ ] File watcher reindex/remove/move flows use ctx-aware dispatcher
      signatures and no longer raise `EnhancedDispatcher.remove_file()` or
      related argument errors.
- [ ] Tests cover add, modify, delete, rename, prompt-change invalidation, and
      watcher-triggered remove/reindex behavior.
- [ ] Incremental semantic repair stays bounded to mutation correctness and
      watcher repair: no semantic ranking changes, no query-routing rewrite,
      and no dogfood rebuild claims.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v7-SEMINCR.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMINCR.md
  artifact_state: staged
```
