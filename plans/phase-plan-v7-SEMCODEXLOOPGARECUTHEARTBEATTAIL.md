---
phase_loop_plan_version: 1
phase: SEMCODEXLOOPGARECUTHEARTBEATTAIL
roadmap: specs/phase-plans-v7.md
roadmap_sha256: 7529b09c8f12eafe40c0e6dc25b14e31537098f4bafe91fdca682c1d4b04d79b
---
# SEMCODEXLOOPGARECUTHEARTBEATTAIL: Legacy Codex Phase-Loop GARECUT Heartbeat Tail Recovery

## Context

SEMCODEXLOOPGARECUTHEARTBEATTAIL is the phase-87 follow-up for the v7 semantic
hardening roadmap. Canonical `.phase-loop/` runtime exists in this checkout,
so it is the authoritative runner state for this planning run. The canonical
state is aligned for this phase: `.phase-loop/tui-handoff.md` and
`.phase-loop/state.json` both identify
`SEMCODEXLOOPGARECUTHEARTBEATTAIL` as the current `unplanned` phase for
`specs/phase-plans-v7.md`, and the recorded roadmap hash matches the
user-required
`7529b09c8f12eafe40c0e6dc25b14e31537098f4bafe91fdca682c1d4b04d79b`.
Legacy `.codex/phase-loop/` artifacts remain compatibility-only and must not
supersede canonical `.phase-loop/` state.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is the active roadmap, it is tracked and clean in
  this worktree, and `sha256sum specs/phase-plans-v7.md` matches the
  user-required
  `7529b09c8f12eafe40c0e6dc25b14e31537098f4bafe91fdca682c1d4b04d79b`.
- The checkout is on `main...origin/main [ahead 169]` at `HEAD`
  `fd9de7cc552bc2526369fc4f07e1e4602859c264`, the worktree is clean before
  this artifact write, and
  `plans/phase-plan-v7-SEMCODEXLOOPGARECUTHEARTBEATTAIL.md` did not exist
  before this run.
- The latest canonical handoff names this phase as the next required step
  after `SEMCODEXLOOPRELAPSEREBOUNDTAIL`, and its recorded live evidence
  matches the phase-87 objective: the refreshed repo-local force-full rerun
  advanced beyond the re-exposed legacy
  `.codex/phase-loop/runs/20260427T081107Z-08-ciflow-plan/terminal-summary.json ->
  .codex/phase-loop/runs/20260427T081107Z-08-ciflow-plan/launch.json`
  pair and later terminalized on the newer exact legacy heartbeat seam
  `.codex/phase-loop/runs/20260425T051448Z-01-garecut-execute/launch.json ->
  .codex/phase-loop/runs/20260425T051448Z-01-garecut-execute/heartbeat.json`.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` already contains a dedicated
  `## SEMCODEXLOOPRELAPSEREBOUNDTAIL Live Rerun Check` block that records the
  current blocker handoff for this phase, including the authoritative
  `2026-04-30T03:26:35Z` force-full trace snapshot and the
  `2026-04-30T03:26:49Z` `repository status` verdict preserving the same
  `garecut-execute` `launch.json -> heartbeat.json` pair.
- Existing coverage already freezes nearby legacy compatibility-runtime
  behavior, but repo search did not show the exact `garecut-execute`
  `launch.json -> heartbeat.json` pair in
  `tests/test_dispatcher.py`, `tests/test_git_index_manager.py`, or
  `tests/test_repository_commands.py`. Those files currently freeze the older
  `gagov-execute`, `artpub-plan`, and `ciflow-plan` seams instead.
- `tests/docs/test_semdogfood_evidence_contract.py` already mentions the exact
  `garecut-execute` pair and the downstream phase name
  `SEMCODEXLOOPGARECUTHEARTBEATTAIL`, so execution should update the checked-in
  dogfood report and its contract test together rather than inventing a new
  evidence surface.
- `mcp_server/cli/repository_commands.py` already prints the generic
  compatibility boundary
  `Lexical boundary: using exact bounded JSON/JSONL indexing for legacy .codex/phase-loop compatibility runtime artifacts while canonical .phase-loop remains authoritative`.
  This phase should preserve that authority split while making the exact
  `garecut-execute` heartbeat pair truthful at the dispatcher, durable trace,
  and operator-status surfaces.

