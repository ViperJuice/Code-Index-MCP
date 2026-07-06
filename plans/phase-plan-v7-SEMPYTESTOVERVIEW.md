---
phase_loop_plan_version: 1
phase: SEMPYTESTOVERVIEW
roadmap: specs/phase-plans-v7.md
roadmap_sha256: ef93f63195ac8b5c9e38a77f1a1768f71423161f0daa6b33fbd72f0cbb787a06
---
# SEMPYTESTOVERVIEW: Pytest Overview Lexical Recovery

## Context

SEMPYTESTOVERVIEW is the phase-27 follow-up for the v7 semantic hardening
roadmap. SEMFASTREPORT proved that the generated
`fast_test_results/fast_report_*.md` family is no longer the active lexical
blocker for a repo-local `repository sync --force-full`, but the live rerun
still remained in lexical walking on `ai_docs/pytest_overview.md`.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is tracked and clean in this worktree, and its
  live SHA matches the required
  `ef93f63195ac8b5c9e38a77f1a1768f71423161f0daa6b33fbd72f0cbb787a06`.
- The checkout is on `main` at `61b15024e6b9`, `main...origin/main` is ahead
  by `49` commits, the worktree is clean before writing this artifact, and
  `plans/phase-plan-v7-SEMPYTESTOVERVIEW.md` did not exist before this run.
- Repo-local phase-loop state exists in `.phase-loop/state.json` and
  `.phase-loop/events.jsonl`, and the reconciled state now marks
  `SEMPYTESTOVERVIEW` as the current `unplanned` phase on the same roadmap
  SHA. This artifact is therefore the active next-phase handoff, not an
  out-of-band side plan.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is still the live blocker
  artifact. Its latest SEMFASTREPORT evidence snapshot
  (`2026-04-29T07:28:19Z`, observed commit `feda36fc`) records that a fresh
  repo-local `repository sync --force-full` advanced beyond the generated
  fast-test report family, persisted a durable `force_full_exit_trace.json`
  with `stage=lexical_walking`, and moved the most recent durable lexical
  progress marker to
  `/home/viperjuice/code/Code-Index-MCP/ai_docs/pytest_overview.md`.
- `ai_docs/pytest_overview.md` is a small tracked document (`138` lines,
  `3731` bytes). The remaining blocker is therefore not raw file size. It is
  more likely a file-class/path handling gap inside the Markdown lexical path
  than a generic large-document timeout.
- `mcp_server/plugins/markdown_plugin/plugin.py` already has a bounded
  lightweight path for exact Markdown classes such as `CHANGELOG`, `ROADMAP`,
  analysis/report files, `AGENTS`, and `README`. It does not currently treat
  `*_overview.md` or `ai_docs/*.md` as a bounded class, so
  `ai_docs/pytest_overview.md` still falls through the heavy Markdown
  structure/chunk path.
- `EnhancedDispatcher.index_directory(...)` already has tests proving the
  bounded Markdown path for `CHANGELOG.md`, `ROADMAP.md`,
  `FINAL_COMPREHENSIVE_MCP_ANALYSIS.md`, `AGENTS.md`, and `README.md`, and it
  already records durable lexical progress such as `last_progress_path` and
  `in_flight_path`.
- `GitAwareIndexManager.sync_repository_index(..., force_full=True)` already
  persists those lexical snapshots into `.mcp-index/force_full_exit_trace.json`,
  and `uv run mcp-index repository status` already surfaces the durable trace
  plus the explicit fast-report lexical boundary from SEMFASTREPORT.
- The narrow planning question for this phase is therefore whether
  `ai_docs/pytest_overview.md` should get an explicit bounded Markdown path
  or another exact-file lexical repair, then carry that repair through the
  force-full rerun and refreshed dogfood evidence without widening into a
  broad Markdown or docs exclusion.

Practical planning boundary:

