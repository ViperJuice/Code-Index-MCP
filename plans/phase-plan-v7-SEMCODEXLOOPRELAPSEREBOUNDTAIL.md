---
phase_loop_plan_version: 1
phase: SEMCODEXLOOPRELAPSEREBOUNDTAIL
roadmap: specs/phase-plans-v7.md
roadmap_sha256: 52efdcae6bc94667a2ba3dd916cbea5492145dafdbd0cb14167010cb830c552e
---
# SEMCODEXLOOPRELAPSEREBOUNDTAIL: Legacy Codex Phase-Loop Relapse Rebound Tail Recovery

## Context

SEMCODEXLOOPRELAPSEREBOUNDTAIL is the phase-86 follow-up for the v7 semantic
hardening roadmap. Canonical `.phase-loop/` runtime exists in this checkout,
so it is the authoritative runner state for this planning run. The canonical
snapshots are aligned for this phase: `.phase-loop/tui-handoff.md` and
`.phase-loop/state.json` both identify `SEMCODEXLOOPRELAPSEREBOUNDTAIL` as
the current `unplanned` phase for `specs/phase-plans-v7.md`, and the recorded
roadmap hash matches the required
`52efdcae6bc94667a2ba3dd916cbea5492145dafdbd0cb14167010cb830c552e`.
Legacy `.codex/phase-loop/` artifacts remain compatibility-only and must not
supersede canonical `.phase-loop/` state.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is the active roadmap, it is tracked and clean in
  this worktree, and `sha256sum specs/phase-plans-v7.md` matches the
  user-required
  `52efdcae6bc94667a2ba3dd916cbea5492145dafdbd0cb14167010cb830c552e`.
- The checkout is on `main...origin/main [ahead 167]` at `HEAD`
  `c1dd94b5d5881dad6c7e5457577ad52779ee3117`, the worktree is currently clean,
  and `plans/phase-plan-v7-SEMCODEXLOOPRELAPSEREBOUNDTAIL.md` did not exist
  before this run.
- The latest canonical handoff names this phase as the next required step
  after `SEMCODEXLOOPHEARTBEATTAIL`, and its recorded live evidence matches
  the phase-86 objective: the refreshed repo-local force-full rerun advanced
  beyond the `artpub-plan launch.json -> heartbeat.json` seam and later
  terminalized on the re-exposed legacy `.codex/phase-loop`
  compatibility-runtime pair
  `.codex/phase-loop/runs/20260427T081107Z-08-ciflow-plan/terminal-summary.json ->
  .codex/phase-loop/runs/20260427T081107Z-08-ciflow-plan/launch.json`.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` already records the current live
  blocker shape from the completed SEMCODEXLOOPHEARTBEATTAIL execution: at
  `2026-04-30T03:09:52Z`, `.mcp-index/force_full_exit_trace.json` still
  showed `status: running`, `stage: lexical_walking`,
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/.codex/phase-loop/runs/20260427T081107Z-08-ciflow-plan/terminal-summary.json`,
  and
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/.codex/phase-loop/runs/20260427T081107Z-08-ciflow-plan/launch.json`.
  At `2026-04-30T03:10:06Z`, `repository status` terminalized that same rerun
  to `Trace status: interrupted` while preserving the same later pair.
- The checked-in evidence also records that the target seam from
  SEMCODEXLOOPHEARTBEATTAIL is no longer the active blocker:
  `.codex/phase-loop/runs/20260427T071207Z-01-artpub-plan/launch.json ->
  .codex/phase-loop/runs/20260427T071207Z-01-artpub-plan/heartbeat.json`.
  This phase therefore starts as a re-exposed regression slice around the
  older `ciflow-plan` pair, not as a continuation of the heartbeat seam.
- Existing repo coverage already freezes the exact `ciflow-plan`
  `terminal-summary.json -> launch.json` pair in
  `tests/test_dispatcher.py`, `tests/test_git_index_manager.py`, and
  `tests/test_repository_commands.py` from the earlier
  SEMCODEXLOOPRELAPSETAIL slice. The exact pair is therefore not brand-new
  contract territory; the likely remaining work is re-anchoring that coverage
  to the later re-exposed context, tightening successor truth, or proving
  that only docs/roadmap steering changed.
- `tests/test_dispatcher.py` already proves bounded lexical discoverability
  for runtime keys such as `artifact_paths`, `terminal_status`, `next_action`,
  `current_phase`, `command`, `phase`, and `.codex/phase-loop` on the
  `ciflow-plan` pair. `tests/test_git_index_manager.py` and
  `tests/test_repository_commands.py` already freeze durable trace and
  interrupted status reporting for that same pair. Execution should treat
  broad new matcher work as suspect unless refreshed fixtures or the live
  rerun prove a real regression.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` already says the roadmap now adds
  downstream phase `SEMCODEXLOOPRELAPSEREBOUNDTAIL`, but there is not yet a
  dedicated `## SEMCODEXLOOPRELAPSEREBOUNDTAIL Live Rerun Check` section and
  there is no execution-ready plan artifact for this phase.
