---
phase_loop_plan_version: 1
phase: SEMTHROUGHPUT
roadmap: specs/phase-plans-v7.md
roadmap_sha256: 860529ae034a1f9ec68e0addfc7832f36f97e82c3e1a04fd9665e3c8295c5a21
---
# SEMTHROUGHPUT: Summary Throughput Recovery

## Context

SEMTHROUGHPUT is the phase-12 follow-up for the v7 semantic hardening
roadmap. SEMSYNCFIX repaired scoped full-sync retry behavior and added a
profile-batch recovery path for the BAML generator/runtime mismatch, but the
real `repository sync --force-full` path still stops at
`semantic_readiness=summaries_missing` before any semantic vector writes begin.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is tracked and clean in this worktree, and its
  live SHA matches the required
  `860529ae034a1f9ec68e0addfc7832f36f97e82c3e1a04fd9665e3c8295c5a21`.
- The checkout is on `main` at `45bcc9b`, `main...origin/main` is ahead by 14
  commits, the worktree is clean before writing this plan, and
  `plans/phase-plan-v7-SEMTHROUGHPUT.md` did not exist before this run.
- `.phase-loop/state.json` already marks `SEMTHROUGHPUT` as the current
  unplanned phase for roadmap `specs/phase-plans-v7.md`, so this artifact is
  the missing execution handoff rather than a speculative side plan.
- The upstream v7 planning and execution chain already exists through
  `plans/phase-plan-v7-SEMSYNCFIX.md`; SEMTHROUGHPUT must consume the semantic
  readiness split, collection bootstrap repair, authoritative summary runtime
  repair, scoped full-sync retry repair, and current dogfood evidence instead
  of redefining any earlier semantic contract.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` now proves the remaining blocker
  precisely: after the latest SEMSYNCFIX rebuild, lexical readiness is `ready`,
  active-profile preflight is `ready`, collection bootstrap state is `reused`,
  `chunk_summaries` rose only to about `2465`, `semantic_points` stayed `0`,
  semantic readiness remained `summaries_missing`, and the report explicitly
  names the remaining issue as the large markdown/plaintext summary backlog.
- `FileBatchSummarizer.summarize_file_chunks(...)` in
  `mcp_server/indexing/summarization.py` now has three relevant branches:
  the BAML batch path, the profile-batch recovery path used when the batch
  runtime raises, and the oversized-file branch where `_call_batch_api(...)`
  raises `FileTooLargeError` and the code still jumps straight to
  `_summarize_topological(...)`.
- `_BATCH_FILE_SIZE_THRESHOLD` is still `400_000` characters, so the largest
  markdown and plaintext files never reach the newer profile-batch recovery
  path even though `_call_profile_batch_api(...)` already supports chunked
  batches of `_PROFILE_BATCH_CHUNK_COUNT=64`.
- `ComprehensiveChunkWriter.process_scope(...)` already drains scoped rows
  until no progress is made, and
  `EnhancedDispatcher.rebuild_semantic_for_paths(...)` already retries summary
  passes until the scoped missing-summary count stops shrinking. That means
  SEMTHROUGHPUT should target per-file summary throughput and full-sync stage
  accounting, not reinvent another rebuild loop.
- `tests/test_summarization.py` already freezes the current oversized-file
  behavior and the runtime-mismatch profile-batch fallback as separate cases.
  `tests/test_dispatcher.py` and `tests/test_git_index_manager.py` already
  freeze the scoped retry contract, but they do not yet prove that oversized
  markdown/plaintext files use a bounded batch recovery path that can clear the
  final repo-wide backlog in one force-full rebuild.
- `tests/real_world/test_semantic_search.py`,
  `tests/docs/test_semdogfood_evidence_contract.py`,
  `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, and
  `docs/guides/semantic-onboarding.md` remain the acceptance and evidence
  surfaces that must flip from "summary throughput still blocked" to a final
  semantic-ready verdict or an exact still-blocked statement.

Practical planning boundary:

- SEMTHROUGHPUT may repair oversized-file summary batching, tune the force-full
  semantic-stage throughput path and its accounting, rerun the clean rebuild,
  and refresh the dogfood evidence plus operator guidance.
- SEMTHROUGHPUT must stay narrowly on summary throughput and rebuild proof. It
  must not widen into semantic ranking, multi-repo rollout policy, new
  collection/bootstrap behavior, or unrelated profile/provider changes already
  handled by earlier phases.

