---
phase_loop_plan_version: 1
phase: SEMCLOSEOUT
roadmap: specs/phase-plans-v7.md
roadmap_sha256: 8dca80257ba7c2e1566cfd801521b5eb976a5ee59c861af77a594bbe77ae7e80
---
# SEMCLOSEOUT: Post-Lexical Semantic Closeout

## Context

SEMCLOSEOUT is the phase-20 follow-up for the v7 semantic hardening roadmap.
SEMREADME cleared the final bounded lexical blocker on `README.md`, restored
indexed-commit freshness, and narrowed the remaining live repo-local blocker
to semantic closeout: authoritative summary generation plus strict semantic
vector linkage for the active `oss_high` profile.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is tracked and clean in this worktree, and the
  file bytes match the required
  `8dca80257ba7c2e1566cfd801521b5eb976a5ee59c861af77a594bbe77ae7e80`.
- `.phase-loop/state.json` already marks `SEMREADME` complete with
  verification passed at current `HEAD`
  `1cefea520d8bd80608bd69fbeaa8e5a056d58804`, and it marks `SEMCLOSEOUT`
  as the current unplanned phase for roadmap `specs/phase-plans-v7.md`.
- The checkout is on `main` at `1cefea520d8bd80608bd69fbeaa8e5a056d58804`,
  `main...origin/main` is ahead by 30 commits, the worktree is clean before
  writing this plan, and `plans/phase-plan-v7-SEMCLOSEOUT.md` did not exist
  before this run.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is the live blocker artifact for
  this phase. Its SEMREADME evidence records the exact downstream gap after a
  clean force-full rebuild: lexical readiness `ready`, query surface `ready`,
  active-profile preflight `ready`, semantic readiness `summaries_missing`,
  `chunk_summaries` `0`, `semantic_points` `0`, and the repo-local semantic
  dogfood harness skipping on `semantic_not_ready`.
- The current implementation already has the intended strict-path surfaces,
  but they are not closing the live rebuild: `mcp_server/indexing/summarization.py`
  owns authoritative summary backlog draining, `mcp_server/utils/semantic_indexer.py`
  owns strict summary-backed embedding input plus `semantic_points` linkage,
  `mcp_server/dispatcher/dispatcher_enhanced.py` owns the full semantic
  build sequence and stage accounting, and
  `mcp_server/storage/git_index_manager.py` owns force-full closeout and
  indexed-commit advancement.
- Existing tests already freeze much of the semantic-stage vocabulary:
  `tests/test_summarization.py` covers scoped backlog draining and large-file
  recovery, `tests/test_profile_aware_semantic_indexer.py` covers strict
  summary-backed batch indexing and semantic-point linkage, `tests/test_dispatcher.py`
  covers summary-pass retries plus semantic stage blockers, `tests/test_git_index_manager.py`
  carries those blockers through force-full closeout, and
  `tests/real_world/test_semantic_search.py` is the repo-local semantic-path
  acceptance harness.

Practical planning boundary:

- SEMCLOSEOUT may repair authoritative summary generation, strict semantic
  vector writes, full-sync closeout wiring, and the repo-local dogfood
  evidence needed to prove semantic readiness `ready` for this repository.
- SEMCLOSEOUT must stay narrowly on post-lexical semantic closeout. It must
  not reopen bounded Markdown timeout work, semantic ranking redesign, or any
  broader multi-repo rollout claims beyond this repo-local dogfood rebuild.

## Interface Freeze Gates

- [ ] IF-0-SEMCLOSEOUT-1 - Authoritative summary closeout contract:
      a clean repo-local force-full rebuild writes non-zero authoritative
      `chunk_summaries` for the active indexed repository instead of exiting
      with semantic readiness `summaries_missing`.
- [ ] IF-0-SEMCLOSEOUT-2 - Strict vector linkage contract:
      once summaries exist, strict semantic indexing writes non-zero
      `semantic_points` linked to `code_index__oss_high__v1`, and ready-path
      semantic responses expose `semantic_source: "semantic"` plus the active
      profile and collection metadata.
- [ ] IF-0-SEMCLOSEOUT-3 - Force-full closeout contract:
      `uv run mcp-index repository sync --force-full` advances through the
      semantic stage without silently degrading to lexical-only success, and
      `uv run mcp-index repository status` reports semantic readiness `ready`
      with current commit equal to indexed commit on the active profile.
