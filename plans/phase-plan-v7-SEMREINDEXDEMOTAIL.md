---
phase_loop_plan_version: 1
phase: SEMREINDEXDEMOTAIL
roadmap: specs/phase-plans-v7.md
roadmap_sha256: 71bb57d4e3ed644313a1db1962188074416d17230f1e414de6e8942e91be8cf9
---
# SEMREINDEXDEMOTAIL: Reindex/Demo Script Tail Recovery

## Context

SEMREINDEXDEMOTAIL is the phase-95 follow-up for the v7 semantic hardening
roadmap. Canonical `.phase-loop/` state is authoritative for this run:
`.phase-loop/state.json` and `.phase-loop/tui-handoff.md` both mark
`SEMREINDEXDEMOTAIL` as the current `unplanned` phase after
`SEMVERIFYAPIREBOUNDTAIL` closed out on `HEAD`
`47c86e7bad10cb0c6757f9c6d97a40316f657f11` with verification `passed`, a
clean worktree, and `main...origin/main [ahead 185]`. Legacy
`.codex/phase-loop/` artifacts remain compatibility-only and do not
supersede canonical `.phase-loop/` runner state here.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is tracked and clean in this worktree, and
  `sha256sum specs/phase-plans-v7.md` matches the required
  `71bb57d4e3ed644313a1db1962188074416d17230f1e414de6e8942e91be8cf9`.
- The target artifact `plans/phase-plan-v7-SEMREINDEXDEMOTAIL.md` did not
  exist before this planning run.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is the active evidence anchor.
  Its SEMVERIFYAPIREBOUNDTAIL block now records that the refreshed
  repo-local force-full rerun moved beyond
  `plans/phase-plan-v7-SEMVERIFYSIMTAIL.md ->
  plans/phase-plan-v7-SEMAPIDOCSTAIL.md` and terminalized later at the
  exact Python script seam
  `scripts/reindex_current_repository.py ->
  scripts/demo_centralized_indexes.py`.
- The same evidence block captures the current live trace for this phase:
  the rerun started at `2026-04-30T05:56:32Z`, exited with code `124` at
  `2026-04-30T05:58:45Z`, and at `2026-04-30T05:58:46Z`
  `.mcp-index/force_full_exit_trace.json` terminalized to
  `status: interrupted`, `stage: lexical_walking`,
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/scripts/reindex_current_repository.py`,
  and
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/scripts/demo_centralized_indexes.py`.
- `uv run mcp-index repository status` already has an operator-surface
  pattern for exact bounded Python seams, and the repo contains helpers for
  many later script families, but repo inspection during planning did not
  show a dedicated boundary reporter or test fixture for the new
  `reindex_current_repository.py -> demo_centralized_indexes.py` pair yet.
- The Python plugin currently uses exact bounded lexical handling through
  `mcp_server/plugins/python_plugin/plugin.py::Plugin._BOUNDED_CHUNK_PATHS`
  for several later script and doc contract surfaces such as
  `scripts/verify_embeddings.py`,
  `scripts/claude_code_behavior_simulator.py`,
  `scripts/create_semantic_embeddings.py`, and
  `scripts/consolidate_real_performance_data.py`, but it does not currently
  list `scripts/reindex_current_repository.py` or
  `scripts/demo_centralized_indexes.py`.
- Existing dispatcher and status coverage is one seam behind. The repo
  already freezes exact lexical behavior for the prior rebound phase-plan
  seam in `tests/test_dispatcher.py`, `tests/test_git_index_manager.py`,
  and `tests/test_repository_commands.py`, while
  `tests/docs/test_semdogfood_evidence_contract.py` already requires the
  checked-in evidence artifact to retain the new downstream steering to
  `SEMREINDEXDEMOTAIL` and the two script paths.
- The two script files are plausible bounded-python candidates rather than
  semantic-pipeline rewrites. `scripts/reindex_current_repository.py` is a
  standalone reindex helper with hardcoded workspace env setup, manual
  SQLite backup/removal, and a direct `EnhancedDispatcher.index_directory`
  call. `scripts/demo_centralized_indexes.py` is a verbose centralized
  storage demo with repository-info printing, index listing, retention
  policy output, and storage-strategy comparison. This phase should assume
  the first repair attempt is a narrow lexical-walk containment for these
  exact files, not a broad rewrite of indexing behavior.
