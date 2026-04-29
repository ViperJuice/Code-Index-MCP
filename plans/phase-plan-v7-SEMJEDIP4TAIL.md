---
phase_loop_plan_version: 1
phase: SEMJEDIP4TAIL
roadmap: specs/phase-plans-v7.md
roadmap_sha256: 84d9995263b877a02111bc404c58a0d8c87e6dfcced929756d3ffb7d8824c5e2
---
# SEMJEDIP4TAIL: SEMJEDI/P4 Tail Recovery

## Context

SEMJEDIP4TAIL is the phase-65 follow-up for the v7 semantic hardening
roadmap. Canonical `.phase-loop/` state is authoritative for this run, and
legacy `.codex/phase-loop/` artifacts remain compatibility-only. The current
`.phase-loop/` handoff still reports `SEMV1PLANTAIL` as `blocked` from the
latest execute run, but the repo-local evidence artifact already shows that
SEMV1PLANTAIL cleared its named historical-v1 seam and that the refreshed live
force-full rerun advanced later to the mixed-generation phase-plan pair
`plans/phase-plan-v7-SEMJEDI.md ->
plans/phase-plan-v1-p4.md`. This planning artifact freezes that later seam so
the next execution slice can stay narrow and evidence-driven.

Current repo state gathered during planning:

- Canonical `.phase-loop/state.json` and `.phase-loop/tui-handoff.md` record
  `roadmap = specs/phase-plans-v7.md`, `phase = SEMJEDIP4TAIL`, and the
  required roadmap hash
  `84d9995263b877a02111bc404c58a0d8c87e6dfcced929756d3ffb7d8824c5e2`.
- `specs/phase-plans-v7.md` currently hashes to that exact required value.
- Live git topology at planning time is `main...origin/main [ahead 125]` on
  `HEAD` `d930ebbc3e31d1043dad1b3ad16f9688edf5f059`.
- `plans/phase-plan-v7-SEMJEDIP4TAIL.md` did not exist before this planning
  run.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is the active evidence anchor. Its
  SEMV1PLANTAIL block records that at `2026-04-29T20:38:02Z` the final running
  lexical trace before timeout had advanced to
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMJEDI.md`
  with
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v1-p4.md`,
  and at `2026-04-29T20:38:17Z` `repository status` terminalized that running
  snapshot to `Trace status: interrupted` with the same exact pair.
- The SEMV1PLANTAIL target pair is no longer the active blocker:
  `plans/phase-plan-v1-p13.md ->
  plans/phase-plan-v1-p3.md`. Older downstream assumptions that still treat
  that historical-v1 seam as current should be considered stale.
- The newly exposed pair is mixed-generation rather than pure historical-v1:
  `plans/phase-plan-v7-SEMJEDI.md` is a modern phase-loop plan with YAML
  frontmatter, execution-ready lane headings, and acceptance/automation
  sections, while `plans/phase-plan-v1-p4.md` is a legacy plan with a quoted
  preamble, long context and execution-notes sections, and no modern
  phase-loop frontmatter.
- `MarkdownPlugin._resolve_lightweight_reason(...)` already routes both stems
  through bounded Markdown handling because `_ROADMAP_MARKDOWN_NAME_RE`
  matches `phase-plan-v7-SEMJEDI` and `phase-plan-v1-p4`. The plugin also
  carries exact bounded-path entries for the earlier
  `plans/phase-plan-v1-p13.md ->
  plans/phase-plan-v1-p3.md` and
  `plans/phase-plan-v7-SEMPHASETAIL.md ->
  plans/phase-plan-v5-gagov.md` seams, but there is no exact-path or
  pair-specific contract yet for `plans/phase-plan-v7-SEMJEDI.md ->
  plans/phase-plan-v1-p4.md`.
- `mcp_server/cli/repository_commands.py` currently prints exact bounded
  boundary lines for the repaired support-doc, historical-v1, and
  mixed-version plan pairs, but it does not yet expose a dedicated operator
  boundary for the later `SEMJEDI -> p4` seam.
