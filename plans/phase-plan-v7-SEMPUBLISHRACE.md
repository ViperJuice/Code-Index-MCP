---
phase_loop_plan_version: 1
phase: SEMPUBLISHRACE
roadmap: specs/phase-plans-v7.md
roadmap_sha256: fa71b23a42bf18db73f41610aaae9f3e648f20757dce7043995a8cd4962dc9b1
---
# SEMPUBLISHRACE: Artifact Publish Race Lexical Exit Recovery

## Context

SEMPUBLISHRACE is the phase-32 follow-up for the v7 semantic hardening
roadmap. SEMDEVCONTAINER proved the live repo-local `repository sync
--force-full` rerun now advances beyond `.devcontainer/devcontainer.json`, but
the same rerun still stops refreshing on
`tests/test_artifact_publish_race.py`.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is the active roadmap, `sha256sum
  specs/phase-plans-v7.md` matches the required
  `fa71b23a42bf18db73f41610aaae9f3e648f20757dce7043995a8cd4962dc9b1`, and the
  canonical `.phase-loop/state.json` records the same roadmap SHA for the
  current `SEMPUBLISHRACE` handoff.
- Canonical phase-loop state exists under `.phase-loop/`; `.phase-loop/state.json`
  marks `SEMPUBLISHRACE` as the current `unplanned` phase and
  `.phase-loop/tui-handoff.md` says the next run should plan that phase.
  Legacy `.codex/phase-loop/` compatibility files are not needed and should
  not supersede this state.
- The checkout is on `main` at `f9a00775f1862bcf098c00cc445be92e31743979`
  (`f9a0077` short), `main...origin/main` is ahead by `59` commits, and the
  worktree is clean before writing this artifact. The target plan path
  `plans/phase-plan-v7-SEMPUBLISHRACE.md` did not exist before this run.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is the active blocker artifact.
  Its latest SEMDEVCONTAINER snapshot (`2026-04-29T09:10:41Z`, observed commit
  `cb748650`) records a live rerun that advanced beyond the prior
  `.devcontainer` seam and then stopped refreshing with
  `trace_status=running`, `trace_stage=lexical_walking`,
  `trace_timestamp=2026-04-29T09:09:48Z`,
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/tests/test_benchmarks.py`,
  and
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/tests/test_artifact_publish_race.py`.
- The current blocker shape is therefore no longer a stale-trace problem.
  SEMTRACEFRESHNESS already repaired live in-flight persistence and operator
  stale-running wording; the next exact work item is making this Python test
  seam exit cleanly or surface a bounded blocker truthfully.
- `tests/test_artifact_publish_race.py` is a tracked Python test file that is
  materially larger than the prior closed lexical seams and currently has no
  exact bounded-path exemption. The adjacent `tests/test_benchmarks.py` marker
  is the last completed lexical progress point, not the active blocker.
- The existing narrow Python-boundary mechanism already lives in
  `mcp_server/plugins/python_plugin/plugin.py`: `_BOUNDED_CHUNK_PATHS` currently
  contains only `scripts/create_multi_repo_visual_report.py`, and
  `_uses_bounded_chunk_path(...)` skips expensive chunk generation while still
  storing file and symbol metadata for that exact path.
- Existing coverage already freezes adjacent surfaces:
  `tests/test_dispatcher.py` proves the exact bounded Python path for
  `scripts/create_multi_repo_visual_report.py`,
  `tests/test_repository_commands.py` prints the corresponding operator
  boundary line, and `tests/docs/test_semdogfood_evidence_contract.py` already
  names `SEMPUBLISHRACE` as the next downstream phase after the current live
  rerun evidence.
- `mcp_server/cli/repository_commands.py` already reports lexical boundaries
  for generated fast-test reports, `ai_docs/*_overview.md`, `ai_docs/jedi.md`,
  and `scripts/create_multi_repo_visual_report.py`, plus the live force-full
  trace freshness surface. No status surface currently explains an exact
  bounded path for `tests/test_artifact_publish_race.py`.

Practical planning boundary:

- SEMPUBLISHRACE may add an exact bounded Python path for
  `tests/test_artifact_publish_race.py`, carry that change through the live
  rerun and operator status surface, and refresh the dogfood evidence with the
  new rerun outcome.
