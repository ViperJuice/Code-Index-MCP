---
phase_loop_plan_version: 1
phase: SEMROOTTESTABORT
roadmap: specs/phase-plans-v7.md
roadmap_sha256: 3aa53d9108558f2412f21d80f462f542238b86a15c8ab82f360c0fd1a0de6702
---
# SEMROOTTESTABORT: Post-Script Root-Test Abort Trace Recovery

## Context

SEMROOTTESTABORT is the phase-39 follow-up for the v7 semantic hardening
roadmap. SEMSCRIPTABORT proved the later
`scripts/run_test_batch.py -> scripts/validate_mcp_comprehensive.py` seam is
cleared on the current head, but the refreshed live repo-local force-full rerun
on observed commit `098c1ad19c3957af05bf1bfaf4ee6ceb07b73cce` still exited with
code `135` after advancing into the next exact root-test pair:
`tests/root_tests/test_voyage_api.py ->
tests/root_tests/run_reranking_tests.py`.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is the active roadmap, it is tracked and clean in
  this worktree, and `sha256sum specs/phase-plans-v7.md` matches the required
  `3aa53d9108558f2412f21d80f462f542238b86a15c8ab82f360c0fd1a0de6702`.
- Canonical phase-loop state exists under `.phase-loop/`; `.phase-loop/state.json`
  and `.phase-loop/tui-handoff.md` both mark `SEMROOTTESTABORT` as the current
  `unplanned` phase after `SEMSCRIPTABORT` completed, with a clean worktree at
  `HEAD a3eb03e9801975a6cb9f2b4e728fa5b20033131a` on
  `main...origin/main [ahead 73]`. Legacy `.codex/phase-loop/` artifacts are
  present only for compatibility and are not authoritative for this run.
- The target artifact `plans/phase-plan-v7-SEMROOTTESTABORT.md` did not exist
  before this planning run.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is the active evidence anchor. It
  already records the SEMSCRIPTABORT repair, the later root-test-pair evidence
  on observed commit `098c1ad19c3957af05bf1bfaf4ee6ceb07b73cce`, and the
  durable trace rewrite to `status=interrupted` at `2026-04-29T11:43:19Z`.
- The current durable trace now preserves the exact later blocker shape
  truthfully:
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/tests/root_tests/test_voyage_api.py`
  and
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/tests/root_tests/run_reranking_tests.py`.
  The remaining gap is no longer stale-running liveness or the script-family
  abort itself; it is the later root-test abort and the need to either clear
  that seam or classify the real downstream blocker exactly.
- `tests/test_dispatcher.py` and `tests/test_git_index_manager.py` already
  freeze the earlier test-pair and script-pair rebound shapes. They do not yet
  freeze the later
  `tests/root_tests/test_voyage_api.py ->
  tests/root_tests/run_reranking_tests.py` pair, so this phase must add the
  next exact fixture rather than reopening older evidence.
- `mcp_server/dispatcher/dispatcher_enhanced.py` still owns the exact bounded
  lexical-shard seam through `_EXACT_BOUNDED_PYTHON_PATHS`,
  `_build_exact_bounded_python_shard(...)`, lexical progress emission, and the
  `force_full_closeout_handoff` snapshot when no lower-level blocker is
  recorded. `mcp_server/storage/git_index_manager.py` persists those snapshots
  into `.mcp-index/force_full_exit_trace.json`, preserves `process_id`,
  `last_progress_path`, and `in_flight_path`, and rewrites dead-process
  `status=running` traces to `status=interrupted`. Together they remain the
  authoritative seam for repairing or reclassifying the later root-test abort.
- `mcp_server/cli/repository_commands.py` already prints exact bounded lexical
  boundary lines for `scripts/create_multi_repo_visual_report.py`,
  `scripts/quick_mcp_vs_native_validation.py`,
  `scripts/validate_mcp_comprehensive.py`,
  `tests/test_artifact_publish_race.py`, and
  `.devcontainer/devcontainer.json`. It does not yet carry any exact boundary
  line for `tests/root_tests/test_voyage_api.py` or
  `tests/root_tests/run_reranking_tests.py`, so this phase must add one only if
  the implementation actually introduces an exact root-test-specific recovery.
