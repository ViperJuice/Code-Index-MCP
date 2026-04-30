---
phase_loop_plan_version: 1
phase: SEMAIDOCREADMETAIL
roadmap: specs/phase-plans-v7.md
roadmap_sha256: 054d013b56a61be17f62a66675097e7b3f2d2232864f858ffd02ea33a13b1862
---
# SEMAIDOCREADMETAIL: AI Docs README Tail Recovery

## Context

SEMAIDOCREADMETAIL is the phase-96 follow-up for the v7 semantic hardening
roadmap. Canonical `.phase-loop/` runtime exists in this checkout, so it is
the authoritative runner state for this planning run. `.phase-loop/state.json`
and `.phase-loop/tui-handoff.md` both mark `SEMAIDOCREADMETAIL` as the current
`unplanned` phase after `SEMREINDEXDEMOTAIL` closed out on `HEAD`
`ad22ecd823c34321e96b481e3427ce24a0c9ffc3` with verification `passed`, a clean
worktree, and `main...origin/main [ahead 187]`. Legacy `.codex/phase-loop/`
artifacts remain compatibility-only and do not supersede canonical `.phase-loop/`
runner state here.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is the active roadmap, is tracked and clean in this
  worktree, and its live file hash matches the required
  `054d013b56a61be17f62a66675097e7b3f2d2232864f858ffd02ea33a13b1862`.
- The target artifact `plans/phase-plan-v7-SEMAIDOCREADMETAIL.md` did not
  exist before this planning run.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is the live evidence anchor. Its
  `SEMREINDEXDEMOTAIL Live Rerun Check` block records that the refreshed
  repo-local force-full command
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  no longer terminalized at
  `scripts/reindex_current_repository.py -> scripts/demo_centralized_indexes.py`
  and instead moved later into the `ai_docs` surface
  `ai_docs/prometheus_overview.md -> ai_docs/README.md`.
- The same evidence block captures the current live trace for this phase:
  at `2026-04-30T06:17:31Z`, `.mcp-index/force_full_exit_trace.json` showed
  `status: running`, `stage: lexical_walking`,
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/ai_docs/prometheus_overview.md`,
  and
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/ai_docs/README.md`;
  at `2026-04-30T06:17:40Z`, `uv run mcp-index repository status` terminalized
  the same rerun to `Trace status: interrupted` while preserving that exact
  later pair.
- The two Markdown documents are not extreme-size outliers by the current
  plugin rules. `ai_docs/prometheus_overview.md` is `573` lines / `14801`
  bytes, and `ai_docs/README.md` is `92` lines / `4159` bytes.
- The Markdown plugin already has coarse bounded paths for both sides of the
  live seam. `mcp_server/plugins/markdown_plugin/plugin.py` routes
  `ai_docs/prometheus_overview.md` through `ai_docs_overview_path` and routes
  `ai_docs/README.md` through the generic `readme_path`, so the active
  planning question is not merely "add a bounded Markdown rule".
- Existing tests freeze those bounded reasons separately but not the exact
  live handoff. `tests/root_tests/test_markdown_production_scenarios.py`
  already asserts `readme_path` for `README.md` and `ai_docs_overview_path`
  for the later overview pair
  `ai_docs/black_isort_overview.md -> ai_docs/sqlite_fts5_overview.md`.
  `tests/test_dispatcher.py` also freezes the later overview pair, but repo
  inspection during planning did not show an exact dispatcher or operator
  contract for
  `ai_docs/prometheus_overview.md -> ai_docs/README.md`.
- The operator surface is one step broader than the live blocker.
  `mcp_server/cli/repository_commands.py` currently prints the generic
  boundary `ai_docs/*_overview.md` and the exact boundary `ai_docs/jedi.md`,
  but it does not currently advertise an exact bounded Markdown seam for
  `ai_docs/prometheus_overview.md -> ai_docs/README.md` even though the live
  rerun and evidence artifact now pivot on that exact pair.
- Semantic state remains fail-closed rather than hiding the lexical blocker:
  SQLite runtime counts after the refreshed rerun were
  `files = 1199`, `code_chunks = 21254`, `chunk_summaries = 0`, and
  `semantic_points = 0`, while `repository status` still reported
  `Readiness: stale_commit`, `Rollout status: partial_index_failure`,
  `Last sync error: disk I/O error`, and
  `Semantic readiness: summaries_missing`.

Practical planning boundary:

