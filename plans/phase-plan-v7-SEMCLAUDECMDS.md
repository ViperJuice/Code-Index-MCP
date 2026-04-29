---
phase_loop_plan_version: 1
phase: SEMCLAUDECMDS
roadmap: specs/phase-plans-v7.md
roadmap_sha256: e53c22ee852978d775f81d2f1c21074b04bc531f495918ba989fc5428d018465
---
# SEMCLAUDECMDS: Claude Command Lexical Recovery

## Context

SEMCLAUDECMDS is the phase-47 follow-up for the v7 semantic hardening
roadmap. Canonical `.phase-loop/state.json` now marks `SEMCLAUDECMDS` as the
current `unplanned` phase after `SEMDOCGOV` closed out on `HEAD`
`3dba95633b28eb2467e46835bfe1f1460647d002` with verification `passed`, a clean
worktree, and `main...origin/main [ahead 89]`. `specs/phase-plans-v7.md` is
tracked and clean in this worktree, and its live SHA matches the roadmap hash
requested for this artifact:
`e53c22ee852978d775f81d2f1c21074b04bc531f495918ba989fc5428d018465`.
Legacy `.codex/phase-loop/` state exists only as compatibility residue and is
not authoritative for this run.

The active blocker evidence is already frozen in
`docs/status/SEMANTIC_DOGFOOD_REBUILD.md`. Its SEMDOCGOV rerun capture at
`2026-04-29T14:41:32Z` records the refreshed repo-local command
`timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
terminalizing later in lexical walking with `Trace status: interrupted`,
`Trace stage: lexical_walking`, `Trace blocker source: lexical_mutation`,
`Last progress path:
/home/viperjuice/code/Code-Index-MCP/.claude/commands/execute-lane.md`, and
`In-flight path:
/home/viperjuice/code/Code-Index-MCP/.claude/commands/plan-phase.md`.
SEMDOCGOV therefore satisfied its own acceptance boundary, and the roadmap now
steers execution to this exact later `.claude/commands` seam.

Repository research narrows the likely repair surface:

- `.claude/commands/execute-lane.md` is `5732` bytes and `186` lines;
  `.claude/commands/plan-phase.md` is `2778` bytes and `86` lines. Both are
  far below `mcp_server/plugins/markdown_plugin/plugin.py`'s current
  `_LIGHTWEIGHT_MARKDOWN_BYTES = 250_000` cutoff.
- The Markdown plugin already has bounded-name rules for changelog, roadmap,
  analysis-report, `AGENTS.md`, `README.md`, `ai_docs/*_overview.md`, plus
  exact bounded Markdown path entries for `ai_docs/jedi.md`,
  `docs/validation/ga-closeout-decision.md`,
  `docs/validation/mre2e-evidence.md`, and the benchmark pair. The current
  `_resolve_lightweight_reason(...)` surface does not include the exact
  `.claude/commands/execute-lane.md` or `.claude/commands/plan-phase.md`
  paths, so those files still fall through to the heavyweight Markdown AST and
  chunking path under the same lexical watchdog.
- Existing test coverage is adjacent but incomplete for this exact seam.
  `tests/test_dispatcher.py`, `tests/test_git_index_manager.py`, and
  `tests/root_tests/test_markdown_production_scenarios.py` already freeze the
  earlier bounded Markdown families and durable trace carry-forward, but they
  do not yet pin this exact `.claude/commands` pair or guard against an
  over-broad `.claude/**/*.md` exemption.
- `mcp_server/cli/repository_commands.py` already advertises exact bounded
  Markdown or Python boundaries for the older validation, benchmark,
  visualization, and docs-contract seams, and
  `tests/docs/test_semdogfood_evidence_contract.py` already requires the
  evidence artifact to keep `.claude/commands/execute-lane.md` and
  `.claude/commands/plan-phase.md` in the live runtime narrative. What is
  still missing is an execution-ready phase plan that freezes the narrow
  command-pair repair, adds the operator-facing boundary wording if needed, and
  refreshes the rerun evidence on the repaired head.

Practical planning boundary:

- SEMCLAUDECMDS may add a narrow exact bounded Markdown path repair for the
  two `.claude/commands` files, preserve lexical document and heading
  discoverability for those files, align `repository status` wording with the
  repaired boundary, rerun the repo-local force-full sync, and refresh the
  dogfood evidence with either a later truthful blocker or proof that the
  command pair is no longer active.
- SEMCLAUDECMDS must stay tightly scoped to
  `.claude/commands/execute-lane.md -> .claude/commands/plan-phase.md`. It
  must not broaden into a blanket `.claude/**/*.md` fast-path, repo-wide
  Markdown timeout retuning, or reopening older validation, benchmark,
  archive-tail, docs-governance, or AGENTS/README seams unless the refreshed
  rerun explicitly re-anchors there again.

## Interface Freeze Gates

- [ ] IF-0-SEMCLAUDECMDS-1 - Claude-command pair advance contract:
      a refreshed repo-local force-full rerun on the post-SEMDOCGOV head no
      longer terminalizes with the durable lexical trace centered on
      `.claude/commands/execute-lane.md ->
      .claude/commands/plan-phase.md`; it either advances durably beyond that
      pair or emits a truthful newer blocker before the 120-second watchdog
      expires.
- [ ] IF-0-SEMCLAUDECMDS-2 - Exact Markdown repair contract:
      any new lexical recovery remains limited to the exact files
      `.claude/commands/execute-lane.md` and
      `.claude/commands/plan-phase.md`. It does not broaden into arbitrary
      `.claude/**/*.md`, a generic command-doc exemption, or a repo-wide
      lexical-timeout retune.
- [ ] IF-0-SEMCLAUDECMDS-3 - Lexical discoverability contract:
      whichever bounded Markdown repair is chosen preserves lexical file
      storage plus durable document and heading discoverability for the exact
      `.claude/commands` files it touches; the repair must not silently turn
      those command docs into lexical blind spots.
- [ ] IF-0-SEMCLAUDECMDS-4 - Durable trace and status contract:
      `force_full_exit_trace.json` and `uv run mcp-index repository status`
      stay truthful about the repaired command-pair boundary. If one or both
      command files are short-circuited onto an exact bounded Markdown path,
      the status surface must explain that exact pair without regressing to
      stale generic Markdown wording or older docs-governance seams.
- [ ] IF-0-SEMCLAUDECMDS-5 - Evidence contract:
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the SEMDOCGOV rerun
      outcome, the SEMCLAUDECMDS rerun command and timestamps, the refreshed
      durable trace/status output, and the final authoritative verdict for the
      `.claude/commands` blocker.

## Lane Index & Dependencies

- SL-0 - Claude-command pair fixture freeze; Depends on: SEMDOCGOV; Blocks: SL-1, SL-2, SL-3; Parallel-safe: no
- SL-1 - Exact `.claude/commands` bounded Markdown repair; Depends on: SL-0; Blocks: SL-2, SL-3; Parallel-safe: no
- SL-2 - Operator boundary and durable-trace alignment; Depends on: SL-0, SL-1; Blocks: SL-3; Parallel-safe: no
- SL-3 - Live rerun evidence reducer and downstream steering refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SEMCLAUDECMDS acceptance; Parallel-safe: no

Lane DAG:

```text
SEMDOCGOV
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SEMCLAUDECMDS acceptance
```

## Lanes

### SL-0 - Claude-Command Pair Fixture Freeze

- **Scope**: Freeze the exact `.claude/commands/execute-lane.md ->
  .claude/commands/plan-phase.md` lexical seam in unit and production-shape
  tests before runtime changes so the phase proves a narrow pair repair rather
  than a broad command-doc shortcut.
- **Owned files**: `tests/test_dispatcher.py`, `tests/test_git_index_manager.py`, `tests/root_tests/test_markdown_production_scenarios.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMCLAUDECMDS-1,
  IF-0-SEMCLAUDECMDS-2,
  IF-0-SEMCLAUDECMDS-3,
  and the durable-trace portion of IF-0-SEMCLAUDECMDS-4
