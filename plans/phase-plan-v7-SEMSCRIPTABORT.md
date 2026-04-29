---
phase_loop_plan_version: 1
phase: SEMSCRIPTABORT
roadmap: specs/phase-plans-v7.md
roadmap_sha256: 607c00adc8e4652bf775ca927257ceeed9dc5d398be7af1e26233cbc8c618951
---
# SEMSCRIPTABORT: Post-Test Script Abort Trace Recovery

## Context

SEMSCRIPTABORT is the phase-38 follow-up for the v7 semantic hardening
roadmap. SEMTESTSTALE proved the later
`tests/test_deployment_runbook_shape.py -> tests/test_reindex_resume.py`
stale-running seam is cleared on the current head, but the refreshed live
repo-local force-full rerun on observed commit `a186b352` still exited with
code `135` after advancing into the next exact script-family pair:
`scripts/run_test_batch.py -> scripts/validate_mcp_comprehensive.py`.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is the active roadmap, it is tracked and clean in
  this worktree, and `sha256sum specs/phase-plans-v7.md` matches the required
  `607c00adc8e4652bf775ca927257ceeed9dc5d398be7af1e26233cbc8c618951`.
- Canonical phase-loop state exists under `.phase-loop/`; `.phase-loop/state.json`
  and `.phase-loop/tui-handoff.md` both mark `SEMSCRIPTABORT` as the current
  `unplanned` phase after `SEMTESTSTALE` completed, with a clean worktree at
  `HEAD d0b83401544af6732e4ff43e3f727a06b8970f9e` on
  `main...origin/main [ahead 71]`. Legacy `.codex/phase-loop/` artifacts are
  present only for compatibility and are not authoritative for this run.
- The target artifact `plans/phase-plan-v7-SEMSCRIPTABORT.md` did not exist
  before this planning run.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is the active evidence anchor. It
  already records the SEMTESTSTALE liveness repair, the later script-pair
  evidence on observed commit `a186b352144a8211552afa432f42d90d2c79546d`, the
  durable trace rewrite to `status=interrupted` at `2026-04-29T11:17:51Z`, and
  the roadmap steering decision that makes `SEMSCRIPTABORT` the next slice.
- The current durable trace now preserves the exact later blocker shape
  truthfully:
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/scripts/run_test_batch.py`
  and
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/scripts/validate_mcp_comprehensive.py`.
  The remaining gap is no longer stale-running liveness; it is the later abort
  itself and the need to either clear that seam or classify the real later
  blocker exactly.
- `scripts/run_test_batch.py` (`226` lines) and
  `scripts/validate_mcp_comprehensive.py` (`243` lines) are small Python files,
  not large outliers. The next repair should therefore stay focused on the
  exact script pair, the dispatcher/git-manager handoff around it, or the later
  blocker classification after it, not on repo-wide throughput retuning.
- `mcp_server/dispatcher/dispatcher_enhanced.py` still owns the live
  `last_progress_path` / `in_flight_path` mutations and only emits the
  `force_full_closeout_handoff` progress snapshot when no low-level blocker is
  recorded. `mcp_server/storage/git_index_manager.py` persists those snapshots
  into `.mcp-index/force_full_exit_trace.json`, writes `process_id`, and
  rewrites dead-process `status=running` traces to `status=interrupted`.
  Together they remain the authoritative seam for repairing or reclassifying
  the later script-family abort.
- `mcp_server/cli/repository_commands.py` already prints the exact bounded
  lexical-boundary lines accumulated by earlier phases for
  `scripts/create_multi_repo_visual_report.py`,
  `scripts/quick_mcp_vs_native_validation.py`,
  `tests/test_artifact_publish_race.py`, and
  `.devcontainer/devcontainer.json`. It does not yet carry any exact boundary
  line for `scripts/run_test_batch.py` or
  `scripts/validate_mcp_comprehensive.py`, so this phase must add one only if
  the implementation actually introduces an exact script-specific recovery.
