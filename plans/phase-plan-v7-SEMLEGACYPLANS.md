---
phase_loop_plan_version: 1
phase: SEMLEGACYPLANS
roadmap: specs/phase-plans-v7.md
roadmap_sha256: 3dc6f53a0d239b608187b8c883517f3e3fa58554e7201f878bc28ee6592417d8
---
# SEMLEGACYPLANS: Historical Phase Plan Tail Recovery

## Context

SEMLEGACYPLANS is the phase-52 follow-up for the v7 semantic hardening
roadmap. Canonical `.phase-loop/` state is authoritative for this run:
`.phase-loop/state.json` and `.phase-loop/tui-handoff.md` both mark
`SEMLEGACYPLANS` as the current `unplanned` phase after `SEMPHASETAIL`
closed out on `HEAD` `f1ee24f67acf` with verification `passed`, a clean
worktree, and `main...origin/main [ahead 99]`. Legacy `.codex/phase-loop/`
artifacts are compatibility-only and are not authoritative here.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is tracked and clean in this worktree, and the
  live roadmap SHA matches the required
  `3dc6f53a0d239b608187b8c883517f3e3fa58554e7201f878bc28ee6592417d8`.
- The target artifact `plans/phase-plan-v7-SEMLEGACYPLANS.md` did not exist
  before this planning run.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is the active evidence anchor.
  Its SEMPHASETAIL live-rerun block captures the current downstream lexical
  failure precisely: at evidence time `2026-04-29T16:07:22Z`, the refreshed
  repo-local command
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  exited `124` with `Trace status: interrupted`, `Trace stage:
  lexical_walking`, `Trace stage family: lexical`, `Trace blocker source:
  lexical_mutation`, `Last progress path:
  /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v6-WATCH.md`, and
  `In-flight path:
  /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v1-p19.md`.
- The SEMPHASETAIL target pair is no longer the active blocker:
  `plans/phase-plan-v7-SEMSYNCFIX.md ->
  plans/phase-plan-v7-SEMVISUALREPORT.md`. The live rerun now reaches the
  historical phase-plan pair
  `plans/phase-plan-v6-WATCH.md ->
  plans/phase-plan-v1-p19.md`, so older downstream assumptions should be
  treated as stale.
- The newly exposed pair is structurally asymmetric. `plans/phase-plan-v6-WATCH.md`
  is a modern phase-loop plan with frontmatter (`189` lines / `13152`
  bytes), while `plans/phase-plan-v1-p19.md` is a legacy plan artifact with
  no phase-loop frontmatter and a long quoted preamble (`359` lines /
  `35053` bytes). This phase should assume the historical layout difference
  matters more than the file extension alone.
- Operator status already advertises several exact lexical seams in
  `mcp_server/cli/repository_commands.py`, including the repaired later
  v7-only phase-plan pair. The SEMPHASETAIL evidence explicitly says the
  historical pair is visible through `force_full_exit_trace.json`, but not a
  dedicated lexical boundary line yet.
- Existing tests already freeze adjacent behavior but not the full
  SEMLEGACYPLANS contract. `tests/test_dispatcher.py` covers bounded
  Markdown routing and lexical visibility for modern phase-plan-like docs,
  `tests/test_git_index_manager.py` and `tests/test_repository_commands.py`
  already reference `plans/phase-plan-v6-WATCH.md` as the next downstream
  document after the repaired later v7 pair, and
  `tests/docs/test_semdogfood_evidence_contract.py` already requires both
  historical plan paths to remain in the dogfood evidence. What is missing is
  the execution-ready contract that binds dispatcher behavior, durable trace
  progression, operator wording, evidence refresh, and possible downstream
  roadmap steering to this exact historical phase-plan seam.

Practical planning boundary:

- SEMLEGACYPLANS may tighten exact historical phase-plan handling, dispatcher
  lexical progress accounting, durable trace persistence, operator status
  wording, the semantic dogfood evidence artifact, and downstream roadmap
  steering needed to prove a live rerun either advances beyond
  `plans/phase-plan-v6-WATCH.md ->
  plans/phase-plan-v1-p19.md` or surfaces a truthful newer blocker.
- SEMLEGACYPLANS must stay narrow and evidence-driven. It must not reopen the
  repaired later v7-only pair, introduce a blanket `plans/phase-plan-*.md`
  exemption, retune the repo-wide lexical watchdog, or reopen older
  benchmark, visualization, devcontainer, archive-tail, docs-governance,
  `.claude`, or script-language seams unless the refreshed rerun directly
  re-anchors there again.

## Interface Freeze Gates

- [ ] IF-0-SEMLEGACYPLANS-1 - Historical phase-plan pair advance contract:
      a refreshed repo-local force-full rerun on the post-SEMPHASETAIL head
      no longer terminalizes with the durable lexical trace centered on
      `plans/phase-plan-v6-WATCH.md ->
      plans/phase-plan-v1-p19.md`; it either advances durably beyond that
      pair or emits a truthful newer blocker before the 120-second watchdog
      expires.
