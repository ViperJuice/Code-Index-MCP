---
phase_loop_plan_version: 1
phase: SEMVISUALREPORT
roadmap: specs/phase-plans-v7.md
roadmap_sha256: da74c52bba9561b7e83894f8a01a2f4e4404c301fb9695a2051eeaa99dc922c3
---
# SEMVISUALREPORT: Visual Report Script Lexical Recovery

## Context

SEMVISUALREPORT is the phase-28 follow-up for the v7 semantic hardening
roadmap. SEMPYTESTOVERVIEW proved that the bounded
`ai_docs/*_overview.md` repair cleared `ai_docs/pytest_overview.md`, but the
live repo-local force-full rerun still remained in lexical walking on
`scripts/create_multi_repo_visual_report.py`.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is tracked and clean in this worktree, and its
  live SHA matches the required
  `da74c52bba9561b7e83894f8a01a2f4e4404c301fb9695a2051eeaa99dc922c3`.
- The checkout is on `main` at `b88a078353febe842464347eba295a8f1d181812`,
  `main...origin/main` is ahead by `51` commits, the worktree is clean before
  writing this artifact, and `plans/phase-plan-v7-SEMVISUALREPORT.md` did not
  exist before this run.
- `.phase-loop/state.json` and `.phase-loop/tui-handoff.md` already mark
  `SEMVISUALREPORT` as the current unplanned phase on the same roadmap SHA,
  and the latest closeout summary records `SEMPYTESTOVERVIEW` complete on the
  current `HEAD`. This artifact is therefore the active next-phase handoff,
  not a speculative side plan.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is the live blocker artifact for
  this phase. Its latest SEMPYTESTOVERVIEW evidence snapshot
  (`2026-04-29T07:49:50Z`, observed commit `6be33712`) records that a fresh
  repo-local `repository sync --force-full` advanced beyond
  `ai_docs/pytest_overview.md`, persisted a durable
  `force_full_exit_trace.json` with `stage=lexical_walking`, and moved the
  most recent durable lexical progress marker to
  `/home/viperjuice/code/Code-Index-MCP/scripts/create_multi_repo_visual_report.py`.
- The same evidence shows the rerun still exited with code `135` before a
  newer durable snapshot was written, leaving `chunk_summaries = 0` and
  `semantic_points = 0`. The repository query surface therefore remains
  `index_unavailable` because semantic closeout never begins.
- `scripts/create_multi_repo_visual_report.py` is a tracked Python source file
  (`666` lines, about `28K`) with nine top-level functions including
  `main()`. This is not an oversized source outlier, so the remaining seam is
  more likely a path-specific Python lexical/chunking issue than a generic
  large-file cutoff.
- `mcp_server/plugins/python_plugin/plugin.py` currently parses Python files
  with Tree-sitter, extracts top-level classes and functions, and then always
  attempts `chunk_text(content, "python")` before storing chunks. There is no
  existing script-specific bounded path, ignore rule, or watchdog-aware fast
  path for `scripts/create_multi_repo_visual_report.py`.
- `SQLiteStore.rebuild_fts_code()` already rebuilds lexical FTS from `files`
  table content rather than from `code_chunks`. That means SEMVISUALREPORT can
  consider a bounded chunking or symbol-handling repair for this exact script
  while still preserving lexical file-content search, as long as the file row
  continues to be stored.
- `repository status` already surfaces the explicit fast-test report boundary
  from SEMFASTREPORT and the explicit `ai_docs/*_overview.md` bounded Markdown
  path from SEMPYTESTOVERVIEW. This phase must not regress or reopen either of
  those narrower upstream contracts.

Practical planning boundary:

- SEMVISUALREPORT may introduce one exact repair for
  `scripts/create_multi_repo_visual_report.py`: a bounded Python indexing path
  in the plugin layer, a minimal script-local source simplification that keeps
  the same operational behavior, or the smallest combination needed to carry
  the live force-full rerun beyond this seam.
- SEMVISUALREPORT must keep the repair narrow and evidence-driven. It must not
  introduce a broad `scripts/*.py` ignore rule, a repo-wide Python fast path,
  a global lexical timeout increase, or unrelated semantic/ranking/release
  work.

## Interface Freeze Gates

