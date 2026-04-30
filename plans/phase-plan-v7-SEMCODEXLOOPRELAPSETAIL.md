---
phase_loop_plan_version: 1
phase: SEMCODEXLOOPRELAPSETAIL
roadmap: specs/phase-plans-v7.md
roadmap_sha256: b66c57c2c2d161d9c01661d8192924dd3e5a4c8601acdaacfed068ef1d66e668
---
# SEMCODEXLOOPRELAPSETAIL: Legacy Codex Phase-Loop Relapse Tail Recovery

## Context

SEMCODEXLOOPRELAPSETAIL is the phase-82 follow-up for the v7 semantic
hardening roadmap. Canonical `.phase-loop/` runtime exists in this checkout,
so it is the authoritative runner state for this planning run. Canonical
state is internally inconsistent at the moment: `.phase-loop/state.json` and
`.phase-loop/tui-handoff.md` still report `SEMQUERYFULLREBOUNDTAIL` as the
current `unplanned` phase, while the active canonical run directory
`.phase-loop/runs/20260430T020310Z-03-semcodexlooprelapsetail-plan/launch.json`
and the explicit operator request both target `SEMCODEXLOOPRELAPSETAIL`.
That drift is a canonical `.phase-loop` snapshot lag, not a reason to let any
legacy `.codex/phase-loop/` compatibility artifact supersede current runner
intent.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is the active roadmap, it is tracked and clean in
  this worktree, and `sha256sum specs/phase-plans-v7.md` matches the
  user-required
  `b66c57c2c2d161d9c01661d8192924dd3e5a4c8601acdaacfed068ef1d66e668`.
- The checkout is on `main...origin/main [ahead 159]` at `HEAD`
  `4618295015f38481fbf0dcb0cbc7ec7fbca99318`, the worktree is clean before
  this artifact write, and
  `plans/phase-plan-v7-SEMCODEXLOOPRELAPSETAIL.md` did not exist before this
  run.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is the active evidence anchor.
  Its `SEMQUERYFULLREBOUNDTAIL Live Rerun Check` block records that the
  refreshed repo-local command
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  advanced durably beyond
  `scripts/run_comprehensive_query_test.py ->
  scripts/index_all_repos_semantic_full.py`
  and later terminalized on the re-exposed legacy `.codex/phase-loop`
  compatibility-runtime pair
  `.codex/phase-loop/runs/20260427T081107Z-08-ciflow-plan/terminal-summary.json ->
  .codex/phase-loop/runs/20260427T081107Z-08-ciflow-plan/launch.json`.
- That same evidence block shows the current exact blocker shape that this
  phase must clear or truthfully supersede: at `2026-04-30T01:51:10Z`,
  `.mcp-index/force_full_exit_trace.json` showed `status: running`,
  `stage: lexical_walking`,
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/tests/test_semantic_namespace_resolver.py`,
  and
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/tests/test_plugin_startup_preindex.py`,
  proving the rerun had already advanced beyond the
  SEMQUERYFULLREBOUNDTAIL-era script seam before the watchdog expired. At
  `2026-04-30T01:52:29Z`, a refreshed `repository status` terminalized the
  rerun to `Trace status: interrupted` while preserving later durable
  progress at the relapse pair
  `.codex/phase-loop/runs/20260427T081107Z-08-ciflow-plan/terminal-summary.json ->
  .codex/phase-loop/runs/20260427T081107Z-08-ciflow-plan/launch.json`.
- `repository status` on the same head remained semantically fail-closed
  after the rerun:
  `Readiness: stale_commit`, `Rollout status: partial_index_failure`,
  `Last sync error: disk I/O error`, and
  `Semantic readiness: summaries_missing`. SQLite runtime counts also remained
  `files = 1064`, `code_chunks = 13095`, `chunk_summaries = 0`, and
  `semantic_points = 0`, so this remains a lexical tail and trace-truth slice
  rather than a semantic-vector recovery phase.
