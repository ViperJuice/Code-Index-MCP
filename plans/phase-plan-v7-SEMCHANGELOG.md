---
phase_loop_plan_version: 1
phase: SEMCHANGELOG
roadmap: specs/phase-plans-v7.md
roadmap_sha256: f133bccf304479ade7e5c2e9a84a57852e3af007592dfc53aa0c7dff6cf15562
---
# SEMCHANGELOG: Changelog Lexical Timeout Repair

## Context

SEMCHANGELOG is the phase-15 follow-up for the v7 semantic hardening roadmap.
SEMIOWAIT already tightened the below-semantic lexical/storage contract and
proved the remaining repo-local force-full blocker exactly: lexical indexing
times out while processing `CHANGELOG.md` before the semantic-stage path can
begin.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is tracked and clean in this worktree, and its
  live SHA matches the required
  `a55b3ccb3d315d476f23532b0028a2d793c499882c130b3d5d3e637abb894b7e`.
- The checkout is on `main` at `abd0216e9bf7`, `main...origin/main` is ahead
  by 20 commits, the worktree is clean before writing this plan, and
  `plans/phase-plan-v7-SEMCHANGELOG.md` did not exist before this run.
- `.phase-loop/state.json` already marks `SEMCHANGELOG` as the current
  unplanned phase for roadmap `specs/phase-plans-v7.md`, and
  `.phase-loop/tui-handoff.md` explicitly says this is the next missing
  execution handoff after `SEMIOWAIT` completed.
- The upstream v7 planning and execution chain already exists through
  `plans/phase-plan-v7-SEMIOWAIT.md`, and the repo-local phase-loop ledger
  records the `SEMIOWAIT` closeout on `2026-04-28T13:24:52Z` after commit
  `abd0216e9bf7d325f3f629ebb00b888c62977612` preserved the low-level lexical
  instrumentation and carried the exact downstream blocker forward to
  `SEMCHANGELOG`.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is the live blocker artifact for
  this phase. Its evidence snapshot at `2026-04-28T13:18:41Z` on observed
  commit `dce6920e` records the current bounded failure precisely:
  `chunk_summaries=3018`, `semantic_points=0`, lexical readiness
  `stale_commit`, semantic readiness `summaries_missing`, active-profile
  preflight `ready`, and a fast fail-closed force-full rebuild with
  `Lexical indexing timed out while processing CHANGELOG.md`.
- The same evidence artifact proves SEMIOWAIT already solved the prior opacity
  problem: the dispatcher now reports `lexical_stage=blocked_file_timeout`,
  preserves `last_progress_path`/`in_flight_path`, and the git-index-manager
  closeout keeps the indexed commit unchanged when a low-level lexical blocker
  fires. SEMCHANGELOG must consume that exact contract instead of broadening
  the timeout taxonomy again.
- `CHANGELOG.md` is only `31068` bytes over `434` lines, which means the
  Markdown plugin's current lightweight cutoff
  (`mcp_server/plugins/markdown_plugin/plugin.py`,
  `_LIGHTWEIGHT_MARKDOWN_BYTES = 250_000`) does not apply to the live blocker.
  The current force-full path therefore still runs full Markdown
  frontmatter/AST/section/chunk extraction for this release-notes document even
  under a five-second lexical watchdog.
- There is already repo-local precedent for bounded lexical-only document
  treatment: `mcp_server/cli/index_management.py::_build_sqlite_baseline()`
  temporarily forces `MCP_LIGHTWEIGHT_DOC_INDEX=true` for baseline lexical
  indexing. SEMCHANGELOG can reuse that bounded-document idea, but it must do
  so without silently dropping `CHANGELOG.md` from durable lexical search or
  weakening the live force-full watchdog globally.
- The likely implementation surfaces are therefore split across the Markdown
  document path and the force-full lexical orchestration path:
  `mcp_server/plugins/markdown_plugin/plugin.py`,
  `mcp_server/plugins/markdown_plugin/chunk_strategies.py`,
  `mcp_server/dispatcher/dispatcher_enhanced.py`, and
  `mcp_server/storage/git_index_manager.py`.