- [ ] IF-0-SEMCLOSEOUT-4 - Evidence contract:
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` and
      `docs/guides/semantic-onboarding.md` record the semantic closeout rerun,
      durable summary and vector counts, semantic-path query evidence, and
      the final semantic-ready or exact still-blocked verdict.

## Lane Index & Dependencies

- SL-0 - Semantic closeout contract tests and regression freeze; Depends on: SEMREADME; Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 - Authoritative summary backlog drain repair; Depends on: SL-0; Blocks: SL-2, SL-3, SL-4; Parallel-safe: no
- SL-2 - Strict summary-backed semantic vector linkage repair; Depends on: SL-0, SL-1; Blocks: SL-3, SL-4; Parallel-safe: no
- SL-3 - Force-full semantic closeout orchestration and repo-local acceptance; Depends on: SL-0, SL-1, SL-2; Blocks: SL-4; Parallel-safe: no
- SL-4 - Dogfood evidence reducer and semantic-ready operator guide refresh; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: SEMCLOSEOUT acceptance; Parallel-safe: no

Lane DAG:

```text
SEMREADME
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SL-4 -> SEMCLOSEOUT acceptance
```

## Lanes

### SL-0 - Semantic Closeout Contract Tests And Regression Freeze

- **Scope**: Freeze the exact post-lexical semantic closeout expectations so
  the implementation must prove summary generation, vector linkage, and
  force-full semantic readiness rather than only preserving the old blocked
  vocabulary.
- **Owned files**: `tests/test_dispatcher.py`, `tests/test_git_index_manager.py`, `tests/test_summarization.py`, `tests/test_profile_aware_semantic_indexer.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMCLOSEOUT-1 through IF-0-SEMCLOSEOUT-3
- **Interfaces consumed**: existing
  `ComprehensiveChunkWriter.process_scope(...)`,
  `SemanticIndexer.index_files_batch(..., require_summaries=True)`,
  `EnhancedDispatcher.rebuild_semantic_for_paths(...)`,
  `EnhancedDispatcher.index_directory(...)`,
  `GitAwareIndexManager._full_index(...)`, and
  `GitAwareIndexManager.sync_repository_index(...)`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_summarization.py` so a repo-scope or target-scope
    summary backlog can only report success when authoritative summaries are
    actually persisted into `chunk_summaries`, not merely attempted.
  - test: Extend `tests/test_profile_aware_semantic_indexer.py` so strict
    summary-backed batch indexing proves non-zero `semantic_points` linkage
    for the active profile and collection when summaries are present.
  - test: Tighten `tests/test_dispatcher.py` so the full semantic rebuild path
    distinguishes the existing blocked states from a repaired semantic closeout
    that drains summaries and reaches `semantic_stage == "indexed"`.
  - test: Tighten `tests/test_git_index_manager.py` so force-full sync only
    advances the indexed commit when semantic closeout really succeeded, and
    still carries exact semantic-stage blockers forward when summary or vector
    writes remain incomplete.
  - impl: Keep fixtures deterministic with fake summary writers, fake semantic
    indexers, and SQLite-backed test stores rather than multi-minute live
    rebuilds inside unit coverage.
  - impl: Keep this lane focused on semantic closeout contracts only; do not
    update docs or the live dogfood report here.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_summarization.py tests/test_profile_aware_semantic_indexer.py -q --no-cov`

### SL-1 - Authoritative Summary Backlog Drain Repair

- **Scope**: Repair the authoritative summary generation path so the force-full
  rebuild can drain the repo-local unsummarized chunk backlog instead of
  exiting with zero summaries after lexical indexing already succeeded.
- **Owned files**: `mcp_server/indexing/summarization.py`
- **Interfaces provided**:
  `ComprehensiveChunkWriter._fetch_unsummarized_rows(...)`,
  `ComprehensiveChunkWriter.process_scope(...)`,
  `FileBatchSummarizer.summarize_file_chunks(...)`, and the authoritative
  `chunk_summaries` persistence contract for the active profile