- The latest SEMCODEXLOOPHEARTBEATTAIL terminal summary reported a historical
  dirty-closeout blocker from generated `.mcp-index` outputs, but live
  `git status --short` is clean now. That stale run artifact is not a blocker
  to writing or staging this plan.

Practical planning boundary:

- SEMCODEXLOOPRELAPSEREBOUNDTAIL should be treated as a re-exposed regression
  and truth-maintenance slice for the exact
  `.codex/phase-loop/runs/20260427T081107Z-08-ciflow-plan/terminal-summary.json ->
  .codex/phase-loop/runs/20260427T081107Z-08-ciflow-plan/launch.json`
  pair after later phases moved the watchdog tail away and back again.
- Because the exact pair is already frozen in tests, execution should first
  refresh or tighten the existing fixtures and operator-surface truth for the
  later context before assuming production runtime code still needs mutation.
- Canonical `.phase-loop/` must remain authoritative throughout. This phase
  must not mutate legacy `.codex/phase-loop` files directly, must not route
  canonical `.phase-loop/state.json`, `.phase-loop/events.jsonl`, or
  `.phase-loop/tui-handoff.md` through legacy compatibility shortcuts, and
  must not reopen the cleared `artpub-plan launch.json -> heartbeat.json`
  seam without new live evidence.

## Interface Freeze Gates

- [ ] IF-0-SEMCODEXLOOPRELAPSEREBOUNDTAIL-1 - Exact relapserebound advance
      contract: a refreshed repo-local force-full rerun on the
      post-SEMCODEXLOOPHEARTBEATTAIL head no longer terminalizes with the
      durable blocker centered on
      `.codex/phase-loop/runs/20260427T081107Z-08-ciflow-plan/terminal-summary.json ->
      .codex/phase-loop/runs/20260427T081107Z-08-ciflow-plan/launch.json`;
      it either advances durably beyond that exact pair or emits a truthful
      newer blocker before the 120-second watchdog expires.
- [ ] IF-0-SEMCODEXLOOPRELAPSEREBOUNDTAIL-2 - Narrow regression contract:
      any repair chosen for the re-exposed legacy `.codex/phase-loop` relapse
      seam stays narrow, tested, and does not reopen the cleared
      `.codex/phase-loop/runs/20260427T071207Z-01-artpub-plan/launch.json ->
      .codex/phase-loop/runs/20260427T071207Z-01-artpub-plan/heartbeat.json`
      boundary without direct evidence.
- [ ] IF-0-SEMCODEXLOOPRELAPSEREBOUNDTAIL-3 - Authority-split contract:
      canonical `.phase-loop/` remains authoritative runner state, legacy
      `.codex/phase-loop/` treatment stays compatibility-only, and the phase
      does not route canonical `.phase-loop/state.json`,
      `.phase-loop/events.jsonl`, or `.phase-loop/tui-handoff.md` through the
      same legacy compatibility path.