- Existing repo coverage already freezes part of the relapse seam. Search in
  `tests/test_git_index_manager.py` and `tests/test_repository_commands.py`
  shows exact fixtures for the
  `.codex/phase-loop/runs/20260427T081107Z-08-ciflow-plan/terminal-summary.json ->
  .codex/phase-loop/runs/20260427T081107Z-08-ciflow-plan/launch.json`
  pair, including assertions that earlier blockers such as
  `scripts/run_comprehensive_query_test.py`,
  `scripts/index_all_repos_semantic_full.py`,
  `tests/docs/test_garc_rc_soak_contract.py`, and
  `tests/docs/test_garel_ga_release_contract.py` do not remain the reported
  active blocker.
- `tests/docs/test_semdogfood_evidence_contract.py` already expects the
  downstream phase name `SEMCODEXLOOPRELAPSETAIL`, the exact relapse pair,
  and the current legacy boundary line, but the checked-in dogfood report
  still lacks a dedicated `## SEMCODEXLOOPRELAPSETAIL Live Rerun Check`
  section and there is no execution-ready plan artifact yet.
- `tests/test_dispatcher.py` already freezes the earlier legacy
  `.codex/phase-loop` families, including the older
  `.codex/phase-loop/runs/20260424T180441Z-01-gagov-execute/launch.json ->
  .codex/phase-loop/runs/20260427T071807Z-02-artpub-execute/terminal-summary.json`
  pair and the later rebound pair
  `.codex/phase-loop/runs/20260424T190651Z-01-garc-plan/launch.json ->
  .codex/phase-loop/runs/20260427T075236Z-05-idxsafe-repair/terminal-summary.json`,
  but repo search did not show exact bounded dispatcher coverage yet for the
  relapse pair centered on the `ciflow-plan` run directory.
- The phase key files from the roadmap remain the correct execution surfaces:
  `mcp_server/dispatcher/dispatcher_enhanced.py`,
  `mcp_server/cli/repository_commands.py`,
  `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`,
  `tests/test_git_index_manager.py`,
  `tests/test_repository_commands.py`, and
  `tests/docs/test_semdogfood_evidence_contract.py`. Execution may expand
  into `tests/test_dispatcher.py` and `mcp_server/storage/git_index_manager.py`
  because the checked-in evidence and existing relapse fixtures already prove
  those are part of the live contract surface.

Practical planning boundary:

- SEMCODEXLOOPRELAPSETAIL may tighten the exact bounded legacy
  compatibility-runtime handling, durable trace promotion, or repository
  status truth surface needed to clear the relapse pair. It should not mutate
  legacy `.codex/phase-loop` runtime files themselves, and it must not treat
  those compatibility artifacts as authoritative runner state.
- Because repo search already shows relapse fixtures in the trace and CLI
  tests, execution should assume the likely remaining gap is one of:
  dispatcher bounded-path coverage for the relapse pair, stale durable-trace
  promotion, or evidence/closeout truth after lexical progress moves later.
  Broad `.codex/**` matching, canonical `.phase-loop/**` bypasses, and
  speculative reopening of already-cleared script seams are all out of scope.
- SEMCODEXLOOPRELAPSETAIL must stay narrow and evidence-driven. It must not
  reopen the repaired
  `scripts/run_comprehensive_query_test.py ->
  scripts/index_all_repos_semantic_full.py`
  seam, broaden canonical `.phase-loop/` runtime behavior, or widen into
  unrelated semantic, integration, or release work unless the refreshed rerun
  proves the blocker has moved again.

## Interface Freeze Gates

- [ ] IF-0-SEMCODEXLOOPRELAPSETAIL-1 - Exact relapse advance contract:
      a refreshed repo-local force-full rerun on the
      post-SEMQUERYFULLREBOUNDTAIL head no longer terminalizes with the
      durable blocker centered on
      `.codex/phase-loop/runs/20260427T081107Z-08-ciflow-plan/terminal-summary.json ->
      .codex/phase-loop/runs/20260427T081107Z-08-ciflow-plan/launch.json`;
      it either advances durably beyond that exact pair or emits a truthful
      newer blocker before the 120-second watchdog expires.
