---
phase_loop_plan_version: 1
phase: SEMOPTUPLOADTAIL
roadmap: specs/phase-plans-v7.md
roadmap_sha256: f0d3842694fbf0ee9c59ef35739bc699969ad8a39061e5f3719a87ce34032fc5
---
# SEMOPTUPLOADTAIL: Optimized Analysis Upload Tail Recovery

## Context

SEMOPTUPLOADTAIL is the phase-74 follow-up for the v7 semantic hardening
roadmap. Canonical `.phase-loop/` runtime exists in this checkout, so it is
the authoritative runner state for this planning run. The current canonical
snapshots agree cleanly: `.phase-loop/state.json` records
`current_phase = SEMOPTUPLOADTAIL`, `SEMQDRANTREPORTTAIL = complete`,
`SEMOPTUPLOADTAIL = unplanned`, a clean worktree before this artifact write,
and the required roadmap hash
`f0d3842694fbf0ee9c59ef35739bc699969ad8a39061e5f3719a87ce34032fc5`.
Legacy `.codex/phase-loop/` artifacts remain compatibility-only and do not
supersede canonical `.phase-loop/` state here.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is the active roadmap, and `sha256sum` confirms
  the live file hash matches the required
  `f0d3842694fbf0ee9c59ef35739bc699969ad8a39061e5f3719a87ce34032fc5`.
- The checkout is on `main...origin/main [ahead 143]` at `HEAD`
  `5ceeb985a47d98e0633357551bb2c2d83fc07c8f`, and
  `plans/phase-plan-v7-SEMOPTUPLOADTAIL.md` did not exist before this run.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is the active evidence anchor.
  Its `SEMQDRANTREPORTTAIL Live Rerun Check` block records that the refreshed
  repo-local command
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  started on observed commit
  `2a439a39b168cb01571e0b0872016875d198b6e2`, advanced durably beyond the
  repaired
  `scripts/map_repos_to_qdrant.py -> scripts/create_claude_code_aware_report.py`
  seam, and then terminalized later at `2026-04-29T23:19:22Z` with
  `Trace status: interrupted` on the exact Python script pair
  `scripts/execute_optimized_analysis.py -> scripts/index-artifact-upload-v2.py`.
- The evidence block also confirms that the SEMQDRANTREPORTTAIL target pair is
  no longer the active blocker and that repository status remains semantically
  fail-closed with `Readiness: stale_commit`,
  `Rollout status: partial_index_failure`, `Last sync error: disk I/O error`,
  and `Semantic readiness: summaries_missing`.
- SQLite runtime counts after that rerun remained
  `files = 1064`, `code_chunks = 13095`, `chunk_summaries = 0`, and
  `semantic_points = 0`, so this phase is still operating on a lexical
  blocker before summary or vector recovery can resume.
- `mcp_server/dispatcher/dispatcher_enhanced.py` already carries exact bounded
  Python entries for the repaired earlier utility and Qdrant/report pairs, but
  it does not yet carry an exact bounded-path contract for
  `scripts/execute_optimized_analysis.py` or
  `scripts/index-artifact-upload-v2.py`.
- `mcp_server/cli/repository_commands.py` already advertises exact bounded
  lexical boundaries for earlier Python pairs, including the repaired
  `scripts/map_repos_to_qdrant.py ->
  scripts/create_claude_code_aware_report.py` seam, but it has no dedicated
  operator boundary yet for the later optimized-analysis/upload pair.
- Existing tests freeze the recurring exact-tail contract for prior Python
  seams, durable trace persistence, and operator boundary wording, but there
  is no current dispatcher, trace, or status coverage for
  `scripts/execute_optimized_analysis.py` or
  `scripts/index-artifact-upload-v2.py`.
- The current checked-in script surfaces are still large enough to justify an
  exact-pair-first repair strategy before source edits: 
  `scripts/execute_optimized_analysis.py` exposes
  `OptimizedAnalysisMetrics`,
  `OptimizedAnalysisExecutor`,
  `execute_optimized_analysis`,
  `_extract_execution_metrics`,
  `_calculate_performance_achievements`,
  `_generate_final_results`,
  `_calculate_roi_analysis`,
  `_generate_optimization_insights`,
  `_generate_final_recommendations`,
  `_save_optimized_results`,
  `_generate_executive_summary_markdown`,
  `_print_executive_summary`, and `main`; 
  `scripts/index-artifact-upload-v2.py` exposes
  `CompatibilityAwareUploader`,
  `_detect_repository`,
  `_find_index_location`,
  `generate_compatibility_hash`,
  `get_existing_artifacts`,
  `find_compatible_artifact`,
  `compress_indexes`,
  `_calculate_checksum`,
  `create_metadata`,
  `_get_index_stats`,
  `trigger_workflow_upload`, and `main`.
