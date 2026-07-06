---
phase_loop_plan_version: 1
phase: SEMGARELTAIL
roadmap: specs/phase-plans-v7.md
roadmap_sha256: 3fa28450d46e4f591f254140610f68d3a1b5e4de89069ede148704d73e43e32c
---
# SEMGARELTAIL: GA Release Docs Tail Recovery

## Context

SEMGARELTAIL is the phase-61 follow-up for the v7 semantic hardening roadmap.
Canonical `.phase-loop/` state is authoritative for this run:
`.phase-loop/state.json` and `.phase-loop/tui-handoff.md` both mark
`SEMGARELTAIL` as the current `unplanned` phase after
`SEMDOCCONTRACTTAIL` completed and the phase loop advanced to the next
downstream blocker on `HEAD` `07a8bca2dce1aa0b71a28263cfbd9706ece28e6c`
with `main...origin/main [ahead 117]`, no dirty paths, and roadmap
`specs/phase-plans-v7.md`. Legacy `.codex/phase-loop/` artifacts remain
compatibility-only and do not supersede canonical `.phase-loop/` runner state
here.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is tracked and clean in this worktree, and
  `sha256sum specs/phase-plans-v7.md` matches the required
  `3fa28450d46e4f591f254140610f68d3a1b5e4de89069ede148704d73e43e32c`.
- The target artifact `plans/phase-plan-v7-SEMGARELTAIL.md` did not exist
  before this planning run.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is the active evidence anchor.
  Its SEMDOCCONTRACTTAIL rerun block records the current downstream lexical
  blocker precisely: the refreshed repo-local command
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  started on observed commit `2167f184`, and at `2026-04-29T19:13:08Z`
  `.mcp-index/force_full_exit_trace.json` showed
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/tests/docs/test_garc_rc_soak_contract.py`
  with
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/tests/docs/test_garel_ga_release_contract.py`;
  at `2026-04-29T19:13:19Z`, `repository status` terminalized that running
  snapshot to `Trace status: interrupted` with the same exact pair while
  still advertising the repaired earlier
  `tests/docs/test_semincr_contract.py ->
  tests/docs/test_gabase_ga_readiness_contract.py` boundary.
- The current blocker files are both Python docs-contract tests of similar
  size and surface breadth. `tests/docs/test_garc_rc_soak_contract.py` is
  `143` lines / `5017` bytes and freezes RC-soak-era release surfaces across
  `docs/validation/ga-rc-evidence.md`, `.github/workflows/release-automation.yml`,
  `CHANGELOG.md`, `README.md`, `docs/GETTING_STARTED.md`,
  `docs/MCP_CONFIGURATION.md`, `docs/DOCKER_GUIDE.md`,
  `docs/SUPPORT_MATRIX.md`, and the deployment and user-action runbooks via
  assertions such as `test_rc8_contract_surfaces_are_frozen`,
  `test_public_surfaces_preserve_rc_only_channel_posture`,
  `test_runbooks_freeze_pre_dispatch_and_observation_commands`, and
  `test_ga_rc_evidence_exists_and_records_blocked_or_observed_state`.
- `tests/docs/test_garel_ga_release_contract.py` is `129` lines / `4984`
  bytes and freezes the later GA final-decision and release-preparation
  surfaces across `docs/validation/ga-final-decision.md`,
  `docs/validation/ga-release-evidence.md`, `specs/phase-plans-v5.md`,
  `.github/workflows/release-automation.yml`, `README.md`,
  `docs/GETTING_STARTED.md`, `docs/MCP_CONFIGURATION.md`,
  `docs/DOCKER_GUIDE.md`, `docs/SUPPORT_MATRIX.md`, and both operator
  runbooks through checks such as
  `test_final_decision_exists_and_cites_all_ga_inputs`,
  `test_ship_decision_defers_release_evidence_to_gadisp_and_keeps_public_surfaces_pre_dispatch`,
  and
  `test_workflow_runtime_warning_is_remediated_before_any_future_ga_dispatch`.
