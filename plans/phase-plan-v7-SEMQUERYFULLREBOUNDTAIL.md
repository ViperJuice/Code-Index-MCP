---
phase_loop_plan_version: 1
phase: SEMQUERYFULLREBOUNDTAIL
roadmap: specs/phase-plans-v7.md
roadmap_sha256: b997590a40e4f43736677297f9053a4b186a1c65ac0b1f90c0799919841e1af6
---
# SEMQUERYFULLREBOUNDTAIL: Comprehensive Query Tail Rebound Recovery

## Context

SEMQUERYFULLREBOUNDTAIL is the phase-81 follow-up for the v7 semantic
hardening roadmap. Canonical `.phase-loop/` runtime exists in this checkout,
so it is the authoritative runner state for this planning run. The current
canonical snapshots agree cleanly: `.phase-loop/state.json` and
`.phase-loop/tui-handoff.md` both identify `SEMQUERYFULLREBOUNDTAIL` as the
current `unplanned` phase for `specs/phase-plans-v7.md`, and the recorded
roadmap hash matches the user-required
`b997590a40e4f43736677297f9053a4b186a1c65ac0b1f90c0799919841e1af6`.
Legacy `.codex/phase-loop/` artifacts remain compatibility-only and do not
supersede canonical `.phase-loop/` state here.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is the active roadmap, it is tracked and clean in
  this worktree, and `sha256sum specs/phase-plans-v7.md` matches the required
  `b997590a40e4f43736677297f9053a4b186a1c65ac0b1f90c0799919841e1af6`.
- The checkout is on `main...origin/main [ahead 157]` at `HEAD`
  `3fe646211fccc035ad897b53e4cc5634f96439df`, the worktree is clean before
  this artifact write, and
  `plans/phase-plan-v7-SEMQUERYFULLREBOUNDTAIL.md` did not exist before this
  run.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is the active evidence anchor.
  Its `SEMCENTRALIZETAIL Live Rerun Check` block records that the refreshed
  repo-local command
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  advanced durably beyond
  `scripts/real_strategic_recommendations.py ->
  scripts/migrate_to_centralized.py`
  and later terminalized on the re-exposed comprehensive-query/full-sync tail.
- That same evidence block shows the exact current blocker shape that this
  phase must clear or truthfully supersede: at `2026-04-30T01:34:55Z`,
  `.mcp-index/force_full_exit_trace.json` still showed `status: running`,
  `stage: lexical_walking`,
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/scripts/run_comprehensive_query_test.py`,
  and
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/scripts/index_all_repos_semantic_full.py`,
  while at `2026-04-30T01:35:03Z` a refreshed `repository status`
  terminalized the rerun to `Trace status: interrupted` while preserving that
  same later durable pair.
- `repository status` on the same head remained semantically fail-closed
  after the rerun:
  `Readiness: stale_commit`, `Rollout status: partial_index_failure`,
  `Last sync error: disk I/O error`, and
  `Semantic readiness: summaries_missing`. SQLite runtime counts also remained
  `files = 1064`, `code_chunks = 13095`, `chunk_summaries = 0`, and
  `semantic_points = 0`, so this is still a lexical-tail and truth-surface
  slice rather than a semantic-vector recovery phase.
- Unlike the first SEMQUERYFULLTAIL pass, the current repo already carries
  exact bounded-path and operator surfaces for this pair. Repo search shows
  `scripts/run_comprehensive_query_test.py` and
  `scripts/index_all_repos_semantic_full.py` are already present in
  `_EXACT_BOUNDED_PYTHON_PATHS` inside
  `mcp_server/dispatcher/dispatcher_enhanced.py`, in the exact lexical
  boundary helper inside `mcp_server/cli/repository_commands.py`, and in
  targeted fixtures inside `tests/test_dispatcher.py`,
  `tests/test_git_index_manager.py`, and
  `tests/test_repository_commands.py`.
