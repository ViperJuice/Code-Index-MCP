---
phase_loop_plan_version: 1
phase: SEMCROSSDOGTAIL
roadmap: specs/phase-plans-v7.md
roadmap_sha256: 6d45ca93078443ae23ab70506da44916ae34c64b49b6ec975b49c0b0ba0fb232
---
# SEMCROSSDOGTAIL: Crossplans Dogfood Tail Recovery

## Context

SEMCROSSDOGTAIL is the phase-66 follow-up for the v7 semantic hardening
roadmap. Canonical `.phase-loop/` state is authoritative for this run, and
legacy `.codex/phase-loop/` artifacts remain compatibility-only. The current
`.phase-loop/` handoff still reports `SEMJEDIP4TAIL` as `blocked` because the
latest execute turn left unrelated runtime artifacts dirty, but the same
canonical state already records `SEMCROSSDOGTAIL` as the next `unplanned`
downstream phase and the repo-local evidence artifact shows that
SEMJEDIP4TAIL cleared its named `SEMJEDI -> p4` seam and advanced the live
force-full rerun later to the modern v7 phase-plan pair
`plans/phase-plan-v7-SEMCROSSPLANS.md ->
plans/phase-plan-v7-SEMDOGFOOD.md`. This planning artifact freezes that later
seam so the next execution slice can stay narrow and evidence-driven.

Current repo state gathered during planning:

- Canonical `.phase-loop/state.json` and `.phase-loop/tui-handoff.md` record
  `roadmap = specs/phase-plans-v7.md`, the required roadmap hash
  `6d45ca93078443ae23ab70506da44916ae34c64b49b6ec975b49c0b0ba0fb232`, and a
  late-run state where `SEMJEDIP4TAIL` is blocked by
  `dirty_worktree_conflict` while `SEMCROSSDOGTAIL` remains `unplanned`.
- `sha256sum specs/phase-plans-v7.md` currently matches the required
  `6d45ca93078443ae23ab70506da44916ae34c64b49b6ec975b49c0b0ba0fb232`.
- Live git topology at planning time is `main...origin/main [ahead 126]` on
  `HEAD` `404664a14acb6783a337113c77a38a2b7977c209`, and the worktree is not
  clean because the latest SEMJEDIP4TAIL execute run left both phase-owned
  edits and unrelated runtime artifacts in place.
- The target artifact `plans/phase-plan-v7-SEMCROSSDOGTAIL.md` did not exist
  before this planning run.
- The current canonical blocker is not a planning blocker. The runner reports
  unowned dirty runtime artifacts
  `.index_metadata.json`,
  `.mcp-index/force_full_exit_trace.json`,
  `.mcp-index/semantic_qdrant/.lock`,
  and `.mcp-index/semantic_qdrant/meta.json`. This phase plan should not try
  to clean or normalize them, but SEMCROSSDOGTAIL execution must preserve or
  isolate them before a new autonomous rerun is treated as closeout-safe.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is the active evidence anchor. Its
  `SEMJEDIP4TAIL Live Rerun Check` block records that the refreshed repo-local
  command
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  started on observed commit `404664a1`, remained a running lexical snapshot
  at `2026-04-29T20:58:32Z` with
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMCROSSPLANS.md`
  and
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMDOGFOOD.md`,
  and then terminalized at `2026-04-29T20:58:40Z` to `Trace status:
  interrupted` with the same exact pair.
- The SEMJEDIP4TAIL target pair is no longer the active blocker:
  `plans/phase-plan-v7-SEMJEDI.md ->
  plans/phase-plan-v1-p4.md`. Older downstream assumptions that still treat
  that mixed-generation seam as current should be considered stale.
- The newly exposed pair is modern v7-only rather than mixed-generation or
  historical. `plans/phase-plan-v7-SEMCROSSPLANS.md` is `353` lines /
  `20947` bytes and `plans/phase-plan-v7-SEMDOGFOOD.md` is `320` lines /
  `17499` bytes. Both are modern phase-loop plans with YAML frontmatter,
  execution-ready lane headings, verification sections, acceptance criteria,
  and automation handoffs.
