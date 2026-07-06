---
phase_loop_plan_version: 1
phase: SEMDEVRELAPSE
roadmap: specs/phase-plans-v7.md
roadmap_sha256: 47d8fb2904ffd11b1ae9ce35f9093da9d33107f34d1f0b51527867d880db3605
---
# SEMDEVRELAPSE: Renewed Devcontainer Lexical Relapse Recovery

## Context

SEMDEVRELAPSE is the phase-40 follow-up for the v7 semantic hardening
roadmap. SEMROOTTESTABORT froze the later
`tests/root_tests/test_voyage_api.py ->
tests/root_tests/run_reranking_tests.py` seam, but its refreshed live rerun on
the new head never reached that pair and instead re-anchored earlier on
`.devcontainer/devcontainer.json` while still in lexical walking.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is the active roadmap, it is tracked and clean in
  this worktree, and `sha256sum specs/phase-plans-v7.md` matches the required
  `47d8fb2904ffd11b1ae9ce35f9093da9d33107f34d1f0b51527867d880db3605`.
- Canonical phase-loop state exists under `.phase-loop/`; `.phase-loop/state.json`
  and `.phase-loop/tui-handoff.md` both mark `SEMDEVRELAPSE` as the current
  `unplanned` phase after `SEMROOTTESTABORT` closed out with commit
  `71a5a0f9f62892bf5d4299b7f15bf1c643bbf5e6`, verification `passed`, a clean
  worktree, and `HEAD 71a5a0f9f62892bf5d4299b7f15bf1c643bbf5e6` on
  `main...origin/main [ahead 75]`. Legacy `.codex/phase-loop/` artifacts are
  compatibility-only and are not authoritative for this run.
- The target artifact `plans/phase-plan-v7-SEMDEVRELAPSE.md` did not exist
  before this planning run.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is the active evidence anchor. It
  already records the SEMROOTTESTABORT code/test repair, the refreshed live
  rerun on observed commit `a4120401381a0e179d0ee0e9355742817e8285d1`, the
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  command, the `2026-04-29T12:04:35Z` lexical snapshot on
  `Last progress path: /home/viperjuice/code/Code-Index-MCP/.devcontainer/devcontainer.json`,
  and the `2026-04-29T12:04:52Z` `repository status` terminalization to
  `Trace status: interrupted` on the same marker.
- The renewed blocker is real, not a stale reading of the later root-test
  pair. The current evidence explicitly says the rerun never advanced to
  `tests/root_tests/test_voyage_api.py ->
  tests/root_tests/run_reranking_tests.py` on the new head.
- The codebase already carries exact bounded coverage for the older
  `.devcontainer/post_create.sh -> .devcontainer/devcontainer.json` rebound,
  the later `tests/test_deployment_runbook_shape.py ->
  tests/test_reindex_resume.py` pair, the later
  `scripts/run_test_batch.py -> scripts/validate_mcp_comprehensive.py` pair,
  and the later root-test pair. `mcp_server/dispatcher/dispatcher_enhanced.py`
  already emits `force_full_closeout_handoff`; `mcp_server/storage/git_index_manager.py`
  already persists `process_id`, rewrites dead-process running traces to
  `interrupted`, and preserves the latest lexical marker across later-stage
  snapshots; `mcp_server/cli/repository_commands.py` already prints exact
  boundary lines for `.devcontainer/devcontainer.json`,
  `tests/root_tests/run_reranking_tests.py`,
  `scripts/validate_mcp_comprehensive.py`,
  `scripts/quick_mcp_vs_native_validation.py`, and
  `tests/test_artifact_publish_race.py`.
- `tests/test_dispatcher.py`, `tests/test_git_index_manager.py`,
  `tests/test_repository_commands.py`, and
  `tests/docs/test_semdogfood_evidence_contract.py` already freeze the older
  seam lineage. This phase must add the renewed same-file
  `.devcontainer/devcontainer.json` relapse shape without reopening the later
  root-test, script, or test-pair contracts unless the refreshed rerun reaches
  them again.

Practical planning boundary:

