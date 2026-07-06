---
phase_loop_plan_version: 1
phase: SEMQUICKCHARTS
roadmap: specs/phase-plans-v7.md
roadmap_sha256: a683cdf80bf3872fb669aef549b501054a6824b6961feb4b4e1d29f9e721e64a
---
# SEMQUICKCHARTS: Visualization Quick Charts Lexical Recovery

## Context

SEMQUICKCHARTS is the phase-42 follow-up for the v7 semantic hardening
roadmap. SEMWALKGAP cleared the post-devcontainer ignored-tail relapse and
committed that closeout on `5479145653bc4fd49d34583f94c38fc9cd18a162`, but the
refreshed live repo-local force-full rerun on the same head still timed out in
lexical walking with the durable trace advanced to the later visualization
pair `mcp_server/visualization/__init__.py ->
mcp_server/visualization/quick_charts.py`.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is the active roadmap, it is tracked and clean in
  this worktree, and canonical `.phase-loop/state.json` reports the required
  `roadmap_sha256`
  `a683cdf80bf3872fb669aef549b501054a6824b6961feb4b4e1d29f9e721e64a`.
- Canonical phase-loop state exists under `.phase-loop/`; `.phase-loop/state.json`
  and `.phase-loop/tui-handoff.md` both mark `SEMQUICKCHARTS` as the current
  unplanned phase after `SEMWALKGAP` closed out with verification passed, a
  clean worktree, and `main...origin/main [ahead 79]`. Legacy
  `.codex/phase-loop/` artifacts are compatibility-only and are not
  authoritative for this run.
- The target artifact `plans/phase-plan-v7-SEMQUICKCHARTS.md` did not exist
  before this planning run.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is the active evidence anchor. Its
  latest SEMWALKGAP refresh records the repaired rerun, the durable
  `force_full_exit_trace.json` fields
  `status=interrupted`,
  `stage=lexical_walking`,
  `blocker_source=lexical_mutation`,
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/mcp_server/visualization/__init__.py`,
  and
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/mcp_server/visualization/quick_charts.py`,
  plus the roadmap steering that adds `SEMQUICKCHARTS` as the next downstream
  phase.
- The current implementation surfaces are split. `Plugin._BOUNDED_CHUNK_PATHS`
  in `mcp_server/plugins/python_plugin/plugin.py` already carries earlier exact
  bounded Python seams such as
  `scripts/create_multi_repo_visual_report.py`,
  `scripts/quick_mcp_vs_native_validation.py`, and
  `tests/test_artifact_publish_race.py`, while
  `EnhancedDispatcher._EXACT_BOUNDED_PYTHON_PATHS` in
  `mcp_server/dispatcher/dispatcher_enhanced.py` currently carries later exact
  rebound seams for
  `scripts/validate_mcp_comprehensive.py` and
  `tests/root_tests/run_reranking_tests.py`. The visualization pair is in
  neither bounded-path surface today.
- `mcp_server/visualization/__init__.py` is a trivial re-export wrapper, but
  `mcp_server/visualization/quick_charts.py` is a tracked Python source file
  with about `501` lines and top-level imports for `matplotlib.pyplot` and
  `numpy`. That makes this seam a good candidate for either an exact bounded
  Python indexing path or the smallest source-local simplification that keeps
  the same charting contract while letting lexical indexing finish under the
  existing watchdog.
- Existing unit coverage already proves earlier exact bounded Python seams, but
  there is no current dispatcher, git-index-manager, or repository-status test
  that freezes the visualization pair as the next later lexical blocker.
  `tests/test_python_plugin.py` likewise has no direct coverage for
  `mcp_server/visualization/quick_charts.py`.
- `mcp_server/cli/repository_commands.py` still prints explicit boundary lines
  for earlier exact seams such as
  `scripts/create_multi_repo_visual_report.py`,
  `scripts/quick_mcp_vs_native_validation.py`,
  `.devcontainer/devcontainer.json`, and `test_workspace/`, but it does not yet
  surface a visualization-specific boundary or clarified later-blocker wording
  for `quick_charts.py`.

Practical planning boundary:

