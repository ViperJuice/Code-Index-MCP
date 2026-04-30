---
phase_loop_plan_version: 1
phase: SEMSWIFTDBEFFTAIL
roadmap: specs/phase-plans-v7.md
roadmap_sha256: 79c1620c82f1a3d7b0661ac1cb1bfe947bb1c144d23adedf37d27d7c37a5d01f
---
# SEMSWIFTDBEFFTAIL: Swift Plugin / MCP Database Efficiency Tail Recovery

## Context

SEMSWIFTDBEFFTAIL is the phase-83 follow-up for the v7 semantic hardening
roadmap. Canonical `.phase-loop/` runtime exists in this checkout, so it is
the authoritative runner state for this planning run. The current canonical
snapshots agree cleanly: `.phase-loop/state.json` and
`.phase-loop/tui-handoff.md` both report `current_phase = SEMSWIFTDBEFFTAIL`,
`SEMCODEXLOOPRELAPSETAIL = complete`, `SEMSWIFTDBEFFTAIL = unplanned`, a clean
worktree before this artifact write, and the required roadmap hash
`79c1620c82f1a3d7b0661ac1cb1bfe947bb1c144d23adedf37d27d7c37a5d01f`. Legacy
`.codex/phase-loop/` artifacts remain compatibility-only and do not supersede
canonical `.phase-loop/` state here.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is the active roadmap, it is tracked and clean in
  this worktree, and `sha256sum specs/phase-plans-v7.md` matches the
  user-required
  `79c1620c82f1a3d7b0661ac1cb1bfe947bb1c144d23adedf37d27d7c37a5d01f`.
- The checkout is on `main...origin/main [ahead 161]` at `HEAD`
  `68f4a03788cc960e06a897e71295ee02e1cf9df9`, the worktree is clean before
  this artifact write, and
  `plans/phase-plan-v7-SEMSWIFTDBEFFTAIL.md` did not exist before this run.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is the active evidence anchor.
  Its `SEMCODEXLOOPRELAPSETAIL Live Rerun Check` block records that the
  refreshed repo-local command
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  advanced durably beyond the cleared legacy compatibility-runtime pair and
  later terminalized on the exact root-test seam
  `tests/root_tests/test_swift_plugin.py ->
  tests/root_tests/test_mcp_database_efficiency.py`.
- That same evidence block records the current blocker shape this phase must
  clear or truthfully supersede: at `2026-04-30T02:13:36Z`,
  `.mcp-index/force_full_exit_trace.json` showed `status: running`,
  `stage: lexical_walking`,
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/tests/root_tests/test_swift_plugin.py`,
  and
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/tests/root_tests/test_mcp_database_efficiency.py`.
  At `2026-04-30T02:14:12Z`, a refreshed `repository status` terminalized the
  rerun to `Trace status: interrupted` while preserving the same durable
  blocker pair.
- `repository status` on the same head remained semantically fail-closed after
  the rerun: `Readiness: stale_commit`,
  `Rollout status: partial_index_failure`,
  `Last sync error: disk I/O error`, and
  `Semantic readiness: summaries_missing`. SQLite runtime counts also remained
  `files = 1064`, `code_chunks = 13095`, `chunk_summaries = 0`, and
  `semantic_points = 0`, so this remains a lexical tail rather than a
  semantic-vector recovery slice.
- `mcp_server/dispatcher/dispatcher_enhanced.py` already carries exact bounded
  Python entries for the earlier root-test blocker
  `tests/root_tests/run_reranking_tests.py` and many later SEM* recovery
  surfaces, but repo search shows no exact bounded entry yet for
  `tests/root_tests/test_swift_plugin.py` or
  `tests/root_tests/test_mcp_database_efficiency.py`.
- `mcp_server/cli/repository_commands.py` already prints a root-test boundary
  line for `tests/root_tests/run_reranking_tests.py`, but it does not yet
  advertise an exact bounded boundary for
  `tests/root_tests/test_swift_plugin.py ->
  tests/root_tests/test_mcp_database_efficiency.py`.
- `tests/test_dispatcher.py` already freezes the earlier root-test exact
  bounded path for `tests/root_tests/run_reranking_tests.py` and the later
  lexical-pair snapshot
  `tests/root_tests/test_voyage_api.py ->
  tests/root_tests/run_reranking_tests.py`, but repo search shows no current
  bounded-path coverage yet for the Swift/database-efficiency pair.