- The current exact bounded-path machinery does not yet name this later GA
  release docs pair. `mcp_server/dispatcher/dispatcher_enhanced.py` already
  carries `_EXACT_BOUNDED_PYTHON_PATHS` for the earlier docs-governance pair,
  the later docs-test pair, the SEMDOCCONTRACTTAIL pair, and the mock-plugin
  fixture pair, but it does not include either
  `tests/docs/test_garc_rc_soak_contract.py` or
  `tests/docs/test_garel_ga_release_contract.py`.
- `mcp_server/plugins/python_plugin/plugin.py` currently bounds chunking for
  the repaired script seams, the earlier docs pairs, the SEMDOCCONTRACTTAIL
  pair, the mock-plugin fixtures, and `mcp_server/visualization/quick_charts.py`,
  but it does not include the current
  `test_garc_rc_soak_contract.py -> test_garel_ga_release_contract.py` seam.
- `mcp_server/cli/repository_commands.py` already advertises exact lexical
  boundary lines for the earlier docs, script, JSON, mock-plugin, and
  SEMDOCCONTRACTTAIL seams, but it has no dedicated helper yet for
  `tests/docs/test_garc_rc_soak_contract.py ->
  tests/docs/test_garel_ga_release_contract.py`.
- Existing tests are adjacent but incomplete for this seam.
  `tests/test_dispatcher.py`, `tests/test_git_index_manager.py`, and
  `tests/test_repository_commands.py` already freeze the earlier docs pairs,
  the SEMDOCCONTRACTTAIL pair, and the mock-plugin fixture recovery, while
  `tests/docs/test_semdogfood_evidence_contract.py` already expects the live
  evidence artifact to preserve the GARC/GAREL blocker pair and downstream
  steering to `SEMGARELTAIL`.

Practical planning boundary:

- SEMGARELTAIL may tighten exact GA release docs tail handling, dispatcher
  lexical progress accounting, durable trace persistence, operator status
  wording, and the semantic dogfood evidence needed to prove a live rerun
  either advances beyond
  `tests/docs/test_garc_rc_soak_contract.py ->
  tests/docs/test_garel_ga_release_contract.py` or surfaces a truthful newer
  blocker.
- SEMGARELTAIL must stay narrow and evidence-driven. It must not reopen the
  repaired SEMDOCCONTRACTTAIL seam, introduce a blanket `tests/docs/**/*.py`
  bypass, or widen into unrelated GA release documentation edits unless the
  refreshed rerun directly proves the active blocker requires them.

## Interface Freeze Gates

- [ ] IF-0-SEMGARELTAIL-1 - Later GA release docs tail advance contract: a
      refreshed repo-local force-full rerun on the post-SEMDOCCONTRACTTAIL
      head no longer terminalizes with the durable lexical trace centered on
      `tests/docs/test_garc_rc_soak_contract.py ->
      tests/docs/test_garel_ga_release_contract.py`; it either advances
      durably beyond that pair or emits a truthful newer blocker before the
      120-second watchdog expires.
- [ ] IF-0-SEMGARELTAIL-2 - Exact boundary contract: any repair introduced by
      this phase remains limited to the exact later GA release docs pair plus
      the immediate dispatcher or plugin or trace or status plumbing needed to
      clear it. The phase must not become a blanket `tests/docs/**/*.py` fast
      path and must not reopen the repaired
      `tests/docs/test_semincr_contract.py ->
      tests/docs/test_gabase_ga_readiness_contract.py` seam without direct
      evidence.
- [ ] IF-0-SEMGARELTAIL-3 - Lexical discoverability contract: both exact GA
      release docs test files remain lexically discoverable after the repair,
      including durable file-level storage plus bounded symbol or content
      discoverability for `test_rc8_contract_surfaces_are_frozen`,
      `test_runbooks_freeze_pre_dispatch_and_observation_commands`,
      `test_final_decision_exists_and_cites_all_ga_inputs`, and
      `test_workflow_runtime_warning_is_remediated_before_any_future_ga_dispatch`,
      instead of turning either file into an indexing blind spot.
- [ ] IF-0-SEMGARELTAIL-4 - Durable trace and operator contract:
      `force_full_exit_trace.json` and `uv run mcp-index repository status`
      stay aligned with the repaired outcome for the exact later GA release
      docs pair and do not regress to stale SEMDOCCONTRACTTAIL-only wording
      once the live rerun advances past it.
