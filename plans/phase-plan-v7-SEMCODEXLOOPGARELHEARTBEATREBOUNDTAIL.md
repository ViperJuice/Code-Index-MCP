---
phase_loop_plan_version: 1
phase: SEMCODEXLOOPGARELHEARTBEATREBOUNDTAIL
roadmap: specs/phase-plans-v7.md
roadmap_sha256: c84ac34841a1b60ba86f8e6ceb58780a89298f1b3a14f31fa48366827cef8d8a
---
# SEMCODEXLOOPGARELHEARTBEATREBOUNDTAIL: Legacy Codex Phase-Loop GAREL Heartbeat Rebound Tail Recovery

## Context

SEMCODEXLOOPGARELHEARTBEATREBOUNDTAIL is the phase-90 follow-up for the v7
semantic hardening roadmap. Canonical `.phase-loop/` runtime exists in this
checkout, so it is the authoritative runner state for this planning run. The
canonical snapshots are aligned for this phase: `.phase-loop/state.json` and
`.phase-loop/tui-handoff.md` both identify
`SEMCODEXLOOPGARELHEARTBEATREBOUNDTAIL` as the current `unplanned` phase for
`specs/phase-plans-v7.md`, and the recorded roadmap hash matches the
user-required
`c84ac34841a1b60ba86f8e6ceb58780a89298f1b3a14f31fa48366827cef8d8a`.
Legacy `.codex/phase-loop/` artifacts remain compatibility-only and must not
supersede canonical `.phase-loop/` state.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is the active roadmap, it is tracked and clean in
  this worktree, and `sha256sum specs/phase-plans-v7.md` matches the
  user-required
  `c84ac34841a1b60ba86f8e6ceb58780a89298f1b3a14f31fa48366827cef8d8a`.
- The checkout is on `main...origin/main [ahead 175]` at `HEAD`
  `fb7375930054a5af813748a536d4690e0e06c053`, the worktree is clean before
  this artifact write, and
  `plans/phase-plan-v7-SEMCODEXLOOPGARELHEARTBEATREBOUNDTAIL.md` did not
  exist before this run.
- The latest canonical handoff names this phase as the next required step
  after `SEMCODEXLOOPCIFLOWEXECRELAPSETAIL`, and its recorded live evidence
  matches the phase-90 objective: the refreshed repo-local force-full rerun
  advanced beyond the earlier
  `.codex/phase-loop/runs/20260427T081704Z-09-ciflow-execute/terminal-summary.json ->
  .codex/phase-loop/runs/20260427T081704Z-09-ciflow-execute/launch.json`
  pair and later terminalized on the newer exact legacy compatibility-runtime
  seam
  `.codex/phase-loop/runs/20260424T225641Z-01-garel-execute/heartbeat.json ->
  .codex/phase-loop/runs/20260425T022006Z-01-garecut-plan/launch.json`.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` already contains a dedicated
  `## SEMCODEXLOOPCIFLOWEXECRELAPSETAIL Live Rerun Check` block that records
  the current blocker handoff for this phase, including the authoritative
  `2026-04-30T04:21:53Z` raw force-full trace snapshot and the
  `2026-04-30T04:22:02Z` `repository status` verdict preserving the same
  `garel-execute heartbeat.json -> garecut-plan launch.json` pair.
- Existing coverage is asymmetrical for this exact pair. Repo search during
  planning showed the current pair already frozen in
  `tests/test_git_index_manager.py` and in
  `tests/docs/test_semdogfood_evidence_contract.py`, but not yet in
  `tests/test_dispatcher.py` or `tests/test_repository_commands.py`.
- `tests/test_dispatcher.py` already freezes nearby exact-bounded legacy
  `.codex/phase-loop` seams for `artpub-plan`, `ciflow-plan`,
  `garecut-execute`, `garc-plan -> idxsafe-repair`, and
  `ciflow-execute terminal-summary.json -> launch.json`. This phase should
  extend that deterministic lexical coverage to the exact later
  `garel-execute heartbeat.json -> garecut-plan launch.json` pair instead of
  widening the matcher family.
- `tests/test_git_index_manager.py` already proves that durable
  `force_full_exit_trace.json` state can move past the cleared
  `ciflow-execute terminal-summary.json -> launch.json` seam and preserve the
  exact newer `garel-execute heartbeat.json -> garecut-plan launch.json`
  blocker. Execution should build on that coverage rather than re-solving the
  earlier pair.