- `MarkdownPlugin._resolve_lightweight_reason(...)` already routes both stems
  through bounded Markdown handling because `_ROADMAP_MARKDOWN_NAME_RE`
  matches `phase-plan-v7-SEMCROSSPLANS` and `phase-plan-v7-SEMDOGFOOD`. The
  plugin also carries exact bounded-path entries for earlier repaired pairs
  such as `plans/phase-plan-v7-SEMJEDI.md ->
  plans/phase-plan-v1-p4.md`, but there is no exact-path or pair-specific
  contract yet for the later modern v7-only
  `plans/phase-plan-v7-SEMCROSSPLANS.md ->
  plans/phase-plan-v7-SEMDOGFOOD.md` seam.
- `mcp_server/cli/repository_commands.py` currently advertises exact bounded
  lexical boundaries for multiple earlier seams, including the repaired
  `SEMJEDI -> p4` pair, but it does not yet expose a dedicated operator
  boundary for the later `SEMCROSSPLANS -> SEMDOGFOOD` seam.
- Existing tests already freeze adjacent behavior but not the exact
  SEMCROSSDOGTAIL contract. `tests/test_dispatcher.py` covers historical,
  mixed-version, and earlier modern phase-plan seams;
  `tests/test_git_index_manager.py` and `tests/test_repository_commands.py`
  preserve durable trace and operator wording for those earlier boundaries;
  and `tests/docs/test_semdogfood_evidence_contract.py` already requires the
  evidence report to mention `plans/phase-plan-v7-SEMCROSSPLANS.md`,
  `plans/phase-plan-v7-SEMDOGFOOD.md`, and roadmap steering to
  `SEMCROSSDOGTAIL`. What is missing is the execution-ready contract that
  binds dispatcher behavior, durable trace progression, operator wording,
  evidence refresh, and possible downstream roadmap steering to this exact
  later modern-v7 seam.

Practical planning boundary:

- SEMCROSSDOGTAIL may tighten exact modern v7 phase-plan handling,
  dispatcher lexical progress accounting, durable trace persistence, operator
  status wording, the semantic dogfood evidence artifact, and downstream
  roadmap steering needed to prove a live rerun either advances beyond
  `plans/phase-plan-v7-SEMCROSSPLANS.md ->
  plans/phase-plan-v7-SEMDOGFOOD.md` or surfaces a truthful newer blocker.
- SEMCROSSDOGTAIL must stay narrow and evidence-driven. It must not reopen the
  repaired SEMJEDIP4TAIL mixed-generation seam, introduce a blanket
  `plans/phase-plan-v7-*.md` bypass, retune the repo-wide lexical watchdog, or
  reopen unrelated roadmap, evidence, query, or semantic-onboarding artifacts
  unless the refreshed rerun re-anchors there directly.
- SEMCROSSDOGTAIL execution should preserve the current unrelated dirty
  runtime artifacts rather than attempting cleanup inside this phase. If the
  live rerun cannot be closed out safely without isolating those paths, that
  should be reported as an execution-time blocker instead of widened planning
  scope.

## Interface Freeze Gates

- [ ] IF-0-SEMCROSSDOGTAIL-1 - SEMCROSSPLANS/SEMDOGFOOD pair advance contract:
      a refreshed repo-local force-full rerun on the post-SEMJEDIP4TAIL head
      no longer terminalizes with the durable lexical trace centered on
      `plans/phase-plan-v7-SEMCROSSPLANS.md ->
      plans/phase-plan-v7-SEMDOGFOOD.md`; it either advances durably beyond
      that pair or emits a truthful newer blocker before the 120-second
      watchdog expires.
- [ ] IF-0-SEMCROSSDOGTAIL-2 - Exact boundary contract:
      any repair introduced by this phase remains limited to the exact
      `SEMCROSSPLANS -> SEMDOGFOOD` phase-plan pair and the immediate
      dispatcher, Markdown, trace, status, evidence, and roadmap-steering
      plumbing needed to clear it. The phase must not introduce a new blanket
      `plans/phase-plan-v7-*.md` lexical bypass.
