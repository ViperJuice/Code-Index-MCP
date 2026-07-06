---
phase_loop_plan_version: 1
phase: SEMROADMAP
roadmap: specs/phase-plans-v7.md
roadmap_sha256: f133bccf304479ade7e5c2e9a84a57852e3af007592dfc53aa0c7dff6cf15562
---
# SEMROADMAP: Roadmap Lexical Timeout Repair

## Context

SEMROADMAP is the phase-16 follow-up for the v7 semantic hardening roadmap.
SEMCHANGELOG cleared the prior exact lexical blocker on `CHANGELOG.md`, and
the live repo-local force-full rerun now times out while processing
`ROADMAP.md` before the rebuild can reach indexed-commit freshness or semantic
closeout.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is tracked and clean in this worktree, and its
  live SHA matches the required
  `f133bccf304479ade7e5c2e9a84a57852e3af007592dfc53aa0c7dff6cf15562`.
- The checkout is on `main` at `b32d7c8fee97`, `main...origin/main` is ahead
  by 22 commits, the worktree was clean before writing this plan, and
  `plans/phase-plan-v7-SEMROADMAP.md` did not exist before this run.
- The upstream v7 planning chain already exists through
  `plans/phase-plan-v7-SEMCHANGELOG.md`, and the latest repo-local closeout in
  `.phase-loop/events.jsonl` marks `SEMCHANGELOG` complete on
  `2026-04-28T13:44:52Z`. The older `.phase-loop/state.json` and
  `.phase-loop/tui-handoff.md` snapshots still point at the earlier
  `SEMCHANGELOG` planned state on `0fcdcc4d`; SEMROADMAP should use the live
  blocker artifact and event tail as planning truth and not widen into phase-
  loop bookkeeping repair.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is the live blocker artifact for
  this phase. Its SEMCHANGELOG evidence snapshot at `2026-04-28T13:38:52Z` on
  observed commit `0fcdcc4d` records the current bounded failure precisely:
  the rerun no longer fails on `CHANGELOG.md`, but still exits with
  `Lexical indexing timed out while processing ROADMAP.md`, leaving lexical
  readiness `stale_commit`, semantic readiness `summaries_missing`, and the
  indexed commit unchanged.
- `ROADMAP.md` is `1010` lines and `45009` bytes. That is far below the
  Markdown plugin's current large-document cutoff
  (`_LIGHTWEIGHT_MARKDOWN_BYTES = 250_000`), so the live force-full path still
  runs the heavyweight Markdown AST/section/chunk extraction under the same
  five-second lexical watchdog.
- The bounded-path helper in
  `mcp_server/plugins/markdown_plugin/plugin.py::_resolve_lightweight_reason()`
  currently recognizes only the forced-env path, oversized Markdown files, and
  filename stems matching `changelog` or `release notes`. `ROADMAP.md` does
  not currently qualify for the lightweight lexical shard even though
  `CHANGELOG.md` now does.
- The current test and evidence surfaces already freeze the adjacent
  contracts: `tests/test_dispatcher.py` proves the exact low-level blocker
  reporting and the bounded changelog path, `tests/test_git_index_manager.py`
  covers fail-closed force-full closeout, `tests/root_tests/test_markdown_production_scenarios.py`
  freezes bounded changelog discoverability, `tests/real_world/test_semantic_search.py`
  carries the repo-local dogfood acceptance surface, and
  `tests/docs/test_semdogfood_evidence_contract.py` plus
  `docs/guides/semantic-onboarding.md` keep the operator-facing blocker
  narrative honest.
- The practical implementation surfaces are therefore the same lexical path
  family narrowed by SEMCHANGELOG: `mcp_server/plugins/markdown_plugin/plugin.py`
  for the bounded Markdown path, `mcp_server/dispatcher/dispatcher_enhanced.py`
  and `mcp_server/storage/git_index_manager.py` for force-full timeout and
  closeout handling, and the dogfood evidence docs/tests for the rerun verdict.

Practical planning boundary:

- SEMROADMAP may introduce a bounded Markdown indexing repair or narrow
  lexical policy for roadmap or planning documents, preserve durable lexical
  indexing for `ROADMAP.md`, rerun the repo-local force-full rebuild, and
  refresh the dogfood evidence with either a semantic-ready verdict or a new
  exact downstream blocker narrower than the current `ROADMAP.md` timeout.
- SEMROADMAP must stay narrowly on the `ROADMAP.md` lexical timeout path,
  watchdog preservation, and rerun evidence. It must not widen into semantic
  ranking redesign, broad Markdown processing rewrites, or a global lexical
  timeout increase that hides true path-level stalls.