- [ ] IF-0-SEMCODEXLOOPRELAPSETAIL-2 - Authority-split contract:
      canonical `.phase-loop/` remains authoritative runner state, and any
      legacy `.codex/phase-loop/` treatment stays compatibility-only. The
      phase must not route canonical `.phase-loop/state.json`,
      `.phase-loop/events.jsonl`, or `.phase-loop/tui-handoff.md` through the
      same relapse fast path, and it must not mutate legacy `.codex` artifacts
      to steer runner truth.
- [ ] IF-0-SEMCODEXLOOPRELAPSETAIL-3 - Bounded discoverability contract:
      the relapse pair remains lexically discoverable with durable file
      storage and bounded content discoverability for checked-in runtime keys
      and phrases such as `command`, `phase`, `artifact_paths`,
      `terminal_status`, `next_action`, `current_phase`, and
      `.codex/phase-loop`; the repair must not clear the seam by turning the
      pair into an indexing blind spot.
- [ ] IF-0-SEMCODEXLOOPRELAPSETAIL-4 - Durable trace and operator contract:
      `force_full_exit_trace.json`, `GitAwareIndexManager`, and
      `uv run mcp-index repository status` stay aligned with the repaired
      relapse outcome and do not leave stale blame on either the cleared
      SEMQUERYFULLREBOUNDTAIL-era script seam or the relapse pair once lexical
      progress has already moved later.
- [ ] IF-0-SEMCODEXLOOPRELAPSETAIL-5 - Evidence contract:
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMQUERYFULLREBOUNDTAIL rerun outcome, adds a dedicated
      `SEMCODEXLOOPRELAPSETAIL` live-rerun block, and captures the final
      authoritative verdict for the relapse pair plus any newer blocker.
- [ ] IF-0-SEMCODEXLOOPRELAPSETAIL-6 - Downstream steering contract:
      if execution exposes a blocker beyond the current roadmap tail,
      `specs/phase-plans-v7.md` is amended before closeout so phase-loop
      points to the newest truthful next phase instead of stale relapse
      assumptions.

## Lane Index & Dependencies

- SL-0 - Exact relapse compatibility-runtime contract freeze; Depends on: SEMQUERYFULLREBOUNDTAIL; Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 - Durable trace and repository-status relapse fixtures; Depends on: SL-0; Blocks: SL-2, SL-3, SL-4; Parallel-safe: no
- SL-2 - Minimal relapse runtime repair; Depends on: SL-0, SL-1; Blocks: SL-3, SL-4; Parallel-safe: no
- SL-3 - Live rerun evidence reducer and contract refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SL-4; Parallel-safe: no
- SL-4 - Downstream roadmap steering reducer; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: SEMCODEXLOOPRELAPSETAIL acceptance; Parallel-safe: no

Lane DAG:

```text
SEMQUERYFULLREBOUNDTAIL
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SL-4 -> SEMCODEXLOOPRELAPSETAIL acceptance
```

## Lanes

### SL-0 - Exact Relapse Compatibility-Runtime Contract Freeze

- **Scope**: Freeze the exact
  `.codex/phase-loop/runs/20260427T081107Z-08-ciflow-plan/terminal-summary.json ->
  .codex/phase-loop/runs/20260427T081107Z-08-ciflow-plan/launch.json`
  relapse in deterministic dispatcher coverage so execution proves a narrow
  bounded repair instead of assuming the older legacy family fixtures already
  make the later pair safe.
