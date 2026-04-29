---
phase_loop_plan_version: 1
phase: SEMMOCKPLUGIN
roadmap: specs/phase-plans-v7.md
roadmap_sha256: 75aad42f4c6ebf29a2e3a7b34115ff35c1e85e96ba0e8113331044f079ba64bc
---
# SEMMOCKPLUGIN: Mock Plugin Fixture Tail Recovery

## Context

SEMMOCKPLUGIN is the phase-58 follow-up for the v7 semantic hardening
roadmap. Canonical `.phase-loop/` state is authoritative for this run:
`.phase-loop/state.json` and `.phase-loop/tui-handoff.md` both mark
`SEMMOCKPLUGIN` as the current `unplanned` phase after `SEMDOCTESTTAIL`
closed out on `HEAD` `4e936198b0f313bb10d500c5c939662761de648e` with
verification `passed`, a clean worktree, and `main...origin/main [ahead 111]`.
Legacy `.codex/phase-loop/` artifacts still exist in this checkout, but they
are compatibility-only and are not authoritative here.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is tracked and clean in this worktree, and
  `sha256sum specs/phase-plans-v7.md` matches the required
  `75aad42f4c6ebf29a2e3a7b34115ff35c1e85e96ba0e8113331044f079ba64bc`.
- The target artifact `plans/phase-plan-v7-SEMMOCKPLUGIN.md` did not exist
  before this planning run.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is the active evidence anchor.
  Its SEMDOCTESTTAIL rerun block captures the current downstream lexical
  failure precisely: the refreshed repo-local command
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  started on observed commit `4133bfe`, and at `2026-04-29T18:06:31Z`
  `.mcp-index/force_full_exit_trace.json` showed
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/tests/security/fixtures/mock_plugin/plugin.py`
  with
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/tests/security/fixtures/mock_plugin/__init__.py`;
  at `2026-04-29T18:06:41Z`, `repository status` terminalized that running
  snapshot to `Trace status: interrupted` with the same exact pair.
- The SEMDOCTESTTAIL target seam is no longer the active blocker:
  `tests/docs/test_gaclose_evidence_closeout.py ->
  tests/docs/test_p8_deployment_security.py`. The authoritative current-head
  blocker is now the later security-fixture pair
  `tests/security/fixtures/mock_plugin/plugin.py ->
  tests/security/fixtures/mock_plugin/__init__.py`, so older downstream
  assumptions should be treated as stale.
- The current blocker files are small and valid Python, which means the next
  repair should first prove why this exact handoff still consumes watchdog
  budget instead of assuming the prior docs-test fix generalizes automatically.
  `tests/security/fixtures/mock_plugin/plugin.py` is `52` lines / `1399`
  bytes; `tests/security/fixtures/mock_plugin/__init__.py` is `5` lines /
  `131` bytes.
- `mcp_server/dispatcher/dispatcher_enhanced.py` already carries
  `_EXACT_BOUNDED_PYTHON_PATHS` for the earlier docs-governance pair, the
  later docs-test pair, the verify/simulator pair, the embed/consolidation
  pair, and `mcp_server/visualization/quick_charts.py`, but it does not
  currently include either
  `tests/security/fixtures/mock_plugin/plugin.py` or
  `tests/security/fixtures/mock_plugin/__init__.py`.
- `mcp_server/plugins/python_plugin/plugin.py` currently bounds chunking for
  the repaired later script and docs-test seams, but its
  `Plugin._BOUNDED_CHUNK_PATHS` also does not include the current
  `tests/security/fixtures/mock_plugin` pair. Those files therefore still
  fall through the normal Python plugin chunking path during lexical walking.
- `mcp_server/cli/repository_commands.py` already advertises exact lexical
  boundary lines for the older docs-governance pair, later docs-test pair,
  verify/simulator, embed/consolidation, and quick-charts seams, but it has
  no dedicated helper yet for
  `tests/security/fixtures/mock_plugin/plugin.py ->
  tests/security/fixtures/mock_plugin/__init__.py`.
- Existing tests freeze adjacent behavior but not this exact later pair.
  `tests/test_dispatcher.py` covers the later docs-test pair and other exact
  bounded Python recoveries; `tests/test_git_index_manager.py` and
  `tests/test_repository_commands.py` preserve durable trace and operator
  wording for those earlier boundaries; and
  `tests/docs/test_semdogfood_evidence_contract.py` already expects the
  dogfood evidence artifact to retain the current mock-plugin blocker pair
  plus downstream steering to `SEMMOCKPLUGIN`.
