---
phase_loop_plan_version: 1
phase: SEMCODEXLOOPHEARTBEATTAIL
roadmap: specs/phase-plans-v7.md
roadmap_sha256: eae54f0b502ea991f0308f54af77a824a16a17a0cad2c2d099e83962aed2f536
---
# SEMCODEXLOOPHEARTBEATTAIL: Legacy Codex Phase-Loop Heartbeat Tail Recovery

## Context

SEMCODEXLOOPHEARTBEATTAIL is the phase-85 follow-up for the v7 semantic
hardening roadmap. Canonical `.phase-loop/` runtime exists in this checkout,
so it is the authoritative runner state for this planning run. The canonical
state is internally consistent for this phase: `.phase-loop/state.json`,
`.phase-loop/tui-handoff.md`, and `.phase-loop/active-loop.json` all point to
`SEMCODEXLOOPHEARTBEATTAIL` as the current `unplanned` phase after
`SEMSECAUTHSANDBOXTAIL` completed. Legacy `.codex/phase-loop/` artifacts are
compatibility-only and must not supersede canonical `.phase-loop/` state.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is the active roadmap, it is tracked and clean in
  this worktree, and `sha256sum specs/phase-plans-v7.md` matches the
  user-required
  `eae54f0b502ea991f0308f54af77a824a16a17a0cad2c2d099e83962aed2f536`.
- The checkout is on `main...origin/main [ahead 165]` at `HEAD`
  `75a0499fade471009a81f822f72c742f7e5375a8`, the worktree is clean before
  this artifact write, and
  `plans/phase-plan-v7-SEMCODEXLOOPHEARTBEATTAIL.md` did not exist before this
  run.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is the active evidence anchor.
  Its roadmap-steering summary now records that `SEMSECAUTHSANDBOXTAIL`
  cleared the later security-test seam, but the refreshed live rerun on the
  new head still terminalized later in lexical walking on the re-exposed
  legacy `.codex/phase-loop` compatibility-runtime seam
  `.codex/phase-loop/runs/20260427T071207Z-01-artpub-plan/launch.json ->
  .codex/phase-loop/runs/20260427T071207Z-01-artpub-plan/heartbeat.json`.
- Existing repo coverage already freezes nearby legacy compatibility-runtime
  behavior, but not this exact pair. `tests/test_dispatcher.py` covers the
  older
  `.codex/phase-loop/runs/20260424T180441Z-01-gagov-execute/launch.json ->
  .codex/phase-loop/runs/20260427T071807Z-02-artpub-execute/terminal-summary.json`
  family, the later
  `.codex/phase-loop/runs/20260424T190651Z-01-garc-plan/launch.json ->
  .codex/phase-loop/runs/20260427T075236Z-05-idxsafe-repair/terminal-summary.json`
  family, and the relapse pair
  `.codex/phase-loop/runs/20260427T081107Z-08-ciflow-plan/terminal-summary.json ->
  .codex/phase-loop/runs/20260427T081107Z-08-ciflow-plan/launch.json`, but
  repo search did not show an exact dispatcher fixture for the later
  `artpub-plan launch.json -> heartbeat.json` pair.
- `mcp_server/plugins/generic_treesitter_plugin.py` already recognizes legacy
  `.codex/phase-loop` `launch.json` and `heartbeat.json` as exact bounded JSON
  compatibility-runtime files. That means this phase should assume the likely
  remaining gap is in dispatcher truth, durable trace promotion, repository
  status reporting, or evidence closeout, not in broad new legacy JSON family
  admission.
- `tests/test_repository_commands.py` and
  `mcp_server/cli/repository_commands.py` already freeze and print the generic
  legacy `.codex/phase-loop` compatibility boundary
  `Lexical boundary: using exact bounded JSON/JSONL indexing for legacy .codex/phase-loop compatibility runtime artifacts while canonical .phase-loop remains authoritative`,
  but the concrete fixture set still centers on older `launch.json ->
  terminal-summary.json` examples and the later `ciflow-plan` relapse pair.
