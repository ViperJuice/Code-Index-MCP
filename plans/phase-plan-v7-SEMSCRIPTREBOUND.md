---
phase_loop_plan_version: 1
phase: SEMSCRIPTREBOUND
roadmap: specs/phase-plans-v7.md
roadmap_sha256: 06d6346c00207ca639722c240f6a3900f6ba5ed2125eee0016ce12b7cb429e42
---
# SEMSCRIPTREBOUND: Script Rebound Lexical Re-Anchor Recovery

## Context

SEMSCRIPTREBOUND is the phase-34 follow-up for the v7 semantic hardening
roadmap. SEMDEVREBOUND proved the live repo-local `repository sync --force-full`
rerun no longer remains on `.devcontainer/devcontainer.json`, but the same
rerun later re-anchored on the next exact lexical seam:
`scripts/quick_mcp_vs_native_validation.py`.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is the active roadmap, it is tracked and clean in
  this worktree, and `sha256sum specs/phase-plans-v7.md` matches the required
  `06d6346c00207ca639722c240f6a3900f6ba5ed2125eee0016ce12b7cb429e42`.
- Canonical phase-loop state exists under `.phase-loop/`; `.phase-loop/state.json`
  and `.phase-loop/tui-handoff.md` both mark `SEMSCRIPTREBOUND` as the current
  `unplanned` phase on the same roadmap SHA, with `SEMDEVREBOUND` complete, a
  clean worktree before this plan write, and `HEAD`
  `9f9b7f57efc8a73fc77a9aebc0733f09fbfaddca` on `main...origin/main [ahead 63]`.
- The target artifact `plans/phase-plan-v7-SEMSCRIPTREBOUND.md` did not exist
  before this planning run.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is the active dogfood evidence
  anchor. Its latest SEMDEVREBOUND snapshot (`2026-04-29T09:52:03Z`, observed
  commit `4c28493a`) records that the refreshed live rerun advanced beyond the
  earlier `.devcontainer/devcontainer.json` blocker and later re-anchored on
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/scripts/rerun_failed_native_tests.py`
  with
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/scripts/quick_mcp_vs_native_validation.py`.
- By `2026-04-29T09:52:03Z`, the durable trace was still frozen on that exact
  script pair, `repository status` later reported `Trace freshness:
  stale-running snapshot`, and the partial runtime still ended with
  `chunk_summaries = 0` and `semantic_points = 0`.
- The renewed blocker files are small and Python-shaped rather than a broad
  large-file outlier:
  `scripts/quick_mcp_vs_native_validation.py` is `2971` bytes and
  `scripts/rerun_failed_native_tests.py` is `5703` bytes. The rebound is
  therefore more likely an exact Python indexing-path or lexical-closeout
  defect than a generic throughput problem.
- `mcp_server/plugins/python_plugin/plugin.py` is the live lexical path for
  `.py` files. Its `_BOUNDED_CHUNK_PATHS` currently includes only
  `scripts/create_multi_repo_visual_report.py` and
  `tests/test_artifact_publish_race.py`; it does not yet carry an exact
  bounded path for `scripts/quick_mcp_vs_native_validation.py`.
- `tests/test_dispatcher.py` already freezes exact bounded Python coverage for
  `scripts/create_multi_repo_visual_report.py` and
  `tests/test_artifact_publish_race.py`, plus exact bounded JSON coverage for
  `.devcontainer/devcontainer.json`. This phase should extend that exact-path
  pattern rather than inventing a new lexical workaround family.
- `mcp_server/cli/repository_commands.py` currently prints explicit lexical
  boundary lines for generated fast-test reports, `ai_docs/*_overview.md`,
  `ai_docs/jedi.md`, `scripts/create_multi_repo_visual_report.py`,
  `tests/test_artifact_publish_race.py`, and `.devcontainer/devcontainer.json`,
  but it has no explicit operator line yet for the renewed
  `scripts/quick_mcp_vs_native_validation.py` seam.
- `tests/test_repository_commands.py` and
  `tests/docs/test_semdogfood_evidence_contract.py` already name the renewed
  script-pair blocker shape in the current repo, so this phase must preserve
  that evidence lineage while moving the active seam forward.

Practical planning boundary:

