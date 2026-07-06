---
phase_loop_plan_version: 1
phase: SEMSECAUTHSANDBOXTAIL
roadmap: specs/phase-plans-v7.md
roadmap_sha256: d51576564b43ebc0da0aaa9346dea8236a37c682138e018b6118e99c3593737b
---
# SEMSECAUTHSANDBOXTAIL: Security Route/Auth Sandbox Tail Recovery

## Context

SEMSECAUTHSANDBOXTAIL is the phase-84 follow-up for the v7 semantic hardening
roadmap. Canonical `.phase-loop/` runtime exists in this checkout, so it is
the authoritative runner state for this planning run. The current canonical
snapshots agree cleanly: `.phase-loop/state.json` and
`.phase-loop/tui-handoff.md` both report
`current_phase = SEMSECAUTHSANDBOXTAIL`,
`SEMSWIFTDBEFFTAIL = complete`,
`SEMSECAUTHSANDBOXTAIL = unplanned`, a clean worktree before this artifact
write, and the required roadmap hash
`d51576564b43ebc0da0aaa9346dea8236a37c682138e018b6118e99c3593737b`. Legacy
`.codex/phase-loop/` artifacts remain compatibility-only and do not supersede
canonical `.phase-loop/` state here.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is the active roadmap, it is tracked and clean in
  this worktree, and `sha256sum specs/phase-plans-v7.md` matches the
  user-required
  `d51576564b43ebc0da0aaa9346dea8236a37c682138e018b6118e99c3593737b`.
- The checkout is on `main...origin/main [ahead 163]` at `HEAD`
  `99e1e0e66cae0cf079ca289212df90d4920f713f`, the worktree is clean before
  this artifact write, and
  `plans/phase-plan-v7-SEMSECAUTHSANDBOXTAIL.md` did not exist before this
  run.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is the active evidence anchor.
  Its `SEMSWIFTDBEFFTAIL Live Rerun Check` block records that the refreshed
  repo-local command
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  advanced durably beyond the cleared root-test seam
  `tests/root_tests/test_swift_plugin.py ->
  tests/root_tests/test_mcp_database_efficiency.py`
  and later terminalized on the exact security-test seam
  `tests/security/test_route_auth_coverage.py ->
  tests/security/test_p24_sandbox_degradation.py`.
- That same evidence block records the current blocker shape this phase must
  clear or truthfully supersede: at `2026-04-30T02:33:46Z`,
  `.mcp-index/force_full_exit_trace.json` showed `status: running`,
  `stage: lexical_walking`,
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/tests/security/test_route_auth_coverage.py`,
  and
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/tests/security/test_p24_sandbox_degradation.py`.
  At `2026-04-30T02:33:57Z`, a refreshed `repository status` terminalized the
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
  Python entries for the earlier root-test seam
  `tests/root_tests/test_swift_plugin.py ->
  tests/root_tests/test_mcp_database_efficiency.py`, but repo search shows no
  exact bounded entry yet for
  `tests/security/test_route_auth_coverage.py` or
  `tests/security/test_p24_sandbox_degradation.py`.
- `mcp_server/cli/repository_commands.py` already prints a dedicated lexical
  boundary line for the later security fixture pair
  `tests/security/fixtures/mock_plugin/plugin.py ->
  tests/security/fixtures/mock_plugin/__init__.py`, but it does not yet
  advertise an exact bounded boundary for
  `tests/security/test_route_auth_coverage.py ->
  tests/security/test_p24_sandbox_degradation.py`.
- `tests/test_dispatcher.py` already freezes exact bounded persistence for the
  earlier Swift/database-efficiency pair and other later tail pairs, but repo
  search shows no current bounded-path fixture yet for the current
  route-auth/sandbox-degradation pair.
- `tests/test_git_index_manager.py` and `tests/test_repository_commands.py`
  already freeze the cleared Swift/database-efficiency seam and later lexical
  promotion behavior, but repo search shows no durable trace or operator
  output fixtures yet for
  `tests/security/test_route_auth_coverage.py ->
  tests/security/test_p24_sandbox_degradation.py`.
