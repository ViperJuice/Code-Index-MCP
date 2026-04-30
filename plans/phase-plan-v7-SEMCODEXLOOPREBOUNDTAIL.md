---
phase_loop_plan_version: 1
phase: SEMCODEXLOOPREBOUNDTAIL
roadmap: specs/phase-plans-v7.md
roadmap_sha256: c5c8692f81797c7000e4b9d43ced925351c95d847ef3f3123d418205368e6c53
---
# SEMCODEXLOOPREBOUNDTAIL: Legacy Codex Phase-Loop Rebound Tail Recovery

## Context

SEMCODEXLOOPREBOUNDTAIL is the phase-78 follow-up for the v7 semantic
hardening roadmap. Canonical `.phase-loop/` runtime exists in this checkout,
so it is the authoritative runner state for this planning run. The current
canonical snapshots agree cleanly: `.phase-loop/state.json` and
`.phase-loop/tui-handoff.md` both identify `SEMCODEXLOOPREBOUNDTAIL` as the
current `unplanned` phase for `specs/phase-plans-v7.md`, and the recorded
roadmap hash matches the user-required
`c5c8692f81797c7000e4b9d43ced925351c95d847ef3f3123d418205368e6c53`.
Legacy `.codex/phase-loop/` artifacts remain compatibility-only and do not
supersede canonical `.phase-loop/` state here.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is the active roadmap, it is tracked and clean in
  this worktree, and `sha256sum specs/phase-plans-v7.md` matches the required
  `c5c8692f81797c7000e4b9d43ced925351c95d847ef3f3123d418205368e6c53`.
- The checkout is on `main...origin/main [ahead 151]` at `HEAD`
  `4f9e32c50b9ef7f9eb780eba3ac61795acd1644b`, the worktree is clean before
  this artifact write, and
  `plans/phase-plan-v7-SEMCODEXLOOPREBOUNDTAIL.md` did not exist before this
  run.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is the active evidence anchor.
  Its `SEMQUERYFULLTAIL Live Rerun Check` block records that the refreshed
  repo-local command
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  advanced on observed commit
  `230557ff39fcb4ec8c494fa13af413b4e8b04ca6`, moved durably beyond
  `scripts/run_comprehensive_query_test.py ->
  scripts/index_all_repos_semantic_full.py`, and later terminalized on the
  re-exposed legacy `.codex/phase-loop` compatibility-runtime pair
  `.codex/phase-loop/runs/20260424T190651Z-01-garc-plan/launch.json ->
  .codex/phase-loop/runs/20260427T075236Z-05-idxsafe-repair/terminal-summary.json`.
- That same evidence block shows the current exact blocker shape that this
  phase must clear or truthfully supersede: at `2026-04-30T00:30:12Z`,
  `.mcp-index/force_full_exit_trace.json` still showed `status: running`,
  `stage: lexical_walking`,
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/.codex/phase-loop/runs/20260424T190651Z-01-garc-plan/launch.json`,
  and
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/.codex/phase-loop/runs/20260427T075236Z-05-idxsafe-repair/terminal-summary.json`.
  At `2026-04-30T00:30:24Z`, `repository status` truthfully terminalized that
  rerun to `Trace status: interrupted` while preserving the same later legacy
  pair.
- SQLite runtime counts after the SEMQUERYFULLTAIL rerun remained
  `files = 1064`, `code_chunks = 13095`, `chunk_summaries = 0`, and
  `semantic_points = 0`, so this remains a lexical tail and trace-truth slice
  rather than a semantic-vector recovery.
- The repo already carries a narrow family-wide legacy matcher.
  `mcp_server/plugins/generic_treesitter_plugin.py` recognizes
  `.codex/phase-loop/runs/*/launch.json`,
  `.codex/phase-loop/runs/*/heartbeat.json`,
  `.codex/phase-loop/runs/*/terminal-summary.json`,
  `.codex/phase-loop/archive/*/state.json`,
  `.codex/phase-loop/archive/*/events.jsonl`, and top-level legacy ledger
  files while leaving canonical `.phase-loop/state.json` on its normal JSON
  path.
