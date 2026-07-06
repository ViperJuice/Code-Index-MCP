---
phase_loop_plan_version: 1
phase: SEMSYNCFIX
roadmap: specs/phase-plans-v7.md
roadmap_sha256: d562f158dc3a6881b53d797ba16a9d935d698ac00e5466664bb30b74be656372
---
# SEMSYNCFIX: Full Sync Summary Coverage Recovery

## Context

SEMSYNCFIX is the phase-11 blocker-repair follow-up for the v7 semantic
hardening roadmap. SEMSUMFIX repaired the direct authoritative summary
runtime for the default local `oss_high` path, but the real
`repository sync --force-full` flow still leaves this repo at
`summaries_missing` and never advances semantic vector writes.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is tracked and clean in this worktree, and its
  live SHA matches the required
  `d562f158dc3a6881b53d797ba16a9d935d698ac00e5466664bb30b74be656372`.
- The checkout is on `main` at `fdc3096d886b`, `main...origin/main` is ahead
  by 12 commits, and `plans/phase-plan-v7-SEMSYNCFIX.md` did not exist before
  this run.
- The upstream v7 planning chain already exists through
  `plans/phase-plan-v7-SEMSUMFIX.md`; SEMSYNCFIX must consume the semantic
  readiness split, enrichment compatibility repair, collection bootstrap
  repair, authoritative summary fallback repair, strict summary-before-vector
  ordering, and semantic-only query contract frozen by SEMCONTRACT through
  SEMSUMFIX instead of redefining them.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` now proves the remaining blocker
  precisely: the 2026-04-28 force-full rebuild completed successfully and
  indexed `1379` files, but immediately after the rebuild
  `chunk_summaries=5`, `semantic_points=0`, semantic readiness remained
  `summaries_missing`, and repo-local semantic queries still fail closed with
  `code: "semantic_not_ready"`.
- The same evidence artifact also proves the repaired direct path works
  outside the force-full flow: post-rebuild manual
  `ComprehensiveChunkWriter.process_scope(...)` probes raised
  `chunk_summaries` from `5` to `125` without changing `semantic_points`,
  which isolates the remaining defect to full-sync summary coverage or the
  strict semantic-stage handoff rather than the repaired summary runtime
  itself.
- `mcp_server/dispatcher/dispatcher_enhanced.py` currently routes a full
  directory rebuild through `index_directory(...)`, collects
  `semantically_indexed_paths`, then calls
  `rebuild_semantic_for_paths(...)`, which runs one scoped
  `ComprehensiveChunkWriter.process_scope(...)` pass before semantic
  preflight and vector indexing. If that pass leaves any
  `missing_chunk_ids`, the strict semantic stage exits with
  `semantic_stage="blocked_missing_summaries"`.
- `mcp_server/indexing/summarization.py` already has the repaired
  authoritative runtime and path-scoped summary writer, but
  `ComprehensiveChunkWriter._fetch_unsummarized_rows(...)` and
  `process_scope(...)` do not yet have explicit contract coverage for the
  full-rebuild case where thousands of chunks must be drained under the
  same scoped path set used by the dispatcher.
- `mcp_server/storage/git_index_manager.py` already preserves additive
  semantic stats from `index_directory(...)`, but its tests only freeze the
  blocked semantic-stage aggregate, not the repaired full-sync success case
  where summary coverage advances far enough for semantic readiness to become
  `ready`.
- `tests/test_dispatcher.py`, `tests/test_git_index_manager.py`, and
  `tests/test_summarization.py` already cover the strict summary gate, the
  additive semantic stats, and the repaired summary fallback path, but they
  do not yet prove the full-sync directory flow drains repo-wide summary work
  or that the semantic stage retries or continues correctly when more than one
  scoped summary pass is needed.
- `tests/real_world/test_semantic_search.py`,
  `tests/docs/test_semdogfood_evidence_contract.py`, and
  `docs/guides/semantic-onboarding.md` remain the repo-local dogfood and
  operator evidence surfaces that must flip from "direct summary repair only"
  to a real semantic-ready rebuild verdict.

Practical planning boundary:

- SEMSYNCFIX may repair the full-sync summary drain in the dispatcher,
  summarizer, or tightly related full-index accounting path, rerun the clean
  rebuild, prove summary coverage now advances far enough for vector writes,
  and refresh the dogfood evidence plus concise operator guidance.
- SEMSYNCFIX must stay narrowly on the real full-sync summary coverage gap,
  strict semantic-stage continuation, and the evidence needed to prove the
  repaired rebuild. It must not widen into semantic ranking redesign,
  multi-repo rollout expansion, or unrelated profile/provider changes already
  handled by SEMREADYFIX, SEMCOLLECT, and SEMSUMFIX.

## Interface Freeze Gates

- [ ] IF-0-SEMSYNCFIX-1 - Full-sync summary drain contract:
      `index_directory(...)` plus `rebuild_semantic_for_paths(...)` must drain
      authoritative summaries for the scoped force-full rebuild well beyond
      the current manual-probe-only baseline instead of stopping after a
      partial inline summary pass.
- [ ] IF-0-SEMSYNCFIX-2 - Strict semantic-stage continuation contract:
      once authoritative summaries are fully available for the scoped rebuild,
      the same force-full flow must advance into semantic vector writes for
      `code_index__oss_high__v1` without requiring a manual
      `ComprehensiveChunkWriter.process_scope(...)` intervention.
- [ ] IF-0-SEMSYNCFIX-3 - Full-sync accounting contract:
      dispatcher and full-index stats must surface whether semantic work was
      blocked on missing summaries, fully indexed, or still blocked for some
      other exact reason, and the repaired path must leave repository status
      at semantic readiness `ready`.
- [ ] IF-0-SEMSYNCFIX-4 - Dogfood evidence contract:
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` and
      `docs/guides/semantic-onboarding.md` must record the repaired full-sync
      path, the post-rebuild `chunk_summaries` and `semantic_points` counts,
      the semantic-ready verdict, and how to distinguish a repaired force-full
      rebuild from the earlier "manual probe works, sync still blocked" state.