- `tests/docs/test_semdogfood_evidence_contract.py` already names the exact
  current blocker pair and the downstream phase alias
  `SEMCODEXLOOPGARELHEARTBEATREBOUNDTAIL`, so execution should update the
  checked-in dogfood report and its contract test together instead of
  inventing a new status surface.
- `mcp_server/cli/repository_commands.py` already prints the generic
  compatibility boundary
  `Lexical boundary: using exact bounded JSON/JSONL indexing for legacy .codex/phase-loop compatibility runtime artifacts while canonical .phase-loop remains authoritative`.
  This phase should preserve that authority split while making the exact
  `garel-execute` and `garecut-plan` pair truthful at the dispatcher,
  durable trace, and operator-status surfaces.
- The latest canonical terminal summary from the prior execute run records a
  blocked dirty closeout caused by regenerated `.index_metadata.json` and
  `.mcp-index/` artifacts, even though the current git worktree is clean after
  supervisor repair. Execution for this phase should treat those runtime-only
  artifacts as rerun preflight/cleanup noise, not as product files or roadmap
  scope.

Practical planning boundary:

- SEMCODEXLOOPGARELHEARTBEATREBOUNDTAIL should be treated as the next narrow
  legacy compatibility-runtime slice for the exact
  `.codex/phase-loop/runs/20260424T225641Z-01-garel-execute/heartbeat.json ->
  .codex/phase-loop/runs/20260425T022006Z-01-garecut-plan/launch.json`
  seam after the newer `ciflow-execute terminal-summary.json -> launch.json`
  blocker was already cleared.
- Canonical `.phase-loop/` must remain authoritative throughout. This phase
  must not mutate legacy `.codex/phase-loop` files directly, must not route
  canonical `.phase-loop/state.json`, `.phase-loop/events.jsonl`, or
  `.phase-loop/tui-handoff.md` through legacy compatibility shortcuts, and
  must not reopen the cleared
  `.codex/phase-loop/runs/20260427T081704Z-09-ciflow-execute/terminal-summary.json ->
  .codex/phase-loop/runs/20260427T081704Z-09-ciflow-execute/launch.json`
  seam without direct evidence.
- Because the generic legacy matcher already covers bounded legacy launch,
  heartbeat, and terminal-summary JSON files, execution should first freeze
  the exact pair at dispatcher and status surfaces before assuming the
  production runtime still needs a broader path-matching or plugin change.
- If rerun preflight regenerates runtime-only `.index_metadata.json` or
  `.mcp-index/` artifacts, execution should clear or restore them before
  closeout and keep them out of the tracked change set unless a code/test/doc
  fix proves they must be mentioned as evidence.

## Interface Freeze Gates

- [ ] IF-0-SEMCODEXLOOPGARELHEARTBEATREBOUNDTAIL-1 - Exact `garel-execute`
      rebound advance contract: a refreshed repo-local force-full rerun on
      the post-SEMCODEXLOOPCIFLOWEXECRELAPSETAIL head no longer terminalizes
      with the durable blocker centered on
      `.codex/phase-loop/runs/20260424T225641Z-01-garel-execute/heartbeat.json ->
      .codex/phase-loop/runs/20260425T022006Z-01-garecut-plan/launch.json`;
      it either advances durably beyond that exact pair or emits a truthful
      newer blocker before the 120-second watchdog expires.
- [ ] IF-0-SEMCODEXLOOPGARELHEARTBEATREBOUNDTAIL-2 - Narrow repair contract:
      any repair chosen for this later legacy `.codex/phase-loop`
      compatibility-runtime seam stays narrow, tested, and does not reopen
      the cleared
      `.codex/phase-loop/runs/20260427T081704Z-09-ciflow-execute/terminal-summary.json ->
      .codex/phase-loop/runs/20260427T081704Z-09-ciflow-execute/launch.json`
      seam or broaden into blanket `.codex/**` or `.phase-loop/**` bypasses
      without direct evidence.
- [ ] IF-0-SEMCODEXLOOPGARELHEARTBEATREBOUNDTAIL-3 - Authority-split
      contract: canonical `.phase-loop/` remains authoritative runner state,
      legacy `.codex/phase-loop/` treatment stays compatibility-only, and the
      phase does not route canonical `.phase-loop/state.json`,
      `.phase-loop/events.jsonl`, or `.phase-loop/tui-handoff.md` through the
      same legacy compatibility path.