- [ ] IF-0-SEMLEGACYPLANS-2 - Exact boundary contract:
      any repair introduced by this phase remains limited to the exact
      historical phase-plan pair and the immediate dispatcher, Markdown,
      trace, status, and evidence plumbing needed to clear it. The phase must
      not introduce a new blanket `plans/phase-plan-*.md` exemption beyond
      the pre-existing generic lightweight phase-plan naming rule.
- [ ] IF-0-SEMLEGACYPLANS-3 - Lexical discoverability contract:
      both exact phase-plan files remain lexically discoverable after the
      repair, including durable file storage plus bounded title and heading
      discoverability for the modern frontmatter-backed `WATCH` plan and the
      legacy `p19` document shape instead of turning either plan into an
      indexing blind spot.
- [ ] IF-0-SEMLEGACYPLANS-4 - Durable trace and operator contract:
      `force_full_exit_trace.json` and `uv run mcp-index repository status`
      stay aligned with the repaired outcome for the exact historical
      phase-plan pair and do not regress to stale SEMPHASETAIL-only wording
      once the live rerun advances past it.
- [ ] IF-0-SEMLEGACYPLANS-5 - Evidence and downstream steering contract:
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the SEMPHASETAIL
      rerun outcome, the SEMLEGACYPLANS rerun command and timestamps, the
      refreshed trace and status output, and the final authoritative verdict
      for the historical phase-plan pair; if execution reveals a blocker
      beyond the current roadmap tail, `specs/phase-plans-v7.md` is amended
      before closeout so the next phase-loop step is truthful.

## Lane Index & Dependencies

- SL-0 - Exact historical phase-plan fixture freeze; Depends on: SEMPHASETAIL; Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 - Bounded historical phase-plan markdown execution-path repair; Depends on: SL-0; Blocks: SL-2, SL-3, SL-4; Parallel-safe: no
- SL-2 - Durable trace persistence and operator boundary alignment; Depends on: SL-0, SL-1; Blocks: SL-3, SL-4; Parallel-safe: no
- SL-3 - Live rerun evidence reducer and contract refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SL-4; Parallel-safe: no
- SL-4 - Downstream roadmap steering reducer; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: SEMLEGACYPLANS acceptance; Parallel-safe: no

Lane DAG:

```text
SEMPHASETAIL
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SL-4 -> SEMLEGACYPLANS acceptance
```

## Lanes

### SL-0 - Exact Historical Phase-Plan Fixture Freeze

- **Scope**: Freeze the exact
  `plans/phase-plan-v6-WATCH.md ->
  plans/phase-plan-v1-p19.md` lexical seam in deterministic dispatcher
  coverage before runtime changes so this phase proves a narrow recovery
  instead of hand-waving around the generic phase-plan family.
- **Owned files**: `tests/test_dispatcher.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMLEGACYPLANS-1,
  IF-0-SEMLEGACYPLANS-2,
  and IF-0-SEMLEGACYPLANS-3 at the dispatcher and plugin boundary
- **Interfaces consumed**: existing
  `Dispatcher.index_directory(...)`,
  `MarkdownPlugin._resolve_lightweight_reason(...)`,
  `MarkdownPlugin.indexFile(...)`,
  the current bounded Markdown routing for roadmap and phase-plan stems,
  and the SEMPHASETAIL evidence for the historical phase-plan pair
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` with a repo-shaped fixture that
    indexes exact copies or trimmed representatives of
    `plans/phase-plan-v6-WATCH.md` and `plans/phase-plan-v1-p19.md`, proves
    the lexical walker records the exact pair in order, and fails if the
    repair silently turns them into an untracked blind spot.
  - test: In the same dispatcher coverage, assert that the repaired path
    keeps document-level and heading-level discoverability for both plans,
    including legacy `p19` heading extraction that does not depend on modern
    phase-loop frontmatter.
  - test: Add a negative guard that an unrelated historical or modern
    phase-plan Markdown document outside the exact pair still uses the normal
    generic lightweight-name rule or heavy Markdown path as appropriate; the
    watchdog repair must not quietly become a broader `plans/phase-plan-*.md`
    fast path.
  - impl: Keep fixtures deterministic with repo-local Markdown strings and
    monkeypatched bounded-path instrumentation rather than long-running live
    waits inside unit tests.
  - impl: Keep this lane on contract freeze only. Do not mutate durable
    trace, CLI wording, evidence docs, or roadmap steering here.
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "phase_plan or WATCH or p19 or markdown or lexical or bounded"`

### SL-1 - Bounded Historical Phase-Plan Markdown Execution-Path Repair

- **Scope**: Implement the smallest dispatcher or Markdown-path repair needed
  so the live lexical walker no longer burns its watchdog budget on the exact
  `phase-plan-v6-WATCH.md -> phase-plan-v1-p19.md` pair.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `mcp_server/plugins/markdown_plugin/plugin.py`
- **Interfaces provided**: IF-0-SEMLEGACYPLANS-2 exact boundary contract;
  IF-0-SEMLEGACYPLANS-3 lexical discoverability contract
- **Interfaces consumed**: SL-0 historical phase-plan fixtures; existing
  bounded Markdown routing in `MarkdownPlugin._resolve_lightweight_reason(...)`;
  the current single-file `index_file(...)` lexical path in
  `dispatcher_enhanced.py`; and existing bounded Markdown persistence
  semantics already used for roadmap, changelog, analysis, AGENTS, README,
  validation, benchmark, `.claude` command, and later phase-plan documents
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 dispatcher slice first and confirm what still makes
    the exact historical pair expensive in the current force-full path even
    though both stems are phase-plan Markdown documents.
  - impl: Apply the narrowest repair that clears the exact pair. Prefer
    reusing the existing bounded Markdown document and heading extraction
    path; only add exact-path or legacy-shape logic if the tests prove the
    generic phase-plan rule is still insufficient for this historical pair in
    the live walker.
  - impl: Preserve frontmatter-derived title handling for `WATCH`, heading
    discoverability for `p19`, and file-level lexical storage for both exact
    plans. The repair must not reduce the pair to empty opaque files.
  - impl: Do not introduce a new blanket `plans/phase-plan-*.md` dispatcher
    bypass, and do not widen into a repo-wide Markdown timeout change that
    masks other later blockers.
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "phase_plan or WATCH or p19 or markdown or bounded"`

