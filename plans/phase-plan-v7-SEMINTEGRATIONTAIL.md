---
phase_loop_plan_version: 1
phase: SEMINTEGRATIONTAIL
roadmap: specs/phase-plans-v7.md
roadmap_sha256: 26def7ccd1710d2fdb2c7d3cbe72366b72a7e8f24ecb3b243f5957c596b9ec1a
---
# SEMINTEGRATIONTAIL: Integration Test Tail Recovery

## Context

SEMINTEGRATIONTAIL is the phase-79 follow-up for the v7 semantic hardening
roadmap. Canonical `.phase-loop/` runtime exists in this checkout, so it is
the authoritative runner state for this planning run. The current canonical
snapshots agree cleanly: `.phase-loop/state.json` and
`.phase-loop/tui-handoff.md` both identify `SEMINTEGRATIONTAIL` as the current
`unplanned` phase for `specs/phase-plans-v7.md`, and the recorded roadmap hash
matches the user-required
`26def7ccd1710d2fdb2c7d3cbe72366b72a7e8f24ecb3b243f5957c596b9ec1a`.
Legacy `.codex/phase-loop/` artifacts remain compatibility-only and do not
supersede canonical `.phase-loop/` state here.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is the active roadmap, it is tracked and clean in
  this worktree, and `sha256sum specs/phase-plans-v7.md` matches the required
  `26def7ccd1710d2fdb2c7d3cbe72366b72a7e8f24ecb3b243f5957c596b9ec1a`.
- The checkout is on `main...origin/main [ahead 153]` at `HEAD`
  `c5170effc65b608737a84e682348a24ec579dc68`, the worktree is clean before
  this artifact write, and `plans/phase-plan-v7-SEMINTEGRATIONTAIL.md` did not
  exist before this run.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is the active evidence anchor.
  Its `SEMCODEXLOOPREBOUNDTAIL Live Rerun Check` block records that the
  refreshed repo-local command
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  advanced durably beyond the cleared legacy
  `.codex/phase-loop/runs/20260424T190651Z-01-garc-plan/launch.json ->
  .codex/phase-loop/runs/20260427T075236Z-05-idxsafe-repair/terminal-summary.json`
  seam and later terminalized on a newer integration-test tail.
- That same evidence block shows the exact current blocker shape that this
  phase must clear or truthfully supersede: at `2026-04-30T00:45:43Z`,
  `.mcp-index/force_full_exit_trace.json` still showed `status: running`,
  `stage: lexical_walking`,
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/tests/test_disk_full.py`,
  and
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/tests/test_incremental_indexer.py`,
  while at `2026-04-30T00:46:51Z` a refreshed `repository status` terminalized
  the rerun to `Trace status: interrupted` with later durable progress already
  anchored on
  `tests/integration/__init__.py ->
  tests/integration/obs/test_obs_smoke.py`.
- `repository status` on that same head remained semantically fail-closed
  after the rerun:
  `Readiness: stale_commit`, `Rollout status: partial_index_failure`,
  `Last sync error: disk I/O error`, and
  `Semantic readiness: summaries_missing`. SQLite runtime counts also remained
  `files = 1064`, `code_chunks = 13095`, `chunk_summaries = 0`, and
  `semantic_points = 0`, so this is still a lexical-tail and truth-surface
  slice rather than a semantic-vector recovery phase.
- Repo search found no current references to
  `tests/integration/__init__.py` or
  `tests/integration/obs/test_obs_smoke.py` inside
  `mcp_server/dispatcher/dispatcher_enhanced.py`,
  `mcp_server/cli/repository_commands.py`,
  `tests/test_dispatcher.py`,
  `tests/test_git_index_manager.py`, or
  `tests/test_repository_commands.py`. The only current repo-local references
  to the exact pair are in `tests/docs/test_semdogfood_evidence_contract.py`
  and the dogfood evidence report, so this phase starts without a frozen
  dispatcher, durable-trace, or CLI contract for the integration seam.
- `tests/integration/obs/test_obs_smoke.py` is a `366` line production-mode
  gateway smoke test that currently exposes `_find_repo_root`,
  `_docker_available`, `_free_port`, `_drain_lines`, fixtures
  `gateway_proc` and `admin_token`, and smoke tests
  `test_json_log_parse_rate`,
  `test_metrics_endpoint_reachable`, and
  `test_secret_redaction_via_http`. `tests/integration/__init__.py` remains a
  one-line package marker. Any repair must preserve those checked-in surfaces
  or their discoverability rather than clearing the seam by turning the files
  into an indexing blind spot.