## Interface Freeze Gates

- [ ] IF-0-SEMROADMAP-1 - Bounded roadmap lexical indexing contract:
      a clean `uv run mcp-index repository sync --force-full` no longer times
      out while processing `ROADMAP.md`, and any repair used for that file
      still leaves durable lexical document and heading discovery for the
      roadmap instead of silently excluding it from the index.
- [ ] IF-0-SEMROADMAP-2 - Watchdog preservation contract:
      the lexical timeout watchdog remains active and still fails closed for
      true path-level stalls, including synthetic dispatcher and git-index-
      manager timeout fixtures that are not fixed by the roadmap-specific
      repair.
- [ ] IF-0-SEMROADMAP-3 - Force-full downstream handoff contract:
      after the `ROADMAP.md` repair, the live force-full rerun either advances
      through indexed-commit freshness and semantic closeout or exits with a
      new exact blocker narrower than
      `Lexical indexing timed out while processing ROADMAP.md`.
- [ ] IF-0-SEMROADMAP-4 - Evidence contract:
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` and
      `docs/guides/semantic-onboarding.md` record the roadmap lexical repair,
      the rerun command and outcome, current-versus-indexed commit evidence,
      and the final ready or still-blocked verdict.

## Lane Index & Dependencies

- SL-0 - Roadmap timeout contract tests and bounded fixture freeze; Depends on: SEMCHANGELOG; Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 - Markdown roadmap lexical path repair; Depends on: SL-0; Blocks: SL-2, SL-3, SL-4; Parallel-safe: no
- SL-2 - Force-full lexical orchestration and closeout integration; Depends on: SL-0, SL-1; Blocks: SL-3, SL-4; Parallel-safe: no
- SL-3 - Repo-local rerun acceptance harness; Depends on: SL-0, SL-1, SL-2; Blocks: SL-4; Parallel-safe: no
- SL-4 - Dogfood evidence reducer and operator guide refresh; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: SEMROADMAP acceptance; Parallel-safe: no

Lane DAG:

```text
SEMCHANGELOG
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SL-4 -> SEMROADMAP acceptance
```

## Lanes

### SL-0 - Roadmap Timeout Contract Tests And Bounded Fixture Freeze

- **Scope**: Freeze the exact `ROADMAP.md` lexical-timeout contract before
  runtime changes so this phase proves a bounded file-path repair instead of
  only moving the live failure somewhere less visible.
- **Owned files**: `tests/test_dispatcher.py`, `tests/test_git_index_manager.py`, `tests/root_tests/test_markdown_production_scenarios.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMROADMAP-1 through IF-0-SEMROADMAP-3
- **Interfaces consumed**: existing `EnhancedDispatcher.index_directory(...)`,
  `Dispatcher._index_file_with_lexical_timeout(...)`,
  `GitAwareIndexManager._full_index(...)`,
  `GitAwareIndexManager.sync_repository_index(...)`, the current
  SEMCHANGELOG low-level blocker vocabulary, and the existing bounded Markdown
  discoverability coverage for changelog-shaped documents
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` with a deterministic
    roadmap-shaped timeout case that freezes the current failure on
    `ROADMAP.md` and then proves the repaired path finishes indexing that
    document without suppressing the watchdog for unrelated files.
  - test: Extend `tests/test_git_index_manager.py` so force-full sync
    distinguishes a repaired post-roadmap handoff from the current exact
    `lexical_file_timeout` blocker, and still refuses to advance the indexed
    commit for synthetic non-roadmap timeout fixtures.
  - test: Tighten `tests/root_tests/test_markdown_production_scenarios.py` so
    roadmap or planning-document fixtures assert whichever bounded indexing
    shape the implementation chooses still preserves durable document and
    heading output for `ROADMAP.md`.
  - impl: Keep fixtures deterministic with monkeypatched dispatcher or plugin
    behavior and repo-local roadmap-sized strings rather than multi-minute
    real waits inside unit coverage.
  - impl: Keep this lane focused on the exact timeout contract and durable
    roadmap indexing semantics; do not update docs or the live dogfood report
    here.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov`
  - verify: `uv run pytest tests/root_tests/test_markdown_production_scenarios.py -q --no-cov -k roadmap`

### SL-1 - Markdown Roadmap Lexical Path Repair

- **Scope**: Repair the Markdown indexing path so `ROADMAP.md` can be
  lexically indexed under the live watchdog without requiring a global timeout
  increase or a broad document-processing rewrite that the force-full rebuild
  does not need for this file.
- **Owned files**: `mcp_server/plugins/markdown_plugin/plugin.py`
- **Interfaces provided**: IF-0-SEMROADMAP-1 bounded roadmap lexical indexing
  contract at the document-plugin layer