- SEMQUICKCHARTS may implement one exact recovery for
  `mcp_server/visualization/__init__.py ->
  mcp_server/visualization/quick_charts.py`: an exact bounded Python indexing
  path, the smallest source-local simplification inside the visualization pair,
  or the minimum combination needed to move the live rerun durably beyond this
  seam.
- SEMQUICKCHARTS must stay narrow and evidence-driven. It must not reopen the
  post-devcontainer ignore-tail recovery, older script/root-test rebounds, or
  broader semantic-closeout and summary/vector work unless the refreshed rerun
  directly reaches a newer blocker after this visualization pair is cleared.

## Interface Freeze Gates

- [ ] IF-0-SEMQUICKCHARTS-1 - Exact visualization-pair recovery contract:
      a refreshed repo-local `repository sync --force-full` no longer leaves
      the durable lexical trace on
      `mcp_server/visualization/__init__.py ->
      mcp_server/visualization/quick_charts.py`; it either advances durably
      beyond `quick_charts.py` or emits a truthful newer blocker before the
      120-second watchdog expires.
- [ ] IF-0-SEMQUICKCHARTS-2 - Bounded Python repair contract: the chosen
      repair remains limited to the exact visualization pair and the immediate
      dispatcher/plugin plumbing needed to prove it; it does not broaden into
      arbitrary `mcp_server/**/*.py`, repo-wide Python chunk-bypass policy, or
      a global lexical-timeout retune.
- [ ] IF-0-SEMQUICKCHARTS-3 - Lexical discoverability contract: the repaired
      path keeps `mcp_server/visualization/quick_charts.py` represented in
      stored file content and preserves the top-level symbol surface needed for
      repo-local lexical search and definitions, even if heavyweight chunking
      is reduced or bypassed.
- [ ] IF-0-SEMQUICKCHARTS-4 - Trace and operator truthfulness contract:
      `EnhancedDispatcher`, `GitAwareIndexManager`, `force_full_exit_trace.json`,
      and `uv run mcp-index repository status` agree on the repaired
      visualization outcome and do not regress earlier exact boundary wording
      for `scripts/create_multi_repo_visual_report.py`,
      `scripts/quick_mcp_vs_native_validation.py`,
      `tests/test_artifact_publish_race.py`,
      `.devcontainer/devcontainer.json`, or `test_workspace/`.
- [ ] IF-0-SEMQUICKCHARTS-5 - Evidence contract:
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the SEMWALKGAP rerun
      outcome, the repaired SEMQUICKCHARTS rerun command and timestamps, the
      refreshed durable trace/status output, and the final authoritative
      verdict for the visualization blocker.
- [ ] IF-0-SEMQUICKCHARTS-6 - Upstream/downstream preservation contract:
      SEMWALKGAP and the earlier exact bounded Python seams remain historically
      valid and closed unless the refreshed rerun directly re-anchors on a
      different later blocker after `quick_charts.py` is cleared.

## Lane Index & Dependencies

- SL-0 - Visualization pair timeout contract and fixture freeze; Depends on: SEMWALKGAP; Blocks: SL-1, SL-2, SL-3; Parallel-safe: no
- SL-1 - Exact visualization bounded recovery or minimal source simplification; Depends on: SL-0; Blocks: SL-2, SL-3; Parallel-safe: no
- SL-2 - Force-full trace and repository-status alignment; Depends on: SL-0, SL-1; Blocks: SL-3; Parallel-safe: no
- SL-3 - Live rerun evidence reducer and closeout refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SEMQUICKCHARTS acceptance; Parallel-safe: no

Lane DAG:

```text
SEMWALKGAP
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SEMQUICKCHARTS acceptance
```

## Lanes

### SL-0 - Visualization Pair Timeout Contract And Fixture Freeze

- **Scope**: Freeze the exact `mcp_server/visualization/__init__.py ->
  mcp_server/visualization/quick_charts.py` lexical seam in unit coverage so
  this phase proves a bounded visualization repair instead of only moving the
  live timeout somewhere less visible.
