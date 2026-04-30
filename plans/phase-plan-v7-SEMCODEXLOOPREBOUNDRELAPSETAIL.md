---
phase_loop_plan_version: 1
phase: SEMCODEXLOOPREBOUNDRELAPSETAIL
roadmap: specs/phase-plans-v7.md
roadmap_sha256: 2944e3819610e56c2ede1834191c426e57ad2e62d7c93dda1656a291eb3e22ac
---
# SEMCODEXLOOPREBOUNDRELAPSETAIL: Legacy Codex Phase-Loop Rebound Relapse Tail Recovery

## Context

SEMCODEXLOOPREBOUNDRELAPSETAIL is the phase-88 follow-up for the v7 semantic
hardening roadmap. Canonical `.phase-loop/` runtime exists in this checkout,
so it is the authoritative runner state for this planning run. The canonical
snapshots are aligned for this phase: `.phase-loop/state.json` and
`.phase-loop/tui-handoff.md` both identify
`SEMCODEXLOOPREBOUNDRELAPSETAIL` as the current `unplanned` phase for
`specs/phase-plans-v7.md`, and the recorded roadmap hash matches the
user-required
`2944e3819610e56c2ede1834191c426e57ad2e62d7c93dda1656a291eb3e22ac`.
Legacy `.codex/phase-loop/` artifacts remain compatibility-only and must not
supersede canonical `.phase-loop/` state.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is the active roadmap, it is tracked and clean in
  this worktree, and `sha256sum specs/phase-plans-v7.md` matches the
  user-required
  `2944e3819610e56c2ede1834191c426e57ad2e62d7c93dda1656a291eb3e22ac`.
- The checkout is on `main...origin/main [ahead 171]` at `HEAD`
  `b5ca16d4593d5056ccc9cef75ac2d9c6d04ce207`, the worktree is clean before
  this artifact write, and
  `plans/phase-plan-v7-SEMCODEXLOOPREBOUNDRELAPSETAIL.md` did not exist
  before this run.
- The latest canonical handoff names this phase as the next required step
  after `SEMCODEXLOOPGARECUTHEARTBEATTAIL`, and its recorded live evidence
  matches the phase-88 objective: the refreshed repo-local force-full rerun
  advanced beyond the exact legacy heartbeat seam
  `.codex/phase-loop/runs/20260425T051448Z-01-garecut-execute/launch.json ->
  .codex/phase-loop/runs/20260425T051448Z-01-garecut-execute/heartbeat.json`
  and later regressed earlier in lexical walking to the re-exposed legacy
  rebound pair
  `.codex/phase-loop/runs/20260424T190651Z-01-garc-plan/launch.json ->
  .codex/phase-loop/runs/20260427T075236Z-05-idxsafe-repair/terminal-summary.json`.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` already contains a dedicated
  `## SEMCODEXLOOPGARECUTHEARTBEATTAIL Live Rerun Check` block that records
  the current blocker handoff for this phase. That block freezes the
  authoritative timestamps for the re-exposed pair:
  `2026-04-30T03:45:02Z` for the raw running
  `.mcp-index/force_full_exit_trace.json` snapshot and
  `2026-04-30T03:45:14Z` for the `repository status` verdict that preserved
  the same `garc-plan launch.json -> idxsafe-repair terminal-summary.json`
  pair.
- Existing coverage already freezes the exact re-exposed pair in the unit
  test surfaces named by the roadmap. `tests/test_dispatcher.py` already
  proves exact bounded indexing and FTS discoverability for the
  `garc-plan -> idxsafe-repair` pair, while
  `tests/test_git_index_manager.py` and `tests/test_repository_commands.py`
  already preserve that pair in durable trace and operator-status fixtures.
- `mcp_server/plugins/generic_treesitter_plugin.py` already owns the narrow
  legacy `.codex/phase-loop` exact-bounded JSON and JSONL family, and
  `mcp_server/cli/repository_commands.py` already prints the generic
  authority split line
  `Lexical boundary: using exact bounded JSON/JSONL indexing for legacy .codex/phase-loop compatibility runtime artifacts while canonical .phase-loop remains authoritative`.
  This phase should preserve those contracts instead of reopening broad
  matcher work.
- The remaining visible gap is not absence of pair-specific fixtures. It is
  that the same older rebound pair resurfaced again after later seams were
  already cleared. Execution therefore needs to prove whether the remaining
  defect is still a production truth-surface issue, a stale precedence or
  closeout-handoff problem, or only an evidence and roadmap-steering lag with
  no runtime diff required.
