---
phase_loop_plan_version: 1
phase: SEMQUERYFULLTAIL
roadmap: specs/phase-plans-v7.md
roadmap_sha256: 963624e51181c066ed886710d069a63f324aec776718e851acd13ef2110b6ee3
---
# SEMQUERYFULLTAIL: Comprehensive Query And Full Semantic Script Tail Recovery

## Context

SEMQUERYFULLTAIL is the phase-77 follow-up for the v7 semantic hardening
roadmap. Canonical `.phase-loop/` runtime exists in this checkout, so it is
the authoritative runner state for this planning run. The current canonical
snapshots agree cleanly: `.phase-loop/state.json` and
`.phase-loop/tui-handoff.md` both identify `SEMQUERYFULLTAIL` as the current
`unplanned` phase for `specs/phase-plans-v7.md`, and the recorded roadmap hash
matches the user-required
`963624e51181c066ed886710d069a63f324aec776718e851acd13ef2110b6ee3`.
Legacy `.codex/phase-loop/` artifacts remain compatibility-only and do not
supersede canonical `.phase-loop/` state here.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is the active roadmap, and canonical
  `.phase-loop/state.json` records the same required hash
  `963624e51181c066ed886710d069a63f324aec776718e851acd13ef2110b6ee3`.
- The checkout is on `main...origin/main [ahead 149]` at `HEAD`
  `25766a232dc9cc5bcdbb584d871ce19db795d2a1`, the worktree is clean before
  this artifact write, and `plans/phase-plan-v7-SEMQUERYFULLTAIL.md` did not
  exist before this run.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is the active evidence anchor.
  Its `SEMSCRIPTLANGSTAIL Live Rerun Check` block records that the refreshed
  repo-local command
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  advanced on observed commit
  `96bc35b08ac83baafd50192cd8a56a22d9601a0d`, moved durably beyond
  `scripts/migrate_large_index_to_multi_repo.py ->
  scripts/check_index_languages.py`, and then terminalized later at
  `2026-04-30T00:12:27Z` with the durable lexical trace already anchored on
  `scripts/run_comprehensive_query_test.py ->
  scripts/index_all_repos_semantic_full.py`.
- That same evidence block shows the current exact blocker shape that this
  phase must resolve truthfully: at `2026-04-30T00:12:10Z`,
  `.mcp-index/force_full_exit_trace.json` still showed `status: running`,
  `stage: lexical_walking`,
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/scripts/run_comprehensive_query_test.py`,
  and
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/scripts/index_all_repos_semantic_full.py`.
  The rerun no longer blames the cleared script-language rebound seam, but it
  does not yet prove whether the remaining timeout is still pair-local or
  whether the exact comprehensive-query/full-sync pair has already completed
  lexical work and the real missing contract is durable closeout or later
  blocker promotion.
- SQLite runtime counts after that rerun remained
  `files = 1064`, `code_chunks = 13095`, `chunk_summaries = 0`, and
  `semantic_points = 0`, so semantic summaries and vectors still have not
  resumed; this remains a pre-semantic lexical blocker or handoff-truthfulness
  slice.
- The current later script pair is not yet covered by the exact bounded
  rebound contract surfaces used for the earlier tails. A repo search found no
  current `run_comprehensive_query_test` or `index_all_repos_semantic_full`
  references inside `mcp_server/dispatcher/dispatcher_enhanced.py`,
  `mcp_server/cli/repository_commands.py`,
  `tests/test_dispatcher.py`,
  `tests/test_git_index_manager.py`, or
  `tests/test_repository_commands.py`, so this phase starts without a frozen
  dispatcher map entry, operator boundary line, or targeted durable-trace
  tests for the exact pair.
- The two scripts are still large enough to justify an exact-pair-first repair
  strategy before source edits. `scripts/run_comprehensive_query_test.py` is
  `402` lines and currently exposes the top-level
  `ParallelQueryTester` class plus `run_all_repository_tests`,
  `aggregate_results`, and `main`. `scripts/index_all_repos_semantic_full.py`
  is `380` lines and currently exposes `get_all_code_files`,
  `create_embeddings_batch`, `process_repository`,
  `find_test_repositories`, and `main`.
- The current code surfaces also explain why discoverability must stay
  explicit if the pair is exact-bounded. `run_comprehensive_query_test.py`
  carries async query orchestration, repo result aggregation, and static
  semantic/BM25 query corpora, while
  `index_all_repos_semantic_full.py` carries repository walking, chunking,
  Voyage/Qdrant integration, full-result persistence, and repository-mapping
  generation. Any repair must preserve those lexical and symbol-level surfaces
  rather than turning either script into an indexing blind spot.