- The acceptance and evidence surfaces already exist in
  `tests/test_dispatcher.py`, `tests/test_git_index_manager.py`,
  `tests/root_tests/test_markdown_production_scenarios.py`,
  `tests/real_world/test_semantic_search.py`,
  `tests/docs/test_semdogfood_evidence_contract.py`,
  `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, and
  `docs/guides/semantic-onboarding.md`. SEMCHANGELOG should tighten those
  surfaces around the exact `CHANGELOG.md` lexical timeout path and the rerun
  outcome rather than reopening semantic ranking, storage diagnostics, or
  earlier summary-stage work.

Practical planning boundary:

- SEMCHANGELOG may introduce a bounded Markdown indexing repair or a narrowly
  scoped force-full lexical policy for changelog/release-note documents,
  preserve durable lexical indexing for `CHANGELOG.md`, rerun the repo-local
  force-full rebuild, and refresh the dogfood evidence with either a semantic-
  ready verdict or a new exact downstream blocker that is narrower than the
  current `CHANGELOG.md` lexical timeout.
- SEMCHANGELOG must stay narrowly on the `CHANGELOG.md` lexical timeout path,
  watchdog preservation, and rerun evidence. It must not widen into semantic
  ranking redesign, broad document-processing refactors, or a global lexical
  timeout increase that hides true path-level stalls.

## Interface Freeze Gates

- [ ] IF-0-SEMCHANGELOG-1 - Bounded changelog lexical indexing contract:
      a clean `uv run mcp-index repository sync --force-full` no longer times
      out while processing `CHANGELOG.md`, and any repair used for that file
      still leaves durable lexical document/search metadata for the changelog
      instead of silently excluding it from the index.
- [ ] IF-0-SEMCHANGELOG-2 - Watchdog preservation contract:
      the lexical timeout watchdog remains active and still fails closed for
      true path-level stalls, including synthetic dispatcher/git-index-manager
      timeout fixtures that are not fixed by the changelog-specific repair.
- [ ] IF-0-SEMCHANGELOG-3 - Force-full downstream handoff contract:
      after the `CHANGELOG.md` repair, the live force-full rerun either
      advances beyond the changelog lexical path to indexed-commit freshness
      and semantic closeout, or exits with a new exact blocker that is
      narrower than `Lexical indexing timed out while processing CHANGELOG.md`.
- [ ] IF-0-SEMCHANGELOG-4 - Evidence contract:
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` and
      `docs/guides/semantic-onboarding.md` record the changelog lexical repair,
      the rerun command/outcome, current-versus-indexed commit evidence, and
      the final ready or still-blocked verdict.

## Lane Index & Dependencies

- SL-0 - Changelog timeout contract tests and bounded fixture freeze; Depends on: SEMIOWAIT; Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 - Markdown changelog lexical path repair; Depends on: SL-0; Blocks: SL-2, SL-3, SL-4; Parallel-safe: no
- SL-2 - Force-full lexical orchestration and closeout integration; Depends on: SL-0, SL-1; Blocks: SL-3, SL-4; Parallel-safe: no
- SL-3 - Repo-local rerun acceptance harness; Depends on: SL-0, SL-1, SL-2; Blocks: SL-4; Parallel-safe: no
- SL-4 - Dogfood evidence reducer and operator guide refresh; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: SEMCHANGELOG acceptance; Parallel-safe: no

Lane DAG:

```text
SEMIOWAIT
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SL-4 -> SEMCHANGELOG acceptance
```

## Lanes

### SL-0 - Changelog Timeout Contract Tests And Bounded Fixture Freeze

- **Scope**: Freeze the exact `CHANGELOG.md` lexical-timeout contract before
  runtime changes so this phase proves a bounded file-path repair instead of
  only moving the live failure somewhere less visible.
- **Owned files**: `tests/test_dispatcher.py`, `tests/test_git_index_manager.py`, `tests/root_tests/test_markdown_production_scenarios.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMCHANGELOG-1 through IF-0-SEMCHANGELOG-3
- **Interfaces consumed**: existing `EnhancedDispatcher.index_directory(...)`,
  `Dispatcher._index_file_with_lexical_timeout(...)`,
  `GitAwareIndexManager._full_index(...)`,
  `GitAwareIndexManager.sync_repository_index(...)`, current SEMIOWAIT
  low-level blocker vocabulary, and the existing Markdown changelog format
  coverage in `tests/root_tests/test_markdown_production_scenarios.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` with a deterministic
    changelog-shaped timeout case that freezes the current failure on
    `CHANGELOG.md` and then proves the repaired path finishes indexing that
    document without suppressing the watchdog for unrelated files.
  - test: Extend `tests/test_git_index_manager.py` so force-full sync
    distinguishes a repaired post-changelog handoff from the current exact
    `lexical_file_timeout` blocker, and still refuses to advance the indexed
    commit for synthetic non-changelog timeout fixtures.
  - test: Tighten `tests/root_tests/test_markdown_production_scenarios.py` so
    changelog/release-note fixtures assert whichever bounded indexing shape the
    implementation chooses still preserves durable document/symbol output for
    a Keep a Changelog file.
  - impl: Keep fixtures deterministic with monkeypatched dispatcher/plugin
    behavior and repo-local changelog-sized strings rather than multi-minute
    real waits inside unit coverage.
  - impl: Keep this lane focused on the exact timeout contract and durable
    changelog indexing semantics; do not update docs or the live dogfood
    report here.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov`
  - verify: `uv run pytest tests/root_tests/test_markdown_production_scenarios.py -q --no-cov -k changelog_format`