- `tests/docs/test_semdogfood_evidence_contract.py` and the evidence report
  already mention `SEMOPTUPLOADTAIL`, so execution should extend the existing
  dogfood-evidence lineage rather than inventing a new status artifact.

Practical planning boundary:

- SEMOPTUPLOADTAIL may tighten exact bounded Python handling for
  `scripts/execute_optimized_analysis.py` and
  `scripts/index-artifact-upload-v2.py`, make the smallest script-local
  simplification only if tests prove a file-local structure hotspot, refresh
  durable trace persistence and repository-status wording, rerun the repo-local
  force-full sync, refresh the dogfood evidence report, and extend the roadmap
  only if a newer blocker appears beyond the current tail.
- SEMOPTUPLOADTAIL must stay narrow and evidence-driven. It must not reopen
  the already-cleared
  `scripts/map_repos_to_qdrant.py ->
  scripts/create_claude_code_aware_report.py`
  seam, add a broad `scripts/*.py` or repo-wide lexical timeout bypass, or
  widen into unrelated semantic or release work unless the refreshed rerun
  proves the blocker has moved again.
- Because the newly exposed pair is not yet covered by the exact bounded
  Python path map or status surface, execution should first prove whether the
  active cost is solved by extending the exact bounded-path contract for this
  pair before mutating the script sources themselves.

## Interface Freeze Gates

- [ ] IF-0-SEMOPTUPLOADTAIL-1 - Exact optimized-analysis/upload pair advance
      contract: a refreshed repo-local force-full rerun on the
      post-SEMQDRANTREPORTTAIL head no longer terminalizes with the durable
      lexical trace centered on
      `scripts/execute_optimized_analysis.py ->
      scripts/index-artifact-upload-v2.py`; it either advances durably beyond
      that exact pair or emits a truthful newer blocker before the 120-second
      watchdog expires.
- [ ] IF-0-SEMOPTUPLOADTAIL-2 - Exact boundary contract:
      any repair introduced by this phase remains limited to the exact named
      script pair and the immediate dispatcher, trace, status, evidence, and
      roadmap-steering plumbing needed to clear it. The phase must not reopen
      the repaired
      `scripts/map_repos_to_qdrant.py ->
      scripts/create_claude_code_aware_report.py`
      seam or widen to a general script-family bypass without direct evidence.
- [ ] IF-0-SEMOPTUPLOADTAIL-3 - Lexical discoverability contract:
      both exact scripts remain lexically discoverable after the repair,
      including durable file storage plus stable symbol and text
      discoverability for the current checked-in script surfaces
      (`OptimizedAnalysisMetrics`,
      `OptimizedAnalysisExecutor`,
      `execute_optimized_analysis`,
      `_generate_final_results`,
      `_generate_executive_summary_markdown`,
      `CompatibilityAwareUploader`,
      `generate_compatibility_hash`,
      `compress_indexes`,
      `create_metadata`,
      `trigger_workflow_upload`, and `main`) instead of turning either
      file into an indexing blind spot.
- [ ] IF-0-SEMOPTUPLOADTAIL-4 - Durable trace and operator contract:
      `force_full_exit_trace.json`, `GitAwareIndexManager`, and
      `uv run mcp-index repository status` stay aligned with the repaired
      outcome for the exact optimized-analysis/upload script pair, preserve
      the fail-closed readiness vocabulary, and do not regress to stale
      SEMQDRANTREPORTTAIL-only boundary wording once the rerun advances beyond
      the pair.
- [ ] IF-0-SEMOPTUPLOADTAIL-5 - Evidence and downstream steering contract:
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMQDRANTREPORTTAIL rerun outcome and the final authoritative verdict
      for the optimized-analysis/upload script pair, and if execution exposes
      a blocker beyond the current roadmap tail, `specs/phase-plans-v7.md` is
      amended before closeout so `.phase-loop/` points to the newest truthful
      next phase instead of stopping at a stale tail.