## Lane Index & Dependencies

- SL-0 - Full-sync summary coverage contract tests; Depends on: SEMSUMFIX; Blocks: SL-1, SL-2; Parallel-safe: no
- SL-1 - Force-full summary drain and semantic-stage recovery implementation; Depends on: SL-0; Blocks: SL-2, SL-3; Parallel-safe: no
- SL-2 - Semantic-ready rebuild acceptance harness; Depends on: SL-0, SL-1; Blocks: SL-3; Parallel-safe: no
- SL-3 - Dogfood evidence reducer and operator guide refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SEMSYNCFIX acceptance; Parallel-safe: no

Lane DAG:

```text
SEMSUMFIX
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SEMSYNCFIX acceptance
```

## Lanes

### SL-0 - Full-Sync Summary Coverage Contract Tests

- **Scope**: Freeze the real force-full summary coverage failure before
  mutating runtime code so the repaired path proves summary drain and strict
  semantic-stage continuation under directory-scale indexing, not just manual
  probes.
- **Owned files**: `tests/test_summarization.py`, `tests/test_dispatcher.py`, `tests/test_git_index_manager.py`
- **Interfaces provided**: executable assertions for IF-0-SEMSYNCFIX-1,
  IF-0-SEMSYNCFIX-2, and IF-0-SEMSYNCFIX-3