- `tests/test_git_index_manager.py` and `tests/test_repository_commands.py`
  already freeze the earlier root-test blocker
  `tests/root_tests/test_voyage_api.py ->
  tests/root_tests/run_reranking_tests.py`, but repo search shows no durable
  trace or operator-output fixtures yet for
  `tests/root_tests/test_swift_plugin.py ->
  tests/root_tests/test_mcp_database_efficiency.py`.
- `tests/docs/test_semdogfood_evidence_contract.py` and
  `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` already mention the downstream
  phase name `SEMSWIFTDBEFFTAIL`, the exact root-test seam, and the
  requirement to refresh evidence once this blocker is executed.
- The current checked-in root tests are large enough to justify an
  exact-bounded-path-first repair strategy before source edits:
  `tests/root_tests/test_swift_plugin.py` exposes
  `test_swift_plugin_basic` and `test_swift_package_analysis` over a long
  embedded Swift fixture;
  `tests/root_tests/test_mcp_database_efficiency.py` exposes
  `DatabaseEfficiencyTester` and `main` over SQLite/WAL/batching/index
  optimization exercises that reference `SQLiteStore`.

Practical planning boundary:

- SEMSWIFTDBEFFTAIL should prefer exact bounded-path handling, durable trace
  truth, and repository-status boundary updates before mutating the root-test
  sources themselves.
- Execution may expand into
  `tests/root_tests/test_swift_plugin.py` and
  `tests/root_tests/test_mcp_database_efficiency.py` only if SL-0 and SL-1
  prove the active watchdog cost remains file-local after the dispatcher and
  operator boundary plumbing is repaired.
- SEMSWIFTDBEFFTAIL must stay narrow and evidence-driven. It must not reopen
  the cleared legacy `.codex/phase-loop` compatibility-runtime relapse or the
  earlier
  `tests/root_tests/test_voyage_api.py ->
  tests/root_tests/run_reranking_tests.py`
  seam without direct evidence, and it must not widen into unrelated
  semantic-stage, integration-test, or release work unless the refreshed
  rerun proves the blocker has moved again.

## Interface Freeze Gates

- [ ] IF-0-SEMSWIFTDBEFFTAIL-1 - Exact root-test advance contract:
      a refreshed repo-local force-full rerun on the
      post-SEMCODEXLOOPRELAPSETAIL head no longer terminalizes with the
      durable blocker centered on
      `tests/root_tests/test_swift_plugin.py ->
      tests/root_tests/test_mcp_database_efficiency.py`; it either advances
      durably beyond that exact pair or emits a truthful newer blocker before
      the 120-second watchdog expires.
- [ ] IF-0-SEMSWIFTDBEFFTAIL-2 - Narrow repair contract:
      any repair introduced by this phase remains limited to the exact
      root-test pair plus the immediate dispatcher, trace, status, evidence,
      and roadmap-steering plumbing needed to clear it. The phase must not
      reopen the cleared legacy `.codex/phase-loop` compatibility-runtime
      relapse or the earlier
      `tests/root_tests/test_voyage_api.py ->
      tests/root_tests/run_reranking_tests.py`
      seam without direct evidence.
- [ ] IF-0-SEMSWIFTDBEFFTAIL-3 - Lexical discoverability contract:
      both exact root-test files remain lexically discoverable with durable
      file storage plus stable symbol/text discoverability for the current
      checked-in surfaces `test_swift_plugin_basic`,
      `test_swift_package_analysis`,
      `DatabaseEfficiencyTester`, and `main` instead of turning either file
      into an indexing blind spot.
- [ ] IF-0-SEMSWIFTDBEFFTAIL-4 - Durable trace and operator contract:
      `force_full_exit_trace.json`, `GitAwareIndexManager`, and
      `uv run mcp-index repository status` stay aligned with the repaired
      root-test outcome and do not leave stale blame on the cleared legacy
      `.codex/phase-loop` relapse or the older
      `test_voyage_api -> run_reranking_tests`
      seam once lexical progress has moved later.
- [ ] IF-0-SEMSWIFTDBEFFTAIL-5 - Evidence contract:
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMCODEXLOOPRELAPSETAIL rerun outcome, adds a dedicated
      `SEMSWIFTDBEFFTAIL` live-rerun block, and captures the final
      authoritative verdict for the Swift/database-efficiency seam plus any
      newer blocker.