## Interface Freeze Gates

- [ ] IF-0-SEMTHROUGHPUT-1 - Oversized-file summary batching contract:
      files that exceed the single-request batch-size threshold use a bounded
      authoritative batch recovery path before falling all the way back to
      per-chunk topological summarization, and that recovery preserves the
      existing authoritative audit metadata contract.
- [ ] IF-0-SEMTHROUGHPUT-2 - One-pass force-full throughput contract:
      the default local `repository sync --force-full` path clears the
      remaining repo-wide summary backlog for the active rebuild scope within
      one run, advances into semantic vector writes for
      `code_index__oss_high__v1`, and leaves semantic readiness `ready`.
- [ ] IF-0-SEMTHROUGHPUT-3 - Throughput accounting contract: dispatcher and
      full-index result surfaces distinguish summary batches attempted,
      summaries written, remaining summary backlog, and semantic-stage outcome
      precisely enough to explain whether the rebuild is ready, still blocked,
      or failed without guessing from raw counts alone.
- [ ] IF-0-SEMTHROUGHPUT-4 - Dogfood semantic-ready contract: after the
      repaired rebuild, the repo-local semantic dogfood prompts return
      semantic-path results with `semantic_source: "semantic"`,
      `semantic_profile_id: "oss_high"`, and
      `semantic_collection_name: "code_index__oss_high__v1"` instead of
      `semantic_not_ready`.
- [ ] IF-0-SEMTHROUGHPUT-5 - Phase boundary contract: SEMTHROUGHPUT changes
      summary batching, full-sync throughput, and the final dogfood proof
      only. It does not redesign ranking, widen rollout policy, or reopen
      earlier collection or runtime-repair phases.

## Lane Index & Dependencies

- SL-0 - Large-file throughput contract tests and fixtures; Depends on: SEMSYNCFIX; Blocks: SL-1, SL-2, SL-3; Parallel-safe: no
- SL-1 - Oversized summary batching implementation; Depends on: SL-0; Blocks: SL-2, SL-3; Parallel-safe: no
- SL-2 - Force-full semantic-stage throughput acceptance; Depends on: SL-0, SL-1; Blocks: SL-3; Parallel-safe: no
- SL-3 - Dogfood evidence reducer and operator guide refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SEMTHROUGHPUT acceptance; Parallel-safe: no

Lane DAG:

```text
SEMSYNCFIX
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SEMTHROUGHPUT acceptance
```

## Lanes

### SL-0 - Large-File Throughput Contract Tests And Fixtures

- **Scope**: Freeze the exact oversized-file and large-backlog behavior before
  runtime changes so the phase proves a throughput repair instead of merely
  reporting better incidental counts.
- **Owned files**: `tests/test_summarization.py`
- **Interfaces provided**: executable assertions for IF-0-SEMTHROUGHPUT-1;
  deterministic fixtures for IF-0-SEMTHROUGHPUT-2 that distinguish oversized
  file threshold handling from runtime-mismatch fallback handling
- **Interfaces consumed**: existing `FileBatchSummarizer._call_batch_api(...)`,
  `_call_profile_batch_api(...)`, `_summarize_topological(...)`,
  `summarize_file_chunks(...)`, `ComprehensiveChunkWriter.process_scope(...)`,
  `_BATCH_FILE_SIZE_THRESHOLD`, and the current SEMSYNCFIX fallback tests
