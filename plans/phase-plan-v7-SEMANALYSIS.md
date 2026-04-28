---
phase_loop_plan_version: 1
phase: SEMANALYSIS
roadmap: specs/phase-plans-v7.md
roadmap_sha256: 92ba4095e66cf209bc6c8558c358f066a537298076dbff62cfaf7692e4f4c810
---
# SEMANALYSIS: Final Analysis Lexical Timeout Repair

## Context

SEMANALYSIS is the phase-17 follow-up for the v7 semantic hardening roadmap.
SEMROADMAP cleared the prior exact lexical blocker on `ROADMAP.md`, and the
live repo-local force-full rerun now times out while processing
`FINAL_COMPREHENSIVE_MCP_ANALYSIS.md` before the rebuild can reach indexed-
commit freshness or semantic closeout.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is tracked and clean in this worktree, and its
  live SHA matches the required
  `92ba4095e66cf209bc6c8558c358f066a537298076dbff62cfaf7692e4f4c810`.
- The checkout is on `main` at `c87dc74415f2`, `main...origin/main` is ahead
  by 24 commits, the worktree is clean before writing this plan, and
  `plans/phase-plan-v7-SEMANALYSIS.md` did not exist before this run.
- The upstream v7 planning chain already exists through
  `plans/phase-plan-v7-SEMROADMAP.md`, and the latest live phase-loop closeout
  marks `SEMROADMAP` complete on `2026-04-28T14:00:16Z`; this phase should
  consume that verified blocker artifact and not reopen older lexical-timeout
  slices.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is the live blocker artifact for
  this phase. Its SEMROADMAP evidence snapshot at `2026-04-28T13:55:06Z` on
  observed commit `019e31d6` records the current bounded failure precisely:
  the rerun no longer fails on `ROADMAP.md`, but still exits with
  `Lexical indexing timed out while processing FINAL_COMPREHENSIVE_MCP_ANALYSIS.md`,
  leaving lexical readiness `stale_commit`, semantic readiness
  `summaries_missing`, and the indexed commit unchanged.
- `FINAL_COMPREHENSIVE_MCP_ANALYSIS.md` is only `206` lines and `7356` bytes.
  That is far below the Markdown plugin's current large-document cutoff
  (`_LIGHTWEIGHT_MARKDOWN_BYTES = 250_000`), so the live force-full path still
  runs the heavyweight Markdown AST/section/chunk extraction under the same
  five-second lexical watchdog for a small analysis report.
- The bounded-path helper in
  `mcp_server/plugins/markdown_plugin/plugin.py::_resolve_lightweight_reason()`
  currently recognizes the forced-env path, oversized Markdown files, bounded
  changelog names, and roadmap or phase-plan names. The stem
  `FINAL_COMPREHENSIVE_MCP_ANALYSIS` does not match those bounded-name
  contracts, so the heavy Markdown path still owns this file even after
  SEMROADMAP.
- The current test and evidence surfaces already freeze the adjacent
  contracts: `tests/test_dispatcher.py` proves the exact low-level blocker
  reporting and the bounded changelog and roadmap paths,
  `tests/test_git_index_manager.py` covers fail-closed force-full closeout and
  downstream blocker carry-forward, `tests/root_tests/test_markdown_production_scenarios.py`
  freezes bounded Markdown discoverability, `tests/real_world/test_semantic_search.py`
  carries the repo-local dogfood acceptance surface, and
  `tests/docs/test_semdogfood_evidence_contract.py` plus
  `docs/guides/semantic-onboarding.md` keep the operator-facing blocker
  narrative honest.
- The practical implementation surfaces are therefore the same lexical path
  family narrowed by SEMCHANGELOG and SEMROADMAP:
  `mcp_server/plugins/markdown_plugin/plugin.py` for the bounded Markdown
  path, `mcp_server/dispatcher/dispatcher_enhanced.py` and
  `mcp_server/storage/git_index_manager.py` for force-full timeout and
  closeout handling, and the dogfood evidence docs/tests for the rerun
  verdict.

Practical planning boundary:

- SEMANALYSIS may introduce one bounded Markdown indexing repair or narrow
  lexical policy for analysis or report documents, preserve durable lexical
  indexing for `FINAL_COMPREHENSIVE_MCP_ANALYSIS.md`, rerun the repo-local
  force-full rebuild, and refresh the dogfood evidence with either a
  semantic-ready verdict or a new exact downstream blocker narrower than the
  current final-analysis timeout.
- SEMANALYSIS must stay narrowly on the
  `FINAL_COMPREHENSIVE_MCP_ANALYSIS.md` lexical timeout path, watchdog
  preservation, and rerun evidence. It must not widen into semantic ranking
  redesign, broad Markdown processing rewrites, or a global lexical timeout
  increase that hides true path-level stalls.