- `tests/test_git_index_manager.py` already freezes durable trace progression
  for the later `ciflow-plan` relapse pair and ensures earlier script seams do
  not remain stale blockers once progress has moved later, but repo search did
  not show the exact `artpub-plan launch.json -> heartbeat.json` pair frozen
  at the `GitAwareIndexManager` status surface yet.
- `tests/docs/test_semdogfood_evidence_contract.py` already mentions both
  `.codex/phase-loop/runs/20260427T071207Z-01-artpub-plan/launch.json` and
  `.codex/phase-loop/runs/20260427T071207Z-01-artpub-plan/heartbeat.json`
  inside the evidence corpus, but the checked-in dogfood report does not yet
  have a dedicated `## SEMCODEXLOOPHEARTBEATTAIL Live Rerun Check` section and
  there is no execution-ready plan artifact defining how execution should
  clear or truthfully supersede this exact seam.

Practical planning boundary:

- SEMCODEXLOOPHEARTBEATTAIL may tighten exact-pair dispatcher fixtures,
  durable trace promotion, repository-status truth, and evidence closeout for
  the `artpub-plan launch.json -> heartbeat.json` seam. It must not mutate
  legacy `.codex/phase-loop` runtime files themselves, and it must not route
  canonical `.phase-loop/` state through the same compatibility path.
- Because exact bounded legacy JSON family support already exists in
  `generic_treesitter_plugin.py`, execution should prefer the smallest repair
  that matches the frozen tests and live rerun evidence before widening into
  new plugin-family behavior.
- SEMCODEXLOOPHEARTBEATTAIL must stay narrow and evidence-driven. It must not
  reopen the cleared
  `tests/security/test_route_auth_coverage.py ->
  tests/security/test_p24_sandbox_degradation.py`
  seam, broaden to blanket `.codex/**` or `.phase-loop/**` handling, or widen
  into unrelated semantic, integration, release, or runner-state mutation work
  unless the refreshed rerun proves the blocker has moved again.

## Interface Freeze Gates

- [ ] IF-0-SEMCODEXLOOPHEARTBEATTAIL-1 - Exact heartbeat-seam advance
      contract: a refreshed repo-local force-full rerun on the
      post-SEMSECAUTHSANDBOXTAIL head no longer terminalizes with the durable
      blocker centered on
      `.codex/phase-loop/runs/20260427T071207Z-01-artpub-plan/launch.json ->
      .codex/phase-loop/runs/20260427T071207Z-01-artpub-plan/heartbeat.json`;
      it either advances durably beyond that exact pair or emits a truthful
      newer blocker before the 120-second watchdog expires.
- [ ] IF-0-SEMCODEXLOOPHEARTBEATTAIL-2 - Authority-split and narrow-repair
      contract: canonical `.phase-loop/` remains authoritative runner state,
      legacy `.codex/phase-loop/` treatment stays compatibility-only, and the
      phase does not reopen the cleared
      `tests/security/test_route_auth_coverage.py ->
      tests/security/test_p24_sandbox_degradation.py`
      seam or widen to blanket `.codex/**`/`.phase-loop/**` shortcuts without
      direct evidence.
- [ ] IF-0-SEMCODEXLOOPHEARTBEATTAIL-3 - Bounded discoverability contract:
      the exact `artpub-plan` `launch.json` and `heartbeat.json` files remain
      lexically discoverable with durable file storage and bounded content
      discoverability for checked-in runtime keys and phrases such as
      `command`, `phase`, `current_phase`, `status`, and `.codex/phase-loop`
      instead of becoming an indexing blind spot.
- [ ] IF-0-SEMCODEXLOOPHEARTBEATTAIL-4 - Durable trace and operator contract:
      `force_full_exit_trace.json`, `GitAwareIndexManager`, and
      `uv run mcp-index repository status` stay aligned with the repaired
      heartbeat-seam outcome and do not leave stale blame on the cleared
      security seam, the later `ciflow-plan` relapse pair, or the
      `artpub-plan` pair once lexical progress has already moved later.
