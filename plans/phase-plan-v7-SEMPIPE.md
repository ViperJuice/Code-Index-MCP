---
phase_loop_plan_version: 1
phase: SEMPIPE
roadmap: specs/phase-plans-v7.md
roadmap_sha256: b8ba13bf3898d59c087f64193fa7415b0f932b34fc002e862d2678d74c1faf0c
---
# SEMPIPE: Enrichment-First Full Semantic Pipeline

## Context

SEMPIPE is the phase-4 execution slice for the v7 semantic hardening roadmap.
It is the first phase allowed to run real enrichment and vector-write paths,
but it must do so fail-closed: summaries are mandatory input for semantic
indexing, while lexical/chunk indexing stays durable even when semantic writes
cannot proceed.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is tracked and clean in this worktree, and its live
  SHA matches the required
  `b8ba13bf3898d59c087f64193fa7415b0f932b34fc002e862d2678d74c1faf0c`.
- The checkout is on `main` at `82e0472`, and the worktree is clean before
  writing this plan.
- `plans/phase-plan-v7-SEMCONTRACT.md`,
  `plans/phase-plan-v7-SEMCONFIG.md`, and
  `plans/phase-plan-v7-SEMPREFLIGHT.md` already exist as the upstream v7 phase
  plans. SEMPIPE must consume their split semantic-readiness vocabulary,
  selected-profile config, and structured semantic preflight blocker instead of
  inventing a parallel contract.
- `GitAwareIndexManager._full_index(...)` currently delegates straight to
  `EnhancedDispatcher.index_directory(...)` and treats durable lexical rows as
  the only success gate. There is no mandatory "summaries before vectors" stage
  inside the full-sync path.
- `EnhancedDispatcher.index_directory(...)` currently persists lexical shards
  for each file, accumulates successful paths, and then calls
  `SemanticIndexer.index_files_batch(...)` directly. That semantic batch has no
  required summarization prerequisite and reports only aggregate semantic
  counts/errors back to the caller.
- `SemanticIndexer._prepare_file_for_indexing(...)` already injects
  `chunk_summaries.summary_text` into embedding text when a summary exists, but
  missing summaries simply produce embedding inputs without them. In other
  words, summary enrichment is opportunistic today, not required.
- `SemanticIndexer._store_file_embeddings(...)` upserts Qdrant points for chunk
  embeddings and file-summary embeddings, but unlike `index_symbol(...)` it
  does not persist `semantic_points` mappings for the source chunks that were
  actually written. That leaves `chunk_summaries` and Qdrant content
  insufficiently linked for durable readiness evidence.
- `ComprehensiveChunkWriter.process_all(...)` and `FileBatchSummarizer` already
  know how to generate authoritative summaries grouped by file, but they are
  only exposed through the explicit `write_summaries` / `summarize_sample`
  tool-handler surfaces. Full reindex does not require or reuse them.
- `handle_reindex(...)` already returns additive semantic counters from
  `index_directory(...)`, and `handle_write_summaries(...)` already exposes the
  standalone summary writer. SEMPIPE should align those operator surfaces with
  the new full-build contract instead of silently changing them.
- `mcp_server/indexing/summarization.py` persists `llm_model`, but there is no
  stronger audit/invalidation payload yet for provider/profile/prompt identity.
  The roadmap exit criteria require summary rows to record enough metadata for
  audit and later invalidation decisions.

Practical planning boundary:

- SEMPIPE may rewire the full sync path so enrichment is required before
  semantic vector writes, may persist stronger summary/vector linkage metadata,
  and may update operator-facing reindex/docs surfaces to describe that
  behavior.
- SEMPIPE must not widen into watcher/incremental mutation repair, semantic
  ranking changes, release dispatch, or the clean-rebuild dogfood proof. Those
  belong to SEMINCR, SEMQUERY, and SEMDOGFOOD.

## Interface Freeze Gates

- [ ] IF-0-SEMPIPE-1 - Full-sync summary prerequisite contract:
      `GitAwareIndexManager` full sync and `EnhancedDispatcher.index_directory`
      run the semantic build in three ordered stages for semantic-enabled
      repos: lexical/chunk persistence, authoritative summary generation for
      the targeted chunks/files, then semantic embedding/upsert. The vector
      stage must not run until the summary stage proves coverage for the chunks
      being embedded.