## Interface Freeze Gates

- [ ] IF-0-SEMANALYSIS-1 - Bounded final-analysis lexical indexing contract:
      a clean `uv run mcp-index repository sync --force-full` no longer times
      out while processing `FINAL_COMPREHENSIVE_MCP_ANALYSIS.md`, and any
      repair used for that file still leaves durable lexical document and
      heading discovery for the analysis report instead of silently excluding
      it from the index.
- [ ] IF-0-SEMANALYSIS-2 - Watchdog preservation contract:
      the lexical timeout watchdog remains active and still fails closed for
      true path-level stalls, including synthetic dispatcher and git-index-
      manager timeout fixtures that are not fixed by the final-analysis-
      specific repair.
- [ ] IF-0-SEMANALYSIS-3 - Force-full downstream handoff contract:
      after the `FINAL_COMPREHENSIVE_MCP_ANALYSIS.md` repair, the live
      force-full rerun either advances through indexed-commit freshness and
      semantic closeout or exits with a new exact blocker narrower than
      `Lexical indexing timed out while processing FINAL_COMPREHENSIVE_MCP_ANALYSIS.md`.
- [ ] IF-0-SEMANALYSIS-4 - Evidence contract:
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` and
      `docs/guides/semantic-onboarding.md` record the final-analysis lexical
      repair, the rerun command and outcome, current-versus-indexed commit
      evidence, and the final ready or still-blocked verdict.

## Lane Index & Dependencies

- SL-0 - Final-analysis timeout contract tests and bounded fixture freeze; Depends on: SEMROADMAP; Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 - Markdown final-analysis lexical path repair; Depends on: SL-0; Blocks: SL-2, SL-3, SL-4; Parallel-safe: no
- SL-2 - Force-full lexical orchestration and closeout integration; Depends on: SL-0, SL-1; Blocks: SL-3, SL-4; Parallel-safe: no
- SL-3 - Repo-local rerun acceptance harness; Depends on: SL-0, SL-1, SL-2; Blocks: SL-4; Parallel-safe: no
- SL-4 - Dogfood evidence reducer and operator guide refresh; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: SEMANALYSIS acceptance; Parallel-safe: no

Lane DAG:

```text
SEMROADMAP
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SL-4 -> SEMANALYSIS acceptance
```

## Lanes

### SL-0 - Final-Analysis Timeout Contract Tests And Bounded Fixture Freeze

- **Scope**: Freeze the exact `FINAL_COMPREHENSIVE_MCP_ANALYSIS.md`
  lexical-timeout contract before runtime changes so this phase proves a
  bounded file-path repair instead of only moving the live failure somewhere
  less visible.
- **Owned files**: `tests/test_dispatcher.py`, `tests/test_git_index_manager.py`, `tests/root_tests/test_markdown_production_scenarios.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMANALYSIS-1 through IF-0-SEMANALYSIS-3
- **Interfaces consumed**: existing `EnhancedDispatcher.index_directory(...)`,
  `Dispatcher._index_file_with_lexical_timeout(...)`,
  `GitAwareIndexManager._full_index(...)`,
  `GitAwareIndexManager.sync_repository_index(...)`, the current
  SEMROADMAP low-level blocker vocabulary, and the existing bounded Markdown
  discoverability coverage for changelog and roadmap-shaped documents
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` with a deterministic
    final-analysis-shaped timeout case that freezes the current failure on
    `FINAL_COMPREHENSIVE_MCP_ANALYSIS.md` and then proves the repaired path
    finishes indexing that document without suppressing the watchdog for
    unrelated files.
  - test: Extend `tests/test_git_index_manager.py` so force-full sync
    distinguishes a repaired post-final-analysis handoff from the current
    exact `lexical_file_timeout` blocker, and still refuses to advance the
    indexed commit for synthetic non-analysis timeout fixtures.
  - test: Tighten `tests/root_tests/test_markdown_production_scenarios.py` so
    final-analysis or report-document fixtures assert whichever bounded
    indexing shape the implementation chooses still preserves durable document
    and heading output for `FINAL_COMPREHENSIVE_MCP_ANALYSIS.md`.
  - impl: Keep fixtures deterministic with monkeypatched dispatcher or plugin
    behavior and repo-local analysis-report strings rather than multi-minute
    real waits inside unit coverage.
  - impl: Keep this lane focused on the exact timeout contract and durable
    analysis-report indexing semantics; do not update docs or the live
    dogfood report here.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov`
  - verify: `uv run pytest tests/root_tests/test_markdown_production_scenarios.py -q --no-cov -k analysis`

### SL-1 - Markdown Final-Analysis Lexical Path Repair

- **Scope**: Repair the Markdown indexing path so
  `FINAL_COMPREHENSIVE_MCP_ANALYSIS.md` can be lexically indexed under the
  live watchdog without requiring a global timeout increase or a broad
  document-processing rewrite that the force-full rebuild does not need for
  this file.
