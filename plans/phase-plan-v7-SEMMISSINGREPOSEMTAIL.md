---
phase_loop_plan_version: 1
phase: SEMMISSINGREPOSEMTAIL
roadmap: specs/phase-plans-v7.md
roadmap_sha256: 03ff72362f3b764859ca673ff1702f8c41645973983b0a1370d2f333cb7413ea
---
# SEMMISSINGREPOSEMTAIL: Missing-Repo Semantic Index Script Tail Recovery

## Context

SEMMISSINGREPOSEMTAIL is the phase-71 follow-up for the v7 semantic hardening
roadmap. Canonical `.phase-loop/` runtime exists in this checkout, so it is
the authoritative runner state for this planning run. The current canonical
snapshots agree cleanly: `.phase-loop/state.json` and `.phase-loop/tui-handoff.md`
both identify `SEMMISSINGREPOSEMTAIL` as the current `unplanned` phase for
`specs/phase-plans-v7.md`, and the recorded roadmap hash matches the
user-required `03ff72362f3b764859ca673ff1702f8c41645973983b0a1370d2f333cb7413ea`.
Legacy `.codex/phase-loop/` artifacts remain compatibility-only and do not
supersede canonical `.phase-loop/` state here.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is the active roadmap, and its live file hash
  matches the required
  `03ff72362f3b764859ca673ff1702f8c41645973983b0a1370d2f333cb7413ea`.
- The checkout is on `main...origin/main [ahead 137]` at `HEAD`
  `2b4055e0d159`, the worktree is clean before writing this artifact, and
  `plans/phase-plan-v7-SEMMISSINGREPOSEMTAIL.md` did not exist before this
  run.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is the live evidence anchor. Its
  `SEMTESTREPOINDEXTAIL Live Rerun Check` block records that the refreshed
  repo-local command
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  started on observed commit `0195d3c`, advanced durably beyond the cleared
  `scripts/check_test_index_schema.py ->
  scripts/ensure_test_repos_indexed.py` seam, and then terminalized later at
  `2026-04-29T22:27:04Z` with `Trace status: interrupted` on the exact script
  pair
  `scripts/index_missing_repos_semantic.py ->
  scripts/identify_working_indexes.py`.
- The phase-70 target pair is no longer the active blocker according to the
  same evidence block and current repository-status output. Older downstream
  assumptions that still treat
  `scripts/check_test_index_schema.py ->
  scripts/ensure_test_repos_indexed.py` as current should now be considered
  stale.
- The repo remains semantically fail-closed after that rerun: the evidence
  block still reports `Readiness: stale_commit`, `Rollout status:
  partial_index_failure`, `Last sync error: disk I/O error`,
  `Semantic readiness: summaries_missing`, and SQLite counts of
  `files = 1064`, `code_chunks = 13095`, `chunk_summaries = 0`, and
  `semantic_points = 0`.
- The newly exposed pair consists of two tracked Python utilities under
  `scripts/`. `scripts/index_missing_repos_semantic.py` is `146` lines and
  currently defines `get_existing_collections`,
  `find_missing_repositories`, `estimate_repo_size`, and `main` around
  Qdrant collection inspection plus `missing_repos_to_index.json` output.
  `scripts/identify_working_indexes.py` is `255` lines and currently defines
  `get_repo_hash`, `check_index_health`, `find_test_repos`, and `main` around
  centralized `~/.mcp/indexes` SQLite inspection plus
  `working_indexes_analysis.json` output.
- `mcp_server/dispatcher/dispatcher_enhanced.py` already carries an
  `_EXACT_BOUNDED_PYTHON_PATHS` map for neighboring script-tail recoveries
  such as `scripts/check_test_index_schema.py`,
  `scripts/ensure_test_repos_indexed.py`,
  `scripts/create_semantic_embeddings.py`, and
  `scripts/consolidate_real_performance_data.py`, but it does not yet include
  `scripts/index_missing_repos_semantic.py` or
  `scripts/identify_working_indexes.py`.
- `mcp_server/storage/git_index_manager.py` and
  `mcp_server/cli/repository_commands.py` already support the recurring
  exact-tail pattern for durable `force_full_exit_trace.json` snapshots and
  operator boundary wording. Existing tests freeze the prior script pair and
  several neighboring exact-path seams, but there is not yet an exact
  durable-trace or repository-status contract for the missing-repo semantic
  index pair.