- [ ] IF-0-SEMSWIFTDBEFFTAIL-6 - Downstream steering contract:
      if execution exposes a blocker beyond the current roadmap tail,
      `specs/phase-plans-v7.md` is amended before closeout so phase-loop
      points to the newest truthful next phase instead of stale
      SEMSWIFTDBEFFTAIL assumptions.

## Lane Index & Dependencies

- SL-0 - Exact Swift/database-efficiency root-test contract freeze; Depends on: SEMCODEXLOOPRELAPSETAIL; Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 - Durable trace and repository-status root-test fixtures; Depends on: SL-0; Blocks: SL-2, SL-3, SL-4; Parallel-safe: no
- SL-2 - Minimal root-test seam repair; Depends on: SL-0, SL-1; Blocks: SL-3, SL-4; Parallel-safe: no
- SL-3 - Live rerun evidence reducer and contract refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SL-4; Parallel-safe: no
- SL-4 - Downstream roadmap steering reducer; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: SEMSWIFTDBEFFTAIL acceptance; Parallel-safe: no

Lane DAG:

```text
SEMCODEXLOOPRELAPSETAIL
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SL-4 -> SEMSWIFTDBEFFTAIL acceptance
```

## Lanes

### SL-0 - Exact Swift/Database-Efficiency Root-Test Contract Freeze

- **Scope**: Freeze the exact
  `tests/root_tests/test_swift_plugin.py ->
  tests/root_tests/test_mcp_database_efficiency.py`
  seam in deterministic dispatcher coverage so execution proves a narrow
  bounded repair instead of assuming the older root-test fixtures already make
  the later pair safe.
- **Owned files**: `tests/test_dispatcher.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMSWIFTDBEFFTAIL-1,
  IF-0-SEMSWIFTDBEFFTAIL-2, and
  IF-0-SEMSWIFTDBEFFTAIL-3 at the dispatcher boundary
- **Interfaces consumed**: existing
  `Dispatcher.index_directory(...)`,
  `_EXACT_BOUNDED_PYTHON_PATHS`,
  durable file metadata storage, and the earlier dispatcher fixtures for
  `tests/root_tests/run_reranking_tests.py` and
  `tests/root_tests/test_voyage_api.py ->
  tests/root_tests/run_reranking_tests.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` with repo-shaped fixtures for the
    exact Swift/database-efficiency pair so the dispatcher contract proves
    durable file rows, zero code chunks where bounded indexing is applied, and
    FTS-backed discoverability for both files.
  - test: Assert that the pair remains textually discoverable for
    `test_swift_plugin_basic`,
    `test_swift_package_analysis`,
    `DatabaseEfficiencyTester`, and `main`.
  - test: Keep negative guards proving the older root-test seams and unrelated
    SEM* bounded surfaces do not silently become the reported active blocker
    once the later pair fixtures are introduced.
  - impl: Keep fixtures deterministic with repo-local Python strings rather
    than live `sync --force-full` waits.
  - impl: Keep this lane on contract freeze only. Do not mutate dispatcher
    implementation, durable trace logic, CLI wording, docs, roadmap steering,
    or the checked-in root-test sources here.
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "swift_plugin or database_efficiency or root_test or lexical or bounded"`

### SL-1 - Durable Trace And Repository-Status Root-Test Fixtures

- **Scope**: Freeze the Swift/database-efficiency pair at the durable trace
  and operator surface so execution can distinguish a real runtime repair from
  a report that still blames the older root-test seam or the cleared legacy
  `.codex/phase-loop` relapse after lexical progress has already moved later.
- **Owned files**: `tests/test_git_index_manager.py`, `tests/test_repository_commands.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMSWIFTDBEFFTAIL-1,
  IF-0-SEMSWIFTDBEFFTAIL-2, and
  IF-0-SEMSWIFTDBEFFTAIL-4
- **Interfaces consumed**: existing durable trace lifecycle in
  `GitAwareIndexManager`; repository-status interrupted and stale-running
  output; the existing root-test boundary print helpers in
  `mcp_server/cli/repository_commands.py`; and the current SEMCODEXLOOPRELAPSETAIL
  evidence block in `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_git_index_manager.py` so running and interrupted
    force-full traces can preserve the exact pair
    `tests/root_tests/test_swift_plugin.py ->
    tests/root_tests/test_mcp_database_efficiency.py`,
    then promote a later blocker or closeout state once the pair has truly
    been cleared.
  - test: Extend `tests/test_repository_commands.py` so
    `repository status` reports the interrupted trace against the exact
    Swift/database-efficiency pair and advertises a dedicated exact bounded
    boundary line for that pair when both files are present.
  - test: Keep negative guards proving the older
    `tests/root_tests/test_voyage_api.py ->
    tests/root_tests/run_reranking_tests.py`
    seam and the cleared legacy `.codex/phase-loop` relapse do not remain the
    reported active blocker once the current pair fixtures are introduced.
  - impl: Model closeout and successor promotion with synthetic trace payloads
    or monkeypatched manager behavior rather than live `sync --force-full`
    execution inside unit tests.
  - impl: Keep this lane fixture-only. Do not update production dispatcher
    code, root-test sources, evidence docs, or roadmap steering here.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "swift_plugin or database_efficiency or root_test or interrupted or boundary or closeout_handoff"`