- `tests/docs/test_semdogfood_evidence_contract.py` and the dogfood report
  already mention `SEMQUERYFULLTAIL` and the later exact pair, but there is
  not yet a phase-local plan artifact or execution-ready contract for how the
  dispatcher, durable trace, status output, and evidence should clear or
  truthfully supersede this exact pair.

Practical planning boundary:

- SEMQUERYFULLTAIL may tighten exact bounded Python handling for
  `scripts/run_comprehensive_query_test.py` and
  `scripts/index_all_repos_semantic_full.py`, make the smallest script-local
  simplification only if tests and the current-head rerun prove a file-local
  structure hotspot, refresh durable trace persistence and repository-status
  wording, rerun the repo-local force-full sync, refresh the dogfood evidence
  report, and extend the roadmap only if a newer blocker appears beyond the
  current tail.
- SEMQUERYFULLTAIL must stay narrow and evidence-driven. It must not reopen
  the already-cleared
  `scripts/migrate_large_index_to_multi_repo.py ->
  scripts/check_index_languages.py`
  seam, add a broad `scripts/*.py` or repo-wide lexical-timeout bypass, or
  widen into unrelated semantic or release work unless the refreshed rerun
  proves the blocker has moved again.
- Because the newly exposed pair is not yet covered by the exact bounded
  Python map or status surface, execution should first prove whether the
  active cost is solved by extending the exact bounded-path contract for this
  pair before mutating the script sources themselves.

## Interface Freeze Gates

- [ ] IF-0-SEMQUERYFULLTAIL-1 - Exact comprehensive-query/full-sync pair
      advance contract: a refreshed repo-local force-full rerun on the
      post-SEMSCRIPTLANGSTAIL head no longer terminalizes with the durable
      lexical trace centered on
      `scripts/run_comprehensive_query_test.py ->
      scripts/index_all_repos_semantic_full.py`; it either advances durably
      beyond that exact pair or emits a truthful newer blocker before the
      120-second watchdog expires.
- [ ] IF-0-SEMQUERYFULLTAIL-2 - Exact boundary contract:
      any repair introduced by this phase remains limited to the exact named
      script pair and the immediate dispatcher, trace, status, evidence, and
      roadmap-steering plumbing needed to clear it. The phase must not reopen
      the repaired
      `scripts/migrate_large_index_to_multi_repo.py ->
      scripts/check_index_languages.py`
      seam or widen to a general script-family bypass without direct evidence.
- [ ] IF-0-SEMQUERYFULLTAIL-3 - Lexical discoverability contract:
      both exact scripts remain lexically discoverable after the repair,
      including durable file storage plus stable symbol and text
      discoverability for the current checked-in script surfaces
      (`ParallelQueryTester`,
      `test_bm25_query`,
      `test_semantic_query`,
      `test_queries_batch`,
      `test_repository`,
      `run_all_repository_tests`,
      `aggregate_results`,
      `get_all_code_files`,
      `create_embeddings_batch`,
      `process_repository`,
      `find_test_repositories`, and `main`) instead of turning either file
      into an indexing blind spot.
- [ ] IF-0-SEMQUERYFULLTAIL-4 - Durable trace and operator contract:
      `force_full_exit_trace.json`, `GitAwareIndexManager`, and
      `uv run mcp-index repository status` stay aligned with the repaired
      outcome for the exact comprehensive-query/full-sync pair, preserve the
      fail-closed readiness vocabulary, and do not regress to stale
      SEMSCRIPTLANGSTAIL-only boundary wording once the rerun advances beyond
      the pair.
- [ ] IF-0-SEMQUERYFULLTAIL-5 - Evidence and downstream steering contract:
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMSCRIPTLANGSTAIL rerun outcome and the final authoritative verdict for
      the comprehensive-query/full-sync script pair, and if execution exposes
      a blocker beyond the current roadmap tail,
      `specs/phase-plans-v7.md` is amended before closeout so `.phase-loop/`
      points to the newest truthful next phase instead of stopping at a stale
      tail.

## Lane Index & Dependencies