- SEMAIDOCREADMETAIL may tighten exact-pair Markdown or dispatcher handling,
  durable trace persistence, operator status wording, the two exact `ai_docs`
  documents themselves if a file-local simplification is proved necessary, the
  semantic dogfood evidence artifact, and downstream roadmap steering needed to
  prove a live rerun either advances beyond
  `ai_docs/prometheus_overview.md -> ai_docs/README.md` or surfaces a truthful
  newer blocker.
- SEMAIDOCREADMETAIL must stay narrow and evidence-driven. It must not reopen
  the already-cleared reindex/demo script seam, remove or redefine the existing
  generic `ai_docs/*_overview.md` or generic `readme_path` contracts for
  unrelated Markdown, add a broad `ai_docs/*.md` or repository-wide Markdown
  bypass, or widen into unrelated semantic-stage, release, or compatibility
  work unless the refreshed rerun points there directly.
- Because both files already route through bounded Markdown reasons, execution
  should first prove whether the active cost is concentrated in exact
  `prometheus_overview -> README` handoff accounting, in the generic README
  lightweight path when exercised inside `ai_docs/`, or in the checked-in doc
  content itself before introducing a new repair surface.

## Interface Freeze Gates

- [ ] IF-0-SEMAIDOCREADMETAIL-1 - AI-docs README pair advance contract:
      a refreshed repo-local force-full rerun on the post-SEMREINDEXDEMOTAIL
      head no longer terminalizes with the durable lexical trace centered on
      `ai_docs/prometheus_overview.md -> ai_docs/README.md`; it either advances
      durably beyond that pair or emits a truthful newer blocker before the
      120-second watchdog expires.
- [ ] IF-0-SEMAIDOCREADMETAIL-2 - Exact boundary contract:
      any repair introduced by this phase remains limited to the exact
      `ai_docs/prometheus_overview.md -> ai_docs/README.md` pair and the
      immediate plugin or dispatcher or trace or status or evidence or
      roadmap-steering plumbing needed to clear it. The phase must not reopen
      the repaired
      `scripts/reindex_current_repository.py -> scripts/demo_centralized_indexes.py`
      seam or widen the existing bounded Markdown behavior into a broader
      `ai_docs/*.md`, docs-wide, or repo-wide bypass without direct evidence.
- [ ] IF-0-SEMAIDOCREADMETAIL-3 - Lexical discoverability contract:
      both exact Markdown documents remain lexically discoverable after the
      repair, including durable file storage plus title and heading
      discoverability for `Prometheus Overview` and `AI Documentation Index`,
      instead of turning either file into an indexing blind spot.
- [ ] IF-0-SEMAIDOCREADMETAIL-4 - Boundary-preservation and operator contract:
      the existing `ai_docs/*_overview.md`, `readme_path`, and
      `ai_docs/jedi.md` bounded Markdown contracts remain truthful after the
      repair; any new exact boundary explanation for the active pair stays
      additive and narrow in durable trace and `repository status` output.
- [ ] IF-0-SEMAIDOCREADMETAIL-5 - Durable evidence and downstream steering
      contract: `force_full_exit_trace.json`, `uv run mcp-index repository status`,
      and `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` stay aligned with the
      repaired outcome for the exact
      `ai_docs/prometheus_overview.md -> ai_docs/README.md` pair, and if
      execution exposes a blocker beyond the current roadmap tail,
      `specs/phase-plans-v7.md` is amended before closeout so the next
      phase-loop step is truthful.

## Lane Index & Dependencies

- SL-0 - Exact ai_docs README seam contract freeze; Depends on: SEMREINDEXDEMOTAIL; Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 - Exact ai_docs README repair or minimal doc-local simplification; Depends on: SL-0; Blocks: SL-2, SL-3, SL-4; Parallel-safe: no
- SL-2 - Durable trace persistence and operator boundary alignment; Depends on: SL-0, SL-1; Blocks: SL-3, SL-4; Parallel-safe: no
- SL-3 - Live rerun evidence reducer and ai_docs README contract refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SL-4; Parallel-safe: no
- SL-4 - Downstream roadmap steering reducer; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: SEMAIDOCREADMETAIL acceptance; Parallel-safe: no

Lane DAG:

```text
SEMREINDEXDEMOTAIL
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SL-4 -> SEMAIDOCREADMETAIL acceptance
```

## Lanes

### SL-0 - Exact ai_docs README Seam Contract Freeze