- Existing dispatcher and CLI tests freeze the earlier legacy family, not this
  later rebound pair. `tests/test_dispatcher.py` currently proves bounded
  persistence for the older
  `.codex/phase-loop/runs/20260424T180441Z-01-gagov-execute/launch.json`,
  `.codex/phase-loop/runs/20260427T071807Z-02-artpub-execute/terminal-summary.json`,
  and heartbeat/archive companions, while `tests/test_repository_commands.py`
  currently asserts the generic legacy boundary line using those same earlier
  files.
- `mcp_server/cli/repository_commands.py` still prints the generic legacy
  boundary message
  `Lexical boundary: using exact bounded JSON/JSONL indexing for legacy .codex/phase-loop compatibility runtime artifacts while canonical .phase-loop remains authoritative`,
  but its fixture gate is still anchored to the earlier run/archive examples.
  This phase therefore needs later-pair truth coverage, not a broad rewrite of
  the authority split.
- `tests/test_git_index_manager.py` already has durable trace and interrupted
  closeout coverage for many lexical tails, but this planning slice has not
  yet frozen the exact later rebound pair or its promotion rules after the
  comprehensive-query/full-sync seam is already cleared.
- `tests/docs/test_semdogfood_evidence_contract.py` already references the
  generic legacy boundary line and the SEMQUERYFULLTAIL handoff, but it does
  not yet enforce an execution-ready evidence block for
  `SEMCODEXLOOPREBOUNDTAIL`.

Practical planning boundary:

- SEMCODEXLOOPREBOUNDTAIL may tighten dispatcher trace progression,
  closeout-handoff promotion, repository-status wording, and dogfood evidence
  so the later
  `.codex/phase-loop/runs/20260424T190651Z-01-garc-plan/launch.json ->
  .codex/phase-loop/runs/20260427T075236Z-05-idxsafe-repair/terminal-summary.json`
  rebound no longer remains the active watchdog tail on the current head.
- Because the generic legacy matcher already exists, execution should treat a
  fresh matcher expansion as suspect until tests or the live rerun prove the
  later pair still misses the bounded path. Prefer minimal trace/closeout
  truth repairs over reopening already-closed family-wide matcher work.
- SEMCODEXLOOPREBOUNDTAIL must stay narrow and evidence-driven. It must not
  reopen the repaired
  `scripts/run_comprehensive_query_test.py ->
  scripts/index_all_repos_semantic_full.py`
  seam, broaden canonical `.phase-loop/` handling, or widen into unrelated
  semantic, release, or script-family work unless the refreshed rerun proves
  the blocker has moved again.

## Interface Freeze Gates

- [ ] IF-0-SEMCODEXLOOPREBOUNDTAIL-1 - Exact rebound advance contract:
      a refreshed repo-local force-full rerun on the post-SEMQUERYFULLTAIL
      head no longer terminalizes with the durable lexical trace centered on
      `.codex/phase-loop/runs/20260424T190651Z-01-garc-plan/launch.json ->
      .codex/phase-loop/runs/20260427T075236Z-05-idxsafe-repair/terminal-summary.json`;
      it either advances durably beyond that exact later pair or emits a
      truthful newer blocker before the 120-second watchdog expires.
- [ ] IF-0-SEMCODEXLOOPREBOUNDTAIL-2 - Boundary-preservation contract:
      any repair introduced by this phase remains limited to the exact later
      rebound pair and the immediate dispatcher, trace, CLI, evidence, and
      roadmap-steering plumbing needed to clear it. The phase must not reopen
      the repaired
      `scripts/run_comprehensive_query_test.py ->
      scripts/index_all_repos_semantic_full.py`
      seam or broaden into a blanket `.codex/**` or `.phase-loop/**` bypass.
- [ ] IF-0-SEMCODEXLOOPREBOUNDTAIL-3 - Authority-split contract:
      canonical `.phase-loop/` remains authoritative runner state, and any
      legacy `.codex/phase-loop/` treatment stays compatibility-only. The
      phase must not route canonical `.phase-loop/state.json` or
      `.phase-loop/events.jsonl` through the same rebound fast path.