- **Parallel-safe**: no
- **Tasks**:
  - test: Replace the current oversized-file assertion that immediately
    expects topological fallback with a contract that proves oversized files
    attempt a bounded profile-batch or equivalent authoritative batch recovery
    path before per-chunk fallback is allowed.
  - test: Add a deterministic large markdown/plaintext fixture that proves one
    oversized file can be summarized across multiple bounded batch requests
    while preserving `is_authoritative=1`, `provider_name`,
    configured-model/effective-model metadata, and accurate
    `missing_chunk_ids`.
  - test: Add a `process_scope(...)` backlog-drain case that proves
    oversized-file recovery makes measurable forward progress on the same file
    across repeated scoped passes instead of stalling after the first threshold
    hit.
  - impl: Keep fixtures deterministic by monkeypatching batch/profile/per-chunk
    helpers rather than introducing live-network timing tests.
  - impl: Keep this lane bounded to summary throughput contracts. Do not change
    dispatcher accounting or dogfood docs here.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_summarization.py -q --no-cov`

### SL-1 - Oversized Summary Batching Implementation

- **Scope**: Repair `summarization.py` so oversized markdown/plaintext files
  use the fastest supported authoritative recovery path instead of dropping
  immediately to the slowest per-chunk path.
- **Owned files**: `mcp_server/indexing/summarization.py`
- **Interfaces provided**: IF-0-SEMTHROUGHPUT-1 oversized-file summary
  batching contract; additive summary results that still report authoritative
  writes and residual missing chunks accurately when only part of a large file
  succeeds
- **Interfaces consumed**: SL-0 contract tests; existing
  `_PROFILE_BATCH_CHUNK_COUNT`, `_call_profile_batch_api(...)`,
  `_summarize_topological(...)`, summary audit persistence in `ChunkWriter`,
  and the SEMSYNCFIX runtime-mismatch recovery path
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 slice first and confirm it reproduces the current
    oversized-file behavior before mutating runtime code.
  - impl: Choose one singular oversized-file recovery path and keep it
    deterministic: for example, route `FileTooLargeError` into the existing
    profile-batch chunk windowing path, or introduce an explicit chunk-windowed
    authoritative batch helper that reuses the same persistence and audit
    metadata contract.
  - impl: Preserve topological per-chunk fallback as the terminal recovery
    path only when bounded authoritative batch recovery is unavailable or still
    leaves exact missing chunks.
  - impl: Keep authoritative metadata identical to the SEMSUMFIX contract so
    downstream invalidation and readiness evidence do not need a new schema or
    new provider vocabulary.
  - impl: Keep this lane local to `summarization.py`; do not add new profile
    flags, new semantic modes, or unrelated provider configuration changes.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_summarization.py -q --no-cov`

### SL-2 - Force-Full Semantic-Stage Throughput Acceptance

- **Scope**: Carry the repaired oversized-file batching through the actual
  force-full semantic pipeline so one rebuild can clear `summaries_missing`,
  populate vectors, and prove repo-local semantic queries become ready.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `mcp_server/storage/git_index_manager.py`, `tests/test_dispatcher.py`, `tests/test_git_index_manager.py`, `tests/real_world/test_semantic_search.py`
- **Interfaces provided**: IF-0-SEMTHROUGHPUT-2 one-pass force-full throughput
  contract; IF-0-SEMTHROUGHPUT-3 stage/accounting contract; IF-0-SEMTHROUGHPUT-4
  repo-local semantic-ready dogfood acceptance
- **Interfaces consumed**: SL-0 oversized-file fixtures; SL-1 repaired
  summary batching path; existing `rebuild_semantic_for_paths(...)`,
  `_count_missing_summaries_for_paths(...)`, `GitAwareIndexManager._full_index(...)`,
  semantic preflight/bootstrap outputs, and the repo-local dogfood query
  harness
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` so the strict semantic stage proves
    a force-full rebuild can continue through large-file summary recovery and
    reach `semantic_stage="indexed"` once the oversized backlog is drained.
  - test: Extend `tests/test_git_index_manager.py` so full-index semantic
    aggregates record a semantic-ready success case with non-zero
    `summaries_written`, zero remaining summary backlog for the active rebuild
    scope, and non-zero semantic indexing activity instead of only the blocked
    `summaries_missing` path.
  - test: Update `tests/real_world/test_semantic_search.py` so the repo-local
    dogfood case becomes the post-rebuild acceptance proof for semantic-path
    results after SEMTHROUGHPUT, while still surfacing the exact blocker if
    execution proves readiness is not restored.
  - impl: Adjust `rebuild_semantic_for_paths(...)` only as needed so
    summary-pass accounting and semantic-stage transitions reflect the repaired
    large-file throughput path without adding a second rebuild workflow.
  - impl: Preserve strict summary-before-vector ordering and fail-closed
    behavior for genuine residual blockers; this lane should make the existing
    rebuild finish, not weaken readiness gates.
  - impl: Keep semantic query routing unchanged. This lane is about rebuild
    throughput and acceptance, not ranking or query semantics.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov`
  - verify: `RUN_REAL_WORLD_TESTS=1 SEMANTIC_SEARCH_ENABLED=true CODE_INDEX_DOGFOOD_REPO=. OPENAI_API_KEY=dummy-local-key uv run --extra dev python -m pytest tests/real_world/test_semantic_search.py -q --no-cov -k repo_local_dogfood_queries_stay_on_semantic_path -rs`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index index check-semantic`
  - verify: `sqlite3 .mcp-index/current.db 'select count(*) as chunk_summaries from chunk_summaries; select count(*) as semantic_points from semantic_points;'`

### SL-3 - Dogfood Evidence Reducer And Operator Guide Refresh

- **Scope**: Refresh the durable dogfood report and operator guide so the repo
  records whether SEMTHROUGHPUT finally restored semantic readiness or exactly
  which throughput blocker remains.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `docs/guides/semantic-onboarding.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: IF-0-SEMTHROUGHPUT-2 durable rebuild evidence;
  IF-0-SEMTHROUGHPUT-3 operator-facing throughput accounting narrative;
  IF-0-SEMTHROUGHPUT-4 final semantic-ready or exact still-blocked verdict