- **Interfaces consumed**: existing
  `ComprehensiveChunkWriter._fetch_unsummarized_rows(...)`,
  `ComprehensiveChunkWriter.process_scope(...)`,
  `EnhancedDispatcher.rebuild_semantic_for_paths(...)`,
  `EnhancedDispatcher.index_directory(...)`,
  `GitAwareIndexManager._full_index(...)`, and the SEMSUMFIX runtime fallback
  contract already frozen in `tests/test_summarization.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_summarization.py` with a deterministic scoped
    summary-coverage case that proves the full-sync summary writer can drain
    all targeted unsummarized chunks for a repo-shaped path set instead of
    reporting success after only a tiny partial subset.
  - test: Extend `tests/test_dispatcher.py` so
    `rebuild_semantic_for_paths(...)` proves one repaired force-full flow can
    continue from summary generation into semantic indexing when the scoped
    summary pass actually drains the targeted chunks, and still emits the
    exact blocker when it does not.
  - test: Extend `tests/test_git_index_manager.py` with a repaired full-index
    aggregate case that requires additive semantic stats for a semantic-ready
    rebuild instead of only freezing the current
    `blocked_missing_summaries` outcome.
  - impl: Keep the fixtures deterministic and local by faking summary rows,
    dispatcher results, and semantic-indexer outputs instead of depending on a
    live rebuild inside unit coverage.
  - impl: Keep this lane limited to summary-coverage and strict-stage
    contracts; do not widen it into semantic ranking or query-routing
    semantics.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_summarization.py tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov`

### SL-1 - Force-Full Summary Drain And Semantic-Stage Recovery Implementation

- **Scope**: Repair the inline force-full semantic path so directory-scale
  rebuilds drain authoritative summaries far enough for strict vector writes
  and semantic readiness to complete without manual post-sync probes.
- **Owned files**: `mcp_server/indexing/summarization.py`, `mcp_server/dispatcher/dispatcher_enhanced.py`, `mcp_server/storage/git_index_manager.py`
- **Interfaces provided**: IF-0-SEMSYNCFIX-1 full-sync summary drain
  contract; IF-0-SEMSYNCFIX-2 strict semantic-stage continuation contract;
  IF-0-SEMSYNCFIX-3 full-sync accounting contract
- **Interfaces consumed**: SL-0 contract tests; existing SEMSUMFIX
  authoritative summary fallback path; existing semantic preflight and active
  collection bootstrap metadata; existing additive semantic stats plumbing
  from dispatcher to `GitAwareIndexManager`
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 unit slice first and confirm it reproduces the current
    force-full semantic-stage gap before changing dispatcher or summarizer
    behavior.
  - impl: Choose one deterministic repair path for the inline full-sync
    summary drain and keep it singular: for example, fix scoped summary
    selection so the rebuild sees all targeted unsummarized chunks, or allow
    the strict semantic stage to continue summary passes until the scoped
    force-full set is actually drained before declaring
    `blocked_missing_summaries`.
  - impl: Keep the summary-stage repair tied to the existing scoped rebuild
    contract in `rebuild_semantic_for_paths(...)`; do not introduce a second
    separate semantic rebuild workflow just to make the dogfood path pass.
  - impl: Preserve the strict summary-before-vector ordering and fail-closed
    behavior for genuine residual blockers. The repaired path should only
    continue into vector writes when the active scoped rebuild really has the
    authoritative summaries it needs.
  - impl: Preserve additive semantic accounting through
    `GitAwareIndexManager._full_index(...)` so operators can distinguish
    summary drain, semantic indexing, and residual blockage from one canonical
    force-full result surface.
  - impl: Do not widen into new profile flags, new summary runtimes, or
    unrelated repository status taxonomy changes.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_summarization.py tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - verify: `sqlite3 .mcp-index/current.db 'select count(*) as chunk_summaries from chunk_summaries; select count(*) as semantic_points from semantic_points;'`

### SL-2 - Semantic-Ready Rebuild Acceptance Harness

- **Scope**: Turn the repo-local semantic dogfood case into the acceptance
  proof for the repaired force-full path so execution must demonstrate
  semantic-path results after the rebuild, not just improved internal counts.
- **Owned files**: `tests/real_world/test_semantic_search.py`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: acceptance checks for IF-0-SEMSYNCFIX-2,
  IF-0-SEMSYNCFIX-3, and IF-0-SEMSYNCFIX-4
- **Interfaces consumed**: SL-0 summary-drain and full-index assertions;
  SL-1 repaired inline force-full path; repo-local dogfood prompts and
  semantic-path metadata contract; existing
  `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` evidence shape
- **Parallel-safe**: no
- **Tasks**:
  - test: Update `tests/real_world/test_semantic_search.py` so the repo-local
    dogfood case becomes a real post-rebuild acceptance check for semantic-path
    results once the repaired force-full sync finishes, while still surfacing
    the exact blocker when semantic readiness is genuinely not restored.
  - test: Update `tests/docs/test_semdogfood_evidence_contract.py` so the
    refreshed report must cite `plans/phase-plan-v7-SEMSYNCFIX.md`, record the
    repaired full-sync path, require semantic readiness `ready`, and require
    non-zero `chunk_summaries` plus non-zero `semantic_points` when recovery
    succeeds.
  - impl: Keep this lane bounded to acceptance checks and report contract
    assertions; do not add a new production command just to drive the proof.
  - impl: Reuse the existing repo-local semantic test harness and env gating
    rather than creating a parallel SEMSYNCFIX-only runner.
  - verify: `RUN_REAL_WORLD_TESTS=1 SEMANTIC_SEARCH_ENABLED=true CODE_INDEX_DOGFOOD_REPO=. OPENAI_API_KEY=dummy-local-key uv run --extra dev python -m pytest tests/real_world/test_semantic_search.py -q --no-cov -k repo_local_dogfood_queries_stay_on_semantic_path -rs`
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`

### SL-3 - Dogfood Evidence Reducer And Operator Guide Refresh

- **Scope**: Re-run the clean rebuild with the repaired force-full summary
  path, capture the final semantic-ready evidence, and refresh the operator
  guide so the repo records how the full-sync blocker was actually cleared.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `docs/guides/semantic-onboarding.md`
