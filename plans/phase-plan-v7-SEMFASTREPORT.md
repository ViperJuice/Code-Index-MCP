---
phase_loop_plan_version: 1
phase: SEMFASTREPORT
roadmap: specs/phase-plans-v7.md
roadmap_sha256: b5b745201c821c616f94bd884244cac63dc586885ed966e9e858779784edf7a2
---
# SEMFASTREPORT: Fast Test Report Lexical Recovery

## Context

SEMFASTREPORT is the phase-26 follow-up for the v7 semantic hardening
roadmap. SEMEXITTRACE landed the durable live force-full trace and narrowed
the remaining repo-local blocker: a repo-local
`repository sync --force-full` can still stay in lexical walking long enough
to be terminated before semantic closeout, and the latest durable progress
marker is a generated fast-test report path under `fast_test_results/`.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is tracked and clean in this worktree, and its
  live SHA matches the required
  `b5b745201c821c616f94bd884244cac63dc586885ed966e9e858779784edf7a2`.
- The checkout is on `main` at `456cca8c0f00f2f91bc007b667012fd6b7192c61`,
  `main...origin/main` is ahead by `47` commits, the worktree is clean before
  writing this artifact, and `plans/phase-plan-v7-SEMFASTREPORT.md` did not
  exist before this run.
- `.phase-loop/state.json` and `.phase-loop/tui-handoff.md` already mark
  `SEMFASTREPORT` as the current unplanned phase for the same roadmap SHA, so
  this plan is the missing execution handoff for the active downstream
  blocker rather than a side plan.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is the live blocker artifact for
  this phase. Its latest SEMEXITTRACE evidence snapshot
  (`2026-04-29T07:06:18Z`, observed commit `a6492a44`) records that a fresh
  `repository sync --force-full` stayed in flight for `2:10.04`, persisted a
  durable `force_full_exit_trace.json` with `stage=lexical_walking`, and left
  `chunk_summaries = 0` plus `semantic_points = 0`.
- The most recent durable progress path in that trace is
  `/home/viperjuice/code/Code-Index-MCP/fast_test_results/fast_report_20250628_193425.md`.
  That file is currently tracked in git, and neither `.gitignore` nor
  `.mcp-index-ignore` excludes the `fast_test_results/` family today.
- The roadmap names `mcp_server/dispatcher/ignore_patterns.py`, but the live
  ignore/filter implementation actually lives in
  `mcp_server/core/ignore_patterns.py`. `EnhancedDispatcher.index_directory(...)`
  consumes `build_walker_filter(...)` from that module before lexical
  mutation starts, so SEMFASTREPORT must target the real filter surface in the
  checkout.
- `EnhancedDispatcher.index_directory(...)` already records lexical progress
  fields such as `lexical_stage`, `lexical_files_attempted`,
  `lexical_files_completed`, `last_progress_path`, and `in_flight_path`.
  `GitAwareIndexManager.sync_repository_index(..., force_full=True)` already
  persists those snapshots into `.mcp-index/force_full_exit_trace.json`, and
  `uv run mcp-index repository status` already renders the durable trace.
  SEMFASTREPORT should consume that contract rather than inventing new
  readiness taxonomy.
- The current evidence proves that the generated fast-test report family is
  the last durable lexical progress marker, but it does not yet prove whether
  the right repair is an explicit ignore/filter boundary or a bounded
  keep-indexing policy. The phase must freeze that decision with tests before
  mutating runtime behavior.

Practical planning boundary:

- SEMFASTREPORT may define an explicit generated-report ignore/filter
  contract, or if the reports must remain indexable, a bounded lexical
  handling contract for that file family, then carry the chosen boundary
  through the live force-full rerun and refreshed dogfood evidence.
- SEMFASTREPORT must stay narrowly on `fast_test_results/fast_report_*.md`,
  the lexical walk / force-full handoff it affects, and the resulting
  operator evidence. It must not reopen summary timeout, runtime restore,
  ranking, semantic provider, or multi-repo contract work from earlier phases.

## Interface Freeze Gates