### SL-2 - Minimal Root-Test Seam Repair

- **Scope**: Implement the smallest production repair needed so the live
  lexical walker no longer burns its watchdog budget on the exact
  `tests/root_tests/test_swift_plugin.py ->
  tests/root_tests/test_mcp_database_efficiency.py`
  pair.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `mcp_server/cli/repository_commands.py`, `mcp_server/storage/git_index_manager.py`, `tests/root_tests/test_swift_plugin.py`, `tests/root_tests/test_mcp_database_efficiency.py`
- **Interfaces provided**: IF-0-SEMSWIFTDBEFFTAIL-1 exact advance contract;
  IF-0-SEMSWIFTDBEFFTAIL-2 narrow repair contract;
  IF-0-SEMSWIFTDBEFFTAIL-3 lexical discoverability contract; and
  IF-0-SEMSWIFTDBEFFTAIL-4 durable trace/operator contract
- **Interfaces consumed**: SL-0 dispatcher fixtures; SL-1 trace/status
  fixtures; existing `_EXACT_BOUNDED_PYTHON_PATHS`; repository-status lexical
  boundary printers; and the current structure of the two checked-in root-test
  files
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 and SL-1 slices first and confirm whether the active
    cost is cleared by exact bounded-path handling plus truthful operator
    boundary output, or whether the live hotspot remains file-local.
  - impl: Prefer the narrow production repair first:
    add exact bounded-path handling for one or both root-test files in
    `mcp_server/dispatcher/dispatcher_enhanced.py` and add a dedicated
    repository-status boundary printer in
    `mcp_server/cli/repository_commands.py` for
    `tests/root_tests/test_swift_plugin.py ->
    tests/root_tests/test_mcp_database_efficiency.py`.
  - impl: If the fixture evidence shows stale durable-trace promotion even
    after bounded-path handling is in place, patch
    `mcp_server/storage/git_index_manager.py` minimally so interrupted and
    closeout traces preserve the truthful current blocker or successor.
  - impl: Only edit
    `tests/root_tests/test_swift_plugin.py` or
    `tests/root_tests/test_mcp_database_efficiency.py`
    if the bounded-path and trace/status repair still leaves the live watchdog
    stuck on file-local structure. Preserve behavioral intent and stable symbol
    names if a root-test edit becomes necessary.
  - impl: Do not reopen the cleared legacy `.codex/phase-loop` relapse or the
    older `test_voyage_api -> run_reranking_tests` seam while closing this
    later blocker.
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "swift_plugin or database_efficiency or root_test or lexical or bounded"`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "swift_plugin or database_efficiency or root_test or interrupted or boundary or closeout_handoff"`

### SL-3 - Live Rerun Evidence Reducer And Contract Refresh

- **Scope**: Refresh the semantic dogfood evidence so the current-head rerun
  verdict for the Swift/database-efficiency seam is durable, reviewable, and
  ready to steer the next downstream phase honestly.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: IF-0-SEMSWIFTDBEFFTAIL-5 evidence contract