Practical planning boundary:

- SEMCODEXLOOPGARECUTHEARTBEATTAIL should be treated as the next narrow
  legacy compatibility-runtime slice for the exact
  `.codex/phase-loop/runs/20260425T051448Z-01-garecut-execute/launch.json ->
  .codex/phase-loop/runs/20260425T051448Z-01-garecut-execute/heartbeat.json`
  seam after later phases already cleared the `artpub-plan` and
  `ciflow-plan` blockers.
- Canonical `.phase-loop/` must remain authoritative throughout. This phase
  must not mutate legacy `.codex/phase-loop` files directly, must not route
  canonical `.phase-loop/state.json`, `.phase-loop/events.jsonl`, or
  `.phase-loop/tui-handoff.md` through legacy compatibility shortcuts, and
  must not reopen the cleared
  `.codex/phase-loop/runs/20260427T081107Z-08-ciflow-plan/terminal-summary.json ->
  .codex/phase-loop/runs/20260427T081107Z-08-ciflow-plan/launch.json`
  seam without new live evidence.
- Because the checked-in evidence already names the exact `garecut-execute`
  pair as the current blocker, execution should first freeze that pair in
  tests and operator surfaces before assuming the production runtime still
  needs a broader change.

## Interface Freeze Gates

- [ ] IF-0-SEMCODEXLOOPGARECUTHEARTBEATTAIL-1 - Exact garecut heartbeat advance
      contract: a refreshed repo-local force-full rerun on the
      post-SEMCODEXLOOPRELAPSEREBOUNDTAIL head no longer terminalizes with the
      durable blocker centered on
      `.codex/phase-loop/runs/20260425T051448Z-01-garecut-execute/launch.json ->
      .codex/phase-loop/runs/20260425T051448Z-01-garecut-execute/heartbeat.json`;
      it either advances durably beyond that exact pair or emits a truthful
      newer blocker before the 120-second watchdog expires.
- [ ] IF-0-SEMCODEXLOOPGARECUTHEARTBEATTAIL-2 - Narrow repair contract: any
      repair chosen for this later legacy `.codex/phase-loop` heartbeat seam
      stays narrow, tested, and does not reopen the cleared
      `.codex/phase-loop/runs/20260427T081107Z-08-ciflow-plan/terminal-summary.json ->
      .codex/phase-loop/runs/20260427T081107Z-08-ciflow-plan/launch.json`
      boundary without direct evidence.
- [ ] IF-0-SEMCODEXLOOPGARECUTHEARTBEATTAIL-3 - Authority-split contract:
      canonical `.phase-loop/` remains authoritative runner state, legacy
      `.codex/phase-loop/` treatment stays compatibility-only, and the phase
      does not route canonical `.phase-loop/state.json`,
      `.phase-loop/events.jsonl`, or `.phase-loop/tui-handoff.md` through the
      same legacy compatibility path.
- [ ] IF-0-SEMCODEXLOOPGARECUTHEARTBEATTAIL-4 - Bounded discoverability
      contract: the exact `garecut-execute` `launch.json` and `heartbeat.json`
      files remain lexically discoverable with durable file storage and
      bounded content discoverability for checked-in runtime keys and phrases
      such as `command`, `phase`, `current_phase`, `status`, `trace`,
      `heartbeat`, and `.codex/phase-loop`.
- [ ] IF-0-SEMCODEXLOOPGARECUTHEARTBEATTAIL-5 - Durable trace and operator
      contract: `.mcp-index/force_full_exit_trace.json`,
      `GitAwareIndexManager`, and `uv run mcp-index repository status` stay
      aligned with the repaired `garecut-execute` outcome and do not leave
      stale blame on the cleared `ciflow-plan` pair or on the exact
      `garecut-execute` heartbeat seam after progress has already moved later.