- SEMPUBLISHRACE must stay narrow. It must not reopen the `.devcontainer`,
  `ai_docs/jedi.md`, `ai_docs/*_overview.md`, fast-report, visual-report,
  trace-freshness, summary-timeout, or semantic-write phases unless a fresh
  rerun directly re-anchors there.

## Interface Freeze Gates

- [ ] IF-0-SEMPUBLISHRACE-1 - Exact publish-race exit contract:
      a live repo-local `repository sync --force-full` no longer remains past
      the configured lexical-timeout window with
      `last_progress_path=/home/viperjuice/code/Code-Index-MCP/tests/test_benchmarks.py`
      and
      `in_flight_path=/home/viperjuice/code/Code-Index-MCP/tests/test_artifact_publish_race.py`
      while the durable trace timestamp stays unchanged.
- [ ] IF-0-SEMPUBLISHRACE-2 - Narrow exact Python boundary contract:
      if the repair uses bounded lexical handling, it applies only to
      `tests/test_artifact_publish_race.py` or a stricter exact-path alias,
      preserves Python symbol discoverability for that file, and does not
      broaden to `tests/*.py`, `test_*.py`, or repo-wide Python bypasses.
- [ ] IF-0-SEMPUBLISHRACE-3 - Operator status contract:
      `uv run mcp-index repository status` stays aligned with the configured
      timeout window, preserves prior lexical-boundary wording, and explains
      the exact `tests/test_artifact_publish_race.py` boundary if that repair
      is adopted.
- [ ] IF-0-SEMPUBLISHRACE-4 - Evidence contract:
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the chosen repair, the
      rerun command and timestamps, the refreshed force-full trace, and the
      next exact blocker if semantic-stage work still does not begin.
- [ ] IF-0-SEMPUBLISHRACE-5 - Upstream-boundary preservation contract:
      SEMFASTREPORT, SEMPYTESTOVERVIEW, SEMVISUALREPORT, SEMJEDI,
      SEMTRACEFRESHNESS, and SEMDEVCONTAINER remain closed unless the refreshed
      rerun directly re-anchors on one of those exact seams.

## Lane Index & Dependencies

- SL-0 - Exact artifact-publish Python boundary and dispatcher contract; Depends on: SEMDEVCONTAINER; Blocks: SL-1, SL-2; Parallel-safe: no
- SL-1 - Repository-status boundary surfacing and rerun truthfulness; Depends on: SL-0; Blocks: SL-2; Parallel-safe: no
- SL-2 - Dogfood evidence reducer and live rerun refresh; Depends on: SL-0, SL-1; Blocks: SEMPUBLISHRACE acceptance; Parallel-safe: no

Lane DAG:

```text
SEMDEVCONTAINER
  -> SL-0 -> SL-1 -> SL-2 -> SEMPUBLISHRACE acceptance
```

## Lanes

### SL-0 - Exact Artifact-Publish Python Boundary And Dispatcher Contract

- **Scope**: Freeze and implement the narrowest lexical repair for
  `tests/test_artifact_publish_race.py` so the live rerun can advance beyond
  that seam without widening Python indexing policy across the test tree.
- **Owned files**: `mcp_server/plugins/python_plugin/plugin.py`, `tests/test_dispatcher.py`
- **Interfaces provided**: IF-0-SEMPUBLISHRACE-1 exact publish-race exit
  contract; IF-0-SEMPUBLISHRACE-2 narrow exact Python boundary contract
- **Interfaces consumed**: existing
  `Plugin._BOUNDED_CHUNK_PATHS`,
  `Plugin._normalized_relative_path(...)`,
  `Plugin._uses_bounded_chunk_path(...)`,
  `Plugin.indexFile(...)`,
  `EnhancedDispatcher.index_directory(...)`,
  and the live blocker evidence for
  `tests/test_benchmarks.py -> tests/test_artifact_publish_race.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` with a repo-shaped fixture for
    `tests/test_artifact_publish_race.py` that proves the current checkout
    does not yet have an exact bounded Python path for that file and freezes
    the chosen narrow repair.
  - test: Require the fixture to preserve Python discoverability for
    `tests/test_artifact_publish_race.py` through stored file content and
    symbol rows while asserting that chunk generation is skipped only for the
    chosen exact path.
  - test: Keep a negative assertion that unrelated files such as
    `tests/test_benchmarks.py` or `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
    do not inherit the new boundary accidentally.
  - impl: Extend the existing bounded Python path mechanism in
    `mcp_server/plugins/python_plugin/plugin.py` with the smallest possible
    repair surface: prefer an exact path entry for
    `tests/test_artifact_publish_race.py` over a broader pattern.
  - impl: Reuse the existing bounded-path contract instead of introducing a
    second Python fast path, new timeout knobs, or repo-wide test-file bypass.
  - impl: Keep dispatcher semantics stable: lexical progress reporting,
    stale-trace handling, and semantic-stage transitions from upstream phases
    should remain unchanged unless the exact bounded Python path requires a
    minimal assertion update in the dispatcher-owned tests only.
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "artifact_publish_race or bounded_python or visual_report"`
  - verify: `rg -n "_BOUNDED_CHUNK_PATHS|artifact_publish_race|create_multi_repo_visual_report" mcp_server/plugins/python_plugin/plugin.py tests/test_dispatcher.py`