- `SEMCODEXLOOPREBOUNDTAIL` already proved the older legacy
  `.codex/phase-loop` rebound is no longer the active blocker, so this phase
  should treat renewed legacy blame as a regression unless the refreshed rerun
  re-anchors there with direct evidence.

Practical planning boundary:

- SEMINTEGRATIONTAIL may tighten exact lexical handling for the integration
  pair in `mcp_server/dispatcher/dispatcher_enhanced.py`, adjust
  `mcp_server/cli/repository_commands.py` or adjacent truth surfaces so the
  durable blocker is reported accurately, make the smallest integration-test
  local simplification only if tests and the current-head rerun prove the
  hotspot is file-local, refresh the dogfood evidence report, rerun the
  repo-local force-full sync, and extend the roadmap only if a newer blocker
  appears beyond the current tail.
- SEMINTEGRATIONTAIL must stay narrow and evidence-driven. It must not reopen
  the repaired later legacy `.codex/phase-loop` rebound, add a broad
  `tests/**/*.py` or repo-wide lexical-timeout bypass, or widen into unrelated
  semantic, docs-family, or release work unless the refreshed rerun proves the
  blocker has moved again.
- Because the current evidence already shows a gap between the raw running
  trace and the later terminalized status output, execution should first prove
  whether the real missing contract is exact integration-tail handling,
  closeout-handoff promotion, or status-surface truthfulness before mutating
  the integration tests themselves.

## Interface Freeze Gates

- [ ] IF-0-SEMINTEGRATIONTAIL-1 - Exact integration-tail advance contract:
      a refreshed repo-local force-full rerun on the
      post-SEMCODEXLOOPREBOUNDTAIL head no longer terminalizes with the
      durable blocker centered on
      `tests/integration/__init__.py ->
      tests/integration/obs/test_obs_smoke.py`; it either advances durably
      beyond that exact pair or emits a truthful newer blocker before the
      120-second watchdog expires.
- [ ] IF-0-SEMINTEGRATIONTAIL-2 - Narrow repair contract:
      any repair introduced by this phase remains limited to the exact later
      integration-test pair and the immediate dispatcher, trace, CLI,
      evidence, and roadmap-steering plumbing needed to clear or truthfully
      supersede it. The phase must not reopen the repaired later legacy
      `.codex/phase-loop` rebound without direct evidence.
- [ ] IF-0-SEMINTEGRATIONTAIL-3 - Integration discoverability contract:
      the exact pair remains lexically discoverable with durable file storage,
      path visibility for `tests/integration/__init__.py`, and stable symbol
      or text discoverability for `_find_repo_root`, `gateway_proc`,
      `admin_token`, `test_json_log_parse_rate`,
      `test_metrics_endpoint_reachable`, and
      `test_secret_redaction_via_http` inside
      `tests/integration/obs/test_obs_smoke.py`.
- [ ] IF-0-SEMINTEGRATIONTAIL-4 - Durable trace and operator contract:
      `force_full_exit_trace.json` and
      `uv run mcp-index repository status` stay aligned on the current head
      once the later legacy rebound is already cleared, and they do not leave
      stale blame on the cleared `.codex/phase-loop` seam or on earlier
      intermediary test files after durable progress has already moved to the
      exact integration pair.
- [ ] IF-0-SEMINTEGRATIONTAIL-5 - Evidence and downstream steering contract:
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMCODEXLOOPREBOUNDTAIL rerun outcome, the SEMINTEGRATIONTAIL rerun
      command and timestamps, the refreshed durable trace and status output,
      and the final authoritative verdict for the integration seam; if
      execution exposes a blocker beyond the current roadmap tail,
      `specs/phase-plans-v7.md` is amended before closeout so `.phase-loop/`
      points to the newest truthful next phase.

## Lane Index & Dependencies

- SL-0 - Exact integration-tail contract freeze; Depends on: SEMCODEXLOOPREBOUNDTAIL; Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 - Durable trace and repository-status truth fixtures; Depends on: SL-0; Blocks: SL-2, SL-3, SL-4; Parallel-safe: no
- SL-2 - Minimal integration-tail runtime repair or test-local simplification; Depends on: SL-0, SL-1; Blocks: SL-3, SL-4; Parallel-safe: no
- SL-3 - Live rerun evidence reducer and SEMINTEGRATIONTAIL contract refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SL-4; Parallel-safe: no
- SL-4 - Downstream roadmap steering reducer; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: SEMINTEGRATIONTAIL acceptance; Parallel-safe: no