- [ ] IF-0-SEMCROSSDOGTAIL-3 - Lexical discoverability contract:
      both exact phase-plan files remain lexically discoverable after the
      repair, including durable file storage plus bounded title and heading
      discoverability for the modern phase-loop frontmatter, lane headings,
      verification sections, and acceptance or automation structure instead of
      turning either plan into an indexing blind spot.
- [ ] IF-0-SEMCROSSDOGTAIL-4 - Durable trace and operator contract:
      `force_full_exit_trace.json` and `uv run mcp-index repository status`
      stay aligned with the repaired outcome for the exact
      `plans/phase-plan-v7-SEMCROSSPLANS.md ->
      plans/phase-plan-v7-SEMDOGFOOD.md` pair and do not regress to stale
      SEMJEDIP4TAIL-only wording once the live rerun advances beyond it.
- [ ] IF-0-SEMCROSSDOGTAIL-5 - Evidence and downstream steering contract:
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the SEMJEDIP4TAIL
      rerun outcome, the SEMCROSSDOGTAIL rerun command and timestamps, the
      refreshed trace and status output, and the final authoritative verdict
      for the later modern v7 phase-plan pair; if execution reveals a blocker
      beyond the current roadmap tail, `specs/phase-plans-v7.md` is amended
      before closeout so the next phase-loop step is truthful.

## Lane Index & Dependencies

- SL-0 - Exact SEMCROSSPLANS/SEMDOGFOOD phase-plan fixture freeze; Depends on: SEMJEDIP4TAIL; Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 - Bounded SEMCROSSPLANS/SEMDOGFOOD execution-path repair or minimal plan-local simplification; Depends on: SL-0; Blocks: SL-2, SL-3, SL-4; Parallel-safe: no
- SL-2 - Durable trace persistence and operator boundary alignment; Depends on: SL-0, SL-1; Blocks: SL-3, SL-4; Parallel-safe: no
- SL-3 - Live rerun evidence reducer and SEMCROSSDOGTAIL contract refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SL-4; Parallel-safe: no
- SL-4 - Downstream roadmap steering reducer; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: SEMCROSSDOGTAIL acceptance; Parallel-safe: no

Lane DAG:

```text
SEMJEDIP4TAIL
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SL-4 -> SEMCROSSDOGTAIL acceptance
```

## Lanes

### SL-0 - Exact SEMCROSSPLANS/SEMDOGFOOD Phase-Plan Fixture Freeze

- **Scope**: Freeze the exact
  `plans/phase-plan-v7-SEMCROSSPLANS.md ->
  plans/phase-plan-v7-SEMDOGFOOD.md` lexical seam in deterministic dispatcher
  coverage before runtime changes so this phase proves a narrow recovery
  instead of assuming the generic modern-v7 phase-plan family is already
  sufficient.