- Semantic state remains fail-closed rather than hiding the lexical blocker:
  SQLite counts remained `files = 1199`, `code_chunks = 21254`,
  `chunk_summaries = 0`, and `semantic_points = 0`, while `repository
  status` still reported `Readiness: stale_commit`, `Rollout status:
  partial_index_failure`, `Last sync error: disk I/O error`, and
  `Semantic readiness: summaries_missing`.

Practical planning boundary:

- SEMREINDEXDEMOTAIL may tighten exact bounded Python handling for the two
  named scripts, dispatcher lexical progress accounting, durable trace
  persistence, operator status wording, and semantic dogfood evidence needed
  to prove a live rerun either advances beyond
  `scripts/reindex_current_repository.py ->
  scripts/demo_centralized_indexes.py` or surfaces a truthful newer blocker.
- SEMREINDEXDEMOTAIL must stay narrow and evidence-driven. It must not
  reopen the cleared rebound phase-plan seam
  `plans/phase-plan-v7-SEMVERIFYSIMTAIL.md ->
  plans/phase-plan-v7-SEMAPIDOCSTAIL.md`, introduce a blanket
  `scripts/*.py` fast path, or widen into unrelated semantic, integration,
  security, or compatibility work unless the refreshed rerun directly proves
  the blocker has moved again.

## Interface Freeze Gates

- [ ] IF-0-SEMREINDEXDEMOTAIL-1 - Exact script-tail advance contract: a
      refreshed repo-local force-full rerun on the
      post-SEMVERIFYAPIREBOUNDTAIL head no longer terminalizes with the
      durable lexical trace centered on
      `scripts/reindex_current_repository.py ->
      scripts/demo_centralized_indexes.py`; it either advances durably
      beyond that pair or emits a truthful newer blocker before the
      120-second watchdog expires.
- [ ] IF-0-SEMREINDEXDEMOTAIL-2 - Narrow script-pair repair contract: any
      repair introduced by this phase remains limited to the exact script
      pair and the immediate Python-plugin or dispatcher or trace or status
      or evidence plumbing needed to clear it. The phase must not introduce
      a new blanket `scripts/*.py` bypass and must not reopen the cleared
      `plans/phase-plan-v7-SEMVERIFYSIMTAIL.md ->
      plans/phase-plan-v7-SEMAPIDOCSTAIL.md` seam without direct evidence.
- [ ] IF-0-SEMREINDEXDEMOTAIL-3 - Lexical discoverability contract: both
      exact script files remain lexically discoverable after the repair,
      including durable file-level storage plus bounded symbol and FTS
      discoverability for the script entrypoints and high-signal strings,
      instead of turning either file into an indexing blind spot.
- [ ] IF-0-SEMREINDEXDEMOTAIL-4 - Durable trace and operator contract:
      `.mcp-index/force_full_exit_trace.json` and
      `uv run mcp-index repository status` stay aligned with the repaired
      outcome for the exact script pair and do not regress to stale
      SEMVERIFYAPIREBOUNDTAIL-era phase-plan wording once the live rerun has
      advanced past it.
- [ ] IF-0-SEMREINDEXDEMOTAIL-5 - Evidence and downstream steering
      contract: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMVERIFYAPIREBOUNDTAIL rerun outcome and the final live verdict for
      the exact
      `scripts/reindex_current_repository.py ->
      scripts/demo_centralized_indexes.py` pair; if execution reveals a
      blocker beyond the current roadmap tail, `specs/phase-plans-v7.md` is
      amended before closeout so the next phase-loop step is truthful.

## Lane Index & Dependencies

- SL-0 - Exact script-pair fixture freeze; Depends on: SEMVERIFYAPIREBOUNDTAIL; Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 - Minimal script-pair lexical recovery; Depends on: SL-0; Blocks: SL-2, SL-3, SL-4; Parallel-safe: no
- SL-2 - Durable trace persistence and operator script-tail alignment; Depends on: SL-0, SL-1; Blocks: SL-3, SL-4; Parallel-safe: no
- SL-3 - Live rerun evidence reducer and script-tail contract refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SL-4; Parallel-safe: no
- SL-4 - Downstream roadmap steering reducer; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: SEMREINDEXDEMOTAIL acceptance; Parallel-safe: no