- Those existing fixtures already freeze bounded lexical discoverability for
  the checked-in script surfaces. `tests/test_dispatcher.py` currently proves
  durable file rows, zero code chunks, stable symbols, and FTS-backed
  discoverability for `ParallelQueryTester`,
  `test_bm25_query`,
  `test_semantic_query`,
  `test_queries_batch`,
  `test_repository`,
  `run_all_repository_tests`,
  `aggregate_results`,
  `get_all_code_files`,
  `create_embeddings_batch`,
  `process_repository`,
  `find_test_repositories`, and `main`.
- `tests/test_git_index_manager.py` and `tests/test_repository_commands.py`
  already freeze the current truthful trace vocabulary for the pair,
  including preservation of
  `scripts/run_comprehensive_query_test.py ->
  scripts/index_all_repos_semantic_full.py`
  when it is the active blocker and promotion beyond that pair when a later
  blocker or closeout handoff is surfaced.
- `tests/docs/test_semdogfood_evidence_contract.py` and the dogfood report
  already mention the SEMCENTRALIZETAIL steering outcome and the downstream
  `SEMQUERYFULLREBOUNDTAIL` phase, but there is not yet an execution-ready
  plan artifact defining how this rebound should distinguish a real remaining
  file-local hotspot from stale blame or from a later successor blocker.

Practical planning boundary:

- SEMQUERYFULLREBOUNDTAIL may tighten the existing exact bounded-path
  handling, trace promotion, status wording, or the smallest script-local
  simplification only if tests and the refreshed current-head rerun prove the
  re-exposed comprehensive-query/full-sync pair is still the truthful active
  watchdog cost.
- Because the current repo already contains exact bounded matcher, status,
  and fixture coverage for this pair, execution should treat any broader
  `scripts/*.py` matcher expansion as suspect. Prefer proving whether the
  remaining issue is file-local structure, stale blocker promotion, or a
  newer blocker exposed after the pair before changing broad lexical
  contracts.
- SEMQUERYFULLREBOUNDTAIL must stay narrow and evidence-driven. It must not
  reopen the repaired
  `scripts/real_strategic_recommendations.py ->
  scripts/migrate_to_centralized.py`
  seam, broaden earlier `.codex/phase-loop`, integration, or script-language
  family work, or widen into semantic-stage or release work unless the
  refreshed rerun proves the blocker has moved again.

## Interface Freeze Gates

- [ ] IF-0-SEMQUERYFULLREBOUNDTAIL-1 - Exact rebound advance contract:
      a refreshed repo-local force-full rerun on the
      post-SEMCENTRALIZETAIL head no longer terminalizes with the durable
      blocker centered on
      `scripts/run_comprehensive_query_test.py ->
      scripts/index_all_repos_semantic_full.py`; it either advances durably
      beyond that exact pair or emits a truthful newer blocker before the
      120-second watchdog expires.
- [ ] IF-0-SEMQUERYFULLREBOUNDTAIL-2 - Narrow rebound repair contract:
      any repair introduced by this phase remains limited to the exact
      comprehensive-query/full-sync pair and the immediate dispatcher, trace,
      CLI, evidence, and roadmap-steering plumbing needed to clear or
      truthfully supersede it. The phase must not reopen the repaired
      `scripts/real_strategic_recommendations.py ->
      scripts/migrate_to_centralized.py`
      seam without direct evidence.
- [ ] IF-0-SEMQUERYFULLREBOUNDTAIL-3 - Script discoverability contract:
      the exact pair remains lexically discoverable with durable file storage
      and stable symbol or text discoverability for
      `ParallelQueryTester`,
      `test_bm25_query`,
      `test_semantic_query`,
      `test_queries_batch`,
      `test_repository`,
      `run_all_repository_tests`,
      `aggregate_results`,
      `get_all_code_files`,
      `create_embeddings_batch`,
      `process_repository`,
      `find_test_repositories`, and `main` instead of turning either script
      into an indexing blind spot.