- [ ] IF-0-SEMGARELTAIL-5 - Evidence and downstream steering contract:
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMDOCCONTRACTTAIL rerun outcome and the final live verdict for the
      later GA release docs pair; if execution reveals a blocker beyond the
      current roadmap tail, `specs/phase-plans-v7.md` is amended before
      closeout so the next phase-loop step is truthful.

## Lane Index & Dependencies

- SL-0 - Exact GA release docs fixture freeze; Depends on: SEMDOCCONTRACTTAIL; Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 - Exact GA release docs bounded indexing repair; Depends on: SL-0; Blocks: SL-2, SL-3, SL-4; Parallel-safe: no
- SL-2 - Durable trace persistence and operator boundary alignment; Depends on: SL-0, SL-1; Blocks: SL-3, SL-4; Parallel-safe: no
- SL-3 - Live rerun evidence reducer and contract refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SL-4; Parallel-safe: no
- SL-4 - Downstream roadmap steering reducer; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: SEMGARELTAIL acceptance; Parallel-safe: no

Lane DAG:

```text
SEMDOCCONTRACTTAIL
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SL-4 -> SEMGARELTAIL acceptance
```

## Lanes

### SL-0 - Exact GA Release Docs Fixture Freeze

- **Scope**: Freeze the exact
  `tests/docs/test_garc_rc_soak_contract.py ->
  tests/docs/test_garel_ga_release_contract.py` lexical seam in deterministic
  dispatcher coverage before runtime changes so this phase proves a narrow
  repair instead of hand-waving around all GA-release docs tests.
- **Owned files**: `tests/test_dispatcher.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMGARELTAIL-1,
  IF-0-SEMGARELTAIL-2,
  and IF-0-SEMGARELTAIL-3
- **Interfaces consumed**: existing
  `Dispatcher.index_directory(...)`,
  `Dispatcher._build_exact_bounded_python_shard(...)`,
  normal Python routing through `Plugin.indexFile(...)`,
  and the SEMDOCCONTRACTTAIL evidence for the exact later GA release docs
  contract-test pair
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` with repo-shaped fixtures that
    index exact copies or trimmed representatives of
    `tests/docs/test_garc_rc_soak_contract.py` and
    `tests/docs/test_garel_ga_release_contract.py`, prove the lexical walker
    records the exact pair in order, and fail if the repair silently turns
    either file into an untracked blind spot.
  - test: In the same dispatcher coverage, assert that the GARC test remains
    symbol or content discoverable for
    `test_rc8_contract_surfaces_are_frozen` and
    `test_runbooks_freeze_pre_dispatch_and_observation_commands`, and that
    the GAREL test remains symbol or content discoverable for
    `test_final_decision_exists_and_cites_all_ga_inputs` and
    `test_workflow_runtime_warning_is_remediated_before_any_future_ga_dispatch`.
  - test: Add a negative guard that unrelated Python files outside the exact
    pair, especially the repaired SEMDOCCONTRACTTAIL pair and the cleared
    mock-plugin fixtures, still use their own existing bounded or normal
    handling. The repair must not quietly become a broader
    `tests/docs/**/*.py` fast path.
  - impl: Keep fixtures deterministic with repo-local Python strings and
    monkeypatched bounded-path instrumentation rather than long-running live
    waits inside unit tests.
  - impl: Keep this lane on contract freeze only. Do not mutate durable trace,
    CLI wording, evidence docs, or roadmap steering here.
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "garc or garel or ga_release or rc_soak or lexical or bounded"`

### SL-1 - Exact GA Release Docs Bounded Indexing Repair

- **Scope**: Implement the smallest dispatcher and Python-plugin repair needed
  so the live lexical walker no longer burns its watchdog budget on the exact
  `tests/docs/test_garc_rc_soak_contract.py ->
  tests/docs/test_garel_ga_release_contract.py` pair.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `mcp_server/plugins/python_plugin/plugin.py`
- **Interfaces provided**: IF-0-SEMGARELTAIL-2 exact boundary contract;
  IF-0-SEMGARELTAIL-3 lexical discoverability contract
- **Interfaces consumed**: SL-0 later GA release docs fixtures; existing exact
  bounded Python behavior in
  `Dispatcher._build_exact_bounded_python_shard(...)`; and the current Python
  bounded chunk rules in `Plugin._BOUNDED_CHUNK_PATHS`
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 dispatcher slice first and confirm which side of the
    pair still consumes watchdog budget in the current force-full path: the
    RC-soak release test, the later GA decision test, or the handoff between
    them.
  - impl: Apply the narrowest repair that clears the exact pair. Prefer
    exact-path bounded handling over any broad docs-test shortcut, and keep
    the repair local to the dispatcher or the relevant Python plugin path.
  - impl: Preserve content discoverability for
    `tests/docs/test_garc_rc_soak_contract.py`, including the RC-only channel
    posture assertions, pre-dispatch runbook command freeze, and
    `ga-rc-evidence.md` contract checks.
  - impl: Preserve top-level symbol or content discoverability for
    `tests/docs/test_garel_ga_release_contract.py`, including the final
    decision, deferred `ga-release-evidence.md` posture, workflow runtime
    warning remediation, and downstream `GADISP` steering assertions.
  - impl: Do not widen `_EXACT_BOUNDED_PYTHON_PATHS` or
    `Plugin._BOUNDED_CHUNK_PATHS` beyond what is needed for this exact pair,
    and do not introduce a repo-wide docs-test timeout or global plaintext
    bypass that masks later blockers.
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "garc or garel or ga_release or rc_soak or lexical or bounded"`