- [ ] IF-0-SEMCODEXLOOPHEARTBEATTAIL-5 - Evidence contract:
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMSECAUTHSANDBOXTAIL rerun outcome, adds a dedicated
      `SEMCODEXLOOPHEARTBEATTAIL` live-rerun block, and captures the final
      authoritative verdict for the `artpub-plan launch.json -> heartbeat.json`
      seam plus any newer blocker.
- [ ] IF-0-SEMCODEXLOOPHEARTBEATTAIL-6 - Downstream steering contract: if
      execution exposes a blocker beyond the current roadmap tail,
      `specs/phase-plans-v7.md` is amended before closeout so phase-loop points
      to the newest truthful next phase instead of stale
      SEMCODEXLOOPHEARTBEATTAIL assumptions.

## Lane Index & Dependencies

- SL-0 - Exact heartbeat compatibility-runtime contract freeze; Depends on: SEMSECAUTHSANDBOXTAIL; Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 - Durable trace and repository-status heartbeat fixtures; Depends on: SL-0; Blocks: SL-2, SL-3, SL-4; Parallel-safe: no
- SL-2 - Minimal heartbeat runtime repair; Depends on: SL-0, SL-1; Blocks: SL-3, SL-4; Parallel-safe: no
- SL-3 - Live rerun evidence reducer and contract refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SL-4; Parallel-safe: no
- SL-4 - Downstream roadmap steering reducer; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: SEMCODEXLOOPHEARTBEATTAIL acceptance; Parallel-safe: no

Lane DAG:

```text
SEMSECAUTHSANDBOXTAIL
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SL-4 -> SEMCODEXLOOPHEARTBEATTAIL acceptance
```

## Lanes

### SL-0 - Exact Heartbeat Compatibility-Runtime Contract Freeze

- **Scope**: Freeze the exact
  `.codex/phase-loop/runs/20260427T071207Z-01-artpub-plan/launch.json ->
  .codex/phase-loop/runs/20260427T071207Z-01-artpub-plan/heartbeat.json`
  seam in deterministic dispatcher coverage so execution proves a narrow
  bounded repair instead of assuming earlier legacy launch/terminal or
  heartbeat fixtures already make the later pair safe.
- **Owned files**: `tests/test_dispatcher.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMCODEXLOOPHEARTBEATTAIL-1,
  IF-0-SEMCODEXLOOPHEARTBEATTAIL-2, and
  IF-0-SEMCODEXLOOPHEARTBEATTAIL-3 at the dispatcher boundary
- **Interfaces consumed**: existing
  `Dispatcher.index_directory(...)`,
  legacy `.codex/phase-loop` exact-bounded JSON family handling,
  durable file metadata storage, and the earlier dispatcher fixtures for the
  `gagov/artpub-execute`, `mrready-execute`, and `ciflow-plan` pairs
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` with repo-shaped fixtures for the
    exact `artpub-plan launch.json -> heartbeat.json` pair so the dispatcher
    contract proves durable file rows, zero code chunks, and FTS-backed
    discoverability for both files.
  - test: Assert that the pair still exposes checked-in runtime keys and
    phrases such as `command`, `phase`, `current_phase`, `status`, and
    `.codex/phase-loop` rather than becoming a silent blind spot.
  - test: Keep negative guards proving the older legacy families still pass
    unchanged and canonical `.phase-loop/state.json` remains on its normal
    non-legacy JSON/plugin path.
  - impl: Keep fixtures deterministic with repo-local JSON strings and
    bounded-path assertions rather than live `sync --force-full` waits.
  - impl: Keep this lane on contract freeze only. Do not mutate dispatcher
    implementation, durable trace logic, CLI wording, evidence docs, or
    roadmap steering here.
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "artpub or heartbeat or legacy_codex_phase_loop or bounded or phase_loop"`

### SL-1 - Durable Trace And Repository-Status Heartbeat Fixtures

- **Scope**: Freeze the exact `artpub-plan launch.json -> heartbeat.json` pair
  at the durable trace and operator surface so execution can distinguish a
  real runtime repair from a report that still blames the cleared security
  seam, the later `ciflow-plan` relapse pair, or this exact pair after lexical
  progress has already moved later.
- **Owned files**: `tests/test_git_index_manager.py`, `tests/test_repository_commands.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMCODEXLOOPHEARTBEATTAIL-1,
  IF-0-SEMCODEXLOOPHEARTBEATTAIL-2, and
  IF-0-SEMCODEXLOOPHEARTBEATTAIL-4
