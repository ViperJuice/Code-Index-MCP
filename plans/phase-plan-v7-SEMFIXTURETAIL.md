---
phase_loop_plan_version: 1
phase: SEMFIXTURETAIL
roadmap: specs/phase-plans-v7.md
roadmap_sha256: 0bc5d7fcaa69e0f2854a295aa4b291c7a6b96183e16b2a68b683c4f88a1ca3f4
---
# SEMFIXTURETAIL: Fixture Tail Recovery

## Context

SEMFIXTURETAIL is the phase-68 follow-up for the v7 semantic hardening
roadmap. Canonical `.phase-loop/` state is authoritative for this run, and
legacy `.codex/phase-loop/` artifacts remain compatibility-only. The current
`.phase-loop/` handoff still reports `SEMOPTREPORTTAIL` as `blocked` because
the latest execute turn left unrelated runtime artifacts dirty, but the same
canonical state already records `SEMFIXTURETAIL` as the next `unplanned`
downstream phase and the repo-local evidence artifact shows that
SEMOPTREPORTTAIL cleared its named generated-report seam and advanced the live
force-full rerun later to the fixture pair
`tests/fixtures/multi_repo.py ->
tests/fixtures/files/test_files/example.c`. This planning artifact freezes
that later seam so the next execution slice can stay narrow and
evidence-driven.

Current repo state gathered during planning:

- Canonical `.phase-loop/state.json` and `.phase-loop/tui-handoff.md` record
  `roadmap = specs/phase-plans-v7.md`, the required roadmap hash
  `0bc5d7fcaa69e0f2854a295aa4b291c7a6b96183e16b2a68b683c4f88a1ca3f4`, a
  current phase of `SEMOPTREPORTTAIL`, and `SEMFIXTURETAIL` as the next
  `unplanned` downstream phase.
- `sha256sum specs/phase-plans-v7.md` currently matches the required
  `0bc5d7fcaa69e0f2854a295aa4b291c7a6b96183e16b2a68b683c4f88a1ca3f4`.
- Live git topology at planning time is `main...origin/main [ahead 130]` on
  `HEAD` `f2600b653977bbad865654414a8d6b841b13c5f7`, and the worktree is not
  clean because the latest SEMOPTREPORTTAIL execute run left both phase-owned
  edits and unrelated runtime artifacts in place.
- The target artifact `plans/phase-plan-v7-SEMFIXTURETAIL.md` did not exist
  before this planning run.
- The current canonical blocker is not a planning blocker. The runner reports
  unowned dirty runtime artifacts
  `.index_metadata.json`,
  `.mcp-index/force_full_exit_trace.json`,
  `.mcp-index/semantic_qdrant/.lock`,
  and `.mcp-index/semantic_qdrant/meta.json`. This phase plan should not try
  to clean or normalize them, but SEMFIXTURETAIL execution must preserve or
  isolate them before a new autonomous rerun is treated as closeout-safe.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is the active evidence anchor. Its
  `SEMOPTREPORTTAIL Live Rerun Check` block records that the refreshed
  repo-local command
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  started on observed commit `f2600b65`, remained a running lexical snapshot
  at `2026-04-29T21:34:54Z` with
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/tests/fixtures/multi_repo.py`
  and
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/tests/fixtures/files/test_files/example.c`,
  and then terminalized at `2026-04-29T21:35:04Z` to `Trace status:
  interrupted` with the same exact pair.
- The SEMOPTREPORTTAIL target pair is no longer the active blocker:
  `final_optimized_report_final_report_1750958096/final_report_data.json ->
  final_optimized_report_final_report_1750958096/FINAL_OPTIMIZED_ANALYSIS_REPORT.md`.
  Older downstream assumptions that still treat that generated-report seam as
  current should be considered stale.
- The newly exposed pair is a code-fixture seam rather than a document seam.
  `tests/fixtures/multi_repo.py` is a heavyweight Python integration-test
  helper at `525` lines / `18505` bytes, while
  `tests/fixtures/files/test_files/example.c` is a small C sample at
  `21` lines / `527` bytes.
- `mcp_server/dispatcher/dispatcher_enhanced.py` already carries exact bounded
  Python handling for several prior lexical seams, but `_EXACT_BOUNDED_PYTHON_PATHS`
  does not yet name `tests/fixtures/multi_repo.py`, and there is no exact
  fixture-tail boundary contract there today.