- [ ] IF-0-SEMFASTREPORT-1 - Generated fast-test report boundary contract:
      `fast_test_results/fast_report_*.md` is either explicitly excluded from
      lexical indexing by the repo-local walker filter, or kept indexable only
      under a bounded lexical path that returns promptly enough for
      `repository sync --force-full` to advance beyond lexical walking.
- [ ] IF-0-SEMFASTREPORT-2 - Narrow-scope filter contract: if the repair
      treats the report family as generated noise, the chosen ignore/filter
      rule is explicit, tested, and narrow enough that ordinary repository
      Markdown source files remain indexable.
- [ ] IF-0-SEMFASTREPORT-3 - Force-full downstream handoff contract: after the
      generated-report repair, a repo-local force-full rerun no longer leaves
      the durable trace stuck on `fast_test_results/fast_report_*.md`; it
      either advances into later lexical/semantic stages or exits with a new
      exact downstream blocker that is narrower than the current lexical-walk
      report family.
- [ ] IF-0-SEMFASTREPORT-4 - Operator evidence contract:
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the chosen generated-
      report boundary, the rerun command/outcome, the refreshed durable trace,
      and whether the next blocker moved beyond lexical walking.
- [ ] IF-0-SEMFASTREPORT-5 - Phase boundary contract: SEMFASTREPORT changes
      only the generated fast-test report lexical boundary, the force-full
      handoff that consumes it, and the resulting evidence. It does not
      redesign broader Markdown indexing, reopen summary-call shutdown logic,
      or widen rollout policy.

## Lane Index & Dependencies

- SL-0 - Generated-report contract tests and fixture freeze; Depends on: SEMEXITTRACE; Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 - Generated-report ignore or bounded lexical policy; Depends on: SL-0; Blocks: SL-2, SL-3, SL-4; Parallel-safe: no
- SL-2 - Force-full lexical handoff and trace integration; Depends on: SL-0, SL-1; Blocks: SL-3, SL-4; Parallel-safe: no
- SL-3 - Repository-status acceptance and blocker wording; Depends on: SL-0, SL-1, SL-2; Blocks: SL-4; Parallel-safe: no
- SL-4 - Dogfood evidence reducer and rerun refresh; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: SEMFASTREPORT acceptance; Parallel-safe: no

Lane DAG:

```text
SEMEXITTRACE
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SL-4 -> SEMFASTREPORT acceptance
```

## Lanes

### SL-0 - Generated-Report Contract Tests And Fixture Freeze

- **Scope**: Freeze the exact `fast_test_results/fast_report_*.md` blocker
  contract before implementation so this phase proves a deliberate lexical
  boundary repair instead of only moving the live timeout somewhere less
  visible.