- The partial runtime still ends with `chunk_summaries = 0` and
  `semantic_points = 0`, so this phase must keep fail-closed reporting intact:
  if the rerun is still blocked after the root-test pair, it must report the
  real later blocker rather than claiming lexical, closeout, or semantic
  readiness early.

Practical planning boundary:

- SEMROOTTESTABORT may tighten the exact later root-test-pair handling, the
  dispatcher-to-git-manager force-full handoff, later blocker classification,
  operator status copy, and the dogfood evidence artifact needed to prove the
  rerun either clears the root-test seam or names the real later blocker
  exactly.
- SEMROOTTESTABORT must stay narrow and evidence-driven. It must not reopen the
  cleared script-pair repair, the earlier test-pair stale-trace repair, the
  renewed `.devcontainer/devcontainer.json` rebound, or the older quick
  validation / visual report / artifact-publish exact boundaries unless the
  refreshed rerun directly re-anchors there again.

## Interface Freeze Gates

- [ ] IF-0-SEMROOTTESTABORT-1 - Exact later root-test abort contract:
      after a live repo-local `repository sync --force-full` advances beyond
      the SEMSCRIPTABORT script pair, it no longer exits with code `135` while
      the durable trace remains stuck on
      `tests/root_tests/test_voyage_api.py ->
      tests/root_tests/run_reranking_tests.py` without either completing or
      naming the real later blocker truthfully.
- [ ] IF-0-SEMROOTTESTABORT-2 - Exact bounded recovery contract:
      if this phase introduces any root-test-specific lexical or bounded
      recovery, it stays limited to `tests/root_tests/run_reranking_tests.py`,
      `tests/root_tests/test_voyage_api.py`, or the immediate handoff after
      `tests/root_tests/test_voyage_api.py`; it does not broaden into arbitrary
      `tests/root_tests/*.py`, all `tests/**/*.py`, provider-wide special
      casing, or repo-wide timeout retuning.
- [ ] IF-0-SEMROOTTESTABORT-3 - Force-full later-blocker truthfulness contract:
      once the rerun reaches the later root-test pair, the dispatcher,
      `force_full_exit_trace.json`, and `repository status` either advance
      durably beyond that pair or record the real later blocker family, stage,
      and source exactly; they must not collapse back to a generic abort story
      with no downstream cause.