Lane DAG:

```text
SEMVERIFYAPIREBOUNDTAIL
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SL-4 -> SEMREINDEXDEMOTAIL acceptance
```

## Lanes

### SL-0 - Exact Script-Pair Fixture Freeze

- **Scope**: Freeze the exact
  `scripts/reindex_current_repository.py ->
  scripts/demo_centralized_indexes.py` lexical seam in deterministic
  dispatcher coverage before runtime changes so this phase proves a narrow
  recovery instead of hand-waving around the broader script family.
- **Owned files**: `tests/test_dispatcher.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMREINDEXDEMOTAIL-1,
  IF-0-SEMREINDEXDEMOTAIL-2,
  and IF-0-SEMREINDEXDEMOTAIL-3 at the dispatcher and Python-plugin
  boundary
- **Interfaces consumed**: existing `Dispatcher.index_directory(...)`;
  `Plugin._BOUNDED_CHUNK_PATHS`; current exact bounded Python path behavior
  for later script seams; and the SEMVERIFYAPIREBOUNDTAIL evidence for the
  exact reindex/demo script pair
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` with repo-shaped fixtures that
    index exact copies or trimmed representatives of
    `scripts/reindex_current_repository.py` and
    `scripts/demo_centralized_indexes.py`, prove the lexical walker records
    the exact pair in order, and fail if the repair silently turns them
    into an untracked blind spot.
  - test: In the same dispatcher coverage, assert that the repaired path
    keeps document-level FTS content and symbol discoverability for
    high-signal script content such as `reindex_current_repo`,
    `demo_centralized_storage`, `demo_storage_strategies`, and the
    user-facing progress strings already present in the scripts.
  - test: Add a negative guard that unrelated Python scripts outside the
    exact pair still use the normal heavy or pre-existing bounded path as
    appropriate; the watchdog repair must not quietly become a broader
    `scripts/*.py` fast path.
  - impl: Keep fixtures deterministic with repo-local Python strings and
    monkeypatched bounded-path instrumentation rather than long-running live
    waits inside unit tests.
  - impl: Keep this lane on contract freeze only. Do not mutate durable
    trace, CLI wording, evidence docs, or roadmap steering here.
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "reindex_current_repository or demo_centralized_indexes or lexical or bounded or script or dispatcher"`

### SL-1 - Minimal Script-Pair Lexical Recovery

- **Scope**: Implement the narrowest lexical-walk repair that lets the live
  force-full rerun move beyond the exact reindex/demo script pair without
  broadening Python-script bypass behavior.
- **Owned files**: `mcp_server/plugins/python_plugin/plugin.py`, `mcp_server/dispatcher/dispatcher_enhanced.py`, `scripts/reindex_current_repository.py`, `scripts/demo_centralized_indexes.py`
- **Interfaces provided**: repaired execution-path behavior for
  IF-0-SEMREINDEXDEMOTAIL-1,
  IF-0-SEMREINDEXDEMOTAIL-2,
  and IF-0-SEMREINDEXDEMOTAIL-3
- **Interfaces consumed**: SL-0 exact script-pair tests; existing bounded
  Python chunking rules in `Plugin._BOUNDED_CHUNK_PATHS`; dispatcher lexical
  progress reporting; and the current live blocker evidence captured in
  `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- **Parallel-safe**: no