- **Owned files**: `tests/test_dispatcher.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMCROSSDOGTAIL-1,
  IF-0-SEMCROSSDOGTAIL-2,
  and IF-0-SEMCROSSDOGTAIL-3 at the dispatcher/plugin boundary
- **Interfaces consumed**: existing
  `Dispatcher.index_directory(...)`,
  `MarkdownPlugin._resolve_lightweight_reason(...)`,
  `MarkdownPlugin.indexFile(...)`,
  the current bounded Markdown routing for roadmap and phase-plan stems,
  and the SEMJEDIP4TAIL evidence for the later modern-v7 phase-plan pair
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` with a repo-shaped fixture that
    indexes exact copies or trimmed representatives of
    `plans/phase-plan-v7-SEMCROSSPLANS.md` and
    `plans/phase-plan-v7-SEMDOGFOOD.md`, proves the lexical walker records the
    exact pair in order, and fails if the repair silently turns them into an
    untracked blind spot.
  - test: In the same dispatcher coverage, assert that the repaired path keeps
    document-level and heading-level discoverability for both plans, including
    modern phase-loop frontmatter, lane headings, verification sections, and
    acceptance or automation structure that do not depend on widening into a
    blanket v7 plan bypass.
  - test: Add a negative guard that an unrelated modern or mixed-generation
    phase-plan Markdown document outside the exact pair still uses the normal
    generic lightweight-name rule or heavy Markdown path as appropriate; the
    watchdog repair must not quietly become a broader `plans/phase-plan-v7-*`
    fast path.
  - impl: Keep fixtures deterministic with repo-local Markdown strings and
    monkeypatched bounded-path instrumentation rather than long-running live
    waits inside unit tests.
  - impl: Keep this lane on contract freeze only. Do not mutate durable trace,
    CLI wording, evidence docs, roadmap steering, or the phase-plan source
    files here.
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "phase_plan or SEMCROSSPLANS or SEMDOGFOOD or markdown or lexical or bounded"`

### SL-1 - Bounded SEMCROSSPLANS/SEMDOGFOOD Execution-Path Repair Or Minimal Plan-Local Simplification

- **Scope**: Implement the smallest dispatcher or Markdown-path repair needed
  so the live lexical walker no longer burns its watchdog budget on the exact
  `plans/phase-plan-v7-SEMCROSSPLANS.md ->
  plans/phase-plan-v7-SEMDOGFOOD.md` pair.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `mcp_server/plugins/markdown_plugin/plugin.py`, `plans/phase-plan-v7-SEMCROSSPLANS.md`, `plans/phase-plan-v7-SEMDOGFOOD.md`
- **Interfaces provided**: IF-0-SEMCROSSDOGTAIL-2 exact boundary contract;
  IF-0-SEMCROSSDOGTAIL-3 lexical discoverability contract
- **Interfaces consumed**: SL-0 SEMCROSSPLANS/SEMDOGFOOD fixtures; existing
  bounded Markdown routing in `MarkdownPlugin._resolve_lightweight_reason(...)`;
  the current single-file lexical path in `dispatcher_enhanced.py`; and the
  current structure of `plans/phase-plan-v7-SEMCROSSPLANS.md` and
  `plans/phase-plan-v7-SEMDOGFOOD.md`
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 dispatcher slice first and confirm what still makes the
    exact modern-v7 pair expensive in the current force-full path even though
    both stems already match the generic roadmap or phase-plan rule.
  - impl: Apply the narrowest repair that clears the exact pair. Prefer
    reusing the existing bounded Markdown document and heading extraction path;
    only add exact-path or plan-shape logic if the tests prove the generic
    phase-plan rule is still insufficient for this
    `SEMCROSSPLANS -> SEMDOGFOOD` seam in the live walker.
  - impl: If a plan-local simplification is necessary, keep it exact to
    `plans/phase-plan-v7-SEMCROSSPLANS.md` and
    `plans/phase-plan-v7-SEMDOGFOOD.md`. Preserve current planning meaning and
    keep the edits lexical-structure-oriented rather than rewriting the plan
    contents or changing phase-loop frontmatter.
  - impl: Preserve stored file rows plus document and heading discoverability
    for both plans; the repair must not turn either file into an ignored
    source document or silently remove it from lexical FTS.
  - impl: Keep the repair exact-file or exact-pair narrow. Do not add a broad
    `plans/phase-plan-v7-*.md` or repository-wide Markdown chunking bypass.
  - verify: `rg -n "phase-plan-v7-SEMCROSSPLANS|phase-plan-v7-SEMDOGFOOD|_ROADMAP_MARKDOWN_NAME_RE|_EXACT_BOUNDED_MARKDOWN_PATHS|index_file|lightweight" mcp_server/dispatcher/dispatcher_enhanced.py mcp_server/plugins/markdown_plugin/plugin.py plans/phase-plan-v7-SEMCROSSPLANS.md plans/phase-plan-v7-SEMDOGFOOD.md tests/test_dispatcher.py`
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "phase_plan or SEMCROSSPLANS or SEMDOGFOOD or markdown or lexical or bounded"`