- `mcp_server/cli/repository_commands.py` currently advertises exact bounded
  lexical surfaces for earlier Python, JSON, shell, Markdown, and mixed-plan
  seams, but it does not yet expose dedicated operator wording for the later
  `tests/fixtures/multi_repo.py ->
  tests/fixtures/files/test_files/example.c` seam.
- Existing tests already freeze adjacent behavior but not the exact fixture
  pair contract. `tests/test_dispatcher.py` covers the generated-report and
  earlier lexical boundaries, `tests/test_git_index_manager.py` and
  `tests/test_repository_commands.py` preserve durable trace and operator
  wording for those earlier seams, and
  `tests/docs/test_semdogfood_evidence_contract.py` already requires the
  evidence report to mention `SEMOPTREPORTTAIL` acceptance, the fixture pair,
  and roadmap steering to `SEMFIXTURETAIL`. What is missing is the
  execution-ready contract that binds dispatcher behavior, durable trace
  progression, operator wording, evidence refresh, and possible downstream
  roadmap steering to this exact later fixture seam.

Practical planning boundary:

- SEMFIXTURETAIL may tighten exact fixture-pair handling, dispatcher lexical
  progress accounting, durable trace persistence, operator status wording, the
  semantic dogfood evidence artifact, and downstream roadmap steering needed
  to prove a live rerun either advances beyond
  `tests/fixtures/multi_repo.py ->
  tests/fixtures/files/test_files/example.c` or surfaces a truthful newer
  blocker.
- SEMFIXTURETAIL must stay narrow and evidence-driven. It must not reopen the
  repaired SEMOPTREPORTTAIL generated-report seam, introduce a blanket bypass
  for all fixture Python or C files, retune the repo-wide lexical watchdog, or
  reopen unrelated semantic-stage, roadmap, or release work unless the
  refreshed rerun re-anchors there directly.
- Because the active pair starts with a heavyweight Python fixture and ends
  with a tiny C sample, execution should first prefer exact-path or exact-pair
  lexical narrowing around `tests/fixtures/multi_repo.py` before simplifying
  fixture contents. Any direct edits to the fixture files must preserve test
  meaning and stay limited to lexical-structure concerns proved necessary by
  the refreshed rerun.

## Interface Freeze Gates

- [ ] IF-0-SEMFIXTURETAIL-1 - Fixture pair advance contract:
      a refreshed repo-local force-full rerun on the post-SEMOPTREPORTTAIL
      head no longer terminalizes with the durable lexical trace centered on
      `tests/fixtures/multi_repo.py ->
      tests/fixtures/files/test_files/example.c`; it either advances durably
      beyond that pair or emits a truthful newer blocker before the
      120-second watchdog expires.
- [ ] IF-0-SEMFIXTURETAIL-2 - Exact boundary contract:
      any repair introduced by this phase remains limited to the exact
      `tests/fixtures/multi_repo.py ->
      tests/fixtures/files/test_files/example.c` pair and the immediate
      dispatcher, trace, status, evidence, and roadmap-steering plumbing
      needed to clear it. The phase must not introduce a blanket
      `tests/fixtures/**/*.py`, `tests/fixtures/files/**/*.c`, or broader
      fixture bypass.
- [ ] IF-0-SEMFIXTURETAIL-3 - Lexical discoverability contract:
      both exact fixture files remain lexically discoverable after the repair,
      including durable file storage plus bounded symbol or content
      discoverability for `build_temp_repo`, `TestServerHandle`, and the C
      fixture's struct/function surface instead of turning either file into an
      indexing blind spot.
- [ ] IF-0-SEMFIXTURETAIL-4 - Durable trace and operator contract:
      `force_full_exit_trace.json` and `uv run mcp-index repository status`
      stay aligned with the repaired outcome for the exact
      `tests/fixtures/multi_repo.py ->
      tests/fixtures/files/test_files/example.c` pair and do not regress to
      stale SEMOPTREPORTTAIL-only wording once the live rerun advances beyond
      it.
- [ ] IF-0-SEMFIXTURETAIL-5 - Evidence and downstream steering contract:
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the SEMOPTREPORTTAIL
      rerun outcome, the SEMFIXTURETAIL rerun command and timestamps, the
      refreshed trace and status output, and the final authoritative verdict
      for the fixture pair; if execution reveals a blocker beyond the current
      roadmap tail, `specs/phase-plans-v7.md` is amended before closeout so
      the next phase-loop step is truthful.