### SL-2 - Durable Trace Persistence And Operator Boundary Alignment

- **Scope**: Carry the bounded historical phase-plan repair through durable
  trace persistence and operator status output so the live rerun truthfully
  advances beyond the pair without stale SEMPHASETAIL-only boundary wording.
- **Owned files**: `mcp_server/storage/git_index_manager.py`, `mcp_server/cli/repository_commands.py`, `tests/test_git_index_manager.py`, `tests/test_repository_commands.py`
- **Interfaces provided**: IF-0-SEMLEGACYPLANS-1 historical phase-plan pair
  advance contract; IF-0-SEMLEGACYPLANS-4 durable trace and operator
  contract
- **Interfaces consumed**: SL-0 dispatcher fixtures; SL-1 repaired bounded
  Markdown behavior; existing `GitAwareIndexManager._full_index(...)`,
  `GitAwareIndexManager.sync_repository_index(...)`,
  `_print_force_full_exit_trace(...)`, and current exact-boundary status
  helpers for validation docs, benchmark docs, `.claude/commands`, scripts,
  JSON seams, ignored `test_workspace/`, and the repaired later phase-plan
  seams
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_git_index_manager.py` so force-full durable
    trace persistence freezes the exact historical phase-plan handoff and
    proves later reruns do not regress to stale
    `plans/phase-plan-v7-SEMSYNCFIX.md ->
    plans/phase-plan-v7-SEMVISUALREPORT.md` or SEMPHASETAIL wording once
    execution advances past the current pair.
  - test: Extend `tests/test_repository_commands.py` so
    `uv run mcp-index repository status` must advertise the exact historical
    Markdown boundary
    `plans/phase-plan-v6-WATCH.md -> plans/phase-plan-v1-p19.md` when both
    files exist and the durable trace has already advanced into or beyond
    that pair.
  - impl: Add the smallest boundary-printer and durable-trace alignment
    needed for the exact historical pair beside the existing validation,
    benchmark, `.claude`, script, JSON, and later phase-plan helpers.
  - impl: Preserve the current trace vocabulary fields `Trace status`,
    `Trace stage`, `Trace stage family`, `Trace blocker source`,
    `last_progress_path`, and `in_flight_path`; this lane should only align
    them with the repaired historical phase-plan pair outcome.
  - impl: Do not generalize status wording into all historical plan docs or a
    generic Markdown fast-path claim; the operator surface should stay exact.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "phase_plan or WATCH or p19 or lexical or interrupted or boundary"`

### SL-3 - Live Rerun Evidence Reducer And Contract Refresh

- **Scope**: Re-run the repaired repo-local force-full sequence and reduce the
  outcome into the durable semantic dogfood evidence artifact.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: IF-0-SEMLEGACYPLANS-1 historical phase-plan pair
  advance contract; IF-0-SEMLEGACYPLANS-4 durable trace and operator
  contract; the evidence portion of IF-0-SEMLEGACYPLANS-5