- The partial runtime still ends with `chunk_summaries = 0` and
  `semantic_points = 0`, so this phase must keep fail-closed reporting intact:
  if the rerun is still blocked after the script pair, it must report the real
  later blocker rather than claiming lexical, closeout, or semantic readiness
  early.

Practical planning boundary:

- SEMSCRIPTABORT may tighten the exact later script-pair handling, the
  dispatcher-to-git-manager force-full handoff, later blocker classification,
  operator status copy, and the dogfood evidence artifact needed to prove the
  rerun either clears the script seam or names the real next blocker exactly.
- SEMSCRIPTABORT must stay narrow and evidence-driven. It must not reopen the
  cleared later test-pair stale-trace repair, the renewed
  `.devcontainer/devcontainer.json` rebound, the earlier quick-validation /
  visual-report / artifact-publish exact boundaries, or generic repo-wide
  timeout tuning unless the refreshed rerun directly re-anchors there again.

## Interface Freeze Gates

- [ ] IF-0-SEMSCRIPTABORT-1 - Exact later script abort contract:
      after a live repo-local `repository sync --force-full` advances beyond
      the SEMTESTSTALE test pair, it no longer exits with code `135` while the
      durable trace remains stuck on
      `scripts/run_test_batch.py -> scripts/validate_mcp_comprehensive.py`
      without either completing or naming the real later blocker truthfully.
- [ ] IF-0-SEMSCRIPTABORT-2 - Exact bounded recovery contract:
      if this phase introduces any script-specific lexical or bounded recovery,
      it stays limited to `scripts/validate_mcp_comprehensive.py`,
      `scripts/run_test_batch.py`, or the immediate handoff after
      `scripts/run_test_batch.py`; it does not broaden into arbitrary
      `scripts/*.py`, all Python files, or repo-wide timeout retuning.
- [ ] IF-0-SEMSCRIPTABORT-3 - Force-full later-blocker truthfulness contract:
      once the rerun reaches the later script pair, the dispatcher,
      `force_full_exit_trace.json`, and `repository status` either advance
      durably beyond that pair or record the real later blocker family, stage,
      and source exactly; they must not collapse back to a generic abort story
      with no downstream cause.