- SEMDEVRELAPSE may tighten the exact `.devcontainer/devcontainer.json`
  lexical mutation path, the immediate handoff after that file, durable
  force-full trace persistence and terminalization, operator status wording,
  and the dogfood evidence artifact needed to prove the refreshed rerun either
  clears this renewed earlier relapse or names the next exact blocker
  truthfully.
- SEMDEVRELAPSE must stay narrow and evidence-driven. It must not reopen the
  later root-test pair, the later script pair, the later
  `tests/test_deployment_runbook_shape.py -> tests/test_reindex_resume.py`
  pair, or the older publish-race / quick-validation seams unless the
  refreshed rerun directly re-anchors there again.

## Interface Freeze Gates

- [ ] IF-0-SEMDEVRELAPSE-1 - Renewed same-file devcontainer relapse contract:
      a refreshed repo-local `repository sync --force-full` on the
      post-SEMROOTTESTABORT head no longer stalls or exits with the durable
      trace re-anchored on
      `Last progress path: /home/viperjuice/code/Code-Index-MCP/.devcontainer/devcontainer.json`
      while the trace is still in `Trace stage: lexical_walking`.
- [ ] IF-0-SEMDEVRELAPSE-2 - Exact bounded repair contract:
      any new recovery remains limited to `.devcontainer/devcontainer.json`,
      the immediate predecessor `.devcontainer/post_create.sh`, or the
      immediate handoff after the config file finishes; it does not broaden to
      arbitrary `.json` files, the whole `.devcontainer/` tree, or repo-wide
      lexical-timeout retuning.
- [ ] IF-0-SEMDEVRELAPSE-3 - Durable trace truthfulness contract:
      `force_full_exit_trace.json` and `GitAwareIndexManager` either advance
      durably beyond `.devcontainer/devcontainer.json` on the new head or fail
      closed with a newer exact blocker; they must not regress to a misleading
      stale-running or interrupted snapshot that hides the real next seam.
- [ ] IF-0-SEMDEVRELAPSE-4 - Operator boundary contract:
      `uv run mcp-index repository status` remains aligned with the repaired
      devcontainer seam, preserves the existing exact boundary lines for
      `.devcontainer/devcontainer.json`,
      `tests/root_tests/run_reranking_tests.py`,
      `scripts/validate_mcp_comprehensive.py`,
      `scripts/quick_mcp_vs_native_validation.py`, and
      `tests/test_artifact_publish_race.py`, and adds no misleading new
      boundary copy.
- [ ] IF-0-SEMDEVRELAPSE-5 - Dogfood evidence contract:
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is refreshed with the
      SEMROOTTESTABORT landing, the renewed `.devcontainer/devcontainer.json`
      relapse evidence on observed commit `a4120401`, and the final live
      verdict for the repaired rerun.

## Lane Index & Dependencies

- SL-0 - Renewed devcontainer relapse fixture freeze; Depends on: SEMROOTTESTABORT; Blocks: SL-1, SL-2, SL-3; Parallel-safe: no
- SL-1 - Exact devcontainer relapse repair or blocker capture; Depends on: SL-0; Blocks: SL-2, SL-3; Parallel-safe: no
- SL-2 - Repository-status and durable-trace boundary alignment; Depends on: SL-0, SL-1; Blocks: SL-3; Parallel-safe: no
- SL-3 - Live rerun evidence reducer and closeout refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SEMDEVRELAPSE acceptance; Parallel-safe: no

Lane DAG:

```text
SEMROOTTESTABORT
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SEMDEVRELAPSE acceptance
```

## Lanes

### SL-0 - Renewed Devcontainer Relapse Fixture Freeze

- **Scope**: Freeze the renewed same-file `.devcontainer/devcontainer.json`
  relapse shape in dispatcher and git-manager coverage so this phase proves the
  post-SEMROOTTESTABORT regression exactly instead of relying on the older
  `.devcontainer/post_create.sh -> .devcontainer/devcontainer.json` rebound or
  the already-cleared later test/script/root-test pairs.
- **Owned files**: `tests/test_dispatcher.py`, `tests/test_git_index_manager.py`
- **Interfaces provided**: executable assertions for IF-0-SEMDEVRELAPSE-1,
  IF-0-SEMDEVRELAPSE-2, and IF-0-SEMDEVRELAPSE-3