- SL-0 - Exact comprehensive-query/full-sync seam contract freeze; Depends on: SEMSCRIPTLANGSTAIL; Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 - Exact bounded comprehensive-query/full-sync repair or minimal script-local simplification; Depends on: SL-0; Blocks: SL-2, SL-3, SL-4; Parallel-safe: no
- SL-2 - Durable trace persistence and operator boundary alignment; Depends on: SL-0, SL-1; Blocks: SL-3, SL-4; Parallel-safe: no
- SL-3 - Live rerun evidence reducer and SEMQUERYFULLTAIL contract refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SL-4; Parallel-safe: no
- SL-4 - Downstream roadmap steering reducer; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: SEMQUERYFULLTAIL acceptance; Parallel-safe: no

Lane DAG:

```text
SEMSCRIPTLANGSTAIL
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SL-4 -> SEMQUERYFULLTAIL acceptance
```

## Lanes

### SL-0 - Exact Comprehensive-Query/Full-Sync Seam Contract Freeze

- **Scope**: Freeze the exact
  `scripts/run_comprehensive_query_test.py ->
  scripts/index_all_repos_semantic_full.py`
  lexical seam in deterministic dispatcher coverage so this phase proves a
  narrow repair instead of assuming the later blocker will clear on its own.
- **Owned files**: `tests/test_dispatcher.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMQUERYFULLTAIL-1,
  IF-0-SEMQUERYFULLTAIL-2,
  and IF-0-SEMQUERYFULLTAIL-3 at the dispatcher boundary
- **Interfaces consumed**: existing `Dispatcher.index_directory(...)`,
  `_EXACT_BOUNDED_PYTHON_PATHS`,
  lexical file metadata storage,
  and the current checked-in content shape of
  `scripts/run_comprehensive_query_test.py` and
  `scripts/index_all_repos_semantic_full.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` with repo-shaped fixtures for
    `scripts/run_comprehensive_query_test.py`,
    `scripts/index_all_repos_semantic_full.py`, and a control script so the
    exact pair preserves durable file rows, stable symbols, zero code chunks,
    and FTS-backed discoverability once the bounded-path repair is in place.
  - test: Add negative guards so the earlier repaired exact bounded Python
    seams such as
    `scripts/migrate_large_index_to_multi_repo.py`,
    `scripts/check_index_languages.py`,
    `scripts/analyze_claude_code_edits.py`, and
    `scripts/verify_mcp_retrieval.py`
    do not silently regress while the comprehensive-query/full-sync pair is
    added.
  - test: Add explicit assertions that once the pair clears lexical walking,
    snapshots promote later work into `force_full_closeout_handoff` instead of
    leaving the exact pair as a stale lexical placeholder.
  - test: Fail if the repair would turn either target script into an ignored
    lexical blind spot or would remove the current stable helper surfaces from
    indexed discoverability.
  - impl: Keep fixtures deterministic with repo-local Python strings and
    bounded-path assertions rather than long-running live waits inside unit
    coverage.
  - impl: Keep this lane on contract freeze only. Do not mutate dispatcher
    implementation, trace persistence, CLI wording, evidence docs, roadmap
    steering, or the checked-in script sources here.
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "run_comprehensive_query_test or index_all_repos_semantic_full or comprehensive_query or full_semantic or lexical or bounded"`

### SL-1 - Exact Bounded Comprehensive-Query/Full-Sync Repair Or Minimal Script-Local Simplification

- **Scope**: Implement the smallest repair needed so the live lexical walker
  no longer burns its watchdog budget on the exact
  `scripts/run_comprehensive_query_test.py ->
  scripts/index_all_repos_semantic_full.py`
  pair.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `scripts/run_comprehensive_query_test.py`, `scripts/index_all_repos_semantic_full.py`
