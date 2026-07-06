---
phase_loop_plan_version: 1
phase: SEMTESTSTALE
roadmap: specs/phase-plans-v7.md
roadmap_sha256: 0eaeb957a06469ec56d046d96bbab31d88883ee3c5b72f24cb78146600ff7747
---
# SEMTESTSTALE: Post-Devcontainer Test Stale-Trace Recovery

## Context

SEMTESTSTALE is the phase-37 follow-up for the v7 semantic hardening roadmap.
SEMDEVSTALE proved the renewed `.devcontainer/devcontainer.json` seam is
cleared on the current head, but its refreshed live rerun on observed commit
`7e547c77` still exited unexpectedly and left the durable force-full trace
frozen on a later exact lexical pair:
`tests/test_deployment_runbook_shape.py ->
tests/test_reindex_resume.py`.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is the active roadmap, it is tracked and clean in
  this worktree, and `sha256sum specs/phase-plans-v7.md` matches the required
  `0eaeb957a06469ec56d046d96bbab31d88883ee3c5b72f24cb78146600ff7747`.
- Canonical phase-loop state exists under `.phase-loop/`; the active run
  metadata already records a `SEMTESTSTALE` planning launch at
  `.phase-loop/runs/20260429T110251Z-01-semteststale-plan/launch.json`.
  Legacy `.codex/phase-loop/` artifacts are present only for compatibility and
  are not authoritative for this run.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is the active evidence anchor. It
  already records the SEMDEVSTALE live rerun at `2026-04-29T10:55:12Z`, the
  later durable trace pair
  `tests/test_deployment_runbook_shape.py ->
  tests/test_reindex_resume.py`, the abnormal process exit with code `135`,
  and the roadmap steering decision that makes `SEMTESTSTALE` the next slice.
- `mcp_server/dispatcher/dispatcher_enhanced.py` currently emits lexical
  walking snapshots for in-flight files and a
  `force_full_closeout_handoff` snapshot after lexical walking completes.
  This phase must preserve that repaired SEMDEVSTALE handoff and determine
  why a later live force-full run can still stop after advancing into the
  test-file pair without writing a truthful terminal trace.
- `mcp_server/storage/git_index_manager.py` persists force-full progress in
  `_make_force_full_progress_callback(...)` and only writes terminal trace
  states such as `force_full_failed` or `force_full_completed` on normal
  return paths inside `sync_repository_index(...)`. That makes it the
  authoritative seam for repairing a durable `status=running` snapshot that
  survives after the process has already exited.
- `mcp_server/cli/repository_commands.py` renders `Trace freshness:
  stale-running snapshot` purely from the durable trace age when the trace
  still says `status=running`. This phase must keep that operator wording
  truthful for genuinely live stale runs while preventing an already-exited
  force-full command from being reported as still running on the later test
  pair.
- Existing regression coverage already freezes older exact lexical boundaries
  for `.devcontainer/devcontainer.json`,
  `scripts/quick_mcp_vs_native_validation.py`, and
  `tests/test_artifact_publish_race.py`. This phase must not reopen those
  exact seams unless a refreshed live rerun directly re-anchors there again.

Practical planning boundary:

- SEMTESTSTALE may tighten durable force-full progress/terminalization,
  dispatcher-to-manager handoff semantics, repository-status rendering, and
  the dogfood evidence artifact needed to prove the later test-path rebound is
  cleared or replaced by a new exact blocker.
- SEMTESTSTALE must stay narrow and evidence-driven. It must not broaden into
  repo-wide timeout retuning, generic special-casing of all `tests/test_*.py`
  files, or a reopening of the earlier `.devcontainer`, script, or
  storage-closeout contracts unless the refreshed rerun directly points there
  again.

## Interface Freeze Gates

- [ ] IF-0-SEMTESTSTALE-1 - Later stale-trace recovery contract:
      a refreshed repo-local `repository sync --force-full` no longer remains
      beyond the lexical-timeout freshness window with
      `Trace stage: lexical_walking`,
      `Trace freshness: stale-running snapshot`, and
      `In-flight path: /home/viperjuice/code/Code-Index-MCP/tests/test_reindex_resume.py`
      after the process has already exited.