- **Interfaces consumed**: existing
  `EnhancedDispatcher.index_directory(...)`,
  `EnhancedDispatcher._index_file_with_lexical_timeout(...)`,
  `GitAwareIndexManager._make_force_full_progress_callback(...)`,
  `GitAwareIndexManager._write_force_full_exit_trace(...)`,
  `GitAwareIndexManager._finalize_running_force_full_trace_as_interrupted(...)`,
  the exact bounded `.devcontainer/devcontainer.json` helper path, and the
  current SEMROOTTESTABORT evidence wording for observed commit `a4120401`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` with a repo-shaped fixture that
    freezes the renewed regression where `.devcontainer/devcontainer.json`
    becomes the latest durable lexical marker on the refreshed head and the
    rerun never advances to the later root-test, later script, or later
    test-pair seams.
  - test: Extend `tests/test_git_index_manager.py` so durable force-full trace
    persistence freezes the renewed same-file `.devcontainer/devcontainer.json`
    relapse, including preserved `last_progress_path`, truthful
    `blocker_source=lexical_mutation`, dead-process or bounded-timeout rewrite
    to `status=interrupted`, and negative assertions that older seam markers do
    not silently become active again.
  - test: Require explicit negative assertions that
    `.devcontainer/post_create.sh`,
    `tests/test_reindex_resume.py`,
    `scripts/validate_mcp_comprehensive.py`, and
    `tests/root_tests/run_reranking_tests.py` do not appear as the active
    blocker under this renewed fixture.
  - impl: Use synthetic dispatcher progress and synthetic durable-trace
    payloads rather than a live multi-minute rerun in unit coverage.
  - impl: Keep this lane focused on contract freeze only. Do not update
    operator status text or the dogfood evidence artifact here.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov -k "devcontainer or lexical or force_full or interrupted or stale or trace"`

### SL-1 - Exact Devcontainer Relapse Repair Or Blocker Capture

- **Scope**: Implement the smallest exact repair needed so the refreshed
  repo-local force-full rerun no longer re-anchors early on
  `.devcontainer/devcontainer.json` before it can reach the later
  test/script/root-test families, or otherwise records the real next blocker
  truthfully.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `mcp_server/storage/git_index_manager.py`
- **Interfaces provided**: IF-0-SEMDEVRELAPSE-1 renewed same-file devcontainer relapse contract;
  IF-0-SEMDEVRELAPSE-2 exact bounded repair contract;
  IF-0-SEMDEVRELAPSE-3 durable trace truthfulness contract