- **Interfaces consumed**: SL-0 roadmap timeout tests; existing Markdown
  metadata extraction, lightweight title and heading extraction,
  `_resolve_lightweight_reason(...)`, and the current
  `_LIGHTWEIGHT_MARKDOWN_BYTES` / bounded-name behavior already present in
  `MarkdownPlugin.indexFile(...)`
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 Markdown slice first and confirm the current roadmap
    fixture still requires the heavy document path even though the file is far
    smaller than the existing lightweight cutoff.
  - impl: Choose one bounded repair path and keep it singular: either broaden
    the existing bounded-name policy from changelog or release-note Markdown
    files to roadmap or planning documents, or add a roadmap-specific path
    that reuses the existing lightweight title and heading shard instead of
    invoking the full AST and chunk pipeline.
  - impl: Preserve durable document metadata plus at least the repo's needed
    lexical and heading discovery surface for `ROADMAP.md`; the repair must
    not turn the roadmap into an ignored file.
  - impl: Keep this lane local to the Markdown plugin. Do not introduce a new
    global lexical timeout knob, and do not widen into a generalized
    Markdown-processing rewrite for every `.md` file.
  - verify: `uv run pytest tests/root_tests/test_markdown_production_scenarios.py -q --no-cov -k roadmap`

### SL-2 - Force-Full Lexical Orchestration And Closeout Integration

- **Scope**: Carry the bounded roadmap repair through the real force-full
  indexing path so the dispatcher and git-index-manager can clear the exact
  `ROADMAP.md` blocker while preserving fail-closed timeout behavior for
  genuinely stalled files.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `mcp_server/storage/git_index_manager.py`
- **Interfaces provided**: IF-0-SEMROADMAP-2 watchdog preservation
  contract; IF-0-SEMROADMAP-3 force-full downstream handoff contract
- **Interfaces consumed**: SL-0 dispatcher and git-index-manager timeout
  tests; SL-1 bounded Markdown roadmap indexing behavior; existing
  `index_directory(...)`, `_index_file_with_lexical_timeout(...)`,
  `_record_low_level_blocker(...)`, `_full_index(...)`, and
  `sync_repository_index(...)`
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 dispatcher and git-index-manager slice first and
    confirm the current low-level lexical blocker still pins the live rerun on
    `ROADMAP.md` before mutating full-sync orchestration or closeout logic.
  - impl: If the bounded roadmap repair requires an explicit force-full hint,
    thread that hint through the existing lexical indexing path for roadmap or
    planning documents only; do not replace the repo-wide watchdog with a
    globally weaker timeout posture.
  - impl: Preserve the exact SEMIOWAIT and SEMCHANGELOG low-level blocker
    contract for genuine timeout cases. Files other than the repaired roadmap
    path must still be able to surface `blocked_file_timeout` plus storage
    diagnostics.
  - impl: Tighten `_full_index(...)` and `sync_repository_index(...)` only as
    needed so a repaired run no longer stops at `ROADMAP.md` and instead
    either reaches indexed-commit freshness or carries forward the next exact
    downstream blocker from summary or semantic stages.
  - impl: Do not widen into semantic ranking, storage diagnostics redesign, or
    new repository-readiness taxonomy.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov`
  - verify: `env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`

### SL-3 - Repo-Local Rerun Acceptance Harness

- **Scope**: Make the repo-local semantic dogfood harness prove that
  `SEMROADMAP` really cleared the exact live blocker instead of only changing
  low-level counters or wording.
- **Owned files**: `tests/real_world/test_semantic_search.py`
- **Interfaces provided**: acceptance checks for IF-0-SEMROADMAP-3
- **Interfaces consumed**: SL-0 timeout fixtures; SL-1 bounded roadmap
  repair; SL-2 repaired force-full rerun and closeout behavior; existing
  repo-local semantic dogfood prompt and readiness assertions
- **Parallel-safe**: no
- **Tasks**:
  - test: Update the repo-local dogfood case so it treats
    `Lexical indexing timed out while processing ROADMAP.md` as the exact
    SEMROADMAP blocker to clear, and after the repair expects either
    semantic-path results on a fresh index or a new exact downstream blocker
    narrower than the roadmap lexical timeout.
  - impl: Keep this lane bounded to acceptance semantics and blocker wording;
    do not add a new production command or duplicate the full rebuild logic.
  - impl: Reuse the existing real-world env gating and prompt surface rather
    than creating a SEMROADMAP-only dogfood harness.
  - verify: `RUN_REAL_WORLD_TESTS=1 SEMANTIC_SEARCH_ENABLED=true CODE_INDEX_DOGFOOD_REPO=. OPENAI_API_KEY=dummy-local-key uv run --extra dev python -m pytest tests/real_world/test_semantic_search.py -q --no-cov -k repo_local_dogfood_queries_stay_on_semantic_path -rs`

### SL-4 - Dogfood Evidence Reducer And Operator Guide Refresh

- **Scope**: Re-run the repaired repo-local force-full sequence, reduce the
  outcome into the durable dogfood evidence artifact, and refresh operator
  guidance so the roadmap lexical repair and its downstream verdict are easy
  to distinguish from the older `CHANGELOG.md` blocker state.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `docs/guides/semantic-onboarding.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: IF-0-SEMROADMAP-4 evidence contract