### SL-2 - Durable Trace Persistence And Operator Boundary Alignment

- **Scope**: Carry the chosen SEMCROSSPLANS/SEMDOGFOOD repair through
  force-full closeout and keep the operator-facing status surface aligned with
  the exact later pair that was repaired.
- **Owned files**: `mcp_server/storage/git_index_manager.py`, `mcp_server/cli/repository_commands.py`, `tests/test_git_index_manager.py`, `tests/test_repository_commands.py`
- **Interfaces provided**: IF-0-SEMCROSSDOGTAIL-1 SEMCROSSPLANS/SEMDOGFOOD
  pair advance contract; IF-0-SEMCROSSDOGTAIL-4 durable trace and operator
  contract
- **Interfaces consumed**: SL-0 dispatcher fixtures; SL-1 chosen repair;
  existing lexical progress snapshot fields, durable
  `force_full_exit_trace.json` persistence, and the current status wording for
  the repaired `SEMJEDI -> p4` seam and earlier lexical boundaries
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_git_index_manager.py` so force-full durable trace
    coverage preserves the exact
    `plans/phase-plan-v7-SEMCROSSPLANS.md ->
    plans/phase-plan-v7-SEMDOGFOOD.md` pair when that seam is still active,
    then proves the trace advances beyond both files once the repair is in
    place without regressing to stale
    `plans/phase-plan-v7-SEMJEDI.md ->
    plans/phase-plan-v1-p4.md` wording.
  - test: Extend `tests/test_repository_commands.py` so
    `uv run mcp-index repository status` continues to render the existing
    repaired lexical boundaries while adding truthful operator guidance for the
    later `plans/phase-plan-v7-SEMCROSSPLANS.md ->
    plans/phase-plan-v7-SEMDOGFOOD.md` seam.
  - impl: Thread the chosen repair through durable trace persistence and
    operator wording only as needed so the rerun can advance beyond the exact
    pair.
  - impl: Preserve the existing force-full trace fields, fail-closed indexed
    commit behavior, and lexical watchdog semantics. This lane should move the
    handoff forward, not rename stages or declare readiness early.
  - impl: If SL-1 alone is sufficient and no runtime storage change is
    required, keep this lane scoped to status wording plus trace fixtures
    rather than inventing extra persistence behavior.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "phase_plan or SEMCROSSPLANS or SEMDOGFOOD or lexical or interrupted or boundary"`

### SL-3 - Live Rerun Evidence Reducer And SEMCROSSDOGTAIL Contract Refresh

- **Scope**: Refresh the repo-local dogfood report so it records the chosen
  SEMCROSSPLANS/SEMDOGFOOD repair, the rerun outcome, and the next exact
  downstream status after this modern-v7 seam is cleared.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: IF-0-SEMCROSSDOGTAIL-4 durable trace and operator
  contract; IF-0-SEMCROSSDOGTAIL-5 evidence and downstream steering contract