Lane DAG:

```text
SEMCODEXLOOPREBOUNDTAIL
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SL-4 -> SEMINTEGRATIONTAIL acceptance
```

## Lanes

### SL-0 - Exact Integration-Tail Contract Freeze

- **Scope**: Freeze the exact
  `tests/integration/__init__.py ->
  tests/integration/obs/test_obs_smoke.py`
  lexical seam in deterministic dispatcher coverage so this phase proves a
  narrow repair instead of assuming the later blocker will clear on its own.
- **Owned files**: `tests/test_dispatcher.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMINTEGRATIONTAIL-1,
  IF-0-SEMINTEGRATIONTAIL-2, and
  IF-0-SEMINTEGRATIONTAIL-3 at the dispatcher boundary
- **Interfaces consumed**: existing
  `Dispatcher.index_directory(...)`,
  `_EXACT_BOUNDED_PYTHON_PATHS`,
  lexical file metadata storage,
  and the current checked-in content shape of
  `tests/integration/__init__.py` and
  `tests/integration/obs/test_obs_smoke.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` with repo-shaped fixtures for
    `tests/integration/__init__.py`,
    `tests/integration/obs/test_obs_smoke.py`, and a control integration file
    so the chosen narrow repair preserves durable file rows, stable path
    storage, and lexical discoverability for the exact pair.
  - test: Add explicit assertions that `_find_repo_root`, `gateway_proc`,
    `admin_token`, `test_json_log_parse_rate`,
    `test_metrics_endpoint_reachable`, and
    `test_secret_redaction_via_http` remain discoverable after the repair,
    while `tests/integration/__init__.py` remains stored and path-searchable
    even if it contributes no useful symbols.
  - test: Add negative guards that the repaired later legacy
    `.codex/phase-loop` rebound pair does not silently reappear as the active
    lexical boundary once the integration fixtures are introduced.
  - test: Fail if the repair would clear the seam by turning either target
    file into an ignored lexical blind spot or by widening the matcher to a
    generic `tests/**/*.py` bypass.
  - impl: Keep fixtures deterministic with repo-local Python strings and
    synthetic indexing assertions rather than live long-running force-full
    waits inside unit coverage.
  - impl: Keep this lane on contract freeze only. Do not mutate dispatcher or
    CLI implementation, the checked-in integration tests, evidence docs, or
    roadmap steering here.
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "integration_init or obs_smoke or integration_tail or lexical or bounded"`

### SL-1 - Durable Trace And Repository-Status Truth Fixtures

- **Scope**: Freeze the exact integration pair at the durable trace and
  operator surface so execution can distinguish a real integration-tail repair
  from a report that still blames cleared legacy or intermediary lexical
  files after durable progress has already moved later.
- **Owned files**: `tests/test_git_index_manager.py`, `tests/test_repository_commands.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMINTEGRATIONTAIL-1,
  IF-0-SEMINTEGRATIONTAIL-2, and
  IF-0-SEMINTEGRATIONTAIL-4
- **Interfaces consumed**: existing durable trace lifecycle in
  `GitAwareIndexManager`; repository-status interrupted and stale-running
  output; the repaired legacy `.codex/phase-loop` boundary wording; and the
  current later-pair evidence from
  `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_git_index_manager.py` so a lexical rerun that
    has already advanced beyond the later legacy `.codex/phase-loop` rebound
    can surface the exact integration pair truthfully, then promote a later
    blocker or closeout status when that integration seam has been cleared.
  - test: Extend `tests/test_repository_commands.py` so
    `uv run mcp-index repository status` can be frozen against the exact
    `tests/integration/__init__.py ->
    tests/integration/obs/test_obs_smoke.py`
    pair rather than leaving the active blocker on
    `tests/test_disk_full.py -> tests/test_incremental_indexer.py` once the
    durable terminal status has already moved later.
  - test: Keep negative guards that the repaired legacy
    `.codex/phase-loop` compatibility-runtime boundary line remains intact and
    that SEMCODEXLOOPREBOUNDTAIL-era blame does not regress into the active
    blocker once the integration-tail fixtures are introduced.
  - impl: Model closeout and successor promotion with synthetic trace payloads
    or monkeypatched manager behavior rather than live `sync --force-full`
    execution inside unit tests.
  - impl: Keep this lane fixture-only. Do not update production dispatcher,
    CLI, evidence, or roadmap code here.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "integration_init or obs_smoke or integration_tail or interrupted or boundary or closeout_handoff"`