- Existing tests already freeze adjacent behavior but not the exact
  SEMJEDI/P4 contract. `tests/test_dispatcher.py` covers the historical-v1 and
  mixed-version phase-plan pairs, `tests/test_git_index_manager.py` and
  `tests/test_repository_commands.py` preserve durable trace and operator
  wording for those earlier seams, and
  `tests/docs/test_semdogfood_evidence_contract.py` already requires the
  evidence report to mention `plans/phase-plan-v7-SEMJEDI.md`,
  `plans/phase-plan-v1-p4.md`, and roadmap steering to `SEMJEDIP4TAIL`. What
  is missing is the execution-ready contract that binds dispatcher behavior,
  durable trace progression, operator wording, evidence refresh, and possible
  downstream roadmap steering to this exact later mixed-generation seam.

Practical planning boundary:

- SEMJEDIP4TAIL may tighten exact mixed-generation phase-plan handling,
  dispatcher lexical progress accounting, durable trace persistence, operator
  status wording, the semantic dogfood evidence artifact, and downstream
  roadmap steering needed to prove a live rerun either advances beyond
  `plans/phase-plan-v7-SEMJEDI.md ->
  plans/phase-plan-v1-p4.md` or surfaces a truthful newer blocker.
- SEMJEDIP4TAIL must stay narrow and evidence-driven. It must not reopen the
  repaired SEMV1PLANTAIL historical-v1 seam, introduce a blanket
  `plans/phase-plan-v1-*.md` or `plans/phase-plan-v7-*.md` bypass, retune the
  repo-wide lexical watchdog, or reopen unrelated roadmap, documentation,
  benchmark, or script-language seams unless the refreshed rerun re-anchors
  there directly.

## Interface Freeze Gates

- [ ] IF-0-SEMJEDIP4TAIL-1 - SEMJEDI/P4 pair advance contract:
      a refreshed repo-local force-full rerun on the post-SEMV1PLANTAIL head
      no longer terminalizes with the durable lexical trace centered on
      `plans/phase-plan-v7-SEMJEDI.md ->
      plans/phase-plan-v1-p4.md`; it either advances durably beyond that pair
      or emits a truthful newer blocker before the 120-second watchdog expires.
- [ ] IF-0-SEMJEDIP4TAIL-2 - Exact boundary contract:
      any repair introduced by this phase remains limited to the exact
      `SEMJEDI -> p4` phase-plan pair and the immediate dispatcher, Markdown,
      trace, status, evidence, and roadmap-steering plumbing needed to clear
      it. The phase must not introduce a new blanket
      `plans/phase-plan-v1-*.md` or `plans/phase-plan-v7-*.md` lexical bypass.
- [ ] IF-0-SEMJEDIP4TAIL-3 - Lexical discoverability contract:
      both exact phase-plan files remain lexically discoverable after the
      repair, including durable file storage plus bounded title and heading
      discoverability for the modern `SEMJEDI` frontmatter-and-lanes shape and
      the legacy `p4` quoted-preamble and execution-notes structure instead of
      turning either plan into an indexing blind spot.
- [ ] IF-0-SEMJEDIP4TAIL-4 - Durable trace and operator contract:
      `force_full_exit_trace.json` and `uv run mcp-index repository status`
      stay aligned with the repaired outcome for the exact
      `plans/phase-plan-v7-SEMJEDI.md ->
      plans/phase-plan-v1-p4.md` pair and do not regress to stale
      SEMV1PLANTAIL-only wording once the live rerun advances beyond it.
- [ ] IF-0-SEMJEDIP4TAIL-5 - Evidence and downstream steering contract:
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the SEMV1PLANTAIL
      rerun outcome, the SEMJEDIP4TAIL rerun command and timestamps, the
      refreshed trace and status output, and the final authoritative verdict
      for the later mixed-generation phase-plan pair; if execution reveals a
      blocker beyond the current roadmap tail, `specs/phase-plans-v7.md` is
      amended before closeout so the next phase-loop step is truthful.

## Lane Index & Dependencies

- SL-0 - Exact SEMJEDI/P4 phase-plan fixture freeze; Depends on: SEMV1PLANTAIL; Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 - Bounded SEMJEDI/P4 execution-path repair or minimal plan-local simplification; Depends on: SL-0; Blocks: SL-2, SL-3, SL-4; Parallel-safe: no
- SL-2 - Durable trace persistence and operator boundary alignment; Depends on: SL-0, SL-1; Blocks: SL-3, SL-4; Parallel-safe: no
- SL-3 - Live rerun evidence reducer and SEMJEDIP4TAIL contract refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SL-4; Parallel-safe: no
- SL-4 - Downstream roadmap steering reducer; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: SEMJEDIP4TAIL acceptance; Parallel-safe: no