- SEMSCRIPTREBOUND may introduce the smallest exact recovery needed for the
  renewed `scripts/quick_mcp_vs_native_validation.py` seam: an exact bounded
  Python indexing path, the smallest dispatcher-side lexical closeout repair
  needed to make timeout truthfully terminal for this file family, or the
  smallest combination needed to carry the live rerun past the renewed script
  re-anchor.
- SEMSCRIPTREBOUND must stay narrow and evidence-driven. It must not reopen
  `.devcontainer/devcontainer.json`, `tests/test_artifact_publish_race.py`,
  `ai_docs/jedi.md`, `ai_docs/*_overview.md`, generated fast-test report,
  visual-report-script, or summary/vector phases unless a refreshed rerun
  directly re-anchors there again.

## Interface Freeze Gates

- [ ] IF-0-SEMSCRIPTREBOUND-1 - Exact rebound trace contract:
      after the rerun has already advanced beyond
      `.devcontainer/devcontainer.json`, a live repo-local
      `repository sync --force-full` no longer remains past the configured
      lexical-timeout window with
      `last_progress_path=/home/viperjuice/code/Code-Index-MCP/scripts/rerun_failed_native_tests.py`
      and
      `in_flight_path=/home/viperjuice/code/Code-Index-MCP/scripts/quick_mcp_vs_native_validation.py`
      while the durable trace timestamp stays unchanged.
- [ ] IF-0-SEMSCRIPTREBOUND-2 - Exact bounded recovery contract:
      if this phase introduces a path-specific Python recovery, it stays
      limited to `scripts/quick_mcp_vs_native_validation.py` or a stricter
      exact alias, preserves operator-visible indexing of that file, and does
      not broaden into arbitrary `scripts/*.py`, all Python files, or the
      whole `scripts/` directory.
- [ ] IF-0-SEMSCRIPTREBOUND-3 - Truthful lexical closeout contract:
      if the live rerun still cannot progress past the renewed script seam,
      the durable trace and dispatcher stats exit with a bounded lexical
      blocker or timeout verdict that still names that exact script pair
      truthfully instead of leaving a stale `status=running` snapshot behind.
- [ ] IF-0-SEMSCRIPTREBOUND-4 - Operator status contract:
      `uv run mcp-index repository status` remains aligned with the configured
      timeout window, preserves the existing exact bounded wording for
      `scripts/create_multi_repo_visual_report.py`,
      `tests/test_artifact_publish_race.py`, and
      `.devcontainer/devcontainer.json`, and adds any new
      `scripts/quick_mcp_vs_native_validation.py` boundary line only if the
      implementation actually introduces that exact recovery path.
- [ ] IF-0-SEMSCRIPTREBOUND-5 - Evidence contract:
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the script rebound
      repair, the live rerun command and outcome, the durable trace
      timestamps and paths, and whether the rerun advances into later lexical
      or semantic work or exits with a new narrower blocker.
- [ ] IF-0-SEMSCRIPTREBOUND-6 - Upstream-boundary preservation contract:
      SEMDEVREBOUND, SEMPUBLISHRACE, SEMFASTREPORT, SEMPYTESTOVERVIEW,
      SEMVISUALREPORT, SEMJEDI, and SEMTRACEFRESHNESS remain closed unless the
      refreshed rerun directly re-anchors on one of those exact seams again.

## Lane Index & Dependencies

- SL-0 - Renewed script rebound contract and fixture freeze; Depends on: SEMDEVREBOUND; Blocks: SL-1, SL-2, SL-3; Parallel-safe: no
- SL-1 - Exact script rebound repair; Depends on: SL-0; Blocks: SL-2, SL-3; Parallel-safe: no
- SL-2 - Repository-status boundary alignment and blocker truthfulness; Depends on: SL-0, SL-1; Blocks: SL-3; Parallel-safe: no
- SL-3 - Dogfood evidence reducer and rerun refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SEMSCRIPTREBOUND acceptance; Parallel-safe: no

Lane DAG:

```text
SEMDEVREBOUND
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SEMSCRIPTREBOUND acceptance
```

## Lanes

### SL-0 - Renewed Script Rebound Contract And Fixture Freeze

- **Scope**: Freeze the renewed
  `scripts/rerun_failed_native_tests.py -> scripts/quick_mcp_vs_native_validation.py`
  rebound shape in dispatcher and status coverage so this phase proves an
  exact recovery after the `.devcontainer` seam was cleared instead of only
  shifting the stale running trace elsewhere.
