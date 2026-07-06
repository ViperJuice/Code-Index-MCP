---
phase_loop_plan_version: 1
phase: SEMTRACEFRESHNESS
roadmap: specs/phase-plans-v7.md
roadmap_sha256: 27e3d66dafe449514164e1833456f69e88fbb0bc6a6d7d46eb6d4adc9508bc8c
---
# SEMTRACEFRESHNESS: Force-Full Trace Freshness Recovery

## Context

SEMTRACEFRESHNESS is the phase-30 follow-up for the v7 semantic hardening
roadmap. SEMJEDI proved the exact bounded Markdown repair for
`ai_docs/jedi.md`, but the live repo-local force-full rerun still did not
close cleanly and the durable trace stopped reflecting the current in-flight
work.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is tracked and clean in this worktree, and both
  `sha256sum specs/phase-plans-v7.md` and `.phase-loop/state.json` match the
  required roadmap SHA
  `27e3d66dafe449514164e1833456f69e88fbb0bc6a6d7d46eb6d4adc9508bc8c`.
- The checkout is on `main` at
  `85d7484a8ad0add82e9b333a7a4ae19d9d08ee8e`, `main...origin/main` is ahead by
  `55` commits, the worktree is clean before writing this artifact, and
  `plans/phase-plan-v7-SEMTRACEFRESHNESS.md` did not exist before this run.