Lane DAG:

```text
SEMV1PLANTAIL
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SL-4 -> SEMJEDIP4TAIL acceptance
```

## Lanes

### SL-0 - Exact SEMJEDI/P4 Phase-Plan Fixture Freeze

- **Scope**: Freeze the exact
  `plans/phase-plan-v7-SEMJEDI.md ->
  plans/phase-plan-v1-p4.md` lexical seam in deterministic dispatcher
  coverage before runtime changes so this phase proves a narrow recovery
  instead of assuming the generic phase-plan family is already sufficient.
- **Owned files**: `tests/test_dispatcher.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMJEDIP4TAIL-1,
  IF-0-SEMJEDIP4TAIL-2,
  and IF-0-SEMJEDIP4TAIL-3 at the dispatcher/plugin boundary
- **Interfaces consumed**: existing
  `Dispatcher.index_directory(...)`,
  `MarkdownPlugin._resolve_lightweight_reason(...)`,
  `MarkdownPlugin.indexFile(...)`,
  the current bounded Markdown routing for roadmap and phase-plan stems,
  and the SEMV1PLANTAIL evidence for the later mixed-generation phase-plan
  pair
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` with a repo-shaped fixture that
    indexes exact copies or trimmed representatives of
    `plans/phase-plan-v7-SEMJEDI.md` and `plans/phase-plan-v1-p4.md`, proves
    the lexical walker records the exact pair in order, and fails if the
    repair silently turns them into an untracked blind spot.
  - test: In the same dispatcher coverage, assert that the repaired path keeps
    document-level and heading-level discoverability for both plans, including
    `SEMJEDI` frontmatter/title headings and `p4` quoted-preamble plus
    execution-notes headings that do not depend on modern phase-loop
    frontmatter.
  - test: Add a negative guard that an unrelated modern or historical
    phase-plan Markdown document outside the exact pair still uses the normal
    generic lightweight-name rule or heavy Markdown path as appropriate; the
    watchdog repair must not quietly become a broader phase-plan bypass.
  - impl: Keep fixtures deterministic with repo-local Markdown strings and
    monkeypatched bounded-path instrumentation rather than long-running live
    waits inside unit tests.
  - impl: Keep this lane on contract freeze only. Do not mutate durable trace,
    CLI wording, evidence docs, roadmap steering, or the phase-plan source
    files here.
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "phase_plan or SEMJEDI or p4 or markdown or lexical or bounded"`

### SL-1 - Bounded SEMJEDI/P4 Execution-Path Repair Or Minimal Plan-Local Simplification

- **Scope**: Implement the smallest dispatcher or Markdown-path repair needed
  so the live lexical walker no longer burns its watchdog budget on the exact
  `plans/phase-plan-v7-SEMJEDI.md ->
  plans/phase-plan-v1-p4.md` pair.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `mcp_server/plugins/markdown_plugin/plugin.py`, `plans/phase-plan-v7-SEMJEDI.md`, `plans/phase-plan-v1-p4.md`
- **Interfaces provided**: IF-0-SEMJEDIP4TAIL-2 exact boundary contract;
  IF-0-SEMJEDIP4TAIL-3 lexical discoverability contract
- **Interfaces consumed**: SL-0 SEMJEDI/P4 fixtures; existing bounded Markdown
  routing in `MarkdownPlugin._resolve_lightweight_reason(...)`; the current
  single-file lexical path in `dispatcher_enhanced.py`; and the current
  structure of `plans/phase-plan-v7-SEMJEDI.md` and
  `plans/phase-plan-v1-p4.md`
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 dispatcher slice first and confirm what still makes the
    exact mixed-generation pair expensive in the current force-full path even
    though both stems already match the generic roadmap/phase-plan rule.
  - impl: Apply the narrowest repair that clears the exact pair. Prefer
    reusing the existing bounded Markdown document and heading extraction path;
    only add exact-path or legacy-shape logic if the tests prove the generic
    phase-plan rule is still insufficient for this `SEMJEDI -> p4` seam in the
    live walker.
  - impl: If a plan-local simplification is necessary, keep it exact to
    `plans/phase-plan-v7-SEMJEDI.md` and `plans/phase-plan-v1-p4.md`. Preserve
    the current planning meaning and keep the edits lexical-structure-oriented
    rather than rewriting the historical plan contents.
  - impl: Preserve stored file rows plus document and heading discoverability
    for both plans; the repair must not turn either file into an ignored
    source document or silently remove it from lexical FTS.
  - impl: Keep the repair exact-file or exact-pair narrow. Do not add a broad
    `plans/phase-plan-v1-*.md`, `plans/phase-plan-v7-*.md`, or repository-wide
    Markdown chunking bypass.
  - verify: `rg -n "phase-plan-v7-SEMJEDI|phase-plan-v1-p4|_ROADMAP_MARKDOWN_NAME_RE|_EXACT_BOUNDED_MARKDOWN_PATHS|index_file|lightweight" mcp_server/dispatcher/dispatcher_enhanced.py mcp_server/plugins/markdown_plugin/plugin.py plans/phase-plan-v7-SEMJEDI.md plans/phase-plan-v1-p4.md tests/test_dispatcher.py`
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "phase_plan or SEMJEDI or p4 or markdown or lexical or bounded"`