- **Interfaces consumed**: SL-0 renewed devcontainer relapse fixtures; current
  exact bounded `.devcontainer/devcontainer.json` handling; current
  lexical-progress emission; `force_full_closeout_handoff`; durable
  `process_id`, `last_progress_path`, and `in_flight_path` persistence; dead
  process rewrite logic; and the live SEMROOTTESTABORT evidence showing the
  rerun timing out on `.devcontainer/devcontainer.json`
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 dispatcher and git-manager slices first and confirm the
    current checkout still lacks a truthful durable advance beyond the renewed
    `.devcontainer/devcontainer.json` marker on the new head.
  - impl: Determine whether the regression is reintroduced by the exact bounded
    JSON path itself, by lexical progress or terminalization immediately after
    `.devcontainer/devcontainer.json` completes, or by durable trace rewrite on
    dead-process or timeout observation. Repair only that nearest seam.
  - impl: If the root cause is still file-local, keep the repair limited to
    `.devcontainer/devcontainer.json`, `.devcontainer/post_create.sh`, or the
    immediate handoff after the config file. Do not broaden to arbitrary JSON,
    all `.devcontainer/*`, or repo-wide timeout tuning.
  - impl: If the rerun still cannot progress past the renewed earlier seam,
    prefer a durable exact blocker classification with truthful stage and
    source fields over another misleading same-file stale-running snapshot.
  - impl: Preserve the already-closed exact boundaries for
    `tests/root_tests/run_reranking_tests.py`,
    `scripts/validate_mcp_comprehensive.py`,
    `scripts/quick_mcp_vs_native_validation.py`,
    `tests/test_artifact_publish_race.py`, and
    `tests/test_reindex_resume.py`. Do not reopen those later phases unless
    the refreshed rerun directly re-anchors there again.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov -k "devcontainer or lexical or force_full or interrupted or trace"`
  - verify: `rg -n "devcontainer|force_full_closeout_handoff|last_progress_path|in_flight_path|process_id|interrupted|lexical_mutation|run_reranking_tests|validate_mcp_comprehensive|artifact_publish_race|test_reindex_resume" mcp_server/dispatcher/dispatcher_enhanced.py mcp_server/storage/git_index_manager.py tests/test_dispatcher.py tests/test_git_index_manager.py`

### SL-2 - Repository-Status And Durable-Trace Boundary Alignment

- **Scope**: Keep the operator-facing status surface aligned with the renewed
  devcontainer repair so `repository status` and the persisted force-full trace
  report either the cleared earlier seam or the real next blocker without
  regressing boundary copy from prior phases.
- **Owned files**: `mcp_server/cli/repository_commands.py`, `tests/test_repository_commands.py`
- **Interfaces provided**: IF-0-SEMDEVRELAPSE-3 durable trace truthfulness contract;
  IF-0-SEMDEVRELAPSE-4 operator boundary contract
- **Interfaces consumed**: SL-0 renewed devcontainer relapse fixture
  vocabulary; SL-1 repair choice and blocker classification; existing exact
  boundary helpers for `.devcontainer/devcontainer.json`,
  `tests/root_tests/run_reranking_tests.py`,
  `scripts/validate_mcp_comprehensive.py`,
  `scripts/quick_mcp_vs_native_validation.py`, and
  `tests/test_artifact_publish_race.py`; plus the current
  `_print_force_full_exit_trace(...)` rendering path
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_repository_commands.py` so `repository status`
    freezes the renewed same-file `.devcontainer/devcontainer.json` relapse and
    proves the repaired path either advances beyond that marker or reports the
    real next blocker without falling back to stale-running wording or boundary
    copy from the older rebound and later root-test phases.
  - impl: Tighten `mcp_server/cli/repository_commands.py` only as needed so
    the operator surface stays aligned with the exact repaired seam. If SL-1
    solves the issue through trace truthfulness alone, keep this lane limited
    to rendering and do not add misleading new exact-boundary copy.
  - impl: Preserve the existing boundary lines for
    `.devcontainer/devcontainer.json`,
    `tests/root_tests/run_reranking_tests.py`,
    `scripts/validate_mcp_comprehensive.py`,
    `scripts/quick_mcp_vs_native_validation.py`, and
    `tests/test_artifact_publish_race.py`.
  - impl: Keep fail-closed semantics intact. If the live rerun still blocks,
    surface the real next blocker rather than claiming lexical, storage, or
    semantic readiness early.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_repository_commands.py -q --no-cov -k "devcontainer or force_full or interrupted or stale-running or boundary"`
  - verify: `rg -n "devcontainer|Trace freshness|Trace status|Trace stage|Trace blocker source|Last progress path|In-flight path|run_reranking_tests|validate_mcp_comprehensive|quick_mcp_vs_native_validation|artifact_publish_race" mcp_server/cli/repository_commands.py tests/test_repository_commands.py`

### SL-3 - Live Rerun Evidence Reducer And Closeout Refresh

- **Scope**: Re-run the repaired repo-local force-full path, reduce the real
  outcome into the dogfood evidence artifact, and keep the final closeout
  narrative aligned with the actual post-repair SEMDEVRELAPSE rerun.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: IF-0-SEMDEVRELAPSE-5 dogfood evidence contract
- **Interfaces consumed**: SL-0 renewed devcontainer relapse fixture
  vocabulary; SL-1 repaired blocker or recovery outcome; SL-2 repository-status
  and durable trace fields; observed commit `a4120401`; current-versus-indexed
  commit evidence; SQLite summary/vector counts; and the current roadmap
  steering from `SEMROOTTESTABORT` to `SEMDEVRELAPSE`
- **Parallel-safe**: no
- **Tasks**:
  - test: Update `tests/docs/test_semdogfood_evidence_contract.py` so the
    report cites `plans/phase-plan-v7-SEMDEVRELAPSE.md`, preserves the earlier
    lexical-boundary lineage, and records the renewed
    `.devcontainer/devcontainer.json` relapse evidence plus the repaired rerun
    outcome.
  - impl: Re-run the repo-local force-full command with the same strict
    watchdog posture used by the recent semantic dogfood phases and capture the
    resulting trace, status output, exit code or next-blocker classification,
    commit evidence, and runtime counts.
  - impl: Refresh `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` with the rerun
    command, timestamps, `force_full_exit_trace.json` fields, repository-status
    lines, current-versus-indexed commit evidence, and the final verdict:
    either the renewed `.devcontainer/devcontainer.json` relapse is cleared and
    a later exact blocker is named, or the same earlier seam still fails
    closed with truthful repaired reporting.
  - impl: If no broader docs are needed, record that decision in the status
    artifact rather than widening this phase into general documentation
    cleanup.
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
  - verify: `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - verify: `python - <<'PY'
from pathlib import Path
trace = Path(".mcp-index") / "force_full_exit_trace.json"
print(trace.read_text() if trace.exists() else "missing")
PY`
  - verify: `sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'`

