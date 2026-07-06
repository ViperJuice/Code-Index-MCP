---
phase_loop_plan_version: 1
phase: SEMAIOVERVIEWTAIL
roadmap: specs/phase-plans-v7.md
roadmap_sha256: c7069fe1946217d14303eea18f38408c6d07b0c6f3ca08d775f1ea1fb279245e
---
# SEMAIOVERVIEWTAIL: AI Docs Overview Tail Recovery

## Context

SEMAIOVERVIEWTAIL is the phase-69 follow-up for the v7 semantic hardening
roadmap. Canonical `.phase-loop/` runtime exists in this checkout, so it is
the authoritative runner state for this planning run. That canonical state is
slightly lagging across its human-facing snapshots: `.phase-loop/state.json`
and `.phase-loop/tui-handoff.md` still show `current_phase=SEMFIXTURETAIL`
with a blocked closeout, while the same canonical `.phase-loop/events.jsonl`
ledger records a later `manual_repair` at `2026-04-29T21:56:29Z` that cleared
the SEMFIXTURETAIL blocker, committed closeout as
`35a3d58b8e76031108ae55bc4f06d4161c0e8c45`, and pointed the next step to
`codex-plan-phase specs/phase-plans-v7.md SEMAIOVERVIEWTAIL`. This artifact
therefore treats SEMAIOVERVIEWTAIL as the active next-phase handoff instead of
letting the stale SEMFIXTURETAIL snapshot block plan creation.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is the active roadmap, and its live file hash
  matches the required
  `c7069fe1946217d14303eea18f38408c6d07b0c6f3ca08d775f1ea1fb279245e`.
- The checkout is on `main...origin/main [ahead 133]` at `HEAD`
  `35a3d58b8e76`, the worktree is currently clean before writing this new plan
  artifact, and `plans/phase-plan-v7-SEMAIOVERVIEWTAIL.md` did not exist
  before this run.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is the live evidence anchor. Its
  `SEMFIXTURETAIL Live Rerun Check` block records that the refreshed repo-local
  command
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  started on observed commit `3b92a81`, remained a running lexical snapshot at
  `2026-04-29T21:50:51Z` with
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/ai_docs/black_isort_overview.md`
  and
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/ai_docs/sqlite_fts5_overview.md`,
  and then terminalized at `2026-04-29T21:51:02Z` to `Trace status:
  interrupted` with the same exact pair.
- The SEMFIXTURETAIL target pair is no longer the active blocker:
  `tests/fixtures/multi_repo.py ->
  tests/fixtures/files/test_files/example.c`. Older downstream assumptions that
  still treat that fixture seam as current should be considered stale.
- The newly exposed pair is a later Markdown overview seam inside `ai_docs`.
  `ai_docs/black_isort_overview.md` is a tracked document of `183` lines /
  `4263` bytes with top heading `# Black & isort AI Context`, while
  `ai_docs/sqlite_fts5_overview.md` is a much larger tracked document of
  `1063` lines / `29115` bytes with top heading
  `# SQLite FTS5 Comprehensive Guide for Code Indexing`.
- The repo already has a broad bounded Markdown rule for `ai_docs/*_overview.md`.
  `mcp_server/plugins/markdown_plugin/plugin.py` returns
  `ai_docs_overview_path` when a Markdown path lives under `ai_docs/` and the
  stem ends with `_overview`, and
  `mcp_server/cli/repository_commands.py` already prints
  `Lexical boundary: using bounded Markdown indexing for ai_docs/*_overview.md`.
  The current planning question is therefore not whether overview docs are
  wholly unhandled, but why the later
  `ai_docs/black_isort_overview.md ->
  ai_docs/sqlite_fts5_overview.md` seam still remains the durable live
  blocker on the current head.