- **Scope**: Freeze the exact
  `ai_docs/prometheus_overview.md -> ai_docs/README.md` lexical seam in
  deterministic Markdown and dispatcher coverage so this phase proves a narrow
  repair instead of assuming the existing generic overview and README bounded
  paths are already sufficient.
- **Owned files**: `tests/test_dispatcher.py`, `tests/root_tests/test_markdown_production_scenarios.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMAIDOCREADMETAIL-1,
  IF-0-SEMAIDOCREADMETAIL-2,
  IF-0-SEMAIDOCREADMETAIL-3,
  and the current broad-boundary assumptions referenced by
  IF-0-SEMAIDOCREADMETAIL-4
- **Interfaces consumed**: existing
  `MarkdownPlugin._resolve_lightweight_reason(...)`,
  `MarkdownPlugin._build_lightweight_index_shard(...)`,
  `Dispatcher.index_directory(...)`,
  and the current checked-in content shape of
  `ai_docs/prometheus_overview.md` and `ai_docs/README.md`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` with repo-shaped fixtures for
    `ai_docs/prometheus_overview.md` and `ai_docs/README.md` that freeze the
    exact live seam, prove whether the current bounded reasons already apply to
    both files under dispatcher walking, and fail if the later repair silently
    turns either file into an untracked blind spot.
  - test: Extend `tests/root_tests/test_markdown_production_scenarios.py` so
    the exact pair preserves document and heading discoverability, records the
    effective lightweight reasons in the path that actually executes, and does
    not silently broaden to unrelated Markdown such as `ai_docs/qdrant.md`,
    `ai_docs/jedi.md`, or repo-root `README.md`.
  - test: Add a negative guard that the existing generic `ai_docs/*_overview.md`
    path, generic `readme_path`, and exact `ai_docs/jedi.md` path remain intact;
    this phase must not regress them while freezing the later exact pair.
  - impl: Keep fixtures deterministic with repo-local Markdown strings and
    monkeypatched plugin or dispatcher instrumentation rather than long-running
    live waits inside unit coverage.
  - impl: Keep this lane on contract freeze only. Do not mutate durable trace,
    CLI wording, evidence docs, roadmap steering, or the checked-in `ai_docs`
    source files here.
  - verify: `uv run pytest tests/test_dispatcher.py tests/root_tests/test_markdown_production_scenarios.py -q --no-cov -k "prometheus or README or ai_docs or markdown or overview"`

### SL-1 - Exact ai_docs README Repair Or Minimal Doc-Local Simplification

- **Scope**: Implement the smallest repair needed so the live lexical walker no
  longer burns its watchdog budget on the exact
  `ai_docs/prometheus_overview.md -> ai_docs/README.md` pair.
- **Owned files**: `mcp_server/plugins/markdown_plugin/plugin.py`, `mcp_server/dispatcher/dispatcher_enhanced.py`, `ai_docs/prometheus_overview.md`, `ai_docs/README.md`
- **Interfaces provided**: IF-0-SEMAIDOCREADMETAIL-2 exact boundary contract;
  IF-0-SEMAIDOCREADMETAIL-3 lexical discoverability contract;
  the repair-point portion of IF-0-SEMAIDOCREADMETAIL-4
- **Interfaces consumed**: SL-0 exact-pair fixtures; existing
  `ai_docs_overview_path` and `readme_path` handling in `MarkdownPlugin`;
  current lexical progress behavior in `dispatcher_enhanced.py`;
  and the current content shape of the two exact `ai_docs` docs
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 Markdown and dispatcher slice first and confirm whether
    the active cost is concentrated in `ai_docs/README.md`, only at the exact
    handoff from `prometheus_overview.md`, or in dispatcher-local accounting
    even though both files already match bounded Markdown reasons.
  - impl: Choose one singular repair surface and keep it exact. Acceptable
    examples are an exact additive bounded-path override for one or both named
    files, a dispatcher-local exact-pair optimization, or the smallest
    file-local simplification of the two Markdown docs that lets the existing
    bounded paths complete under the current watchdog.
  - impl: Only edit `ai_docs/prometheus_overview.md` or `ai_docs/README.md`
    if tests prove the active hotspot is file-local structure rather than
    already-matched path handling. Preserve the docs' intended reference meaning
    and stable title and heading surface.
  - impl: Preserve stored file rows plus title and heading discoverability for
    both documents; the repair must not turn either file into an ignored source
    document or silently remove it from lexical FTS.
  - impl: Keep the repair exact-file or exact-pair narrow. Do not add a broad
    `ai_docs/*.md`, `docs/**/*.md`, or repository-wide Markdown bypass, and do
    not increase the global lexical watchdog just to move the seam.
  - verify: `rg -n "prometheus_overview|readme_path|ai_docs_overview_path|_resolve_lightweight_reason|lightweight_reason" mcp_server/plugins/markdown_plugin/plugin.py mcp_server/dispatcher/dispatcher_enhanced.py ai_docs/prometheus_overview.md ai_docs/README.md tests/test_dispatcher.py tests/root_tests/test_markdown_production_scenarios.py`
  - verify: `uv run pytest tests/test_dispatcher.py tests/root_tests/test_markdown_production_scenarios.py -q --no-cov -k "prometheus or README or ai_docs or markdown or overview"`