- **Interfaces consumed**: SL-0 summary-closeout tests; existing summary
  prompt fingerprinting, profile batch recovery, large-file fallback, and
  SQLite `store_chunk_summary(...)` behavior
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 summarization slice first and confirm the current
    repo-scope closeout gap is representable as authoritative summaries not
    being durably written even though semantic preflight is already ready.
  - impl: Audit the unsummarized-row selection, per-file batching, persistence
    conditions, and multi-pass backlog drain loop so repeated summary passes
    actually reduce repo-local missing-summary counts for the targeted force-
    full scope.
  - impl: Preserve the existing profile-batch and topological recovery paths;
    do not widen this lane into prompt redesign or a new summary-only CLI.
  - impl: Keep authoritative summary audit fields coherent with the active
    profile so downstream semantic compatibility checks still have provider,
    profile, and prompt-fingerprint metadata.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_summarization.py -q --no-cov`

### SL-2 - Strict Summary-Backed Semantic Vector Linkage Repair

- **Scope**: Repair the strict semantic write path so summary-backed force-full
  indexing creates the expected vector records and SQLite-to-Qdrant linkages
  for `code_index__oss_high__v1` once authoritative summaries are available.
- **Owned files**: `mcp_server/utils/semantic_indexer.py`
- **Interfaces provided**:
  `SemanticIndexer._prepare_file_for_indexing(...)`,
  `SemanticIndexer.index_file(...)`,
  `SemanticIndexer.index_files_batch(..., require_summaries=True)`, and the
  `semantic_points` linkage contract for the active profile
- **Interfaces consumed**: SL-0 semantic indexer tests; SL-1 authoritative
  summaries in `chunk_summaries`; existing semantic profile resolution,
  Qdrant collection handling, file-summary chunk IDs, and SQLite
  `upsert_semantic_point(...)` behavior
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 strict-batch slice first and confirm current failures
    still block on missing summary-backed embeddings or missing point linkage
    rather than on lexical readiness.
  - impl: Audit the preparation-to-store path so strict batch indexing consumes
    authoritative summary text, emits embedding inputs for chunk, subchunk,
    and file-summary units as intended, and persists the corresponding
    `semantic_points` mappings for the active profile.
  - impl: Preserve fail-closed behavior when summaries are still missing or
    semantic preflight blocks vector writes; do not introduce lexical fallback
    in `semantic: true` runtime paths.
  - impl: Keep this lane local to strict semantic indexing and point linkage.
    Do not widen into semantic ranking heuristics or readiness-surface wording.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_profile_aware_semantic_indexer.py -q --no-cov`

### SL-3 - Force-Full Semantic Closeout Orchestration And Repo-Local Acceptance

- **Scope**: Carry the repaired summary and vector paths through the real
  force-full rebuild sequence so repo-local dogfood can prove semantic-path
  results on a fresh index instead of stopping at `semantic_not_ready`.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `mcp_server/storage/git_index_manager.py`, `tests/real_world/test_semantic_search.py`
- **Interfaces provided**: IF-0-SEMCLOSEOUT-2 ready-path semantic metadata
  contract; IF-0-SEMCLOSEOUT-3 force-full semantic closeout contract
- **Interfaces consumed**: SL-0 dispatcher and git-index-manager tests;
  SL-1 summary backlog drain behavior; SL-2 strict point-linkage behavior;
  existing `EnhancedDispatcher.rebuild_semantic_for_paths(...)`,
  `EnhancedDispatcher.index_directory(...)`,
  `GitAwareIndexManager._full_index(...)`,
  `GitAwareIndexManager.sync_repository_index(...)`, and the repo-local
  dogfood acceptance harness in
  `tests/real_world/test_semantic_search.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 dispatcher and git-index-manager slices first and
    confirm the current downstream failure is still the semantic closeout gap
    from SEMREADME rather than a reopened lexical blocker.
  - impl: Tighten the dispatcher semantic-stage accounting only as needed so a
    repaired summary/vector pass reports real closeout success, carries exact
    blocker details when it still fails, and never treats lexical-only success
    as semantic completion.
  - impl: Tighten `GitAwareIndexManager` only as needed so force-full closeout
    advances the indexed commit when semantic closeout succeeded and refuses
    advancement when the semantic stage is still blocked or partial.
  - impl: Update the repo-local dogfood harness so the SEMCLOSEOUT acceptance
    surface expects ready-path semantic results and metadata once semantic
    readiness reaches `ready`, while still preserving exact skips for any
    residual semantic blocker discovered during execution.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov`
  - verify: `RUN_REAL_WORLD_TESTS=1 SEMANTIC_SEARCH_ENABLED=true CODE_INDEX_DOGFOOD_REPO=. OPENAI_API_KEY=dummy-local-key uv run --extra dev python -m pytest tests/real_world/test_semantic_search.py -q --no-cov -k repo_local_dogfood_queries_stay_on_semantic_path -rs`
  - verify: `env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index index check-semantic`