- `tests/docs/test_semdogfood_evidence_contract.py` already references the
  downstream roadmap addition
  `roadmap now adds downstream phase \`SEMCODEXLOOPREBOUNDRELAPSETAIL\``,
  but repo search does not yet show an execution-ready plan artifact for this
  phase or a dedicated
  `## SEMCODEXLOOPREBOUNDRELAPSETAIL Live Rerun Check` block in the checked-in
  dogfood report.

Practical planning boundary:

- SEMCODEXLOOPREBOUNDRELAPSETAIL should be treated as a narrow
  re-exposed-earlier-pair recovery slice for the exact
  `.codex/phase-loop/runs/20260424T190651Z-01-garc-plan/launch.json ->
  .codex/phase-loop/runs/20260427T075236Z-05-idxsafe-repair/terminal-summary.json`
  seam after later phases already cleared the
  `garecut-execute launch.json -> heartbeat.json` blocker.
- Canonical `.phase-loop/` must remain authoritative throughout. This phase
  must not mutate legacy `.codex/phase-loop` files directly, must not route
  canonical `.phase-loop/state.json`, `.phase-loop/events.jsonl`, or
  `.phase-loop/tui-handoff.md` through legacy compatibility shortcuts, and
  must not reopen the cleared
  `.codex/phase-loop/runs/20260425T051448Z-01-garecut-execute/launch.json ->
  .codex/phase-loop/runs/20260425T051448Z-01-garecut-execute/heartbeat.json`
  seam without new live evidence.
- Because the checked-in dispatcher, durable trace, and CLI tests already
  cover the exact pair, execution should first refresh those fixtures with
  the right precedence and negative guards before assuming the production
  runtime still needs a broader change.
- Broad `.codex/**` matching, canonical `.phase-loop/**` bypasses, reopening
  earlier SEMQUERYFULLTAIL or SEMQUERYFULLREBOUNDTAIL script seams, or
  widening into unrelated semantic, release, or security work are out of
  scope unless the refreshed rerun proves the blocker has moved again.

## Interface Freeze Gates

- [ ] IF-0-SEMCODEXLOOPREBOUNDRELAPSETAIL-1 - Exact rebound-relapse advance
      contract: a refreshed repo-local force-full rerun on the
      post-SEMCODEXLOOPGARECUTHEARTBEATTAIL head no longer terminalizes with
      the durable blocker centered on
      `.codex/phase-loop/runs/20260424T190651Z-01-garc-plan/launch.json ->
      .codex/phase-loop/runs/20260427T075236Z-05-idxsafe-repair/terminal-summary.json`;
      it either advances durably beyond that exact pair or emits a truthful
      newer blocker before the 120-second watchdog expires.
- [ ] IF-0-SEMCODEXLOOPREBOUNDRELAPSETAIL-2 - Narrow repair contract: any
      repair chosen for this re-exposed earlier legacy `.codex/phase-loop`
      rebound seam stays narrow, tested, and does not reopen the cleared
      `.codex/phase-loop/runs/20260425T051448Z-01-garecut-execute/launch.json ->
      .codex/phase-loop/runs/20260425T051448Z-01-garecut-execute/heartbeat.json`
      seam or broaden into blanket `.codex/**` or `.phase-loop/**` bypasses
      without direct evidence.
- [ ] IF-0-SEMCODEXLOOPREBOUNDRELAPSETAIL-3 - Authority-split contract:
      canonical `.phase-loop/` remains authoritative runner state, legacy
      `.codex/phase-loop/` treatment stays compatibility-only, and the phase
      does not route canonical `.phase-loop/state.json`,
      `.phase-loop/events.jsonl`, or `.phase-loop/tui-handoff.md` through the
      same legacy compatibility path.
- [ ] IF-0-SEMCODEXLOOPREBOUNDRELAPSETAIL-4 - Bounded discoverability
      contract: the exact `garc-plan launch.json -> idxsafe-repair
      terminal-summary.json` pair remains lexically discoverable with durable
      file storage and bounded content discoverability for checked-in runtime
      keys and phrases such as `command`, `phase`, `artifact_paths`,
      `terminal_status`, `next_action`, `current_phase`, and
      `.codex/phase-loop`.