### SL-2 - Durable Trace Persistence And Operator Boundary Alignment

- **Scope**: Carry the chosen SEMJEDI/P4 repair through force-full closeout and
  keep the operator-facing status surface aligned with the exact later pair
  that was repaired.
- **Owned files**: `mcp_server/storage/git_index_manager.py`, `mcp_server/cli/repository_commands.py`, `tests/test_git_index_manager.py`, `tests/test_repository_commands.py`
- **Interfaces provided**: IF-0-SEMJEDIP4TAIL-1 SEMJEDI/P4 pair advance
  contract; IF-0-SEMJEDIP4TAIL-4 durable trace and operator contract
- **Interfaces consumed**: SL-0 dispatcher fixtures; SL-1 chosen repair;
  existing lexical progress snapshot fields, durable
  `force_full_exit_trace.json` persistence, and the current status wording for
  the repaired historical-v1 and mixed-version phase-plan seams
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_git_index_manager.py` so force-full durable trace
    coverage preserves the exact `SEMJEDI -> p4` pair when that seam is still
    active, then proves the trace advances beyond both files once the repair is
    in place without regressing to stale `p13 -> p3` or
    `SEMPHASETAIL -> gagov` wording.
  - test: Extend `tests/test_repository_commands.py` so
    `uv run mcp-index repository status` continues to render the existing
    repaired lexical boundaries while adding truthful operator guidance for the
    later `plans/phase-plan-v7-SEMJEDI.md ->
    plans/phase-plan-v1-p4.md` seam.
  - impl: Thread the chosen repair through durable trace persistence and
    operator wording only as needed so the rerun can advance beyond the exact
    pair.
  - impl: Preserve the existing force-full trace fields, fail-closed
    indexed-commit behavior, and lexical watchdog semantics. This lane should
    move the handoff forward, not rename stages or declare readiness early.
  - impl: If SL-1 alone is sufficient and no runtime storage change is
    required, keep this lane scoped to status wording plus trace fixtures
    rather than inventing extra persistence behavior.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "phase_plan or SEMJEDI or p4 or lexical or interrupted or boundary"`

### SL-3 - Live Rerun Evidence Reducer And SEMJEDIP4TAIL Contract Refresh

- **Scope**: Refresh the repo-local dogfood report so it records the chosen
  SEMJEDI/P4 repair, the rerun outcome, and the next exact downstream status
  after this mixed-generation seam is cleared.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: IF-0-SEMJEDIP4TAIL-4 durable trace and operator
  contract; IF-0-SEMJEDIP4TAIL-5 evidence and downstream steering contract