- **Tasks**:
  - test: Make the SL-0 dispatcher fixtures fail first on current `HEAD`
    and keep them as the narrow proof target for the repair.
  - impl: First evaluate the pre-existing exact-bounded-Python pattern used
    by later script seams and apply it to
    `scripts/reindex_current_repository.py` and
    `scripts/demo_centralized_indexes.py` if that is sufficient to preserve
    lexical discoverability while eliminating the watchdog burn at this
    pair.
  - impl: Only if the bounded-path addition is insufficient, make the
    smallest follow-on edit in `mcp_server/dispatcher/dispatcher_enhanced.py`
    or in the exact script files themselves that is needed to preserve
    accurate lexical progress and bounded storage without widening into a
    generic Python fast path.
  - impl: Keep any script-file edits minimal and evidence-driven. Do not
    rewrite these helpers for style or architecture cleanup; only trim or
    restructure the exact content that execution proves is necessary to move
    the lexical walker past the seam.
  - impl: Do not touch semantic summary or vector code in this lane unless
    the lexical repair directly requires a tiny contract-preserving guard.
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "reindex_current_repository or demo_centralized_indexes or lexical or bounded or script or dispatcher"`

### SL-2 - Durable Trace Persistence And Operator Script-Tail Alignment

- **Scope**: Keep the durable force-full trace and `repository status`
  output aligned with the exact script-pair blocker so operators see the
  repaired current seam instead of stale phase-plan wording or unrelated
  script-family summaries.
- **Owned files**: `mcp_server/storage/git_index_manager.py`, `mcp_server/cli/repository_commands.py`, `tests/test_git_index_manager.py`, `tests/test_repository_commands.py`
- **Interfaces provided**: the trace and operator portions of
  IF-0-SEMREINDEXDEMOTAIL-4
- **Interfaces consumed**: SL-1 repaired lexical progress behavior; current
  trace persistence in `GitAwareIndexManager.get_repository_status(...)`;
  CLI boundary printers in `mcp_server/cli/repository_commands.py`; and the
  current SEMVERIFYAPIREBOUNDTAIL-era evidence showing the exact script
  pair
- **Parallel-safe**: no
- **Tasks**:
  - test: Add or extend `tests/test_git_index_manager.py` so a stored
    `force_full_exit_trace.json` preserving
    `scripts/reindex_current_repository.py` as `last_progress_path` and
    `scripts/demo_centralized_indexes.py` as `in_flight_path` survives
    `get_repository_status(...)` unchanged and without regressing to older
    phase-plan seam wording.
  - test: Add or extend `tests/test_repository_commands.py` so
    `uv run mcp-index repository status` prints the exact bounded Python
    seam for
    `scripts/reindex_current_repository.py ->
    scripts/demo_centralized_indexes.py`, keeps the trace paths aligned,
    and stops advertising the cleared
    `plans/phase-plan-v7-SEMVERIFYSIMTAIL.md ->
    plans/phase-plan-v7-SEMAPIDOCSTAIL.md` pair as the active blocker once
    the trace has moved later.
  - impl: Add a dedicated exact-boundary reporter for the reindex/demo
    script pair only if the current operator surface cannot already express
    this later seam truthfully from the repaired trace.
  - impl: Keep trace persistence durable and monotonic: interrupted reruns
    that move beyond the rebound phase-plan seam must continue to report the
    later script pair even when the run times out or fails later.
  - impl: Keep this lane limited to operator truthfulness and trace
    alignment. Do not widen into unrelated readiness, semantic preflight, or
    artifact-publish logic.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "reindex_current_repository or demo_centralized_indexes or lexical or interrupted or boundary or script"`

### SL-3 - Live Rerun Evidence Reducer And Script-Tail Contract Refresh

- **Scope**: Refresh the real dogfood evidence after the script-tail repair
  so the active blocker report matches the repaired runtime rather than
  stale SEMVERIFYAPIREBOUNDTAIL assumptions.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: the evidence portion of
  IF-0-SEMREINDEXDEMOTAIL-5