- **Owned files**: `mcp_server/plugins/markdown_plugin/plugin.py`
- **Interfaces provided**: IF-0-SEMANALYSIS-1 bounded final-analysis lexical
  indexing contract at the document-plugin layer
- **Interfaces consumed**: SL-0 final-analysis timeout tests; existing
  Markdown metadata extraction, lightweight title and heading extraction,
  `_resolve_lightweight_reason(...)`, and the current
  `_LIGHTWEIGHT_MARKDOWN_BYTES` / bounded-name behavior already present in
  `MarkdownPlugin.indexFile(...)`
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 Markdown slice first and confirm the current
    final-analysis fixture still requires the heavy document path even though
    the file is far smaller than the existing lightweight cutoff.
  - impl: Choose one bounded repair path and keep it singular: either broaden
    the existing bounded-name policy from changelog, roadmap, and phase-plan
    Markdown files to cover this analysis-report class, or add an exact
    final-analysis path that reuses the existing lightweight title and heading
    shard instead of invoking the full AST and chunk pipeline.
  - impl: Preserve durable document metadata plus at least the repo's needed
    lexical and heading discovery surface for
    `FINAL_COMPREHENSIVE_MCP_ANALYSIS.md`; the repair must not turn the file
    into an ignored document.
  - impl: Keep this lane local to the Markdown plugin. Do not introduce a new
    global lexical timeout knob, and do not widen into a generalized
    Markdown-processing rewrite for every `.md` file.
  - verify: `uv run pytest tests/root_tests/test_markdown_production_scenarios.py -q --no-cov -k analysis`

### SL-2 - Force-Full Lexical Orchestration And Closeout Integration

- **Scope**: Carry the bounded final-analysis repair through the real
  force-full indexing path so the dispatcher and git-index-manager can clear
  the exact `FINAL_COMPREHENSIVE_MCP_ANALYSIS.md` blocker while preserving
  fail-closed timeout behavior for genuinely stalled files.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `mcp_server/storage/git_index_manager.py`
- **Interfaces provided**: IF-0-SEMANALYSIS-2 watchdog preservation
  contract; IF-0-SEMANALYSIS-3 force-full downstream handoff contract
- **Interfaces consumed**: SL-0 dispatcher and git-index-manager timeout
  tests; SL-1 bounded Markdown final-analysis indexing behavior; existing
  `index_directory(...)`, `_index_file_with_lexical_timeout(...)`,
  `_record_low_level_blocker(...)`, `_full_index(...)`, and
  `sync_repository_index(...)`
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 dispatcher and git-index-manager slice first and
    confirm the current low-level lexical blocker still pins the live rerun on
    `FINAL_COMPREHENSIVE_MCP_ANALYSIS.md` before mutating full-sync
    orchestration or closeout logic.
  - impl: If the bounded final-analysis repair requires an explicit force-full
    hint, thread that hint through the existing lexical indexing path for
    analysis-report documents only; do not replace the repo-wide watchdog with
    a globally weaker timeout posture.
  - impl: Preserve the exact SEMIOWAIT, SEMCHANGELOG, and SEMROADMAP
    low-level blocker contract for genuine timeout cases. Files other than the
    repaired final-analysis path must still be able to surface
    `blocked_file_timeout` plus storage diagnostics.
  - impl: Tighten `_full_index(...)` and `sync_repository_index(...)` only as
    needed so a repaired run no longer stops at
    `FINAL_COMPREHENSIVE_MCP_ANALYSIS.md` and instead either reaches
    indexed-commit freshness or carries forward the next exact downstream
    blocker from summary or semantic stages.
  - impl: Do not widen into semantic ranking, storage diagnostics redesign, or
    new repository-readiness taxonomy.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov`
  - verify: `env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`

### SL-3 - Repo-Local Rerun Acceptance Harness

- **Scope**: Make the repo-local semantic dogfood harness prove that
  `SEMANALYSIS` really cleared the exact live blocker instead of only changing
  low-level counters or wording.
- **Owned files**: `tests/real_world/test_semantic_search.py`
- **Interfaces provided**: acceptance checks for IF-0-SEMANALYSIS-3
- **Interfaces consumed**: SL-0 timeout fixtures; SL-1 bounded final-analysis
  repair; SL-2 repaired force-full rerun and closeout behavior; existing
  repo-local semantic dogfood prompt and readiness assertions
- **Parallel-safe**: no
- **Tasks**:
  - test: Update the repo-local dogfood case so it treats
    `Lexical indexing timed out while processing FINAL_COMPREHENSIVE_MCP_ANALYSIS.md`
    as the exact SEMANALYSIS blocker to clear, and after the repair expects
    either semantic-path results on a fresh index or a new exact downstream
    blocker narrower than the final-analysis lexical timeout.
  - impl: Keep this lane bounded to acceptance semantics and blocker wording;
    do not add a new production command or duplicate the full rebuild logic.
  - impl: Reuse the existing real-world env gating and prompt surface rather
    than creating a SEMANALYSIS-only dogfood harness.
  - verify: `RUN_REAL_WORLD_TESTS=1 SEMANTIC_SEARCH_ENABLED=true CODE_INDEX_DOGFOOD_REPO=. OPENAI_API_KEY=dummy-local-key uv run --extra dev python -m pytest tests/real_world/test_semantic_search.py -q --no-cov -k repo_local_dogfood_queries_stay_on_semantic_path -rs`

### SL-4 - Dogfood Evidence Reducer And Operator Guide Refresh

- **Scope**: Re-run the repaired repo-local force-full sequence, reduce the
  outcome into the durable dogfood evidence artifact, and refresh operator
  guidance so the final-analysis lexical repair and its downstream verdict are
  easy to distinguish from the older `CHANGELOG.md` and `ROADMAP.md` blocker
  states.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `docs/guides/semantic-onboarding.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: IF-0-SEMANALYSIS-4 evidence contract