## Verification

Planning-only work is complete once this artifact is written and staged. Do
not execute the commands below during plan creation; run them during
`codex-execute-phase` or manual SEMDEVRELAPSE execution.

Lane-specific checks:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov -k "devcontainer or lexical or force_full or interrupted or stale or trace"
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_repository_commands.py -q --no-cov -k "devcontainer or force_full or interrupted or stale-running or boundary"
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
rg -n "devcontainer|force_full_closeout_handoff|last_progress_path|in_flight_path|process_id|Trace freshness|Trace blocker source|run_reranking_tests|validate_mcp_comprehensive|quick_mcp_vs_native_validation|artifact_publish_race|test_reindex_resume" \
  mcp_server/dispatcher/dispatcher_enhanced.py \
  mcp_server/storage/git_index_manager.py \
  mcp_server/cli/repository_commands.py \
  docs/status/SEMANTIC_DOGFOOD_REBUILD.md \
  tests/test_dispatcher.py \
  tests/test_git_index_manager.py \
  tests/test_repository_commands.py \
  tests/docs/test_semdogfood_evidence_contract.py
```

Whole-phase live verification after code changes:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest \
  tests/test_dispatcher.py \
  tests/test_git_index_manager.py \
  tests/test_repository_commands.py \
  tests/docs/test_semdogfood_evidence_contract.py \
  -q --no-cov
timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
python - <<'PY'
from pathlib import Path
trace = Path(".mcp-index") / "force_full_exit_trace.json"
print(trace.read_text() if trace.exists() else "missing")
PY
sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'
git status --short -- specs/phase-plans-v7.md plans/phase-plan-v7-SEMDEVRELAPSE.md
```

## Acceptance Criteria

- [ ] A refreshed repo-local force-full rerun on the post-SEMROOTTESTABORT
      head no longer stalls or exits re-anchored on
      `.devcontainer/devcontainer.json` while the durable trace is still in
      `lexical_walking`.
- [ ] The repaired code path stays exact: it remains limited to
      `.devcontainer/devcontainer.json`, the immediate predecessor
      `.devcontainer/post_create.sh`, or the immediate handoff after the config
      file, without broadening into arbitrary `.json` files, the whole
      `.devcontainer/` tree, or repo-wide timeout retuning.
- [ ] `force_full_exit_trace.json` and
      `uv run mcp-index repository status` either advance durably beyond
      `.devcontainer/devcontainer.json` or fail closed with the real next
      exact blocker, while preserving the existing exact boundary lines for the
      later root-test, script, publish-race, and reindex-resume seams.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` cites
      `plans/phase-plan-v7-SEMDEVRELAPSE.md` and records the renewed
      `.devcontainer/devcontainer.json` relapse on observed commit `a4120401`
      plus the final repaired rerun verdict.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v7-SEMDEVRELAPSE.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMDEVRELAPSE.md
  artifact_state: staged
```