- **Owned files**: `tests/test_dispatcher.py`, `tests/test_git_index_manager.py`, `tests/test_python_plugin.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMQUICKCHARTS-1,
  IF-0-SEMQUICKCHARTS-2,
  IF-0-SEMQUICKCHARTS-3,
  and IF-0-SEMQUICKCHARTS-6
- **Interfaces consumed**: existing
  `EnhancedDispatcher.index_directory(...)`,
  `EnhancedDispatcher._build_exact_bounded_python_shard(...)`,
  `GitAwareIndexManager._write_force_full_exit_trace(...)`,
  `GitAwareIndexManager._finalize_running_force_full_trace_as_interrupted(...)`,
  `Plugin.indexFile(...)`,
  `Plugin._BOUNDED_CHUNK_PATHS`,
  and the current SEMWALKGAP evidence wording for the visualization pair
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` with a repo-shaped fixture that
    freezes `mcp_server/visualization/__init__.py` as the latest durable
    `last_progress_path` and `mcp_server/visualization/quick_charts.py` as the
    exact `in_flight_path`, then proves the repaired path advances beyond
    `quick_charts.py` without weakening the lexical watchdog for unrelated
    Python files.
  - test: Extend `tests/test_git_index_manager.py` so durable force-full trace
    persistence freezes the visualization-pair handoff, preserves truthful
    interrupted-finalization semantics, and requires the final durable trace to
    move past `quick_charts.py` or expose a newer later blocker.
  - test: Extend `tests/test_python_plugin.py` so whichever bounded recovery is
    chosen still preserves stored file rows, FTS-backed file content, and
    top-level symbols for `mcp_server/visualization/quick_charts.py`, even if
    chunk generation is reduced or skipped.
  - test: Require negative assertions that earlier exact bounded seams for
    `scripts/create_multi_repo_visual_report.py`,
    `scripts/quick_mcp_vs_native_validation.py`,
    `tests/test_artifact_publish_race.py`, and
    `tests/root_tests/run_reranking_tests.py` do not silently regress under the
    new visualization fixtures.
  - impl: Use synthetic dispatcher progress and synthetic durable-trace
    payloads rather than a live multi-minute rerun inside unit coverage.
  - impl: Keep this lane focused on contract freeze only. Do not update status
    wording or the dogfood evidence artifact here.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_python_plugin.py -q --no-cov -k "quick_charts or visualization or lexical or force_full or bounded or trace"`

### SL-1 - Exact Visualization Bounded Recovery Or Minimal Source Simplification

- **Scope**: Implement the smallest exact repair needed so the later
  visualization pair can complete lexical indexing under the existing watchdog
  without broadening repo-wide Python behavior.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `mcp_server/plugins/python_plugin/plugin.py`, `mcp_server/visualization/__init__.py`, `mcp_server/visualization/quick_charts.py`
- **Interfaces provided**: IF-0-SEMQUICKCHARTS-1 exact visualization-pair
  recovery contract; IF-0-SEMQUICKCHARTS-2 bounded Python repair contract;
  IF-0-SEMQUICKCHARTS-3 lexical discoverability contract
- **Interfaces consumed**: SL-0 visualization fixtures; existing
  `_EXACT_BOUNDED_PYTHON_PATHS`,
  `Plugin._BOUNDED_CHUNK_PATHS`,
  the current top-level import and function layout in
  `mcp_server/visualization/quick_charts.py`,
  and the current re-export surface in
  `mcp_server/visualization/__init__.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 dispatcher, git-manager, and python-plugin slices first
    and confirm the current checkout still reproduces the later visualization
    seam or leaves the exact repair path unimplemented.
  - impl: Determine whether the minimal repair belongs in the dispatcher exact
    bounded-path surface, the python-plugin bounded-chunk surface, the
    visualization source pair itself, or the smallest combination required to
    let lexical indexing finish on `quick_charts.py`.
  - impl: If a bounded-path repair is chosen, keep it exact to
    `mcp_server/visualization/quick_charts.py` or the immediate
    `__init__.py -> quick_charts.py` pair. Do not introduce a broad
    `mcp_server/visualization/*.py` or repository-wide Python exemption.
  - impl: If a source-local simplification is chosen, preserve the public
    `QuickCharts` export, chart-generation behavior, and output contract.
    This phase is about lexical recoverability, not a redesign of the
    visualization API.
  - impl: Preserve lexical file storage and top-level symbol discoverability
    for `quick_charts.py`; the repair must not turn the visualization module
    into an ignored file or silently remove it from lexical FTS.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_python_plugin.py tests/test_dispatcher.py -q --no-cov -k "quick_charts or visualization or bounded"`
  - verify: `rg -n "_EXACT_BOUNDED_PYTHON_PATHS|_BOUNDED_CHUNK_PATHS|quick_charts|QuickCharts|matplotlib|numpy" mcp_server/dispatcher/dispatcher_enhanced.py mcp_server/plugins/python_plugin/plugin.py mcp_server/visualization/__init__.py mcp_server/visualization/quick_charts.py tests/test_dispatcher.py tests/test_python_plugin.py`

### SL-2 - Force-Full Trace And Repository-Status Alignment

- **Scope**: Carry the chosen visualization repair through durable trace
  closeout and keep the operator-facing status surface aligned with the exact
  later blocker or recovery outcome.
- **Owned files**: `mcp_server/storage/git_index_manager.py`, `mcp_server/cli/repository_commands.py`, `tests/test_repository_commands.py`
- **Interfaces provided**: IF-0-SEMQUICKCHARTS-4 trace and operator
  truthfulness contract; IF-0-SEMQUICKCHARTS-6 upstream/downstream
  preservation contract
- **Interfaces consumed**: SL-0 fixture vocabulary; SL-1 chosen repair; the
  current force-full trace writer/finalizer; `_print_force_full_exit_trace(...)`;
  existing boundary helpers for
  `scripts/create_multi_repo_visual_report.py`,
  `scripts/quick_mcp_vs_native_validation.py`,
  `.devcontainer/devcontainer.json`,
  and `test_workspace/`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_repository_commands.py` so `repository status`
    freezes the exact visualization pair and proves the repaired path either
    advances beyond `quick_charts.py` or reports the real later blocker without
    falling back to stale-running wording or boundary copy from older phases.
  - impl: Thread the chosen visualization repair through durable trace writing
    and repository-status wording only as needed so operators can tell whether
    `quick_charts.py` now uses an exact bounded path, completed normally, or
    exposed a newer exact blocker.
  - impl: If SL-1 introduces an exact visualization-specific bounded path, add
    only the matching minimal operator boundary line. If SL-1 resolves the seam
    through source-local simplification alone, keep this lane limited to
    truthful trace/status rendering and do not add misleading boundary copy.
  - impl: Preserve the existing boundary lines for
    `scripts/create_multi_repo_visual_report.py`,
    `scripts/quick_mcp_vs_native_validation.py`,
    `tests/test_artifact_publish_race.py`,
    `.devcontainer/devcontainer.json`,
    and `test_workspace/`.
  - impl: Keep fail-closed semantics intact. If the live rerun still blocks,
    surface the true later blocker rather than claiming lexical or semantic
    readiness early.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_repository_commands.py -q --no-cov -k "quick_charts or visualization or boundary or force_full or interrupted"`
  - verify: `rg -n "quick_charts|visualization/__init__|Trace status|Trace stage|Trace blocker source|Last progress path|In-flight path|create_multi_repo_visual_report|quick_mcp_vs_native_validation|test_workspace" mcp_server/storage/git_index_manager.py mcp_server/cli/repository_commands.py tests/test_repository_commands.py`

### SL-3 - Live Rerun Evidence Reducer And Closeout Refresh

- **Scope**: Re-run the repaired repo-local force-full path, reduce the real
  outcome into the dogfood evidence artifact, and keep the closeout narrative
  aligned with the actual post-repair visualization rerun.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: IF-0-SEMQUICKCHARTS-5 evidence contract;
  IF-0-SEMQUICKCHARTS-6 upstream/downstream preservation contract
- **Interfaces consumed**: SL-0 fixture vocabulary; SL-1 chosen repair; SL-2
  rerun command, durable trace, and repository-status wording; current versus
  indexed commit evidence; SQLite runtime counts; and the current roadmap
  steering from `SEMWALKGAP` to `SEMQUICKCHARTS`
- **Parallel-safe**: no
- **Tasks**:
  - test: Update `tests/docs/test_semdogfood_evidence_contract.py` so the
    report cites `plans/phase-plan-v7-SEMQUICKCHARTS.md`, preserves the earlier
    lexical-boundary lineage, and records the visualization-pair rerun outcome.
  - impl: Re-run the repo-local force-full command with the same strict
    watchdog posture used by the recent semantic dogfood phases and capture the
    resulting durable trace, status output, exit code or newer blocker
    classification, commit evidence, and runtime counts.
  - impl: Refresh `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` with the
    SEMWALKGAP visualization-pair evidence, the repaired SEMQUICKCHARTS rerun
    command, timestamps, `force_full_exit_trace.json` fields,
    repository-status lines, current-versus-indexed commit evidence, and the
    final verdict: either the rerun now moves durably beyond
    `quick_charts.py`, or a newer exact blocker is named.
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
`codex-execute-phase` or manual SEMQUICKCHARTS execution.

Lane-specific checks:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_python_plugin.py -q --no-cov -k "quick_charts or visualization or lexical or force_full or bounded or trace"
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_repository_commands.py -q --no-cov -k "quick_charts or visualization or boundary or force_full or interrupted"
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
rg -n "quick_charts|visualization/__init__|_EXACT_BOUNDED_PYTHON_PATHS|_BOUNDED_CHUNK_PATHS|Trace status|Trace stage|Trace blocker source|Last progress path|In-flight path|create_multi_repo_visual_report|quick_mcp_vs_native_validation|test_workspace" \
  mcp_server/dispatcher/dispatcher_enhanced.py \
  mcp_server/plugins/python_plugin/plugin.py \
  mcp_server/storage/git_index_manager.py \
  mcp_server/cli/repository_commands.py \
  mcp_server/visualization/__init__.py \
  mcp_server/visualization/quick_charts.py \
  tests/test_dispatcher.py \
  tests/test_git_index_manager.py \
  tests/test_python_plugin.py \
  tests/test_repository_commands.py \
  tests/docs/test_semdogfood_evidence_contract.py
```