- **Interfaces provided**: IF-0-SEMSYNCFIX-4 dogfood evidence contract; final
  operator guidance for distinguishing repaired force-full sync from the prior
  manual-probe-only state
- **Interfaces consumed**: SL-1 repaired force-full summary drain and
  semantic-stage continuation; SL-2 acceptance checks; repo-local rebuild
  timing and count evidence; semantic-ready repository status output
- **Parallel-safe**: no
- **Tasks**:
  - test: Use the SL-2 docs contract test as the gate for this reducer lane
    so the evidence artifact and guide cannot drift from the repaired rebuild
    outcome.
  - impl: Re-run the clean repo-local force-full rebuild using the repaired
    path, preserving the established reset boundary around `.mcp-index/current.db`
    and shared `qdrant_storage/` unless a new explicit destructive blocker
    appears during execution.
  - impl: Refresh `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` with the repaired
    force-full timing, indexed-file count, post-rebuild `chunk_summaries` and
    `semantic_points` counts, repository status output, semantic query
    outcomes, and the final semantic-ready or exact still-blocked verdict.
  - impl: Update `docs/guides/semantic-onboarding.md` so operators can
    distinguish direct summary probes from the repaired inline force-full path
    and know which commands prove semantic readiness is now truly `ready`.
  - impl: If the repaired rebuild still leaves a blocker, record the exact
    remaining failure and command evidence in the report instead of widening
    into ranking, rollout, or unrelated provider work.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - verify: `sqlite3 .mcp-index/current.db 'select count(*) as chunk_summaries from chunk_summaries; select count(*) as semantic_points from semantic_points;'`
  - verify: `RUN_REAL_WORLD_TESTS=1 SEMANTIC_SEARCH_ENABLED=true CODE_INDEX_DOGFOOD_REPO=. OPENAI_API_KEY=dummy-local-key uv run --extra dev python -m pytest tests/real_world/test_semantic_search.py -q --no-cov -k repo_local_dogfood_queries_stay_on_semantic_path -rs`

## Verification

Planning-only run: do not execute these during plan creation. Run them during
`codex-execute-phase` or manual SEMSYNCFIX execution.

Lane-specific checks:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_summarization.py tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
RUN_REAL_WORLD_TESTS=1 SEMANTIC_SEARCH_ENABLED=true CODE_INDEX_DOGFOOD_REPO=. OPENAI_API_KEY=dummy-local-key uv run --extra dev python -m pytest tests/real_world/test_semantic_search.py -q --no-cov -k repo_local_dogfood_queries_stay_on_semantic_path -rs
```

Evidence commands:

```bash
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
env OPENAI_API_KEY=dummy-local-key uv run mcp-index index check-semantic
sqlite3 .mcp-index/current.db 'select count(*) as chunk_summaries from chunk_summaries; select count(*) as semantic_points from semantic_points;'
```

Whole-phase regression commands:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_summarization.py tests/test_dispatcher.py tests/test_git_index_manager.py tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
RUN_REAL_WORLD_TESTS=1 SEMANTIC_SEARCH_ENABLED=true CODE_INDEX_DOGFOOD_REPO=. OPENAI_API_KEY=dummy-local-key uv run --extra dev python -m pytest tests/real_world/test_semantic_search.py -q --no-cov -k repo_local_dogfood_queries_stay_on_semantic_path -rs
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
git status --short -- specs/phase-plans-v7.md plans/phase-plan-v7-SEMSYNCFIX.md
```

## Acceptance Criteria

- [ ] A clean force-full rebuild writes authoritative summaries well beyond
      the current `5`-row baseline left by the broken inline sync path.
- [ ] The same rebuild produces non-zero `semantic_points` linked to
      `code_index__oss_high__v1`.
- [ ] `uv run mcp-index repository status` reports semantic readiness `ready`
      for the active profile after the rebuild.
- [ ] Semantic dogfood queries for the fixed prompts return semantic-path code
      results instead of `semantic_not_ready`.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is refreshed with the repaired
      full-sync/write-path outcome and final semantic-ready verdict.
- [ ] `docs/guides/semantic-onboarding.md` explains how to verify the repaired
      force-full summary drain separately from direct summary probes and other
      readiness surfaces.
- [ ] SEMSYNCFIX stays bounded to the real full-sync summary coverage gap,
      strict semantic-stage continuation, and the evidence needed to prove the
      repaired rebuild; it does not widen into semantic ranking redesign,
      multi-repo rollout expansion, or unrelated provider/profile changes.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v7-SEMSYNCFIX.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMSYNCFIX.md
  artifact_state: staged
```