- **Interfaces consumed**: existing durable trace lifecycle in
  `GitAwareIndexManager`; repository-status interrupted and stale-running
  output; the generic legacy `.codex/phase-loop` boundary print helpers in
  `mcp_server/cli/repository_commands.py`; and the current
  SEMSECAUTHSANDBOXTAIL evidence lineage in
  `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_git_index_manager.py` so running and interrupted
    force-full traces can preserve the exact
    `artpub-plan launch.json -> heartbeat.json` pair when it is the truthful
    blocker, then promote a later blocker or closeout state once the pair has
    truly been cleared.
  - test: Extend `tests/test_repository_commands.py` so `repository status`
    reports the interrupted trace against the exact `artpub-plan` pair while
    preserving the generic legacy `.codex/phase-loop` boundary line and the
    canonical `.phase-loop` authority wording.
  - test: Keep negative guards proving the cleared
    `tests/security/test_route_auth_coverage.py ->
    tests/security/test_p24_sandbox_degradation.py`
    seam and the later
    `.codex/phase-loop/runs/20260427T081107Z-08-ciflow-plan/terminal-summary.json ->
    .codex/phase-loop/runs/20260427T081107Z-08-ciflow-plan/launch.json`
    pair do not remain the reported active blocker once the current fixtures
    are introduced.
  - impl: Model closeout and successor promotion with synthetic trace payloads
    or monkeypatched manager behavior rather than live `sync --force-full`
    execution inside unit tests.
  - impl: Keep this lane fixture-only. Do not update production dispatcher
    code, docs, or roadmap steering here.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "artpub or heartbeat or legacy_codex_phase_loop or interrupted or boundary or closeout_handoff or phase_loop"`

### SL-2 - Minimal Heartbeat Runtime Repair

- **Scope**: Implement the smallest dispatcher, closeout-trace, or
  repository-status repair needed so the current-head force-full rerun no
  longer leaves the `artpub-plan launch.json -> heartbeat.json` pair as the
  active lexical watchdog tail.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `mcp_server/storage/git_index_manager.py`, `mcp_server/cli/repository_commands.py`
- **Interfaces provided**: IF-0-SEMCODEXLOOPHEARTBEATTAIL-1 exact heartbeat
  advance contract; IF-0-SEMCODEXLOOPHEARTBEATTAIL-2 authority-split and
  narrow-repair contract; IF-0-SEMCODEXLOOPHEARTBEATTAIL-3 bounded
  discoverability contract; and IF-0-SEMCODEXLOOPHEARTBEATTAIL-4 durable trace
  and operator contract
- **Interfaces consumed**: SL-0 dispatcher fixtures; SL-1 durable
  trace/status fixtures; existing legacy exact-bounded JSON family handling;
  and the current generic legacy boundary wording in
  `repository_commands.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 and SL-1 slices first and confirm whether the active
    defect is dispatcher truth for the exact pair, durable closeout-trace
    promotion after later lexical progress, or CLI status reporting after the
    pair has already been cleared.
  - impl: Prefer the smallest repair surface that matches the frozen tests and
    live evidence. Acceptable outcomes include a dispatcher-side repair in
    `dispatcher_enhanced.py`, a `GitAwareIndexManager` trace-promotion
    correction, or a `repository status` truth repair that stops stale blame
    on the `artpub-plan` pair once progress has already moved on.
  - impl: Preserve the generic legacy boundary line and canonical
    `.phase-loop` authority split. Do not broaden to blanket `.codex/**` or
    `.phase-loop/**` handling, do not mutate runner-state files directly, and
    do not regress the cleared
    `tests/security/test_route_auth_coverage.py ->
    tests/security/test_p24_sandbox_degradation.py`
    seam.
  - impl: If the repair moves the live tail beyond the `artpub-plan` pair,
    ensure the durable trace and operator surface promote the newer blocker or
    closeout stage truthfully instead of leaving stale
    `last_progress_path` or `in_flight_path` blame on the pair.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "artpub or heartbeat or legacy_codex_phase_loop or interrupted or boundary or closeout_handoff or phase_loop"`

### SL-3 - Live Rerun Evidence Reducer And Contract Refresh

- **Scope**: Re-run the bounded repo-local force-full command after SL-2,
  capture the authoritative heartbeat-seam outcome, and refresh the dogfood
  report plus its contract test without widening into unrelated semantic
  claims.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: IF-0-SEMCODEXLOOPHEARTBEATTAIL-1 exact heartbeat
  advance contract; IF-0-SEMCODEXLOOPHEARTBEATTAIL-4 durable trace and
  operator contract; and IF-0-SEMCODEXLOOPHEARTBEATTAIL-5 evidence contract
- **Interfaces consumed**: SL-2 runtime repair; live outputs from
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`,
  `uv run mcp-index repository status`, and
  `.mcp-index/force_full_exit_trace.json`; plus the existing
  SEMSECAUTHSANDBOXTAIL rerun summary in
  `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/docs/test_semdogfood_evidence_contract.py` so the
    report must include a `## SEMCODEXLOOPHEARTBEATTAIL Live Rerun Check`
    block, cite the SEMSECAUTHSANDBOXTAIL prior plan and rerun outcome, and
    record the exact `artpub-plan` pair or its truthful successor.
  - impl: Run the refreshed repo-local force-full rerun after SL-2 using the
    same bounded command from the roadmap evidence, then capture
    `repository status`, `force_full_exit_trace.json`, and SQLite row counts
    on the same head.
  - impl: Update `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` with the final
    authoritative verdict for the `artpub-plan launch.json -> heartbeat.json`
    pair, explicitly naming whether the rerun advanced beyond it, terminalized
    truthfully on it again, or exposed a later blocker.
  - impl: Keep the evidence block semantically fail-closed. Preserve
    readiness, rollout-status, last-sync-error, semantic-readiness, and the
    canonical-versus-legacy authority wording unless the live probes on the
    same head prove they changed.
  - impl: If the rerun advances beyond the pair, state clearly that the
    security seam from SEMSECAUTHSANDBOXTAIL stays closed and that the current
    blocker has moved later.
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "SEMSECAUTHSANDBOXTAIL or SEMCODEXLOOPHEARTBEATTAIL or heartbeat or phase_loop"`
  - verify: `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - verify: `sed -n '1,240p' .mcp-index/force_full_exit_trace.json`
  - verify: `sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'`

