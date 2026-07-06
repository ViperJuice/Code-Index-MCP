---
phase_loop_plan_version: 1
phase: SEMCODEXLOOPCIFLOWEXECRELAPSETAIL
roadmap: specs/phase-plans-v7.md
roadmap_sha256: d821e9b17c8653d9e53397c8445e0360d736161dccd8c5fec95ef1d03dc0fc48
---
# SEMCODEXLOOPCIFLOWEXECRELAPSETAIL: Legacy Codex Phase-Loop CIFLOW Execute Relapse Tail Recovery

## Context

SEMCODEXLOOPCIFLOWEXECRELAPSETAIL is the phase-89 follow-up for the v7
semantic hardening roadmap. Canonical `.phase-loop/` runtime exists in this
checkout, so it is the authoritative runner state for this planning run. The
canonical snapshots are aligned for this phase: `.phase-loop/state.json` and
`.phase-loop/tui-handoff.md` both identify
`SEMCODEXLOOPCIFLOWEXECRELAPSETAIL` as the current `unplanned` phase for
`specs/phase-plans-v7.md`, and the recorded roadmap hash matches the
user-required
`d821e9b17c8653d9e53397c8445e0360d736161dccd8c5fec95ef1d03dc0fc48`.
Legacy `.codex/phase-loop/` artifacts remain compatibility-only and must not
supersede canonical `.phase-loop/` state.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is the active roadmap, it is tracked and clean in
  this worktree, and `sha256sum specs/phase-plans-v7.md` matches the
  user-required
  `d821e9b17c8653d9e53397c8445e0360d736161dccd8c5fec95ef1d03dc0fc48`.
- The checkout is on `main...origin/main [ahead 173]` at `HEAD`
  `f7ac089175580187fe79f5c36584ce4beb377213`, the worktree is clean before
  this artifact write, and
  `plans/phase-plan-v7-SEMCODEXLOOPCIFLOWEXECRELAPSETAIL.md` did not exist
  before this run.
- The latest canonical handoff names this phase as the next required step
  after `SEMCODEXLOOPREBOUNDRELAPSETAIL`, and its recorded evidence matches
  the phase-89 objective: the refreshed repo-local force-full rerun advanced
  beyond the re-exposed earlier legacy rebound seam
  `.codex/phase-loop/runs/20260424T190651Z-01-garc-plan/launch.json ->
  .codex/phase-loop/runs/20260427T075236Z-05-idxsafe-repair/terminal-summary.json`
  and later terminalized on the newer legacy execute relapse seam
  `.codex/phase-loop/runs/20260427T081704Z-09-ciflow-execute/terminal-summary.json ->
  .codex/phase-loop/runs/20260427T081704Z-09-ciflow-execute/launch.json`.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` already contains a dedicated
  `## SEMCODEXLOOPREBOUNDRELAPSETAIL Live Rerun Check` block that records the
  current blocker handoff for this phase. That block freezes the authoritative
  timestamps for the execute-relapse pair:
  `2026-04-30T04:04:54Z` for the raw running
  `.mcp-index/force_full_exit_trace.json` snapshot and
  `2026-04-30T04:05:03Z` for the `repository status` verdict that preserved
  the same `ciflow-execute terminal-summary.json -> launch.json` pair.
- Existing coverage already freezes nearby legacy compatibility-runtime
  behavior, but repo search during planning did not show the exact
  `ciflow-execute terminal-summary.json -> launch.json` pair in
  `tests/test_dispatcher.py`, `tests/test_git_index_manager.py`, or
  `tests/test_repository_commands.py`. Those files currently freeze the
  earlier `ciflow-plan`, `artpub-plan`, `garecut-execute`, and
  `garc-plan -> idxsafe-repair` seams instead.
- `tests/docs/test_semdogfood_evidence_contract.py` and
  `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` already mention the exact later
  execute-relapse pair, the downstream roadmap addition
  `SEMCODEXLOOPCIFLOWEXECRELAPSETAIL`, and the prior
  `SEMCODEXLOOPREBOUNDRELAPSETAIL` evidence lineage, so execution should keep
  the checked-in dogfood report and contract test as the evidence authority
  rather than inventing a new status surface.