## Lane Index & Dependencies

- SL-0 - Exact fixture-pair contract freeze; Depends on: SEMOPTREPORTTAIL; Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 - Bounded fixture-pair execution-path repair or minimal fixture-local simplification; Depends on: SL-0; Blocks: SL-2, SL-3, SL-4; Parallel-safe: no
- SL-2 - Durable trace persistence and operator boundary alignment; Depends on: SL-0, SL-1; Blocks: SL-3, SL-4; Parallel-safe: no
- SL-3 - Live rerun evidence reducer and SEMFIXTURETAIL contract refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SL-4; Parallel-safe: no
- SL-4 - Downstream roadmap steering reducer; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: SEMFIXTURETAIL acceptance; Parallel-safe: no

Lane DAG:

```text
SEMOPTREPORTTAIL
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SL-4 -> SEMFIXTURETAIL acceptance
```

## Lanes

### SL-0 - Exact Fixture-Pair Contract Freeze

- **Scope**: Freeze the exact
  `tests/fixtures/multi_repo.py ->
  tests/fixtures/files/test_files/example.c` lexical seam in deterministic
  dispatcher coverage before runtime changes so this phase proves a narrow
  recovery instead of assuming generic fixture indexing is already sufficient.
- **Owned files**: `tests/test_dispatcher.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMFIXTURETAIL-1,
  IF-0-SEMFIXTURETAIL-2,
  and IF-0-SEMFIXTURETAIL-3 at the dispatcher boundary
- **Interfaces consumed**: existing
  `Dispatcher.index_directory(...)`,
  `_EXACT_BOUNDED_PYTHON_PATHS`,
  the current Python and C indexing paths,
  and the SEMOPTREPORTTAIL evidence for the later fixture pair
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` with a repo-shaped fixture that
    indexes exact copies or trimmed representatives of
    `tests/fixtures/multi_repo.py` and
    `tests/fixtures/files/test_files/example.c`, proves the lexical walker
    records the exact pair in order, and fails if the repair silently turns
    either file into an untracked blind spot.
  - test: In the same dispatcher coverage, assert that the repaired path keeps
    document or symbol discoverability for the Python fixture helper surface
    (`build_temp_repo`, `TestServerHandle`, and related headings/docstrings)
    and the C sample surface (`Employee`, `createEmployee`, `printEmployee`).
  - test: Add a negative guard that unrelated fixture Python or C files
    outside the exact pair still use the normal indexing path; the watchdog
    repair must not quietly become a broader fixture bypass.
  - impl: Keep fixtures deterministic with repo-local source strings and
    monkeypatched bounded-path instrumentation rather than long-running live
    waits inside unit tests.
  - impl: Keep this lane on contract freeze only. Do not mutate durable trace,
    CLI wording, evidence docs, roadmap steering, or the checked-in fixture
    source files here.
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "multi_repo or example_c or fixture_tail or lexical or bounded"`

### SL-1 - Bounded Fixture-Pair Execution-Path Repair Or Minimal Fixture-Local Simplification

- **Scope**: Implement the smallest dispatcher or fixture-local repair needed
  so the live lexical walker no longer burns its watchdog budget on the exact
  `tests/fixtures/multi_repo.py ->
  tests/fixtures/files/test_files/example.c` pair.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `tests/fixtures/multi_repo.py`, `tests/fixtures/files/test_files/example.c`
- **Interfaces provided**: IF-0-SEMFIXTURETAIL-2 exact boundary contract;
  IF-0-SEMFIXTURETAIL-3 lexical discoverability contract
- **Interfaces consumed**: SL-0 fixture-pair dispatcher fixtures; existing
  exact bounded Python path handling in `dispatcher_enhanced.py`; the current
  structure of `tests/fixtures/multi_repo.py`; and the current structure of
  `tests/fixtures/files/test_files/example.c`
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 dispatcher slice first and confirm whether the active
    cost is concentrated on `tests/fixtures/multi_repo.py` itself or only at
    the exact handoff into `tests/fixtures/files/test_files/example.c`.
  - impl: Apply the narrowest repair that clears the exact pair. Prefer
    reusing the existing exact bounded Python-path mechanism for
    `tests/fixtures/multi_repo.py` while keeping `example.c` on the normal C
    indexing path if that alone clears the seam.
  - impl: Only simplify `tests/fixtures/multi_repo.py` or
    `tests/fixtures/files/test_files/example.c` if the tests prove path
    handling alone is insufficient. Preserve fixture semantics and keep edits
    lexical-structure-oriented rather than changing test meaning.
  - impl: Preserve stored file rows plus discoverability for both fixtures;
    the repair must not turn either file into an ignored source document or
    silently remove it from lexical FTS.
  - impl: Keep the repair exact-file or exact-pair narrow. Do not add a broad
    `tests/fixtures/**/*.py`, `tests/fixtures/files/**/*.c`, or repo-wide
    source bypass.
  - verify: `rg -n "tests/fixtures/multi_repo.py|tests/fixtures/files/test_files/example.c|_EXACT_BOUNDED_PYTHON_PATHS|bounded|fixture" mcp_server/dispatcher/dispatcher_enhanced.py tests/fixtures/multi_repo.py tests/fixtures/files/test_files/example.c tests/test_dispatcher.py`
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "multi_repo or example_c or fixture_tail or lexical or bounded"`