- `tests/security/test_plugin_sandbox.py` already uses
  `tests.security.fixtures.mock_plugin` as the end-to-end sandbox fixture.
  The SEMMOCKPLUGIN repair must therefore preserve that dotted-path runtime
  contract while tightening lexical walking around the same files.

Practical planning boundary:

- SEMMOCKPLUGIN may tighten exact security-fixture tail handling, dispatcher
  lexical progress accounting, direct Python-plugin bounded chunk behavior,
  durable trace persistence, operator status wording, and the semantic
  dogfood evidence artifact needed to prove a live rerun either advances
  beyond
  `tests/security/fixtures/mock_plugin/plugin.py ->
  tests/security/fixtures/mock_plugin/__init__.py` or surfaces a truthful
  newer blocker.
- SEMMOCKPLUGIN must stay narrow and evidence-driven. It must not reopen the
  repaired docs-test recovery, introduce a blanket
  `tests/security/fixtures/**/*.py` fast path, retune the repo-wide lexical
  watchdog, or reopen older security, sandbox, docs-governance, or script-tail
  seams unless the refreshed rerun directly re-anchors there again.

## Interface Freeze Gates

- [ ] IF-0-SEMMOCKPLUGIN-1 - Later security-fixture tail advance contract:
      a refreshed repo-local force-full rerun on the post-SEMDOCTESTTAIL
      head no longer terminalizes with the durable lexical trace centered on
      `tests/security/fixtures/mock_plugin/plugin.py ->
      tests/security/fixtures/mock_plugin/__init__.py`; it either advances
      durably beyond that pair or emits a truthful newer blocker before the
      120-second watchdog expires.
- [ ] IF-0-SEMMOCKPLUGIN-2 - Exact boundary contract:
      any repair introduced by this phase remains limited to the exact
      mock-plugin fixture pair plus the immediate dispatcher/plugin/trace/status
      plumbing needed to clear it. The phase must not introduce a broader
      `tests/security/fixtures/**/*.py` fast path, and it must not reopen the
      prior `tests/docs/test_gaclose_evidence_closeout.py ->
      tests/docs/test_p8_deployment_security.py` seam without direct
      evidence.
- [ ] IF-0-SEMMOCKPLUGIN-3 - Lexical discoverability contract:
      both exact fixture files remain lexically discoverable after the repair,
      including durable file-level storage plus bounded symbol or content
      discoverability for `Plugin`, `indexFile`, `findReferences`,
      `from .plugin import Plugin`, and `__all__ = ["Plugin"]`, instead of
      turning either fixture into an indexing blind spot.
- [ ] IF-0-SEMMOCKPLUGIN-4 - Sandbox fixture continuity contract:
      the existing runtime contract for
      `SandboxedPlugin("tests.security.fixtures.mock_plugin", ...)` stays
      intact after the repair, including `supports`, `indexFile`, and
      `findReferences` round-trips in `tests/security/test_plugin_sandbox.py`.
- [ ] IF-0-SEMMOCKPLUGIN-5 - Durable trace and operator contract:
      `force_full_exit_trace.json` and `uv run mcp-index repository status`
      stay aligned with the repaired outcome for the exact later mock-plugin
      pair and do not regress to stale SEMDOCTESTTAIL-only wording once the
      live rerun advances past it.
- [ ] IF-0-SEMMOCKPLUGIN-6 - Evidence and downstream steering contract:
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the SEMDOCTESTTAIL
      rerun outcome and the final live verdict for the later security-fixture
      blocker pair; if execution reveals a blocker beyond the current roadmap
      tail, `specs/phase-plans-v7.md` is amended before closeout so the next
      phase-loop step is truthful.

## Lane Index & Dependencies

- SL-0 - Exact mock-plugin fixture freeze; Depends on: SEMDOCTESTTAIL; Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 - Exact mock-plugin bounded indexing repair; Depends on: SL-0; Blocks: SL-2, SL-3, SL-4; Parallel-safe: no
- SL-2 - Durable trace persistence and operator boundary alignment; Depends on: SL-0, SL-1; Blocks: SL-3, SL-4; Parallel-safe: no
- SL-3 - Live rerun evidence reducer and contract refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SL-4; Parallel-safe: no
- SL-4 - Downstream roadmap steering reducer; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: SEMMOCKPLUGIN acceptance; Parallel-safe: no