### SL-1 - Repository-Status Boundary Surfacing And Rerun Truthfulness

- **Scope**: Carry the exact publish-race repair through the operator-facing
  status surface and prove a live force-full rerun no longer stalls
  indefinitely on the same in-flight seam without truthful boundary reporting.
- **Owned files**: `mcp_server/cli/repository_commands.py`, `tests/test_repository_commands.py`
- **Interfaces provided**: IF-0-SEMPUBLISHRACE-1 exact publish-race exit
  contract; IF-0-SEMPUBLISHRACE-3 operator status contract
- **Interfaces consumed**: SL-0 exact bounded Python decision; existing
  `_print_force_full_exit_trace(...)`,
  `_force_full_trace_is_stale(...)`,
  `_print_visual_report_python_boundary(...)`,
  repository-status lexical-boundary wording, and the live
  `force_full_exit_trace.json` shape recorded by SEMDEVCONTAINER
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_repository_commands.py` so `repository status`
    continues to print the current force-full trace fields and stale-running
    wording while also surfacing the exact bounded Python boundary for
    `tests/test_artifact_publish_race.py` if that file exists.
  - test: Preserve the existing lexical-boundary lines for generated
    fast-test reports, `ai_docs/*_overview.md`, `ai_docs/jedi.md`, and
    `scripts/create_multi_repo_visual_report.py` so this phase is additive and
    does not regress earlier exact seams.
  - test: Freeze a trace payload that still names
    `last_progress_path=/.../tests/test_benchmarks.py` and
    `in_flight_path=/.../tests/test_artifact_publish_race.py` so the status
    surface remains truthful whether the rerun advances, stays running too
    long, or exits with a later bounded blocker.
  - impl: Add the minimal repository-status boundary helper needed for the
    chosen exact path, mirroring the existing exact bounded Python boundary
    pattern instead of inventing a new readiness or rollout state.
  - impl: Keep timeout semantics fail-closed. If the rerun still blocks after
    the exact path repair, report the true downstream blocker rather than
    claiming lexical readiness or semantic progress early.
  - impl: If the live rerun proves no status wording change is necessary
    beyond the exact boundary line, record that no-op outcome in execution
    notes and keep this lane scoped to operator surfacing plus rerun proof.
  - verify: `uv run pytest tests/test_repository_commands.py -q --no-cov -k "artifact_publish_race or bounded Python or stale-running"`
  - verify: `env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - verify: `python - <<'PY'
from pathlib import Path
trace = Path(".mcp-index") / "force_full_exit_trace.json"
print(trace.read_text() if trace.exists() else "missing")
PY`

### SL-2 - Dogfood Evidence Reducer And Live Rerun Refresh

- **Scope**: Refresh the repo-local dogfood report so it records the
  publish-race repair, the live rerun outcome, and the next exact blocker if
  semantic-stage work still does not begin.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: IF-0-SEMPUBLISHRACE-4 evidence contract;
  IF-0-SEMPUBLISHRACE-5 upstream-boundary preservation contract
- **Interfaces consumed**: SL-0 exact bounded Python repair; SL-1 repository
  status wording and live rerun outcome; roadmap SEMPUBLISHRACE exit criteria;
  prior SEMFASTREPORT, SEMPYTESTOVERVIEW, SEMVISUALREPORT, SEMJEDI,
  SEMTRACEFRESHNESS, and SEMDEVCONTAINER evidence lineage
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/docs/test_semdogfood_evidence_contract.py` so the
    refreshed report cites `plans/phase-plan-v7-SEMPUBLISHRACE.md`, the live
    rerun command and timestamps, the exact
    `tests/test_artifact_publish_race.py` boundary, and the next exact blocker
    if semantic-stage work still does not begin.
  - test: Require the report to preserve the older fast-report,
    `ai_docs/*_overview.md`, exact Jedi, exact visual-report, trace-freshness,
    and `.devcontainer` evidence lineage while making clear that the active
    seam is now the artifact-publish-race lexical exit gap.
  - test: Require the report to state whether the rerun advanced into later
    lexical work, reached semantic-stage mutation, or exited with a new exact
    bounded blocker after the publish-race seam.
  - impl: Refresh `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` with the live
    rerun command, observed commit IDs, durable trace contents,
    repository-status output, and the steering verdict after the
    `tests/test_artifact_publish_race.py` seam is repaired or truthfully
    terminalized.
  - impl: Keep the report factual and durable. Record exact timestamps,
    `last_progress_path`, `in_flight_path`, trace `status`, stage family,
    blocker source, and chunk/vector counts without claiming semantic success
    before the evidence exists.
  - impl: If the rerun still does not begin semantic work, name the next exact
    blocker directly and keep SEMPUBLISHRACE itself scoped to the
    `tests/test_artifact_publish_race.py` seam once that seam is no longer the
    active blocker.
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
  - verify: `rg -n "SEMPUBLISHRACE|artifact_publish_race|Trace status|Trace stage|Last progress path|In-flight path|next exact blocker" docs/status/SEMANTIC_DOGFOOD_REBUILD.md tests/docs/test_semdogfood_evidence_contract.py`

## Verification

Planning-only run: do not execute these during plan creation. Run them during
`codex-execute-phase` or manual SEMPUBLISHRACE execution.

Lane-specific checks:

```bash
uv run pytest tests/test_dispatcher.py -q --no-cov -k "artifact_publish_race or bounded_python or visual_report"
uv run pytest tests/test_repository_commands.py -q --no-cov -k "artifact_publish_race or bounded Python or stale-running"
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
rg -n "_BOUNDED_CHUNK_PATHS|artifact_publish_race|create_multi_repo_visual_report" \
  mcp_server/plugins/python_plugin/plugin.py \
  tests/test_dispatcher.py
rg -n "artifact_publish_race|bounded Python|Lexical boundary|Last progress path|In-flight path|stale-running snapshot" \
  mcp_server/cli/repository_commands.py \
  tests/test_repository_commands.py \
  docs/status/SEMANTIC_DOGFOOD_REBUILD.md \
  tests/docs/test_semdogfood_evidence_contract.py
```

Whole-phase regression commands:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest \
  tests/test_dispatcher.py \
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
git status --short -- specs/phase-plans-v7.md plans/phase-plan-v7-SEMPUBLISHRACE.md
```

## Acceptance Criteria

- [ ] A live repo-local force-full rerun no longer remains past the configured
      lexical-timeout window with
      `last_progress_path=/home/viperjuice/code/Code-Index-MCP/tests/test_benchmarks.py`
      and
      `in_flight_path=/home/viperjuice/code/Code-Index-MCP/tests/test_artifact_publish_race.py`
      while the durable trace timestamp stays unchanged.
- [ ] The chosen repair for `tests/test_artifact_publish_race.py` stays exact
      or narrower than that file family, is covered by targeted tests, and
      does not broaden into a repo-wide test or Python bypass.
- [ ] `tests/test_artifact_publish_race.py` remains lexically discoverable
      through stored file content and Python symbol metadata after the repair.
- [ ] `uv run mcp-index repository status` remains aligned with the configured
      timeout window, preserves earlier lexical-boundary wording, and explains
      the exact `tests/test_artifact_publish_race.py` boundary if that repair
      is active.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is refreshed with the
      publish-race repair evidence, the rerun outcome, and the next exact
      blocker if semantic-stage work still does not begin.
- [ ] SEMFASTREPORT, SEMPYTESTOVERVIEW, SEMVISUALREPORT, SEMJEDI,
      SEMTRACEFRESHNESS, and SEMDEVCONTAINER remain closed unless the refreshed
      rerun directly re-anchors on one of those exact seams.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v7-SEMPUBLISHRACE.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMPUBLISHRACE.md
  artifact_state: staged
```