- [ ] IF-0-SEMPIPE-2 - Strict semantic embedding contract:
      `SemanticIndexer.index_file(...)` and
      `SemanticIndexer.index_files_batch(...)` can run in a strict
      summary-required mode used by full sync. In that mode, missing summaries
      or active SEMPREFLIGHT blockers refuse Qdrant writes rather than falling
      back to code-only embeddings.
- [ ] IF-0-SEMPIPE-3 - Durable linkage and audit contract:
      semantic writes persist `semantic_points` mappings for the source chunks
      they index, and summary rows store enough audit metadata to answer which
      enrichment provider/model/profile/prompt contract produced the summary
      used for the vector.
- [ ] IF-0-SEMPIPE-4 - Partial-success contract:
      when enrichment or strict semantic embedding fails, lexical/chunk
      indexing may still complete and remain durable, but semantic vectors are
      not advanced for the affected chunks, semantic readiness remains
      not-ready, and tool/reporting surfaces expose the semantic blocker
      explicitly.
- [ ] IF-0-SEMPIPE-5 - Manual surface contract:
      `write_summaries` stays an explicit summary-only tool, `summarize_sample`
      stays a diagnostic/sample tool, and `reindex` reports whether the
      semantic stage wrote vectors, was blocked before writes, or failed after
      lexical persistence. Lazy search-triggered summaries must not count as
      satisfying the full-sync semantic contract.

## Lane Index & Dependencies

- SL-0 - Authoritative summary generation and audit metadata; Depends on: (none); Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 - Strict semantic embedding and durable point linkage; Depends on: SL-0; Blocks: SL-2, SL-3, SL-4; Parallel-safe: no
- SL-2 - Full-sync orchestration and partial-success accounting; Depends on: SL-0, SL-1; Blocks: SL-3, SL-4; Parallel-safe: no
- SL-3 - Tool-handler semantic-build surfacing; Depends on: SL-0, SL-1, SL-2; Blocks: SL-4; Parallel-safe: no
- SL-4 - Docs and contract reducer; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: SEMINCR; Parallel-safe: no

Lane DAG:

```text
SL-0 --> SL-1 --> SL-2 --> SL-3 --> SL-4 --> SEMINCR
   \         \        \        \
    `---------`--------`--------> contract inputs only
```

## Lanes

### SL-0 - Authoritative Summary Generation And Audit Metadata

- **Scope**: Turn the existing batch summarizers into the full-pipeline summary
  prerequisite and persist stronger summary audit metadata through a shared
  SQLite-backed path instead of ad hoc inserts.
- **Owned files**: `mcp_server/indexing/summarization.py`, `mcp_server/storage/sqlite_store.py`, `tests/test_summarization.py`
- **Interfaces provided**: IF-0-SEMPIPE-1 summary-stage portion;
  IF-0-SEMPIPE-3 summary-audit portion; a structured summary-generation result
  from `ComprehensiveChunkWriter` or a shared helper that reports files/chunks
  attempted, summaries written, and chunks left unsummarized for the targeted
  build scope
- **Interfaces consumed**: SEMCONFIG selected-profile summarization config;
  existing `ComprehensiveChunkWriter.process_all(...)`,
  `FileBatchSummarizer.summarize_file_chunks(...)`,
  `ChunkWriter._get_model_name()`, `SQLiteStore.get_missing_summaries(...)`,
  and current `chunk_summaries` persistence behavior
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_summarization.py` beyond constructor coverage so
    the full-pipeline writer can be exercised with grouped file chunks,
    authoritative summary persistence, and explicit "missing summary"
    accounting when the summarizer cannot produce output.
  - test: Add coverage proving the shared full-pipeline summary helper records
    enough metadata for audit/invalidation decisions, not only bare
    `llm_model`.
  - test: Add regression coverage proving the batch writer continues to prefer
    file-grouped summaries and falls back cleanly without silently marking
    missing summaries as authoritative success.
  - impl: Refactor the summary writer so the full semantic build path can call
    one shared helper that returns structured counts/details instead of only an
    integer.
  - impl: Move summary persistence behind a shared SQLite helper path so
    authoritative summaries and their audit metadata are written consistently,
    whether they come from the explicit tool or from full sync.
  - impl: Persist summary metadata that identifies the enrichment contract used
    for the row: at minimum provider/model identity plus the active semantic
    profile or prompt/fingerprint input needed for later invalidation.
  - impl: Keep `write_summaries` reusable on top of the same helper, but do not
    make lazy search-triggered background summarization satisfy the strict
    full-sync semantic prerequisite.
  - verify: `uv run pytest tests/test_summarization.py -q --no-cov`