- [ ] IF-0-SEMCODEXLOOPGARECUTHEARTBEATTAIL-6 - Evidence and steering
      contract: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMCODEXLOOPRELAPSEREBOUNDTAIL rerun outcome, adds a dedicated
      `SEMCODEXLOOPGARECUTHEARTBEATTAIL` live-rerun block, and captures the
      final authoritative verdict for the exact `garecut-execute`
      `launch.json -> heartbeat.json` pair; if execution exposes a blocker
      beyond the current roadmap tail, `specs/phase-plans-v7.md` is amended
      before closeout so `.phase-loop/` points to the newest truthful next
      phase.

## Lane Index & Dependencies

- SL-0 - Exact `garecut-execute` dispatcher contract freeze; Depends on: SEMCODEXLOOPRELAPSEREBOUNDTAIL; Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 - Durable trace and repository-status garecut fixtures; Depends on: SL-0; Blocks: SL-2, SL-3, SL-4; Parallel-safe: no
- SL-2 - Minimal garecut heartbeat runtime or truth repair; Depends on: SL-0, SL-1; Blocks: SL-3, SL-4; Parallel-safe: no
- SL-3 - Live rerun evidence reducer and docs contract refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SL-4; Parallel-safe: no
- SL-4 - Downstream roadmap steering reducer; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: SEMCODEXLOOPGARECUTHEARTBEATTAIL acceptance; Parallel-safe: no

Lane DAG:

```text
SEMCODEXLOOPRELAPSEREBOUNDTAIL
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SL-4 -> SEMCODEXLOOPGARECUTHEARTBEATTAIL acceptance
```

## Lanes

### SL-0 - Exact `garecut-execute` Dispatcher Contract Freeze

- **Scope**: Freeze the exact
  `.codex/phase-loop/runs/20260425T051448Z-01-garecut-execute/launch.json ->
  .codex/phase-loop/runs/20260425T051448Z-01-garecut-execute/heartbeat.json`
  seam in deterministic dispatcher coverage so execution proves a narrow
  bounded repair instead of assuming older `artpub-plan` or `ciflow-plan`
  heartbeat fixtures already make the later pair safe.
- **Owned files**: `tests/test_dispatcher.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMCODEXLOOPGARECUTHEARTBEATTAIL-1,
  IF-0-SEMCODEXLOOPGARECUTHEARTBEATTAIL-2,
  IF-0-SEMCODEXLOOPGARECUTHEARTBEATTAIL-3, and
  IF-0-SEMCODEXLOOPGARECUTHEARTBEATTAIL-4 at the dispatcher boundary
- **Interfaces consumed**: existing
  `Dispatcher.index_directory(...)`; current bounded legacy `.codex/phase-loop`
  JSON handling; the older `artpub-plan` and `ciflow-plan` fixture lineage in
  `tests/test_dispatcher.py`; and canonical `.phase-loop` non-legacy JSON
  routing
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` with repo-shaped fixtures for the
    exact `garecut-execute launch.json -> heartbeat.json` pair so the
    dispatcher contract proves durable file rows, zero code chunks, and
    FTS-backed discoverability for both files.
  - test: Assert that the pair still exposes checked-in runtime keys and
    phrases such as `command`, `phase`, `current_phase`, `status`, `trace`,
    `heartbeat`, and `.codex/phase-loop` rather than becoming an indexing
    blind spot.
  - test: Keep negative guards proving the cleared `artpub-plan` and
    `ciflow-plan` seams still pass unchanged and canonical `.phase-loop`
    `state.json` remains on its normal non-legacy JSON/plugin path.
  - impl: Keep fixtures deterministic with repo-local JSON strings and
    bounded-path assertions rather than live `sync --force-full` waits.
  - impl: Keep this lane on contract freeze only. Do not mutate dispatcher
    implementation, durable trace logic, CLI wording, docs, or roadmap
    steering here.
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "garecut or heartbeat or legacy_codex_phase_loop or bounded or phase_loop"`

### SL-1 - Durable Trace And Repository-Status GARECUT Fixtures

- **Scope**: Freeze the exact `garecut-execute launch.json -> heartbeat.json`
  pair at the durable trace and operator surface so execution can distinguish
  a real runtime repair from a report that still blames the already-cleared
  `ciflow-plan` seam or this exact pair after progress has already moved
  later.
- **Owned files**: `tests/test_git_index_manager.py`, `tests/test_repository_commands.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMCODEXLOOPGARECUTHEARTBEATTAIL-1,
  IF-0-SEMCODEXLOOPGARECUTHEARTBEATTAIL-2,
  IF-0-SEMCODEXLOOPGARECUTHEARTBEATTAIL-3, and
  IF-0-SEMCODEXLOOPGARECUTHEARTBEATTAIL-5