- [ ] IF-0-SEMCODEXLOOPRELAPSEREBOUNDTAIL-4 - Bounded discoverability
      contract: the exact `ciflow-plan` `terminal-summary.json` and
      `launch.json` files remain lexically discoverable with durable file
      storage and bounded content discoverability for checked-in runtime keys
      and phrases such as `artifact_paths`, `terminal_status`, `next_action`,
      `current_phase`, `command`, `phase`, and `.codex/phase-loop`.
- [ ] IF-0-SEMCODEXLOOPRELAPSEREBOUNDTAIL-5 - Durable trace and operator
      contract: `force_full_exit_trace.json`, `GitAwareIndexManager`, and
      `uv run mcp-index repository status` stay aligned with the repaired
      relapserebound outcome and do not leave stale blame on the cleared
      `artpub-plan launch.json -> heartbeat.json` seam or on the
      `ciflow-plan` pair after lexical progress has already moved beyond it.
- [ ] IF-0-SEMCODEXLOOPRELAPSEREBOUNDTAIL-6 - Evidence and steering contract:
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMCODEXLOOPHEARTBEATTAIL rerun outcome, adds a dedicated
      `SEMCODEXLOOPRELAPSEREBOUNDTAIL` live-rerun block, and captures the
      final authoritative verdict for the re-exposed `ciflow-plan` pair; if
      execution exposes a blocker beyond the current roadmap tail,
      `specs/phase-plans-v7.md` is amended before closeout so `.phase-loop/`
      points to the newest truthful next phase.

## Lane Index & Dependencies

- SL-0 - Re-exposed `ciflow-plan` dispatcher contract refresh; Depends on: SEMCODEXLOOPHEARTBEATTAIL; Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 - Durable trace and repository-status relapserebound fixtures; Depends on: SL-0; Blocks: SL-2, SL-3, SL-4; Parallel-safe: no
- SL-2 - Minimal relapserebound runtime or truth repair; Depends on: SL-0, SL-1; Blocks: SL-3, SL-4; Parallel-safe: no
- SL-3 - Live rerun evidence reducer and docs contract refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SL-4; Parallel-safe: no
- SL-4 - Downstream roadmap steering reducer; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: SEMCODEXLOOPRELAPSEREBOUNDTAIL acceptance; Parallel-safe: no

Lane DAG:

```text
SEMCODEXLOOPHEARTBEATTAIL
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SL-4 -> SEMCODEXLOOPRELAPSEREBOUNDTAIL acceptance
```

## Lanes

### SL-0 - Re-Exposed `ciflow-plan` Dispatcher Contract Refresh

- **Scope**: Refresh the exact
  `.codex/phase-loop/runs/20260427T081107Z-08-ciflow-plan/terminal-summary.json ->
  .codex/phase-loop/runs/20260427T081107Z-08-ciflow-plan/launch.json`
  dispatcher contract so it is frozen as a later re-exposed seam after
  SEMCODEXLOOPHEARTBEATTAIL, not only as the earlier
  SEMCODEXLOOPRELAPSETAIL context.