- `tests/test_dispatcher.py` already contains the exact bounded-Python
  indexing pattern for prior script-tail phases, preserving symbol
  discoverability with zero code chunks and single FTS rows on the bounded
  paths. There is no equivalent coverage yet for the new script pair.
- `tests/docs/test_semdogfood_evidence_contract.py` and
  `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` already mention the newly exposed
  pair and the downstream steering to `SEMMISSINGREPOSEMTAIL`. This phase
  needs to refresh that lineage, not invent a new evidence surface.
- `specs/phase-plans-v7.md` currently ends at this phase. If execution clears
  the named seam and reveals a newer blocker beyond the current roadmap tail,
  closeout must extend the roadmap before handing off so `.phase-loop/`
  remains truthful about the next unplanned phase.

Practical planning boundary:

- SEMMISSINGREPOSEMTAIL may tighten exact bounded Python handling for
  `scripts/index_missing_repos_semantic.py` and
  `scripts/identify_working_indexes.py`, make the smallest script-local
  simplification only if tests prove a file-local structure hotspot, refresh
  durable trace persistence and repository-status wording, rerun the repo-local
  force-full sync, refresh the dogfood evidence report, and extend the roadmap
  only if a newer blocker appears beyond the current tail.
- SEMMISSINGREPOSEMTAIL must stay narrow and evidence-driven. It must not
  reopen the already-cleared
  `scripts/check_test_index_schema.py ->
  scripts/ensure_test_repos_indexed.py` seam, add a broad `scripts/*.py`
  bypass, raise the global lexical watchdog, or widen into unrelated semantic
  or release work unless the refreshed rerun proves the blocker has moved.
- Because the new pair is not yet covered by `_EXACT_BOUNDED_PYTHON_PATHS`,
  execution should first prove whether the active cost is solved by extending
  the exact bounded-path contract for this pair before mutating the script
  sources themselves.

## Interface Freeze Gates

- [ ] IF-0-SEMMISSINGREPOSEMTAIL-1 - Exact missing-repo script pair advance
      contract: a refreshed repo-local force-full rerun on the
      post-SEMTESTREPOINDEXTAIL head no longer terminalizes with the durable
      lexical trace centered on
      `scripts/index_missing_repos_semantic.py ->
      scripts/identify_working_indexes.py`; it either advances durably beyond
      that exact pair or emits a truthful newer blocker before the 120-second
      watchdog expires.
- [ ] IF-0-SEMMISSINGREPOSEMTAIL-2 - Exact boundary contract:
      any repair introduced by this phase remains limited to the exact named
      script pair and the immediate dispatcher, trace, status, evidence, and
      roadmap-steering plumbing needed to clear it. The phase must not reopen
      the repaired
      `scripts/check_test_index_schema.py ->
      scripts/ensure_test_repos_indexed.py`
      seam or broaden to a general `scripts/*.py` bypass without direct
      evidence.
- [ ] IF-0-SEMMISSINGREPOSEMTAIL-3 - Lexical discoverability contract:
      both exact scripts remain lexically discoverable after the repair,
      including durable file storage plus stable symbol and text
      discoverability for the currently checked-in script surfaces
      (`get_existing_collections`, `find_missing_repositories`,
      `estimate_repo_size`, `get_repo_hash`, `check_index_health`,
      `find_test_repos`, and `main`) instead of turning either file into an
      indexing blind spot.
- [ ] IF-0-SEMMISSINGREPOSEMTAIL-4 - Durable trace and operator contract:
      `force_full_exit_trace.json`, `GitAwareIndexManager`, and
      `uv run mcp-index repository status` stay aligned with the repaired
      outcome for the exact script pair, preserve the fail-closed readiness
      vocabulary, and do not regress to stale SEMTESTREPOINDEXTAIL-only
      boundary wording once the rerun advances beyond the pair.
- [ ] IF-0-SEMMISSINGREPOSEMTAIL-5 - Evidence and downstream steering
      contract: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMTESTREPOINDEXTAIL rerun outcome and the final authoritative verdict
      for the missing-repo script pair, and if execution exposes a blocker
      beyond the current roadmap tail, `specs/phase-plans-v7.md` is amended
      before closeout so `.phase-loop/` points to the newest truthful next
      phase instead of stopping at a stale tail.