- **Interfaces consumed**: existing durable trace lifecycle in
  `GitAwareIndexManager`; `repository status` interrupted and stale-running
  output; the current generic legacy `.codex/phase-loop` boundary line in
  `mcp_server/cli/repository_commands.py`; and the
  SEMCODEXLOOPRELAPSEREBOUNDTAIL evidence lineage in
  `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_git_index_manager.py` so running and interrupted
    force-full traces can preserve the exact
    `garecut-execute launch.json -> heartbeat.json` pair when it is the
    truthful blocker, then promote a later blocker or closeout state once the
    pair has truly been cleared.
  - test: Extend `tests/test_repository_commands.py` so `repository status`
    reports the interrupted trace against the exact `garecut-execute` pair
    while preserving the generic legacy `.codex/phase-loop` boundary line and
    the canonical `.phase-loop` authority wording.
  - test: Keep negative guards proving the cleared
    `.codex/phase-loop/runs/20260427T081107Z-08-ciflow-plan/terminal-summary.json ->
    .codex/phase-loop/runs/20260427T081107Z-08-ciflow-plan/launch.json`
    seam does not remain the reported active blocker once the current
    fixtures are introduced.
  - impl: Model closeout and successor promotion with synthetic trace payloads
    or monkeypatched manager behavior rather than live `sync --force-full`
    execution inside unit tests.
  - impl: Keep this lane fixture-only. Do not update production runtime code,
    docs, or roadmap steering here.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "garecut or heartbeat or legacy_codex_phase_loop or interrupted or boundary or closeout_handoff or phase_loop"`

### SL-2 - Minimal GARECUT Heartbeat Runtime Or Truth Repair

- **Scope**: Implement the smallest production repair needed so the
  current-head force-full rerun no longer leaves the
  `garecut-execute launch.json -> heartbeat.json` pair as the active lexical
  watchdog tail, or prove with the tightened fixtures that no production code
  diff is required before the live rerun and evidence refresh.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `mcp_server/storage/git_index_manager.py`, `mcp_server/cli/repository_commands.py`
- **Interfaces provided**: IF-0-SEMCODEXLOOPGARECUTHEARTBEATTAIL-1 exact
  garecut heartbeat advance contract;
  IF-0-SEMCODEXLOOPGARECUTHEARTBEATTAIL-2 narrow repair contract;
  IF-0-SEMCODEXLOOPGARECUTHEARTBEATTAIL-3 authority-split contract;
  IF-0-SEMCODEXLOOPGARECUTHEARTBEATTAIL-4 bounded discoverability contract;
  and IF-0-SEMCODEXLOOPGARECUTHEARTBEATTAIL-5 durable trace and operator
  contract
- **Interfaces consumed**: SL-0 dispatcher fixtures; SL-1 durable
  trace/status fixtures; existing bounded legacy `.codex/phase-loop`
  compatibility handling; and the current generic legacy boundary wording in
  `repository_commands.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 and SL-1 slices first and confirm whether the active
    defect is dispatcher-side bounded indexing for the exact pair, durable
    closeout-trace promotion after later lexical progress, CLI trace/status
    wording, or only stale evidence with no remaining production defect.
  - impl: Prefer the smallest repair surface that matches the frozen tests and
    live evidence. Acceptable outcomes include a dispatcher bounded-path fix,
    a `GitAwareIndexManager` trace-promotion correction, a `repository status`
    truth repair, or an explicit no-runtime-diff outcome if the refreshed
    fixtures and live rerun prove the older repair still holds.
  - impl: Preserve the generic legacy boundary line and canonical
    `.phase-loop` authority split. Do not broaden to blanket `.codex/**` or
    `.phase-loop/**` handling, do not mutate runner-state files directly, and
    do not regress the cleared `ciflow-plan` relapse seam.
  - impl: If the repair moves the live tail beyond the `garecut-execute`
    pair, ensure the durable trace and operator surface promote the newer
    blocker or closeout stage truthfully instead of leaving stale
    `last_progress_path` or `in_flight_path` blame on the pair.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "garecut or heartbeat or legacy_codex_phase_loop or interrupted or boundary or closeout_handoff or phase_loop"`

### SL-3 - Live Rerun Evidence Reducer And Docs Contract Refresh

- **Scope**: Re-run the bounded repo-local force-full command after SL-2,
  capture the authoritative `garecut-execute` outcome, and refresh the
  dogfood report plus its contract test without widening into unrelated
  semantic claims.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: IF-0-SEMCODEXLOOPGARECUTHEARTBEATTAIL-1 exact
  garecut heartbeat advance contract;
  IF-0-SEMCODEXLOOPGARECUTHEARTBEATTAIL-5 durable trace and operator
  contract; and IF-0-SEMCODEXLOOPGARECUTHEARTBEATTAIL-6 evidence and steering
  contract
- **Interfaces consumed**: SL-2 runtime or truth outcome; live outputs from
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`,
  `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`,
  and `.mcp-index/force_full_exit_trace.json`; plus the existing
  `SEMCODEXLOOPRELAPSEREBOUNDTAIL Live Rerun Check` block
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/docs/test_semdogfood_evidence_contract.py` so the
    report must include a
    `## SEMCODEXLOOPGARECUTHEARTBEATTAIL Live Rerun Check` block, cite the
    SEMCODEXLOOPRELAPSEREBOUNDTAIL prior plan and rerun outcome, and record
    the exact `garecut-execute` pair or its truthful successor.
  - impl: Run the refreshed repo-local force-full rerun after SL-2 using the
    same bounded command from the roadmap evidence, then capture
    `repository status`, `force_full_exit_trace.json`, and SQLite row counts
    on the same head.
  - impl: Update `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` with the final
    authoritative verdict for the exact `garecut-execute`
    `launch.json -> heartbeat.json` pair, explicitly naming whether the rerun
    advanced beyond it, terminalized truthfully on it again, or exposed a
    later blocker.
  - impl: Keep the evidence block semantically fail-closed. Preserve
    readiness, rollout-status, last-sync-error, semantic-readiness, and the
    canonical-versus-legacy authority wording unless the live probes on the
    same head prove they changed.
  - impl: If the rerun advances beyond the pair, state clearly that the
    `ciflow-plan` relapse seam stays closed and that the current blocker has
    moved later.
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "SEMCODEXLOOPRELAPSEREBOUNDTAIL or SEMCODEXLOOPGARECUTHEARTBEATTAIL or garecut or phase_loop"`
  - verify: `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - verify: `sed -n '1,240p' .mcp-index/force_full_exit_trace.json`
  - verify: `sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'`