- [ ] IF-0-SEMVISUALREPORT-1 - Exact visual-report blocker contract:
      repo-local `repository sync --force-full` no longer leaves the durable
      lexical trace on `scripts/create_multi_repo_visual_report.py`, and the
      repair is explicitly tied to that script or a stricter file class it
      belongs to.
- [ ] IF-0-SEMVISUALREPORT-2 - Bounded Python handling contract:
      the chosen repair preserves lexical discoverability for
      `scripts/create_multi_repo_visual_report.py` through stored file content
      and preserves at least the top-level symbol surface the repo needs for
      that script; it does not introduce a broad `scripts/*.py`, `*.py`, or
      repository-wide ignore or fast-path bypass.
- [ ] IF-0-SEMVISUALREPORT-3 - Watchdog preservation contract:
      the lexical timeout watchdog remains active and still fails closed for
      genuine stalled Python files that are not fixed by the exact
      visual-report repair, including synthetic dispatcher or git-index-manager
      timeout fixtures.
- [ ] IF-0-SEMVISUALREPORT-4 - Force-full downstream handoff contract:
      after the repair, a repo-local force-full rerun advances beyond
      `scripts/create_multi_repo_visual_report.py` and either reaches a later
      lexical or semantic stage or names a new exact downstream blocker that
      is narrower than the current visual-report script seam.