- **Interfaces provided**: IF-0-SEMQUERYFULLTAIL-1 exact advance contract;
  IF-0-SEMQUERYFULLTAIL-2 exact boundary contract;
  IF-0-SEMQUERYFULLTAIL-3 lexical discoverability contract
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
    `scripts/run_comprehensive_query_test.py` or
    `scripts/index_all_repos_semantic_full.py` that allows the current
    watchdog to advance beyond the pair.
  - impl: Only edit the script sources if tests and the current-head rerun
    prove the active hotspot is file-local structure rather than missing exact
    bounded-path handling. Preserve the scripts' intended operational meaning,
    stable helper/class names, query/indexing behavior, and current artifact
    filenames.
  - impl: Preserve durable file rows and lexical discoverability for both
    scripts; the repair must not turn either script into an ignored source
    file or silently remove it from lexical FTS.
  - verify: `rg -n "run_comprehensive_query_test|index_all_repos_semantic_full|_EXACT_BOUNDED_PYTHON_PATHS|bounded" mcp_server/dispatcher/dispatcher_enhanced.py scripts/run_comprehensive_query_test.py scripts/index_all_repos_semantic_full.py tests/test_dispatcher.py`
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "run_comprehensive_query_test or index_all_repos_semantic_full or comprehensive_query or full_semantic or lexical or bounded"`

### SL-2 - Durable Trace Persistence And Operator Boundary Alignment

- **Scope**: Keep durable force-full trace output and operator-visible status
  wording aligned with the repaired comprehensive-query/full-sync boundary and
  any newer blocker it reveals.
- **Owned files**: `mcp_server/storage/git_index_manager.py`, `mcp_server/cli/repository_commands.py`, `tests/test_git_index_manager.py`, `tests/test_repository_commands.py`
- **Interfaces provided**: IF-0-SEMQUERYFULLTAIL-4 durable trace and operator
  contract
- **Interfaces consumed**: SL-0 exact-pair fixture vocabulary; SL-1 chosen
  repair shape; existing force-full trace fields such as `status`, `stage`,
  `stage_family`, `last_progress_path`, `in_flight_path`, and
  `blocker_source`; and current repository-status readiness wording
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_git_index_manager.py` so interrupted and
    post-pair-later-blocker traces preserve
    `scripts/run_comprehensive_query_test.py ->
    scripts/index_all_repos_semantic_full.py`
    when it is the truthful active seam, and stop preserving it once the
    rerun has clearly moved to a later path or closeout stage.
  - test: Extend `tests/test_repository_commands.py` with the exact operator
    boundary string for this pair and with assertions that `repository status`
    reports the later blocker paths without regressing to stale
    SEMSCRIPTLANGSTAIL-only wording.
  - impl: Add the minimal repository-status boundary helper for the exact pair
    and keep it consistent with the earlier exact bounded Python boundary
    helpers already used by the tail phases.
  - impl: Keep durable trace and status output truthful if the current-head
    rerun clears the pair and reaches a later blocker or a
    `force_full_closeout_handoff` stage. Do not leave stale blame on
    `scripts/index_all_repos_semantic_full.py` once lexical work has already
    advanced beyond it.
  - impl: Preserve fail-closed readiness/query vocabulary, semantic readiness
    reporting, and existing operator metadata outside the exact pair and its
    truthful successor stage.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "run_comprehensive_query_test or index_all_repos_semantic_full or comprehensive_query or full_semantic or lexical or interrupted or boundary"`

### SL-3 - Live Rerun Evidence Reducer And SEMQUERYFULLTAIL Contract Refresh

- **Scope**: Refresh the dogfood evidence so it records the
  SEMQUERYFULLTAIL rerun command, timestamps, trace/status outputs, runtime
  counts, and final verdict for the exact comprehensive-query/full-sync pair.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: the evidence portion of
  IF-0-SEMQUERYFULLTAIL-5
- **Interfaces consumed**: SL-1 repair outcome; SL-2 trace/status wording;
  canonical repo-local rerun command; `.mcp-index/force_full_exit_trace.json`;
  SQLite runtime counts; and the existing SEMSCRIPTLANGSTAIL evidence lineage
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/docs/test_semdogfood_evidence_contract.py` so the
    dogfood report expects `SEMQUERYFULLTAIL`, the new phase-plan lineage,
    the exact pair, the updated verification commands, and the final steering
    verdict for this seam.
  - impl: Add a `## SEMQUERYFULLTAIL Live Rerun Check` section that records
    the refreshed rerun command, timestamps, trace/status output, runtime
    counts, and whether the pair remained the active blocker or moved later.
  - impl: If the rerun still names the exact pair, the report must include why
    that attribution remains truthful on the current head; if the rerun moves
    later, the report must say the comprehensive-query/full-sync seam is no
    longer the active blocker and preserve the exact newer blocker or
    closeout-stage attribution.
  - impl: Keep this lane limited to the dogfood evidence artifact and its
    test. Do not mutate the roadmap here; SL-4 owns any required downstream
    phase-tail amendment.
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "SEMQUERYFULLTAIL or SEMSCRIPTLANGSTAIL or run_comprehensive_query_test or index_all_repos_semantic_full"`
  - verify: `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - verify: `sed -n '1,240p' .mcp-index/force_full_exit_trace.json`
  - verify: `sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'`