- [ ] IF-0-SEMTESTSTALE-2 - Exact later-boundary contract:
      if this phase keeps or adds a bounded lexical repair, it stays limited
      to `tests/test_reindex_resume.py` or the immediate handoff after
      `tests/test_deployment_runbook_shape.py`; it does not broaden into
      arbitrary test files, the whole `tests/` tree, or global timeout tuning.
- [ ] IF-0-SEMTESTSTALE-3 - Force-full terminal truthfulness contract:
      once the live rerun reaches
      `tests/test_deployment_runbook_shape.py ->
      tests/test_reindex_resume.py`, the dispatcher and git-aware trace either
      advance durably into the next stage or write a terminal failed/interrupted
      trace that reflects the real blocker; they must not leave a durable
      `status=running` lexical snapshot behind after process exit.
- [ ] IF-0-SEMTESTSTALE-4 - Operator and evidence contract:
      `force_full_exit_trace.json`, `uv run mcp-index repository status`, and
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` stay aligned on the rerun
      command, exit code or termination mode, timestamps, progress paths,
      current-versus-indexed commit evidence, summary/vector counts, and the
      final repaired verdict.

## Lane Index & Dependencies

- SL-0 - Later test-path stale-trace fixture freeze; Depends on: SEMDEVSTALE; Blocks: SL-1, SL-2, SL-3; Parallel-safe: no
- SL-1 - Force-full abnormal-exit terminalization repair; Depends on: SL-0; Blocks: SL-2, SL-3; Parallel-safe: no
- SL-2 - Repository-status and durable trace alignment; Depends on: SL-0, SL-1; Blocks: SL-3; Parallel-safe: no
- SL-3 - Live rerun evidence reducer and closeout refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SEMTESTSTALE acceptance; Parallel-safe: no

Lane DAG:

```text
SEMDEVSTALE
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SEMTESTSTALE acceptance
```

## Lanes

### SL-0 - Later Test-Path Stale-Trace Fixture Freeze

- **Scope**: Freeze the current later lexical/crash rebound in unit coverage so
  this phase proves the exact
  `tests/test_deployment_runbook_shape.py ->
  tests/test_reindex_resume.py` stale-running shape instead of relying on the
  earlier `.devcontainer` seam.
- **Owned files**: `tests/test_dispatcher.py`, `tests/test_git_index_manager.py`
- **Interfaces provided**: executable assertions for IF-0-SEMTESTSTALE-1 and IF-0-SEMTESTSTALE-3
- **Interfaces consumed**: existing
  `EnhancedDispatcher.index_directory(...)`,
  `EnhancedDispatcher._index_file_with_lexical_timeout(...)`,
  `GitAwareIndexManager._make_force_full_progress_callback(...)`,
  `GitAwareIndexManager._write_force_full_exit_trace(...)`, and the current
  SEMDEVSTALE evidence wording for the later test-file pair and exit code
  `135`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` with a repo-shaped fixture that
    freezes the later progress pair
    `tests/test_deployment_runbook_shape.py ->
    tests/test_reindex_resume.py` and proves the dispatcher-side repair does
    not regress the earlier `.devcontainer` handoff contract.
  - test: Extend `tests/test_git_index_manager.py` so durable force-full
    progress persistence freezes the bad shape where the trace still says
    `status=running`, `stage=lexical_walking`, and
    `in_flight_path=tests/test_reindex_resume.py` after the run has already
    stopped without a terminal update.
  - test: Require negative assertions that the older exact seams for
    `.devcontainer/devcontainer.json`,
    `scripts/quick_mcp_vs_native_validation.py`, and
    `tests/test_artifact_publish_race.py` do not silently become the active
    blocker again under this later-path fixture.
  - impl: Use synthetic dispatcher snapshots and durable-trace payloads rather
    than a live multi-minute rerun in unit coverage.
  - impl: Keep this lane focused on contract freeze only. Do not update the
    repository-status text surface or the dogfood evidence artifact here.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov -k "reindex_resume or deployment_runbook_shape or stale or lexical or force_full or trace"`

### SL-1 - Force-Full Abnormal-Exit Terminalization Repair

- **Scope**: Implement the smallest code repair needed so a later force-full
  crash or abnormal exit no longer leaves the durable trace parked in
  `status=running` on the test-file pair after the process has already exited.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `mcp_server/storage/git_index_manager.py`
- **Interfaces provided**: IF-0-SEMTESTSTALE-1 later stale-trace recovery contract;
  IF-0-SEMTESTSTALE-2 exact later-boundary contract;
  IF-0-SEMTESTSTALE-3 force-full terminal truthfulness contract
- **Interfaces consumed**: SL-0 later stale-trace fixtures; existing lexical
  progress emission and `force_full_closeout_handoff` behavior; durable
  `last_progress_path` preservation in `_make_force_full_progress_callback(...)`;
  and the SEMDEVSTALE live evidence showing exit code `135` with no later
  terminal trace write
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 dispatcher and git-manager slices first and confirm the
    current checkout still allows the later test-file pair to survive as a
    durable `running` trace after abnormal exit.
  - impl: Determine whether the missing terminalization seam belongs in the
    dispatcher handoff, the git-aware sync/trace lifecycle, or the exact
    boundary around `tests/test_reindex_resume.py`, and repair only that
    nearest seam.
  - impl: If the root cause is the later exact file boundary, keep the fix
    limited to `tests/test_reindex_resume.py` or the immediate handoff after
    `tests/test_deployment_runbook_shape.py` instead of broadening to all test
    files or generic Python path exemptions.
  - impl: If the root cause is abnormal termination after progress already
    advanced, prefer durable failed/interrupted terminalization over another
    path-specific exemption.
  - impl: Preserve the already-closed exact boundaries for
    `.devcontainer/devcontainer.json`,
    `scripts/quick_mcp_vs_native_validation.py`, and
    `tests/test_artifact_publish_race.py`. Do not reopen those earlier phases
    unless the refreshed rerun directly re-anchors there again.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov -k "reindex_resume or deployment_runbook_shape or stale or lexical or force_full or trace"`
  - verify: `rg -n "force_full_closeout_handoff|last_progress_path|in_flight_path|force_full_failed|force_full_completed|trace_timestamp|lexical_walking" mcp_server/dispatcher/dispatcher_enhanced.py mcp_server/storage/git_index_manager.py tests/test_dispatcher.py tests/test_git_index_manager.py`