- [ ] IF-0-SEMVISUALREPORT-5 - Status and evidence contract:
      `uv run mcp-index repository status` and
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` record the chosen
      visual-report repair, the rerun command/outcome, the refreshed durable
      trace, and whether semantic-stage work finally begins or a still
      narrower downstream blocker remains.
- [ ] IF-0-SEMVISUALREPORT-6 - Upstream-boundary preservation contract:
      SEMFASTREPORT's `fast_test_results/fast_report_*.md` boundary and
      SEMPYTESTOVERVIEW's `ai_docs/*_overview.md` bounded path remain intact
      and are not reopened unless the rerun produces new direct evidence.

## Lane Index & Dependencies

- SL-0 - Visual-report Python timeout contract and fixture freeze; Depends on: SEMPYTESTOVERVIEW; Blocks: SL-1, SL-2, SL-3; Parallel-safe: no
- SL-1 - Exact visual-report script repair at plugin or source layer; Depends on: SL-0; Blocks: SL-2, SL-3; Parallel-safe: no
- SL-2 - Force-full lexical handoff and repository-status clarity; Depends on: SL-0, SL-1; Blocks: SL-3; Parallel-safe: no
- SL-3 - Dogfood evidence reducer and rerun refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SEMVISUALREPORT acceptance; Parallel-safe: no

Lane DAG:

```text
SEMPYTESTOVERVIEW
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SEMVISUALREPORT acceptance
```

## Lanes

### SL-0 - Visual-Report Python Timeout Contract And Fixture Freeze

- **Scope**: Freeze the exact `scripts/create_multi_repo_visual_report.py`
  lexical seam before implementation so this phase proves a bounded
  Python-path repair instead of only moving the live timeout somewhere less
  visible.
- **Owned files**: `tests/test_dispatcher.py`, `tests/test_git_index_manager.py`, `tests/test_python_plugin.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMVISUALREPORT-1 through IF-0-SEMVISUALREPORT-4
- **Interfaces consumed**: existing
  `EnhancedDispatcher.index_directory(...)`,
  `Dispatcher._index_file_with_lexical_timeout(...)`,
  `GitAwareIndexManager._full_index(...)`,
  `GitAwareIndexManager.sync_repository_index(...)`,
  `Plugin.indexFile(...)` in `mcp_server/plugins/python_plugin/plugin.py`,
  `SQLiteStore.rebuild_fts_code()`, and the tracked
  `scripts/create_multi_repo_visual_report.py` file shape from the current
  checkout
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` with a deterministic
    visual-report-script fixture that freezes the current seam on
    `scripts/create_multi_repo_visual_report.py` and proves the repaired path
    finishes lexical indexing for that file without suppressing the watchdog
    for unrelated Python files.
  - test: Extend `tests/test_git_index_manager.py` so a force-full rerun
    proves the durable trace no longer reports
    `scripts/create_multi_repo_visual_report.py` as the last lexical blocker
    after the repair while still refusing to advance the indexed commit for a
    genuine downstream blocker.
  - test: Extend `tests/test_python_plugin.py` so the chosen exact repair
    preserves the stored-file and top-level-symbol contract for the
    visual-report script even if chunking or other heavyweight work is
    reduced.
  - impl: Keep fixtures deterministic with monkeypatched plugin or dispatcher
    behavior and repo-local script-shaped content rather than long live waits
    inside unit coverage.
  - impl: Keep this lane focused on contract freeze. Do not update live
    dogfood evidence or rerun the force-full command here.
  - verify: `uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_python_plugin.py -q --no-cov`

### SL-1 - Exact Visual-Report Script Repair At Plugin Or Source Layer

- **Scope**: Implement one exact recovery for
  `scripts/create_multi_repo_visual_report.py` so lexical indexing can finish
  under the live watchdog without weakening the repo-wide Python indexing
  posture.
- **Owned files**: `mcp_server/plugins/python_plugin/plugin.py`, `scripts/create_multi_repo_visual_report.py`
- **Interfaces provided**: IF-0-SEMVISUALREPORT-1 exact visual-report blocker
  contract; IF-0-SEMVISUALREPORT-2 bounded Python handling contract
- **Interfaces consumed**: SL-0 Python timeout tests; existing Tree-sitter
  parse flow, top-level symbol extraction, unconditional `chunk_text(...)`
  path in `Plugin.indexFile(...)`, and the current operational behavior of
  `scripts/create_multi_repo_visual_report.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 Python slice first and confirm the current
    visual-report fixture still takes the standard Python indexing path that
    leaves this script as the last durable lexical progress marker.
  - impl: Choose one singular repair surface and keep it explicit: either add
    an exact bounded Python path for
    `scripts/create_multi_repo_visual_report.py` inside the plugin layer, or
    make the smallest script-local source simplification that lets the normal
    Python indexing path complete under the existing watchdog.
  - impl: Preserve stored file rows and top-level function discoverability for
    `scripts/create_multi_repo_visual_report.py`; the repair must not turn the
    script into an ignored source file or silently remove it from lexical FTS.
  - impl: Keep the repair exact-file or exact-file-class narrow. Do not add a
    broad `scripts/*.py`, `*.py`, or repository-wide chunking bypass.
  - impl: If a script-local edit is chosen, keep report-generation behavior
    and output paths stable. This phase is about lexical recoverability, not a
    product redesign of benchmark reporting.
  - verify: `uv run pytest tests/test_python_plugin.py -q --no-cov`

### SL-2 - Force-Full Lexical Handoff And Repository-Status Clarity

- **Scope**: Carry the chosen visual-report repair through force-full closeout
  and keep the operator-facing status surface aligned with the exact repair
  that was made.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `mcp_server/storage/git_index_manager.py`, `mcp_server/cli/repository_commands.py`, `tests/test_repository_commands.py`
- **Interfaces provided**: IF-0-SEMVISUALREPORT-3 watchdog preservation
  contract; IF-0-SEMVISUALREPORT-4 force-full downstream handoff contract;
  IF-0-SEMVISUALREPORT-5 repository-status clarity contract
- **Interfaces consumed**: SL-0 dispatcher and git-index-manager fixtures;
  SL-1 chosen visual-report repair; existing lexical progress snapshot fields,
  durable `force_full_exit_trace.json` persistence, and the current
  SEMFASTREPORT / SEMPYTESTOVERVIEW status wording for earlier boundaries
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_repository_commands.py` so `repository status`
    continues to render the durable force-full trace and any existing
    fast-report or overview-doc boundary wording while explaining the chosen
    visual-report-script repair narrowly.
  - impl: Thread the chosen repair through the dispatcher and git-index-manager
    only as needed so the rerun can advance beyond
    `scripts/create_multi_repo_visual_report.py`.
  - impl: Preserve the existing lexical trace vocabulary and fail-closed
    indexed-commit behavior. This lane should move the handoff forward, not
    rename stages or declare readiness early.
  - impl: Tighten `repository status` only as needed so operators can tell
    whether the visual-report script now uses an exact bounded Python path,
    completed normally, or exposed a new exact downstream blocker.
  - impl: If SL-1 alone is sufficient and no runtime code change is required,
    record that no-op outcome in execution notes and keep this lane scoped to
    status wording plus live rerun proof.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_repository_commands.py -q --no-cov`
  - verify: `env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - verify: `python - <<'PY'
from pathlib import Path
print((Path(".mcp-index") / "force_full_exit_trace.json").read_text())
PY`

### SL-3 - Dogfood Evidence Reducer And Rerun Refresh

- **Scope**: Refresh the repo-local dogfood report so it records the chosen
  visual-report repair, the rerun outcome, and the next exact downstream
  status after this Python seam is cleared.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: IF-0-SEMVISUALREPORT-5 status and evidence
  contract; IF-0-SEMVISUALREPORT-6 upstream-boundary preservation contract
- **Interfaces consumed**: SL-1 chosen visual-report repair; SL-2 rerun
  command, durable trace, and repository-status wording; roadmap
  SEMVISUALREPORT exit criteria; prior SEMFASTREPORT and SEMPYTESTOVERVIEW
  evidence lineage
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/docs/test_semdogfood_evidence_contract.py` so the
    refreshed report cites `plans/phase-plan-v7-SEMVISUALREPORT.md`, the
    chosen `scripts/create_multi_repo_visual_report.py` repair, the rerun
    outcome, and whether the repo advanced beyond lexical walking or exposed a
    new exact downstream blocker.
  - test: Require the report to preserve the existing fast-test report and
    `ai_docs/*_overview.md` evidence lineage while making clear that neither
    upstream seam is the active blocker anymore.
  - impl: Refresh `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` with the new live
    rerun evidence, force-full trace details, SQLite summary/vector counts,
    and the current verdict on whether semantic-stage work can now begin.
  - impl: If the rerun exposes a new exact downstream blocker instead of
    semantic advancement, name that blocker directly and keep roadmap steering
    explicit rather than reverting to a generic retry narrative.
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
  - verify: `sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'`
  - verify: `rg -n "SEMVISUALREPORT|create_multi_repo_visual_report|force_full_exit_trace|Trace stage|Trace stage family|Last progress path|Dogfood Verdict" docs/status/SEMANTIC_DOGFOOD_REBUILD.md tests/docs/test_semdogfood_evidence_contract.py`

## Verification

Planning-only run: do not execute these during plan creation. Run them during
`codex-execute-phase` or manual SEMVISUALREPORT execution.

Lane-specific checks:

```bash
uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_python_plugin.py -q --no-cov
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_repository_commands.py -q --no-cov
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
python - <<'PY'
from pathlib import Path
print((Path(".mcp-index") / "force_full_exit_trace.json").read_text())
PY
sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'
```

Whole-phase regression commands:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest \
  tests/test_dispatcher.py \
  tests/test_git_index_manager.py \
  tests/test_python_plugin.py \
  tests/test_repository_commands.py \
  tests/docs/test_semdogfood_evidence_contract.py \
  -q --no-cov
env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
git status --short -- specs/phase-plans-v7.md plans/phase-plan-v7-SEMVISUALREPORT.md docs/status/SEMANTIC_DOGFOOD_REBUILD.md
```

## Acceptance Criteria

- [ ] A live repo-local force-full rerun no longer leaves the durable lexical
      trace in `lexical_walking` with
      `scripts/create_multi_repo_visual_report.py` as the last progress
      marker.
- [ ] The chosen repair for
      `scripts/create_multi_repo_visual_report.py` is explicit, narrow, and
      preserves lexical discoverability for that script without introducing a
      broad Python or `scripts/`-wide bypass.
- [ ] The lexical timeout watchdog still fails closed for genuine non-visual-
      report Python stalls after the repair.
- [ ] `repository status` remains aligned with the durable trace and explains
      any exact visual-report-script recovery without inventing new readiness
      states.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is refreshed with the
      visual-report rerun outcome and either semantic-stage advancement or a
      still narrower downstream blocker.
- [ ] SEMFASTREPORT's explicit `fast_test_results/fast_report_*.md` boundary
      and SEMPYTESTOVERVIEW's explicit `ai_docs/*_overview.md` boundary remain
      intact and are not reopened by this phase.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v7-SEMVISUALREPORT.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMVISUALREPORT.md
  artifact_state: staged
```