### SL-4 - Downstream Roadmap Steering Reducer

- **Scope**: Keep the roadmap truthful after the refreshed rerun by only
  adding a downstream phase when SL-3 proves the active blocker moved beyond
  the current roadmap tail.
- **Owned files**: `specs/phase-plans-v7.md`
- **Interfaces provided**: the downstream-steering portion of
  IF-0-SEMCODEXLOOPHEARTBEATTAIL-6
- **Interfaces consumed**: SL-3 refreshed evidence verdict; current roadmap
  DAG and tail ordering for `specs/phase-plans-v7.md`; and canonical
  `.phase-loop/` expectations that the next unplanned phase reflect the latest
  durable blocker rather than stale heartbeat-tail assumptions
- **Parallel-safe**: no
- **Tasks**:
  - test: Re-read the post-SL-3 evidence and confirm whether the repaired
    rerun actually exposes a newer blocker beyond the current roadmap tail
    before mutating roadmap steering.
  - impl: If the active blocker remains inside the `artpub-plan` pair or the
    rerun completes lexical closeout without exposing a new tail, leave the
    roadmap unchanged.
  - impl: If the rerun advances beyond the current roadmap tail and no
    downstream phase already covers the new blocker, append the nearest
    truthful downstream recovery phase to `specs/phase-plans-v7.md` with the
    same evidence-first structure used by the current SEM* lexical-recovery
    chain.
  - impl: Keep any roadmap mutation limited to the newly exposed blocker. Do
    not rewrite earlier phases or reopen SEMSECAUTHSANDBOXTAIL assumptions
    while closing this heartbeat seam.
  - verify: `git diff -- specs/phase-plans-v7.md`