### SL-2 - Repository-Status And Durable Trace Alignment

- **Scope**: Keep the persisted force-full trace and operator-facing status
  surface aligned with the repaired later test-path seam so stale-running is
  reported only for truly live stale runs and not for an already-exited
  force-full process.
- **Owned files**: `mcp_server/cli/repository_commands.py`, `tests/test_repository_commands.py`
- **Interfaces provided**: IF-0-SEMTESTSTALE-3 force-full terminal truthfulness contract;
  IF-0-SEMTESTSTALE-4 operator and evidence contract
- **Interfaces consumed**: SL-0 later stale-trace fixture vocabulary; SL-1
  abnormal-exit repair choice; existing repository-status boundary helpers for
  `.devcontainer/devcontainer.json`,
  `scripts/quick_mcp_vs_native_validation.py`, and
  `tests/test_artifact_publish_race.py`; and the current stale-running wording
  in `_print_force_full_exit_trace(...)`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_repository_commands.py` so `repository status`
    freezes the later test-file pair and proves the repaired path either
    advances beyond it or reports a truthful terminal failure/interruption
    instead of continuing to render a stale-running lexical snapshot after
    exit.
  - impl: Tighten `mcp_server/cli/repository_commands.py` only as needed so the
    operator surface stays aligned with the repaired terminalization contract
    while preserving the existing lexical boundary lines from earlier phases.
  - impl: Keep fail-closed semantics intact. If the live rerun still blocks,
    surface the real later blocker rather than claiming lexical success,
    semantic readiness, or storage-closeout recovery early.
  - impl: Do not weaken genuinely live stale-running detection for future
    active force-full runs that are still in progress.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_repository_commands.py -q --no-cov -k "reindex_resume or deployment_runbook_shape or stale-running or force_full or boundary"`
  - verify: `rg -n "Trace freshness|Last progress path|In-flight path|force_full_exit_trace|stale-running|lexical_walking" mcp_server/cli/repository_commands.py tests/test_repository_commands.py`