- [ ] IF-0-SEMQUERYFULLREBOUNDTAIL-4 - Durable trace and operator contract:
      `force_full_exit_trace.json` and
      `uv run mcp-index repository status` stay aligned with the repaired
      outcome once the centralization seam is already cleared, and they do
      not leave stale blame on
      `scripts/real_strategic_recommendations.py ->
      scripts/migrate_to_centralized.py`
      or on earlier intermediary script seams after durable progress has
      already moved back to the exact comprehensive-query/full-sync pair or
      later.
- [ ] IF-0-SEMQUERYFULLREBOUNDTAIL-5 - Evidence and downstream steering
      contract: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMCENTRALIZETAIL rerun outcome, the SEMQUERYFULLREBOUNDTAIL rerun
      command and timestamps, the refreshed durable trace and status output,
      and the final authoritative verdict for the comprehensive-query/full-sync
      seam; if execution exposes a blocker beyond the current roadmap tail,
      `specs/phase-plans-v7.md` is amended before closeout so `.phase-loop/`
      points to the newest truthful next phase.

## Lane Index & Dependencies

- SL-0 - Exact comprehensive-query rebound contract freeze; Depends on: SEMCENTRALIZETAIL; Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 - Durable trace and repository-status rebound fixtures; Depends on: SL-0; Blocks: SL-2, SL-3, SL-4; Parallel-safe: no
- SL-2 - Minimal comprehensive-query rebound repair or script-local simplification; Depends on: SL-0, SL-1; Blocks: SL-3, SL-4; Parallel-safe: no
- SL-3 - Live rerun evidence reducer and SEMQUERYFULLREBOUNDTAIL contract refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SL-4; Parallel-safe: no
- SL-4 - Downstream roadmap steering reducer; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: SEMQUERYFULLREBOUNDTAIL acceptance; Parallel-safe: no

Lane DAG:

```text
SEMCENTRALIZETAIL
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SL-4 -> SEMQUERYFULLREBOUNDTAIL acceptance
```

## Lanes

### SL-0 - Exact Comprehensive-Query Rebound Contract Freeze

- **Scope**: Freeze the exact
  `scripts/run_comprehensive_query_test.py ->
  scripts/index_all_repos_semantic_full.py`
  rebound in deterministic dispatcher coverage so this phase proves a narrow
  repair instead of reopening broad matcher work that is already present.
- **Owned files**: `tests/test_dispatcher.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMQUERYFULLREBOUNDTAIL-1,
  IF-0-SEMQUERYFULLREBOUNDTAIL-2, and
  IF-0-SEMQUERYFULLREBOUNDTAIL-3 at the dispatcher boundary
- **Interfaces consumed**: existing
  `Dispatcher.index_directory(...)`,
  `_EXACT_BOUNDED_PYTHON_PATHS`,
  lexical file metadata storage,
  and the current checked-in content shape of
  `scripts/run_comprehensive_query_test.py` and
  `scripts/index_all_repos_semantic_full.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Re-freeze the exact pair in `tests/test_dispatcher.py` with
    repo-shaped fixtures that prove the current bounded-path contract still
    preserves durable file rows, zero code chunks, stable symbols, and
    FTS-backed discoverability for the pair on the rebound head.
  - test: Add negative guards that the cleared centralization pair
    `scripts/real_strategic_recommendations.py ->
    scripts/migrate_to_centralized.py`
    does not silently reappear as the active lexical boundary once the
    rebound fixtures are refreshed.
  - test: Fail if the repair would clear the seam by turning either target
    script into an ignored lexical blind spot or by widening the matcher to a
    generic `scripts/*.py` bypass.
  - impl: Keep fixtures deterministic with repo-local Python strings and
    synthetic indexing assertions rather than long-running force-full waits
    inside unit coverage.
  - impl: Keep this lane on contract freeze only. Do not mutate dispatcher or
    CLI implementation, the checked-in scripts, evidence docs, or roadmap
    steering here.
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "run_comprehensive_query_test or index_all_repos_semantic_full or comprehensive_query or full_semantic or lexical or bounded"`

### SL-1 - Durable Trace And Repository-Status Rebound Fixtures

- **Scope**: Freeze the exact rebound pair at the durable trace and operator
  surface so execution can distinguish a real remaining script-tail cost from
  stale centralization blame or from a later successor blocker.
- **Owned files**: `tests/test_git_index_manager.py`, `tests/test_repository_commands.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMQUERYFULLREBOUNDTAIL-1,
  IF-0-SEMQUERYFULLREBOUNDTAIL-2, and
  IF-0-SEMQUERYFULLREBOUNDTAIL-4