- SEMPYTESTOVERVIEW may add an explicit bounded lexical policy for
  `ai_docs/pytest_overview.md` or a similarly narrow `ai_docs/*_overview.md`
  class, carry that policy through the dispatcher and force-full trace, make
  any minimal repository-status wording adjustment needed to keep the repair
  legible, and refresh the dogfood evidence with the rerun outcome.
- SEMPYTESTOVERVIEW must stay narrowly on the exact `pytest_overview.md`
  blocker and the lexical path it exercises. It must not reopen the
  fast-report ignore boundary, summary timeout recovery, semantic ranking,
  provider configuration, or release work.

## Interface Freeze Gates

- [ ] IF-0-SEMPYTESTOVERVIEW-1 - Exact overview blocker contract:
      repo-local `repository sync --force-full` no longer leaves the durable
      lexical trace on `ai_docs/pytest_overview.md`; the repair is explicit
      and tied to that file or a stricter file class it belongs to.
- [ ] IF-0-SEMPYTESTOVERVIEW-2 - Narrow overview Markdown handling contract:
      if the repair uses a bounded Markdown path, it applies only to
      `ai_docs/pytest_overview.md` or a similarly narrow `ai_docs/*_overview.md`
      class, preserves lightweight title/heading discoverability, and does not
      bypass unrelated Markdown/documentation files.
- [ ] IF-0-SEMPYTESTOVERVIEW-3 - Force-full downstream handoff contract:
      after the repair, a repo-local force-full rerun advances beyond
      `ai_docs/pytest_overview.md` and either reaches a later lexical or
      semantic stage or names a new exact downstream blocker that is narrower
      than the current overview-doc seam.
- [ ] IF-0-SEMPYTESTOVERVIEW-4 - Repository-status clarity contract:
      `uv run mcp-index repository status` remains aligned with the durable
      trace and, if the repair adds a new explicit overview-doc boundary,
      explains that boundary without inventing new readiness states.
- [ ] IF-0-SEMPYTESTOVERVIEW-5 - Operator evidence contract:
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the chosen
      `pytest_overview.md` repair, the rerun command/outcome, the refreshed
      durable trace, and whether the repo advanced into semantic work or
      exposed a still narrower downstream blocker.

## Lane Index & Dependencies

- SL-0 - Overview Markdown contract and bounded-path repair; Depends on: SEMFASTREPORT; Blocks: SL-1, SL-2, SL-3; Parallel-safe: no
- SL-1 - Force-full lexical handoff and durable trace advancement; Depends on: SL-0; Blocks: SL-2, SL-3; Parallel-safe: no
- SL-2 - Repository-status wording and blocker surfacing; Depends on: SL-0, SL-1; Blocks: SL-3; Parallel-safe: no
- SL-3 - Dogfood evidence reducer and rerun refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SEMPYTESTOVERVIEW acceptance; Parallel-safe: no

Lane DAG:

```text
SEMFASTREPORT
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SEMPYTESTOVERVIEW acceptance
```

## Lanes

### SL-0 - Overview Markdown Contract And Bounded-Path Repair

- **Scope**: Freeze and implement the exact Markdown handling decision for
  `ai_docs/pytest_overview.md` so this phase removes the known lexical blocker
  without widening into a broad docs exemption.
- **Owned files**: `mcp_server/plugins/markdown_plugin/plugin.py`, `tests/test_dispatcher.py`
- **Interfaces provided**: IF-0-SEMPYTESTOVERVIEW-1 exact overview blocker
  contract; IF-0-SEMPYTESTOVERVIEW-2 narrow overview Markdown handling
  contract