- [ ] IF-0-SEMCODEXLOOPREBOUNDTAIL-4 - Lexical discoverability contract:
      the later legacy rebound pair remains lexically discoverable with
      durable file storage and bounded content discoverability for checked-in
      runtime keys and phrases such as `command`, `phase`, `artifact_paths`,
      `terminal_status`, `next_action`, `current_phase`, and
      `.codex/phase-loop`; the repair must not clear the seam by turning the
      pair into an indexing blind spot.
- [ ] IF-0-SEMCODEXLOOPREBOUNDTAIL-5 - Durable trace and operator contract:
      `force_full_exit_trace.json`, `GitAwareIndexManager`, and
      `uv run mcp-index repository status` stay aligned with the repaired
      later rebound outcome, preserve the generic legacy boundary line when it
      is still true, and do not leave stale blame on the later
      `.codex/phase-loop` pair after lexical progress has already moved on.
- [ ] IF-0-SEMCODEXLOOPREBOUNDTAIL-6 - Evidence and downstream steering
      contract: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMQUERYFULLTAIL rerun outcome and the final authoritative verdict for
      the later rebound pair, and if execution exposes a blocker beyond the
      current roadmap tail, `specs/phase-plans-v7.md` is amended before
      closeout so `.phase-loop/` points to the newest truthful next phase.

## Lane Index & Dependencies

- SL-0 - Exact later legacy rebound contract freeze; Depends on: SEMQUERYFULLTAIL; Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 - Durable trace and repository-status truth fixtures; Depends on: SL-0; Blocks: SL-2, SL-3, SL-4; Parallel-safe: no
- SL-2 - Minimal later rebound runtime repair; Depends on: SL-0, SL-1; Blocks: SL-3, SL-4; Parallel-safe: no
- SL-3 - Live rerun evidence reducer and contract refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SL-4; Parallel-safe: no
- SL-4 - Downstream roadmap steering reducer; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: SEMCODEXLOOPREBOUNDTAIL acceptance; Parallel-safe: no

Lane DAG:

```text
SEMQUERYFULLTAIL
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SL-4 -> SEMCODEXLOOPREBOUNDTAIL acceptance
```

## Lanes

### SL-0 - Exact Later Legacy Rebound Contract Freeze

- **Scope**: Freeze the exact later
  `.codex/phase-loop/runs/20260424T190651Z-01-garc-plan/launch.json ->
  .codex/phase-loop/runs/20260427T075236Z-05-idxsafe-repair/terminal-summary.json`
  rebound in deterministic dispatcher coverage so this phase proves a narrow
  repair instead of assuming the existing generic legacy matcher already makes
  the later pair safe.