- **Interfaces consumed**: existing durable trace lifecycle in
  `GitAwareIndexManager`; repository-status interrupted and stale-running
  output; the exact comprehensive-query boundary helper in
  `repository_commands.py`; and the current later-pair evidence from
  `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend or refresh `tests/test_git_index_manager.py` so a lexical
    rerun that has already advanced beyond the cleared centralization seam
    can still preserve the exact comprehensive-query/full-sync pair when that
    pair remains the truthful blocker, then promote a later blocker or
    closeout status once the pair has been cleared.
  - test: Extend or refresh `tests/test_repository_commands.py` so
    `uv run mcp-index repository status` can be frozen against the exact
    comprehensive-query/full-sync pair on the rebound head rather than
    leaving the active blocker on the cleared centralization seam or on an
    older intermediary pair.
  - test: Keep negative guards that the repaired centralization boundary
    remains intact and that SEMCENTRALIZETAIL-era blame does not regress into
    the active blocker once the rebound fixtures are introduced.
  - impl: Model closeout and successor promotion with synthetic trace payloads
    or monkeypatched manager behavior rather than live `sync --force-full`
    execution inside unit tests.
  - impl: Keep this lane fixture-only. Do not update production dispatcher,
    CLI, evidence, or roadmap code here.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "run_comprehensive_query_test or index_all_repos_semantic_full or comprehensive_query or full_semantic or lexical or interrupted or boundary or closeout_handoff"`

### SL-2 - Minimal Comprehensive-Query Rebound Repair Or Script-Local Simplification

- **Scope**: Implement the smallest repair needed so the current-head
  force-full rerun no longer leaves
  `scripts/run_comprehensive_query_test.py ->
  scripts/index_all_repos_semantic_full.py`
  as the active lexical watchdog tail.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `mcp_server/storage/git_index_manager.py`, `mcp_server/cli/repository_commands.py`, `scripts/run_comprehensive_query_test.py`, `scripts/index_all_repos_semantic_full.py`
- **Interfaces provided**: IF-0-SEMQUERYFULLREBOUNDTAIL-1 exact rebound
  advance contract; IF-0-SEMQUERYFULLREBOUNDTAIL-2 narrow rebound repair
  contract; IF-0-SEMQUERYFULLREBOUNDTAIL-3 script discoverability contract;
  and IF-0-SEMQUERYFULLREBOUNDTAIL-4 durable trace and operator contract