- Existing tests freeze only the broader class, not this exact later pair.
  `tests/test_dispatcher.py` proves bounded Markdown handling for
  `ai_docs/pytest_overview.md`, and
  `tests/test_repository_commands.py` proves the generic
  `ai_docs/*_overview.md` boundary line, but neither test currently freezes the
  exact `black_isort_overview.md -> sqlite_fts5_overview.md` handoff.
  `tests/test_git_index_manager.py` also lacks an exact durable-trace contract
  for this pair. By contrast,
  `tests/docs/test_semdogfood_evidence_contract.py` already requires the
  evidence artifact to mention `SEMFIXTURETAIL` acceptance, the
  `ai_docs/black_isort_overview.md -> ai_docs/sqlite_fts5_overview.md` pair,
  and roadmap steering to `SEMAIOVERVIEWTAIL`.

Practical planning boundary:

- SEMAIOVERVIEWTAIL may tighten exact later-overview handling, dispatcher
  lexical progress accounting, durable trace persistence, operator status
  wording, the two exact `ai_docs` overview documents themselves if a
  file-local simplification is proved necessary, the semantic dogfood evidence
  artifact, and downstream roadmap steering needed to prove a live rerun
  either advances beyond
  `ai_docs/black_isort_overview.md ->
  ai_docs/sqlite_fts5_overview.md` or surfaces a truthful newer blocker.
- SEMAIOVERVIEWTAIL must stay narrow and evidence-driven. It must not reopen
  the already-cleared fixture-tail seam, remove or redefine the existing
  `ai_docs/*_overview.md` bounded Markdown contract for unrelated overview
  docs, add a broad `ai_docs/*.md` or repository-wide Markdown bypass, or
  widen into unrelated semantic-stage, release, or roadmap work unless the
  refreshed rerun points there directly.
- Because a generic `ai_docs/*_overview.md` bounded rule already exists,
  execution should first prove whether the active cost is concentrated in the
  larger `sqlite_fts5_overview.md` file, the exact handoff from
  `black_isort_overview.md` into `sqlite_fts5_overview.md`, or stale
  operator/trace accounting around that pair before introducing a new repair
  surface.

## Interface Freeze Gates

- [ ] IF-0-SEMAIOVERVIEWTAIL-1 - AI-docs overview pair advance contract:
      a refreshed repo-local force-full rerun on the post-SEMFIXTURETAIL head
      no longer terminalizes with the durable lexical trace centered on
      `ai_docs/black_isort_overview.md ->
      ai_docs/sqlite_fts5_overview.md`; it either advances durably beyond that
      pair or emits a truthful newer blocker before the 120-second watchdog
      expires.
- [ ] IF-0-SEMAIOVERVIEWTAIL-2 - Exact boundary contract:
      any repair introduced by this phase remains limited to the exact
      `ai_docs/black_isort_overview.md ->
      ai_docs/sqlite_fts5_overview.md` pair and the immediate dispatcher,
      plugin, trace, status, evidence, and roadmap-steering plumbing needed to
      clear it. The phase must not reopen the repaired
      `tests/fixtures/multi_repo.py ->
      tests/fixtures/files/test_files/example.c` seam or widen the existing
      `ai_docs/*_overview.md` boundary to a broader `ai_docs/*.md` or
      docs-wide bypass without direct evidence.
- [ ] IF-0-SEMAIOVERVIEWTAIL-3 - Lexical discoverability contract:
      both exact overview docs remain lexically discoverable after the repair,
      including durable file storage plus lightweight or normal heading/title
      discoverability for `Black & isort AI Context` and
      `SQLite FTS5 Comprehensive Guide for Code Indexing`, instead of turning
      either file into an indexing blind spot.
- [ ] IF-0-SEMAIOVERVIEWTAIL-4 - Boundary-preservation and operator contract:
      the existing bounded Markdown contract for `ai_docs/*_overview.md`, the
      exact `ai_docs/jedi.md` handling, and the current repository-status
      readiness vocabulary remain truthful after the repair; any new exact
      boundary explanation must stay additive and narrow.