### SL-1 - Markdown Changelog Lexical Path Repair

- **Scope**: Repair the Markdown indexing path so `CHANGELOG.md` can be
  lexically indexed under the live watchdog without requiring a global timeout
  increase or full document-processing work that the force-full rebuild does
  not need for this file.
- **Owned files**: `mcp_server/plugins/markdown_plugin/plugin.py`, `mcp_server/plugins/markdown_plugin/chunk_strategies.py`
- **Interfaces provided**: IF-0-SEMCHANGELOG-1 bounded changelog lexical
  indexing contract at the document-plugin layer
- **Interfaces consumed**: SL-0 changelog timeout tests; existing Markdown
  metadata extraction, AST parsing, section extraction, chunk generation, and
  the current `_LIGHTWEIGHT_MARKDOWN_BYTES` / `MCP_LIGHTWEIGHT_DOC_INDEX`
  behavior already present in `MarkdownPlugin.indexFile(...)`
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 Markdown slice first and confirm the current changelog
    fixture still requires the heavy document path even though the file is
    much smaller than the existing lightweight cutoff.
  - impl: Choose one bounded repair path and keep it singular: either teach
    changelog/release-note Markdown files to use the existing lightweight
    document-symbol path below the current byte threshold, or add a bounded
    changelog-specific parsing/chunking path that stays under the lexical
    watchdog without dropping the document from lexical indexing.
  - impl: Preserve durable document metadata and at least the repo's needed
    lexical/document discovery surface for `CHANGELOG.md`; the repair must not
    turn the changelog into an ignored file.
  - impl: Keep this lane local to the Markdown plugin. Do not introduce a new
    global lexical timeout knob, and do not widen into a generalized document-
    processing rewrite for every `.md` file.
  - verify: `uv run pytest tests/root_tests/test_markdown_production_scenarios.py -q --no-cov -k changelog_format`

### SL-2 - Force-Full Lexical Orchestration And Closeout Integration

- **Scope**: Carry the bounded changelog repair through the real force-full
  indexing path so the dispatcher and git-index-manager can clear the exact
  `CHANGELOG.md` blocker while preserving fail-closed timeout behavior for
  genuinely stalled files.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `mcp_server/storage/git_index_manager.py`
- **Interfaces provided**: IF-0-SEMCHANGELOG-2 watchdog preservation
  contract; IF-0-SEMCHANGELOG-3 force-full downstream handoff contract
- **Interfaces consumed**: SL-0 dispatcher/git-index-manager timeout tests;
  SL-1 bounded Markdown changelog indexing behavior; existing
  `index_directory(...)`, `_index_file_with_lexical_timeout(...)`,
  `_record_low_level_blocker(...)`, `_full_index(...)`, and
  `sync_repository_index(...)`
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 dispatcher and git-index-manager slice first and
    confirm the current low-level lexical blocker still pins the live rerun on
    `CHANGELOG.md` before mutating full-sync orchestration or closeout logic.
  - impl: If the bounded changelog repair requires an explicit force-full hint,
    thread that hint through the existing lexical indexing path for this file
    or document class only; do not replace the repo-wide watchdog with a
    globally weaker timeout posture.
  - impl: Preserve the exact SEMIOWAIT low-level blocker contract for genuine
    timeout cases. Files other than the repaired changelog path must still be
    able to surface `blocked_file_timeout` plus storage diagnostics.
  - impl: Tighten `_full_index(...)` / `sync_repository_index(...)` only as
    needed so a repaired run no longer stops at `CHANGELOG.md` and instead
    either reaches indexed-commit freshness or carries forward the next exact
    downstream blocker from summary/semantic stages.
  - impl: Do not widen into semantic ranking, storage diagnostics redesign, or
    new repository-readiness taxonomy.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov`
  - verify: `env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`

### SL-3 - Repo-Local Rerun Acceptance Harness

- **Scope**: Make the repo-local semantic dogfood harness prove that
  `SEMCHANGELOG` really cleared the exact live blocker instead of only
  changing low-level counters or wording.
- **Owned files**: `tests/real_world/test_semantic_search.py`
- **Interfaces provided**: acceptance checks for IF-0-SEMCHANGELOG-3
- **Interfaces consumed**: SL-0 timeout fixtures; SL-1 bounded changelog
  repair; SL-2 repaired force-full rerun/closeout behavior; existing repo-
  local semantic dogfood prompt and readiness assertions
- **Parallel-safe**: no
- **Tasks**:
  - test: Update the repo-local dogfood case so it treats
    `Lexical indexing timed out while processing CHANGELOG.md` as the exact
    SEMCHANGELOG blocker to clear, and after the repair expects either
    semantic-path results on a fresh index or a new exact downstream blocker
    narrower than the changelog lexical timeout.
  - impl: Keep this lane bounded to acceptance semantics and blocker wording;
    do not add a new production command or duplicate the full rebuild logic.
  - impl: Reuse the existing real-world env gating and prompt surface rather
    than creating a SEMCHANGELOG-only dogfood harness.
  - verify: `RUN_REAL_WORLD_TESTS=1 SEMANTIC_SEARCH_ENABLED=true CODE_INDEX_DOGFOOD_REPO=. OPENAI_API_KEY=dummy-local-key uv run --extra dev python -m pytest tests/real_world/test_semantic_search.py -q --no-cov -k repo_local_dogfood_queries_stay_on_semantic_path -rs`

### SL-4 - Dogfood Evidence Reducer And Operator Guide Refresh

- **Scope**: Re-run the repaired repo-local force-full sequence, reduce the
  outcome into the durable dogfood evidence artifact, and refresh operator
  guidance so the changelog lexical repair and its downstream verdict are easy
  to distinguish from the older SEMIOWAIT blocker state.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `docs/guides/semantic-onboarding.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: IF-0-SEMCHANGELOG-4 evidence contract