- [ ] IF-0-SEMROOTTESTABORT-4 - Operator and evidence contract:
      `force_full_exit_trace.json`, `uv run mcp-index repository status`, and
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` stay aligned on the rerun
      command, exit code or blocker classification, timestamps, progress paths,
      current-versus-indexed commit evidence, summary/vector counts, and the
      final live verdict.
- [ ] IF-0-SEMROOTTESTABORT-5 - Upstream-boundary preservation contract:
      SEMSCRIPTABORT, SEMTESTSTALE, SEMDEVSTALE, and the earlier exact bounded
      paths for `scripts/validate_mcp_comprehensive.py`,
      `tests/test_artifact_publish_race.py`,
      `scripts/quick_mcp_vs_native_validation.py`,
      `scripts/create_multi_repo_visual_report.py`, and
      `.devcontainer/devcontainer.json` remain closed unless the refreshed live
      rerun directly re-anchors on one of those exact historical seams again.

## Lane Index & Dependencies

- SL-0 - Later root-test abort fixture freeze; Depends on: SEMSCRIPTABORT; Blocks: SL-1, SL-2, SL-3; Parallel-safe: no
- SL-1 - Exact later root-test recovery or blocker capture; Depends on: SL-0; Blocks: SL-2, SL-3; Parallel-safe: no
- SL-2 - Repository-status boundary and force-full trace alignment; Depends on: SL-0, SL-1; Blocks: SL-3; Parallel-safe: no
- SL-3 - Live rerun evidence reducer and closeout refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SEMROOTTESTABORT acceptance; Parallel-safe: no

Lane DAG:

```text
SEMSCRIPTABORT
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SEMROOTTESTABORT acceptance
```

## Lanes

### SL-0 - Later Root-Test Abort Fixture Freeze

- **Scope**: Freeze the current
  `tests/root_tests/test_voyage_api.py ->
  tests/root_tests/run_reranking_tests.py` rebound shape in dispatcher and
  git-manager coverage so this phase proves the exact later root-test abort
  after SEMSCRIPTABORT instead of relying on the already-cleared script seam.
- **Owned files**: `tests/test_dispatcher.py`, `tests/test_git_index_manager.py`
- **Interfaces provided**: executable assertions for IF-0-SEMROOTTESTABORT-1,
  IF-0-SEMROOTTESTABORT-3, and IF-0-SEMROOTTESTABORT-5
- **Interfaces consumed**: existing
  `EnhancedDispatcher.index_directory(...)`,
  `EnhancedDispatcher._index_file_with_lexical_timeout(...)`,
  `GitAwareIndexManager._make_force_full_progress_callback(...)`,
  `GitAwareIndexManager._write_force_full_exit_trace(...)`,
  `GitAwareIndexManager._finalize_running_force_full_trace_as_interrupted(...)`,
  and the current SEMSCRIPTABORT evidence wording for the later root-test pair
  and exit code `135`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` with a repo-shaped fixture that
    freezes the later root-test pair after the SEMSCRIPTABORT script seam has
    already been cleared, and proves the dispatcher emits either a durable
    downstream handoff or an exact later blocker instead of leaving the abort
    story implicit.
  - test: Extend `tests/test_git_index_manager.py` so durable force-full trace
    persistence freezes the later root-test abort shape, including preserved
    `last_progress_path`, preserved `in_flight_path`, dead-process rewrite to
    `status=interrupted`, and the requirement that the exact later blocker
    remains attributable to the root-test family.
  - test: Require negative assertions that the earlier exact seams for
    `tests/test_reindex_resume.py`,
    `scripts/validate_mcp_comprehensive.py`,
    `tests/test_artifact_publish_race.py`, and
    `.devcontainer/devcontainer.json` do not silently become the active
    blocker again under this later root-test fixture.
  - impl: Use synthetic dispatcher progress, synthetic durable-trace payloads,
    and explicit abnormal-exit fixtures rather than a live multi-minute rerun
    inside unit coverage.
  - impl: Keep this lane focused on contract freeze only. Do not update the
    operator status text surface or the dogfood evidence artifact here.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov -k "voyage_api or reranking_tests or force_full or lexical or trace or interrupted"`

### SL-1 - Exact Later Root-Test Recovery Or Blocker Capture

- **Scope**: Implement the smallest exact repair needed so the later
  `tests/root_tests/test_voyage_api.py ->
  tests/root_tests/run_reranking_tests.py` seam no longer ends in an
  unclassified code-`135` abort after SEMSCRIPTABORT has already restored
  truthful interrupted traces for the script pair.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `mcp_server/storage/git_index_manager.py`
- **Interfaces provided**: IF-0-SEMROOTTESTABORT-1 exact later root-test abort contract;
  IF-0-SEMROOTTESTABORT-2 exact bounded recovery contract;
  IF-0-SEMROOTTESTABORT-3 force-full later-blocker truthfulness contract
- **Interfaces consumed**: SL-0 later root-test fixtures; existing exact
  bounded Python path handling and lexical progress emission; existing
  `force_full_closeout_handoff` behavior; durable `process_id`,
  `last_progress_path`, and `in_flight_path` persistence; dead-process rewrite
  logic; and the live SEMSCRIPTABORT evidence showing exit code `135` on
  `tests/root_tests/test_voyage_api.py ->
  tests/root_tests/run_reranking_tests.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 dispatcher and git-manager slices first and confirm the
    current checkout still reproduces the later root-test abort shape or leaves
    the later blocker under-classified.
  - impl: Determine whether the remaining failure occurs during lexical
    mutation of `tests/root_tests/run_reranking_tests.py`, during the immediate
    handoff after `tests/root_tests/test_voyage_api.py`, or during later trace
    finalization or blocker classification, and repair only that nearest seam.
  - impl: If the root cause is still root-test-local lexical handling, keep the
    repair limited to the exact later pair or the immediate handoff after
    `tests/root_tests/test_voyage_api.py`; do not broaden to arbitrary
    `tests/root_tests/*.py`, all Python test files, or a repo-wide lexical
    timeout retune.
  - impl: If the rerun still cannot progress past the later pair, prefer a
    durable exact blocker classification with truthful stage and source fields
    over another generic `interrupted` outcome that hides the downstream cause.
  - impl: Preserve the already-closed historical seams for
    `scripts/validate_mcp_comprehensive.py`,
    `tests/test_reindex_resume.py`,
    `tests/test_artifact_publish_race.py`,
    `scripts/quick_mcp_vs_native_validation.py`,
    `scripts/create_multi_repo_visual_report.py`, and
    `.devcontainer/devcontainer.json`. Do not reopen those earlier phases
    unless the refreshed rerun directly re-anchors there again.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov -k "voyage_api or reranking_tests or force_full or lexical or trace or interrupted"`
  - verify: `rg -n "test_voyage_api|run_reranking_tests|force_full_closeout_handoff|last_progress_path|in_flight_path|process_id|interrupted|blocked_|validate_mcp_comprehensive|artifact_publish_race|devcontainer.json" mcp_server/dispatcher/dispatcher_enhanced.py mcp_server/storage/git_index_manager.py tests/test_dispatcher.py tests/test_git_index_manager.py`

### SL-2 - Repository-Status Boundary And Force-Full Trace Alignment

- **Scope**: Keep the operator-facing status surface aligned with the repaired
  later root-test seam so `repository status` and the durable trace present
  either the cleared path or the real later blocker without regressing earlier
  exact boundary copy.
- **Owned files**: `mcp_server/cli/repository_commands.py`, `tests/test_repository_commands.py`
- **Interfaces provided**: IF-0-SEMROOTTESTABORT-3 force-full later-blocker truthfulness contract;
  IF-0-SEMROOTTESTABORT-4 operator and evidence contract;
  IF-0-SEMROOTTESTABORT-5 upstream-boundary preservation contract
- **Interfaces consumed**: SL-0 later root-test fixture vocabulary; SL-1
  repair choice and later blocker classification; existing exact boundary
  helpers for `scripts/create_multi_repo_visual_report.py`,
  `scripts/quick_mcp_vs_native_validation.py`,
  `scripts/validate_mcp_comprehensive.py`,
  `tests/test_artifact_publish_race.py`, and
  `.devcontainer/devcontainer.json`; plus the current force-full trace printer
  in `_print_force_full_exit_trace(...)`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_repository_commands.py` so `repository status`
    freezes the exact later root-test pair and proves the repaired path either
    advances beyond it or reports the real later blocker without falling back
    to stale-running wording or boundary copy from earlier phases.
  - impl: If SL-1 introduces an exact root-test-specific recovery for one of
    the two later root-test files, add only the matching minimal operator
    boundary line. If SL-1 solves the issue through later blocker
    classification alone, keep this lane limited to truthful trace and status
    rendering and do not add misleading exact-boundary copy.
  - impl: Preserve the existing boundary lines for
    `scripts/create_multi_repo_visual_report.py`,
    `scripts/quick_mcp_vs_native_validation.py`,
    `scripts/validate_mcp_comprehensive.py`,
    `tests/test_artifact_publish_race.py`, and
    `.devcontainer/devcontainer.json`.
  - impl: Keep fail-closed semantics intact. If the live rerun still blocks,
    surface the true later blocker rather than claiming lexical, storage, or
    semantic readiness early.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_repository_commands.py -q --no-cov -k "voyage_api or reranking_tests or force_full or interrupted or boundary"`
  - verify: `rg -n "test_voyage_api|run_reranking_tests|Trace status|Trace stage|Trace blocker source|Last progress path|In-flight path|validate_mcp_comprehensive|quick_mcp_vs_native_validation|artifact_publish_race|devcontainer.json" mcp_server/cli/repository_commands.py tests/test_repository_commands.py`

### SL-3 - Live Rerun Evidence Reducer And Closeout Refresh

- **Scope**: Re-run the repaired repo-local force-full path, reduce the real
  outcome into the dogfood evidence artifact, and keep the final closeout
  narrative aligned with the actual post-repair later root-test rerun.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: IF-0-SEMROOTTESTABORT-4 operator and evidence contract;
  IF-0-SEMROOTTESTABORT-5 upstream-boundary preservation contract
- **Interfaces consumed**: SL-0 later root-test fixture vocabulary; SL-1
  repaired blocker or recovery outcome; SL-2 repository-status and durable
  trace fields; observed commit `098c1ad19c3957af05bf1bfaf4ee6ceb07b73cce`;
  current-versus-indexed commit evidence; SQLite summary/vector counts; and the
  current roadmap steering from `SEMSCRIPTABORT` to `SEMROOTTESTABORT`
- **Parallel-safe**: no
- **Tasks**:
  - test: Update `tests/docs/test_semdogfood_evidence_contract.py` so the
    report cites `plans/phase-plan-v7-SEMROOTTESTABORT.md`, preserves the
    earlier lexical-boundary lineage, and records the later
    `tests/root_tests/test_voyage_api.py ->
    tests/root_tests/run_reranking_tests.py` evidence plus the repaired rerun
    outcome.
  - impl: Re-run the repo-local force-full command with the same strict
    watchdog posture used by the recent semantic dogfood phases and capture the
    resulting trace, status output, exit code or later blocker classification,
    commit evidence, and runtime counts.
  - impl: Refresh `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` with the rerun
    command, timestamps, `force_full_exit_trace.json` fields, repository-status
    lines, current-versus-indexed commit evidence, and the final verdict:
    either the later root-test abort is cleared and a new exact blocker is
    named, or the same root-test seam still fails closed with truthful repaired
    reporting.
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
`codex-execute-phase` or manual SEMROOTTESTABORT execution.

Lane-specific checks:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov -k "voyage_api or reranking_tests or force_full or lexical or trace or interrupted"
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_repository_commands.py -q --no-cov -k "voyage_api or reranking_tests or force_full or interrupted or boundary"
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
rg -n "test_voyage_api|run_reranking_tests|force_full_closeout_handoff|last_progress_path|in_flight_path|process_id|Trace blocker source|validate_mcp_comprehensive|quick_mcp_vs_native_validation|artifact_publish_race|devcontainer.json" \
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

- [ ] A refreshed repo-local force-full rerun on the post-SEMSCRIPTABORT head
      no longer exits with code `135` after advancing into
      `tests/root_tests/test_voyage_api.py ->
      tests/root_tests/run_reranking_tests.py` without either completing or
      naming the real later exact blocker truthfully.
- [ ] `force_full_exit_trace.json` and
      `uv run mcp-index repository status` either advance durably beyond
      `tests/root_tests/test_voyage_api.py ->
      tests/root_tests/run_reranking_tests.py` or fail closed with the real
      later root-test blocker, including truthful stage and source fields.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is refreshed with the
      SEMSCRIPTABORT repair, the later root-test-pair evidence on commit
      `098c1ad19c3957af05bf1bfaf4ee6ceb07b73cce`, and the final live verdict
      for the rerun.
- [ ] Earlier exact boundaries for
      `scripts/validate_mcp_comprehensive.py`,
      `tests/test_reindex_resume.py`,
      `tests/test_artifact_publish_race.py`,
      `scripts/quick_mcp_vs_native_validation.py`,
      `scripts/create_multi_repo_visual_report.py`, and
      `.devcontainer/devcontainer.json` remain preserved unless the live rerun
      re-anchors on one of them again.