Lane DAG:

```text
SEMDOCTESTTAIL
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SL-4 -> SEMMOCKPLUGIN acceptance
```

## Lanes

### SL-0 - Exact Mock-Plugin Fixture Freeze

- **Scope**: Freeze the exact
  `tests/security/fixtures/mock_plugin/plugin.py ->
  tests/security/fixtures/mock_plugin/__init__.py` lexical seam in
  deterministic dispatcher coverage before runtime changes so this phase
  proves a narrow repair instead of hand-waving around all security fixtures
  or package `__init__.py` files.
- **Owned files**: `tests/test_dispatcher.py`, `tests/security/test_plugin_sandbox.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMMOCKPLUGIN-1,
  IF-0-SEMMOCKPLUGIN-2,
  IF-0-SEMMOCKPLUGIN-3,
  and IF-0-SEMMOCKPLUGIN-4
- **Interfaces consumed**: existing
  `Dispatcher.index_directory(...)`,
  `Dispatcher._build_exact_bounded_python_shard(...)`,
  normal Python routing through `Plugin.indexFile(...)`,
  and the existing
  `SandboxedPlugin("tests.security.fixtures.mock_plugin", ...)` round-trip
  contract
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` with a repo-shaped fixture that
    indexes exact copies of
    `tests/security/fixtures/mock_plugin/plugin.py` and
    `tests/security/fixtures/mock_plugin/__init__.py`, proves the lexical
    walker records the exact pair in order, and fails if the repair silently
    turns either file into an untracked blind spot.
  - test: In the same dispatcher coverage, assert that
    `tests/security/fixtures/mock_plugin/plugin.py` remains symbol or content
    discoverable for `Plugin`, `indexFile`, and `findReferences`, and that
    `tests/security/fixtures/mock_plugin/__init__.py` remains content
    discoverable for `from .plugin import Plugin` and `__all__ = ["Plugin"]`
    after the repair.
  - test: Use `tests/security/test_plugin_sandbox.py` as the runtime guardrail
    for the dotted-path fixture import surface, extending it only if the
    exact bounded repair would otherwise leave the lexical fix uncorrelated
    with the existing sandbox round-trip assertions.
  - test: Add a negative guard that unrelated files outside the exact pair,
    especially the cleared docs-test seam and unrelated security tests, still
    use their own existing bounded or normal handling. The watchdog repair
    must not quietly become a broader fixture-package fast path.
  - impl: Keep fixtures deterministic with repo-local Python strings and
    monkeypatched bounded-path instrumentation rather than long-running live
    waits inside unit tests.
  - impl: Keep this lane on contract freeze only. Do not mutate durable
    trace, CLI wording, evidence docs, or roadmap steering here.
  - verify: `uv run pytest tests/test_dispatcher.py tests/security/test_plugin_sandbox.py -q --no-cov -k "mock_plugin or lexical or bounded or sandbox or fixture"`

### SL-1 - Exact Mock-Plugin Bounded Indexing Repair

- **Scope**: Implement the smallest dispatcher and Python-plugin repair
  needed so the live lexical walker no longer burns its watchdog budget on
  the exact
  `tests/security/fixtures/mock_plugin/plugin.py ->
  tests/security/fixtures/mock_plugin/__init__.py` security-fixture pair.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `mcp_server/plugins/python_plugin/plugin.py`
- **Interfaces provided**: IF-0-SEMMOCKPLUGIN-2 exact boundary contract;
  IF-0-SEMMOCKPLUGIN-3 lexical discoverability contract;
  IF-0-SEMMOCKPLUGIN-4 sandbox fixture continuity contract