- `tests/docs/test_semdogfood_evidence_contract.py` and
  `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` already mention the current
  security-test files and the downstream phase name
  `SEMSECAUTHSANDBOXTAIL`, but there is not yet an execution-ready plan
  artifact defining how execution should clear or truthfully supersede the
  exact pair.
- The current checked-in security tests are concrete enough to justify an
  exact-bounded-path-first repair strategy before source edits:
  `tests/security/test_route_auth_coverage.py` exposes the route enumeration
  helpers `_protected_routes` and `_has_auth_dependency` plus the tokenless
  route coverage tests
  `test_search_capabilities_requires_auth` and
  `test_all_protected_routes_return_401_without_token`;
  `tests/security/test_p24_sandbox_degradation.py` exposes capability-state
  and alias-construction tests through `_caps`,
  `test_worker_missing_extra_failure_has_capability_state`,
  `test_csharp_aliases_construct_in_sandbox`, and
  `test_specific_plugin_alias_exports_construct_in_sandbox`.

Practical planning boundary:

- SEMSECAUTHSANDBOXTAIL should prefer exact bounded-path handling, durable
  trace truth, and repository-status boundary updates before mutating the
  checked-in security tests themselves.
- Execution may expand into
  `tests/security/test_route_auth_coverage.py` and
  `tests/security/test_p24_sandbox_degradation.py` only if SL-0 and SL-1
  prove the active watchdog cost remains file-local after the dispatcher and
  operator boundary plumbing is repaired.
- SEMSECAUTHSANDBOXTAIL must stay narrow and evidence-driven. It must not
  reopen the cleared
  `tests/root_tests/test_swift_plugin.py ->
  tests/root_tests/test_mcp_database_efficiency.py`
  seam, it must not skip directly to the later mock-plugin fixture boundary
  without direct rerun evidence, and it must not widen into blanket
  `tests/security/**/*.py`, integration, semantic-stage, or release work
  unless the refreshed rerun proves the blocker has moved again.

## Interface Freeze Gates

- [ ] IF-0-SEMSECAUTHSANDBOXTAIL-1 - Exact security-test advance contract:
      a refreshed repo-local force-full rerun on the post-SEMSWIFTDBEFFTAIL
      head no longer terminalizes with the durable blocker centered on
      `tests/security/test_route_auth_coverage.py ->
      tests/security/test_p24_sandbox_degradation.py`; it either advances
      durably beyond that exact pair or emits a truthful newer blocker before
      the 120-second watchdog expires.
- [ ] IF-0-SEMSECAUTHSANDBOXTAIL-2 - Narrow repair contract:
      any repair introduced by this phase remains limited to the exact
      security-test pair plus the immediate dispatcher, trace, status,
      evidence, and roadmap-steering plumbing needed to clear it. The phase
      must not reopen the cleared
      `tests/root_tests/test_swift_plugin.py ->
      tests/root_tests/test_mcp_database_efficiency.py`
      seam or jump ahead to the later
      `tests/security/fixtures/mock_plugin/plugin.py ->
      tests/security/fixtures/mock_plugin/__init__.py`
      boundary without direct evidence.
- [ ] IF-0-SEMSECAUTHSANDBOXTAIL-3 - Lexical discoverability contract:
      both exact security-test files remain lexically discoverable with durable
      file storage plus stable symbol/text discoverability for
      `_protected_routes`,
      `_has_auth_dependency`,
      `test_search_capabilities_requires_auth`,
      `test_all_protected_routes_return_401_without_token`,
      `_caps`,
      `test_worker_missing_extra_failure_has_capability_state`,
      `test_csharp_aliases_construct_in_sandbox`, and
      `test_specific_plugin_alias_exports_construct_in_sandbox` instead of
      turning either file into an indexing blind spot.