- **Interfaces consumed**: SL-1 chosen repair; SL-2 rerun command, durable
  trace, and repository-status wording; roadmap SEMCROSSDOGTAIL exit criteria;
  prior SEMJEDIP4TAIL evidence lineage
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/docs/test_semdogfood_evidence_contract.py` so the
    refreshed report cites
    `plans/phase-plan-v7-SEMCROSSPLANS.md`,
    `plans/phase-plan-v7-SEMDOGFOOD.md`,
    the chosen repair, the rerun outcome, and the final authoritative verdict
    for the later modern-v7 phase-plan pair.
  - test: Require the report to preserve the existing evidence lineage for the
    already cleared `SEMJEDI -> p4` seam while making clear that the active
    current-head blocker has moved later to
    `SEMCROSSPLANS -> SEMDOGFOOD` or beyond.
  - impl: Update `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` with the live
    SEMCROSSDOGTAIL rerun command, timestamps, refreshed trace snapshot,
    repository-status terminalization, and current SQLite counts so the report
    proves whether the repaired rerun advanced beyond the pair or surfaced a
    newer blocker.
  - impl: Keep the evidence truthful about lexical-only progress.
    `chunk_summaries` and `semantic_points` may remain zero here; do not imply
    semantic closeout unless the rerun actually leaves lexical walking.
  - impl: If the refreshed rerun exposes a newer blocker, record the exact new
    blocker and stop treating older downstream assumptions as authoritative.
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
  IF-0-SEMCROSSDOGTAIL-5
- **Interfaces consumed**: SL-3 refreshed evidence verdict; current roadmap
  DAG and phase ordering for `specs/phase-plans-v7.md`; canonical
  `.phase-loop/` expectation that the next unplanned phase reflects the latest
  durable blocker rather than stale prior assumptions
- **Parallel-safe**: no
- **Tasks**:
  - test: Re-read the post-SL-3 evidence and confirm whether the repaired
    rerun actually exposes a newer blocker beyond the current roadmap tail
    before mutating roadmap steering.
  - impl: If the active blocker is still the exact
    `SEMCROSSPLANS -> SEMDOGFOOD` pair, leave the roadmap unchanged.
  - impl: If the active blocker advances beyond the pair and no downstream
    phase already covers it, append the nearest truthful downstream recovery
    phase to `specs/phase-plans-v7.md` with the same evidence-first structure
    used by the current SEM* lexical-recovery chain.
  - impl: Keep any roadmap mutation limited to the newly exposed blocker. Do
    not rewrite earlier phases or backfill unrelated sequencing while closing
    this seam.
  - verify: `git diff -- specs/phase-plans-v7.md`

## Verification

- Lane checks:
  - `uv run pytest tests/test_dispatcher.py -q --no-cov -k "phase_plan or SEMCROSSPLANS or SEMDOGFOOD or markdown or lexical or bounded"`
  - `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "phase_plan or SEMCROSSPLANS or SEMDOGFOOD or lexical or interrupted or boundary"`
  - `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
- Whole-phase checks:
  - `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_repository_commands.py tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "phase_plan or SEMCROSSPLANS or SEMDOGFOOD or markdown or lexical or bounded or interrupted or boundary"`
  - `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  - `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - `sed -n '1,240p' .mcp-index/force_full_exit_trace.json`
  - `sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'`
  - `git diff --check`
  - `git diff --cached --check`

## Acceptance Criteria

- [ ] A refreshed repo-local force-full rerun on the post-SEMJEDIP4TAIL head
      either advances durably beyond
      `plans/phase-plan-v7-SEMCROSSPLANS.md ->
      plans/phase-plan-v7-SEMDOGFOOD.md` or emits a truthful newer blocker
      before the 120-second watchdog expires.
- [ ] The repair stays narrowly scoped to the exact modern-v7 phase-plan pair
      and the immediate dispatcher/Markdown/trace/status/evidence plumbing
      needed to prove it.
- [ ] The chosen repair does not reopen the repaired
      `plans/phase-plan-v7-SEMJEDI.md ->
      plans/phase-plan-v1-p4.md` boundary without direct new evidence.
- [ ] Both exact phase-plan files remain lexically discoverable with durable
      file storage plus bounded document and heading discoverability,
      including phase-loop frontmatter, lane headings, verification sections,
      and acceptance or automation structure.
- [ ] `uv run mcp-index repository status` and
      `force_full_exit_trace.json` stay aligned with the repaired
      modern-v7 phase-plan boundary outcome and do not regress to stale
      SEMJEDIP4TAIL wording.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the SEMJEDIP4TAIL
      rerun outcome and the final live verdict for the later
      `plans/phase-plan-v7-SEMCROSSPLANS.md ->
      plans/phase-plan-v7-SEMDOGFOOD.md` phase-plan pair.
- [ ] If execution reveals a newer blocker beyond the current roadmap tail,
      `specs/phase-plans-v7.md` is updated before closeout so the next
      phase-loop step is truthful.

automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMCROSSDOGTAIL.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMCROSSDOGTAIL.md
  artifact_state: staged