- **Interfaces consumed**: SL-0 fixture expectations; existing exact bounded
  Python behavior in
  `Dispatcher._build_exact_bounded_python_shard(...)`; current Python bounded
  chunk rules in `Plugin._BOUNDED_CHUNK_PATHS`; and the existing runtime
  sandbox fixture behavior
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 dispatcher slice first and confirm which side of the
    pair still consumes watchdog budget in the current force-full path: the
    import-heavy `plugin.py`, the tiny `__init__.py`, or the handoff between
    them.
  - impl: Apply the narrowest repair that clears the exact pair. Prefer
    exact-path bounded handling over any broader security-fixture shortcut,
    and keep the repair local to the dispatcher or the relevant Python plugin
    path.
  - impl: Preserve class and method discoverability for
    `tests/security/fixtures/mock_plugin/plugin.py`, including `Plugin`,
    `supports`, `indexFile`, `getDefinition`, `findReferences`, and `search`,
    instead of reducing the file to an opaque skipped artifact.
  - impl: Preserve direct content discoverability for
    `tests/security/fixtures/mock_plugin/__init__.py`, including
    `from .plugin import Plugin` and `__all__ = ["Plugin"]`.
  - impl: Do not widen `_EXACT_BOUNDED_PYTHON_PATHS` or
    `Plugin._BOUNDED_CHUNK_PATHS` beyond what is needed for this exact pair,
    and do not mutate the runtime behavior of the sandbox fixture itself
    unless the targeted tests prove the lexical repair cannot be isolated from
    it.
  - verify: `uv run pytest tests/test_dispatcher.py tests/security/test_plugin_sandbox.py -q --no-cov -k "mock_plugin or lexical or bounded or sandbox or fixture"`

### SL-2 - Durable Trace Persistence And Operator Boundary Alignment

- **Scope**: Carry the exact later mock-plugin repair into the durable
  force-full trace and operator status surfaces so runtime reporting
  truthfully distinguishes the cleared pair from any later blocker.
- **Owned files**: `mcp_server/storage/git_index_manager.py`, `mcp_server/cli/repository_commands.py`, `tests/test_git_index_manager.py`, `tests/test_repository_commands.py`
- **Interfaces provided**: IF-0-SEMMOCKPLUGIN-1 later security-fixture tail
  advance contract; IF-0-SEMMOCKPLUGIN-5 durable trace and operator
  contract
- **Interfaces consumed**: SL-0 fixture expectations; SL-1 repaired exact
  mock-plugin bounded indexing behavior; existing
  `force_full_exit_trace.json` persistence in `GitAwareIndexManager`; and
  current operator boundary helpers in `repository_commands.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_git_index_manager.py` so durable trace fixtures
    preserve the exact
    `tests/security/fixtures/mock_plugin/plugin.py ->
    tests/security/fixtures/mock_plugin/__init__.py` blocker when it is
    active and prove the rerun advances to a newer blocker without regressing
    to the cleared SEMDOCTESTTAIL seam.
  - test: Extend `tests/test_repository_commands.py` so `repository status`
    advertises the repaired exact bounded lexical surface for the later
    mock-plugin pair and still prints the correct later
    `last_progress_path` and `in_flight_path` when the live blocker moves
    forward.
  - impl: Add the minimal `repository status` helper or wording needed to
    name the exact mock-plugin fixture pair once the repair is in place,
    matching the existing style used for the earlier docs-governance,
    docs-test, and exact script seams.
  - impl: Preserve truthful terminalization behavior when the live command
    times out or fails later. This lane must not relabel a later blocker as if
    the mock-plugin seam were still active once the rerun has moved on.
  - impl: Keep earlier boundary wording for
    `tests/docs/test_gaclose_evidence_closeout.py ->
    tests/docs/test_p8_deployment_security.py`,
    `tests/docs/test_mre2e_evidence_contract.py ->
    tests/docs/test_gagov_governance_contract.py`, and
    `scripts/create_semantic_embeddings.py ->
    scripts/consolidate_real_performance_data.py` intact unless the rerun
    directly proves one of those seams has regressed.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "mock_plugin or lexical or interrupted or boundary or sandbox or fixture"`

### SL-3 - Live Rerun Evidence Reducer And Contract Refresh

- **Scope**: Refresh the real dogfood evidence after the exact later
  mock-plugin repair so the active blocker report matches the repaired
  runtime rather than stale SEMDOCTESTTAIL assumptions.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: the evidence portion of
  IF-0-SEMMOCKPLUGIN-6
- **Interfaces consumed**: SL-2 durable trace and repository-status output;
  live rerun command output; existing SEMDOCTESTTAIL evidence block; and the
  current evidence-contract assertions in
  `tests/docs/test_semdogfood_evidence_contract.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/docs/test_semdogfood_evidence_contract.py` only as
    needed so the status artifact must retain the exact current blocker pair,
    the SEMMOCKPLUGIN phase name, and any newly exposed downstream steering
    after execution.
  - impl: Run a fresh repo-local force-full rerun after SL-1 and SL-2 land,
    then capture the rerun command, observed commit, timeout or completion
    timestamp, durable trace snapshot, `repository status` output, and SQLite
    counts in `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`.
  - impl: If the repaired rerun still times out, record the exact later
    blocker pair that replaced
    `tests/security/fixtures/mock_plugin/plugin.py ->
    tests/security/fixtures/mock_plugin/__init__.py` rather than leaving the
    older pair as the active narrative.
  - impl: Keep this lane on evidence reduction. Do not back-edit older phase
    narratives except where the new rerun explicitly supersedes the active
    blocker statement.
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`