- **Owned files**: `tests/test_ignore_patterns.py`, `tests/test_dispatcher.py`, `tests/test_git_index_manager.py`, `tests/test_repository_commands.py`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMFASTREPORT-1 through IF-0-SEMFASTREPORT-5
- **Interfaces consumed**: existing `build_walker_filter(...)`,
  `IgnorePatternManager.should_ignore(...)`,
  `EnhancedDispatcher.index_directory(...)`,
  `GitAwareIndexManager.sync_repository_index(...)`,
  `GitAwareIndexManager.get_repository_status(...)`,
  `repository status` CLI output, and the current
  `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` evidence structure
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_ignore_patterns.py` with a repo-shaped fixture
    that proves the current checkout does not exclude
    `fast_test_results/fast_report_*.md`, then freezes the chosen repair so
    nearby Markdown source files remain indexable.
  - test: Extend `tests/test_dispatcher.py` so lexical-walk progress fixtures
    prove the fast-report family is either skipped before mutation or handled
    through a bounded lexical path without stalling the lexical stage.
  - test: Extend `tests/test_git_index_manager.py` so a force-full rerun
    proves the durable trace no longer reports the fast-report family as the
    last lexical blocker after the repair, while still preserving fail-closed
    commit advancement on genuine downstream failures.
  - test: Extend `tests/test_repository_commands.py` so `repository status`
    continues to surface the durable trace and, if the chosen repair uses an
    explicit ignore/filter boundary, explains that boundary without inventing
    new readiness states.
  - test: Extend `tests/docs/test_semdogfood_evidence_contract.py` so the
    refreshed report must cite `SEMFASTREPORT`, the chosen report-family
    boundary, the rerun outcome, and the next exact blocker or semantic-ready
    verdict.
  - impl: Keep fixtures synthetic with repo-local paths, mocked trace payloads,
    and monkeypatched dispatcher/git-index-manager behavior rather than long
    live waits inside unit coverage.
  - impl: Keep this lane focused on contract freeze. Do not edit the live
    evidence report or rerun the force-full command here.
  - verify: `uv run pytest tests/test_ignore_patterns.py tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_repository_commands.py tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`

### SL-1 - Generated-Report Ignore Or Bounded Lexical Policy

- **Scope**: Implement one deliberate repository-local policy for
  `fast_test_results/fast_report_*.md` so the lexical walker no longer spends
  the live force-full window on generated fast-test report artifacts.
- **Owned files**: `mcp_server/core/ignore_patterns.py`, `.mcp-index-ignore`
- **Interfaces provided**: IF-0-SEMFASTREPORT-1 generated-report boundary
  contract; IF-0-SEMFASTREPORT-2 narrow-scope filter contract
- **Interfaces consumed**: SL-0 ignore-pattern and dispatcher tests; existing
  root-level `.gitignore` / `.mcp-index-ignore` loading,
  `IgnorePatternManager.should_ignore(...)`, `build_walker_filter(...)`, and
  the tracked `fast_test_results/fast_report_20250628_193425.md` repo fixture
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 ignore-pattern slice first and confirm the current
    checkout still allows `fast_test_results/fast_report_*.md` into the
    walker filter.
  - impl: Choose one singular generated-report policy and keep it explicit:
    either add a narrow ignore/filter rule for the fast-report family, or
    document in code why the family must stay indexable and expose a matching
    bounded lexical predicate for the dispatcher to consume.
  - impl: Keep the rule narrow to generated fast-test reports or their parent
    directory. Do not widen it into a broad `*.md`, `tests/`, or
    documentation-wide exclusion.
  - impl: Preserve the existing root-level ignore manager contract. This lane
    should refine the repo-local generated-report boundary, not introduce a
    second ignore subsystem.
  - impl: If `.mcp-index-ignore` changes, keep the rule machine-readable and
    consistent with `IgnorePatternManager` semantics so the same family is
    filtered in both unit fixtures and live force-full walking.
  - verify: `uv run pytest tests/test_ignore_patterns.py tests/test_dispatcher.py -q --no-cov`

### SL-2 - Force-Full Lexical Handoff And Trace Integration

- **Scope**: Carry the chosen generated-report boundary through the real
  lexical walk and force-full closeout so the durable trace moves beyond the
  fast-report family instead of timing out in the same lexical stage.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `mcp_server/storage/git_index_manager.py`
- **Interfaces provided**: IF-0-SEMFASTREPORT-3 force-full downstream handoff
  contract
- **Interfaces consumed**: SL-0 dispatcher/git-index-manager tests; SL-1
  generated-report boundary decision; existing `index_directory(...)`,
  `_index_file_with_lexical_timeout(...)`,
  `GitAwareIndexManager._full_index(...)`,
  `GitAwareIndexManager.sync_repository_index(...)`, and durable
  `force_full_exit_trace.json` persistence from SEMEXITTRACE
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 dispatcher and git-index-manager slice first and
    confirm the current force-full path still leaves the durable lexical trace
    anchored on the fast-report family.
  - impl: Thread the chosen generated-report boundary through lexical walking
    so skipped or specially handled fast-test reports do not consume the live
    force-full budget before semantic closeout can begin.
  - impl: Preserve the existing SEMEXITTRACE trace vocabulary and fail-closed
    commit advancement behavior. This lane should move the handoff forward,
    not redefine trace stages or claim success early.
  - impl: If the chosen policy is a bounded keep-indexing path rather than a
    pure ignore rule, keep that path local to the fast-report family and avoid
    broad Markdown performance changes for unrelated documents.
  - impl: Do not reopen summary-timeout settlement, runtime restore, semantic
    ranking, or provider configuration. This lane owns the lexical/force-full
    handoff only.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov`
  - verify: `env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - verify: `python - <<'PY'