- [ ] IF-0-SEMCODEXLOOPGARELHEARTBEATREBOUNDTAIL-4 - Bounded discoverability
      contract: the exact `garel-execute heartbeat.json` and
      `garecut-plan launch.json` files remain lexically discoverable with
      durable file storage and bounded content discoverability for checked-in
      runtime keys and phrases such as `command`, `phase`, `current_phase`,
      `status`, `trace`, `heartbeat`, and `.codex/phase-loop`.
- [ ] IF-0-SEMCODEXLOOPGARELHEARTBEATREBOUNDTAIL-5 - Durable trace and
      operator contract: `.mcp-index/force_full_exit_trace.json`,
      `GitAwareIndexManager`, and `uv run mcp-index repository status` stay
      aligned with the repaired `garel-execute heartbeat.json ->
      garecut-plan launch.json` outcome and do not leave stale blame on the
      cleared `ciflow-execute terminal-summary.json -> launch.json` seam or
      on the exact current pair after progress has already moved later.
- [ ] IF-0-SEMCODEXLOOPGARELHEARTBEATREBOUNDTAIL-6 - Evidence and steering
      contract: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMCODEXLOOPCIFLOWEXECRELAPSETAIL rerun outcome, adds a dedicated
      `SEMCODEXLOOPGARELHEARTBEATREBOUNDTAIL` live-rerun block, and captures
      the final authoritative verdict for the exact
      `garel-execute heartbeat.json -> garecut-plan launch.json` pair; if
      execution exposes a blocker beyond the current roadmap tail,
      `specs/phase-plans-v7.md` is amended before closeout so `.phase-loop/`
      points to the newest truthful next phase.

## Lane Index & Dependencies

- SL-0 - Exact `garel-execute` / `garecut-plan` dispatcher contract freeze; Depends on: SEMCODEXLOOPCIFLOWEXECRELAPSETAIL; Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 - Durable trace and repository-status `garel` / `garecut` fixtures; Depends on: SL-0; Blocks: SL-2, SL-3, SL-4; Parallel-safe: no
- SL-2 - Minimal `garel` rebound runtime or truth repair; Depends on: SL-0, SL-1; Blocks: SL-3, SL-4; Parallel-safe: no
- SL-3 - Live rerun evidence reducer and docs contract refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SL-4; Parallel-safe: no
- SL-4 - Downstream roadmap steering reducer; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: SEMCODEXLOOPGARELHEARTBEATREBOUNDTAIL acceptance; Parallel-safe: no

Lane DAG:

```text
SEMCODEXLOOPCIFLOWEXECRELAPSETAIL
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SL-4 -> SEMCODEXLOOPGARELHEARTBEATREBOUNDTAIL acceptance
```

## Lanes

### SL-0 - Exact `garel-execute` / `garecut-plan` Dispatcher Contract Freeze

- **Scope**: Freeze deterministic dispatcher coverage for the exact
  `.codex/phase-loop/runs/20260424T225641Z-01-garel-execute/heartbeat.json ->
  .codex/phase-loop/runs/20260425T022006Z-01-garecut-plan/launch.json`
  pair so execution proves a narrow bounded repair instead of assuming the
  nearby `garecut-execute`, `garc-plan -> idxsafe-repair`, or
  `ciflow-execute` fixtures already make the later pair safe.