### SL-3 - Live Rerun Evidence Reducer And Closeout Refresh

- **Scope**: Re-run the repaired repo-local force-full path, reduce the real
  outcome into the dogfood evidence artifact, and keep the closeout narrative
  aligned with the actual post-repair later-path rerun.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: IF-0-SEMTESTSTALE-4 operator and evidence contract
- **Interfaces consumed**: SL-0 fixture vocabulary; SL-1 repaired
  terminalization outcome; SL-2 repository-status and durable trace fields;
  current-versus-indexed commit evidence; SQLite summary/vector counts; and
  the current roadmap steering from `SEMDEVSTALE` to `SEMTESTSTALE`
- **Parallel-safe**: no
- **Tasks**:
  - test: Update `tests/docs/test_semdogfood_evidence_contract.py` so the
    report cites `plans/phase-plan-v7-SEMTESTSTALE.md`, preserves the earlier
    lexical-boundary lineage, and records the later
    `tests/test_deployment_runbook_shape.py ->
    tests/test_reindex_resume.py` evidence plus the repaired rerun outcome.
  - impl: Re-run the repo-local force-full command with the same strict
    watchdog posture used by the recent semantic dogfood phases and capture the
    resulting trace, status output, exit code or interruption mode, commit
    evidence, and runtime counts.
  - impl: Refresh `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` with the rerun
    command, timestamps, durable trace fields, repository-status lines,
    current-versus-indexed commit evidence, and the final verdict: either the
    later test-path stale/crash seam is cleared and a new exact blocker is
    named, or the same later seam still fails closed with truthful repaired
    reporting.
  - impl: If no broader docs are needed, record that decision in the status
    artifact rather than widening this phase into general documentation
    cleanup.
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
  - verify: `env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - verify: `python - <<'PY'
from pathlib import Path
trace = Path('.mcp-index') / 'force_full_exit_trace.json'
print(trace.read_text() if trace.exists() else 'missing')
PY`
  - verify: `sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'`

## Verification

Planning-only run: do not execute these during plan creation. Run them during
`codex-execute-phase` or manual SEMTESTSTALE execution.

Lane-specific checks:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov -k "reindex_resume or deployment_runbook_shape or stale or lexical or force_full or trace"
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_repository_commands.py -q --no-cov -k "reindex_resume or deployment_runbook_shape or stale-running or force_full or boundary"
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
rg -n "force_full_closeout_handoff|last_progress_path|in_flight_path|force_full_failed|force_full_completed|trace_timestamp|lexical_walking" \
  mcp_server/dispatcher/dispatcher_enhanced.py \
  mcp_server/storage/git_index_manager.py \
  tests/test_dispatcher.py \
  tests/test_git_index_manager.py
rg -n "Trace freshness|Last progress path|In-flight path|force_full_exit_trace|stale-running|lexical_walking" \
  mcp_server/cli/repository_commands.py \
  tests/test_repository_commands.py
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
git status --short -- specs/phase-plans-v7.md plans/phase-plan-v7-SEMTESTSTALE.md
```

## Acceptance Criteria

- [ ] A live repo-local force-full rerun no longer remains beyond the
      lexical-timeout freshness window with a stale-running
      `tests/test_reindex_resume.py` marker after the process has already
      exited.
- [ ] The repaired code path stays exact: it remains limited to the
      `tests/test_deployment_runbook_shape.py ->
      tests/test_reindex_resume.py` seam or the immediate terminalization after
      it, without broadening into arbitrary test files, the whole `tests/`
      tree, or repo-wide timeout retuning.
- [ ] `force_full_exit_trace.json` and `uv run mcp-index repository status`
      either advance durably beyond `tests/test_reindex_resume.py` or fail
      closed with a truthful terminal trace, while preserving the earlier
      lexical boundary lines from the prior semantic dogfood phases.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` cites
      `plans/phase-plan-v7-SEMTESTSTALE.md` and records the later stale trace,
      the repaired rerun outcome, and the next exact blocker if semantic
      closeout still is not reached on the active head.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v7-SEMTESTSTALE.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMTESTSTALE.md
  artifact_state: staged
```