Whole-phase live verification after code changes:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest \
  tests/test_dispatcher.py \
  tests/test_git_index_manager.py \
  tests/test_python_plugin.py \
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
git status --short -- specs/phase-plans-v7.md plans/phase-plan-v7-SEMQUICKCHARTS.md
```

## Acceptance Criteria

- [ ] A refreshed repo-local force-full rerun on the post-SEMWALKGAP head no
      longer leaves the durable lexical trace on
      `mcp_server/visualization/__init__.py ->
      mcp_server/visualization/quick_charts.py`; it either advances beyond
      `quick_charts.py` or fails closed with a truthful newer blocker before
      the 120-second watchdog expires.
- [ ] The repair remains bounded to the exact visualization pair and the
      immediate dispatcher/plugin plumbing needed to prove it, without
      broadening into repo-wide Python exemptions or unrelated timeout retunes.
- [ ] `mcp_server/visualization/quick_charts.py` remains discoverable through
      stored file content and preserves its top-level symbol surface after the
      repair, even if heavyweight chunking is reduced.
- [ ] `force_full_exit_trace.json` and
      `uv run mcp-index repository status` agree on the repaired outcome and do
      not regress earlier exact boundary wording for
      `scripts/create_multi_repo_visual_report.py`,
      `scripts/quick_mcp_vs_native_validation.py`,
      `tests/test_artifact_publish_race.py`,
      `.devcontainer/devcontainer.json`, or `test_workspace/`.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` cites
      `plans/phase-plan-v7-SEMQUICKCHARTS.md` and records the SEMWALKGAP
      visualization-pair evidence, the repaired SEMQUICKCHARTS rerun, and the
      final authoritative blocker or advancement verdict.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v7-SEMQUICKCHARTS.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMQUICKCHARTS.md
  artifact_state: staged
```