- [ ] IF-0-SEMCODEXLOOPREBOUNDRELAPSETAIL-5 - Durable trace and operator
      contract: `.mcp-index/force_full_exit_trace.json`,
      `GitAwareIndexManager`, and `uv run mcp-index repository status` stay
      aligned with the repaired rebound-relapse outcome and do not leave
      stale blame on the cleared `garecut-execute` seam or on the exact
      `garc-plan -> idxsafe-repair` pair after progress has already moved
      later.
- [ ] IF-0-SEMCODEXLOOPREBOUNDRELAPSETAIL-6 - Evidence and steering
      contract: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMCODEXLOOPGARECUTHEARTBEATTAIL rerun outcome, adds a dedicated
      `SEMCODEXLOOPREBOUNDRELAPSETAIL` live-rerun block, and captures the
      final authoritative verdict for the exact
      `garc-plan launch.json -> idxsafe-repair terminal-summary.json` pair;
      if execution exposes a blocker beyond the current roadmap tail,
      `specs/phase-plans-v7.md` is amended before closeout so `.phase-loop/`
      points to the newest truthful next phase.

## Lane Index & Dependencies

- SL-0 - Exact `garc-plan -> idxsafe-repair` dispatcher contract refresh; Depends on: SEMCODEXLOOPGARECUTHEARTBEATTAIL; Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 - Durable trace and repository-status rebound-relapse fixtures; Depends on: SL-0; Blocks: SL-2, SL-3, SL-4; Parallel-safe: no
- SL-2 - Minimal rebound-relapse runtime or truth repair; Depends on: SL-0, SL-1; Blocks: SL-3, SL-4; Parallel-safe: no
- SL-3 - Live rerun evidence reducer and docs contract refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SL-4; Parallel-safe: no
- SL-4 - Downstream roadmap steering reducer; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: SEMCODEXLOOPREBOUNDRELAPSETAIL acceptance; Parallel-safe: no

Lane DAG:

```text
SEMCODEXLOOPGARECUTHEARTBEATTAIL
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SL-4 -> SEMCODEXLOOPREBOUNDRELAPSETAIL acceptance
```

## Lanes

### SL-0 - Exact `garc-plan -> idxsafe-repair` Dispatcher Contract Refresh

- **Scope**: Refresh deterministic dispatcher coverage for the exact
  `.codex/phase-loop/runs/20260424T190651Z-01-garc-plan/launch.json ->
  .codex/phase-loop/runs/20260427T075236Z-05-idxsafe-repair/terminal-summary.json`
  pair so execution proves the older pair can still be surfaced truthfully
  after later seams were already cleared.
- **Owned files**: `tests/test_dispatcher.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMCODEXLOOPREBOUNDRELAPSETAIL-1,
  IF-0-SEMCODEXLOOPREBOUNDRELAPSETAIL-2,
  IF-0-SEMCODEXLOOPREBOUNDRELAPSETAIL-3, and
  IF-0-SEMCODEXLOOPREBOUNDRELAPSETAIL-4 at the dispatcher boundary
- **Interfaces consumed**: existing `Dispatcher.index_directory(...)`;
  `GenericTreeSitterPlugin._exact_bounded_legacy_codex_phase_loop_json_reason(...)`;
  `GenericTreeSitterPlugin._exact_bounded_legacy_codex_phase_loop_jsonl_reason(...)`;
  current repo-shaped fixtures for the exact pair; and canonical `.phase-loop`
  non-legacy JSON routing
- **Parallel-safe**: no
- **Tasks**:
  - test: Refresh `tests/test_dispatcher.py` coverage for the exact
    `garc-plan launch.json -> idxsafe-repair terminal-summary.json` pair so
    the dispatcher contract still proves durable file rows, zero code chunks,
    and FTS-backed discoverability for that exact pair on the rebound-relapse
    head.
  - test: Add negative guards that the cleared
    `.codex/phase-loop/runs/20260425T051448Z-01-garecut-execute/launch.json ->
    .codex/phase-loop/runs/20260425T051448Z-01-garecut-execute/heartbeat.json`
    seam does not remain the sticky reported blocker once the rerun regresses
    earlier to `garc-plan -> idxsafe-repair`.
  - test: Keep guards proving the exact pair still exposes checked-in runtime
    keys and phrases such as `command`, `phase`, `artifact_paths`,
    `terminal_status`, `next_action`, `current_phase`, and `.codex/phase-loop`
    rather than becoming an indexing blind spot.
  - test: Keep negative guards proving canonical `.phase-loop/state.json`,
    `.phase-loop/events.jsonl`, and `.phase-loop/tui-handoff.md` remain on
    their normal non-legacy path.
  - impl: Keep fixtures deterministic with repo-local JSON strings and
    bounded-path assertions rather than live `sync --force-full` waits.
  - impl: Keep this lane on contract refresh only. Do not mutate dispatcher
    implementation, durable trace logic, CLI wording, docs, or roadmap
    steering here.
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "garc or idxsafe or garecut or legacy_codex_phase_loop or terminal_summary or launch or bounded or phase_loop"`