- **Owned files**: `tests/test_dispatcher.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMCODEXLOOPRELAPSETAIL-1,
  IF-0-SEMCODEXLOOPRELAPSETAIL-2, and
  IF-0-SEMCODEXLOOPRELAPSETAIL-3 at the dispatcher boundary
- **Interfaces consumed**: existing
  `Dispatcher.index_directory(...)`,
  the checked-in bounded legacy `.codex/phase-loop` path family,
  durable file metadata storage, and the earlier dispatcher fixtures for the
  `gagov/artpub` and `garc/idxsafe` legacy pairs
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` with repo-shaped fixtures for the
    exact relapse pair
    `.codex/phase-loop/runs/20260427T081107Z-08-ciflow-plan/terminal-summary.json ->
    .codex/phase-loop/runs/20260427T081107Z-08-ciflow-plan/launch.json`
    so the dispatcher contract proves durable file rows, zero code chunks,
    and FTS-backed discoverability for that pair.
  - test: Keep negative guards proving the older legacy families still pass
    unchanged and canonical `.phase-loop/state.json` remains on its normal
    non-legacy JSON/plugin path.
  - test: Assert that the relapse pair still exposes checked-in runtime keys
    and phrases such as `command`, `phase`, `artifact_paths`,
    `terminal_status`, `next_action`, `current_phase`, and
    `.codex/phase-loop` rather than becoming a silent blind spot.
  - impl: Keep fixtures deterministic with repo-local JSON strings and
    bounded-path assertions rather than live `sync --force-full` waits.
  - impl: Keep this lane on contract freeze only. Do not mutate dispatcher
    implementation, durable trace logic, CLI wording, evidence docs, or
    roadmap steering here.
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "ciflow or legacy_codex_phase_loop or terminal_summary or launch or bounded or phase_loop"`

### SL-1 - Durable Trace And Repository-Status Relapse Fixtures

- **Scope**: Freeze the relapse pair at the durable trace and operator surface
  so execution can distinguish a real runtime repair from a report that still
  blames the exact legacy pair after lexical progress has already moved later.
- **Owned files**: `tests/test_git_index_manager.py`, `tests/test_repository_commands.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMCODEXLOOPRELAPSETAIL-1,
  IF-0-SEMCODEXLOOPRELAPSETAIL-2, and
  IF-0-SEMCODEXLOOPRELAPSETAIL-4
- **Interfaces consumed**: existing durable trace lifecycle in
  `GitAwareIndexManager`; repository-status interrupted and stale-running
  output; `_print_legacy_codex_phase_loop_boundary(...)`; and the current
  relapse evidence from `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- **Parallel-safe**: no
- **Tasks**:
  - test: Refresh or extend `tests/test_git_index_manager.py` so a lexical
    rerun that has already advanced beyond the SEMQUERYFULLREBOUNDTAIL script
    seam can still preserve the exact relapse pair when it is the truthful
    blocker, then promote a later blocker or closeout status once the pair
    has been cleared.
  - test: Refresh or extend `tests/test_repository_commands.py` so
    `repository status` continues to print the generic legacy boundary line
    when the compatibility runtime family is present, while freezing the
    interrupted trace output against the relapse pair instead of older
    legacy examples or the cleared script seam.
  - test: Keep negative guards that canonical `.phase-loop` authority wording
    remains intact and that the repaired
    `scripts/run_comprehensive_query_test.py ->
    scripts/index_all_repos_semantic_full.py`
    seam does not regress into the reported active blocker once the relapse
    fixtures are introduced.
  - impl: Model closeout and successor promotion with synthetic trace payloads
    or monkeypatched manager behavior rather than live `sync --force-full`
    execution inside unit tests.
  - impl: Keep this lane fixture-only. Do not update production trace logic,
    CLI code, docs, or roadmap steering here.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "ciflow or legacy_codex_phase_loop or interrupted or boundary or closeout_handoff or phase_loop"`

### SL-2 - Minimal Relapse Runtime Repair

- **Scope**: Implement the smallest dispatcher or closeout-trace or
  repository-status repair needed so the current-head force-full rerun no
  longer leaves the relapse pair as the active lexical watchdog tail.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `mcp_server/storage/git_index_manager.py`, `mcp_server/cli/repository_commands.py`
- **Interfaces provided**: IF-0-SEMCODEXLOOPRELAPSETAIL-1 exact relapse
  advance contract; IF-0-SEMCODEXLOOPRELAPSETAIL-2 authority-split contract;
  IF-0-SEMCODEXLOOPRELAPSETAIL-3 bounded discoverability contract; and
  IF-0-SEMCODEXLOOPRELAPSETAIL-4 durable trace and operator contract