- `mcp_server/plugins/generic_treesitter_plugin.py` already owns the narrow
  exact-bounded legacy `.codex/phase-loop` JSON family for checked-in
  `launch.json`, `heartbeat.json`, and `terminal-summary.json` files. This
  phase should preserve that bounded family and treat the remaining gap as a
  dispatcher truth, durable trace promotion, repository-status reporting, or
  evidence closeout problem unless the refreshed rerun proves otherwise.
- `mcp_server/cli/repository_commands.py` already prints the generic
  authority-split line
  `Lexical boundary: using exact bounded JSON/JSONL indexing for legacy .codex/phase-loop compatibility runtime artifacts while canonical .phase-loop remains authoritative`.
  This phase should preserve that canonical/legacy split while making the
  exact `ciflow-execute` pair truthful at the dispatcher, durable trace, and
  operator-status surfaces.

Practical planning boundary:

- SEMCODEXLOOPCIFLOWEXECRELAPSETAIL should be treated as the next narrow
  legacy compatibility-runtime slice for the exact
  `.codex/phase-loop/runs/20260427T081704Z-09-ciflow-execute/terminal-summary.json ->
  .codex/phase-loop/runs/20260427T081704Z-09-ciflow-execute/launch.json`
  seam after the earlier
  `garc-plan launch.json -> idxsafe-repair terminal-summary.json`
  blocker was already cleared.
- Canonical `.phase-loop/` must remain authoritative throughout. This phase
  must not mutate legacy `.codex/phase-loop` files directly, must not route
  canonical `.phase-loop/state.json`, `.phase-loop/events.jsonl`, or
  `.phase-loop/tui-handoff.md` through legacy compatibility shortcuts, and
  must not reopen the cleared
  `.codex/phase-loop/runs/20260424T190651Z-01-garc-plan/launch.json ->
  .codex/phase-loop/runs/20260427T075236Z-05-idxsafe-repair/terminal-summary.json`
  seam without direct evidence.
- Because the generic legacy matcher already covers bounded
  `.codex/phase-loop` `launch.json` and `terminal-summary.json` files,
  execution should first refresh exact-pair fixtures and precedence guards
  before assuming the production runtime still needs a broader matcher change.
- Broad `.codex/**` matching, canonical `.phase-loop/**` bypasses, reopening
  earlier script-family or security seams, or widening into unrelated
  semantic, integration, release, or runner-state mutation work are out of
  scope unless the refreshed rerun proves the active blocker has moved again.

## Interface Freeze Gates

- [ ] IF-0-SEMCODEXLOOPCIFLOWEXECRELAPSETAIL-1 - Exact ciflow-execute relapse
      advance contract: a refreshed repo-local force-full rerun on the
      post-SEMCODEXLOOPREBOUNDRELAPSETAIL head no longer terminalizes with the
      durable blocker centered on
      `.codex/phase-loop/runs/20260427T081704Z-09-ciflow-execute/terminal-summary.json ->
      .codex/phase-loop/runs/20260427T081704Z-09-ciflow-execute/launch.json`;
      it either advances durably beyond that exact pair or emits a truthful
      newer blocker before the 120-second watchdog expires.
- [ ] IF-0-SEMCODEXLOOPCIFLOWEXECRELAPSETAIL-2 - Narrow repair contract: any
      repair chosen for this later legacy `.codex/phase-loop` execute relapse
      seam stays narrow, tested, and does not reopen the cleared
      `.codex/phase-loop/runs/20260424T190651Z-01-garc-plan/launch.json ->
      .codex/phase-loop/runs/20260427T075236Z-05-idxsafe-repair/terminal-summary.json`
      seam or broaden into blanket `.codex/**` or `.phase-loop/**` bypasses
      without direct evidence.