- [ ] IF-0-SEMSECAUTHSANDBOXTAIL-4 - Durable trace and operator contract:
      `force_full_exit_trace.json`, `GitAwareIndexManager`, and
      `uv run mcp-index repository status` stay aligned with the repaired
      security-test outcome and do not leave stale blame on the cleared
      Swift/database-efficiency seam or prematurely promote the later
      mock-plugin fixture boundary once lexical progress has not yet advanced
      beyond the current pair.
- [ ] IF-0-SEMSECAUTHSANDBOXTAIL-5 - Evidence contract:
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMSWIFTDBEFFTAIL rerun outcome, adds a dedicated
      `SEMSECAUTHSANDBOXTAIL` live-rerun block, and captures the final
      authoritative verdict for the route-auth/sandbox-degradation seam plus
      any newer blocker.
- [ ] IF-0-SEMSECAUTHSANDBOXTAIL-6 - Downstream steering contract:
      if execution exposes a blocker beyond the current roadmap tail,
      `specs/phase-plans-v7.md` is amended before closeout so phase-loop
      points to the newest truthful next phase instead of stale
      SEMSECAUTHSANDBOXTAIL assumptions.

## Lane Index & Dependencies

- SL-0 - Exact security-test contract freeze; Depends on: SEMSWIFTDBEFFTAIL; Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 - Durable trace and repository-status security fixtures; Depends on: SL-0; Blocks: SL-2, SL-3, SL-4; Parallel-safe: no
- SL-2 - Minimal security seam repair; Depends on: SL-0, SL-1; Blocks: SL-3, SL-4; Parallel-safe: no
- SL-3 - Live rerun evidence reducer and contract refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SL-4; Parallel-safe: no
- SL-4 - Downstream roadmap steering reducer; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: SEMSECAUTHSANDBOXTAIL acceptance; Parallel-safe: no

Lane DAG:

```text
SEMSWIFTDBEFFTAIL
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SL-4 -> SEMSECAUTHSANDBOXTAIL acceptance
```

## Lanes

### SL-0 - Exact Security-Test Contract Freeze

- **Scope**: Freeze the exact
  `tests/security/test_route_auth_coverage.py ->
  tests/security/test_p24_sandbox_degradation.py`
  seam in deterministic dispatcher coverage so execution proves a narrow
  bounded repair instead of assuming the later security fixture boundary
  already makes the current pair safe.
- **Owned files**: `tests/test_dispatcher.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMSECAUTHSANDBOXTAIL-1,
  IF-0-SEMSECAUTHSANDBOXTAIL-2, and
  IF-0-SEMSECAUTHSANDBOXTAIL-3 at the dispatcher boundary
- **Interfaces consumed**: existing
  `Dispatcher.index_directory(...)`,
  `_EXACT_BOUNDED_PYTHON_PATHS`,
  durable file metadata storage, and the current checked-in content shape of
  `tests/security/test_route_auth_coverage.py` and
  `tests/security/test_p24_sandbox_degradation.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` with repo-shaped fixtures for the
    exact route-auth/sandbox-degradation pair so the dispatcher contract proves
    durable file rows, zero code chunks where bounded indexing is applied, and
    FTS-backed discoverability for both files.
  - test: Assert that the pair remains textually discoverable for
    `_protected_routes`,
    `_has_auth_dependency`,
    `test_search_capabilities_requires_auth`,
    `test_all_protected_routes_return_401_without_token`,
    `_caps`,
    `test_worker_missing_extra_failure_has_capability_state`,
    `test_csharp_aliases_construct_in_sandbox`, and
    `test_specific_plugin_alias_exports_construct_in_sandbox`.
  - test: Keep negative guards proving the cleared Swift/database-efficiency
    seam and the later mock-plugin fixture boundary do not silently become the
    reported active blocker once the current security-pair fixtures are
    introduced.
  - impl: Keep fixtures deterministic with repo-local Python strings rather
    than live `sync --force-full` waits.
  - impl: Keep this lane on contract freeze only. Do not mutate dispatcher
    implementation, durable trace logic, CLI wording, docs, roadmap steering,
    or the checked-in security test sources here.
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "route_auth or sandbox_degradation or security or lexical or bounded"`