### SL-2 - Durable Trace Persistence And Operator Boundary Alignment

- **Scope**: Carry the chosen fixture-pair repair through force-full closeout
  and keep the operator-facing status surface aligned with the exact later
  pair that was repaired.
- **Owned files**: `mcp_server/storage/git_index_manager.py`, `mcp_server/cli/repository_commands.py`, `tests/test_git_index_manager.py`, `tests/test_repository_commands.py`
- **Interfaces provided**: IF-0-SEMFIXTURETAIL-1 fixture-pair advance
  contract; IF-0-SEMFIXTURETAIL-4 durable trace and operator contract
- **Interfaces consumed**: SL-0 dispatcher fixtures; SL-1 chosen repair;
  existing lexical progress snapshot fields, durable
  `force_full_exit_trace.json` persistence, and the current status wording for
  the repaired generated-report seam
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_git_index_manager.py` so force-full durable trace
    coverage preserves the exact `tests/fixtures/multi_repo.py ->
    tests/fixtures/files/test_files/example.c` pair when that seam is still
    active, then proves the trace advances beyond both files once the repair
    is in place without regressing to stale SEMOPTREPORTTAIL generated-report
    wording.
  - test: Extend `tests/test_repository_commands.py` so
    `uv run mcp-index repository status` continues to render the existing
    repaired lexical boundaries while adding truthful operator guidance for
    the later fixture seam.
  - impl: Thread the chosen repair through durable trace persistence and
    operator wording only as needed so the rerun can advance beyond the exact
    pair.
  - impl: Preserve the existing force-full trace fields, fail-closed
    indexed-commit behavior, and lexical watchdog semantics. This lane should
    move the handoff forward, not rename stages or declare readiness early.
  - impl: If SL-1 alone is sufficient and no runtime storage change is
    required, keep this lane scoped to status wording plus trace fixtures
    rather than inventing extra persistence behavior.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "multi_repo or example_c or fixture_tail or interrupted or boundary or lexical"`

### SL-3 - Live Rerun Evidence Reducer And SEMFIXTURETAIL Contract Refresh

- **Scope**: Refresh the repo-local dogfood report so it records the chosen
  fixture-tail repair, the rerun outcome, and the next exact downstream status
  after this seam is cleared.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: IF-0-SEMFIXTURETAIL-4 durable trace and operator
  contract; IF-0-SEMFIXTURETAIL-5 evidence and downstream steering contract