- **Owned files**: `tests/test_dispatcher.py`, `tests/test_repository_commands.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMSCRIPTREBOUND-1 through IF-0-SEMSCRIPTREBOUND-4
- **Interfaces consumed**: existing
  `EnhancedDispatcher.index_directory(...)`,
  `EnhancedDispatcher._index_file_with_lexical_timeout(...)`,
  `_run_blocking_with_timeout(...)`,
  the current exact bounded Python seams for
  `scripts/create_multi_repo_visual_report.py` and
  `tests/test_artifact_publish_race.py`,
  the current exact bounded JSON seam for
  `.devcontainer/devcontainer.json`, and the renewed script-pair blocker
  vocabulary from `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` with a repo-shaped rebound fixture
    that freezes the current exact script seam after a prior lexical step has
    already advanced beyond `.devcontainer/devcontainer.json`.
  - test: Require the rebound fixture to prove the repaired path either
    completes lexical indexing for `scripts/quick_mcp_vs_native_validation.py`
    or returns a bounded lexical timeout/error instead of leaving the durable
    trace parked as a stale `status=running` snapshot.
  - test: Keep the fixture exact. Use repo-local
    `scripts/rerun_failed_native_tests.py` and
    `scripts/quick_mcp_vs_native_validation.py` inputs rather than broad
    `scripts/*.py` fixtures so the contract stays tied to the live rebound
    evidence.
  - test: Extend `tests/test_repository_commands.py` so `repository status`
    freezes the renewed script-pair trace while preserving the existing exact
    bounded lines for `scripts/create_multi_repo_visual_report.py`,
    `tests/test_artifact_publish_race.py`, and
    `.devcontainer/devcontainer.json`.
  - test: Keep negative assertions that unrelated Python scripts do not
    inherit a new exact script policy accidentally.
  - impl: Use monkeypatched chunker or dispatcher behavior and synthetic
    durable-trace payloads rather than multi-minute live waits inside unit
    coverage.
  - impl: Keep this lane focused on contract freeze only. Do not update the
    operator evidence artifact or run the real force-full command here.
  - verify: `uv run pytest tests/test_dispatcher.py tests/test_repository_commands.py -q --no-cov -k "script or lexical or timeout or devcontainer or artifact_publish_race"`

### SL-1 - Exact Script Rebound Repair

- **Scope**: Implement the smallest exact recovery needed so the renewed
  `scripts/quick_mcp_vs_native_validation.py` seam no longer leaves the live
  force-full rerun parked past the configured lexical-timeout window after
  `.devcontainer/devcontainer.json` has already been cleared.
- **Owned files**: `mcp_server/plugins/python_plugin/plugin.py`, `mcp_server/dispatcher/dispatcher_enhanced.py`
- **Interfaces provided**: IF-0-SEMSCRIPTREBOUND-1 exact rebound trace
  contract; IF-0-SEMSCRIPTREBOUND-2 exact bounded recovery contract;
  IF-0-SEMSCRIPTREBOUND-3 truthful lexical closeout contract
- **Interfaces consumed**: SL-0 rebound fixtures; the Python plugin's
  `_BOUNDED_CHUNK_PATHS`; dispatcher lexical timeout handling; existing
  `last_progress_path` / `in_flight_path` accounting; and the live rebound
  evidence for
  `scripts/rerun_failed_native_tests.py -> scripts/quick_mcp_vs_native_validation.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 dispatcher slice first and confirm the current
    checkout still has no exact bounded
    `scripts/quick_mcp_vs_native_validation.py` recovery or truthful terminal
    closeout under the frozen rebound fixture.
  - impl: Prefer the smallest exact repair that matches the live evidence. If
    the Python chunking path is the root cause, add an exact normalized-path
    helper for `scripts/quick_mcp_vs_native_validation.py` or a stricter
    alias rather than a broad `scripts/*.py` or general Python bypass.
  - impl: If the live evidence shows the real defect is lexical-timeout
    closeout rather than Python chunking itself, keep the fix local to
    dispatcher terminalization and do not add a speculative bounded-path
    exemption.
  - impl: Preserve operator-visible indexing for the renewed script seam. Do
    not solve the stall by silently dropping the file from storage, progress
    reporting, or the repository-status trace.
  - impl: Preserve the existing exact bounded Python seams for
    `scripts/create_multi_repo_visual_report.py` and
    `tests/test_artifact_publish_race.py`, plus the exact bounded JSON seam
    for `.devcontainer/devcontainer.json`. Do not reopen those earlier phases
    unless the refreshed live rerun directly re-anchors there again.
  - impl: Do not broaden to all Python files, all `scripts/*.py` files, or a
    repo-wide timeout retune. Any allowlist or fast path must stay specific
    to the renewed rebound seam and be documented by code shape and tests.
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "script or lexical or timeout"`
  - verify: `rg -n "quick_mcp_vs_native_validation|rerun_failed_native_tests|_BOUNDED_CHUNK_PATHS|in_flight_path|last_progress_path" mcp_server/plugins/python_plugin/plugin.py mcp_server/dispatcher/dispatcher_enhanced.py tests/test_dispatcher.py`

### SL-2 - Repository-Status Boundary Alignment And Blocker Truthfulness

- **Scope**: Keep the operator-facing status surface aligned with the renewed
  script repair and the true live or terminal state of the rerun.
- **Owned files**: `mcp_server/cli/repository_commands.py`
- **Interfaces provided**: IF-0-SEMSCRIPTREBOUND-4 operator status contract
- **Interfaces consumed**: SL-0 repository-status fixtures; SL-1 exact repair
  choice; existing boundary helpers for fast-test reports,
  `ai_docs/*_overview.md`, `ai_docs/jedi.md`,
  `scripts/create_multi_repo_visual_report.py`,
  `tests/test_artifact_publish_race.py`, and
  `.devcontainer/devcontainer.json`; plus the current durable stale-running
  trace rendering
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 repository-status slice first and confirm the renewed
    script-pair trace is rendered truthfully while the older bounded seam
    lines stay intact.
  - impl: If SL-1 introduces an exact
    `scripts/quick_mcp_vs_native_validation.py` bounded path, add the
    matching minimal repository-status boundary helper so operators can see
    that this rebound seam is intentional and exact.
  - impl: If SL-1 solves the issue entirely in timeout closeout without an
    exact bounded path, keep this lane limited to truthful blocker/freshness
    rendering and do not add misleading script-boundary copy.
  - impl: Keep timeout semantics fail-closed and preserve the existing
    publish-race, visual-report, and `.devcontainer` boundary wording; if the
    live rerun still blocks after the repair, report the true downstream
    blocker rather than claiming lexical or semantic readiness early.
  - verify: `uv run pytest tests/test_repository_commands.py -q --no-cov -k "script or force_full or boundary or stale-running"`
  - verify: `rg -n "quick_mcp_vs_native_validation|rerun_failed_native_tests|create_multi_repo_visual_report|artifact_publish_race|devcontainer.json|Lexical boundary|Trace freshness|Last progress path|In-flight path" mcp_server/cli/repository_commands.py tests/test_repository_commands.py`

### SL-3 - Dogfood Evidence Reducer And Rerun Refresh

- **Scope**: Refresh the repo-local dogfood report so it records the script
  rebound repair, the live rerun outcome, and the next exact blocker if
  semantic-stage work still does not begin.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: IF-0-SEMSCRIPTREBOUND-5 evidence contract;
  IF-0-SEMSCRIPTREBOUND-6 upstream-boundary preservation contract
- **Interfaces consumed**: SL-1 exact rebound repair; SL-2 repository-status
  wording; roadmap SEMSCRIPTREBOUND exit criteria; prior SEMTRACEFRESHNESS,
  SEMPUBLISHRACE, and SEMDEVREBOUND evidence lineage; and the older fast-test,
  `ai_docs/*_overview.md`, exact Jedi, visual-report, publish-race, and
  `.devcontainer` boundary history
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/docs/test_semdogfood_evidence_contract.py` so the
    refreshed report cites `plans/phase-plan-v7-SEMSCRIPTREBOUND.md`, the
    live rerun command and timestamps, the renewed
    `scripts/rerun_failed_native_tests.py` plus
    `scripts/quick_mcp_vs_native_validation.py` trace pair, and the next
    exact blocker if semantic-stage work still does not begin.
  - test: Require the report to preserve the older trace-freshness,
    publish-race, and `.devcontainer` lineage while making clear that the
    active seam is now the renewed exact Python script re-anchor.
  - test: Require the report to say whether the rerun advanced into later
    lexical work, reached semantic closeout, or exited with a new narrower
    bounded blocker after the script rebound repair.
  - impl: Refresh `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` with the live
    rerun command, observed commit IDs, durable trace contents,
    repository-status output, and the steering verdict after the renewed
    script seam is repaired or truthfully terminalized.
  - impl: Keep the report factual and durable. Record exact timestamps,
    `last_progress_path`, `in_flight_path`, trace `status`, stage family,
    blocker source, and chunk/vector counts without claiming semantic success
    before the evidence exists.
  - impl: If the rerun still does not begin semantic work, name the next exact
    blocker directly and keep SEMSCRIPTREBOUND itself scoped to the renewed
    `scripts/quick_mcp_vs_native_validation.py` seam once that seam is no
    longer a stale-running trace.
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
  - verify: `rg -n "SEMSCRIPTREBOUND|quick_mcp_vs_native_validation|rerun_failed_native_tests|Trace status|Trace stage|Last progress path|In-flight path|next exact blocker" docs/status/SEMANTIC_DOGFOOD_REBUILD.md tests/docs/test_semdogfood_evidence_contract.py`

## Verification

Planning-only run: do not execute these during plan creation. Run them during
`codex-execute-phase` or manual SEMSCRIPTREBOUND execution.

Lane-specific checks:

```bash
uv run pytest tests/test_dispatcher.py tests/test_repository_commands.py -q --no-cov -k "script or lexical or timeout or devcontainer or artifact_publish_race"
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
rg -n "quick_mcp_vs_native_validation|rerun_failed_native_tests|create_multi_repo_visual_report|artifact_publish_race|devcontainer.json|Lexical boundary|Trace freshness|Last progress path|In-flight path|SEMSCRIPTREBOUND" \
  mcp_server/plugins/python_plugin/plugin.py \
  mcp_server/dispatcher/dispatcher_enhanced.py \
  mcp_server/cli/repository_commands.py \
  docs/status/SEMANTIC_DOGFOOD_REBUILD.md \
  tests/test_dispatcher.py \
  tests/test_repository_commands.py \
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
git status --short -- specs/phase-plans-v7.md plans/phase-plan-v7-SEMSCRIPTREBOUND.md
```

## Acceptance Criteria

- [ ] A live repo-local force-full rerun no longer remains past the configured
      lexical-timeout window with
      `last_progress_path=/home/viperjuice/code/Code-Index-MCP/scripts/rerun_failed_native_tests.py`
      and
      `in_flight_path=/home/viperjuice/code/Code-Index-MCP/scripts/quick_mcp_vs_native_validation.py`
      once the rerun has already advanced beyond
      `.devcontainer/devcontainer.json`.
- [ ] The chosen repair for the renewed
      `scripts/quick_mcp_vs_native_validation.py` seam stays exact or narrower
      than that file family, is covered by targeted tests, and does not
      broaden into a repo-wide Python or `scripts/` bypass.
- [ ] The rerun either completes the renewed
      `scripts/quick_mcp_vs_native_validation.py` lexical seam and advances
      into later lexical or semantic work, or exits with a bounded lexical
      blocker that still names that exact script pair truthfully.
- [ ] `uv run mcp-index repository status` remains aligned with the configured
      timeout window, preserves the existing exact bounded
      `scripts/create_multi_repo_visual_report.py`,
      `tests/test_artifact_publish_race.py`, and
      `.devcontainer/devcontainer.json` wording, and adds script-boundary copy
      only if that exact repair is active.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is refreshed with the script
      rebound repair evidence, the rerun outcome, and the next exact blocker
      if semantic-stage work still does not begin.
- [ ] SEMDEVREBOUND, SEMPUBLISHRACE, SEMFASTREPORT, SEMPYTESTOVERVIEW,
      SEMVISUALREPORT, SEMJEDI, and SEMTRACEFRESHNESS remain closed unless the
      refreshed rerun directly re-anchors on one of those exact seams again.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v7-SEMSCRIPTREBOUND.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMSCRIPTREBOUND.md
  artifact_state: staged
```