- **Interfaces consumed**: SL-1 chosen repair; SL-2 rerun command, durable
  trace, and repository-status wording; roadmap SEMJEDIP4TAIL exit criteria;
  prior SEMV1PLANTAIL evidence lineage
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/docs/test_semdogfood_evidence_contract.py` so the
    refreshed report cites `plans/phase-plan-v7-SEMJEDI.md`,
    `plans/phase-plan-v1-p4.md`, the chosen repair, the rerun outcome, and the
    final authoritative verdict for the later mixed-generation phase-plan
    pair.
  - test: Require the report to preserve the existing evidence lineage for the
    already cleared `p13 -> p3` seam while making clear that the active
    current-head blocker has moved later to `SEMJEDI -> p4` or beyond.
  - impl: Update `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` with the live
    SEMJEDIP4TAIL rerun command, timestamps, refreshed trace snapshot,
    repository-status terminalization, and current SQLite counts so the report
    proves whether the repaired rerun advanced beyond the pair or surfaced a
    newer blocker.
  - impl: If the rerun advances to a later blocker, make the report name that
    blocker exactly and mark the `SEMJEDI -> p4` seam as cleared. If the rerun
    still ends at the exact pair, keep the report truthful and do not pretend
    the boundary is repaired.
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
  - verify: `rg -n "SEMJEDIP4TAIL|phase-plan-v7-SEMJEDI|phase-plan-v1-p4|force_full_exit_trace|Trace stage|Trace blocker source|roadmap now adds downstream phase" docs/status/SEMANTIC_DOGFOOD_REBUILD.md tests/docs/test_semdogfood_evidence_contract.py`

### SL-4 - Downstream Roadmap Steering Reducer

- **Scope**: Keep the roadmap and next phase-loop step truthful if the repaired
  live rerun proves a newer blocker beyond the current roadmap tail.
- **Owned files**: `specs/phase-plans-v7.md`
- **Interfaces provided**: the downstream-steering portion of
  IF-0-SEMJEDIP4TAIL-5
- **Interfaces consumed**: SL-3 refreshed evidence verdict; current roadmap
  DAG and phase ordering for `specs/phase-plans-v7.md`; canonical
  `.phase-loop/` expectation that the next unplanned phase reflects the latest
  durable blocker rather than stale prior assumptions
- **Parallel-safe**: no
- **Tasks**:
  - test: Re-read the post-SL-3 evidence and confirm whether the repaired
    rerun actually exposes a newer blocker beyond the current roadmap tail
    before mutating roadmap steering.
  - impl: If the active blocker is still the exact `SEMJEDI -> p4` pair, leave
    the roadmap unchanged.
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
  - `uv run pytest tests/test_dispatcher.py -q --no-cov -k "phase_plan or SEMJEDI or p4 or markdown or lexical or bounded"`
  - `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "phase_plan or SEMJEDI or p4 or lexical or interrupted or boundary"`
  - `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
- Whole-phase checks:
  - `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_repository_commands.py tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "phase_plan or SEMJEDI or p4 or markdown or lexical or bounded or interrupted or boundary"`
  - `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  - `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - `sed -n '1,240p' .mcp-index/force_full_exit_trace.json`
  - `sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'`
  - `git diff --check`
  - `git diff --cached --check`

## Acceptance Criteria

- [ ] A refreshed repo-local force-full rerun on the post-SEMV1PLANTAIL head
      either advances durably beyond
      `plans/phase-plan-v7-SEMJEDI.md ->
      plans/phase-plan-v1-p4.md` or emits a truthful newer blocker before
      the 120-second watchdog expires.
- [ ] The chosen repair stays narrowly scoped to the exact SEMJEDI/P4
      phase-plan pair and the immediate dispatcher/Markdown/trace/status/
      evidence plumbing needed to prove it.
- [ ] The chosen repair does not reopen the repaired
      `plans/phase-plan-v1-p13.md ->
      plans/phase-plan-v1-p3.md` boundary without direct new evidence.
- [ ] Both exact phase-plan files remain lexically discoverable with durable
      file storage plus bounded document and heading discoverability,
      including the modern `SEMJEDI` plan shape and the legacy `p4`
      quoted-preamble and execution-notes structure.
- [ ] `uv run mcp-index repository status` and
      `force_full_exit_trace.json` stay aligned with the repaired
      mixed-generation phase-plan boundary outcome and do not regress to stale
      SEMV1PLANTAIL wording.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the SEMV1PLANTAIL
      rerun outcome and the final live verdict for the later
      `plans/phase-plan-v7-SEMJEDI.md ->
      plans/phase-plan-v1-p4.md` phase-plan pair.
- [ ] If execution reveals a newer blocker beyond the current roadmap tail,
      `specs/phase-plans-v7.md` is updated before closeout so the next
      phase-loop step is truthful.

automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMJEDIP4TAIL.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMJEDIP4TAIL.md
  artifact_state: staged