## Verification

Planning-only run: do not execute these during plan creation. Run them during
`codex-execute-phase` or manual SEMCODEXLOOPHEARTBEATTAIL execution.

Lane-specific checks:

```bash
uv run pytest tests/test_dispatcher.py -q --no-cov -k "artpub or heartbeat or legacy_codex_phase_loop or bounded or phase_loop"
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "artpub or heartbeat or legacy_codex_phase_loop or interrupted or boundary or closeout_handoff or phase_loop"
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "artpub or heartbeat or legacy_codex_phase_loop or interrupted or boundary or closeout_handoff or phase_loop"
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "SEMSECAUTHSANDBOXTAIL or SEMCODEXLOOPHEARTBEATTAIL or heartbeat or phase_loop"
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
  -q --no-cov -k "artpub or heartbeat or legacy_codex_phase_loop or interrupted or boundary or closeout_handoff or phase_loop"
timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
sed -n '1,240p' .mcp-index/force_full_exit_trace.json
git status --short -- plans/phase-plan-v7-SEMCODEXLOOPHEARTBEATTAIL.md docs/status/SEMANTIC_DOGFOOD_REBUILD.md specs/phase-plans-v7.md
git diff --check
git diff --cached --check
```

## Acceptance Criteria

- [ ] A refreshed repo-local force-full rerun on the post-SEMSECAUTHSANDBOXTAIL
      head either advances durably beyond the later
      `.codex/phase-loop/runs/20260427T071207Z-01-artpub-plan/launch.json ->
      .codex/phase-loop/runs/20260427T071207Z-01-artpub-plan/heartbeat.json`
      pair or emits a truthful newer blocker before the 120-second watchdog
      expires.
- [ ] Any repair chosen for the legacy `.codex/phase-loop` heartbeat seam
      stays narrow, tested, keeps canonical `.phase-loop/` authoritative, and
      does not reopen the cleared
      `tests/security/test_route_auth_coverage.py ->
      tests/security/test_p24_sandbox_degradation.py`
      boundary without direct evidence.
- [ ] The exact `artpub-plan` `launch.json` and `heartbeat.json` files remain
      lexically discoverable with durable file storage and bounded content
      discoverability for checked-in runtime keys and phrases such as
      `command`, `phase`, `current_phase`, `status`, and `.codex/phase-loop`.
- [ ] `force_full_exit_trace.json` and
      `uv run mcp-index repository status` stay aligned with the repaired
      heartbeat-seam outcome and do not leave stale blame on the cleared
      security seam, the later `ciflow-plan` relapse pair, or the
      `artpub-plan` pair after progress has already moved beyond them.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMSECAUTHSANDBOXTAIL rerun outcome and the final live verdict for the
      `artpub-plan launch.json -> heartbeat.json` seam.
- [ ] If execution reveals a newer blocker beyond the current roadmap tail,
      `specs/phase-plans-v7.md` is updated before closeout so the next
      phase-loop step stays truthful.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMCODEXLOOPHEARTBEATTAIL.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMCODEXLOOPHEARTBEATTAIL.md
  artifact_state: staged
```