### SL-1 - Durable Trace And Repository-Status Rebound-Relapse Fixtures

- **Scope**: Refresh the exact `garc-plan launch.json -> idxsafe-repair
  terminal-summary.json` pair at the durable trace and operator surface so
  execution can distinguish a real runtime repair from a report that still
  blames the cleared `garecut-execute` seam or leaves stale blame on the
  exact pair after progress has already moved later.
- **Owned files**: `tests/test_git_index_manager.py`, `tests/test_repository_commands.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMCODEXLOOPREBOUNDRELAPSETAIL-1,
  IF-0-SEMCODEXLOOPREBOUNDRELAPSETAIL-3, and
  IF-0-SEMCODEXLOOPREBOUNDRELAPSETAIL-5
- **Interfaces consumed**: existing durable trace lifecycle in
  `GitAwareIndexManager`; repository-status interrupted and stale-running
  output; `_print_legacy_codex_phase_loop_boundary(...)`; and the current
  `SEMCODEXLOOPGARECUTHEARTBEATTAIL` evidence lineage in
  `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- **Parallel-safe**: no
- **Tasks**:
  - test: Refresh or extend `tests/test_git_index_manager.py` so running and
    interrupted force-full traces preserve the exact `garc-plan ->
    idxsafe-repair` pair when it is the truthful blocker after later seams
    were cleared, then promote a later blocker or closeout state once the
    pair is truly cleared.
  - test: Refresh `tests/test_repository_commands.py` so `repository status`
    reports the interrupted trace against the exact `garc-plan ->
    idxsafe-repair` pair while preserving the generic legacy `.codex/phase-loop`
    boundary line and the canonical `.phase-loop` authority wording.
  - test: Add negative guards proving the cleared `garecut-execute
    launch.json -> heartbeat.json` seam does not remain the reported active
    blocker once the current fixtures are introduced.
  - impl: Model closeout and successor promotion with synthetic trace
    payloads or monkeypatched manager behavior rather than live
    `sync --force-full` execution inside unit tests.
  - impl: Keep this lane fixture-only. Do not update production runtime code,
    docs, or roadmap steering here.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "garc or idxsafe or garecut or legacy_codex_phase_loop or interrupted or boundary or closeout_handoff or phase_loop"`

### SL-2 - Minimal Rebound-Relapse Runtime Or Truth Repair

- **Scope**: Implement the smallest production repair needed so the
  current-head force-full rerun no longer leaves the re-exposed
  `garc-plan launch.json -> idxsafe-repair terminal-summary.json` pair as the
  active lexical watchdog tail, or prove with the refreshed fixtures and live
  rerun that no runtime diff is required before evidence and steering update.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `mcp_server/storage/git_index_manager.py`, `mcp_server/cli/repository_commands.py`
- **Interfaces provided**: IF-0-SEMCODEXLOOPREBOUNDRELAPSETAIL-1 exact
  rebound-relapse advance contract;
  IF-0-SEMCODEXLOOPREBOUNDRELAPSETAIL-2 narrow repair contract;
  IF-0-SEMCODEXLOOPREBOUNDRELAPSETAIL-3 authority-split contract;
  IF-0-SEMCODEXLOOPREBOUNDRELAPSETAIL-4 bounded discoverability contract; and
  IF-0-SEMCODEXLOOPREBOUNDRELAPSETAIL-5 durable trace and operator contract
- **Interfaces consumed**: SL-0 dispatcher fixtures; SL-1 durable
  trace/status fixtures; existing exact-bounded legacy `.codex/phase-loop`
  compatibility handling; and the current generic legacy boundary wording in
  `repository_commands.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 and SL-1 slices first and confirm whether the active
    defect is dispatcher-side precedence for the exact pair, durable
    closeout-trace promotion after later lexical progress, CLI trace/status
    wording, or only stale evidence with no remaining production defect.
  - impl: Prefer the smallest repair surface that matches the frozen tests and
    live evidence. Acceptable outcomes include a dispatcher precedence fix, a
    `GitAwareIndexManager` trace-promotion correction, a `repository status`
    truth repair, or an explicit no-runtime-diff outcome if the refreshed
    fixtures and live rerun prove the existing rebound repair still holds.
  - impl: Preserve the generic legacy boundary line and canonical
    `.phase-loop` authority split. Do not widen path matching into blanket
    `.codex/**` or `.phase-loop/**` behavior.
  - impl: Keep the cleared `garecut-execute launch.json -> heartbeat.json`
    seam closed unless the live rerun on this head proves it really reopened.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "garc or idxsafe or garecut or legacy_codex_phase_loop or interrupted or boundary or closeout_handoff or phase_loop"`

### SL-3 - Live Rerun Evidence Reducer And Docs Contract Refresh

- **Scope**: Re-run the bounded force-full command on the post-SL-2 head and
  reduce the resulting evidence into the checked-in dogfood report and docs
  contract so the final blocker verdict is explicit, reproducible, and
  phase-local.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: IF-0-SEMCODEXLOOPREBOUNDRELAPSETAIL-1 final
  rerun verdict; IF-0-SEMCODEXLOOPREBOUNDRELAPSETAIL-5 operator truth
  evidence; and IF-0-SEMCODEXLOOPREBOUNDRELAPSETAIL-6 docs/evidence contract
- **Interfaces consumed**: SL-2 runtime outcome; current
  `SEMCODEXLOOPGARECUTHEARTBEATTAIL` evidence block; `repository status`
  output; `.mcp-index/force_full_exit_trace.json`; SQLite runtime counts; and
  current docs contract expectations in
  `tests/docs/test_semdogfood_evidence_contract.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Add or refresh docs-contract assertions for
    `Phase plan: \`plans/phase-plan-v7-SEMCODEXLOOPREBOUNDRELAPSETAIL.md\``,
    `Prior phase plan: \`plans/phase-plan-v7-SEMCODEXLOOPGARECUTHEARTBEATTAIL.md\``,
    the dedicated `## SEMCODEXLOOPREBOUNDRELAPSETAIL Live Rerun Check` block,
    the exact `garc-plan -> idxsafe-repair` pair, and the final steering
    statement for whether this phase satisfied its named blocker or exposed a
    newer blocker.
  - impl: Run `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`,
    then capture `uv run mcp-index repository status`,
    `.mcp-index/force_full_exit_trace.json`, and SQLite counts on the same
    head.
  - impl: Update `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` with the refreshed
    rerun command, timestamps, exact pair, current counts, readiness lines,
    and a clear final verdict stating whether the exact pair was cleared,
    remained active, or yielded a newer blocker.
  - impl: If the rerun advances beyond the `garc-plan -> idxsafe-repair`
    pair, state clearly that the `garecut-execute launch.json -> heartbeat.json`
    seam stays closed and that the current blocker has moved later.
  - impl: If the rerun still terminates on the exact pair, make that failure
    explicit and keep the steering note truthful rather than implying success.
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "SEMCODEXLOOPGARECUTHEARTBEATTAIL or SEMCODEXLOOPREBOUNDRELAPSETAIL or garc or idxsafe or phase_loop"`

### SL-4 - Downstream Roadmap Steering Reducer

- **Scope**: Keep the roadmap truthful after the refreshed rerun by only
  adding a downstream phase when SL-3 proves the active blocker moved beyond
  the current roadmap tail.
- **Owned files**: `specs/phase-plans-v7.md`
- **Interfaces provided**: the downstream-steering portion of
  IF-0-SEMCODEXLOOPREBOUNDRELAPSETAIL-6
- **Interfaces consumed**: SL-3 refreshed evidence verdict; current roadmap
  DAG and tail ordering for `specs/phase-plans-v7.md`; and canonical
  `.phase-loop/` expectations that the next unplanned phase reflect the latest
  durable blocker rather than stale rebound-relapse assumptions
- **Parallel-safe**: no
- **Tasks**:
  - test: Re-read the post-SL-3 evidence and confirm whether the repaired
    rerun actually exposes a newer blocker beyond the current roadmap tail
    before mutating roadmap steering.
  - impl: If the active blocker remains inside the current
    `garc-plan launch.json -> idxsafe-repair terminal-summary.json` pair or
    the rerun completes lexical closeout without exposing a new tail, leave
    the roadmap unchanged.
  - impl: If the rerun advances beyond the current roadmap tail and no
    downstream phase already covers the new blocker, append the nearest
    truthful downstream recovery phase to `specs/phase-plans-v7.md` with the
    same evidence-first structure used by the current SEM* lexical-recovery
    chain.
  - impl: Keep any roadmap mutation limited to the newly exposed blocker. Do
    not rewrite earlier phases or reopen
    `SEMCODEXLOOPGARECUTHEARTBEATTAIL` assumptions while closing this
    rebound-relapse seam.
  - verify: `git diff -- specs/phase-plans-v7.md`

## Verification

Planning-only run: do not execute these during plan creation. Run them during
`codex-execute-phase` or manual SEMCODEXLOOPREBOUNDRELAPSETAIL execution.

Lane-specific checks:

```bash
uv run pytest tests/test_dispatcher.py -q --no-cov -k "garc or idxsafe or garecut or legacy_codex_phase_loop or terminal_summary or launch or bounded or phase_loop"
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "garc or idxsafe or garecut or legacy_codex_phase_loop or interrupted or boundary or closeout_handoff or phase_loop"
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "garc or idxsafe or garecut or legacy_codex_phase_loop or interrupted or boundary or closeout_handoff or phase_loop"
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "SEMCODEXLOOPGARECUTHEARTBEATTAIL or SEMCODEXLOOPREBOUNDRELAPSETAIL or garc or idxsafe or phase_loop"
timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
sed -n '1,240p' .mcp-index/force_full_exit_trace.json
sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'
```

Whole-phase regression commands:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest \
  tests/test_dispatcher.py \
  tests/test_git_index_manager.py \
  tests/test_repository_commands.py \
  tests/docs/test_semdogfood_evidence_contract.py \
  -q --no-cov -k "garc or idxsafe or garecut or legacy_codex_phase_loop or interrupted or boundary or closeout_handoff or phase_loop"
timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
sed -n '1,240p' .mcp-index/force_full_exit_trace.json
git status --short -- plans/phase-plan-v7-SEMCODEXLOOPREBOUNDRELAPSETAIL.md docs/status/SEMANTIC_DOGFOOD_REBUILD.md specs/phase-plans-v7.md
git diff --check
git diff --cached --check
```