### SL-2 - Durable Trace Persistence And Operator Boundary Alignment

- **Scope**: Carry the chosen ai_docs README repair through force-full closeout
  and keep the operator-facing status surface aligned with the exact pair that
  was repaired.
- **Owned files**: `mcp_server/storage/git_index_manager.py`, `mcp_server/cli/repository_commands.py`, `tests/test_git_index_manager.py`, `tests/test_repository_commands.py`
- **Interfaces provided**: IF-0-SEMAIDOCREADMETAIL-1 AI-docs README pair
  advance contract; IF-0-SEMAIDOCREADMETAIL-4 boundary-preservation and
  operator contract; the trace and status portions of
  IF-0-SEMAIDOCREADMETAIL-5
- **Interfaces consumed**: SL-0 exact-pair fixtures; SL-1 chosen repair;
  existing lexical progress snapshot fields, durable
  `force_full_exit_trace.json` persistence, and the current status wording for
  `ai_docs/*_overview.md`, `ai_docs/jedi.md`, and generic README handling
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_git_index_manager.py` so force-full durable trace
    coverage preserves the exact
    `ai_docs/prometheus_overview.md -> ai_docs/README.md` pair when that seam
    is still active, then proves the trace advances beyond both files once the
    repair is in place without regressing to the cleared
    reindex/demo script seam.
  - test: Extend `tests/test_repository_commands.py` so
    `uv run mcp-index repository status` continues to print the generic
    `ai_docs/*_overview.md` boundary and any existing README or `ai_docs/jedi.md`
    contract lines, but also reports the exact current
    `ai_docs/prometheus_overview.md -> ai_docs/README.md` blocker pair once the
    durable trace moves there.
  - test: Add a negative operator guard that older blocker wording for
    `scripts/reindex_current_repository.py -> scripts/demo_centralized_indexes.py`
    does not remain the active blocker once the trace has moved later.
  - impl: Add only the exact status or trace alignment needed for the later
    `prometheus_overview -> README` pair; keep broader overview and README
    boundary reporting additive and truthful rather than rewritten.
  - impl: Preserve the existing readiness vocabulary and fail-closed behavior;
    files outside the repaired pair must still be able to surface exact
    low-level blockers and storage diagnostics.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "prometheus or README or ai_docs or lexical or interrupted or boundary"`

### SL-3 - Live Rerun Evidence Reducer And ai_docs README Contract Refresh

- **Scope**: Refresh the real dogfood evidence after the ai_docs README repair
  so the active blocker report matches the repaired runtime rather than stale
  SEMREINDEXDEMOTAIL assumptions.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: the evidence portion of
  IF-0-SEMAIDOCREADMETAIL-5
- **Interfaces consumed**: SL-2 durable trace and repository-status output;
  live rerun command output; existing SEMREINDEXDEMOTAIL evidence block; and
  the current evidence-contract assertions in
  `tests/docs/test_semdogfood_evidence_contract.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/docs/test_semdogfood_evidence_contract.py` only as
    needed so the evidence artifact must retain the SEMREINDEXDEMOTAIL rerun
    outcome, the active `SEMAIDOCREADMETAIL` phase name, the exact current
    `ai_docs/prometheus_overview.md -> ai_docs/README.md` verdict, and any
    newly exposed downstream steering after execution.
  - impl: Run a fresh repo-local force-full rerun after SL-1 and SL-2 land,
    then capture the rerun command, observed commit, timeout or completion
    timestamp, durable trace snapshot, `repository status` output, and SQLite
    counts in `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`.
  - impl: If the repaired rerun still times out, record the exact later blocker
    pair or family that replaced
    `ai_docs/prometheus_overview.md -> ai_docs/README.md` instead of leaving the
    older reindex/demo seam or the current ai_docs README seam as the active
    narrative.
  - impl: Keep this lane on evidence reduction. Do not back-edit older phase
    narratives except where the new rerun explicitly supersedes the active
    blocker statement.
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "SEMAIDOCREADMETAIL or SEMREINDEXDEMOTAIL or prometheus_overview or ai_docs"`

### SL-4 - Downstream Roadmap Steering Reducer

- **Scope**: Keep the roadmap and next phase-loop step truthful if the repaired
  live rerun proves a blocker beyond the current roadmap tail.
- **Owned files**: `specs/phase-plans-v7.md`
- **Interfaces provided**: the downstream-steering portion of
  IF-0-SEMAIDOCREADMETAIL-5
- **Interfaces consumed**: SL-3 refreshed evidence verdict; current roadmap
  DAG and phase ordering for `specs/phase-plans-v7.md`; and canonical
  `.phase-loop/` expectations that the next unplanned phase reflects the latest
  durable blocker rather than stale SEMREINDEXDEMOTAIL assumptions
- **Parallel-safe**: no
- **Tasks**:
  - test: Re-read the post-SL-3 evidence and confirm whether the repaired rerun
    actually exposes a newer blocker beyond the current roadmap tail before
    mutating roadmap steering.
  - impl: If the active blocker remains inside the current
    `SEMAIDOCREADMETAIL` ai_docs README family or the rerun completes lexical
    closeout, leave the roadmap unchanged.
  - impl: If the active blocker advances beyond the current roadmap tail and no
    downstream phase already covers it, append the nearest truthful downstream
    recovery phase to `specs/phase-plans-v7.md` with the same evidence-first
    structure used by the current SEM* lexical-recovery chain.
  - impl: Keep any roadmap mutation limited to the newly exposed blocker. Do
    not rewrite earlier phases or backfill unrelated sequencing while closing
    this seam.
  - verify: `git diff -- specs/phase-plans-v7.md`

## Verification

- Lane checks:
  - `uv run pytest tests/test_dispatcher.py tests/root_tests/test_markdown_production_scenarios.py -q --no-cov -k "prometheus or README or ai_docs or markdown or overview"`
  - `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "prometheus or README or ai_docs or lexical or interrupted or boundary"`
  - `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "SEMAIDOCREADMETAIL or SEMREINDEXDEMOTAIL or prometheus_overview or ai_docs"`
- Whole-phase checks:
  - `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/root_tests/test_markdown_production_scenarios.py tests/test_git_index_manager.py tests/test_repository_commands.py tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "prometheus or README or ai_docs or markdown or overview or lexical or interrupted or boundary or SEMAIDOCREADMETAIL or SEMREINDEXDEMOTAIL"`
  - `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  - `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - `sed -n '1,240p' .mcp-index/force_full_exit_trace.json`
  - `sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'`
  - `git status --short -- plans/phase-plan-v7-SEMAIDOCREADMETAIL.md docs/status/SEMANTIC_DOGFOOD_REBUILD.md specs/phase-plans-v7.md`
  - `git diff --check`
  - `git diff --cached --check`

## Acceptance Criteria

- [ ] A refreshed repo-local force-full rerun on the post-SEMREINDEXDEMOTAIL
      head either advances durably beyond
      `ai_docs/prometheus_overview.md -> ai_docs/README.md` or emits a
      truthful newer blocker before the 120-second watchdog expires.
- [ ] The repair stays narrowly scoped to the exact
      `ai_docs/prometheus_overview.md -> ai_docs/README.md` pair and the
      immediate plugin or dispatcher or trace or status or evidence plumbing
      needed to prove it.
- [ ] Both exact Markdown documents remain lexically discoverable with durable
      file storage plus title and heading discoverability.
- [ ] `uv run mcp-index repository status` and
      `.mcp-index/force_full_exit_trace.json` stay aligned with the repaired
      ai_docs README-tail outcome and do not regress to stale
      SEMREINDEXDEMOTAIL or earlier blocker wording.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMREINDEXDEMOTAIL rerun outcome and the final live verdict for the exact
      `ai_docs/prometheus_overview.md -> ai_docs/README.md` pair.
- [ ] If execution reveals a newer blocker beyond the current roadmap tail,
      `specs/phase-plans-v7.md` is updated before closeout so the next
      phase-loop step is truthful.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMAIDOCREADMETAIL.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMAIDOCREADMETAIL.md
  artifact_state: staged
```