- **Interfaces consumed**: SL-0 dispatcher verdict; SL-1 trace/status verdict;
  SL-2 production repair result; current evidence lineage in
  `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`; and the phase-chain assertions in
  `tests/docs/test_semdogfood_evidence_contract.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/docs/test_semdogfood_evidence_contract.py` so the
    evidence artifact must mention the SEMCODEXLOOPRELAPSETAIL rerun outcome,
    the exact Swift/database-efficiency pair, the final authoritative verdict
    for this phase, and any downstream steering if the blocker moves again.
  - impl: Update `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` with a dedicated
    `SEMSWIFTDBEFFTAIL Live Rerun Check` section that records observed commit,
    rerun command, timestamps, trace snapshot, repository-status output,
    SQLite counts, and the verdict on whether the exact pair is cleared or
    still active.
  - impl: Preserve the current evidence lineage. Do not create a new docs
    status file or split the semantic dogfood report by phase.
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "SEMCODEXLOOPRELAPSETAIL or SEMSWIFTDBEFFTAIL or swift_plugin or database_efficiency"`
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
  IF-0-SEMSWIFTDBEFFTAIL-6
- **Interfaces consumed**: SL-3 refreshed evidence verdict; current roadmap
  DAG and tail ordering for `specs/phase-plans-v7.md`; and canonical
  `.phase-loop/` expectations that the next unplanned phase reflect the latest
  durable blocker rather than stale SEMSWIFTDBEFFTAIL assumptions
- **Parallel-safe**: no
- **Tasks**:
  - test: Re-read the post-SL-3 evidence and confirm whether the repaired
    rerun actually exposes a newer blocker beyond the current roadmap tail
    before mutating roadmap steering.
  - impl: If the active blocker remains inside the current Swift/database-efficiency
    pair or the rerun completes lexical closeout without exposing a new tail,
    leave the roadmap unchanged.
  - impl: If the rerun advances beyond the current roadmap tail and no
    downstream phase already covers the new blocker, append the nearest
    truthful downstream recovery phase to `specs/phase-plans-v7.md` with the
    same evidence-first structure used by the current SEM* lexical-recovery
    chain.
  - impl: Keep any roadmap mutation limited to the newly exposed blocker. Do
    not rewrite earlier phases or reopen SEMCODEXLOOPRELAPSETAIL assumptions
    while closing this seam.
  - verify: `git diff -- specs/phase-plans-v7.md`

## Verification

Planning-only run: do not execute these during plan creation. Run them during
`codex-execute-phase` or manual SEMSWIFTDBEFFTAIL execution.

Lane-specific checks:

```bash
uv run pytest tests/test_dispatcher.py -q --no-cov -k "swift_plugin or database_efficiency or root_test or lexical or bounded"
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "swift_plugin or database_efficiency or root_test or interrupted or boundary or closeout_handoff"
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "SEMCODEXLOOPRELAPSETAIL or SEMSWIFTDBEFFTAIL or swift_plugin or database_efficiency"
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
  -q --no-cov -k "swift_plugin or database_efficiency or root_test or interrupted or boundary or closeout_handoff or lexical or bounded"
timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
sed -n '1,240p' .mcp-index/force_full_exit_trace.json
git status --short -- plans/phase-plan-v7-SEMSWIFTDBEFFTAIL.md docs/status/SEMANTIC_DOGFOOD_REBUILD.md specs/phase-plans-v7.md
git diff --check
git diff --cached --check
```

## Acceptance Criteria

- [ ] A refreshed repo-local force-full rerun on the
      post-SEMCODEXLOOPRELAPSETAIL head either advances durably beyond the
      later
      `tests/root_tests/test_swift_plugin.py ->
      tests/root_tests/test_mcp_database_efficiency.py`
      pair or emits a truthful newer blocker before the 120-second watchdog
      expires.
- [ ] Any repair chosen for the Swift/database-efficiency seam stays narrow,
      tested, and does not reopen the cleared legacy `.codex/phase-loop`
      compatibility-runtime relapse or the older
      `tests/root_tests/test_voyage_api.py ->
      tests/root_tests/run_reranking_tests.py`
      boundary without direct evidence.
- [ ] Both exact root-test files remain lexically discoverable with durable
      file storage and stable symbol/text discoverability for
      `test_swift_plugin_basic`,
      `test_swift_package_analysis`,
      `DatabaseEfficiencyTester`, and `main`.
- [ ] `force_full_exit_trace.json` and
      `uv run mcp-index repository status` stay aligned with the repaired
      root-test outcome and do not leave stale blame on the cleared legacy
      `.codex/phase-loop` relapse or the older root-test seam after progress
      has already moved beyond them.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMCODEXLOOPRELAPSETAIL rerun outcome and the final live verdict for the
      Swift/database-efficiency seam.
- [ ] If execution reveals a newer blocker beyond the current roadmap tail,
      `specs/phase-plans-v7.md` is updated before closeout so the next
      phase-loop step stays truthful.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMSWIFTDBEFFTAIL.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMSWIFTDBEFFTAIL.md
  artifact_state: staged
```