- **Interfaces consumed**: SL-2 durable trace and repository-status output;
  live rerun command output; existing SEMVERIFYAPIREBOUNDTAIL evidence block;
  and the current evidence-contract assertions in
  `tests/docs/test_semdogfood_evidence_contract.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/docs/test_semdogfood_evidence_contract.py` only as
    needed so the evidence artifact must retain the
    SEMVERIFYAPIREBOUNDTAIL rerun outcome, the active
    SEMREINDEXDEMOTAIL phase name, the exact current script-pair verdict,
    and any newly exposed downstream steering after execution.
  - impl: Run a fresh repo-local force-full rerun after SL-1 and SL-2 land,
    then capture the rerun command, observed commit, timeout or completion
    timestamp, durable trace snapshot, `repository status` output, and
    SQLite counts in `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`.
  - impl: If the repaired rerun still times out, record the exact later
    blocker pair or family that replaced
    `scripts/reindex_current_repository.py ->
    scripts/demo_centralized_indexes.py` instead of leaving the old script
    seam or the earlier rebound phase-plan seam as the active narrative.
  - impl: Keep this lane on evidence reduction. Do not back-edit older phase
    narratives except where the new rerun explicitly supersedes the active
    blocker statement.
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "SEMREINDEXDEMOTAIL or SEMVERIFYAPIREBOUNDTAIL or reindex_current_repository or demo_centralized_indexes or script"`

### SL-4 - Downstream Roadmap Steering Reducer

- **Scope**: Keep the roadmap and next phase-loop step truthful if the
  repaired live rerun proves a blocker beyond the current roadmap tail.
- **Owned files**: `specs/phase-plans-v7.md`
- **Interfaces provided**: the downstream-steering portion of
  IF-0-SEMREINDEXDEMOTAIL-5
- **Interfaces consumed**: SL-3 refreshed evidence verdict; current roadmap
  DAG and phase ordering for `specs/phase-plans-v7.md`; and canonical
  `.phase-loop/` expectations that the next unplanned phase reflects the
  latest durable blocker rather than stale SEMVERIFYAPIREBOUNDTAIL
  assumptions
- **Parallel-safe**: no
- **Tasks**:
  - test: Re-read the post-SL-3 evidence and confirm whether the repaired
    rerun actually exposes a newer blocker beyond the current roadmap tail
    before mutating roadmap steering.
  - impl: If the active blocker remains inside the current
    SEMREINDEXDEMOTAIL script family or the rerun completes lexical
    closeout, leave the roadmap unchanged.
  - impl: If the active blocker advances beyond the current roadmap tail and
    no downstream phase already covers it, append the nearest truthful
    downstream recovery phase to `specs/phase-plans-v7.md` with the same
    evidence-first structure used by the current SEM* lexical-recovery
    chain.
  - impl: Keep any roadmap mutation limited to the newly exposed blocker. Do
    not rewrite earlier phases or backfill unrelated sequencing while
    closing this seam.
  - verify: `git diff -- specs/phase-plans-v7.md`

## Verification

- Lane checks:
  - `uv run pytest tests/test_dispatcher.py -q --no-cov -k "reindex_current_repository or demo_centralized_indexes or lexical or bounded or script or dispatcher"`
  - `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "reindex_current_repository or demo_centralized_indexes or lexical or interrupted or boundary or script"`
  - `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "SEMREINDEXDEMOTAIL or SEMVERIFYAPIREBOUNDTAIL or reindex_current_repository or demo_centralized_indexes or script"`
- Whole-phase checks:
  - `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_repository_commands.py tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "SEMREINDEXDEMOTAIL or SEMVERIFYAPIREBOUNDTAIL or reindex_current_repository or demo_centralized_indexes or lexical or bounded or interrupted or boundary or script"`
  - `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  - `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - `sed -n '1,240p' .mcp-index/force_full_exit_trace.json`
  - `sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'`
  - `git status --short -- plans/phase-plan-v7-SEMREINDEXDEMOTAIL.md docs/status/SEMANTIC_DOGFOOD_REBUILD.md specs/phase-plans-v7.md`
  - `git diff --check`
  - `git diff --cached --check`

## Acceptance Criteria

- [ ] A refreshed repo-local force-full rerun on the
      post-SEMVERIFYAPIREBOUNDTAIL head either advances durably beyond
      `scripts/reindex_current_repository.py ->
      scripts/demo_centralized_indexes.py` or emits a truthful newer
      blocker before the 120-second watchdog expires.
- [ ] The repair stays narrowly scoped to the exact reindex/demo script pair
      and the immediate Python-plugin or dispatcher or trace or status or
      evidence plumbing needed to prove it.
- [ ] Both exact script files remain lexically discoverable with durable
      file storage plus bounded symbol and FTS discoverability.
- [ ] `uv run mcp-index repository status` and
      `.mcp-index/force_full_exit_trace.json` stay aligned with the repaired
      script-tail outcome and do not regress to stale
      SEMVERIFYAPIREBOUNDTAIL or earlier phase-plan-pair wording.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMVERIFYAPIREBOUNDTAIL rerun outcome and the final live verdict for
      the exact reindex/demo script pair.
- [ ] If execution reveals a newer blocker beyond the current roadmap tail,
      `specs/phase-plans-v7.md` is updated before closeout so the next
      phase-loop step is truthful.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMREINDEXDEMOTAIL.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMREINDEXDEMOTAIL.md
  artifact_state: staged
```