- **Interfaces consumed**: SL-0 historical phase-plan fixtures; SL-1 repaired
  dispatcher and Markdown behavior; SL-2 durable trace and status wording;
  the current SEMPHASETAIL evidence block; and the live repo-local
  `force_full_exit_trace.json`, `repository status`, and SQLite runtime
  counts after the refreshed rerun
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/docs/test_semdogfood_evidence_contract.py` so the
    evidence artifact must retain the exact historical phase-plan pair, the
    SEMLEGACYPLANS rerun command, the refreshed trace and status fields, the
    current phase-plan reference, the prior phase-plan reference, and the
    final verdict on whether the active blocker moved beyond
    `plans/phase-plan-v1-p19.md`.
  - impl: Refresh `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` with the
    SEMPHASETAIL observed historical phase-plan blocker, the repaired
    SEMLEGACYPLANS rerun command and timestamps, the resulting durable trace
    snapshot, the matching `repository status` output, and the final call on
    whether the active blocker advanced beyond the exact pair.
  - impl: Keep the evidence truthful about lexical-only progress.
    `chunk_summaries` and `semantic_points` may remain zero here; do not
    imply semantic closeout unless the rerun actually leaves lexical walking.
  - impl: If the refreshed rerun exposes a newer blocker, record the exact
    new blocker and stop treating older downstream assumptions as
    authoritative.
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
  - verify: `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - verify: `sed -n '1,240p' .mcp-index/force_full_exit_trace.json`
  - verify: `sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'`

### SL-4 - Downstream Roadmap Steering Reducer

- **Scope**: Keep the roadmap and next phase-loop step truthful if the
  repaired live rerun proves a newer blocker beyond the current roadmap tail.
- **Owned files**: `specs/phase-plans-v7.md`
- **Interfaces provided**: the downstream-steering portion of
  IF-0-SEMLEGACYPLANS-5
- **Interfaces consumed**: SL-3 refreshed evidence verdict; current roadmap
  DAG and phase ordering for `specs/phase-plans-v7.md`; canonical
  `.phase-loop/` expectation that the next unplanned phase reflects the
  latest durable blocker rather than stale prior assumptions
- **Parallel-safe**: no
- **Tasks**:
  - test: Re-read the post-SL-3 evidence and confirm whether the repaired
    rerun actually exposes a newer blocker beyond the current roadmap tail
    before mutating roadmap steering.
  - impl: If the active blocker is still the exact historical phase-plan
    pair, leave the roadmap unchanged.
  - impl: If the active blocker advances beyond the pair and no downstream
    phase already covers it, append the nearest truthful downstream recovery
    phase to `specs/phase-plans-v7.md` with the same evidence-first structure
    used by the current SEM* lexical-recovery chain.
  - impl: Keep any roadmap mutation limited to the newly exposed blocker.
    Do not rewrite earlier phases or backfill unrelated sequencing while
    closing this seam.
  - verify: `git diff -- specs/phase-plans-v7.md`

## Verification

- Lane checks:
  - `uv run pytest tests/test_dispatcher.py -q --no-cov -k "phase_plan or WATCH or p19 or markdown or lexical or bounded"`
  - `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "phase_plan or WATCH or p19 or lexical or interrupted or boundary"`
  - `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
- Whole-phase checks:
  - `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_repository_commands.py tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "phase_plan or WATCH or p19 or markdown or lexical or bounded or interrupted or boundary"`
  - `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  - `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - `sed -n '1,240p' .mcp-index/force_full_exit_trace.json`
  - `sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'`
  - `git diff --check`
  - `git diff --cached --check`

## Acceptance Criteria

- [ ] A refreshed repo-local force-full rerun on the post-SEMPHASETAIL head
      either advances durably beyond
      `plans/phase-plan-v6-WATCH.md ->
      plans/phase-plan-v1-p19.md` or emits a truthful newer blocker before
      the 120-second watchdog expires.
- [ ] The repair stays narrowly scoped to the exact historical phase-plan
      pair and the immediate dispatcher, Markdown, trace, status, evidence,
      and roadmap-steering plumbing needed to prove it.
- [ ] Both exact phase-plan files remain lexically discoverable with durable
      file storage plus bounded title and heading discoverability, including
      legacy `p19` heading extraction that does not depend on phase-loop
      frontmatter.
- [ ] `uv run mcp-index repository status` and
      `force_full_exit_trace.json` stay aligned with the repaired historical
      phase-plan boundary outcome and do not regress to stale SEMPHASETAIL
      wording.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the SEMPHASETAIL
      rerun outcome and the final live verdict for the historical phase-plan
      pair.
- [ ] If execution reveals a newer blocker beyond the current roadmap tail,
      `specs/phase-plans-v7.md` is updated before closeout so the next
      phase-loop step is truthful.

automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMLEGACYPLANS.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMLEGACYPLANS.md
  artifact_state: staged