### SL-4 - Downstream Roadmap Steering Reducer

- **Scope**: Keep the roadmap truthful after the refreshed rerun by only
  adding a downstream phase when SL-3 proves the active blocker moved beyond
  the current roadmap tail.
- **Owned files**: `specs/phase-plans-v7.md`
- **Interfaces provided**: the steering portion of
  IF-0-SEMCODEXLOOPGARECUTHEARTBEATTAIL-6
- **Interfaces consumed**: SL-3 refreshed evidence verdict; current roadmap
  DAG and tail ordering for `specs/phase-plans-v7.md`; and canonical
  `.phase-loop/` expectations that the next unplanned phase reflect the
  latest durable blocker rather than stale `garecut-execute` assumptions
- **Parallel-safe**: no
- **Tasks**:
  - test: Re-read the post-SL-3 evidence and confirm whether the repaired
    rerun actually exposes a newer blocker beyond the current roadmap tail
    before mutating roadmap steering.
  - impl: If the active blocker remains inside the
    `garecut-execute launch.json -> heartbeat.json` pair or the rerun
    completes lexical closeout without exposing a new tail, leave the roadmap
    unchanged.
  - impl: If the rerun advances beyond the current roadmap tail and no
    downstream phase already covers the new blocker, append the nearest
    truthful downstream recovery phase to `specs/phase-plans-v7.md` with the
    same evidence-first structure used by the current SEM* lexical-recovery
    chain.
  - impl: Keep any roadmap mutation limited to the newly exposed blocker. Do
    not rewrite earlier phases or reopen SEMCODEXLOOPRELAPSEREBOUNDTAIL
    assumptions while closing this heartbeat seam.
  - verify: `git diff -- specs/phase-plans-v7.md`