- **Owned files**: `tests/test_dispatcher.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMCODEXLOOPGARELHEARTBEATREBOUNDTAIL-1,
  IF-0-SEMCODEXLOOPGARELHEARTBEATREBOUNDTAIL-2,
  IF-0-SEMCODEXLOOPGARELHEARTBEATREBOUNDTAIL-3, and
  IF-0-SEMCODEXLOOPGARELHEARTBEATREBOUNDTAIL-4 at the dispatcher boundary
- **Interfaces consumed**: existing `Dispatcher.index_directory(...)`;
  current exact-bounded legacy `.codex/phase-loop` JSON handling; the nearby
  `garecut-execute`, `garc-plan -> idxsafe-repair`, and `ciflow-execute`
  fixture lineage in `tests/test_dispatcher.py`; and canonical `.phase-loop`
  non-legacy JSON routing
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` with repo-shaped fixtures for the
    exact `garel-execute heartbeat.json -> garecut-plan launch.json` pair so
    the dispatcher contract proves durable file rows, zero code chunks, and
    FTS-backed discoverability for both files.
  - test: Assert that the pair still exposes checked-in runtime keys and
    phrases such as `command`, `phase`, `current_phase`, `status`, `trace`,
    `heartbeat`, and `.codex/phase-loop` rather than becoming an indexing
    blind spot.
  - test: Keep negative guards proving the cleared
    `ciflow-execute terminal-summary.json -> launch.json` seam still passes
    unchanged and canonical `.phase-loop/state.json`,
    `.phase-loop/events.jsonl`, and `.phase-loop/tui-handoff.md` remain on
    their normal non-legacy JSON or JSONL paths.
  - impl: Keep fixtures deterministic with repo-local JSON strings and
    bounded-path assertions rather than live `sync --force-full` waits.
  - impl: Keep this lane on contract freeze only. Do not mutate dispatcher
    implementation, durable trace logic, CLI wording, docs, or roadmap
    steering here.
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "garel or garecut or heartbeat or launch or legacy_codex_phase_loop or bounded or phase_loop"`

### SL-1 - Durable Trace And Repository-Status `garel` / `garecut` Fixtures

- **Scope**: Freeze the exact
  `garel-execute heartbeat.json -> garecut-plan launch.json` pair at the
  durable trace and operator surface so execution can distinguish a real
  runtime repair from a report that still blames the already-cleared
  `ciflow-execute terminal-summary.json -> launch.json` seam or this exact
  pair after progress has already moved later.
- **Owned files**: `tests/test_git_index_manager.py`, `tests/test_repository_commands.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMCODEXLOOPGARELHEARTBEATREBOUNDTAIL-1,
  IF-0-SEMCODEXLOOPGARELHEARTBEATREBOUNDTAIL-2,
  IF-0-SEMCODEXLOOPGARELHEARTBEATREBOUNDTAIL-3, and
  IF-0-SEMCODEXLOOPGARELHEARTBEATREBOUNDTAIL-5
- **Interfaces consumed**: existing durable trace lifecycle in
  `GitAwareIndexManager`; the current
  `test_force_full_sync_durable_trace_moves_past_legacy_codex_phase_loop_ciflow_execute_relapse_pair`
  coverage; `repository status` interrupted and stale-running output; the
  generic legacy `.codex/phase-loop` boundary line in
  `mcp_server/cli/repository_commands.py`; and the
  SEMCODEXLOOPCIFLOWEXECRELAPSETAIL evidence lineage in
  `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- **Parallel-safe**: no
- **Tasks**:
  - test: Tighten `tests/test_git_index_manager.py` so the durable trace can
    preserve the exact
    `garel-execute heartbeat.json -> garecut-plan launch.json` pair while it
    is the truthful blocker, then promote a later blocker or closeout state
    once that pair has truly been cleared.
  - test: Extend `tests/test_repository_commands.py` so `repository status`
    reports the interrupted trace against the exact `garel-execute` /
    `garecut-plan` pair while preserving the generic legacy `.codex/phase-loop`
    boundary line and the canonical `.phase-loop` authority wording.
  - test: Keep negative guards proving the cleared
    `.codex/phase-loop/runs/20260427T081704Z-09-ciflow-execute/terminal-summary.json ->
    .codex/phase-loop/runs/20260427T081704Z-09-ciflow-execute/launch.json`
    pair no longer appears as the final blocker once the durable trace has
    moved later.
  - impl: Keep fixtures deterministic and repo-local. Do not depend on a live
    semantic index or external services for these operator-surface checks.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "garel or garecut or heartbeat or launch or legacy_codex_phase_loop or interrupted or boundary or closeout_handoff or phase_loop"`

### SL-2 - Minimal `garel` Rebound Runtime Or Truth Repair

- **Scope**: Repair only the concrete runtime or truth surface that still
  misclassifies the exact
  `garel-execute heartbeat.json -> garecut-plan launch.json` pair after SL-0
  and SL-1 freeze the failing contract, while preserving canonical
  `.phase-loop/` authority and the existing exact-bounded legacy matcher
  boundary.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `mcp_server/storage/git_index_manager.py`, `mcp_server/cli/repository_commands.py`
- **Interfaces provided**: production behavior for
  IF-0-SEMCODEXLOOPGARELHEARTBEATREBOUNDTAIL-1,
  IF-0-SEMCODEXLOOPGARELHEARTBEATREBOUNDTAIL-2,
  IF-0-SEMCODEXLOOPGARELHEARTBEATREBOUNDTAIL-3,
  IF-0-SEMCODEXLOOPGARELHEARTBEATREBOUNDTAIL-4, and
  IF-0-SEMCODEXLOOPGARELHEARTBEATREBOUNDTAIL-5