### SL-2 - Durable Trace Persistence And Operator Boundary Alignment

- **Scope**: Carry the exact later GA release docs repair into the durable
  force-full trace and operator status surfaces so runtime reporting
  truthfully distinguishes the cleared pair from any later blocker.
- **Owned files**: `mcp_server/storage/git_index_manager.py`, `mcp_server/cli/repository_commands.py`, `tests/test_git_index_manager.py`, `tests/test_repository_commands.py`
- **Interfaces provided**: IF-0-SEMGARELTAIL-1 later GA release docs tail
  advance contract; IF-0-SEMGARELTAIL-4 durable trace and operator contract
- **Interfaces consumed**: SL-0 fixture expectations; SL-1 repaired exact GA
  release docs bounded indexing behavior; existing
  `force_full_exit_trace.json` persistence in `GitAwareIndexManager`; and
  current operator boundary helpers in `repository_commands.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_git_index_manager.py` so durable trace fixtures
    preserve the exact
    `tests/docs/test_garc_rc_soak_contract.py ->
    tests/docs/test_garel_ga_release_contract.py` blocker when it is active
    and prove the rerun advances to a newer blocker without regressing to the
    cleared SEMDOCCONTRACTTAIL pair or the earlier mock-plugin seam.
  - test: Extend `tests/test_repository_commands.py` so `repository status`
    advertises the repaired exact bounded lexical surface for the later GA
    release docs pair and still prints the correct later
    `last_progress_path` and `in_flight_path` when the live blocker moves
    forward.
  - impl: Add the minimal `repository status` helper or wording needed to name
    the exact GA release docs pair once the repair is in place, matching the
    style already used for the earlier docs, script, JSON, and mock-plugin
    boundaries.
  - impl: Preserve truthful terminalization behavior when the live command
    times out or fails later. This lane must not relabel a later blocker as
    if the repaired GA release docs seam were still active once the rerun has
    moved on.
  - impl: Keep existing boundary wording for the SEMDOCCONTRACTTAIL pair, the
    mock-plugin fixtures, the earlier docs pairs, and the script recoveries
    intact unless the rerun directly proves one of those surfaces has
    regressed.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "garc or garel or ga_release or rc_soak or boundary or interrupted or lexical"`

### SL-3 - Live Rerun Evidence Reducer And Contract Refresh

- **Scope**: Refresh the real dogfood evidence after the GA release docs repair
  so the active blocker report matches the repaired runtime rather than stale
  SEMDOCCONTRACTTAIL assumptions.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: the evidence portion of
  IF-0-SEMGARELTAIL-5
- **Interfaces consumed**: SL-2 durable trace and repository-status output;
  live rerun command output; existing SEMDOCCONTRACTTAIL evidence block; and
  the current evidence-contract assertions in
  `tests/docs/test_semdogfood_evidence_contract.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/docs/test_semdogfood_evidence_contract.py` only as
    needed so the evidence artifact must retain the SEMDOCCONTRACTTAIL rerun
    outcome, the active SEMGARELTAIL phase name, the exact current GA release
    docs verdict, and any newly exposed downstream steering after execution.
  - impl: Run a fresh repo-local force-full rerun after SL-1 and SL-2 land,
    then capture the rerun command, observed commit, timeout or completion
    timestamp, durable trace snapshot, `repository status` output, and SQLite
    counts in `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`.
  - impl: If the repaired rerun still times out, record the exact later
    blocker pair or family that replaced the current GA release docs pair
    instead of leaving the old
    `test_garc_rc_soak_contract.py ->
    test_garel_ga_release_contract.py` pair as the active narrative.
  - impl: Keep this lane on evidence reduction. Do not back-edit older phase
    narratives except where the new rerun explicitly supersedes the active
    blocker statement.
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`