- [ ] IF-0-SEMCODEXLOOPCIFLOWEXECRELAPSETAIL-3 - Authority-split contract:
      canonical `.phase-loop/` remains authoritative runner state, legacy
      `.codex/phase-loop/` treatment stays compatibility-only, and the phase
      does not route canonical `.phase-loop/state.json`,
      `.phase-loop/events.jsonl`, or `.phase-loop/tui-handoff.md` through the
      same legacy compatibility path.
- [ ] IF-0-SEMCODEXLOOPCIFLOWEXECRELAPSETAIL-4 - Bounded discoverability
      contract: the exact `ciflow-execute terminal-summary.json ->
      launch.json` pair remains lexically discoverable with durable file
      storage and bounded content discoverability for checked-in runtime keys
      and phrases such as `command`, `phase`, `artifact_paths`,
      `terminal_status`, `next_action`, `current_phase`, and
      `.codex/phase-loop`.
- [ ] IF-0-SEMCODEXLOOPCIFLOWEXECRELAPSETAIL-5 - Durable trace and operator
      contract: `.mcp-index/force_full_exit_trace.json`,
      `GitAwareIndexManager`, and `uv run mcp-index repository status` stay
      aligned with the repaired execute-relapse outcome and do not leave stale
      blame on the cleared `garc-plan -> idxsafe-repair` seam or on the exact
      `ciflow-execute` pair after progress has already moved later.
- [ ] IF-0-SEMCODEXLOOPCIFLOWEXECRELAPSETAIL-6 - Evidence and steering
      contract: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMCODEXLOOPREBOUNDRELAPSETAIL rerun outcome, adds a dedicated
      `SEMCODEXLOOPCIFLOWEXECRELAPSETAIL` live-rerun block, and captures the
      final authoritative verdict for the exact `ciflow-execute
      terminal-summary.json -> launch.json` pair; if execution exposes a
      blocker beyond the current roadmap tail, `specs/phase-plans-v7.md` is
      amended before closeout so `.phase-loop/` points to the newest truthful
      next phase.

## Lane Index & Dependencies

- SL-0 - Exact `ciflow-execute` dispatcher contract freeze; Depends on: SEMCODEXLOOPREBOUNDRELAPSETAIL; Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 - Durable trace and repository-status `ciflow-execute` fixtures; Depends on: SL-0; Blocks: SL-2, SL-3, SL-4; Parallel-safe: no
- SL-2 - Minimal `ciflow-execute` runtime or truth repair; Depends on: SL-0, SL-1; Blocks: SL-3, SL-4; Parallel-safe: no
- SL-3 - Live rerun evidence reducer and docs contract refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SL-4; Parallel-safe: no
- SL-4 - Downstream roadmap steering reducer; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: SEMCODEXLOOPCIFLOWEXECRELAPSETAIL acceptance; Parallel-safe: no

Lane DAG:

```text
SEMCODEXLOOPREBOUNDRELAPSETAIL
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SL-4 -> SEMCODEXLOOPCIFLOWEXECRELAPSETAIL acceptance
```

## Lanes

### SL-0 - Exact `ciflow-execute` Dispatcher Contract Freeze

- **Scope**: Freeze deterministic dispatcher coverage for the exact
  `.codex/phase-loop/runs/20260427T081704Z-09-ciflow-execute/terminal-summary.json ->
  .codex/phase-loop/runs/20260427T081704Z-09-ciflow-execute/launch.json`
  pair so execution proves a narrow bounded repair instead of assuming earlier
  `ciflow-plan`, `artpub-plan`, or `garecut-execute` fixtures already make the
  later pair safe.