- **Interfaces consumed**: SL-0 exact-pair dispatcher fixtures; SL-1 durable
  trace and repository-status fixtures; existing bounded legacy `.codex/phase-loop`
  JSON or JSONL boundary behavior; `.mcp-index/force_full_exit_trace.json`
  last-progress / in-flight reporting; and `repository status` rollout and
  lexical-boundary output
- **Parallel-safe**: no
- **Tasks**:
  - impl: Fix only the boundary that still fails after the frozen tests are in
    place: exact-bounded dispatcher ingestion, durable trace last-progress /
    in-flight promotion, or `repository status` rendering of the mixed
    heartbeat / launch pair.
  - impl: Preserve the generic operator line
    `Lexical boundary: using exact bounded JSON/JSONL indexing for legacy .codex/phase-loop compatibility runtime artifacts while canonical .phase-loop remains authoritative`
    unless the frozen tests prove that wording is false.
  - impl: Do not broaden into blanket `.codex/**` matching, canonical
    `.phase-loop/**` bypasses, earlier blocker re-triage, or unrelated
    semantic, integration, or security work.
  - impl: If rerun preflight regenerates runtime-only `.index_metadata.json`
    or `.mcp-index/` artifacts, clear or restore them before the live rerun
    and keep them out of the tracked change set unless a checked-in evidence
    file explicitly needs to mention them.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "garel or garecut or heartbeat or launch or legacy_codex_phase_loop or interrupted or boundary or closeout_handoff or phase_loop"`

### SL-3 - Live Rerun Evidence Reducer And Docs Contract Refresh

- **Scope**: Refresh the checked-in dogfood rebuild report and its contract
  tests so the repo records the final authoritative live verdict for the exact
  `garel-execute heartbeat.json -> garecut-plan launch.json` pair and whether
  the rerun moved later again.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: IF-0-SEMCODEXLOOPGARELHEARTBEATREBOUNDTAIL-6
- **Interfaces consumed**: SL-0 dispatcher contract; SL-1 durable trace and
  status contract; SL-2 repaired live rerun behavior; existing
  SEMCODEXLOOPCIFLOWEXECRELAPSETAIL evidence block; and the canonical
  `.phase-loop/` handoff that already names this phase as current
- **Parallel-safe**: no
- **Tasks**:
  - impl: Update `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` with a dedicated
    `## SEMCODEXLOOPGARELHEARTBEATREBOUNDTAIL Live Rerun Check` block that
    records the bounded rerun command, authoritative timestamps, exact
    `last_progress_path` / `in_flight_path` values, SQLite count snapshots,
    whether the rerun cleared the `garel-execute` / `garecut-plan` pair or
    exposed a newer blocker, and the final steering verdict.
  - impl: Refresh `tests/docs/test_semdogfood_evidence_contract.py` so it
    requires the new phase plan path, the prior phase lineage, the exact
    `garel-execute heartbeat.json -> garecut-plan launch.json` pair, and the
    new evidence block heading.
  - impl: If the live rerun proves the target pair is no longer active, the
    report must name the newer blocker exactly and state that older
    `SEMCODEXLOOPCIFLOWEXECRELAPSETAIL` assumptions are stale.
  - impl: Record any rerun preflight cleanup of generated `.mcp-index/` or
    `.index_metadata.json` artifacts only as closeout-safe evidence context;
    do not let those runtime leftovers become tracked outputs of the phase.
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "SEMCODEXLOOPCIFLOWEXECRELAPSETAIL or SEMCODEXLOOPGARELHEARTBEATREBOUNDTAIL or garel or garecut or phase_loop"`

### SL-4 - Downstream Roadmap Steering Reducer

- **Scope**: Keep the v7 roadmap and phase-loop next step truthful after the
  live rerun by either confirming this phase as the new terminal blocker or
  adding the nearest downstream phase if the rerun moves later again.
- **Owned files**: `specs/phase-plans-v7.md`
- **Interfaces provided**: IF-0-SEMCODEXLOOPGARELHEARTBEATREBOUNDTAIL-6
- **Interfaces consumed**: SL-0 exact-pair dispatcher contract; SL-1 durable
  trace/status contract; SL-2 live rerun verdict; and SL-3 checked-in
  evidence conclusions
- **Parallel-safe**: no
- **Tasks**:
  - impl: Leave `specs/phase-plans-v7.md` unchanged if execution clears the
    exact `garel-execute heartbeat.json -> garecut-plan launch.json` pair and
    does not expose a newer blocker beyond the current roadmap tail.
  - impl: If the rerun advances later to a new exact lexical seam, amend
    `specs/phase-plans-v7.md` before closeout with one downstream phase whose
    objective, exit criteria, key files, and dependency point to the newest
    truthful blocker.
  - impl: Do not rewrite older completed phases or treat any prior downstream
    phase plan as authoritative after a roadmap amendment.
  - verify: `git diff -- specs/phase-plans-v7.md`
  - verify: `git status --short -- specs/phase-plans-v7.md docs/status/SEMANTIC_DOGFOOD_REBUILD.md tests/docs/test_semdogfood_evidence_contract.py`

## Verification

Lane verification commands:

```bash
uv run pytest tests/test_dispatcher.py -q --no-cov -k "garel or garecut or heartbeat or launch or legacy_codex_phase_loop or bounded or phase_loop"
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "garel or garecut or heartbeat or launch or legacy_codex_phase_loop or interrupted or boundary or closeout_handoff or phase_loop"
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "garel or garecut or heartbeat or launch or legacy_codex_phase_loop or interrupted or boundary or closeout_handoff or phase_loop"
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "SEMCODEXLOOPCIFLOWEXECRELAPSETAIL or SEMCODEXLOOPGARELHEARTBEATREBOUNDTAIL or garel or garecut or phase_loop"
timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
sed -n '1,240p' .mcp-index/force_full_exit_trace.json
sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'
git status --short -- .index_metadata.json .mcp-index
```

Whole-phase regression commands:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest \
  tests/test_dispatcher.py \
  tests/test_git_index_manager.py \
  tests/test_repository_commands.py \
  tests/docs/test_semdogfood_evidence_contract.py \
  -q --no-cov -k "garel or garecut or heartbeat or launch or legacy_codex_phase_loop or interrupted or boundary or closeout_handoff or phase_loop"
timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
sed -n '1,240p' .mcp-index/force_full_exit_trace.json
git status --short -- plans/phase-plan-v7-SEMCODEXLOOPGARELHEARTBEATREBOUNDTAIL.md docs/status/SEMANTIC_DOGFOOD_REBUILD.md specs/phase-plans-v7.md
git diff --check
git diff --cached --check
```