### SL-4 - Dogfood Evidence Reducer And Semantic-Ready Operator Guide Refresh

- **Scope**: Re-run the repaired repo-local force-full sequence, reduce the
  live closeout outcome into the durable dogfood evidence artifact, and update
  operator guidance so semantic-ready closeout is clearly distinguished from
  the earlier lexical-blocked phases.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `docs/guides/semantic-onboarding.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: IF-0-SEMCLOSEOUT-4 evidence contract
- **Interfaces consumed**: SL-0 semantic-closeout wording; SL-1 authoritative
  summary evidence; SL-2 vector-linkage evidence; SL-3 rerun command,
  repository status, semantic preflight, and repo-local dogfood acceptance
  verdict
- **Parallel-safe**: no
- **Tasks**:
  - test: Update `tests/docs/test_semdogfood_evidence_contract.py` so the
    refreshed report must cite `plans/phase-plan-v7-SEMCLOSEOUT.md`, require
    non-zero summary and vector evidence or an exact residual semantic blocker,
    and require the semantic-path query outcome plus collection metadata.
  - impl: Re-run the repo-local force-full rebuild with the same strict
    watchdog posture used by SEMREADME, record whether semantic readiness now
    reaches `ready`, and capture current-versus-indexed commit evidence
    together with `chunk_summaries`, `semantic_points`, and semantic query
    outcomes.
  - impl: Refresh `docs/guides/semantic-onboarding.md` so operators can tell
    the difference between lexical-ready-but-semantic-blocked SEMREADME state
    and semantic-closeout-complete SEMCLOSEOUT state, including what exact
    evidence to inspect if the rebuild still blocks downstream.
  - impl: Keep this lane as the final reducer only. It must depend on every
    producer lane and must not speculate about semantic-ready status before the
    repaired rerun actually runs.
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
  - verify: `env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index index check-semantic`
  - verify: `RUN_REAL_WORLD_TESTS=1 SEMANTIC_SEARCH_ENABLED=true CODE_INDEX_DOGFOOD_REPO=. OPENAI_API_KEY=dummy-local-key uv run --extra dev python -m pytest tests/real_world/test_semantic_search.py -q --no-cov -k repo_local_dogfood_queries_stay_on_semantic_path -rs`

## Verification

Lane-focused verification sequence:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_summarization.py tests/test_profile_aware_semantic_indexer.py -q --no-cov
env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
env OPENAI_API_KEY=dummy-local-key uv run mcp-index index check-semantic
RUN_REAL_WORLD_TESTS=1 SEMANTIC_SEARCH_ENABLED=true CODE_INDEX_DOGFOOD_REPO=. OPENAI_API_KEY=dummy-local-key uv run --extra dev python -m pytest tests/real_world/test_semantic_search.py -q --no-cov -k repo_local_dogfood_queries_stay_on_semantic_path -rs
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
```

Whole-phase regression guard:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_summarization.py tests/test_profile_aware_semantic_indexer.py -q --no-cov
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
RUN_REAL_WORLD_TESTS=1 SEMANTIC_SEARCH_ENABLED=true CODE_INDEX_DOGFOOD_REPO=. OPENAI_API_KEY=dummy-local-key uv run --extra dev python -m pytest tests/real_world/test_semantic_search.py -q --no-cov -k repo_local_dogfood_queries_stay_on_semantic_path -rs
```

## Acceptance Criteria

- [ ] A clean `uv run mcp-index repository sync --force-full` ends with
      current commit equal to indexed commit and does not stop at
      semantic readiness `summaries_missing`.
- [ ] The same rebuild produces non-zero authoritative `chunk_summaries` for
      the active indexed repository and non-zero `semantic_points` linked to
      `code_index__oss_high__v1`.
- [ ] `uv run mcp-index repository status` reports semantic readiness `ready`
      for the active `oss_high` profile, while preserving lexical readiness
      and query-surface `ready`.
- [ ] The repo-local semantic dogfood harness returns semantic-path results
      with `semantic_source: "semantic"`,
      `semantic_profile_id: "oss_high"`, and
      `semantic_collection_name: "code_index__oss_high__v1"` instead of
      skipping on `semantic_not_ready`.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the semantic closeout
      rerun, summary and vector evidence, semantic query outcome, and the
      final semantic-ready or exact still-blocked verdict on the current
      commit.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v7-SEMCLOSEOUT.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMCLOSEOUT.md
  artifact_state: staged
```