- Canonical `.phase-loop/state.json` already marks `SEMTRACEFRESHNESS` as the
  current unplanned phase on this roadmap, and `.phase-loop/tui-handoff.md`
  says the next run should plan this phase. Legacy `.codex/phase-loop/` state
  is not needed or consulted.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is the active blocker artifact for
  this phase. Its SEMJEDI evidence snapshot (`2026-04-29T08:35:12Z`, observed
  commit `7335cf35`) records that the durable
  `force_full_exit_trace.json` no longer points at `ai_docs/jedi.md`, but the
  live rerun still hung after the trace stopped refreshing at
  `trace_timestamp=2026-04-29T08:33:47Z` with
  `stage=lexical_walking`, `blocker_source=lexical_mutation`,
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/ai_docs/pytest_overview.md`,
  and no recorded `in_flight_path`.
- The current checkout still has `.mcp-index/current.db`, but there is no
  `.mcp-index/force_full_exit_trace.json` on disk at planning time. That is
  not a blocker, but it means SEMTRACEFRESHNESS execution must recreate the
  runtime trace from a fresh repo-local rerun rather than relying on a
  preserved stale trace file.
- `EnhancedDispatcher.index_directory(...)` currently carries
  `last_progress_path` and `in_flight_path` in its shared `stats` payload, but
  the lexical path only calls `emit_progress(...)` after a file finishes or
  after a timeout/failure is raised. `_index_file_with_lexical_timeout(...)`
  sets `stats["in_flight_path"]` before the blocking file index call, yet that
  new in-flight state is not pushed to the force-full trace until a later
  progress emission happens.
- `GitAwareIndexManager._make_force_full_progress_callback(...)` persists
  whatever dispatcher snapshots it receives into
  `.mcp-index/force_full_exit_trace.json`, and `_write_force_full_exit_trace(...)`
  refreshes `trace_timestamp` on each write. The stale-trace gap is therefore
  downstream of when snapshots are emitted, not in the atomic file-write path
  itself.
- `mcp_server/cli/repository_commands.py::_print_force_full_exit_trace(...)`
  only prints the trace fields that are present. Together with the missing
  on-disk trace today, that means SEMTRACEFRESHNESS must keep operator output
  honest when a rerun is in flight, blocked, completed, or missing a fresh
  trace artifact altogether.
- Existing coverage already defines the adjacent contract surfaces:
  `tests/test_dispatcher.py` covers lexical and semantic progress snapshots,
  `tests/test_git_index_manager.py` covers durable force-full trace persistence
  and closeout semantics, `tests/test_repository_commands.py` covers operator
  status wording for force-full traces and prior lexical boundaries, and
  `tests/docs/test_semdogfood_evidence_contract.py` keeps the status document
  aligned with the latest rerun evidence.

Practical planning boundary:

- SEMTRACEFRESHNESS may tighten dispatcher progress emission, durable
  force-full trace persistence, and repository-status wording so a fresh
  repo-local rerun either keeps naming the current in-flight path as work
  advances or exits promptly with a completed or bounded blocked trace.
- SEMTRACEFRESHNESS must stay on trace freshness, force-full closeout, and the
  evidence reducer. It must not reopen the exact `ai_docs/jedi.md`,
  `ai_docs/*_overview.md`, fast-report, or visual-report-script lexical fixes
  unless a refreshed trace directly re-anchors on one of those seams.

## Interface Freeze Gates

- [ ] IF-0-SEMTRACEFRESHNESS-1 - Lexical trace freshness contract:
      during repo-local `repository sync --force-full`, the durable
      `force_full_exit_trace.json` is refreshed when a new lexical file becomes
      in flight so the trace cannot remain pinned only to an older
      `last_progress_path` while current work proceeds elsewhere.
- [ ] IF-0-SEMTRACEFRESHNESS-2 - Force-full exit contract:
      after the rerun, the durable trace either advances to a later lexical or
      semantic stage with a fresh timestamp and current in-flight path, or the
      command exits with a completed, interrupted, or bounded blocked trace
      that names the true downstream blocker instead of leaving stale
      `status=running` lexical state behind.
- [ ] IF-0-SEMTRACEFRESHNESS-3 - Operator status contract:
      `uv run mcp-index repository status` reports the refreshed trace
      accurately, preserves existing boundary wording from prior phases, and
      does not imply current in-flight progress when the trace artifact is
      missing or stale.
- [ ] IF-0-SEMTRACEFRESHNESS-4 - Evidence contract:
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the rerun command,
      refreshed trace snapshot, rerun outcome, and the next exact blocker if
      semantic-stage work still does not begin.
- [ ] IF-0-SEMTRACEFRESHNESS-5 - Upstream-boundary preservation contract:
      SEMFASTREPORT, SEMPYTESTOVERVIEW, SEMVISUALREPORT, and SEMJEDI remain
      closed unless the refreshed trace directly re-anchors on one of those
      exact seams.

## Lane Index & Dependencies

- SL-0 - Trace freshness contract and stale-trace fixture freeze; Depends on: SEMJEDI; Blocks: SL-1, SL-2, SL-3; Parallel-safe: no
- SL-1 - Dispatcher live progress freshness repair; Depends on: SL-0; Blocks: SL-2, SL-3; Parallel-safe: no
- SL-2 - Durable trace persistence and repository-status clarity; Depends on: SL-0, SL-1; Blocks: SL-3; Parallel-safe: no
- SL-3 - Dogfood evidence reducer and rerun refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SEMTRACEFRESHNESS acceptance; Parallel-safe: no

Lane DAG:

```text
SEMJEDI
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SEMTRACEFRESHNESS acceptance
```

## Lanes

### SL-0 - Trace Freshness Contract And Stale-Trace Fixture Freeze

- **Scope**: Freeze the stale-trace regression precisely before implementation
  so this phase proves a freshness repair instead of only moving the live hang
  to a less visible spot.
- **Owned files**: `tests/test_dispatcher.py`, `tests/test_git_index_manager.py`, `tests/test_repository_commands.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMTRACEFRESHNESS-1 through IF-0-SEMTRACEFRESHNESS-3
- **Interfaces consumed**: existing
  `EnhancedDispatcher.index_directory(...)`,
  `Dispatcher._index_file_with_lexical_timeout(...)`,
  `GitAwareIndexManager._make_force_full_progress_callback(...)`,
  `GitAwareIndexManager.sync_repository_index(...)`,
  `repository status` force-full trace rendering, and the SEMJEDI evidence
  vocabulary for `last_progress_path`, `in_flight_path`, `trace_timestamp`,
  `status`, and `blocker_source`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` with a deterministic long-running
    lexical fixture that reproduces the stale-trace shape: an older
    `last_progress_path` has already been emitted, a new file becomes
    in flight, and the progress callback must receive that updated
    `in_flight_path` before the file returns.
  - test: Extend `tests/test_git_index_manager.py` so force-full sync proves a
    fresh in-flight snapshot is persisted to `force_full_exit_trace.json` and a
    rerun no longer leaves stale `status=running` lexical state behind after
    clean closeout, interruption, or bounded failure.
  - test: Extend `tests/test_repository_commands.py` so `repository status`
    distinguishes a fresh in-flight trace, a completed or blocked trace, and a
    missing trace artifact without regressing the existing fast-report,
    overview-doc, visual-report-script, or exact Jedi boundary wording.
  - impl: Keep fixtures deterministic with monkeypatched dispatcher callbacks,
    synthetic trace payloads, and short-lived fake blocking work rather than
    multi-minute live waits inside unit coverage.
  - impl: Keep this lane focused on contract freeze only. Do not update the
    live dogfood report or rerun the real force-full command here.
  - verify: `uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov`

### SL-1 - Dispatcher Live Progress Freshness Repair

- **Scope**: Repair the lexical progress emission path so force-full tracing
  receives fresh in-flight snapshots while a new file is actively being
  indexed, not only after completion or timeout.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`
- **Interfaces provided**: IF-0-SEMTRACEFRESHNESS-1 lexical trace freshness
  contract at the mutation source
- **Interfaces consumed**: SL-0 dispatcher freshness tests; existing
  `stats["last_progress_path"]`, `stats["in_flight_path"]`,
  `_index_file_with_lexical_timeout(...)`, and lexical
  `emit_progress(...)` snapshots
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 dispatcher slice first and confirm the current lexical
    path only emits progress after completion or timeout, which allows a stale
    durable trace to linger on an older file marker.
  - impl: Add the smallest dispatcher-side freshness repair needed so a new
    lexical file entering `_index_file_with_lexical_timeout(...)` emits an
    updated progress snapshot before the blocking file-index work begins.
  - impl: Preserve current `last_progress_path` semantics: completion still
    moves that field to the finished file, timeout still fails closed with the
    exact low-level blocker, and semantic-stage progress emission remains
    unchanged unless the lexical freshness repair requires a shared helper.
  - impl: Keep this lane local to dispatcher progress emission. Do not widen
    it into broader timeout-duration changes, new lexical filters, or renewed
    exact-path repairs for files already closed in upstream phases.
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "trace or progress or timeout"`

### SL-2 - Durable Trace Persistence And Repository-Status Clarity

- **Scope**: Carry the refreshed dispatcher snapshots through the durable
  force-full trace and keep the operator-facing status surface aligned with the
  true live or terminal state of the rerun.
- **Owned files**: `mcp_server/storage/git_index_manager.py`, `mcp_server/cli/repository_commands.py`
- **Interfaces provided**: IF-0-SEMTRACEFRESHNESS-2 force-full exit contract;
  IF-0-SEMTRACEFRESHNESS-3 operator status contract
- **Interfaces consumed**: SL-0 git-index-manager and CLI fixtures; SL-1 fresh
  dispatcher snapshots; existing `_write_force_full_exit_trace(...)`,
  `_make_force_full_progress_callback(...)`, `_trace_blocker_source(...)`, and
  `_print_force_full_exit_trace(...)`
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 git-index-manager and repository-status slice first and
    keep the existing trace vocabulary stable while making the stored trace
    reflect current in-flight work or a real terminal blocker.
  - impl: Tighten force-full trace persistence only as needed so a new
    dispatcher in-flight snapshot is durably written with a fresh timestamp and
    terminal closeout no longer leaves a stale `running` lexical trace as the
    last on-disk verdict.
  - impl: Keep fail-closed behavior intact. If the rerun still blocks after
    the freshness repair, preserve the exact downstream blocker and do not mark
    readiness or indexed-commit advancement early.
  - impl: Update `repository status` only as needed so operators can tell when
    the trace is actively in flight, terminal, or missing, while preserving the
    explicit prior lexical-boundary reporting from SEMFASTREPORT,
    SEMPYTESTOVERVIEW, SEMVISUALREPORT, and SEMJEDI.
  - impl: If the dispatcher repair alone makes the trace truthful and no CLI
    wording change is required, record that no-op outcome in execution notes
    and keep this lane scoped to durable trace persistence plus live rerun
    proof.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov`
  - verify: `env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - verify: `python - <<'PY'
from pathlib import Path
trace = Path(".mcp-index") / "force_full_exit_trace.json"
print(trace.read_text() if trace.exists() else "missing")
PY`

### SL-3 - Dogfood Evidence Reducer And Rerun Refresh

- **Scope**: Refresh the repo-local dogfood report so it records the
  trace-freshness repair, the rerun outcome, and the next exact blocker if
  semantic-stage work still does not begin.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: IF-0-SEMTRACEFRESHNESS-4 evidence contract;
  IF-0-SEMTRACEFRESHNESS-5 upstream-boundary preservation contract
- **Interfaces consumed**: SL-1 dispatcher freshness repair; SL-2 rerun
  command, durable trace, and repository-status wording; roadmap
  SEMTRACEFRESHNESS exit criteria; prior SEMFASTREPORT, SEMPYTESTOVERVIEW,
  SEMVISUALREPORT, and SEMJEDI evidence lineage
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/docs/test_semdogfood_evidence_contract.py` so the
    refreshed report cites `plans/phase-plan-v7-SEMTRACEFRESHNESS.md`, the new
    rerun command and timestamps, the refreshed or recreated trace artifact,
    and the next exact blocker if semantic-stage work still does not begin.
  - test: Require the report to preserve the upstream fast-report,
    `ai_docs/*_overview.md`, exact visual-report-script, and exact Jedi
    evidence lineage while making clear that the active work item is now trace
    freshness rather than another retry of those seams.
  - test: Require the report to state whether the rerun reached a later lexical
    or semantic stage, exited with a bounded blocked trace, or finally produced
    summary/vector progress.
  - impl: Refresh `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` with the live rerun
    command, observed commit IDs, refreshed trace contents, repository-status
    output, and the steering verdict after the stale-trace gap is repaired.
  - impl: Keep the report factual and durable. Record exact timestamps,
    `last_progress_path`, `in_flight_path`, `status`, stage family, blocker
    source, and chunk/vector counts without claiming semantic success before
    the evidence exists.
  - impl: If the rerun still does not begin semantic work, name the next exact
    blocker directly and make clear that SEMTRACEFRESHNESS itself is complete
    once the durable trace truthfully reports that blocker.
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
  - verify: `rg -n "SEMTRACEFRESHNESS|force_full_exit_trace|Trace status|Trace stage|Last progress path|In-flight path|next exact blocker" docs/status/SEMANTIC_DOGFOOD_REBUILD.md tests/docs/test_semdogfood_evidence_contract.py`

## Verification

Planning-only run: do not execute these during plan creation. Run them during
`codex-execute-phase` or manual SEMTRACEFRESHNESS execution.

Lane-specific checks:

```bash
uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov
uv run pytest tests/test_dispatcher.py -q --no-cov -k "trace or progress or timeout"
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
rg -n "force_full_exit_trace|trace_timestamp|last_progress_path|in_flight_path|SEMTRACEFRESHNESS" \
  mcp_server/dispatcher/dispatcher_enhanced.py \
  mcp_server/storage/git_index_manager.py \
  mcp_server/cli/repository_commands.py \
  docs/status/SEMANTIC_DOGFOOD_REBUILD.md \
  tests/test_dispatcher.py \
  tests/test_git_index_manager.py \
  tests/test_repository_commands.py \
  tests/docs/test_semdogfood_evidence_contract.py
```

Whole-phase regression commands:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest \
  tests/test_dispatcher.py \
  tests/test_git_index_manager.py \
  tests/test_repository_commands.py \
  tests/docs/test_semdogfood_evidence_contract.py \
  -q --no-cov
env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
python - <<'PY'
from pathlib import Path
trace = Path(".mcp-index") / "force_full_exit_trace.json"
print(trace.read_text() if trace.exists() else "missing")
PY
sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'
git status --short -- specs/phase-plans-v7.md plans/phase-plan-v7-SEMTRACEFRESHNESS.md
```

## Acceptance Criteria

- [ ] A live repo-local force-full rerun no longer hangs with
      `force_full_exit_trace.json` frozen at
      `last_progress_path=/home/viperjuice/code/Code-Index-MCP/ai_docs/pytest_overview.md`
      and `in_flight_path=null`.
- [ ] The durable trace refreshes to a later lexical or semantic stage with a
      current in-flight path, or the command exits cleanly with a completed or
      bounded blocked trace.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is refreshed with the
      trace-freshness evidence, the rerun outcome, and the next exact blocker
      if semantic-stage work still does not begin.
- [ ] Tests prove dispatcher progress emission, durable trace persistence, and
      repository-status rendering stay truthful without weakening fail-closed
      timeout behavior.
- [ ] SEMFASTREPORT, SEMPYTESTOVERVIEW, SEMVISUALREPORT, and SEMJEDI remain
      closed unless the refreshed trace directly re-anchors on one of those
      exact seams.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v7-SEMTRACEFRESHNESS.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMTRACEFRESHNESS.md
  artifact_state: staged
```