- **Interfaces consumed**: SL-0 timeout contract wording; SL-1 bounded
  final-analysis repair; SL-2 rerun command and indexed-commit status; SL-3
  repo-local dogfood acceptance verdict
- **Parallel-safe**: no
- **Tasks**:
  - test: Update `tests/docs/test_semdogfood_evidence_contract.py` so the
    evidence report must cite `plans/phase-plan-v7-SEMANALYSIS.md`, describe
    the final-analysis repair, and require either a ready-path verdict or a
    new exact downstream blocker that is narrower than the prior
    `FINAL_COMPREHENSIVE_MCP_ANALYSIS.md` timeout message.
  - impl: Re-run the repo-local force-full rebuild with the same strict
    watchdog posture used by SEMCHANGELOG and SEMROADMAP, record whether the
    run now clears `FINAL_COMPREHENSIVE_MCP_ANALYSIS.md`, and capture the next
    exact outcome together with current-versus-indexed commit evidence,
    `chunk_summaries`, and `semantic_points`.
  - impl: Refresh `docs/guides/semantic-onboarding.md` so operators can tell
    the difference between the older SEMROADMAP blocker on
    `FINAL_COMPREHENSIVE_MCP_ANALYSIS.md` and the repaired SEMANALYSIS state,
    including where to look for the next bounded blocker if the rerun still
    does not finish fully.
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
uv run pytest tests/root_tests/test_markdown_production_scenarios.py -q --no-cov -k analysis
env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
env OPENAI_API_KEY=dummy-local-key uv run mcp-index index check-semantic
RUN_REAL_WORLD_TESTS=1 SEMANTIC_SEARCH_ENABLED=true CODE_INDEX_DOGFOOD_REPO=. OPENAI_API_KEY=dummy-local-key uv run --extra dev python -m pytest tests/real_world/test_semantic_search.py -q --no-cov -k repo_local_dogfood_queries_stay_on_semantic_path -rs
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
```

Whole-phase regression guard:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov
uv run pytest tests/root_tests/test_markdown_production_scenarios.py -q --no-cov -k analysis
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
RUN_REAL_WORLD_TESTS=1 SEMANTIC_SEARCH_ENABLED=true CODE_INDEX_DOGFOOD_REPO=. OPENAI_API_KEY=dummy-local-key uv run --extra dev python -m pytest tests/real_world/test_semantic_search.py -q --no-cov -k repo_local_dogfood_queries_stay_on_semantic_path -rs
```

## Acceptance Criteria

- [ ] A clean `uv run mcp-index repository sync --force-full` no longer exits
      with `Lexical indexing timed out while processing FINAL_COMPREHENSIVE_MCP_ANALYSIS.md`.
- [ ] The chosen repair for `FINAL_COMPREHENSIVE_MCP_ANALYSIS.md` is bounded
      and preserves durable lexical indexing for the analysis report; the file
      is not silently ignored or dropped from document or heading discovery
      just to satisfy the watchdog.
- [ ] Synthetic non-analysis timeout fixtures still fail closed through the
      existing low-level blocker contract, proving the watchdog remains active
      for genuine path-level stalls.
- [ ] After the final-analysis repair, the live repo-local rerun either
      completes through indexed-commit freshness and semantic closeout or
      surfaces a new exact downstream blocker that is narrower than the
      current final-analysis lexical timeout.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the final-analysis
      repair, the rerun outcome, current-versus-indexed commit evidence,
      durable counts, and the final ready or still-blocked verdict on the
      current commit.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v7-SEMANALYSIS.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMANALYSIS.md
  artifact_state: staged
```