- **Interfaces consumed**: SL-0 timeout contract wording; SL-1 bounded
  changelog repair; SL-2 rerun command/outcome and indexed-commit status;
  SL-3 repo-local dogfood acceptance verdict
- **Parallel-safe**: no
- **Tasks**:
  - test: Update `tests/docs/test_semdogfood_evidence_contract.py` so the
    refreshed report must cite `plans/phase-plan-v7-SEMCHANGELOG.md`, record
    the changelog lexical repair, and require either a ready-path verdict or a
    new exact downstream blocker that is narrower than the prior
    `CHANGELOG.md` timeout message.
  - impl: Re-run the repo-local force-full rebuild with the same strict
    watchdog posture used by SEMIOWAIT, record whether the run now clears
    `CHANGELOG.md`, and capture the next exact outcome together with current-
    versus-indexed commit evidence, `chunk_summaries`, and `semantic_points`.
  - impl: Refresh `docs/guides/semantic-onboarding.md` so operators can tell
    the difference between the old SEMIOWAIT lexical timeout on `CHANGELOG.md`
    and the repaired SEMCHANGELOG state, including where to look for the next
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
uv run pytest tests/root_tests/test_markdown_production_scenarios.py -q --no-cov -k changelog_format
env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
env OPENAI_API_KEY=dummy-local-key uv run mcp-index index check-semantic
RUN_REAL_WORLD_TESTS=1 SEMANTIC_SEARCH_ENABLED=true CODE_INDEX_DOGFOOD_REPO=. OPENAI_API_KEY=dummy-local-key uv run --extra dev python -m pytest tests/real_world/test_semantic_search.py -q --no-cov -k repo_local_dogfood_queries_stay_on_semantic_path -rs
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
```

Whole-phase regression guard:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov
uv run pytest tests/root_tests/test_markdown_production_scenarios.py -q --no-cov -k changelog_format
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
RUN_REAL_WORLD_TESTS=1 SEMANTIC_SEARCH_ENABLED=true CODE_INDEX_DOGFOOD_REPO=. OPENAI_API_KEY=dummy-local-key uv run --extra dev python -m pytest tests/real_world/test_semantic_search.py -q --no-cov -k repo_local_dogfood_queries_stay_on_semantic_path -rs
```

## Acceptance Criteria

- [ ] A clean `uv run mcp-index repository sync --force-full` no longer exits
      with `Lexical indexing timed out while processing CHANGELOG.md`.
- [ ] The chosen repair for `CHANGELOG.md` is bounded and preserves durable
      lexical indexing for the changelog; the file is not silently ignored or
      dropped from document search/symbol surfaces just to satisfy the
      watchdog.
- [ ] Synthetic non-changelog timeout fixtures still fail closed through the
      SEMIOWAIT low-level blocker contract, proving the watchdog remains active
      for genuine path-level stalls.
- [ ] After the changelog repair, the live repo-local rerun either completes
      through indexed-commit freshness and semantic closeout or surfaces a new
      exact downstream blocker that is narrower than the current changelog
      lexical timeout.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the changelog repair,
      the rerun outcome, current-versus-indexed commit evidence, durable
      counts, and the final ready or still-blocked verdict on the current
      commit.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v7-SEMCHANGELOG.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMCHANGELOG.md
  artifact_state: staged
```