- **Owned files**: `tests/test_dispatcher.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMCODEXLOOPRELAPSEREBOUNDTAIL-1,
  IF-0-SEMCODEXLOOPRELAPSEREBOUNDTAIL-2,
  IF-0-SEMCODEXLOOPRELAPSEREBOUNDTAIL-3, and
  IF-0-SEMCODEXLOOPRELAPSEREBOUNDTAIL-4 at the dispatcher boundary
- **Interfaces consumed**: existing
  `Dispatcher.index_directory(...)`; current bounded legacy `.codex/phase-loop`
  JSON handling; the earlier `ciflow-plan` fixture lineage from
  SEMCODEXLOOPRELAPSETAIL; and canonical `.phase-loop` non-legacy JSON/plugin
  routing
- **Parallel-safe**: no
- **Tasks**:
  - test: Refresh `tests/test_dispatcher.py` so the exact `ciflow-plan`
    `terminal-summary.json -> launch.json` pair is asserted as the later
    re-exposed seam after the `artpub-plan launch.json -> heartbeat.json`
    boundary has already been cleared.
  - test: Keep assertions that the pair still exposes checked-in runtime keys
    and phrases such as `artifact_paths`, `terminal_status`, `next_action`,
    `current_phase`, `command`, `phase`, and `.codex/phase-loop` rather than
    becoming an indexing blind spot.
  - test: Keep negative guards proving the cleared
    `artpub-plan launch.json -> heartbeat.json` seam does not remain the
    dispatcher-reported blocker and canonical `.phase-loop/state.json`
    remains on its normal non-legacy path.
  - impl: Keep fixtures deterministic with repo-local JSON strings and
    bounded-path assertions rather than live `sync --force-full` waits.
  - impl: Keep this lane on contract refresh only. Do not mutate production
    dispatcher code, durable trace logic, docs, or roadmap steering here.
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "ciflow or terminal_summary or launch or heartbeat or legacy_codex_phase_loop or bounded or phase_loop"`

### SL-1 - Durable Trace And Repository-Status Relapserebound Fixtures

- **Scope**: Refresh the operator-surface fixtures so a re-exposed
  `ciflow-plan` blocker is reported truthfully after later phases and stops
  blaming the already-cleared heartbeat seam once lexical progress has moved
  back onto the older pair.
- **Owned files**: `tests/test_git_index_manager.py`, `tests/test_repository_commands.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMCODEXLOOPRELAPSEREBOUNDTAIL-1,
  IF-0-SEMCODEXLOOPRELAPSEREBOUNDTAIL-2,
  IF-0-SEMCODEXLOOPRELAPSEREBOUNDTAIL-3, and
  IF-0-SEMCODEXLOOPRELAPSEREBOUNDTAIL-5
- **Interfaces consumed**: existing durable trace lifecycle in
  `GitAwareIndexManager`; `repository status` interrupted and stale-running
  output; the current generic legacy `.codex/phase-loop` boundary line; and
  the SEMCODEXLOOPHEARTBEATTAIL evidence lineage in
  `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- **Parallel-safe**: no
- **Tasks**:
  - test: Refresh or extend `tests/test_git_index_manager.py` so a lexical
    rerun that has already advanced beyond the `artpub-plan` heartbeat seam
    can still preserve the exact `ciflow-plan` pair when it is the truthful
    blocker, then promote a newer blocker or closeout stage once that pair is
    truly cleared.
  - test: Refresh or extend `tests/test_repository_commands.py` so
    `repository status` keeps the generic legacy boundary line and canonical
    `.phase-loop` authority wording while freezing interrupted trace output
    against the re-exposed `ciflow-plan` pair instead of the already-cleared
    heartbeat seam.
  - test: Keep negative guards that the
    `.codex/phase-loop/runs/20260427T071207Z-01-artpub-plan/launch.json ->
    .codex/phase-loop/runs/20260427T071207Z-01-artpub-plan/heartbeat.json`
    seam does not remain the reported active blocker once the relapserebound
    fixtures are introduced.
  - impl: Model closeout and successor promotion with synthetic trace payloads
    or monkeypatched manager behavior rather than live `sync --force-full`
    execution inside unit tests.
  - impl: Keep this lane fixture-only. Do not update production runtime code,
    docs, or roadmap steering here.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "ciflow or heartbeat or legacy_codex_phase_loop or interrupted or boundary or closeout_handoff or phase_loop"`

### SL-2 - Minimal Relapserebound Runtime Or Truth Repair

- **Scope**: Implement the smallest production repair needed so the
  current-head force-full rerun no longer leaves the re-exposed
  `ciflow-plan` pair as the active lexical watchdog tail, or prove with the
  tightened fixtures that no production code diff is required before the live
  rerun and evidence refresh.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `mcp_server/storage/git_index_manager.py`, `mcp_server/cli/repository_commands.py`
- **Interfaces provided**: IF-0-SEMCODEXLOOPRELAPSEREBOUNDTAIL-1 exact
  relapserebound advance contract;
  IF-0-SEMCODEXLOOPRELAPSEREBOUNDTAIL-2 narrow regression contract;
  IF-0-SEMCODEXLOOPRELAPSEREBOUNDTAIL-3 authority-split contract;
  IF-0-SEMCODEXLOOPRELAPSEREBOUNDTAIL-4 bounded discoverability contract; and
  IF-0-SEMCODEXLOOPRELAPSEREBOUNDTAIL-5 durable trace and operator contract
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
    do not regress the cleared `artpub-plan launch.json -> heartbeat.json`
    seam.
  - impl: If the repair moves the live tail beyond the `ciflow-plan` pair,
    ensure the durable trace and operator surface promote the newer blocker or
    closeout stage truthfully instead of leaving stale `last_progress_path`
    or `in_flight_path` blame on the pair.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "ciflow or heartbeat or legacy_codex_phase_loop or interrupted or boundary or closeout_handoff or phase_loop"`