- [ ] IF-0-SEMAIOVERVIEWTAIL-5 - Durable trace, evidence, and downstream
      steering contract: `force_full_exit_trace.json`,
      `uv run mcp-index repository status`, and
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` stay aligned with the repaired
      outcome for the exact later overview pair, and if execution exposes a
      blocker beyond the current roadmap tail, `specs/phase-plans-v7.md` is
      amended before closeout so the next phase-loop step is truthful.

## Lane Index & Dependencies

- SL-0 - Exact later-overview seam contract freeze; Depends on: SEMFIXTURETAIL; Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 - Exact later-overview repair or minimal doc-local simplification; Depends on: SL-0; Blocks: SL-2, SL-3, SL-4; Parallel-safe: no
- SL-2 - Durable trace persistence and operator boundary alignment; Depends on: SL-0, SL-1; Blocks: SL-3, SL-4; Parallel-safe: no
- SL-3 - Live rerun evidence reducer and SEMAIOVERVIEWTAIL contract refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SL-4; Parallel-safe: no
- SL-4 - Downstream roadmap steering reducer; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: SEMAIOVERVIEWTAIL acceptance; Parallel-safe: no

Lane DAG:

```text
SEMFIXTURETAIL
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SL-4 -> SEMAIOVERVIEWTAIL acceptance
```

## Lanes

### SL-0 - Exact Later-Overview Seam Contract Freeze

- **Scope**: Freeze the exact
  `ai_docs/black_isort_overview.md ->
  ai_docs/sqlite_fts5_overview.md` lexical seam in deterministic Markdown and
  dispatcher coverage so this phase proves a narrow repair instead of assuming
  the existing broad overview-doc boundary is already sufficient.
- **Owned files**: `tests/test_dispatcher.py`, `tests/root_tests/test_markdown_production_scenarios.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMAIOVERVIEWTAIL-1,
  IF-0-SEMAIOVERVIEWTAIL-2,
  IF-0-SEMAIOVERVIEWTAIL-3,
  and the current broad-overview-boundary assumptions referenced by
  IF-0-SEMAIOVERVIEWTAIL-4