- [ ] IF-0-SEMSCRIPTABORT-4 - Operator and evidence contract:
      `force_full_exit_trace.json`, `uv run mcp-index repository status`, and
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` stay aligned on the rerun
      command, exit code or blocker classification, timestamps, progress paths,
      current-versus-indexed commit evidence, summary/vector counts, and the
      final live verdict.
- [ ] IF-0-SEMSCRIPTABORT-5 - Upstream-boundary preservation contract:
      SEMSCRIPTREBOUND, SEMDISKIO, SEMDEVSTALE, and SEMTESTSTALE remain closed
      unless the refreshed rerun directly re-anchors on one of those exact
      historical seams again.

## Lane Index & Dependencies

- SL-0 - Later script-family abort fixture freeze; Depends on: SEMTESTSTALE; Blocks: SL-1, SL-2, SL-3; Parallel-safe: no
- SL-1 - Exact later script-family recovery or blocker capture; Depends on: SL-0; Blocks: SL-2, SL-3; Parallel-safe: no
- SL-2 - Repository-status boundary and force-full trace alignment; Depends on: SL-0, SL-1; Blocks: SL-3; Parallel-safe: no
- SL-3 - Live rerun evidence reducer and closeout refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SEMSCRIPTABORT acceptance; Parallel-safe: no

Lane DAG:

```text
SEMTESTSTALE
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SEMSCRIPTABORT acceptance
```

## Lanes

### SL-0 - Later Script-Family Abort Fixture Freeze

- **Scope**: Freeze the current
  `scripts/run_test_batch.py -> scripts/validate_mcp_comprehensive.py`
  rebound shape in dispatcher and git-manager coverage so this phase proves the
  exact later abort after SEMTESTSTALE instead of relying on the already-cleared
  later test-pair seam.
- **Owned files**: `tests/test_dispatcher.py`, `tests/test_git_index_manager.py`
- **Interfaces provided**: executable assertions for IF-0-SEMSCRIPTABORT-1,
  IF-0-SEMSCRIPTABORT-3, and IF-0-SEMSCRIPTABORT-5
- **Interfaces consumed**: existing
  `EnhancedDispatcher.index_directory(...)`,
  `EnhancedDispatcher._index_file_with_lexical_timeout(...)`,
  `GitAwareIndexManager._make_force_full_progress_callback(...)`,
  `GitAwareIndexManager._write_force_full_exit_trace(...)`,
  `GitAwareIndexManager._finalize_running_force_full_trace_as_interrupted(...)`,
  and the current SEMTESTSTALE evidence wording for the later script pair and
  exit code `135`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` with a repo-shaped fixture that
    freezes the later script pair after the SEMTESTSTALE test-pair boundary has
    already been cleared, and proves the dispatcher emits either a durable
    downstream handoff or an exact later blocker instead of leaving the abort
    story implicit.
  - test: Extend `tests/test_git_index_manager.py` so durable force-full trace
    persistence freezes the later script-pair abort shape, including preserved
    `last_progress_path`, preserved `in_flight_path`, dead-process rewrite to
    `status=interrupted`, and the requirement that the exact later blocker
    remains attributable to the script family.
  - test: Require negative assertions that the earlier exact seams for
    `.devcontainer/devcontainer.json`,
    `scripts/quick_mcp_vs_native_validation.py`, and
    `tests/test_artifact_publish_race.py` do not silently become the active
    blocker again under this later script fixture.
  - impl: Use synthetic dispatcher progress, synthetic durable-trace payloads,
    and explicit abnormal-exit fixtures rather than a live multi-minute rerun
    inside unit coverage.
  - impl: Keep this lane focused on contract freeze only. Do not update the
    operator status text surface or the dogfood evidence artifact here.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov -k "run_test_batch or validate_mcp_comprehensive or force_full or lexical or trace or interrupted"`

### SL-1 - Exact Later Script-Family Recovery Or Blocker Capture

- **Scope**: Implement the smallest exact repair needed so the later
  `scripts/run_test_batch.py -> scripts/validate_mcp_comprehensive.py` seam no
  longer ends in an unclassified code-`135` abort after SEMTESTSTALE has
  already restored truthful interrupted traces.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `mcp_server/storage/git_index_manager.py`
- **Interfaces provided**: IF-0-SEMSCRIPTABORT-1 exact later script abort contract;
  IF-0-SEMSCRIPTABORT-2 exact bounded recovery contract;
  IF-0-SEMSCRIPTABORT-3 force-full later-blocker truthfulness contract
- **Interfaces consumed**: SL-0 later script-pair fixtures; existing lexical
  progress emission and `force_full_closeout_handoff` behavior; durable
  `process_id`, `last_progress_path`, and `in_flight_path` persistence;
  dead-process rewrite logic; and the live SEMTESTSTALE evidence showing exit
  code `135` on
  `scripts/run_test_batch.py -> scripts/validate_mcp_comprehensive.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 dispatcher and git-manager slices first and confirm the
    current checkout still reproduces the later script-family abort shape or
    leaves the later blocker under-classified.
  - impl: Determine whether the remaining failure occurs during lexical
    mutation of `scripts/validate_mcp_comprehensive.py`, during the immediate
    handoff after `scripts/run_test_batch.py`, or during later trace
    finalization/classification, and repair only that nearest seam.
  - impl: If the root cause is still script-local lexical handling, keep the
    repair limited to the exact later pair or the immediate handoff after
    `scripts/run_test_batch.py`; do not broaden to arbitrary `scripts/*.py`,
    all Python files, or a repo-wide lexical-timeout retune.
  - impl: If the rerun still cannot progress past the later pair, prefer a
    durable exact blocker classification with truthful stage/source fields over
    another generic `interrupted` outcome that hides the downstream cause.
  - impl: Preserve the already-closed historical seams for
    `.devcontainer/devcontainer.json`,
    `scripts/quick_mcp_vs_native_validation.py`, and
    `tests/test_artifact_publish_race.py`. Do not reopen those earlier phases
    unless the refreshed rerun directly re-anchors there again.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov -k "run_test_batch or validate_mcp_comprehensive or force_full or lexical or trace or interrupted"`
  - verify: `rg -n "force_full_closeout_handoff|last_progress_path|in_flight_path|process_id|interrupted|summary_call_timed_out|blocked_storage_error|lexical_walking" mcp_server/dispatcher/dispatcher_enhanced.py mcp_server/storage/git_index_manager.py tests/test_dispatcher.py tests/test_git_index_manager.py`

### SL-2 - Repository-Status Boundary And Force-Full Trace Alignment

- **Scope**: Keep the operator-facing status surface aligned with the repaired
  later script seam so `repository status` and the durable trace present either
  the cleared path or the real later blocker without regressing earlier exact
  boundary copy.
- **Owned files**: `mcp_server/cli/repository_commands.py`, `tests/test_repository_commands.py`
- **Interfaces provided**: IF-0-SEMSCRIPTABORT-3 force-full later-blocker truthfulness contract;
  IF-0-SEMSCRIPTABORT-4 operator and evidence contract;
  IF-0-SEMSCRIPTABORT-5 upstream-boundary preservation contract
- **Interfaces consumed**: SL-0 later script-pair fixture vocabulary; SL-1
  repair choice and later blocker classification; existing exact boundary
  helpers for `scripts/create_multi_repo_visual_report.py`,
  `scripts/quick_mcp_vs_native_validation.py`,
  `tests/test_artifact_publish_race.py`, and
  `.devcontainer/devcontainer.json`; plus the current force-full trace printer
  in `_print_force_full_exit_trace(...)`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_repository_commands.py` so `repository status`
    freezes the exact later script pair and proves the repaired path either
    advances beyond it or reports the real later blocker without falling back
    to stale-running wording or boundary copy from earlier phases.
  - impl: If SL-1 introduces an exact script-specific recovery for one of the
    two later script files, add only the matching minimal operator boundary
    line. If SL-1 solves the issue through later blocker classification alone,
    keep this lane limited to truthful trace/status rendering and do not add
    misleading exact-boundary copy.
  - impl: Preserve the existing boundary lines for
    `scripts/create_multi_repo_visual_report.py`,
    `scripts/quick_mcp_vs_native_validation.py`,
    `tests/test_artifact_publish_race.py`, and
    `.devcontainer/devcontainer.json`.
  - impl: Keep fail-closed semantics intact. If the live rerun still blocks,
    surface the true later blocker rather than claiming lexical, storage, or
    semantic readiness early.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_repository_commands.py -q --no-cov -k "run_test_batch or validate_mcp_comprehensive or force_full or interrupted or boundary"`
  - verify: `rg -n "run_test_batch|validate_mcp_comprehensive|Trace status|Trace stage|Trace blocker source|Last progress path|In-flight path|quick_mcp_vs_native_validation|artifact_publish_race|devcontainer.json" mcp_server/cli/repository_commands.py tests/test_repository_commands.py`

### SL-3 - Live Rerun Evidence Reducer And Closeout Refresh

- **Scope**: Re-run the repaired repo-local force-full path, reduce the real
  outcome into the dogfood evidence artifact, and keep the final closeout
  narrative aligned with the actual post-repair later-script rerun.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: IF-0-SEMSCRIPTABORT-4 operator and evidence contract;
  IF-0-SEMSCRIPTABORT-5 upstream-boundary preservation contract
- **Interfaces consumed**: SL-0 later script-pair fixture vocabulary; SL-1
  repaired blocker or recovery outcome; SL-2 repository-status and durable
  trace fields; observed commit `a186b352`; current-versus-indexed commit
  evidence; SQLite summary/vector counts; and the current roadmap steering from
  `SEMTESTSTALE` to `SEMSCRIPTABORT`
- **Parallel-safe**: no
- **Tasks**:
  - test: Update `tests/docs/test_semdogfood_evidence_contract.py` so the
    report cites `plans/phase-plan-v7-SEMSCRIPTABORT.md`, preserves the earlier
    lexical-boundary lineage, and records the later
    `scripts/run_test_batch.py -> scripts/validate_mcp_comprehensive.py`
    evidence plus the repaired rerun outcome.
  - impl: Re-run the repo-local force-full command with the same strict
    watchdog posture used by the recent semantic dogfood phases and capture the
    resulting trace, status output, exit code or later blocker classification,
    commit evidence, and runtime counts.
  - impl: Refresh `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` with the rerun
    command, timestamps, `force_full_exit_trace.json` fields, repository-status
    lines, current-versus-indexed commit evidence, and the final verdict:
    either the later script-family abort is cleared and a new exact blocker is
    named, or the same script-family seam still fails closed with truthful
    repaired reporting.
  - impl: If no broader docs are needed, record that decision in the status
    artifact rather than widening this phase into general documentation
    cleanup.
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
  - verify: `env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - verify: `python - <<'PY'
from pathlib import Path
trace = Path(".mcp-index") / "force_full_exit_trace.json"
print(trace.read_text() if trace.exists() else "missing")
PY`
  - verify: `sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'`