from pathlib import Path
print((Path(".mcp-index") / "force_full_exit_trace.json").read_text())
PY`
  - verify: `sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'`

### SL-3 - Repository-Status Acceptance And Blocker Wording

- **Scope**: Keep the operator-facing status surface aligned with the chosen
  generated-report boundary so the rerun outcome is legible without reopening
  the broader readiness taxonomy.
- **Owned files**: `mcp_server/cli/repository_commands.py`
- **Interfaces provided**: operator-facing acceptance for IF-0-SEMFASTREPORT-3
  and IF-0-SEMFASTREPORT-4
- **Interfaces consumed**: SL-0 repository-status tests; SL-2 refreshed
  durable trace payload; existing `repository status` readiness, semantic
  evidence, and force-full trace sections
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 repository-status slice first and confirm whether the
    chosen generated-report policy already renders clearly with the existing
    SEMEXITTRACE surface or needs narrow wording adjustments.
  - impl: Tighten `repository status` only as needed so operators can tell
    whether the fast-report family is now ignored, bounded, or no longer the
    active lexical blocker after the rerun.
  - impl: Keep the current readiness, preflight, and semantic evidence output
    intact. This lane should clarify the fast-report outcome, not introduce
    new rollout states or semantic remediation categories.
  - impl: If no CLI code change is required after SL-0 and SL-2 prove the
    existing surface is sufficient, record that no-op decision in the lane
    execution notes rather than widening the scope.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_repository_commands.py -q --no-cov`

### SL-4 - Dogfood Evidence Reducer And Rerun Refresh

- **Scope**: Re-run the repaired repo-local force-full path and refresh the
  durable dogfood report so the repository records whether the generated
  fast-report boundary finally moved execution beyond lexical walking.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- **Interfaces provided**: IF-0-SEMFASTREPORT-4 refreshed operator evidence
- **Interfaces consumed**: SL-1 chosen generated-report boundary; SL-2 rerun
  command outcomes, durable trace payload, and SQLite counts; SL-3 final
  operator wording contract; existing `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
  structure from SEMEXITTRACE
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 docs contract slice first and confirm the existing
    report still names SEMEXITTRACE as the latest closeout and fast-test
    reports as the next blocker to clear.
  - impl: Refresh `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` after the
    SEMFASTREPORT rerun with the chosen generated-report boundary, the rerun
    timing, the refreshed force-full trace, SQLite counts, current-versus-
    indexed commit evidence, and the final verdict.
  - impl: State explicitly whether the rerun advanced beyond lexical walking,
    reached later summary/semantic stages, or exposed a new narrower blocker.
    Do not leave the report at the older SEMEXITTRACE ambiguity.
  - impl: Keep the report inside the existing repo-local dogfood boundary:
    `.mcp-index/current.db`, `.mcp-index/semantic_qdrant/`, and
    `.mcp-index/force_full_exit_trace.json`. Do not broaden into release,
    multi-repo rollout, or unrelated benchmark reporting.
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
  - verify: `env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - verify: `python - <<'PY'
from pathlib import Path
print((Path(".mcp-index") / "force_full_exit_trace.json").read_text())
PY`
  - verify: `sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'`

## Verification

- `uv run pytest tests/test_ignore_patterns.py tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_repository_commands.py tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
- `env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full`
- `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
- `python - <<'PY'
from pathlib import Path
print((Path(".mcp-index") / "force_full_exit_trace.json").read_text())
PY`
- `sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'`

## Acceptance Criteria

- [ ] The live repo-local force-full rerun no longer leaves the durable trace
      in `lexical_walking` with `fast_test_results/fast_report_*.md` as the
      last progress marker.
- [ ] The generated fast-test report family has an explicit, narrow, and
      tested lexical boundary: either ignored as generated noise or retained
      only under a bounded lexical path that does not stall force-full
      closeout.
- [ ] `repository status` and `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
      explain the chosen report-family policy and the rerun outcome without
      inventing new readiness taxonomy.
- [ ] The refreshed dogfood evidence records whether execution advanced into a
      later lexical/semantic stage or exposed a new narrower downstream
      blocker after the fast-report repair.