- **Interfaces consumed**: existing `MarkdownPlugin._resolve_lightweight_reason(...)`,
  `_extract_lightweight_title(...)`, `_extract_lightweight_heading_symbols(...)`,
  `EnhancedDispatcher.index_directory(...)`, and the tracked
  `ai_docs/pytest_overview.md` file shape from the current checkout
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` with a repo-shaped fixture that
    proves the current checkout still sends `ai_docs/pytest_overview.md`
    through the heavy Markdown path before the repair, then freezes the chosen
    bounded behavior.
  - test: Add coverage proving the chosen overview repair preserves heading
    discoverability and last-progress reporting for `ai_docs/pytest_overview.md`
    without broadening to unrelated Markdown such as
    `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`.
  - impl: Choose one singular repair surface and keep it explicit: either an
    exact-file bounded path for `ai_docs/pytest_overview.md` or a narrowly
    defined `ai_docs/*_overview.md` bounded class inside the existing
    lightweight Markdown policy.
  - impl: Reuse the existing lightweight Markdown contract rather than adding
    a second document fast path or a repo-wide Markdown ignore rule.
  - impl: Keep the repair file-class narrow and machine-checkable. Do not add
    a broad `ai_docs/*.md`, `*.md`, or documentation-wide bypass.
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov`

### SL-1 - Force-Full Lexical Handoff And Durable Trace Advancement

- **Scope**: Carry the chosen `pytest_overview.md` repair through the real
  lexical handoff so the durable force-full trace moves past that exact path
  instead of timing out in the same lexical-walking seam.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `mcp_server/storage/git_index_manager.py`, `tests/test_git_index_manager.py`
- **Interfaces provided**: IF-0-SEMPYTESTOVERVIEW-3 force-full downstream
  handoff contract
- **Interfaces consumed**: SL-0 bounded overview decision; existing
  `index_directory(...)`, lexical progress snapshot fields,
  `GitAwareIndexManager._full_index(...)`,
  `GitAwareIndexManager.sync_repository_index(...)`, and durable
  `force_full_exit_trace.json` persistence from SEMFASTREPORT
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_git_index_manager.py` so a force-full rerun
    proves the durable trace no longer reports `ai_docs/pytest_overview.md` as
    the last lexical blocker after the repair while still preserving fail-closed
    indexed-commit behavior on a genuine downstream blocker.
  - test: Keep fixture-level assertions on `last_progress_path`,
    `in_flight_path`, `stage`, and `stage_family` so this lane preserves the
    current lexical trace vocabulary instead of renaming stages.
  - impl: Thread the chosen overview-doc repair through the lexical walk and
    force-full handoff only as needed so the rerun can advance beyond
    `ai_docs/pytest_overview.md`.
  - impl: Preserve the SEMFASTREPORT trace contract and the existing
    fail-closed indexed-commit behavior. This lane should move the handoff
    forward, not declare readiness early.
  - impl: If the bounded Markdown repair in SL-0 already gives the dispatcher
    and git-index-manager sufficient behavior with no extra runtime code
    change, record that no-op outcome in execution notes and keep this lane
    scoped to the trace assertion updates plus live rerun proof.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py -q --no-cov`
  - verify: `env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full`
  - verify: `python - <<'PY'
from pathlib import Path
print((Path(".mcp-index") / "force_full_exit_trace.json").read_text())
PY`

### SL-2 - Repository-Status Wording And Blocker Surfacing

- **Scope**: Keep the operator-facing status surface aligned with the chosen
  `pytest_overview.md` repair so the rerun outcome is legible without widening
  the readiness taxonomy.
- **Owned files**: `mcp_server/cli/repository_commands.py`, `tests/test_repository_commands.py`
- **Interfaces provided**: IF-0-SEMPYTESTOVERVIEW-4 repository-status clarity
  contract
- **Interfaces consumed**: SL-1 refreshed durable trace payload; existing
  `repository status` readiness output, semantic evidence sections,
  force-full trace rendering, and the SEMFASTREPORT fast-report boundary
  wording helper
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_repository_commands.py` so `repository status`
    continues to render the durable force-full trace and, if the chosen repair
    introduces a new explicit overview-doc boundary, explains that boundary
    narrowly without inventing new rollout or query states.
  - test: Preserve the existing SEMFASTREPORT fast-report boundary wording and
    the current lexical/semantic readiness fields so this phase does not
    regress the previous blocker explanation while fixing the new one.
  - impl: Tighten `repository status` only as needed so operators can tell
    whether `ai_docs/pytest_overview.md` now uses a bounded path, is no longer
    the active lexical blocker, or exposed a new exact downstream blocker.
  - impl: Keep this lane additive and narrow. Do not redefine readiness states
    or overload semantic preflight/status contracts from earlier phases.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_repository_commands.py -q --no-cov`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`

### SL-3 - Dogfood Evidence Reducer And Rerun Refresh

- **Scope**: Refresh the repo-local dogfood report so it records the
  `pytest_overview.md` repair, the live rerun outcome, and the next exact
  downstream state after this lexical seam is cleared.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: IF-0-SEMPYTESTOVERVIEW-5 operator evidence
  contract
- **Interfaces consumed**: SL-0 chosen overview-doc repair; SL-1 rerun command
  and durable trace; SL-2 repository-status wording; roadmap
  SEMPYTESTOVERVIEW exit criteria
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/docs/test_semdogfood_evidence_contract.py` so the
    refreshed report cites `plans/phase-plan-v7-SEMPYTESTOVERVIEW.md`, the
    chosen `pytest_overview.md` repair, the rerun outcome, and whether the
    repo advanced beyond lexical walking or exposed a narrower blocker.
  - test: Require the report to preserve the existing SEMFASTREPORT evidence
    lineage while making clear that the generated fast-report family is no
    longer the active blocker.
  - impl: Refresh `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` with the new live
    rerun evidence, force-full trace details, SQLite summary/vector counts,
    and the current verdict on whether semantic-stage work can now begin.
  - impl: If the rerun exposes a new exact downstream blocker instead of
    semantic advancement, name that blocker directly and keep roadmap steering
    explicit rather than reverting to a generic retry narrative.
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
  - verify: `sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'`
  - verify: `rg -n "SEMPYTESTOVERVIEW|pytest_overview|force_full_exit_trace|Trace stage|Trace stage family|Last progress path|Dogfood Verdict" docs/status/SEMANTIC_DOGFOOD_REBUILD.md tests/docs/test_semdogfood_evidence_contract.py`

## Verification

Planning-only run: do not execute these during plan creation. Run them during
`codex-execute-phase` or manual SEMPYTESTOVERVIEW execution.

Lane-specific checks:

```bash
uv run pytest tests/test_dispatcher.py -q --no-cov
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py -q --no-cov
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
  tests/test_repository_commands.py \
  tests/docs/test_semdogfood_evidence_contract.py \
  -q --no-cov
env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
git status --short -- specs/phase-plans-v7.md plans/phase-plan-v7-SEMPYTESTOVERVIEW.md docs/status/SEMANTIC_DOGFOOD_REBUILD.md
```

## Acceptance Criteria

- [ ] A live repo-local force-full rerun no longer leaves the durable lexical
      trace in `lexical_walking` with `ai_docs/pytest_overview.md` as the last
      progress marker.
- [ ] The chosen `pytest_overview.md` repair is explicit, narrow, and keeps
      unrelated Markdown/documentation files on their existing indexing paths
      unless new evidence proves another exact blocker.
- [ ] If the repair uses a bounded Markdown path, heading/title
      discoverability remains available for `ai_docs/pytest_overview.md`.
- [ ] `repository status` remains aligned with the durable trace and explains
      any new explicit overview-doc boundary without inventing new readiness
      states.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is refreshed with the
      `pytest_overview.md` rerun outcome and either semantic-stage advancement
      or a still narrower downstream blocker.
- [ ] SEMFASTREPORT's explicit `fast_test_results/fast_report_*.md` boundary
      remains intact and is not reopened by this phase.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v7-SEMPYTESTOVERVIEW.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMPYTESTOVERVIEW.md
  artifact_state: staged
```