### SL-4 - Downstream Roadmap Steering Reducer

- **Scope**: Keep the v7 roadmap truthful if the refreshed current-head rerun
  exposes a blocker beyond the present roadmap tail.
- **Owned files**: `specs/phase-plans-v7.md`
- **Interfaces provided**: the roadmap-steering portion of
  IF-0-SEMQUERYFULLTAIL-5
- **Interfaces consumed**: SL-3 live rerun verdict; current phase-77 tail
  position in `specs/phase-plans-v7.md`; and canonical `.phase-loop/`
  expectation that the roadmap names the next unplanned phase truthfully
- **Parallel-safe**: no
- **Tasks**:
  - test: Re-read the end of `specs/phase-plans-v7.md` after the SL-3 rerun
    and only amend it if the refreshed current-head evidence proves a blocker
    beyond `scripts/run_comprehensive_query_test.py ->
    scripts/index_all_repos_semantic_full.py`.
  - impl: If the rerun reveals a newer blocker, append one downstream phase
    with the same exact-pair specificity used elsewhere in v7 and update any
    affected execution notes so `.phase-loop/` does not stop on a stale tail.
  - impl: If the rerun keeps the comprehensive-query/full-sync pair as the
    active truthful blocker, leave the roadmap unchanged and record that
    decision explicitly in the execution closeout and evidence.
  - impl: Keep this lane reducer-only. Do not reopen earlier phase-plan,
    docs, or script families that the rerun did not re-anchor on.
  - verify: `rg -n "SEMQUERYFULLTAIL|run_comprehensive_query_test.py|index_all_repos_semantic_full.py" specs/phase-plans-v7.md docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
  - verify: `git diff -- specs/phase-plans-v7.md`

## Verification

Planning-only run: do not execute these during plan creation. Run them during
`codex-execute-phase` or manual SEMQUERYFULLTAIL execution.

Lane-specific checks:

```bash
uv run pytest tests/test_dispatcher.py -q --no-cov -k "run_comprehensive_query_test or index_all_repos_semantic_full or comprehensive_query or full_semantic or lexical or bounded"
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "run_comprehensive_query_test or index_all_repos_semantic_full or comprehensive_query or full_semantic or lexical or interrupted or boundary"
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "SEMQUERYFULLTAIL or SEMSCRIPTLANGSTAIL or run_comprehensive_query_test or index_all_repos_semantic_full"
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
  -q --no-cov -k "run_comprehensive_query_test or index_all_repos_semantic_full or comprehensive_query or full_semantic or lexical or bounded or interrupted or boundary"
timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
git status --short -- plans/phase-plan-v7-SEMQUERYFULLTAIL.md docs/status/SEMANTIC_DOGFOOD_REBUILD.md specs/phase-plans-v7.md
git diff --check
git diff --cached --check
```

## Acceptance Criteria

- [ ] A refreshed repo-local force-full rerun on the post-SEMSCRIPTLANGSTAIL
      head either advances durably beyond
      `scripts/run_comprehensive_query_test.py ->
      scripts/index_all_repos_semantic_full.py`
      or emits a truthful newer blocker before the 120-second watchdog
      expires.
- [ ] The chosen repair for the later comprehensive-query/full-sync script
      seam stays narrow, tested, and does not reopen the already-cleared
      `scripts/migrate_large_index_to_multi_repo.py ->
      scripts/check_index_languages.py`
      boundary without direct evidence.
- [ ] Both exact scripts remain lexically discoverable with durable file
      storage and stable symbol/text discoverability for the current checked-in
      script surfaces.
- [ ] `force_full_exit_trace.json` and
      `uv run mcp-index repository status` stay aligned with the repaired
      outcome for the exact comprehensive-query/full-sync pair; if lexical
      walking has already completed, they truthfully promote the later
      closeout or successor blocker instead of leaving stale blame on
      `scripts/index_all_repos_semantic_full.py`.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMSCRIPTLANGSTAIL rerun outcome and the final live verdict for the
      later comprehensive-query/full-sync pair.
- [ ] If the rerun exposes a blocker beyond the current roadmap tail,
      `specs/phase-plans-v7.md` is updated before closeout so the next
      phase-loop step stays truthful.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMQUERYFULLTAIL.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMQUERYFULLTAIL.md
  artifact_state: staged
```