- **Interfaces consumed**: existing
  `MarkdownPlugin._resolve_lightweight_reason(...)`,
  `MarkdownPlugin._build_lightweight_index_shard(...)`,
  `EnhancedDispatcher.index_directory(...)`,
  `GitAwareIndexManager.sync_repository_index(...)`,
  and the current SEMDOCGOV evidence for the `.claude/commands` pair
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` with a repo-shaped fixture that
    proves the repaired path advances past
    `.claude/commands/execute-lane.md` without leaving
    `.claude/commands/plan-phase.md` as a silent heavy-path regression, while
    preserving the lexical watchdog for unrelated Markdown files.
  - test: Extend `tests/test_git_index_manager.py` so durable force-full trace
    persistence freezes the command-pair handoff and verifies later reruns do
    not regress to the older docs-governance blocker wording once the exact
    pair is repaired.
  - test: Extend `tests/root_tests/test_markdown_production_scenarios.py` so
    both command docs assert the chosen bounded Markdown shape preserves
    document plus heading symbols, and add a negative assertion that unrelated
    `.claude/commands/*.md` files do not automatically inherit the same exact
    fast-path unless explicitly named.
  - impl: Keep fixtures deterministic with synthetic command-doc content and
    monkeypatched Markdown heavy-path guards rather than multi-minute live
    waits inside test coverage.
  - impl: Keep this lane on contract freeze only. Do not update operator
    status wording or the dogfood evidence artifact here.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov -k "claude or commands or execute or plan or lexical or force_full or markdown"`
  - verify: `uv run pytest tests/root_tests/test_markdown_production_scenarios.py -q --no-cov -k "claude or command or execute or plan"`

### SL-1 - Exact `.claude/commands` Bounded Markdown Repair

- **Scope**: Implement the smallest exact Markdown repair needed so the live
  lexical walker no longer spends its watchdog budget on the
  `.claude/commands/execute-lane.md -> .claude/commands/plan-phase.md` pair.
- **Owned files**: `mcp_server/plugins/markdown_plugin/plugin.py`
- **Interfaces provided**: IF-0-SEMCLAUDECMDS-2 exact Markdown repair
  contract; IF-0-SEMCLAUDECMDS-3 lexical discoverability contract
- **Interfaces consumed**: SL-0 command-pair fixtures; existing bounded-name
  Markdown rules; existing `_EXACT_BOUNDED_MARKDOWN_PATHS`; lightweight title
  and heading extraction; and the current heavy-path fallback behavior for
  Markdown files that are not on a bounded path
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 Markdown slice first and confirm the exact
    `.claude/commands` pair still falls through to the heavy Markdown path on
    the current checkout.
  - impl: Choose the narrowest repair surface and keep it exact: either extend
    `_EXACT_BOUNDED_MARKDOWN_PATHS` with the two concrete
    `.claude/commands` paths or add an equivalently narrow exact-path branch
    in `_resolve_lightweight_reason(...)`. Do not add a broad `.claude`
    directory rule or a generic command-doc filename heuristic.
  - impl: Reuse the existing lightweight Markdown shard builder so
    `execute-lane.md` and `plan-phase.md` preserve document metadata plus
    heading discoverability rather than becoming ignored or contentless files.
  - impl: Keep this lane local to the Markdown plugin. Do not retune the
    global Markdown byte cutoff and do not reopen earlier AGENTS, README,
    roadmap, or benchmark bounded-name behavior here.
  - verify: `uv run pytest tests/root_tests/test_markdown_production_scenarios.py -q --no-cov -k "claude or command or execute or plan"`

### SL-2 - Operator Boundary And Durable-Trace Alignment

- **Scope**: Keep the operator-facing status surface aligned with the repaired
  command-pair behavior so `repository status` explains the exact bounded
  Markdown seam truthfully instead of leaving the pair implicit in raw paths
  alone.
- **Owned files**: `mcp_server/cli/repository_commands.py`, `tests/test_repository_commands.py`
- **Interfaces provided**: the operator-surface portion of
  IF-0-SEMCLAUDECMDS-4 durable trace and status contract
- **Interfaces consumed**: SL-0 command-pair fixture vocabulary; SL-1 chosen
  exact Markdown repair; existing `_print_force_full_exit_trace(...)`; current
  exact bounded Markdown boundary helpers for validation and benchmark docs;
  and current durable trace fields `last_progress_path` / `in_flight_path`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_repository_commands.py` so `uv run mcp-index repository status`
    must advertise the exact bounded Markdown seam for
    `.claude/commands/execute-lane.md -> .claude/commands/plan-phase.md`
    whenever both files exist and the durable trace has already advanced into
    or beyond that pair.
  - impl: Add the narrowest boundary-printer helper needed for the exact
    `.claude/commands` pair and keep it additive beside the existing
    validation, benchmark, Jedi, and docs-governance helpers.
  - impl: Preserve the current durable trace vocabulary. This lane should not
    rename `Trace stage`, `Trace blocker source`, `last_progress_path`, or
    `in_flight_path`; it should only make the command-pair boundary explicit
    when the files are present.
  - impl: Do not broaden status wording into a generic `.claude` directory
    claim or a catch-all Markdown fast-path summary.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_repository_commands.py -q --no-cov -k "claude or commands or execute or plan or boundary or force_full or interrupted"`

### SL-3 - Live Rerun Evidence Reducer And Downstream Steering Refresh

- **Scope**: Re-run the repaired repo-local force-full sequence, reduce the
  outcome into the durable semantic dogfood evidence artifact, and record the
  authoritative post-command-pair verdict for the next downstream work.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: IF-0-SEMCLAUDECMDS-1 command-pair advance contract;
  IF-0-SEMCLAUDECMDS-4 durable trace and status contract;
  IF-0-SEMCLAUDECMDS-5 evidence contract
- **Interfaces consumed**: SL-0 command-pair fixture vocabulary; SL-1 repaired
  command-doc behavior; SL-2 status wording; current SEMDOCGOV evidence; and
  the live repo-local `force_full_exit_trace.json`, `repository status`, and
  SQLite runtime counts after the refreshed rerun
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/docs/test_semdogfood_evidence_contract.py` so the
    evidence artifact must retain the `.claude/commands` pair, the
    SEMCLAUDECMDS rerun command, the refreshed trace/status fields, the phase
    plan reference, and the final verdict for whether the active blocker moved
    beyond the exact command-doc seam.
  - impl: Refresh `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` with the SEMDOCGOV
    observed command-pair blocker, the repaired SEMCLAUDECMDS rerun command
    and timestamps, the resulting durable trace snapshot, the matching
    `repository status` output, and the final call on whether the active
    blocker advanced beyond `.claude/commands/plan-phase.md`.
  - impl: If the refreshed rerun reaches a newer blocker after the command
    pair is cleared, record that exact blocker and amend the roadmap at the
    nearest downstream phase that is not already executing before treating any
    older downstream plan or handoff as authoritative.
  - impl: Keep the evidence truthful about lexical-only progress.
    `chunk_summaries` and `semantic_points` may remain zero here; do not imply
    semantic closeout unless the rerun actually leaves lexical walking.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
  - verify: `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - verify: `sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'`
  - verify: `git diff --check`
  - verify: `git diff --cached --check`

## Verification

- Lane checks:
  - `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov -k "claude or commands or execute or plan or lexical or force_full or markdown"`
  - `uv run pytest tests/root_tests/test_markdown_production_scenarios.py -q --no-cov -k "claude or command or execute or plan"`
  - `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_repository_commands.py -q --no-cov -k "claude or commands or execute or plan or boundary or force_full or interrupted"`
  - `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
- Whole-phase checks:
  - `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_repository_commands.py tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "claude or commands or execute or plan or lexical or force_full or boundary or interrupted"`
  - `uv run pytest tests/root_tests/test_markdown_production_scenarios.py -q --no-cov -k "claude or command or execute or plan"`
  - `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  - `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - `sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'`
  - `git diff --check`
  - `git diff --cached --check`

## Acceptance Criteria

- [ ] A refreshed repo-local force-full rerun on the post-SEMDOCGOV head
      either advances durably beyond
      `.claude/commands/execute-lane.md ->
      .claude/commands/plan-phase.md` or emits a truthful newer blocker
      before the 120-second watchdog expires.
- [ ] The repair stays narrowly scoped to the exact
      `.claude/commands/execute-lane.md` and
      `.claude/commands/plan-phase.md` pair plus the immediate status/evidence
      plumbing needed to prove it.
- [ ] Lexical file storage and document-plus-heading discoverability remain
      intact for the exact `.claude/commands` path(s) touched by the repair.
- [ ] `uv run mcp-index repository status` and
      `force_full_exit_trace.json` stay aligned with the repaired command-pair
      outcome and do not regress to stale generic Markdown or older
      docs-governance wording.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the SEMDOCGOV rerun
      outcome and the final live verdict for the `.claude/commands` blocker.

automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMCLAUDECMDS.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMCLAUDECMDS.md
  artifact_state: staged