## Lane Index & Dependencies

- SL-0 - Exact optimized-analysis/upload seam contract freeze; Depends on: SEMQDRANTREPORTTAIL; Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 - Exact bounded optimized-analysis/upload repair or minimal script-local simplification; Depends on: SL-0; Blocks: SL-2, SL-3, SL-4; Parallel-safe: no
- SL-2 - Durable trace persistence and operator boundary alignment; Depends on: SL-0, SL-1; Blocks: SL-3, SL-4; Parallel-safe: no
- SL-3 - Live rerun evidence reducer and SEMOPTUPLOADTAIL contract refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SL-4; Parallel-safe: no
- SL-4 - Downstream roadmap steering reducer; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: SEMOPTUPLOADTAIL acceptance; Parallel-safe: no

Lane DAG:

```text
SEMQDRANTREPORTTAIL
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SL-4 -> SEMOPTUPLOADTAIL acceptance
```

## Lanes

### SL-0 - Exact Optimized-Analysis/Upload Seam Contract Freeze

- **Scope**: Freeze the exact
  `scripts/execute_optimized_analysis.py ->
  scripts/index-artifact-upload-v2.py`
  lexical seam in deterministic dispatcher coverage so this phase proves a
  narrow repair instead of assuming the later blocker will clear on its own.
- **Owned files**: `tests/test_dispatcher.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMOPTUPLOADTAIL-1,
  IF-0-SEMOPTUPLOADTAIL-2,
  and IF-0-SEMOPTUPLOADTAIL-3 at the dispatcher boundary
- **Interfaces consumed**: existing
  `Dispatcher.index_directory(...)`,
  `_EXACT_BOUNDED_PYTHON_PATHS`,
  lexical file metadata storage,
  and the current checked-in content shape of
  `scripts/execute_optimized_analysis.py` and
  `scripts/index-artifact-upload-v2.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` with repo-shaped fixtures for
    `scripts/execute_optimized_analysis.py`,
    `scripts/index-artifact-upload-v2.py`, and a control script so the exact
    pair preserves durable file rows, stable symbols, zero code chunks, and
    FTS-backed discoverability once the bounded-path repair is in place.
  - test: Add negative guards so earlier repaired exact bounded Python seams
    such as
    `scripts/utilities/prepare_index_for_upload.py`,
    `scripts/utilities/verify_tool_usage.py`,
    `scripts/map_repos_to_qdrant.py`, and
    `scripts/create_claude_code_aware_report.py`
    do not silently regress while the optimized-analysis/upload pair is added.
  - test: Fail if the repair would turn either target script into an ignored
    lexical blind spot or would remove the current stable helper surfaces from
    indexed discoverability.
  - impl: Keep fixtures deterministic with repo-local Python strings and
    bounded-path assertions rather than long-running live waits inside unit
    coverage.
  - impl: Keep this lane on contract freeze only. Do not mutate dispatcher
    implementation, trace persistence, CLI wording, evidence docs, roadmap
    steering, or the checked-in script sources here.
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "execute_optimized_analysis or index_artifact_upload or upload or optimized or lexical or bounded"`

### SL-1 - Exact Bounded Optimized-Analysis/Upload Repair Or Minimal Script-Local Simplification

- **Scope**: Implement the smallest repair needed so the live lexical walker
  no longer burns its watchdog budget on the exact
  `scripts/execute_optimized_analysis.py ->
  scripts/index-artifact-upload-v2.py`
  pair.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `scripts/execute_optimized_analysis.py`, `scripts/index-artifact-upload-v2.py`
- **Interfaces provided**: IF-0-SEMOPTUPLOADTAIL-1 exact advance contract;
  IF-0-SEMOPTUPLOADTAIL-2 exact boundary contract;
  IF-0-SEMOPTUPLOADTAIL-3 lexical discoverability contract