- **Owned files**: `tests/test_dispatcher.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMCODEXLOOPCIFLOWEXECRELAPSETAIL-1,
  IF-0-SEMCODEXLOOPCIFLOWEXECRELAPSETAIL-2,
  IF-0-SEMCODEXLOOPCIFLOWEXECRELAPSETAIL-3, and
  IF-0-SEMCODEXLOOPCIFLOWEXECRELAPSETAIL-4 at the dispatcher boundary
- **Interfaces consumed**: existing `Dispatcher.index_directory(...)`;
  `GenericTreeSitterPlugin._exact_bounded_legacy_codex_phase_loop_json_reason(...)`;
  bounded lexical persistence for the earlier `ciflow-plan`,
  `artpub-plan`, `garecut-execute`, and `garc-plan -> idxsafe-repair`
  fixture families; and canonical `.phase-loop` non-legacy JSON routing
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` with repo-shaped fixtures for the
    exact `ciflow-execute terminal-summary.json -> launch.json` pair so the
    dispatcher contract proves durable file rows, zero code chunks, and
    FTS-backed discoverability for that exact pair.
  - test: Add negative guards that the cleared
    `garc-plan launch.json -> idxsafe-repair terminal-summary.json` seam does
    not remain the sticky reported blocker once the rerun has moved later to
    `ciflow-execute`.
  - test: Keep guards proving the exact pair still exposes checked-in runtime
    keys and phrases such as `command`, `phase`, `artifact_paths`,
    `terminal_status`, `next_action`, `current_phase`, and `.codex/phase-loop`
    rather than becoming an indexing blind spot.
  - test: Keep negative guards proving canonical `.phase-loop/state.json`,
    `.phase-loop/events.jsonl`, and `.phase-loop/tui-handoff.md` remain on
    their normal non-legacy path.
  - impl: Keep fixtures deterministic with repo-local JSON strings and
    bounded-path assertions rather than live `sync --force-full` waits.
  - impl: Keep this lane on contract freeze only. Do not mutate dispatcher
    implementation, durable trace logic, CLI wording, docs, or roadmap
    steering here.
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "ciflow or execute or legacy_codex_phase_loop or terminal_summary or launch or bounded or phase_loop"`

### SL-1 - Durable Trace And Repository-Status `ciflow-execute` Fixtures

- **Scope**: Refresh the exact `ciflow-execute terminal-summary.json ->
  launch.json` pair at the durable trace and operator surface so execution can
  distinguish a real runtime repair from a report that still blames the
  cleared `garc-plan -> idxsafe-repair` seam or leaves stale blame on the
  exact execute-relapse pair after progress has already moved later.
- **Owned files**: `tests/test_git_index_manager.py`, `tests/test_repository_commands.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMCODEXLOOPCIFLOWEXECRELAPSETAIL-1,
  IF-0-SEMCODEXLOOPCIFLOWEXECRELAPSETAIL-3, and
  IF-0-SEMCODEXLOOPCIFLOWEXECRELAPSETAIL-5