### SL-1 - Durable Trace And Repository-Status Security Fixtures

- **Scope**: Freeze the route-auth/sandbox-degradation pair at the durable
  trace and operator surface so execution can distinguish a real runtime repair
  from a report that still blames the cleared Swift/database-efficiency seam or
  that jumps ahead to the later mock-plugin fixture boundary after lexical
  progress has not yet moved past the current pair.
- **Owned files**: `tests/test_git_index_manager.py`, `tests/test_repository_commands.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMSECAUTHSANDBOXTAIL-1,
  IF-0-SEMSECAUTHSANDBOXTAIL-2, and
  IF-0-SEMSECAUTHSANDBOXTAIL-4
- **Interfaces consumed**: existing durable trace lifecycle in
  `GitAwareIndexManager`; repository-status interrupted and stale-running
  output; the current lexical boundary print helpers in
  `mcp_server/cli/repository_commands.py`; and the SEMSWIFTDBEFFTAIL evidence
  block in `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_git_index_manager.py` so running and interrupted
    force-full traces can preserve the exact pair
    `tests/security/test_route_auth_coverage.py ->
    tests/security/test_p24_sandbox_degradation.py`,
    then promote a later blocker or closeout state once the pair has truly
    been cleared.
  - test: Extend `tests/test_repository_commands.py` so
    `repository status` reports the interrupted trace against the exact
    route-auth/sandbox-degradation pair and advertises a dedicated exact
    bounded boundary line for that pair when both files are present.
  - test: Keep negative guards proving the cleared
    `tests/root_tests/test_swift_plugin.py ->
    tests/root_tests/test_mcp_database_efficiency.py`
    seam and the later mock-plugin fixture boundary do not remain the reported
    active blocker once the current pair fixtures are introduced.
  - impl: Model closeout and successor promotion with synthetic trace payloads
    or monkeypatched manager behavior rather than live `sync --force-full`
    execution inside unit tests.
  - impl: Keep this lane fixture-only. Do not update production dispatcher
    code, security test sources, evidence docs, or roadmap steering here.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "route_auth or sandbox_degradation or security or interrupted or boundary or closeout_handoff"`

### SL-2 - Minimal Security Seam Repair

- **Scope**: Implement the smallest production repair needed so the live
  lexical walker no longer burns its watchdog budget on the exact
  `tests/security/test_route_auth_coverage.py ->
  tests/security/test_p24_sandbox_degradation.py`
  pair.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `mcp_server/cli/repository_commands.py`, `mcp_server/storage/git_index_manager.py`, `tests/security/test_route_auth_coverage.py`, `tests/security/test_p24_sandbox_degradation.py`
- **Interfaces provided**: IF-0-SEMSECAUTHSANDBOXTAIL-1 exact advance
  contract; IF-0-SEMSECAUTHSANDBOXTAIL-2 narrow repair contract;
  IF-0-SEMSECAUTHSANDBOXTAIL-3 lexical discoverability contract; and
  IF-0-SEMSECAUTHSANDBOXTAIL-4 durable trace/operator contract