- **Interfaces consumed**: SL-0 exact-pair fixtures; existing
  `_EXACT_BOUNDED_PYTHON_PATHS`; current lexical timeout behavior in
  `_index_file_with_lexical_timeout(...)`; and the current structure of the
  two exact scripts
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 dispatcher slice first and confirm whether the active
    cost is best cleared by adding the pair to the existing exact bounded
    Python map or by the smallest file-local simplification of one of the two
    scripts.
  - impl: Choose one singular repair surface and keep it exact. Acceptable
    examples are adding one or both named files to
    `_EXACT_BOUNDED_PYTHON_PATHS` in `dispatcher_enhanced.py`, or making the
    smallest file-local simplification to
    `scripts/execute_optimized_analysis.py` or
    `scripts/index-artifact-upload-v2.py` that allows the current watchdog to
    advance beyond the pair.
  - impl: Only edit the script sources if tests prove the active hotspot is
    file-local structure rather than missing exact bounded-path handling.
    Preserve the scripts' intended operational meaning, stable helper
    function names, upload/report behavior, and current artifact names.
  - impl: Preserve durable file rows and lexical discoverability for both
    scripts; the repair must not turn either script into an ignored source
    file or silently remove it from lexical FTS.
  - verify: `rg -n "execute_optimized_analysis|index-artifact-upload-v2|_EXACT_BOUNDED_PYTHON_PATHS|bounded" mcp_server/dispatcher/dispatcher_enhanced.py scripts/execute_optimized_analysis.py scripts/index-artifact-upload-v2.py tests/test_dispatcher.py`
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "execute_optimized_analysis or index_artifact_upload or upload or optimized or lexical or bounded"`

### SL-2 - Durable Trace Persistence And Operator Boundary Alignment

- **Scope**: Keep durable force-full trace output and operator-visible status
  wording aligned with the repaired optimized-analysis/upload boundary and any
  newer blocker it reveals.
- **Owned files**: `mcp_server/storage/git_index_manager.py`, `mcp_server/cli/repository_commands.py`, `tests/test_git_index_manager.py`, `tests/test_repository_commands.py`
- **Interfaces provided**: IF-0-SEMOPTUPLOADTAIL-1 exact advance contract;
  IF-0-SEMOPTUPLOADTAIL-4 durable trace and operator contract
- **Interfaces consumed**: SL-0 dispatcher fixtures; SL-1 chosen repair;
  existing lexical progress snapshot fields, durable
  `force_full_exit_trace.json` persistence, and the current status wording for
  earlier Python-pair recoveries
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_git_index_manager.py` with a durable-trace case
    that preserves the exact optimized-analysis/upload pair in interrupted
    lexical snapshots and later rewrites that trace truthfully once the rerun
    advances beyond it.
  - test: Extend `tests/test_repository_commands.py` with repository-status
    assertions that print the optimized-analysis/upload boundary only when both
    scripts exist, while preserving the earlier utility and Qdrant/report
    boundary messages unchanged.
  - impl: Add the smallest repository-status helper needed for
    `scripts/execute_optimized_analysis.py ->
    scripts/index-artifact-upload-v2.py` and wire it into the current lexical
    boundary printing order without disturbing the existing fail-closed
    readiness surfaces.
  - impl: Keep `GitAwareIndexManager` trace semantics truthful: once the rerun
    moves beyond the pair, the persisted interrupted snapshot and status
    surfaces must stop presenting it as the active blocker.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "execute_optimized_analysis or index_artifact_upload or upload or optimized or lexical or interrupted or boundary"`

### SL-3 - Live Rerun Evidence Reducer And SEMOPTUPLOADTAIL Contract Refresh

- **Scope**: Re-run the repo-local force-full command after the repair and
  reduce its evidence into the canonical dogfood report without inventing a
  second status surface.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: IF-0-SEMOPTUPLOADTAIL-1 exact advance contract;
  IF-0-SEMOPTUPLOADTAIL-4 durable trace and operator contract;
  IF-0-SEMOPTUPLOADTAIL-5 evidence contract
- **Interfaces consumed**: SL-1 repair result; SL-2 repository-status and
  trace wording; live outputs from
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`,
  `uv run mcp-index repository status`, and
  `.mcp-index/force_full_exit_trace.json`; existing evidence sections for
  SEMUTILVERIFYTAIL and SEMQDRANTREPORTTAIL
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/docs/test_semdogfood_evidence_contract.py` so the
    evidence artifact must mention the SEMQDRANTREPORTTAIL rerun outcome, the
    optimized-analysis/upload pair, the final authoritative verdict for this
    phase, and any downstream steering if the blocker moves again.
  - impl: Update `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` with a dedicated
    `SEMOPTUPLOADTAIL Live Rerun Check` section that records observed commit,
    rerun command, timestamps, trace snapshot, repository-status output,
    SQLite counts, and the verdict on whether the exact pair is cleared or
    still active.
  - impl: Preserve the current evidence lineage. Do not create a new docs
    status file or split the semantic dogfood report by phase.
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "SEMOPTUPLOADTAIL or execute_optimized_analysis or index_artifact_upload or upload"`
  - verify: `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - verify: `sed -n '1,240p' .mcp-index/force_full_exit_trace.json`
  - verify: `sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'`