### SL-1 - Strict Semantic Embedding And Durable Point Linkage

- **Scope**: Make semantic indexing consume authoritative summaries as required
  input during full sync, refuse writes when they are missing, and persist the
  SQLite chunk-to-point linkage for every written vector.
- **Owned files**: `mcp_server/utils/semantic_indexer.py`, `tests/test_profile_aware_semantic_indexer.py`
- **Interfaces provided**: IF-0-SEMPIPE-2; IF-0-SEMPIPE-3 vector-linkage
  portion; strict semantic build helpers in `SemanticIndexer.index_file(...)`
  and `SemanticIndexer.index_files_batch(...)` or a shared internal helper that
  can require summaries and consume the active semantic preflight blocker
- **Interfaces consumed**: SL-0 authoritative summary metadata and structured
  missing-summary results; SEMPREFLIGHT structured blocker contract;
  existing `_prepare_file_for_indexing(...)`, `_store_file_embeddings(...)`,
  `delete_stale_vectors(...)`, and `SQLiteStore.upsert_semantic_point(...)`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_profile_aware_semantic_indexer.py` so strict-mode
    semantic indexing refuses Qdrant upserts when a source chunk lacks an
    authoritative summary.
  - test: Add coverage proving chunk embedding text includes both
    `summary_text` and bounded chunk context in strict full-sync mode.
  - test: Add coverage proving successful strict batch indexing persists
    `semantic_points` mappings for each source chunk and keeps file-summary
    points distinct from chunk-level linkage.
  - test: Add coverage proving an active semantic preflight blocker prevents
    vector writes before any Qdrant upsert occurs.
  - impl: Introduce a strict summary-required semantic build path for full
    sync, rather than letting missing summaries degrade to code-only embedding
    text.
  - impl: Update the batch store path so successful chunk embeddings upsert the
    corresponding `semantic_points` mapping rows for the active profile and
    collection.
  - impl: Keep semantic search/query ranking behavior unchanged; this lane owns
    build-time semantic correctness, not retrieval policy.
  - impl: Ensure failure paths remain fail-closed: if strict prerequisites are
    not met, do not write partial vectors for the affected file/chunks.
  - verify: `uv run pytest tests/test_profile_aware_semantic_indexer.py -q --no-cov`

### SL-2 - Full-Sync Orchestration And Partial-Success Accounting

- **Scope**: Wire the lexical indexer, summary stage, strict semantic stage,
  and semantic preflight blocker into one ordered full-sync flow while keeping
  lexical durability behavior intact.
- **Owned files**: `mcp_server/storage/git_index_manager.py`, `mcp_server/dispatcher/dispatcher_enhanced.py`, `tests/test_git_index_manager.py`, `tests/test_dispatcher.py`
- **Interfaces provided**: IF-0-SEMPIPE-1 orchestration order; IF-0-SEMPIPE-4;
  additive semantic build stats from `index_directory(...)` / `_full_index(...)`
  that distinguish semantic success, semantic blocked-before-write, and
  semantic failure after lexical persistence
- **Interfaces consumed**: SL-0 structured summary-stage result; SL-1 strict
  semantic embedding helper; SEMPREFLIGHT structured blocker contract; existing
  lexical persistence in `index_file(...)`, `index_directory(...)`, and
  `_full_index(...)`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` so `index_directory(...)` proves
    lexical indexing happens first, then the authoritative summary stage, then
    the strict semantic batch only when summaries and preflight allow it.
  - test: Add dispatcher coverage proving no Qdrant batch upsert happens when
    summaries are missing or when the semantic preflight blocker says vectors
    cannot be written.
  - test: Extend `tests/test_git_index_manager.py` so a full reindex can remain
    lexically successful while surfacing semantic blocked/failure stats
    additively, without claiming semantic readiness.
  - test: Add regression coverage proving semantic-stage failure does not erase
    durable lexical rows or silently increment semantic success counters.
  - impl: Refactor `EnhancedDispatcher.index_directory(...)` so full-directory
    semantic work runs through the ordered summary-required pipeline instead of
    calling `SemanticIndexer.index_files_batch(...)` directly on fresh lexical
    paths.
  - impl: Consume the SEMPREFLIGHT blocker before vector writes and expose
    semantic-stage outcomes through explicit stats such as summaries written,
    semantic blocked, semantic indexed, semantic failed, and semantic error.
  - impl: Keep lexical row durability and commit/update behavior aligned with
    the v6 local-index contract: lexical indexing may succeed independently, but
    semantic readiness must remain not-ready when the semantic stage was
    blocked or incomplete.
  - impl: Do not pull watcher/incremental repair forward here; SEMINCR should
    reuse this ordered helper later instead of duplicating it.
  - verify: `uv run pytest tests/test_git_index_manager.py tests/test_dispatcher.py -q --no-cov`