- **Interfaces consumed**: SL-0 dispatcher fixtures; SL-1 trace/status
  fixtures; existing `_EXACT_BOUNDED_PYTHON_PATHS`; repository-status lexical
  boundary printers; and the current structure of the two checked-in security
  test files
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 and SL-1 slices first and confirm whether the active
    cost is cleared by exact bounded-path handling plus truthful operator
    boundary output, or whether the live hotspot remains file-local.
  - impl: Prefer the narrow production repair first:
    add exact bounded-path handling for one or both security test files in
    `mcp_server/dispatcher/dispatcher_enhanced.py` and add a dedicated
    repository-status boundary printer in
    `mcp_server/cli/repository_commands.py` for
    `tests/security/test_route_auth_coverage.py ->
    tests/security/test_p24_sandbox_degradation.py`.
  - impl: If the fixture evidence shows stale durable-trace promotion even
    after bounded-path handling is in place, patch
    `mcp_server/storage/git_index_manager.py` minimally so interrupted and
    closeout traces preserve the truthful current blocker or successor.
  - impl: Only edit
    `tests/security/test_route_auth_coverage.py` or
    `tests/security/test_p24_sandbox_degradation.py`
    if the bounded-path and trace/status repair still leaves the live watchdog
    stuck on file-local structure. Preserve behavioral intent and stable symbol
    names if a security-test edit becomes necessary.
  - impl: Do not clear the seam with a broad `tests/security/**/*.py` bypass,
    a generic ignore rule, or a repair that silently jumps ahead to the later
    mock-plugin fixture boundary without direct evidence.
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "route_auth or sandbox_degradation or security or lexical or bounded"`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "route_auth or sandbox_degradation or security or interrupted or boundary or closeout_handoff"`
  - verify: `uv run pytest tests/security/test_route_auth_coverage.py tests/security/test_p24_sandbox_degradation.py -q --no-cov`

### SL-3 - Live Rerun Evidence Reducer And Contract Refresh

- **Scope**: Refresh the semantic dogfood evidence so the current-head rerun
  verdict for the route-auth/sandbox-degradation seam is durable, reviewable,
  and ready to steer the next downstream phase honestly.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: IF-0-SEMSECAUTHSANDBOXTAIL-5 evidence contract
- **Interfaces consumed**: SL-0 dispatcher verdict; SL-1 trace/status verdict;
  SL-2 production repair result; current evidence lineage in
  `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`; and the phase-chain assertions in
  `tests/docs/test_semdogfood_evidence_contract.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/docs/test_semdogfood_evidence_contract.py` so the
    evidence artifact must mention the SEMSWIFTDBEFFTAIL rerun outcome, the
    exact route-auth/sandbox-degradation pair, the final authoritative verdict
    for this phase, and any downstream steering if the blocker moves again.
  - impl: Update `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` with a dedicated
    `SEMSECAUTHSANDBOXTAIL Live Rerun Check` section that records observed
    commit, rerun command, timestamps, trace snapshot, repository-status
    output, SQLite counts, and the final authoritative verdict for the current
    security seam.
  - impl: If the rerun advances beyond the current pair, record the newer
    blocker precisely instead of leaving the evidence anchored on the cleared
    security seam or on the earlier Swift/database-efficiency boundary.
  - impl: Keep the evidence wording truthful about semantic readiness staying
    fail-closed unless the rerun itself proves otherwise.
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "SEMSWIFTDBEFFTAIL or SEMSECAUTHSANDBOXTAIL or route_auth or sandbox_degradation or security"`
  - verify: `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - verify: `sed -n '1,240p' .mcp-index/force_full_exit_trace.json`
  - verify: `sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'`

### SL-4 - Downstream Roadmap Steering Reducer

- **Scope**: Amend the roadmap only if execution proves the active blocker has
  moved beyond the current tail, so phase-loop stays truthful after this
  closeout.
- **Owned files**: `specs/phase-plans-v7.md`
- **Interfaces provided**: IF-0-SEMSECAUTHSANDBOXTAIL-6 downstream steering
  contract
- **Interfaces consumed**: SL-3 final rerun verdict; current phase-84 tail in
  `specs/phase-plans-v7.md`; and the SEM* downstream phase structure already
  used in the roadmap