- **Interfaces consumed**: existing durable trace lifecycle in
  `GitAwareIndexManager`; repository-status interrupted and stale-running
  output; `_print_legacy_codex_phase_loop_boundary(...)`; and the current
  `SEMCODEXLOOPREBOUNDRELAPSETAIL` evidence lineage in
  `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_git_index_manager.py` so running and interrupted
    force-full traces preserve the exact `ciflow-execute terminal-summary.json
    -> launch.json` pair when it is the truthful blocker after the
    `garc-plan -> idxsafe-repair` seam was cleared, then promote a later
    blocker or closeout state once the pair is truly cleared.
  - test: Extend `tests/test_repository_commands.py` so `repository status`
    reports the interrupted trace against the exact `ciflow-execute` pair
    while preserving the generic legacy `.codex/phase-loop` boundary line and
    the canonical `.phase-loop` authority wording.
  - test: Add negative guards proving the cleared
    `garc-plan launch.json -> idxsafe-repair terminal-summary.json` seam does
    not remain the reported active blocker once the current fixtures are
    introduced.
  - impl: Model closeout and successor promotion with synthetic trace payloads
    or monkeypatched manager behavior rather than live `sync --force-full`
    execution inside unit tests.
  - impl: Keep this lane fixture-only. Do not update production runtime code,
    docs, or roadmap steering here.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "ciflow or execute or legacy_codex_phase_loop or interrupted or boundary or closeout_handoff or phase_loop"`

### SL-2 - Minimal `ciflow-execute` Runtime Or Truth Repair

- **Scope**: Implement the smallest production repair needed so the
  current-head force-full rerun no longer leaves the
  `ciflow-execute terminal-summary.json -> launch.json` pair as the active
  lexical watchdog tail, or prove with the refreshed fixtures and live rerun
  that no runtime diff is required before evidence and steering update.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `mcp_server/storage/git_index_manager.py`, `mcp_server/cli/repository_commands.py`
- **Interfaces provided**: IF-0-SEMCODEXLOOPCIFLOWEXECRELAPSETAIL-1 exact
  ciflow-execute relapse advance contract;
  IF-0-SEMCODEXLOOPCIFLOWEXECRELAPSETAIL-2 narrow repair contract;
  IF-0-SEMCODEXLOOPCIFLOWEXECRELAPSETAIL-3 authority-split contract;
  IF-0-SEMCODEXLOOPCIFLOWEXECRELAPSETAIL-4 bounded discoverability contract;
  and IF-0-SEMCODEXLOOPCIFLOWEXECRELAPSETAIL-5 durable trace and operator
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
    `.phase-loop/` authority split. Do not broaden matcher scope or mutate
    legacy `.codex/phase-loop` runtime artifacts directly.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "ciflow or execute or legacy_codex_phase_loop or interrupted or boundary or closeout_handoff or phase_loop"`
  - verify: `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - verify: `sed -n '1,240p' .mcp-index/force_full_exit_trace.json`

### SL-3 - Live Rerun Evidence Reducer And Docs Contract Refresh

- **Scope**: Reduce the execution proof into the checked-in dogfood evidence
  artifact and contract test so the repo records the
  `SEMCODEXLOOPREBOUNDRELAPSETAIL` rerun outcome, the dedicated
  `SEMCODEXLOOPCIFLOWEXECRELAPSETAIL` live-rerun block, and the final
  authoritative verdict for the exact `ciflow-execute` pair.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: IF-0-SEMCODEXLOOPCIFLOWEXECRELAPSETAIL-5 durable
  trace and operator contract evidence; and
  IF-0-SEMCODEXLOOPCIFLOWEXECRELAPSETAIL-6 evidence and steering contract
- **Interfaces consumed**: SL-0 exact-pair dispatcher assertions; SL-1 durable
  trace/status assertions; SL-2 live rerun output from `sync --force-full`,
  `repository status`, and `.mcp-index/force_full_exit_trace.json`; and the
  existing `SEMCODEXLOOPREBOUNDRELAPSETAIL` evidence block
- **Parallel-safe**: no
- **Tasks**:
  - impl: Add a dedicated `## SEMCODEXLOOPCIFLOWEXECRELAPSETAIL Live Rerun Check`
    section to `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` that records the
    exact rerun command, authoritative timestamps, whether the watchdog moved
    beyond the `ciflow-execute` pair or exposed a newer blocker, SQLite count
    snapshots, and the final steering verdict.
  - impl: Refresh `tests/docs/test_semdogfood_evidence_contract.py` so it
    requires the new phase plan path, the prior phase lineage, the exact
    `ciflow-execute terminal-summary.json -> launch.json` pair, and the new
    evidence block heading.
  - impl: If the live rerun proves the target pair is no longer active, the
    report must name the newer blocker exactly and state that older
    `SEMCODEXLOOPREBOUNDRELAPSETAIL` assumptions are stale.
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "SEMCODEXLOOPREBOUNDRELAPSETAIL or SEMCODEXLOOPCIFLOWEXECRELAPSETAIL or ciflow or execute or phase_loop"`

### SL-4 - Downstream Roadmap Steering Reducer

- **Scope**: Keep the v7 roadmap and phase-loop next step truthful after the
  live rerun by either confirming this phase as the new terminal blocker or
  adding the nearest downstream phase if the rerun moves later again.
- **Owned files**: `specs/phase-plans-v7.md`
- **Interfaces provided**: IF-0-SEMCODEXLOOPCIFLOWEXECRELAPSETAIL-6
- **Interfaces consumed**: SL-0 exact-pair dispatcher contract; SL-1 durable
  trace/status contract; SL-2 live rerun verdict; and SL-3 checked-in
  evidence conclusions
- **Parallel-safe**: no
- **Tasks**:
  - impl: Leave `specs/phase-plans-v7.md` unchanged if execution clears the
    exact `ciflow-execute` pair and does not expose a newer blocker beyond the
    current roadmap tail.
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
uv run pytest tests/test_dispatcher.py -q --no-cov -k "ciflow or execute or legacy_codex_phase_loop or terminal_summary or launch or bounded or phase_loop"
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "ciflow or execute or legacy_codex_phase_loop or interrupted or boundary or closeout_handoff or phase_loop"
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "ciflow or execute or legacy_codex_phase_loop or interrupted or boundary or closeout_handoff or phase_loop"
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "SEMCODEXLOOPREBOUNDRELAPSETAIL or SEMCODEXLOOPCIFLOWEXECRELAPSETAIL or ciflow or execute or phase_loop"
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
  -q --no-cov -k "ciflow or execute or legacy_codex_phase_loop or interrupted or boundary or closeout_handoff or phase_loop"
timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
sed -n '1,240p' .mcp-index/force_full_exit_trace.json
git status --short -- plans/phase-plan-v7-SEMCODEXLOOPCIFLOWEXECRELAPSETAIL.md docs/status/SEMANTIC_DOGFOOD_REBUILD.md specs/phase-plans-v7.md
git diff --check
git diff --cached --check
```