### SL-3 - Tool-Handler Semantic-Build Surfacing

- **Scope**: Keep repo/tool surfaces aligned with the new full-sync contract so
  operators can tell whether semantic vectors were written, blocked, or skipped
  without conflating that with manual summary tools or semantic query readiness.
- **Owned files**: `mcp_server/cli/tool_handlers.py`, `tests/test_tool_handlers_readiness.py`
- **Interfaces provided**: IF-0-SEMPIPE-5; `reindex` response fields that
  report the semantic build stage outcome; `write_summaries` remaining
  summary-only while reusing the shared summary helper contract
- **Interfaces consumed**: SL-0 shared summary helper/result; SL-2 additive
  semantic build stats; existing `handle_reindex(...)`,
  `handle_write_summaries(...)`, `_semantic_not_ready_response(...)`, and
  `handle_summarize_sample(...)`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_tool_handlers_readiness.py` so `handle_reindex`
    reports additive semantic-stage metadata when lexical indexing succeeded
    but semantic vector writes were blocked or skipped.
  - test: Add coverage proving `handle_write_summaries` remains a summary-only
    operation and does not claim vector-write success.
  - test: Preserve the existing `semantic_not_ready` search response contract
    for query-time readiness failures; SEMPIPE should not collapse build-time
    reporting into query-time refusal semantics.
  - impl: Thread the new semantic summary/vector stage stats from
    `index_directory(...)` into `handle_reindex(...)` so operators see whether
    semantic vectors were written, blocked before write, or failed after
    lexical persistence.
  - impl: Reuse the SL-0 shared summary helper for `write_summaries`, but keep
    that tool explicitly summary-only and keep `summarize_sample` explicitly
    diagnostic/sample-only.
  - impl: Avoid widening into query ranking or repository readiness policy
    changes beyond the additive build metadata needed for SEMPIPE.
  - verify: `uv run pytest tests/test_tool_handlers_readiness.py -q --no-cov`

### SL-4 - Docs And Contract Reducer

- **Scope**: Reduce the new full-sync semantic-build contract into operator
  docs and a docs-level guard so SEMINCR inherits the same expectations instead
  of reverse-engineering them from code.
- **Owned files**: `docs/guides/semantic-onboarding.md`, `docs/tools/cli-setup-reference.md`, `tests/docs/test_sempipe_contract.py`
- **Interfaces provided**: docs that state full reindex now requires
  summaries-before-vectors for semantic mode, lexical success can coexist with
  semantic blocked/not-ready state, and manual summary tools remain distinct
- **Interfaces consumed**: SL-0 summary-stage contract; SL-2 additive semantic
  build stats and failure/blocked semantics; SL-3 tool-surface wording; roadmap
  SEMPIPE exit criteria
- **Parallel-safe**: no
- **Tasks**:
  - test: Add a docs contract test that requires semantic onboarding/setup docs
    to name the ordered full-sync pipeline: lexical/chunk persistence,
    authoritative summaries, then semantic vector writes.
  - test: Require docs to state that semantic vector writes are skipped when
    summaries are missing or preflight blocks the active profile, while lexical
    indexing may still complete.
  - test: Require docs to keep `write_summaries` and `summarize_sample`
    described as explicit/manual tools rather than as implicit full-sync
    substitutes.
  - impl: Update `docs/guides/semantic-onboarding.md` so operators understand
    what `reindex` now does in semantic mode and why semantic readiness can lag
    lexical readiness after a blocked enrichment/vector stage.
  - impl: Update `docs/tools/cli-setup-reference.md` so the setup/reindex
    workflow names the semantic-build stages and the difference between manual
    summary generation and full semantic sync.
  - impl: Keep docs bounded to the SEMPIPE build contract. Do not pull watcher
    invalidation or semantic ranking claims forward from later phases.
  - verify: `uv run pytest tests/docs/test_sempipe_contract.py -q --no-cov`
  - verify: `rg -n "write_summaries|summarize_sample|summary|semantic vector|reindex|lexical readiness|semantic readiness" docs/guides/semantic-onboarding.md docs/tools/cli-setup-reference.md tests/docs/test_sempipe_contract.py`

## Verification

Planning-only run: do not execute these during plan creation. Run them during
`codex-execute-phase` or manual SEMPIPE execution.

Lane-specific checks:

```bash
uv run pytest tests/test_summarization.py -q --no-cov
uv run pytest tests/test_profile_aware_semantic_indexer.py -q --no-cov
uv run pytest tests/test_git_index_manager.py tests/test_dispatcher.py -q --no-cov
uv run pytest tests/test_tool_handlers_readiness.py -q --no-cov
uv run pytest tests/docs/test_sempipe_contract.py -q --no-cov
rg -n "ComprehensiveChunkWriter|FileBatchSummarizer|semantic_points|summary_text|write_summaries|semantic_error|semantic_blocked|semantic_paths_queued|can_write_semantic_vectors" \
  mcp_server/indexing/summarization.py \
  mcp_server/storage/sqlite_store.py \
  mcp_server/utils/semantic_indexer.py \
  mcp_server/storage/git_index_manager.py \
  mcp_server/dispatcher/dispatcher_enhanced.py \
  mcp_server/cli/tool_handlers.py \
  docs/guides/semantic-onboarding.md \
  docs/tools/cli-setup-reference.md \
  tests/test_summarization.py \
  tests/test_profile_aware_semantic_indexer.py \
  tests/test_git_index_manager.py \
  tests/test_dispatcher.py \
  tests/test_tool_handlers_readiness.py \
  tests/docs/test_sempipe_contract.py