- **Interfaces consumed**: SL-0 timeout contract wording; SL-1 bounded
  roadmap repair; SL-2 rerun command and indexed-commit status; SL-3 repo-
  local dogfood acceptance verdict
- **Parallel-safe**: no
- **Tasks**:
  - test: Update `tests/docs/test_semdogfood_evidence_contract.py` so the
    refreshed report must cite `plans/phase-plan-v7-SEMROADMAP.md`, record
    the roadmap lexical repair, and require either a ready-path verdict or a
    new exact downstream blocker that is narrower than the prior
    `ROADMAP.md` timeout message.
  - impl: Re-run the repo-local force-full rebuild with the same strict
    watchdog posture used by SEMCHANGELOG, record whether the run now clears
    `ROADMAP.md`, and capture the next exact outcome together with current-
    versus-indexed commit evidence, `chunk_summaries`, and `semantic_points`.
  - impl: Refresh `docs/guides/semantic-onboarding.md` so operators can tell
    the difference between the old SEMCHANGELOG blocker on `ROADMAP.md` and
    the repaired SEMROADMAP state, including where to look for the next
    bounded blocker if the rerun still does not finish fully.
  - impl: Keep this lane as the final reducer only. It must depend on every
    producer lane and must not speculate about outcomes before the repaired
    rerun actually runs.
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
  - verify: `env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index index check-semantic`
  - verify: `RUN_REAL_WORLD_TESTS=1 SEMANTIC_SEARCH_ENABLED=true CODE_INDEX_DOGFOOD_REPO=. OPENAI_API_KEY=dummy-local-key uv run --extra dev python -m pytest tests/real_world/test_semantic_search.py -q --no-cov -k repo_local_dogfood_queries_stay_on_semantic_path -rs`

## Verification

Lane-focused verification sequence:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov
uv run pytest tests/root_tests/test_markdown_production_scenarios.py -q --no-cov -k roadmap
env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
env OPENAI_API_KEY=dummy-local-key uv run mcp-index index check-semantic
RUN_REAL_WORLD_TESTS=1 SEMANTIC_SEARCH_ENABLED=true CODE_INDEX_DOGFOOD_REPO=. OPENAI_API_KEY=dummy-local-key uv run --extra dev python -m pytest tests/real_world/test_semantic_search.py -q --no-cov -k repo_local_dogfood_queries_stay_on_semantic_path -rs
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
```

Whole-phase regression guard:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov
uv run pytest tests/root_tests/test_markdown_production_scenarios.py -q --no-cov -k roadmap
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
RUN_REAL_WORLD_TESTS=1 SEMANTIC_SEARCH_ENABLED=true CODE_INDEX_DOGFOOD_REPO=. OPENAI_API_KEY=dummy-local-key uv run --extra dev python -m pytest tests/real_world/test_semantic_search.py -q --no-cov -k repo_local_dogfood_queries_stay_on_semantic_path -rs
```

## Acceptance Criteria

- [ ] A clean `uv run mcp-index repository sync --force-full` no longer exits
      with `Lexical indexing timed out while processing ROADMAP.md`.
- [ ] The chosen repair for `ROADMAP.md` is bounded and preserves durable
      lexical indexing for the roadmap; the file is not silently ignored or
      dropped from document or heading discovery just to satisfy the
      watchdog.
- [ ] Synthetic non-roadmap timeout fixtures still fail closed through the
      existing low-level blocker contract, proving the watchdog remains active
      for genuine path-level stalls.
- [ ] After the roadmap repair, the live repo-local rerun either completes
      through indexed-commit freshness and semantic closeout or surfaces a new
      exact downstream blocker that is narrower than the current roadmap
      lexical timeout.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the roadmap repair,
      the rerun outcome, current-versus-indexed commit evidence, durable
      counts, and the final ready or still-blocked verdict on the current
      commit.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v7-SEMROADMAP.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMROADMAP.md
  artifact_state: staged
```