### SL-2 - Minimal Integration-Tail Runtime Repair Or Test-Local Simplification

- **Scope**: Implement the smallest repair needed so the current-head
  force-full rerun no longer leaves
  `tests/integration/__init__.py ->
  tests/integration/obs/test_obs_smoke.py`
  as the active lexical watchdog tail.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `mcp_server/cli/repository_commands.py`, `tests/integration/__init__.py`, `tests/integration/obs/test_obs_smoke.py`
- **Interfaces provided**: IF-0-SEMINTEGRATIONTAIL-1 exact integration-tail
  advance contract; IF-0-SEMINTEGRATIONTAIL-2 narrow repair contract;
  IF-0-SEMINTEGRATIONTAIL-3 integration discoverability contract; and
  IF-0-SEMINTEGRATIONTAIL-4 durable trace and operator contract
- **Interfaces consumed**: SL-0 dispatcher fixtures; SL-1 durable trace and
  repository-status fixtures; existing `_EXACT_BOUNDED_PYTHON_PATHS`; current
  lexical timeout behavior in `Dispatcher.index_directory(...)`; current
  repository-status wording; and the checked-in structure of the integration
  pair
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 and SL-1 slices first and determine whether the active
    cost is best cleared by exact lexical handling for the integration pair,
    closeout-handoff and status-truth repair, or the smallest file-local
    simplification inside `tests/integration/obs/test_obs_smoke.py`.
  - impl: Choose one singular repair surface and keep it exact. Acceptable
    examples are adding the exact integration pair to the existing bounded
    lexical handling in `dispatcher_enhanced.py`, tightening
    `repository status` truth promotion so the exact pair is reported
    accurately, or making the smallest integration-test-local simplification
    that allows the current watchdog to advance beyond the pair.
  - impl: Only edit `tests/integration/__init__.py` or
    `tests/integration/obs/test_obs_smoke.py` if tests and the current-head
    rerun prove the active hotspot is file-local structure rather than missing
    dispatcher or truth-surface handling.
  - impl: Preserve the observability smoke test's intended operational
    meaning, `_find_repo_root`, fixtures `gateway_proc` and `admin_token`, and
    smoke-test names `test_json_log_parse_rate`,
    `test_metrics_endpoint_reachable`, and
    `test_secret_redaction_via_http`. Keep
    `tests/integration/__init__.py` as a package marker if it remains needed.
  - impl: Do not clear the seam with a broad `tests/**` bypass, a generic
    integration-suite ignore rule, or a repair that reopens the cleared later
    legacy `.codex/phase-loop` rebound.
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "integration_init or obs_smoke or integration_tail or lexical or bounded"`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "integration_init or obs_smoke or integration_tail or interrupted or boundary or closeout_handoff"`

### SL-3 - Live Rerun Evidence Reducer And SEMINTEGRATIONTAIL Contract Refresh

- **Scope**: Refresh the dogfood evidence artifact so it records the
  authoritative current-head verdict for the exact integration seam after the
  narrow runtime repair lands.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: IF-0-SEMINTEGRATIONTAIL-5 evidence contract
- **Interfaces consumed**: SL-2 repair outcome; live outputs from
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`,
  `uv run mcp-index repository status`,
  `.mcp-index/force_full_exit_trace.json`, and SQLite runtime counts; plus the
  prior SEMCODEXLOOPREBOUNDTAIL evidence block
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/docs/test_semdogfood_evidence_contract.py` so the
    evidence contract requires the SEMCODEXLOOPREBOUNDTAIL rerun outcome, the
    exact integration pair, the SEMINTEGRATIONTAIL rerun commands, and the
    updated verification sequence.
  - impl: Update `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` with a dedicated
    `SEMINTEGRATIONTAIL` evidence block that records the refreshed rerun
    timestamps, exact trace and status output, SQLite counts, and the final
    authoritative verdict for
    `tests/integration/__init__.py ->
    tests/integration/obs/test_obs_smoke.py`.
  - impl: If the rerun still names the exact integration pair, the report must
    explain why that attribution remains truthful on the current head; if the
    rerun moves later, the report must say the integration seam is no longer
    the active blocker and preserve the exact newer blocker or closeout-stage
    attribution.
  - impl: Preserve the same-head readiness, rollout-status, last-sync-error,
    and semantic-readiness lines unless the refreshed live probes prove they
    changed.
  - impl: Keep this lane limited to the dogfood evidence artifact and its
    test. Do not mutate the roadmap here; SL-4 owns any required downstream
    phase-tail amendment.
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "SEMCODEXLOOPREBOUNDTAIL or SEMINTEGRATIONTAIL or obs_smoke or integration"`
  - verify: `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - verify: `sed -n '1,240p' .mcp-index/force_full_exit_trace.json`
  - verify: `sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'`