## Lane Index & Dependencies

- SL-0 - Exact missing-repo script seam contract freeze; Depends on: SEMTESTREPOINDEXTAIL; Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 - Exact bounded script-pair repair or minimal script-local simplification; Depends on: SL-0; Blocks: SL-2, SL-3, SL-4; Parallel-safe: no
- SL-2 - Durable trace persistence and operator boundary alignment; Depends on: SL-0, SL-1; Blocks: SL-3, SL-4; Parallel-safe: no
- SL-3 - Live rerun evidence reducer and SEMMISSINGREPOSEMTAIL contract refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SL-4; Parallel-safe: no
- SL-4 - Downstream roadmap steering reducer; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: SEMMISSINGREPOSEMTAIL acceptance; Parallel-safe: no

Lane DAG:

```text
SEMTESTREPOINDEXTAIL
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SL-4 -> SEMMISSINGREPOSEMTAIL acceptance
```

## Lanes

### SL-0 - Exact Missing-Repo Script Seam Contract Freeze

- **Scope**: Freeze the exact
  `scripts/index_missing_repos_semantic.py ->
  scripts/identify_working_indexes.py` lexical seam in deterministic
  dispatcher coverage so this phase proves a narrow repair instead of assuming
  the newly exposed later script blocker will disappear on its own.
- **Owned files**: `tests/test_dispatcher.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMMISSINGREPOSEMTAIL-1,
  IF-0-SEMMISSINGREPOSEMTAIL-2,
  and IF-0-SEMMISSINGREPOSEMTAIL-3 at the dispatcher boundary
- **Interfaces consumed**: existing
  `Dispatcher.index_directory(...)`,
  `_EXACT_BOUNDED_PYTHON_PATHS`,
  lexical file metadata storage,
  and the current checked-in content shape of
  `scripts/index_missing_repos_semantic.py` and
  `scripts/identify_working_indexes.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` with repo-shaped fixtures for
    `scripts/index_missing_repos_semantic.py`,
    `scripts/identify_working_indexes.py`, and a control script so the exact
    pair preserves durable file rows, stable symbols, zero code chunks, and
    FTS-backed discoverability once the bounded-path repair is in place.
  - test: Add negative guards so earlier repaired exact bounded Python seams
    such as
    `scripts/check_test_index_schema.py`,
    `scripts/ensure_test_repos_indexed.py`,
    `scripts/create_semantic_embeddings.py`, and
    `scripts/consolidate_real_performance_data.py`
    do not silently regress while the missing-repo pair is added.
  - test: Fail if the repair would turn either target script into an ignored
    lexical blind spot or would remove the currently stable helper symbols from
    indexed discoverability.
  - impl: Keep fixtures deterministic with repo-local Python strings and
    bounded-path assertions rather than long-running live waits inside unit
    coverage.
  - impl: Keep this lane on contract freeze only. Do not mutate dispatcher
    implementation, trace persistence, CLI wording, evidence docs, roadmap
    steering, or the checked-in script sources here.
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "index_missing_repos_semantic or identify_working_indexes or lexical or bounded or missing_repo or script"`

### SL-1 - Exact Bounded Script-Pair Repair Or Minimal Script-Local Simplification

- **Scope**: Implement the smallest repair needed so the live lexical walker no
  longer burns its watchdog budget on the exact
  `scripts/index_missing_repos_semantic.py ->
  scripts/identify_working_indexes.py` pair.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `scripts/index_missing_repos_semantic.py`, `scripts/identify_working_indexes.py`
- **Interfaces provided**: IF-0-SEMMISSINGREPOSEMTAIL-1 exact advance
  contract; IF-0-SEMMISSINGREPOSEMTAIL-2 exact boundary contract;
  IF-0-SEMMISSINGREPOSEMTAIL-3 lexical discoverability contract