- **Interfaces consumed**: SL-1 chosen repair; SL-2 rerun command, durable
  trace, and repository-status wording; roadmap SEMFIXTURETAIL exit criteria;
  prior SEMOPTREPORTTAIL evidence lineage
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/docs/test_semdogfood_evidence_contract.py` so the
    refreshed report cites `tests/fixtures/multi_repo.py`,
    `tests/fixtures/files/test_files/example.c`, the chosen repair, the rerun
    outcome, and the final authoritative verdict for the fixture pair.
  - test: Require the report to preserve the existing evidence lineage for the
    already cleared generated-report seam while making clear that the active
    current-head blocker has moved later to the fixture pair or beyond.
  - impl: Update `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` with the live
    SEMFIXTURETAIL rerun command, timestamps, refreshed trace snapshot,
    repository-status terminalization, and current SQLite counts so the report
    proves whether the repaired rerun advanced beyond the pair or surfaced a
    newer blocker.
  - impl: If the rerun advances to a later blocker, make the report name that
    blocker exactly and mark the fixture seam as cleared. If the rerun still
    ends at the exact pair, keep the report truthful and do not pretend the
    boundary is repaired.
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
  - verify: `rg -n "SEMFIXTURETAIL|multi_repo.py|example.c|SEMOPTREPORTTAIL|force_full_exit_trace|Trace status|roadmap now adds downstream phase" docs/status/SEMANTIC_DOGFOOD_REBUILD.md tests/docs/test_semdogfood_evidence_contract.py`

### SL-4 - Downstream Roadmap Steering Reducer

- **Scope**: Keep the roadmap and next phase-loop step truthful if the
  repaired live rerun proves a newer blocker beyond the current roadmap tail.
- **Owned files**: `specs/phase-plans-v7.md`
- **Interfaces provided**: the downstream-steering portion of
  IF-0-SEMFIXTURETAIL-5
- **Interfaces consumed**: SL-3 refreshed evidence verdict; current roadmap
  DAG and phase ordering for `specs/phase-plans-v7.md`; canonical
  `.phase-loop/` expectation that the next unplanned phase reflects the latest
  durable blocker rather than stale prior assumptions
- **Parallel-safe**: no
- **Tasks**:
  - test: Re-read the post-SL-3 evidence and confirm whether the repaired
    rerun actually exposes a newer blocker beyond the current roadmap tail
    before mutating roadmap steering.
  - impl: If the active blocker is still the exact
    `tests/fixtures/multi_repo.py ->
    tests/fixtures/files/test_files/example.c` pair, leave the roadmap
    unchanged.
  - impl: If the active blocker advances beyond the pair and no downstream
    phase already covers it, append the nearest truthful downstream recovery
    phase to `specs/phase-plans-v7.md` with the same evidence-first structure
    used by the current SEM* lexical-recovery chain.
  - impl: Keep any roadmap mutation limited to the newly exposed blocker. Do
    not rewrite earlier phases or backfill unrelated sequencing while closing
    this seam.
  - verify: `git diff -- specs/phase-plans-v7.md`

## Verification

- Lane checks:
  - `uv run pytest tests/test_dispatcher.py -q --no-cov -k "multi_repo or example_c or fixture_tail or lexical or bounded"`
  - `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "multi_repo or example_c or fixture_tail or interrupted or boundary or lexical"`
  - `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
- Whole-phase checks:
  - `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_repository_commands.py tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "multi_repo or example_c or fixture_tail or lexical or bounded or interrupted or boundary"`
  - `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  - `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - `sed -n '1,240p' .mcp-index/force_full_exit_trace.json`
  - `sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'`
  - `git diff --check`
  - `git diff --cached --check`

## Acceptance Criteria

- [ ] A refreshed repo-local force-full rerun on the post-SEMOPTREPORTTAIL
      head either advances durably beyond
      `tests/fixtures/multi_repo.py ->
      tests/fixtures/files/test_files/example.c` or emits a truthful newer
      blocker before the 120-second watchdog expires.
- [ ] The chosen repair stays narrowly scoped to the exact fixture pair and
      the immediate dispatcher/trace/status/evidence plumbing needed to prove
      it.
- [ ] The chosen repair does not reopen the repaired
      `final_optimized_report_final_report_1750958096/final_report_data.json ->
      final_optimized_report_final_report_1750958096/FINAL_OPTIMIZED_ANALYSIS_REPORT.md`
      boundary without direct new evidence.
- [ ] The repair does not introduce a blanket bypass for all fixture Python or
      C files.
- [ ] Both exact fixture files remain lexically discoverable with durable file
      storage plus bounded symbol or content discoverability for the Python
      helper surface and the C sample surface.
- [ ] `uv run mcp-index repository status` and
      `force_full_exit_trace.json` stay aligned with the repaired fixture
      boundary outcome and do not regress to stale SEMOPTREPORTTAIL wording.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the SEMOPTREPORTTAIL
      rerun outcome and the final live verdict for the later
      `tests/fixtures/multi_repo.py ->
      tests/fixtures/files/test_files/example.c` pair.
- [ ] If execution reveals a newer blocker beyond the current roadmap tail,
      `specs/phase-plans-v7.md` is updated before closeout so the next
      phase-loop step is truthful.

automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMFIXTURETAIL.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMFIXTURETAIL.md
  artifact_state: staged