```

Whole-phase regression commands:

```bash
uv run pytest \
  tests/test_summarization.py \
  tests/test_profile_aware_semantic_indexer.py \
  tests/test_git_index_manager.py \
  tests/test_dispatcher.py \
  tests/test_tool_handlers_readiness.py \
  tests/docs/test_sempipe_contract.py \
  -q --no-cov
git status --short -- specs/phase-plans-v7.md plans/phase-plan-v7-SEMPIPE.md
```

## Acceptance Criteria

- [ ] Full semantic sync runs in order: lexical/chunk persistence first,
      authoritative summaries second, semantic vector writes third.
- [ ] `chunk_summaries` is populated for the targeted semantic build scope
      before Qdrant embedding/upsert begins.
- [ ] Strict semantic build mode refuses Qdrant writes when summaries are
      missing or the active semantic preflight blocker says vectors cannot be
      written.
- [ ] Semantic embedding input includes `summary_text` plus bounded chunk
      context rather than silently falling back to code-only embedding text in
      full-sync mode.
- [ ] Successful semantic writes persist `semantic_points` mappings for the
      source chunks they indexed.
- [ ] Summary rows store audit/invalidation metadata sufficient to identify the
      enrichment contract used for that summary.
- [ ] If enrichment or strict semantic embedding fails, lexical/chunk indexing
      may still complete, but semantic vectors are not advanced for the
      affected chunks/files and semantic readiness remains not-ready.
- [ ] `reindex` reports the semantic build outcome additively, while
      `write_summaries` and `summarize_sample` remain explicit manual tools
      rather than implicit substitutes for full semantic sync.
- [ ] Tests prove no Qdrant upsert occurs when summaries are missing in the
      strict full-sync path.
- [ ] SEMPIPE stays limited to the full build path: no watcher/incremental
      invalidation repair, no semantic ranking changes, and no release work.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v7-SEMPIPE.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMPIPE.md
  artifact_state: staged
```