## Acceptance Criteria

- [ ] A refreshed repo-local force-full rerun on the
      post-SEMCODEXLOOPREBOUNDRELAPSETAIL head either advances durably beyond
      the newer legacy
      `.codex/phase-loop/runs/20260427T081704Z-09-ciflow-execute/terminal-summary.json ->
      .codex/phase-loop/runs/20260427T081704Z-09-ciflow-execute/launch.json`
      pair or emits a truthful newer blocker before the 120-second watchdog
      expires.
- [ ] Any repair chosen for the legacy `.codex/phase-loop` execute-relapse
      seam stays narrow, tested, and does not reopen the cleared
      `.codex/phase-loop/runs/20260424T190651Z-01-garc-plan/launch.json ->
      .codex/phase-loop/runs/20260427T075236Z-05-idxsafe-repair/terminal-summary.json`
      boundary without direct evidence.
- [ ] Canonical `.phase-loop/` remains authoritative runner state, and the
      repair does not route canonical `.phase-loop/state.json`,
      `.phase-loop/events.jsonl`, or `.phase-loop/tui-handoff.md` through the
      same legacy compatibility path.
- [ ] The exact `ciflow-execute terminal-summary.json -> launch.json` pair
      remains lexically discoverable with durable file storage and bounded
      content discoverability for checked-in runtime keys and phrases such as
      `command`, `phase`, `artifact_paths`, `terminal_status`, `next_action`,
      `current_phase`, and `.codex/phase-loop`.
- [ ] `.mcp-index/force_full_exit_trace.json` and
      `uv run mcp-index repository status` stay aligned with the repaired
      execute-relapse outcome and do not leave stale blame on the cleared
      `garc-plan -> idxsafe-repair` seam or on the exact `ciflow-execute`
      pair after progress has already moved beyond them.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMCODEXLOOPREBOUNDRELAPSETAIL rerun outcome and the final live verdict
      for the exact `ciflow-execute terminal-summary.json -> launch.json`
      pair.
- [ ] If execution reveals a newer blocker beyond the current roadmap tail,
      `specs/phase-plans-v7.md` is updated before closeout so the next
      phase-loop step stays truthful.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMCODEXLOOPCIFLOWEXECRELAPSETAIL.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMCODEXLOOPCIFLOWEXECRELAPSETAIL.md
  artifact_state: staged
```