### SL-4 - Downstream Roadmap Steering Reducer

- **Scope**: Keep the roadmap and next phase-loop step truthful if the repaired
  live rerun proves a newer blocker beyond the current roadmap tail.
- **Owned files**: `specs/phase-plans-v7.md`
- **Interfaces provided**: IF-0-SEMOPTUPLOADTAIL-5 downstream steering
  contract
- **Interfaces consumed**: SL-3 refreshed evidence verdict; current roadmap
  DAG and phase ordering for `specs/phase-plans-v7.md`; and canonical
  `.phase-loop/` expectations that the next unplanned phase reflects the
  latest durable blocker rather than stale prior assumptions
- **Parallel-safe**: no
- **Tasks**:
  - test: Re-read the post-SL-3 evidence and confirm whether the repaired
    rerun actually exposes a newer blocker beyond the current roadmap tail
    before mutating roadmap steering.
  - impl: If the active blocker is still the exact optimized-analysis/upload
    pair, leave the roadmap unchanged.
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
`codex-execute-phase` or manual SEMOPTUPLOADTAIL execution.

Lane-specific checks:

```bash
uv run pytest tests/test_dispatcher.py -q --no-cov -k "execute_optimized_analysis or index_artifact_upload or upload or optimized or lexical or bounded"
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "execute_optimized_analysis or index_artifact_upload or upload or optimized or lexical or interrupted or boundary"
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "SEMOPTUPLOADTAIL or execute_optimized_analysis or index_artifact_upload or upload"
timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
sed -n '1,240p' .mcp-index/force_full_exit_trace.json
sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'
```

Whole-phase regression commands:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest \
  tests/test_dispatcher.py \
  tests/test_git_index_manager.py \
  tests/test_repository_commands.py \
  tests/docs/test_semdogfood_evidence_contract.py \
  -q --no-cov -k "execute_optimized_analysis or index_artifact_upload or upload or optimized or lexical or bounded or interrupted or boundary"
timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
git status --short -- plans/phase-plan-v7-SEMOPTUPLOADTAIL.md docs/status/SEMANTIC_DOGFOOD_REBUILD.md specs/phase-plans-v7.md
git diff --check
git diff --cached --check
```

## Acceptance Criteria

- [ ] A refreshed repo-local force-full rerun on the post-SEMQDRANTREPORTTAIL
      head either advances durably beyond
      `scripts/execute_optimized_analysis.py ->
      scripts/index-artifact-upload-v2.py`
      or emits a truthful newer blocker before the 120-second watchdog
      expires.
- [ ] The chosen repair for the optimized-analysis/upload script seam stays
      narrow, tested, and does not reopen the already-cleared
      `scripts/map_repos_to_qdrant.py ->
      scripts/create_claude_code_aware_report.py`
      boundary without direct evidence.
- [ ] Both exact scripts remain lexically discoverable with durable file
      storage and stable symbol/text discoverability for the current checked-in
      script surfaces.
- [ ] `force_full_exit_trace.json` and
      `uv run mcp-index repository status` stay aligned with the repaired
      outcome for the exact optimized-analysis/upload script pair and preserve
      the fail-closed semantic readiness vocabulary.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMQDRANTREPORTTAIL rerun outcome and the final live verdict for the
      optimized-analysis/upload script pair.
- [ ] If the rerun exposes a blocker beyond the current roadmap tail,
      `specs/phase-plans-v7.md` is updated before closeout so the next
      phase-loop step stays truthful.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMOPTUPLOADTAIL.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMOPTUPLOADTAIL.md
  artifact_state: staged
```