### SL-4 - Downstream Roadmap Steering Reducer

- **Scope**: Keep the v7 roadmap truthful if the refreshed current-head rerun
  exposes a blocker beyond the present roadmap tail.
- **Owned files**: `specs/phase-plans-v7.md`
- **Interfaces provided**: the roadmap-steering portion of
  IF-0-SEMINTEGRATIONTAIL-5
- **Interfaces consumed**: SL-3 live rerun verdict; current phase-79 tail
  position in `specs/phase-plans-v7.md`; and canonical `.phase-loop/`
  expectation that the roadmap names the next unplanned phase truthfully
- **Parallel-safe**: no
- **Tasks**:
  - test: Re-read the end of `specs/phase-plans-v7.md` after the SL-3 rerun
    and only amend it if the refreshed current-head evidence proves a blocker
    beyond
    `tests/integration/__init__.py ->
    tests/integration/obs/test_obs_smoke.py`.
  - impl: If the rerun reveals a newer blocker, append one downstream phase
    with the same exact-pair specificity and evidence-first structure used
    elsewhere in the v7 lexical-recovery chain so `.phase-loop/` does not stop
    on a stale integration tail.
  - impl: If the rerun keeps the integration pair as the active truthful
    blocker, leave the roadmap unchanged and record that decision explicitly
    in the execution closeout and evidence.
  - impl: Keep this lane reducer-only. Do not reopen earlier legacy, docs,
    script-family, or semantic phases that the rerun did not re-anchor on.
  - verify: `rg -n "SEMINTEGRATIONTAIL|tests/integration/__init__\\.py|tests/integration/obs/test_obs_smoke\\.py" specs/phase-plans-v7.md docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
  - verify: `git diff -- specs/phase-plans-v7.md`

## Verification

Planning-only run: do not execute these during plan creation. Run them during
`codex-execute-phase` or manual SEMINTEGRATIONTAIL execution.

Lane-specific checks:

```bash
uv run pytest tests/test_dispatcher.py -q --no-cov -k "integration_init or obs_smoke or integration_tail or lexical or bounded"
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "integration_init or obs_smoke or integration_tail or interrupted or boundary or closeout_handoff"
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "SEMCODEXLOOPREBOUNDTAIL or SEMINTEGRATIONTAIL or obs_smoke or integration"
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
  -q --no-cov -k "integration_init or obs_smoke or integration_tail or lexical or bounded or interrupted or boundary or closeout_handoff"
timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
sed -n '1,240p' .mcp-index/force_full_exit_trace.json
git status --short -- plans/phase-plan-v7-SEMINTEGRATIONTAIL.md docs/status/SEMANTIC_DOGFOOD_REBUILD.md specs/phase-plans-v7.md
git diff --check
git diff --cached --check
```

## Acceptance Criteria

- [ ] A refreshed repo-local force-full rerun on the
      post-SEMCODEXLOOPREBOUNDTAIL head either advances durably beyond
      `tests/integration/__init__.py ->
      tests/integration/obs/test_obs_smoke.py`
      or emits a truthful newer blocker before the 120-second watchdog
      expires.
- [ ] The chosen repair for the later integration-test seam stays narrow,
      tested, and does not reopen the repaired later legacy
      `.codex/phase-loop` rebound without direct evidence.
- [ ] The exact integration pair remains lexically discoverable with durable
      file storage, path visibility for `tests/integration/__init__.py`, and
      stable symbol or text discoverability for the checked-in smoke-test
      surfaces in `tests/integration/obs/test_obs_smoke.py`.
- [ ] `force_full_exit_trace.json` and
      `uv run mcp-index repository status` stay aligned with the repaired
      outcome for the exact integration pair and do not leave stale blame on
      the cleared later legacy `.codex/phase-loop` seam or on earlier
      intermediary test files after durable progress has already moved later.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMCODEXLOOPREBOUNDTAIL rerun outcome and the final live verdict for the
      exact integration pair.
- [ ] If execution reveals a newer blocker beyond the current roadmap tail,
      `specs/phase-plans-v7.md` is updated before closeout so the next
      phase-loop step stays truthful.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMINTEGRATIONTAIL.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMINTEGRATIONTAIL.md
  artifact_state: staged
```