## Acceptance Criteria

- [ ] A refreshed repo-local force-full rerun on the
      post-SEMCODEXLOOPCIFLOWEXECRELAPSETAIL head either advances durably
      beyond the newer legacy
      `.codex/phase-loop/runs/20260424T225641Z-01-garel-execute/heartbeat.json ->
      .codex/phase-loop/runs/20260425T022006Z-01-garecut-plan/launch.json`
      pair or emits a truthful newer blocker before the 120-second watchdog
      expires.
- [ ] Any repair chosen for the later legacy `.codex/phase-loop`
      compatibility-runtime seam stays narrow, tested, and does not reopen
      the cleared
      `.codex/phase-loop/runs/20260427T081704Z-09-ciflow-execute/terminal-summary.json ->
      .codex/phase-loop/runs/20260427T081704Z-09-ciflow-execute/launch.json`
      boundary without direct evidence.
- [ ] Canonical `.phase-loop/` remains authoritative runner state, and the
      repair does not route canonical `.phase-loop/state.json`,
      `.phase-loop/events.jsonl`, or `.phase-loop/tui-handoff.md` through the
      same legacy compatibility path.
- [ ] The exact `garel-execute heartbeat.json -> garecut-plan launch.json`
      pair remains lexically discoverable with durable file storage and
      bounded content discoverability for checked-in runtime keys and phrases
      such as `command`, `phase`, `current_phase`, `status`, `trace`,
      `heartbeat`, and `.codex/phase-loop`.
- [ ] `.mcp-index/force_full_exit_trace.json` and
      `uv run mcp-index repository status` stay aligned with the repaired
      rebound outcome and do not leave stale blame on the cleared
      `ciflow-execute terminal-summary.json -> launch.json` seam or on the
      exact `garel-execute heartbeat.json -> garecut-plan launch.json` pair
      after progress has already moved beyond them.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMCODEXLOOPCIFLOWEXECRELAPSETAIL rerun outcome and the final live
      verdict for the exact
      `garel-execute heartbeat.json -> garecut-plan launch.json` pair.
- [ ] If execution reveals a newer blocker beyond the current roadmap tail,
      `specs/phase-plans-v7.md` is updated before closeout so the next
      phase-loop step stays truthful.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMCODEXLOOPGARELHEARTBEATREBOUNDTAIL.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMCODEXLOOPGARELHEARTBEATREBOUNDTAIL.md
  artifact_state: staged
```