## Acceptance Criteria

- [ ] A refreshed repo-local force-full rerun on the
      post-SEMCODEXLOOPGARECUTHEARTBEATTAIL head either advances durably
      beyond the re-exposed earlier legacy
      `.codex/phase-loop/runs/20260424T190651Z-01-garc-plan/launch.json ->
      .codex/phase-loop/runs/20260427T075236Z-05-idxsafe-repair/terminal-summary.json`
      pair or emits a truthful newer blocker before the 120-second watchdog
      expires.
- [ ] Any repair chosen for the legacy `.codex/phase-loop` rebound-relapse
      seam stays narrow, tested, and does not reopen the cleared
      `.codex/phase-loop/runs/20260425T051448Z-01-garecut-execute/launch.json ->
      .codex/phase-loop/runs/20260425T051448Z-01-garecut-execute/heartbeat.json`
      boundary without direct evidence.
- [ ] Canonical `.phase-loop/` remains authoritative runner state, and the
      repair does not route canonical `.phase-loop/state.json`,
      `.phase-loop/events.jsonl`, or `.phase-loop/tui-handoff.md` through the
      same legacy compatibility path.
- [ ] The exact `garc-plan launch.json -> idxsafe-repair terminal-summary.json`
      pair remains lexically discoverable with durable file storage and
      bounded content discoverability for checked-in runtime keys and phrases
      such as `command`, `phase`, `artifact_paths`, `terminal_status`,
      `next_action`, `current_phase`, and `.codex/phase-loop`.
- [ ] `.mcp-index/force_full_exit_trace.json` and
      `uv run mcp-index repository status` stay aligned with the repaired
      rebound-relapse outcome and do not leave stale blame on the cleared
      `garecut-execute` seam or on the exact `garc-plan -> idxsafe-repair`
      pair after progress has already moved beyond them.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMCODEXLOOPGARECUTHEARTBEATTAIL rerun outcome and the final live
      verdict for the exact `garc-plan -> idxsafe-repair` pair.
- [ ] If execution reveals a newer blocker beyond the current roadmap tail,
      `specs/phase-plans-v7.md` is updated before closeout so the next
      phase-loop step stays truthful.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMCODEXLOOPREBOUNDRELAPSETAIL.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMCODEXLOOPREBOUNDRELAPSETAIL.md
  artifact_state: staged
```