### SL-4 - Downstream Roadmap Steering Reducer

- **Scope**: Keep the roadmap and next phase-loop step truthful if the repaired
  live rerun proves a blocker beyond the current roadmap tail.
- **Owned files**: `specs/phase-plans-v7.md`
- **Interfaces provided**: the downstream-steering portion of
  IF-0-SEMGARELTAIL-5
- **Interfaces consumed**: SL-3 refreshed evidence verdict; current roadmap
  DAG and phase ordering for `specs/phase-plans-v7.md`; and canonical
  `.phase-loop/` expectations that the next unplanned phase reflects the
  latest durable blocker rather than stale SEMDOCCONTRACTTAIL assumptions
- **Parallel-safe**: no
- **Tasks**:
  - test: Re-read the post-SL-3 evidence and confirm whether the repaired
    rerun actually exposes a newer blocker beyond the current roadmap tail
    before mutating roadmap steering.
  - impl: If the active blocker remains inside the current SEMGARELTAIL GA
    release docs family or the rerun completes the lexical closeout, leave
    the roadmap unchanged.
  - impl: If the active blocker advances beyond the current roadmap tail and
    no downstream phase already covers it, append the nearest truthful
    downstream recovery phase to `specs/phase-plans-v7.md` with the same
    evidence-first structure used by the current SEM* lexical-recovery chain.
  - impl: Keep any roadmap mutation limited to the newly exposed blocker. Do
    not rewrite earlier phases or backfill unrelated sequencing while closing
    this seam.
  - verify: `git diff -- specs/phase-plans-v7.md`

## Verification

- Lane checks:
  - `uv run pytest tests/test_dispatcher.py -q --no-cov -k "garc or garel or ga_release or rc_soak or lexical or bounded"`
  - `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "garc or garel or ga_release or rc_soak or boundary or interrupted or lexical"`
  - `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
- Whole-phase checks:
  - `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_repository_commands.py tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "garc or garel or ga_release or rc_soak or lexical or bounded or boundary or interrupted"`
  - `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  - `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - `sed -n '1,240p' .mcp-index/force_full_exit_trace.json`
  - `sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'`
  - `git diff --check`
  - `git diff --cached --check`

## Acceptance Criteria

- [ ] A refreshed repo-local force-full rerun on the post-SEMDOCCONTRACTTAIL
      head either advances durably beyond the later
      `tests/docs/test_garc_rc_soak_contract.py ->
      tests/docs/test_garel_ga_release_contract.py` pair or emits a truthful
      newer blocker before the 120-second watchdog expires.
- [ ] The repair stays narrowly scoped to the exact GA release docs pair and
      the immediate dispatcher or plugin or trace or status or evidence
      plumbing needed to prove it.
- [ ] The repaired GA release docs surfaces remain lexically discoverable with
      durable file-level storage plus bounded content discoverability for the
      key GARC and GAREL contract assertions named above.
- [ ] `uv run mcp-index repository status` and
      `force_full_exit_trace.json` stay aligned with the repaired GA release
      docs outcome and do not regress to stale SEMDOCCONTRACTTAIL-only
      wording.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMDOCCONTRACTTAIL rerun outcome and the final live verdict for the
      later GA release docs pair.
- [ ] If execution reveals a newer blocker beyond the current roadmap tail,
      `specs/phase-plans-v7.md` is updated before closeout so the next
      phase-loop step is truthful.

automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMGARELTAIL.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMGARELTAIL.md
  artifact_state: staged