## Verification

Planning-only run: do not execute these during plan creation. Run them during
`codex-execute-phase` or manual SEMCODEXLOOPGARECUTHEARTBEATTAIL execution.

Lane-specific checks:

```bash
uv run pytest tests/test_dispatcher.py -q --no-cov -k "garecut or heartbeat or legacy_codex_phase_loop or bounded or phase_loop"
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "garecut or heartbeat or legacy_codex_phase_loop or interrupted or boundary or closeout_handoff or phase_loop"
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "garecut or heartbeat or legacy_codex_phase_loop or interrupted or boundary or closeout_handoff or phase_loop"
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "SEMCODEXLOOPRELAPSEREBOUNDTAIL or SEMCODEXLOOPGARECUTHEARTBEATTAIL or garecut or phase_loop"
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
  -q --no-cov -k "garecut or heartbeat or legacy_codex_phase_loop or interrupted or boundary or closeout_handoff or phase_loop"
timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
sed -n '1,240p' .mcp-index/force_full_exit_trace.json
git status --short -- plans/phase-plan-v7-SEMCODEXLOOPGARECUTHEARTBEATTAIL.md docs/status/SEMANTIC_DOGFOOD_REBUILD.md specs/phase-plans-v7.md
git diff --check
git diff --cached --check
```

## Acceptance Criteria

- [ ] A refreshed repo-local force-full rerun on the
      post-SEMCODEXLOOPRELAPSEREBOUNDTAIL head either advances durably beyond
      the exact
      `.codex/phase-loop/runs/20260425T051448Z-01-garecut-execute/launch.json ->
      .codex/phase-loop/runs/20260425T051448Z-01-garecut-execute/heartbeat.json`
      pair or emits a truthful newer blocker before the 120-second watchdog
      expires.
- [ ] Any repair chosen for this later legacy `.codex/phase-loop` heartbeat
      seam stays narrow, tested, keeps canonical `.phase-loop/`
      authoritative, and does not reopen the cleared
      `.codex/phase-loop/runs/20260427T081107Z-08-ciflow-plan/terminal-summary.json ->
      .codex/phase-loop/runs/20260427T081107Z-08-ciflow-plan/launch.json`
      boundary without direct evidence.
- [ ] The exact `garecut-execute` `launch.json` and `heartbeat.json` files
      remain lexically discoverable with durable file storage and bounded
      content discoverability for checked-in runtime keys and phrases such as
      `command`, `phase`, `current_phase`, `status`, `trace`, `heartbeat`,
      and `.codex/phase-loop`.
- [ ] `.mcp-index/force_full_exit_trace.json` and
      `uv run mcp-index repository status` stay aligned with the repaired
      `garecut-execute` outcome and do not leave stale blame on the cleared
      `ciflow-plan` relapse seam or on the `garecut-execute` pair after
      progress has already moved beyond them.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMCODEXLOOPRELAPSEREBOUNDTAIL rerun outcome and the final live verdict
      for the exact `garecut-execute launch.json -> heartbeat.json` pair.
- [ ] If execution reveals a newer blocker beyond the current roadmap tail,
      `specs/phase-plans-v7.md` is updated before closeout so the next
      phase-loop step stays truthful.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMCODEXLOOPGARECUTHEARTBEATTAIL.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMCODEXLOOPGARECUTHEARTBEATTAIL.md
  artifact_state: staged
```