- **Parallel-safe**: no
- **Tasks**:
  - test: Re-read the active phase-84 tail after SL-3 so any amendment is
    based on the final authoritative rerun outcome rather than the original
    planning assumptions.
  - impl: If the final rerun exposes a later blocker beyond
    `tests/security/test_route_auth_coverage.py ->
    tests/security/test_p24_sandbox_degradation.py`,
    append one narrow downstream phase that freezes the newer blocker, updates
    the DAG, and records the new exact pair as the next truthful phase-loop
    step.
  - impl: If execution clears the current seam without exposing a newer
    blocker, leave the roadmap unchanged and record that no downstream phase
    was required.
  - impl: Keep any roadmap amendment narrow: no renumbering, no unrelated phase
    rewrites, and no stale downstream assumptions left behind.
  - verify: `rg -n "SEMSECAUTHSANDBOXTAIL|test_route_auth_coverage|test_p24_sandbox_degradation" specs/phase-plans-v7.md docs/status/SEMANTIC_DOGFOOD_REBUILD.md tests/docs/test_semdogfood_evidence_contract.py`

## Verification

Planning-only run: do not execute these during plan creation. Run them during
`codex-execute-phase` or manual SEMSECAUTHSANDBOXTAIL execution.

Lane-specific checks:

```bash
uv run pytest tests/test_dispatcher.py -q --no-cov -k "route_auth or sandbox_degradation or security or lexical or bounded"
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "route_auth or sandbox_degradation or security or interrupted or boundary or closeout_handoff"
uv run pytest tests/security/test_route_auth_coverage.py tests/security/test_p24_sandbox_degradation.py -q --no-cov
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "SEMSWIFTDBEFFTAIL or SEMSECAUTHSANDBOXTAIL or route_auth or sandbox_degradation or security"
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
  tests/security/test_route_auth_coverage.py \
  tests/security/test_p24_sandbox_degradation.py \
  tests/docs/test_semdogfood_evidence_contract.py \
  -q --no-cov -k "route_auth or sandbox_degradation or security or interrupted or boundary or closeout_handoff or lexical or bounded"
timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
sed -n '1,240p' .mcp-index/force_full_exit_trace.json
git status --short -- plans/phase-plan-v7-SEMSECAUTHSANDBOXTAIL.md docs/status/SEMANTIC_DOGFOOD_REBUILD.md specs/phase-plans-v7.md
git diff --check
git diff --cached --check
```

## Acceptance Criteria

- [ ] A refreshed repo-local force-full rerun on the post-SEMSWIFTDBEFFTAIL
      head either advances durably beyond the later
      `tests/security/test_route_auth_coverage.py ->
      tests/security/test_p24_sandbox_degradation.py`
      pair or emits a truthful newer blocker before the 120-second watchdog
      expires.
- [ ] Any repair chosen for the route-auth/sandbox-degradation seam stays
      narrow, tested, and does not reopen the cleared
      `tests/root_tests/test_swift_plugin.py ->
      tests/root_tests/test_mcp_database_efficiency.py`
      boundary or skip directly to the later mock-plugin fixture boundary
      without direct evidence.
- [ ] Both exact security-test files remain lexically discoverable with
      durable file storage and stable symbol/text discoverability for
      `_protected_routes`,
      `_has_auth_dependency`,
      `test_search_capabilities_requires_auth`,
      `test_all_protected_routes_return_401_without_token`,
      `_caps`,
      `test_worker_missing_extra_failure_has_capability_state`,
      `test_csharp_aliases_construct_in_sandbox`, and
      `test_specific_plugin_alias_exports_construct_in_sandbox`.
- [ ] `force_full_exit_trace.json` and
      `uv run mcp-index repository status` stay aligned with the repaired
      security-test outcome and do not leave stale blame on the cleared
      Swift/database-efficiency seam or prematurely advance to the later
      security fixture boundary after progress has not yet moved beyond the
      current pair.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMSWIFTDBEFFTAIL rerun outcome and the final live verdict for the
      route-auth/sandbox-degradation seam.
- [ ] If execution reveals a newer blocker beyond the current roadmap tail,
      `specs/phase-plans-v7.md` is updated before closeout so the next
      phase-loop step stays truthful.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMSECAUTHSANDBOXTAIL.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMSECAUTHSANDBOXTAIL.md
  artifact_state: staged
```