- **Interfaces consumed**: SL-1 oversized-file repair description; SL-2 rebuild
  timings, summary/vector counts, semantic-ready status output, and repo-local
  query outcomes; existing evidence shape in
  `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- **Parallel-safe**: no
- **Tasks**:
  - test: Update `tests/docs/test_semdogfood_evidence_contract.py` so the
    refreshed report must cite `plans/phase-plan-v7-SEMTHROUGHPUT.md`, record
    the large-file throughput repair, capture post-rebuild
    `chunk_summaries` and `semantic_points`, and state the final semantic-ready
    or exact still-blocked verdict.
  - test: Require `docs/guides/semantic-onboarding.md` to explain how to
    distinguish collection/bootstrap readiness from summary-throughput
    readiness, and to point operators at the repaired force-full verification
    commands.
  - impl: Refresh `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` after the
    SEMTHROUGHPUT rebuild with timings, active collection identity, summary
    backlog counts, vector counts, semantic query outcomes, and the final
    verdict.
  - impl: Update `docs/guides/semantic-onboarding.md` so the troubleshooting
    section reflects the repaired oversized-file summary path or records the
    exact remaining blocker if one rebuild still cannot clear the backlog.
  - impl: If execution still fails to reach semantic readiness `ready`, record
    the exact residual blocker and command evidence instead of widening into
    ranking or multi-repo rollout work.
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
  - verify: `rg -n "SEMTHROUGHPUT|summary throughput|semantic readiness|semantic_points|chunk_summaries" docs/status/SEMANTIC_DOGFOOD_REBUILD.md docs/guides/semantic-onboarding.md tests/docs/test_semdogfood_evidence_contract.py`

## Verification

Planning-only run: do not execute these during plan creation. Run them during
`codex-execute-phase` or manual SEMTHROUGHPUT execution.

Focused verification sequence:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_summarization.py -q --no-cov
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov
RUN_REAL_WORLD_TESTS=1 SEMANTIC_SEARCH_ENABLED=true CODE_INDEX_DOGFOOD_REPO=. OPENAI_API_KEY=dummy-local-key uv run --extra dev python -m pytest tests/real_world/test_semantic_search.py -q --no-cov -k repo_local_dogfood_queries_stay_on_semantic_path -rs
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
env OPENAI_API_KEY=dummy-local-key uv run mcp-index index check-semantic
sqlite3 .mcp-index/current.db 'select count(*) as chunk_summaries from chunk_summaries; select count(*) as semantic_points from semantic_points;'
```

Whole-phase regression guard:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_summarization.py tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov
RUN_REAL_WORLD_TESTS=1 SEMANTIC_SEARCH_ENABLED=true CODE_INDEX_DOGFOOD_REPO=. OPENAI_API_KEY=dummy-local-key uv run --extra dev python -m pytest tests/real_world/test_semantic_search.py -q --no-cov -k repo_local_dogfood_queries_stay_on_semantic_path -rs
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
```

## Acceptance Criteria

- [ ] Oversized markdown/plaintext files no longer jump straight from
      `FileTooLargeError` into the slowest per-chunk path when an authoritative
      bounded batch recovery path is available.
- [ ] A clean `uv run mcp-index repository sync --force-full` clears the
      repo-wide `summaries_missing` blocker in one rebuild and produces
      non-zero `semantic_points` for `code_index__oss_high__v1`.
- [ ] `uv run mcp-index repository status` reports semantic readiness `ready`
      for the active profile after the repaired rebuild.
- [ ] Repo-local semantic dogfood queries return semantic-path results instead
      of `semantic_not_ready`.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the throughput repair
      evidence and final semantic-ready or exact still-blocked verdict.