- **Owned files**: `tests/test_dispatcher.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMCODEXLOOPREBOUNDTAIL-1,
  IF-0-SEMCODEXLOOPREBOUNDTAIL-2,
  IF-0-SEMCODEXLOOPREBOUNDTAIL-3, and
  IF-0-SEMCODEXLOOPREBOUNDTAIL-4 at the dispatcher boundary
- **Interfaces consumed**: existing
  `Dispatcher.index_directory(...)`,
  `GenericTreeSitterPlugin._exact_bounded_legacy_codex_phase_loop_json_reason(...)`,
  `GenericTreeSitterPlugin._exact_bounded_legacy_codex_phase_loop_jsonl_reason(...)`,
  bounded lexical persistence for the older legacy pair, and the current
  checked-in runtime-key discoverability contract
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` with repo-shaped fixtures for the
    later rebound pair
    `.codex/phase-loop/runs/20260424T190651Z-01-garc-plan/launch.json ->
    .codex/phase-loop/runs/20260427T075236Z-05-idxsafe-repair/terminal-summary.json`
    so the current dispatcher contract proves durable file rows, zero code
    chunks, and FTS-backed discoverability for that exact pair.
  - test: Keep negative guards proving the earlier SEMCODEXLOOPTAIL-era
    legacy family still passes unchanged and canonical `.phase-loop/state.json`
    remains on its normal JSON/plugin path.
  - test: Assert that the later pair still exposes checked-in runtime keys and
    phrases such as `command`, `phase`, `artifact_paths`, `terminal_status`,
    `next_action`, `current_phase`, and `.codex/phase-loop` rather than
    becoming a silent blind spot.
  - impl: Keep fixtures deterministic with repo-local JSON strings and
    bounded-path assertions rather than multi-minute live waits.
  - impl: Keep this lane on contract freeze only. Do not mutate dispatcher
    implementation, durable trace logic, CLI wording, evidence docs, or
    roadmap steering here.
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "garc or idxsafe or legacy_codex_phase_loop or terminal_summary or launch or bounded or phase_loop"`

### SL-1 - Durable Trace And Repository-Status Truth Fixtures

- **Scope**: Freeze the later rebound pair at the durable trace and operator
  surface so execution can distinguish a real runtime repair from a report
  that still blames the later pair after lexical progress has already moved
  on.
- **Owned files**: `tests/test_git_index_manager.py`, `tests/test_repository_commands.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMCODEXLOOPREBOUNDTAIL-1,
  IF-0-SEMCODEXLOOPREBOUNDTAIL-3, and
  IF-0-SEMCODEXLOOPREBOUNDTAIL-5
- **Interfaces consumed**: existing durable trace lifecycle in
  `GitAwareIndexManager`; repository-status interrupted/stale-running output;
  `_print_legacy_codex_phase_loop_boundary(...)`; and the current later-pair
  evidence from `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- **Parallel-safe**: no
- **Tasks**:
  - test: Add or extend `tests/test_git_index_manager.py` coverage so a
    lexical rerun that has already advanced beyond the SEMQUERYFULLTAIL script
    seam can still surface the later
    `.codex/phase-loop/.../launch.json ->
    .codex/phase-loop/.../terminal-summary.json`
    pair truthfully, then promote a later blocker or closeout status when the
    rebound pair has been cleared.
  - test: Extend `tests/test_repository_commands.py` so `repository status`
    continues to print the generic legacy boundary line when the compatibility
    runtime family is present, but its interrupted/stale-running trace output
    can be frozen against the later rebound pair rather than only the older
    SEMCODEXLOOPTAIL-era examples.
  - test: Keep negative guards that canonical `.phase-loop` authority wording
    remains intact and that the repaired
    `scripts/run_comprehensive_query_test.py ->
    scripts/index_all_repos_semantic_full.py`
    boundary does not regress into the active blocker once the later rebound
    fixture is introduced.
  - impl: Model closeout and successor promotion with synthetic trace payloads
    or monkeypatched manager behavior rather than live `sync --force-full`
    execution inside unit tests.
  - impl: Keep this lane fixture-only. Do not update production trace logic,
    CLI code, docs, or roadmap steering here.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "garc or idxsafe or legacy_codex_phase_loop or interrupted or boundary or closeout_handoff or phase_loop"`

### SL-2 - Minimal Later Rebound Runtime Repair

- **Scope**: Implement the smallest dispatcher or closeout-trace or
  repository-status repair needed so the current-head force-full rerun no
  longer leaves the later rebound pair as the active lexical watchdog tail.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `mcp_server/storage/git_index_manager.py`, `mcp_server/cli/repository_commands.py`
- **Interfaces provided**: IF-0-SEMCODEXLOOPREBOUNDTAIL-1 exact rebound
  advance contract; IF-0-SEMCODEXLOOPREBOUNDTAIL-2
  boundary-preservation contract; IF-0-SEMCODEXLOOPREBOUNDTAIL-3
  authority-split contract; IF-0-SEMCODEXLOOPREBOUNDTAIL-5 durable trace and
  operator contract