- **Interfaces consumed**: SL-0 dispatcher fixtures; SL-1 durable
  trace/status fixtures; existing bounded legacy `.codex/phase-loop`
  compatibility handling; and the current generic legacy boundary wording in
  `repository_commands.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 and SL-1 slices first and confirm whether the active
    defect is still dispatcher-side bounded indexing for the relapse pair,
    durable closeout-trace promotion, or CLI trace reporting after the pair
    has already been cleared.
  - impl: Prefer the smallest repair surface that matches the frozen tests and
    live evidence. Acceptable outcomes include a dispatcher bounded-path fix,
    a `GitAwareIndexManager` closeout-trace correction, or a
    `repository status` truth repair that stops stale blame on the relapse
    pair once progress has already moved on.
  - impl: Preserve the generic legacy boundary line and canonical
    `.phase-loop` authority split. Do not broaden to blanket `.codex/**` or
    `.phase-loop/**` handling, do not mutate runner-state files directly, and
    do not regress the repaired
    `scripts/run_comprehensive_query_test.py ->
    scripts/index_all_repos_semantic_full.py`
    seam.
  - impl: If the repair moves the live tail beyond the relapse pair, ensure
    the durable trace and operator surface promote the newer blocker or
    closeout stage truthfully instead of leaving stale `last_progress_path`
    or `in_flight_path` blame on the `ciflow-plan` pair.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "ciflow or legacy_codex_phase_loop or interrupted or boundary or closeout_handoff or phase_loop"`

### SL-3 - Live Rerun Evidence Reducer And Contract Refresh

- **Scope**: Re-run the bounded repo-local force-full command after SL-2,
  capture the authoritative relapse outcome, and refresh the dogfood report
  plus its contract test without widening into unrelated semantic claims.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: IF-0-SEMCODEXLOOPRELAPSETAIL-1 exact relapse
  advance contract; IF-0-SEMCODEXLOOPRELAPSETAIL-4 durable trace and operator
  contract; and IF-0-SEMCODEXLOOPRELAPSETAIL-5 evidence contract
- **Interfaces consumed**: SL-2 runtime repair; live outputs from
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`,
  `uv run mcp-index repository status`, and
  `.mcp-index/force_full_exit_trace.json`; plus the existing
  `SEMQUERYFULLREBOUNDTAIL Live Rerun Check` block
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/docs/test_semdogfood_evidence_contract.py` so the
    report must include a `## SEMCODEXLOOPRELAPSETAIL Live Rerun Check` block,
    cite the SEMQUERYFULLREBOUNDTAIL prior plan and rerun outcome, and record
    the exact relapse pair or its truthful successor.
  - impl: Run the refreshed repo-local force-full rerun after SL-2 using the
    same bounded command from the roadmap evidence, then capture
    `repository status`, `force_full_exit_trace.json`, and SQLite row counts
    on the same head.
  - impl: Update `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` with the final
    authoritative verdict for the relapse pair, explicitly naming whether the
    rerun advanced beyond it, terminalized truthfully on it again, or exposed
    a later blocker.
  - impl: Keep the evidence block semantically fail-closed. Preserve
    readiness, rollout-status, last-sync-error, semantic-readiness, and the
    canonical-versus-legacy authority wording unless the live probes on the
    same head prove they changed.
  - impl: If the rerun advances beyond the relapse pair, state clearly that
    the SEMQUERYFULLREBOUNDTAIL-era script seam stays closed and that the
    current blocker has moved later.
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "SEMQUERYFULLREBOUNDTAIL or SEMCODEXLOOPRELAPSETAIL or phase_loop"`

### SL-4 - Downstream Roadmap Steering Reducer

- **Scope**: Keep the roadmap truthful after the refreshed rerun by only
  adding a downstream phase when SL-3 proves the active blocker moved beyond
  the current roadmap tail.
- **Owned files**: `specs/phase-plans-v7.md`
- **Interfaces provided**: the downstream-steering portion of
  IF-0-SEMCODEXLOOPRELAPSETAIL-6
- **Interfaces consumed**: SL-3 refreshed evidence verdict; current roadmap
  DAG and tail ordering for `specs/phase-plans-v7.md`; and canonical
  `.phase-loop/` expectations that the next unplanned phase reflect the
  latest durable blocker rather than stale relapse assumptions
- **Parallel-safe**: no
- **Tasks**:
  - test: Re-read the post-SL-3 evidence and confirm whether the repaired
    rerun actually exposes a newer blocker beyond the current roadmap tail
    before mutating roadmap steering.
  - impl: If the active blocker remains inside the current relapse pair or
    the rerun completes lexical closeout without exposing a new tail, leave
    the roadmap unchanged.
  - impl: If the rerun advances beyond the current roadmap tail and no
    downstream phase already covers the new blocker, append the nearest
    truthful downstream recovery phase to `specs/phase-plans-v7.md` with the
    same evidence-first structure used by the current SEM* lexical-recovery
    chain.
  - impl: Keep any roadmap mutation limited to the newly exposed blocker. Do
    not rewrite earlier phases or reopen SEMQUERYFULLREBOUNDTAIL assumptions
    while closing this relapse seam.
  - verify: `git diff -- specs/phase-plans-v7.md`

## Verification

Planning-only run: do not execute these during plan creation. Run them during
`codex-execute-phase` or manual SEMCODEXLOOPRELAPSETAIL execution.

Lane-specific checks:

```bash
uv run pytest tests/test_dispatcher.py -q --no-cov -k "ciflow or legacy_codex_phase_loop or terminal_summary or launch or bounded or phase_loop"
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "ciflow or legacy_codex_phase_loop or interrupted or boundary or closeout_handoff or phase_loop"
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "ciflow or legacy_codex_phase_loop or interrupted or boundary or closeout_handoff or phase_loop"
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "SEMQUERYFULLREBOUNDTAIL or SEMCODEXLOOPRELAPSETAIL or phase_loop"
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
  -q --no-cov -k "ciflow or legacy_codex_phase_loop or interrupted or boundary or closeout_handoff or phase_loop"
timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
sed -n '1,240p' .mcp-index/force_full_exit_trace.json
git status --short -- plans/phase-plan-v7-SEMCODEXLOOPRELAPSETAIL.md docs/status/SEMANTIC_DOGFOOD_REBUILD.md specs/phase-plans-v7.md
git diff --check
git diff --cached --check
```

## Acceptance Criteria

- [ ] A refreshed repo-local force-full rerun on the
      post-SEMQUERYFULLREBOUNDTAIL head either advances durably beyond the
      later
      `.codex/phase-loop/runs/20260427T081107Z-08-ciflow-plan/terminal-summary.json ->
      .codex/phase-loop/runs/20260427T081107Z-08-ciflow-plan/launch.json`
      pair or emits a truthful newer blocker before the 120-second watchdog
      expires.
- [ ] Any repair chosen for the legacy `.codex/phase-loop` relapse seam stays
      narrow, tested, and does not reopen the repaired
      `scripts/run_comprehensive_query_test.py ->
      scripts/index_all_repos_semantic_full.py`
      boundary without direct evidence.
- [ ] Canonical `.phase-loop/` remains authoritative runner state, and the
      repair does not route canonical `.phase-loop/state.json`,
      `.phase-loop/events.jsonl`, or `.phase-loop/tui-handoff.md` through the
      same legacy compatibility path.
- [ ] The relapse pair remains lexically discoverable with durable file
      storage and bounded content discoverability for checked-in runtime keys
      and phrases such as `command`, `phase`, `artifact_paths`,
      `terminal_status`, `next_action`, `current_phase`, and
      `.codex/phase-loop`.
- [ ] `force_full_exit_trace.json` and
      `uv run mcp-index repository status` stay aligned with the repaired
      relapse outcome and do not leave stale blame on the cleared
      SEMQUERYFULLREBOUNDTAIL-era script seam or on the relapse pair after
      progress has already moved beyond them.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMQUERYFULLREBOUNDTAIL rerun outcome and the final live verdict for the
      relapse pair.
- [ ] If execution reveals a newer blocker beyond the current roadmap tail,
      `specs/phase-plans-v7.md` is updated before closeout so the next
      phase-loop step stays truthful.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMCODEXLOOPRELAPSETAIL.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMCODEXLOOPRELAPSETAIL.md
  artifact_state: staged
```