### SL-3 - Live Rerun Evidence Reducer And Docs Contract Refresh

- **Scope**: Re-run the bounded repo-local force-full command after SL-2,
  capture the authoritative relapserebound outcome, and refresh the dogfood
  report plus its contract test without widening into unrelated semantic
  claims.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: IF-0-SEMCODEXLOOPRELAPSEREBOUNDTAIL-1 exact
  relapserebound advance contract;
  IF-0-SEMCODEXLOOPRELAPSEREBOUNDTAIL-5 durable trace and operator contract;
  and IF-0-SEMCODEXLOOPRELAPSEREBOUNDTAIL-6 evidence and steering contract
- **Interfaces consumed**: SL-2 runtime or truth outcome; live outputs from
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`,
  `uv run mcp-index repository status`, and
  `.mcp-index/force_full_exit_trace.json`; plus the existing
  `SEMCODEXLOOPHEARTBEATTAIL Live Rerun Check` block
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/docs/test_semdogfood_evidence_contract.py` so the
    report must include a `## SEMCODEXLOOPRELAPSEREBOUNDTAIL Live Rerun Check`
    block, cite the SEMCODEXLOOPHEARTBEATTAIL prior plan and rerun outcome,
    and record the exact `ciflow-plan` pair or its truthful successor.
  - impl: Run the refreshed repo-local force-full rerun after SL-2 using the
    same bounded command from the roadmap evidence, then capture
    `repository status`, `force_full_exit_trace.json`, and SQLite row counts
    on the same head.
  - impl: Update `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` with the final
    authoritative verdict for the re-exposed `ciflow-plan`
    `terminal-summary.json -> launch.json` pair, explicitly naming whether
    the rerun advanced beyond it, terminalized truthfully on it again, or
    exposed a later blocker.
  - impl: Keep the evidence block semantically fail-closed. Preserve
    readiness, rollout-status, last-sync-error, semantic-readiness, and the
    canonical-versus-legacy authority wording unless the live probes on the
    same head prove they changed.
  - impl: If the rerun advances beyond the pair, state clearly that the
    `artpub-plan launch.json -> heartbeat.json` seam stays closed and that the
    current blocker has moved later.
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "SEMCODEXLOOPHEARTBEATTAIL or SEMCODEXLOOPRELAPSEREBOUNDTAIL or ciflow or phase_loop"`
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
  IF-0-SEMCODEXLOOPRELAPSEREBOUNDTAIL-6
- **Interfaces consumed**: SL-3 refreshed evidence verdict; current roadmap
  DAG and tail ordering for `specs/phase-plans-v7.md`; and canonical
  `.phase-loop/` expectations that the next unplanned phase reflect the
  latest durable blocker rather than stale relapserebound assumptions
- **Parallel-safe**: no
- **Tasks**:
  - test: Re-read the post-SL-3 evidence and confirm whether the repaired
    rerun actually exposes a newer blocker beyond the current roadmap tail
    before mutating roadmap steering.
  - impl: If the active blocker remains inside the `ciflow-plan` pair or the
    rerun completes lexical closeout without exposing a new tail, leave the
    roadmap unchanged.
  - impl: If the rerun advances beyond the current roadmap tail and no
    downstream phase already covers the new blocker, append the nearest
    truthful downstream recovery phase to `specs/phase-plans-v7.md` with the
    same evidence-first structure used by the current SEM* lexical-recovery
    chain.
  - impl: Keep any roadmap mutation limited to the newly exposed blocker. Do
    not rewrite earlier phases or reopen SEMCODEXLOOPHEARTBEATTAIL
    assumptions while closing this re-exposed seam.
  - verify: `git diff -- specs/phase-plans-v7.md`

## Verification

Planning-only run: do not execute these during plan creation. Run them during
`codex-execute-phase` or manual SEMCODEXLOOPRELAPSEREBOUNDTAIL execution.

Lane-specific checks:

```bash
uv run pytest tests/test_dispatcher.py -q --no-cov -k "ciflow or terminal_summary or launch or heartbeat or legacy_codex_phase_loop or bounded or phase_loop"
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "ciflow or heartbeat or legacy_codex_phase_loop or interrupted or boundary or closeout_handoff or phase_loop"
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "ciflow or heartbeat or legacy_codex_phase_loop or interrupted or boundary or closeout_handoff or phase_loop"
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "SEMCODEXLOOPHEARTBEATTAIL or SEMCODEXLOOPRELAPSEREBOUNDTAIL or ciflow or phase_loop"
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
  -q --no-cov -k "ciflow or heartbeat or legacy_codex_phase_loop or interrupted or boundary or closeout_handoff or phase_loop"
timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
sed -n '1,240p' .mcp-index/force_full_exit_trace.json
git status --short -- plans/phase-plan-v7-SEMCODEXLOOPRELAPSEREBOUNDTAIL.md docs/status/SEMANTIC_DOGFOOD_REBUILD.md specs/phase-plans-v7.md
git diff --check
git diff --cached --check
```

## Acceptance Criteria

- [ ] A refreshed repo-local force-full rerun on the
      post-SEMCODEXLOOPHEARTBEATTAIL head either advances durably beyond the
      re-exposed
      `.codex/phase-loop/runs/20260427T081107Z-08-ciflow-plan/terminal-summary.json ->
      .codex/phase-loop/runs/20260427T081107Z-08-ciflow-plan/launch.json`
      pair or emits a truthful newer blocker before the 120-second watchdog
      expires.
- [ ] Any repair chosen for the re-exposed legacy `.codex/phase-loop` relapse
      seam stays narrow, tested, keeps canonical `.phase-loop/`
      authoritative, and does not reopen the cleared
      `.codex/phase-loop/runs/20260427T071207Z-01-artpub-plan/launch.json ->
      .codex/phase-loop/runs/20260427T071207Z-01-artpub-plan/heartbeat.json`
      boundary without direct evidence.
- [ ] The exact `ciflow-plan` `terminal-summary.json` and `launch.json` files
      remain lexically discoverable with durable file storage and bounded
      content discoverability for checked-in runtime keys and phrases such as
      `artifact_paths`, `terminal_status`, `next_action`, `current_phase`,
      `command`, `phase`, and `.codex/phase-loop`.
- [ ] `force_full_exit_trace.json` and
      `uv run mcp-index repository status` stay aligned with the repaired
      relapserebound outcome and do not leave stale blame on the cleared
      heartbeat seam or on the `ciflow-plan` pair after progress has already
      moved beyond them.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMCODEXLOOPHEARTBEATTAIL rerun outcome and the final live verdict for
      the re-exposed `ciflow-plan` pair.
- [ ] If execution reveals a newer blocker beyond the current roadmap tail,
      `specs/phase-plans-v7.md` is updated before closeout so the next
      phase-loop step stays truthful.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMCODEXLOOPRELAPSEREBOUNDTAIL.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMCODEXLOOPRELAPSEREBOUNDTAIL.md
  artifact_state: staged
```