- **Interfaces consumed**: SL-0 exact-pair fixtures; existing
  `_EXACT_BOUNDED_PYTHON_PATHS`; current lexical timeout behavior in
  `_index_file_with_lexical_timeout(...)`; and the current structure of the
  two exact script files
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
    `scripts/index_missing_repos_semantic.py` or
    `scripts/identify_working_indexes.py` that allows the current watchdog to
    advance beyond the pair.
  - impl: Only edit the script sources if tests prove the active hotspot is
    file-local structure rather than missing exact bounded-path handling.
    Preserve the scripts' intended operational meaning, stable helper symbols,
    and output artifact names.
  - impl: Preserve durable file rows and lexical discoverability for both
    scripts; the repair must not turn either script into an ignored source file
    or silently remove it from lexical FTS.
  - impl: Keep the repair exact-script narrow. Do not add a broad
    `scripts/*.py` bypass, and do not raise the global lexical timeout just to
    move the seam.
  - verify: `rg -n "index_missing_repos_semantic|identify_working_indexes|EXACT_BOUNDED_PYTHON_PATHS|lexical_timeout" mcp_server/dispatcher/dispatcher_enhanced.py scripts/index_missing_repos_semantic.py scripts/identify_working_indexes.py`
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "index_missing_repos_semantic or identify_working_indexes or lexical or bounded or missing_repo or script"`

### SL-2 - Durable Trace Persistence And Operator Boundary Alignment

- **Scope**: Carry the chosen missing-repo repair through force-full closeout
  and keep the operator-facing status surface aligned with the exact pair that
  was repaired.
- **Owned files**: `mcp_server/storage/git_index_manager.py`, `mcp_server/cli/repository_commands.py`, `tests/test_git_index_manager.py`, `tests/test_repository_commands.py`
- **Interfaces provided**: IF-0-SEMMISSINGREPOSEMTAIL-1 exact advance
  contract; IF-0-SEMMISSINGREPOSEMTAIL-4 durable trace and operator contract
- **Interfaces consumed**: SL-0 exact-pair fixtures; SL-1 chosen repair;
  existing lexical progress snapshot fields, durable
  `force_full_exit_trace.json` persistence, and the current status wording for
  neighboring exact bounded Python seams
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_git_index_manager.py` so force-full durable trace
    coverage preserves the exact
    `scripts/index_missing_repos_semantic.py ->
    scripts/identify_working_indexes.py` pair when that seam is still active,
    then proves the trace advances beyond both files once the repair is in
    place without regressing to stale SEMTESTREPOINDEXTAIL-only wording.
  - test: Extend `tests/test_repository_commands.py` so
    `uv run mcp-index repository status` renders an exact bounded Python
    boundary line for
    `scripts/index_missing_repos_semantic.py ->
    scripts/identify_working_indexes.py`, preserves `Last progress path` and
    `In-flight path`, and keeps the current readiness, rollout, and semantic
    fail-closed vocabulary intact.
  - test: Guard against regressions by proving the new exact status line does
    not leak older script seams such as
    `scripts/check_test_index_schema.py`,
    `scripts/ensure_test_repos_indexed.py`, or
    `scripts/consolidate_real_performance_data.py`
    into this phase's operator output.
  - impl: Thread the chosen repair through durable trace persistence and
    operator wording only as needed so the rerun can advance beyond the exact
    pair.
  - impl: Preserve the existing force-full trace fields, fail-closed
    indexed-commit behavior, and lexical watchdog semantics. This lane should
    move the handoff forward, not rename stages or declare readiness early.
  - impl: If SL-1 alone is sufficient and no runtime storage change is
    required, keep this lane scoped to status wording plus trace fixtures
    rather than inventing extra persistence behavior.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "index_missing_repos_semantic or identify_working_indexes or lexical or interrupted or boundary or missing_repo or script"`

### SL-3 - Live Rerun Evidence Reducer And SEMMISSINGREPOSEMTAIL Contract Refresh

- **Scope**: Refresh the repo-local dogfood report so it records the chosen
  missing-repo repair, the rerun outcome, and the next exact downstream status
  after this seam is cleared.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: the evidence portion of
  IF-0-SEMMISSINGREPOSEMTAIL-5
- **Interfaces consumed**: SL-1 chosen repair; SL-2 rerun command, durable
  trace, and repository-status wording; roadmap SEMMISSINGREPOSEMTAIL exit
  criteria; prior SEMTESTREPOINDEXTAIL evidence lineage
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/docs/test_semdogfood_evidence_contract.py` so the
    refreshed report cites
    `plans/phase-plan-v7-SEMMISSINGREPOSEMTAIL.md`,
    `scripts/index_missing_repos_semantic.py`,
    `scripts/identify_working_indexes.py`, the chosen repair, the rerun
    outcome, and the final authoritative verdict for the missing-repo script
    pair.
  - test: Require the report to preserve the existing evidence lineage for the
    already-cleared SEMTESTREPOINDEXTAIL seam while making clear that the
    active current-head blocker has moved to this exact pair or beyond it.
  - impl: Update `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` with the live
    SEMMISSINGREPOSEMTAIL rerun command, timestamps, refreshed trace snapshot,
    repository-status terminalization, and current SQLite counts so the report
    proves whether the repaired rerun advanced beyond the pair or surfaced a
    newer blocker.
  - impl: If the rerun advances to a later blocker, make the report name that
    blocker exactly and mark the missing-repo seam as cleared. If the rerun
    still ends at the exact pair, keep the report truthful and do not pretend
    the boundary is repaired.
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "SEMMISSINGREPOSEMTAIL or index_missing_repos_semantic or identify_working_indexes or missing_repo or script"`
  - verify: `rg -n "SEMMISSINGREPOSEMTAIL|index_missing_repos_semantic|identify_working_indexes|SEMTESTREPOINDEXTAIL|force_full_exit_trace|Trace status|roadmap now adds downstream phase" docs/status/SEMANTIC_DOGFOOD_REBUILD.md tests/docs/test_semdogfood_evidence_contract.py`

### SL-4 - Downstream Roadmap Steering Reducer

- **Scope**: Keep the roadmap and next phase-loop step truthful if the repaired
  live rerun proves a newer blocker beyond the current roadmap tail.
- **Owned files**: `specs/phase-plans-v7.md`
- **Interfaces provided**: the downstream-steering portion of
  IF-0-SEMMISSINGREPOSEMTAIL-5
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
    `scripts/index_missing_repos_semantic.py ->
    scripts/identify_working_indexes.py` pair, leave the roadmap unchanged.
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
`codex-execute-phase` or manual SEMMISSINGREPOSEMTAIL execution.

Lane-specific checks:

```bash
uv run pytest tests/test_dispatcher.py -q --no-cov -k "index_missing_repos_semantic or identify_working_indexes or lexical or bounded or missing_repo or script"
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "index_missing_repos_semantic or identify_working_indexes or lexical or interrupted or boundary or missing_repo or script"
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "SEMMISSINGREPOSEMTAIL or index_missing_repos_semantic or identify_working_indexes or missing_repo or script"
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
  -q --no-cov -k "index_missing_repos_semantic or identify_working_indexes or lexical or interrupted or boundary or missing_repo or script"
timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
git status --short -- plans/phase-plan-v7-SEMMISSINGREPOSEMTAIL.md docs/status/SEMANTIC_DOGFOOD_REBUILD.md specs/phase-plans-v7.md
git diff --check
git diff --cached --check
```

## Acceptance Criteria

- [ ] A refreshed repo-local force-full rerun on the post-SEMTESTREPOINDEXTAIL
      head either advances durably beyond
      `scripts/index_missing_repos_semantic.py ->
      scripts/identify_working_indexes.py`
      or emits a truthful newer blocker before the 120-second watchdog expires.
- [ ] The chosen repair for the missing-repo semantic index script seam stays
      narrow, tested, and does not reopen the already-cleared
      `scripts/check_test_index_schema.py ->
      scripts/ensure_test_repos_indexed.py`
      boundary without direct evidence.
- [ ] Both exact scripts remain lexically discoverable with durable file
      storage and stable symbol/text discoverability for the currently checked-
      in script surfaces.
- [ ] `force_full_exit_trace.json` and
      `uv run mcp-index repository status` stay aligned with the repaired
      outcome for the exact script pair and preserve the fail-closed semantic
      readiness vocabulary.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMTESTREPOINDEXTAIL rerun outcome and the final live verdict for the
      missing-repo semantic index script pair.
- [ ] If the rerun exposes a blocker beyond the current roadmap tail,
      `specs/phase-plans-v7.md` is updated before closeout so the next
      phase-loop step stays truthful.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v7-SEMMISSINGREPOSEMTAIL.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMMISSINGREPOSEMTAIL.md
  artifact_state: staged
```