## Verification

Planning-only run: do not execute these during plan creation. Run them during
`codex-execute-phase` or manual SEMSCRIPTABORT execution.

Lane-specific checks:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov -k "run_test_batch or validate_mcp_comprehensive or force_full or lexical or trace or interrupted"
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_repository_commands.py -q --no-cov -k "run_test_batch or validate_mcp_comprehensive or force_full or interrupted or boundary"
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
rg -n "run_test_batch|validate_mcp_comprehensive|force_full_closeout_handoff|last_progress_path|in_flight_path|process_id|Trace blocker source|quick_mcp_vs_native_validation|artifact_publish_race|devcontainer.json" \
  mcp_server/dispatcher/dispatcher_enhanced.py \
  mcp_server/storage/git_index_manager.py \
  mcp_server/cli/repository_commands.py \
  tests/test_dispatcher.py \
  tests/test_git_index_manager.py \
  tests/test_repository_commands.py
```

Whole-phase live verification after code changes:

```bash
env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
python - <<'PY'
from pathlib import Path
trace = Path(".mcp-index") / "force_full_exit_trace.json"
print(trace.read_text() if trace.exists() else "missing")
PY
sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'
```

## Acceptance Criteria

- [ ] A refreshed repo-local force-full rerun on the post-SEMTESTSTALE head no
      longer exits with code `135` after advancing into
      `scripts/run_test_batch.py -> scripts/validate_mcp_comprehensive.py`
      without either completing or naming the real later exact blocker
      truthfully.
- [ ] `force_full_exit_trace.json` and
      `uv run mcp-index repository status` either advance durably beyond
      `scripts/run_test_batch.py -> scripts/validate_mcp_comprehensive.py` or
      fail closed with the real later script-family blocker, including truthful
      stage/source fields.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is refreshed with the
      SEMTESTSTALE liveness repair, the later script-pair evidence on commit
      `a186b352`, and the final live verdict for the repaired rerun.
- [ ] Earlier exact boundaries for
      `.devcontainer/devcontainer.json`,
      `scripts/quick_mcp_vs_native_validation.py`,
      `scripts/create_multi_repo_visual_report.py`, and
      `tests/test_artifact_publish_race.py` remain preserved unless the live
      rerun re-anchors on one of them again.