### SL-4 - Downstream Roadmap Steering Reducer

- **Scope**: Keep the roadmap and next phase-loop step truthful if the
  repaired live rerun proves a newer blocker beyond the current roadmap tail.
- **Owned files**: `specs/phase-plans-v7.md`
- **Interfaces provided**: the downstream-steering portion of
  IF-0-SEMMOCKPLUGIN-6
- **Interfaces consumed**: SL-3 refreshed evidence verdict; current roadmap
  DAG and phase ordering for `specs/phase-plans-v7.md`; canonical
  `.phase-loop/` expectation that the next unplanned phase reflects the
  latest durable blocker rather than stale prior assumptions
- **Parallel-safe**: no
- **Tasks**:
  - test: Re-read the post-SL-3 evidence and confirm whether the repaired
    rerun actually exposes a newer blocker beyond the current roadmap tail
    before mutating roadmap steering.
  - impl: If the active blocker is still the exact later mock-plugin fixture
    pair, leave the roadmap unchanged.
  - impl: If the active blocker advances beyond the pair and no downstream
    phase already covers it, append the nearest truthful downstream recovery
    phase to `specs/phase-plans-v7.md` with the same evidence-first
    structure used by the current SEM* lexical-recovery chain.
  - impl: Keep any roadmap mutation limited to the newly exposed blocker.
    Do not rewrite earlier phases or backfill unrelated sequencing while
    closing this seam.
  - verify: `git diff -- specs/phase-plans-v7.md`

## Verification

- Lane checks:
  - `uv run pytest tests/test_dispatcher.py tests/security/test_plugin_sandbox.py -q --no-cov -k "mock_plugin or lexical or bounded or sandbox or fixture"`
  - `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "mock_plugin or lexical or interrupted or boundary or sandbox or fixture"`
  - `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
- Whole-phase checks:
  - `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/security/test_plugin_sandbox.py tests/test_git_index_manager.py tests/test_repository_commands.py tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "mock_plugin or lexical or bounded or interrupted or boundary or sandbox or fixture"`
  - `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  - `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - `sed -n '1,240p' .mcp-index/force_full_exit_trace.json`
  - `sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'`
  - `git diff --check`
  - `git diff --cached --check`

## Acceptance Criteria

- [ ] A refreshed repo-local force-full rerun on the post-SEMDOCTESTTAIL
      head either advances durably beyond
      `tests/security/fixtures/mock_plugin/plugin.py ->
      tests/security/fixtures/mock_plugin/__init__.py` or emits a truthful
      newer blocker before the 120-second watchdog expires.
- [ ] The repair stays narrowly scoped to the exact later mock-plugin
      fixture pair and the immediate dispatcher/plugin/trace/status/evidence
      plumbing needed to prove it.
- [ ] Both exact fixture files remain lexically discoverable with durable
      file-level storage plus bounded symbol or content discoverability for
      `Plugin`, `indexFile`, `findReferences`, `from .plugin import Plugin`,
      and `__all__ = ["Plugin"]`.
- [ ] `SandboxedPlugin("tests.security.fixtures.mock_plugin", ...)`
      round-trips still pass for `supports`, `indexFile`, and
      `findReferences`.
- [ ] `uv run mcp-index repository status` and
      `force_full_exit_trace.json` stay aligned with the repaired later
      mock-plugin boundary outcome and do not regress to stale
      SEMDOCTESTTAIL wording.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the SEMDOCTESTTAIL
      rerun outcome and the final live verdict for the later mock-plugin
      fixture pair.
- [ ] If execution reveals a newer blocker beyond the current roadmap tail,
      `specs/phase-plans-v7.md` is updated before closeout so the next
      phase-loop step is truthful.

automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMMOCKPLUGIN.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMMOCKPLUGIN.md
  artifact_state: staged