- **Interfaces consumed**: SL-0 dispatcher fixtures; SL-1 durable trace and
  repository-status fixtures; existing `_EXACT_BOUNDED_PYTHON_PATHS`; current
  repository-status wording; current force-full trace promotion behavior; and
  the checked-in structure of the script pair
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 and SL-1 slices first and determine whether the
    re-exposed cost is best cleared by a minimal adjustment to the existing
    exact bounded-path handling, a truthful trace or status promotion repair,
    or the smallest file-local simplification inside one of the two scripts.
  - impl: Choose one singular repair surface and keep it exact. Acceptable
    examples are tightening the existing bounded lexical handling for the
    exact pair, tightening durable trace or `repository status` promotion so
    the exact pair is reported truthfully, or making the smallest
    script-local simplification that allows the current watchdog to advance
    beyond the pair.
  - impl: Only edit `scripts/run_comprehensive_query_test.py` or
    `scripts/index_all_repos_semantic_full.py` if tests and the refreshed
    current-head rerun prove the active hotspot is file-local structure
    rather than existing matcher or truth-surface behavior.
  - impl: Preserve the scripts' intended operational meaning,
    `ParallelQueryTester`,
    `test_bm25_query`,
    `test_semantic_query`,
    `test_queries_batch`,
    `test_repository`,
    `run_all_repository_tests`,
    `aggregate_results`,
    `get_all_code_files`,
    `create_embeddings_batch`,
    `process_repository`,
    `find_test_repositories`, and `main`, plus current output filenames and
    indexing intent.
  - impl: Do not clear the seam with a broad `scripts/*.py` bypass, a generic
    ignore rule, or a repair that reopens the cleared centralization seam.
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "run_comprehensive_query_test or index_all_repos_semantic_full or comprehensive_query or full_semantic or lexical or bounded"`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "run_comprehensive_query_test or index_all_repos_semantic_full or comprehensive_query or full_semantic or lexical or interrupted or boundary or closeout_handoff"`

### SL-3 - Live Rerun Evidence Reducer And SEMQUERYFULLREBOUNDTAIL Contract Refresh

- **Scope**: Refresh the dogfood evidence so it records the
  SEMCENTRALIZETAIL outcome, the SEMQUERYFULLREBOUNDTAIL rerun command and
  timestamps, the trace and status outputs, runtime counts, and the final
  authoritative verdict for the exact rebound pair.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: IF-0-SEMQUERYFULLREBOUNDTAIL-5 evidence contract
- **Interfaces consumed**: SL-2 repair outcome; live outputs from
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`,
  `uv run mcp-index repository status`,
  `.mcp-index/force_full_exit_trace.json`, and SQLite runtime counts; plus the
  SEMCENTRALIZETAIL evidence lineage
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/docs/test_semdogfood_evidence_contract.py` so the
    dogfood report expects `SEMQUERYFULLREBOUNDTAIL`, the new plan lineage,
    the SEMCENTRALIZETAIL rerun outcome, the exact comprehensive-query pair,
    and the updated verification sequence.
  - impl: Add a dedicated `## SEMQUERYFULLREBOUNDTAIL Live Rerun Check`
    section that records the refreshed rerun command, timestamps, trace and
    status output, runtime counts, and whether the pair remained the active
    blocker or moved later.
  - impl: If the rerun still names the exact pair, the report must explain
    why that attribution remains truthful on the rebound head; if the rerun
    moves later, the report must say the comprehensive-query/full-sync seam
    is no longer the active blocker and preserve the exact newer blocker or
    closeout-stage attribution.
  - impl: Preserve the same-head readiness, rollout-status, last-sync-error,
    and semantic-readiness lines unless the refreshed live probes prove they
    changed.
  - impl: Keep this lane limited to the dogfood evidence artifact and its
    test. Do not mutate the roadmap here; SL-4 owns any required downstream
    phase-tail amendment.
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "SEMCENTRALIZETAIL or SEMQUERYFULLREBOUNDTAIL or run_comprehensive_query_test or index_all_repos_semantic_full"`
  - verify: `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - verify: `sed -n '1,240p' .mcp-index/force_full_exit_trace.json`
  - verify: `sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'`

### SL-4 - Downstream Roadmap Steering Reducer

- **Scope**: Keep the v7 roadmap truthful if the refreshed current-head rerun
  exposes a blocker beyond the present roadmap tail.
- **Owned files**: `specs/phase-plans-v7.md`
- **Interfaces provided**: the roadmap-steering portion of
  IF-0-SEMQUERYFULLREBOUNDTAIL-5
- **Interfaces consumed**: SL-3 live rerun verdict; current phase-81 tail
  position in `specs/phase-plans-v7.md`; and canonical `.phase-loop/`
  expectation that the roadmap names the next unplanned phase truthfully