- **Interfaces consumed**: SL-0 dispatcher fixtures; SL-1 durable
  trace/status fixtures; existing generic legacy compatibility-runtime matcher
  in `GenericTreeSitterPlugin`; current lexical timeout handling in
  `dispatcher_enhanced.py`; and the current generic legacy boundary wording in
  `repository_commands.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 and SL-1 slices first and confirm whether the active
    defect is still dispatcher-side lexical progression, durable
    closeout-handoff promotion, or CLI trace reporting after the later pair is
    already bounded.
  - impl: Prefer the smallest repair surface that matches the frozen tests and
    live evidence. Acceptable outcomes include a dispatcher-side promotion fix,
    a `GitAwareIndexManager` closeout-trace correction, or a repository-status
    truth repair that stops stale blame on the later pair once progress has
    already moved on.
  - impl: Treat `GenericTreeSitterPlugin` as pre-existing unless the tests
    prove the later pair still misses the family-wide exact bounded matcher.
    Do not reopen that plugin surface speculatively.
  - impl: Preserve the generic legacy boundary line and canonical
    `.phase-loop` authority split. Do not broaden to blanket `.codex/**` or
    `.phase-loop/**` handling and do not regress the repaired
    `scripts/run_comprehensive_query_test.py ->
    scripts/index_all_repos_semantic_full.py`
    seam.
  - impl: If the repair moves the live tail beyond the later rebound pair,
    ensure the durable trace and operator surface promote the newer blocker or
    closeout stage truthfully instead of leaving stale `last_progress_path` or
    `in_flight_path` blame on the later pair.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "garc or idxsafe or legacy_codex_phase_loop or interrupted or boundary or closeout_handoff or phase_loop"`

### SL-3 - Live Rerun Evidence Reducer And Contract Refresh

- **Scope**: Re-run the bounded repo-local force-full command after SL-2,
  capture the authoritative later-pair outcome, and refresh the dogfood report
  plus its contract test without widening into unrelated semantic claims.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: IF-0-SEMCODEXLOOPREBOUNDTAIL-1 exact rebound
  advance contract; IF-0-SEMCODEXLOOPREBOUNDTAIL-5 durable trace and operator
  contract; IF-0-SEMCODEXLOOPREBOUNDTAIL-6 evidence contract
- **Interfaces consumed**: SL-2 runtime repair; live outputs from
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`,
  `uv run mcp-index repository status`, and
  `.mcp-index/force_full_exit_trace.json`; plus the existing SEMQUERYFULLTAIL
  evidence block
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/docs/test_semdogfood_evidence_contract.py` so the
    report must include a `## SEMCODEXLOOPREBOUNDTAIL Live Rerun Check` block,
    cite the SEMQUERYFULLTAIL prior plan and rerun outcome, and record the
    exact later rebound pair or its truthful successor.
  - impl: Run the refreshed repo-local force-full rerun after SL-2 using the
    same bounded command from the roadmap evidence, then capture
    `repository status`, `force_full_exit_trace.json`, and SQLite row counts
    on the same head.
  - impl: Update `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` with the final
    authoritative verdict for the later rebound pair, explicitly naming
    whether the rerun advanced beyond it, terminalized truthfully on it again,
    or exposed a later blocker.
  - impl: Keep the evidence block semantically fail-closed. Preserve
    readiness, rollout-status, last-sync-error, and semantic-readiness lines
    unless the live probes on the same head prove they changed.
  - impl: If the rerun advances beyond the later pair, state clearly that the
    SEMQUERYFULLTAIL-era script seam stays closed and that the current blocker
    has moved later.
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "SEMQUERYFULLTAIL or SEMCODEXLOOPREBOUNDTAIL or phase_loop or garc or idxsafe"`

### SL-4 - Downstream Roadmap Steering Reducer

- **Scope**: Keep the roadmap truthful after the refreshed rerun by only
  adding a downstream phase when SL-3 proves the active blocker moved beyond
  the current roadmap tail.
- **Owned files**: `specs/phase-plans-v7.md`
- **Interfaces provided**: the downstream-steering portion of
  IF-0-SEMCODEXLOOPREBOUNDTAIL-6
- **Interfaces consumed**: SL-3 refreshed evidence verdict; current roadmap
  DAG and tail ordering for `specs/phase-plans-v7.md`; and canonical
  `.phase-loop/` expectations that the next unplanned phase reflect the latest
  durable blocker rather than stale rebound assumptions
- **Parallel-safe**: no
- **Tasks**:
  - test: Re-read the post-SL-3 evidence and confirm whether the repaired
    rerun actually exposes a newer blocker beyond the current roadmap tail
    before mutating roadmap steering.
  - impl: If the active blocker remains inside the current later rebound pair
    or the rerun completes lexical closeout without exposing a new tail, leave
    the roadmap unchanged.
  - impl: If the rerun advances beyond the current roadmap tail and no
    downstream phase already covers the new blocker, append the nearest
    truthful downstream recovery phase to `specs/phase-plans-v7.md` with the
    same evidence-first structure used by the current SEM* lexical-recovery
    chain.
  - impl: Keep any roadmap mutation limited to the newly exposed blocker. Do
    not rewrite earlier phases or reopen SEMQUERYFULLTAIL assumptions while
    closing this rebound seam.
  - verify: `git diff -- specs/phase-plans-v7.md`

## Verification

Planning-only run: do not execute these during plan creation. Run them during
`codex-execute-phase` or manual SEMCODEXLOOPREBOUNDTAIL execution.

Lane-specific checks:

```bash
uv run pytest tests/test_dispatcher.py -q --no-cov -k "garc or idxsafe or legacy_codex_phase_loop or terminal_summary or launch or bounded or phase_loop"
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "garc or idxsafe or legacy_codex_phase_loop or interrupted or boundary or closeout_handoff or phase_loop"
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "SEMQUERYFULLTAIL or SEMCODEXLOOPREBOUNDTAIL or phase_loop or garc or idxsafe"
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
  -q --no-cov -k "garc or idxsafe or legacy_codex_phase_loop or interrupted or boundary or closeout_handoff or phase_loop"
timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
sed -n '1,240p' .mcp-index/force_full_exit_trace.json
git status --short -- plans/phase-plan-v7-SEMCODEXLOOPREBOUNDTAIL.md docs/status/SEMANTIC_DOGFOOD_REBUILD.md specs/phase-plans-v7.md
git diff --check
git diff --cached --check
```

## Acceptance Criteria

- [ ] A refreshed repo-local force-full rerun on the post-SEMQUERYFULLTAIL
      head either advances durably beyond the later
      `.codex/phase-loop/runs/20260424T190651Z-01-garc-plan/launch.json ->
      .codex/phase-loop/runs/20260427T075236Z-05-idxsafe-repair/terminal-summary.json`
      pair or emits a truthful newer blocker before the 120-second watchdog
      expires.
- [ ] The chosen repair for the later rebound pair stays narrow, tested, and
      does not reopen the repaired
      `scripts/run_comprehensive_query_test.py ->
      scripts/index_all_repos_semantic_full.py`
      seam without direct evidence.
- [ ] Canonical `.phase-loop/` remains authoritative runner state, and the
      repair does not route canonical `.phase-loop/state.json` or
      `.phase-loop/events.jsonl` through the same legacy compatibility path.
- [ ] The later rebound pair remains lexically discoverable with durable file
      storage and bounded content discoverability for checked-in runtime keys
      and phrases such as `command`, `phase`, `artifact_paths`,
      `terminal_status`, `next_action`, `current_phase`, and
      `.codex/phase-loop`.
- [ ] `force_full_exit_trace.json` and
      `uv run mcp-index repository status` stay aligned with the repaired
      later rebound outcome and do not leave stale blame on the later
      `.codex/phase-loop` pair after progress has already moved beyond it.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMQUERYFULLTAIL rerun outcome and the final live verdict for the later
      rebound pair.
- [ ] If execution reveals a newer blocker beyond the current roadmap tail,
      `specs/phase-plans-v7.md` is updated before closeout so the next
      phase-loop step stays truthful.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMCODEXLOOPREBOUNDTAIL.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMCODEXLOOPREBOUNDTAIL.md
  artifact_state: staged
```