- **Interfaces consumed**: existing
  `MarkdownPlugin._resolve_lightweight_reason(...)`,
  `MarkdownPlugin._build_lightweight_index_shard(...)`,
  `Dispatcher.index_directory(...)`,
  and the current checked-in content shape of
  `ai_docs/black_isort_overview.md` and `ai_docs/sqlite_fts5_overview.md`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` with repo-shaped fixtures for
    `ai_docs/black_isort_overview.md` and
    `ai_docs/sqlite_fts5_overview.md` that freeze the current lexical seam,
    prove whether the broad `ai_docs_overview_path` rule is already applied to
    both files, and fail if the later repair silently turns either file into an
    untracked blind spot.
  - test: Extend `tests/root_tests/test_markdown_production_scenarios.py` so
    the exact pair preserves document and heading discoverability, records the
    lightweight reason in the path that actually executes, and does not
    silently broaden to unrelated Markdown such as `ai_docs/qdrant.md`,
    `ai_docs/jedi.md`, or repo-wide docs content.
  - test: Add a negative guard that earlier repaired boundaries remain intact,
    especially the existing generic `ai_docs/*_overview.md` path and the exact
    `ai_docs/jedi.md` path; this phase must not regress them while freezing the
    later exact pair.
  - impl: Keep fixtures deterministic with repo-local Markdown strings and
    monkeypatched plugin or dispatcher instrumentation rather than long-running
    live waits inside unit coverage.
  - impl: Keep this lane on contract freeze only. Do not mutate durable trace,
    CLI wording, evidence docs, roadmap steering, or the checked-in `ai_docs`
    source files here.
  - verify: `uv run pytest tests/test_dispatcher.py tests/root_tests/test_markdown_production_scenarios.py -q --no-cov -k "black_isort or sqlite_fts5 or overview or ai_docs or markdown"`

### SL-1 - Exact Later-Overview Repair Or Minimal Doc-Local Simplification

- **Scope**: Implement the smallest repair needed so the live lexical walker no
  longer burns its watchdog budget on the exact
  `ai_docs/black_isort_overview.md ->
  ai_docs/sqlite_fts5_overview.md` pair.
- **Owned files**: `mcp_server/plugins/markdown_plugin/plugin.py`, `mcp_server/dispatcher/dispatcher_enhanced.py`, `ai_docs/black_isort_overview.md`, `ai_docs/sqlite_fts5_overview.md`
- **Interfaces provided**: IF-0-SEMAIOVERVIEWTAIL-2 exact boundary contract;
  IF-0-SEMAIOVERVIEWTAIL-3 lexical discoverability contract;
  the repair-point portion of IF-0-SEMAIOVERVIEWTAIL-4
- **Interfaces consumed**: SL-0 exact-pair fixtures; existing
  `ai_docs_overview_path` handling in `MarkdownPlugin`;
  current lexical progress behavior in `dispatcher_enhanced.py`;
  and the current content shape of the two exact overview docs
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 Markdown and dispatcher slice first and confirm whether
    the active cost is concentrated in `ai_docs/sqlite_fts5_overview.md`,
    only at the exact handoff from `black_isort_overview.md`, or in a
    dispatcher-local accounting gap even though the broad overview rule already
    matches both files.
  - impl: Choose one singular repair surface and keep it exact. Acceptable
    examples are an exact bounded Markdown override for one or both named files,
    a dispatcher-local exact-pair optimization, or the smallest file-local
    simplification of the two Markdown docs that lets the existing overview
    contract complete under the current watchdog.
  - impl: Only edit `ai_docs/black_isort_overview.md` or
    `ai_docs/sqlite_fts5_overview.md` if tests prove the active hotspot is
    file-local structure rather than already-matched path handling. Preserve
    the docs' intended reference meaning and stable title/heading surface.
  - impl: Preserve stored file rows plus title and heading discoverability for
    both overview docs; the repair must not turn either file into an ignored
    source document or silently remove it from lexical FTS.
  - impl: Keep the repair exact-file or exact-pair narrow. Do not add a broad
    `ai_docs/*.md`, `docs/**/*.md`, or repository-wide Markdown bypass, and do
    not increase the global lexical watchdog just to move the seam.
  - verify: `rg -n "black_isort_overview|sqlite_fts5_overview|ai_docs_overview_path|_resolve_lightweight_reason|lightweight_reason" mcp_server/plugins/markdown_plugin/plugin.py mcp_server/dispatcher/dispatcher_enhanced.py ai_docs/black_isort_overview.md ai_docs/sqlite_fts5_overview.md tests/test_dispatcher.py tests/root_tests/test_markdown_production_scenarios.py`
  - verify: `uv run pytest tests/test_dispatcher.py tests/root_tests/test_markdown_production_scenarios.py -q --no-cov -k "black_isort or sqlite_fts5 or overview or ai_docs or markdown"`

### SL-2 - Durable Trace Persistence And Operator Boundary Alignment

- **Scope**: Carry the chosen later-overview repair through force-full closeout
  and keep the operator-facing status surface aligned with the exact pair that
  was repaired.
- **Owned files**: `mcp_server/storage/git_index_manager.py`, `mcp_server/cli/repository_commands.py`, `tests/test_git_index_manager.py`, `tests/test_repository_commands.py`
- **Interfaces provided**: IF-0-SEMAIOVERVIEWTAIL-1 AI-docs overview pair
  advance contract; IF-0-SEMAIOVERVIEWTAIL-4 boundary-preservation and
  operator contract; the trace/status portion of
  IF-0-SEMAIOVERVIEWTAIL-5
- **Interfaces consumed**: SL-0 exact-pair fixtures; SL-1 chosen repair;
  existing lexical progress snapshot fields, durable
  `force_full_exit_trace.json` persistence, and the current status wording for
  `ai_docs/*_overview.md`, `ai_docs/jedi.md`, and the repaired fixture seam
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_git_index_manager.py` so force-full durable trace
    coverage preserves the exact
    `ai_docs/black_isort_overview.md ->
    ai_docs/sqlite_fts5_overview.md` pair when that seam is still active, then
    proves the trace advances beyond both files once the repair is in place
    without regressing to stale SEMFIXTURETAIL-only wording.
  - test: Extend `tests/test_repository_commands.py` so
    `uv run mcp-index repository status` continues to render the existing
    generic `ai_docs/*_overview.md` boundary line and any exact later-overview
    explanation needed for this pair, while preserving the current readiness,
    rollout, and semantic status vocabulary.
  - impl: Thread the chosen repair through durable trace persistence and
    operator wording only as needed so the rerun can advance beyond the exact
    pair.
  - impl: Preserve the existing force-full trace fields, fail-closed
    indexed-commit behavior, and lexical watchdog semantics. This lane should
    move the handoff forward, not rename stages or declare readiness early.
  - impl: If SL-1 alone is sufficient and no runtime storage change is
    required, keep this lane scoped to status wording plus trace fixtures
    rather than inventing extra persistence behavior.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "black_isort or sqlite_fts5 or overview or lexical or interrupted or boundary"`

### SL-3 - Live Rerun Evidence Reducer And SEMAIOVERVIEWTAIL Contract Refresh

- **Scope**: Refresh the repo-local dogfood report so it records the chosen
  later-overview repair, the rerun outcome, and the next exact downstream
  status after this seam is cleared.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: the evidence portion of
  IF-0-SEMAIOVERVIEWTAIL-5
- **Interfaces consumed**: SL-1 chosen repair; SL-2 rerun command, durable
  trace, and repository-status wording; roadmap SEMAIOVERVIEWTAIL exit
  criteria; prior SEMFIXTURETAIL evidence lineage
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/docs/test_semdogfood_evidence_contract.py` so the
    refreshed report cites `plans/phase-plan-v7-SEMAIOVERVIEWTAIL.md`,
    `ai_docs/black_isort_overview.md`,
    `ai_docs/sqlite_fts5_overview.md`, the chosen repair, the rerun outcome,
    and the final authoritative verdict for the later overview pair.
  - test: Require the report to preserve the existing evidence lineage for the
    already-cleared fixture seam and the existing broad overview-boundary
    wording while making clear that the active current-head blocker has moved
    later to this exact pair or beyond it.
  - impl: Update `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` with the live
    SEMAIOVERVIEWTAIL rerun command, timestamps, refreshed trace snapshot,
    repository-status terminalization, and current SQLite counts so the report
    proves whether the repaired rerun advanced beyond the pair or surfaced a
    newer blocker.
  - impl: If the rerun advances to a later blocker, make the report name that
    blocker exactly and mark the overview seam as cleared. If the rerun still
    ends at the exact pair, keep the report truthful and do not pretend the
    boundary is repaired.
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "SEMAIOVERVIEWTAIL or black_isort or sqlite_fts5 or overview"`
  - verify: `rg -n "SEMAIOVERVIEWTAIL|black_isort_overview|sqlite_fts5_overview|SEMFIXTURETAIL|force_full_exit_trace|Trace status|roadmap now adds downstream phase" docs/status/SEMANTIC_DOGFOOD_REBUILD.md tests/docs/test_semdogfood_evidence_contract.py`

### SL-4 - Downstream Roadmap Steering Reducer

- **Scope**: Keep the roadmap and next phase-loop step truthful if the repaired
  live rerun proves a newer blocker beyond the current roadmap tail.
- **Owned files**: `specs/phase-plans-v7.md`
- **Interfaces provided**: the downstream-steering portion of
  IF-0-SEMAIOVERVIEWTAIL-5
- **Interfaces consumed**: SL-3 refreshed evidence verdict; current roadmap DAG
  and phase ordering for `specs/phase-plans-v7.md`; canonical `.phase-loop/`
  expectation that the next unplanned phase reflects the latest durable blocker
  rather than stale prior assumptions
- **Parallel-safe**: no
- **Tasks**:
  - test: Re-read the post-SL-3 evidence and confirm whether the repaired
    rerun actually exposes a newer blocker beyond the current roadmap tail
    before mutating roadmap steering.
  - impl: If the active blocker is still the exact
    `ai_docs/black_isort_overview.md ->
    ai_docs/sqlite_fts5_overview.md` pair, leave the roadmap unchanged.
  - impl: If the active blocker advances beyond the pair and no downstream
    phase already covers it, append the nearest truthful downstream recovery
    phase to `specs/phase-plans-v7.md` with the same evidence-first structure
    used by the current SEM* lexical-recovery chain.
  - impl: Keep any roadmap mutation limited to the newly exposed blocker. Do
    not rewrite earlier phases or backfill unrelated sequencing while closing
    this seam.
  - verify: `git diff -- specs/phase-plans-v7.md`

## Verification

Planning-only run: do not execute these during plan creation. Run them during
`codex-execute-phase` or manual SEMAIOVERVIEWTAIL execution.

Lane-specific checks:

```bash
uv run pytest tests/test_dispatcher.py tests/root_tests/test_markdown_production_scenarios.py -q --no-cov -k "black_isort or sqlite_fts5 or overview or ai_docs or markdown"
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "black_isort or sqlite_fts5 or overview or lexical or interrupted or boundary"
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "SEMAIOVERVIEWTAIL or black_isort or sqlite_fts5 or overview"
timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
sed -n '1,240p' .mcp-index/force_full_exit_trace.json
sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'
```

Whole-phase regression commands:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest \
  tests/test_dispatcher.py \
  tests/root_tests/test_markdown_production_scenarios.py \
  tests/test_git_index_manager.py \
  tests/test_repository_commands.py \
  tests/docs/test_semdogfood_evidence_contract.py \
  -q --no-cov -k "black_isort or sqlite_fts5 or overview or ai_docs or lexical or interrupted or boundary or markdown"
timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
git status --short -- specs/phase-plans-v7.md plans/phase-plan-v7-SEMAIOVERVIEWTAIL.md docs/status/SEMANTIC_DOGFOOD_REBUILD.md
git diff --check
git diff --cached --check
```

## Acceptance Criteria

- [ ] A refreshed repo-local force-full rerun on the post-SEMFIXTURETAIL head
      either advances durably beyond
      `ai_docs/black_isort_overview.md ->
      ai_docs/sqlite_fts5_overview.md` or emits a truthful newer blocker
      before the 120-second watchdog expires.
- [ ] The chosen repair stays narrowly scoped to the exact later overview pair
      and the immediate plugin or dispatcher or trace or status or evidence or
      roadmap plumbing needed to prove it.
- [ ] The repair does not reopen the cleared
      `tests/fixtures/multi_repo.py ->
      tests/fixtures/files/test_files/example.c` seam or replace the existing
      `ai_docs/*_overview.md` contract with a broader `ai_docs/*.md` or
      docs-wide bypass.
- [ ] Both exact overview docs remain lexically discoverable with durable file
      storage plus title and heading discoverability for the current tracked
      docs.
- [ ] `uv run mcp-index repository status` and
      `force_full_exit_trace.json` stay aligned with the repaired later
      overview boundary outcome and remain compatible with the existing
      `ai_docs/*_overview.md` and `ai_docs/jedi.md` operator wording.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the SEMFIXTURETAIL
      rerun outcome and the final live verdict for the later
      `ai_docs/black_isort_overview.md ->
      ai_docs/sqlite_fts5_overview.md` pair.
- [ ] If execution reveals a newer blocker beyond the current roadmap tail,
      `specs/phase-plans-v7.md` is updated before closeout so the next
      phase-loop step is truthful.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v7-SEMAIOVERVIEWTAIL.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMAIOVERVIEWTAIL.md
  artifact_state: staged
```