- **Parallel-safe**: no
- **Tasks**:
  - test: Re-read the end of `specs/phase-plans-v7.md` after the SL-3 rerun
    and only amend it if the refreshed current-head evidence proves a blocker
    beyond
    `scripts/run_comprehensive_query_test.py ->
    scripts/index_all_repos_semantic_full.py`.
  - impl: If the rerun reveals a newer blocker, append one downstream phase
    with the same exact-pair specificity and evidence-first structure used
    elsewhere in the v7 lexical-recovery chain so `.phase-loop/` does not
    stop on a stale comprehensive-query rebound tail.
  - impl: If the rerun keeps the comprehensive-query/full-sync pair as the
    active truthful blocker, leave the roadmap unchanged and record that
    decision explicitly in the execution closeout and evidence.
  - impl: Keep this lane reducer-only. Do not reopen earlier centralization,
    integration, legacy-runtime, script-family, or semantic phases that the
    rerun did not re-anchor on.
  - verify: `rg -n "SEMQUERYFULLREBOUNDTAIL|scripts/run_comprehensive_query_test\\.py|scripts/index_all_repos_semantic_full\\.py" specs/phase-plans-v7.md docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
  - verify: `git diff -- specs/phase-plans-v7.md`

## Verification

Planning-only run: do not execute these during plan creation. Run them during
`codex-execute-phase` or manual SEMQUERYFULLREBOUNDTAIL execution.

Lane-specific checks:

```bash
uv run pytest tests/test_dispatcher.py -q --no-cov -k "run_comprehensive_query_test or index_all_repos_semantic_full or comprehensive_query or full_semantic or lexical or bounded"
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "run_comprehensive_query_test or index_all_repos_semantic_full or comprehensive_query or full_semantic or lexical or interrupted or boundary or closeout_handoff"
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "SEMCENTRALIZETAIL or SEMQUERYFULLREBOUNDTAIL or run_comprehensive_query_test or index_all_repos_semantic_full"
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
  -q --no-cov -k "run_comprehensive_query_test or index_all_repos_semantic_full or comprehensive_query or full_semantic or lexical or bounded or interrupted or boundary or closeout_handoff"
timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
sed -n '1,240p' .mcp-index/force_full_exit_trace.json
git status --short -- plans/phase-plan-v7-SEMQUERYFULLREBOUNDTAIL.md docs/status/SEMANTIC_DOGFOOD_REBUILD.md specs/phase-plans-v7.md
git diff --check
git diff --cached --check
```

## Acceptance Criteria

- [ ] A refreshed repo-local force-full rerun on the
      post-SEMCENTRALIZETAIL head either advances durably beyond
      `scripts/run_comprehensive_query_test.py ->
      scripts/index_all_repos_semantic_full.py`
      or emits a truthful newer blocker before the 120-second watchdog
      expires.
- [ ] The chosen repair for the re-exposed comprehensive-query/full-sync seam
      stays narrow, tested, and does not reopen the repaired
      `scripts/real_strategic_recommendations.py ->
      scripts/migrate_to_centralized.py`
      boundary without direct evidence.
- [ ] Both exact scripts remain lexically discoverable with durable file
      storage and stable symbol or text discoverability for the checked-in
      comprehensive-query and full-sync script surfaces.
- [ ] `force_full_exit_trace.json` and
      `uv run mcp-index repository status` stay aligned with the repaired
      outcome for the exact comprehensive-query/full-sync pair and do not
      leave stale blame on the cleared centralization seam or earlier
      intermediary script pairs after durable progress has already moved
      later.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMCENTRALIZETAIL rerun outcome and the final live verdict for the
      exact comprehensive-query/full-sync pair.
- [ ] If execution reveals a newer blocker beyond the current roadmap tail,
      `specs/phase-plans-v7.md` is updated before closeout so the next
      phase-loop step stays truthful.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMQUERYFULLREBOUNDTAIL.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMQUERYFULLREBOUNDTAIL.md
  artifact_state: staged
```
