---
phase_loop_plan_version: 1
phase: SEMEMBEDCONSOL
roadmap: specs/phase-plans-v7.md
roadmap_sha256: 5f53c84aa192d9b3c1c11888f44a7b8c5a5ccbcf0615b82f3f4dc4a1a11a7af3
---
# SEMEMBEDCONSOL: Embed/Consolidation Tail Recovery

## Context

SEMEMBEDCONSOL is the phase-56 follow-up for the v7 semantic hardening
roadmap. Canonical `.phase-loop/` state is authoritative for this run:
`.phase-loop/state.json` and `.phase-loop/tui-handoff.md` both mark
`SEMEMBEDCONSOL` as the current `unplanned` phase after `SEMVERIFYSIMTAIL`
closed out on `HEAD` `82f8e44821ec14af93ef3bd5770e8ebf92b08961` with
verification `passed`, a clean worktree, and `main...origin/main [ahead 107]`.
Legacy `.codex/phase-loop/` artifacts are compatibility-only and are not
authoritative here.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is tracked and clean in this worktree, and
  `sha256sum specs/phase-plans-v7.md` matches the required
  `5f53c84aa192d9b3c1c11888f44a7b8c5a5ccbcf0615b82f3f4dc4a1a11a7af3`.
- The target artifact `plans/phase-plan-v7-SEMEMBEDCONSOL.md` did not exist
  before this planning run.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is the active evidence anchor.
  Its SEMVERIFYSIMTAIL rerun block records the current downstream lexical
  failure precisely: the refreshed repo-local command
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  started on observed commit `504e419a`, and at `2026-04-29T17:28:28Z`
  `.mcp-index/force_full_exit_trace.json` showed
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/scripts/create_semantic_embeddings.py`
  with
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/scripts/consolidate_real_performance_data.py`;
  at `2026-04-29T17:28:49Z`, `repository status` terminalized that running
  snapshot to `Trace status: interrupted` with the same exact pair.
- The SEMVERIFYSIMTAIL blocker is no longer active. The authoritative
  current-head blocker is now the later Python-script seam
  `scripts/create_semantic_embeddings.py ->
  scripts/consolidate_real_performance_data.py`, so older downstream
  assumptions that still stop at
  `scripts/verify_embeddings.py ->
  scripts/claude_code_behavior_simulator.py` are stale.
- The two exact script files differ materially in shape and likely indexing
  cost. `scripts/create_semantic_embeddings.py` is `177` lines / `6118` bytes
  with top-level functions `get_repository_info(...)`,
  `process_repository(...)`, and `main()`. `scripts/consolidate_real_performance_data.py`
  is `483` lines / `19613` bytes with top-level surfaces
  `ConsolidatedResult`, `PerformanceDataConsolidator`, and `main()`.
- `mcp_server/dispatcher/dispatcher_enhanced.py` already carries exact bounded
  Python handling for earlier repaired script pairs including
  `scripts/verify_embeddings.py` and
  `scripts/claude_code_behavior_simulator.py`, but it does not yet include
  `scripts/create_semantic_embeddings.py` or
  `scripts/consolidate_real_performance_data.py`.
- `mcp_server/plugins/python_plugin/plugin.py` already bounds chunking for the
  verify/simulator pair and other earlier exact rebound files, but it does not
  include the embed/consolidation pair. Both active blocker files therefore
  still fall through the normal Python plugin path during lexical walking.
- `mcp_server/cli/repository_commands.py` already advertises exact lexical
  boundary messages for earlier bounded Python, shell/Python, Markdown, and
  JSON seams, but it has no dedicated helper yet for
  `scripts/create_semantic_embeddings.py ->
  scripts/consolidate_real_performance_data.py`.
- Existing tests already freeze adjacent behavior but not this exact pair.
  `tests/test_dispatcher.py` covers earlier exact bounded Python seams,
  `tests/test_git_index_manager.py` and `tests/test_repository_commands.py`
  preserve durable trace and operator wording for earlier script boundaries,
  and `tests/docs/test_semdogfood_evidence_contract.py` already expects the
  dogfood evidence artifact to retain the current embed/consolidation pair plus
  the roadmap steering to downstream phase `SEMEMBEDCONSOL`.

Practical planning boundary:

- SEMEMBEDCONSOL may tighten exact Python-script tail handling, dispatcher
  lexical progress accounting, durable trace persistence, operator status
  wording, and the semantic dogfood evidence artifact needed to prove a live
  rerun either advances beyond
  `scripts/create_semantic_embeddings.py ->
  scripts/consolidate_real_performance_data.py` or surfaces a truthful newer
  blocker.
- SEMEMBEDCONSOL must stay narrow and evidence-driven. It must not reopen the
  repaired verify/simulator recovery, introduce a broad `scripts/*.py`
  exemption, retune the repo-wide lexical watchdog, or reopen older ai-docs,
  Markdown, benchmark, visualization, devcontainer, archive-tail, docs-governance,
  or earlier script seams unless the refreshed rerun directly re-anchors there
  again.

## Interface Freeze Gates

- [ ] IF-0-SEMEMBEDCONSOL-1 - Embed/consolidation tail advance contract:
      a refreshed repo-local force-full rerun on the post-SEMVERIFYSIMTAIL
      head no longer terminalizes with the durable lexical trace centered on
      `scripts/create_semantic_embeddings.py ->
      scripts/consolidate_real_performance_data.py`; it either advances
      durably beyond that pair or emits a truthful newer blocker before the
      120-second watchdog expires.
- [ ] IF-0-SEMEMBEDCONSOL-2 - Exact boundary contract:
      any repair introduced by this phase remains limited to the exact
      embed/consolidation Python pair plus the immediate dispatcher/plugin
      plumbing needed to clear it. The phase must not introduce a new blanket
      `scripts/*.py` fast path, and it must not reopen the prior
      `scripts/verify_embeddings.py ->
      scripts/claude_code_behavior_simulator.py` seam without direct evidence.
- [ ] IF-0-SEMEMBEDCONSOL-3 - Lexical discoverability contract:
      both exact scripts remain lexically discoverable after the repair,
      including durable file-level storage plus bounded symbol or content
      discoverability for `get_repository_info(...)`,
      `process_repository(...)`, `ConsolidatedResult`,
      and `PerformanceDataConsolidator`, instead of turning either file into an
      indexing blind spot.
- [ ] IF-0-SEMEMBEDCONSOL-4 - Durable trace and operator contract:
      `force_full_exit_trace.json` and `uv run mcp-index repository status`
      stay aligned with the repaired outcome for the exact later
      Python-script pair and do not regress to stale SEMVERIFYSIMTAIL-only
      wording once the live rerun advances past it.
- [ ] IF-0-SEMEMBEDCONSOL-5 - Evidence and downstream steering contract:
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the SEMVERIFYSIMTAIL
      rerun outcome, the SEMEMBEDCONSOL rerun command and timestamps, the
      refreshed trace/status output, and the final authoritative verdict for
      the later Python-script pair; if execution reveals a blocker beyond the
      current roadmap tail, `specs/phase-plans-v7.md` is amended before
      closeout so the next phase-loop step is truthful.

## Lane Index & Dependencies

- SL-0 - Exact later Python-script fixture freeze; Depends on: SEMVERIFYSIMTAIL; Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 - Exact embed/consolidation bounded indexing repair; Depends on: SL-0; Blocks: SL-2, SL-3, SL-4; Parallel-safe: no
- SL-2 - Durable trace persistence and operator boundary alignment; Depends on: SL-0, SL-1; Blocks: SL-3, SL-4; Parallel-safe: no
- SL-3 - Live rerun evidence reducer and contract refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SL-4; Parallel-safe: no
- SL-4 - Downstream roadmap steering reducer; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: SEMEMBEDCONSOL acceptance; Parallel-safe: no

Lane DAG:

```text
SEMVERIFYSIMTAIL
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SL-4 -> SEMEMBEDCONSOL acceptance
```

## Lanes

### SL-0 - Exact Later Python-Script Fixture Freeze

- **Scope**: Freeze the exact
  `scripts/create_semantic_embeddings.py ->
  scripts/consolidate_real_performance_data.py` lexical seam in deterministic
  dispatcher coverage before runtime changes so this phase proves a narrow
  repair instead of hand-waving around all Python scripts.
- **Owned files**: `tests/test_dispatcher.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMEMBEDCONSOL-1,
  IF-0-SEMEMBEDCONSOL-2,
  and IF-0-SEMEMBEDCONSOL-3 at the dispatcher/plugin boundary
- **Interfaces consumed**: existing
  `Dispatcher.index_directory(...)`,
  `Dispatcher._build_exact_bounded_python_shard(...)`,
  normal Python routing through `Plugin.indexFile(...)`,
  and the SEMVERIFYSIMTAIL evidence for the exact later Python-script pair
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` with a repo-shaped fixture that
    indexes exact copies or trimmed representatives of
    `scripts/create_semantic_embeddings.py` and
    `scripts/consolidate_real_performance_data.py`, proves the lexical walker
    records the exact pair in order, and fails if the repair silently turns
    either file into an untracked blind spot.
  - test: In the same dispatcher coverage, assert that the embedding script
    remains content-discoverable for `get_repository_info` and
    `process_repository`, and that the consolidation script remains symbol or
    content discoverable for `ConsolidatedResult` and
    `PerformanceDataConsolidator` after the repair.
  - test: Add a negative guard that unrelated Python scripts outside the exact
    pair still use the normal bounded or full Python handling. The watchdog
    repair must not quietly become a broader `scripts/*.py` fast path.
  - impl: Keep fixtures deterministic with repo-local Python strings and
    monkeypatched bounded-path instrumentation rather than long-running live
    waits inside unit tests.
  - impl: Keep this lane on contract freeze only. Do not mutate durable trace,
    CLI wording, evidence docs, or roadmap steering here.
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "create_semantic_embeddings or consolidate_real_performance_data or lexical or bounded or consolidator or script"`

### SL-1 - Exact Embed/Consolidation Bounded Indexing Repair

- **Scope**: Implement the smallest dispatcher and Python-plugin repair
  needed so the live lexical walker no longer burns its watchdog budget on
  the exact `create_semantic_embeddings.py -> consolidate_real_performance_data.py`
  script pair.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `mcp_server/plugins/python_plugin/plugin.py`
- **Interfaces provided**: IF-0-SEMEMBEDCONSOL-2 exact boundary contract;
  IF-0-SEMEMBEDCONSOL-3 lexical discoverability contract
- **Interfaces consumed**: SL-0 later Python-script fixtures; existing exact
  bounded Python behavior in
  `Dispatcher._build_exact_bounded_python_shard(...)`; and the current
  Python bounded chunk rules in `Plugin._BOUNDED_CHUNK_PATHS`
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 dispatcher slice first and confirm which side of the
    pair still consumes watchdog budget in the current force-full path:
    the smaller embedding script, the larger consolidation file, or the
    handoff between them.
  - impl: Apply the narrowest repair that clears the exact pair. Prefer
    exact-path bounded handling over any broad script-family shortcut, and
    keep the repair local to the dispatcher or the relevant Python plugin
    path.
  - impl: Preserve content discoverability for
    `scripts/create_semantic_embeddings.py`, including
    `get_repository_info(...)`, `process_repository(...)`, and its semantic
    indexing flow, instead of reducing the file to an opaque skipped artifact.
  - impl: Preserve top-level symbol or content discoverability for
    `scripts/consolidate_real_performance_data.py`, including the
    `ConsolidatedResult` dataclass, the `PerformanceDataConsolidator` class,
    and the analysis entrypoint surfaces.
  - impl: Do not widen `_EXACT_BOUNDED_PYTHON_PATHS` or
    `Plugin._BOUNDED_CHUNK_PATHS` beyond what is needed for this exact
    pair, and do not introduce a repo-wide Python timeout or global
    plaintext bypass that masks later blockers.
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "create_semantic_embeddings or consolidate_real_performance_data or lexical or bounded or consolidator or script"`

### SL-2 - Durable Trace Persistence And Operator Boundary Alignment

- **Scope**: Carry the exact later Python-script repair into the durable
  force-full trace and operator status surfaces so runtime reporting
  truthfully distinguishes the cleared pair from any later blocker.
- **Owned files**: `mcp_server/storage/git_index_manager.py`, `mcp_server/cli/repository_commands.py`, `tests/test_git_index_manager.py`, `tests/test_repository_commands.py`
- **Interfaces provided**: IF-0-SEMEMBEDCONSOL-1 embed/consolidation tail
  advance contract; IF-0-SEMEMBEDCONSOL-4 durable trace and operator
  contract
- **Interfaces consumed**: SL-0 fixture expectations; SL-1 repaired exact
  Python bounded indexing behavior; existing `force_full_exit_trace.json`
  persistence in `GitAwareIndexManager`; and current operator boundary
  helpers in `repository_commands.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_git_index_manager.py` so durable trace fixtures
    preserve the exact
    `scripts/create_semantic_embeddings.py ->
    scripts/consolidate_real_performance_data.py` blocker when it is active
    and prove the rerun advances to a newer blocker without regressing to
    the cleared SEMVERIFYSIMTAIL seam.
  - test: Extend `tests/test_repository_commands.py` so `repository status`
    advertises the repaired exact bounded lexical surface for the later
    Python-script pair and still prints the correct later
    `last_progress_path` and `in_flight_path` when the live blocker moves
    forward.
  - impl: Add the minimal `repository status` helper or wording needed to
    name the exact embed/consolidation pair once the repair is in place,
    matching the existing style used for earlier exact bounded Python,
    shell/Python, Markdown, and JSON seams.
  - impl: Preserve truthful terminalization behavior when the live command
    times out or fails later. This lane must not relabel a later blocker as if
    the embed/consolidation seam were still active once the rerun has moved on.
  - impl: Keep earlier boundary wording for
    `scripts/preflight_upgrade.sh ->
    scripts/test_mcp_protocol_direct.py` and
    `scripts/verify_embeddings.py ->
    scripts/claude_code_behavior_simulator.py` intact unless the rerun
    directly proves one of those seams has regressed.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "create_semantic_embeddings or consolidate_real_performance_data or lexical or interrupted or boundary or consolidator or script"`

### SL-3 - Live Rerun Evidence Reducer And Contract Refresh

- **Scope**: Refresh the real dogfood evidence after the exact later
  Python-script repair so the active blocker report matches the repaired
  runtime rather than stale SEMVERIFYSIMTAIL assumptions.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: the evidence portion of
  IF-0-SEMEMBEDCONSOL-5
- **Interfaces consumed**: SL-2 durable trace and repository-status output;
  live rerun command output; existing SEMVERIFYSIMTAIL evidence block; and the
  current evidence-contract assertions in
  `tests/docs/test_semdogfood_evidence_contract.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/docs/test_semdogfood_evidence_contract.py` only as
    needed so the status artifact must retain the exact current blocker pair,
    the SEMEMBEDCONSOL phase name, and any newly exposed downstream steering
    after execution.
  - impl: Run a fresh repo-local force-full rerun after SL-1 and SL-2 land,
    then capture the rerun command, observed commit, timeout or completion
    timestamp, durable trace snapshot, `repository status` output, and SQLite
    counts in `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`.
  - impl: If the repaired rerun still times out, record the exact later
    blocker pair that replaced
    `scripts/create_semantic_embeddings.py ->
    scripts/consolidate_real_performance_data.py` rather than leaving the
    older pair as the active narrative.
  - impl: Keep this lane on evidence reduction. Do not back-edit older phase
    narratives except where the new rerun explicitly supersedes the active
    blocker statement.
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`

### SL-4 - Downstream Roadmap Steering Reducer

- **Scope**: Keep the roadmap and next phase-loop step truthful if the
  repaired live rerun proves a newer blocker beyond the current roadmap
  tail.
- **Owned files**: `specs/phase-plans-v7.md`
- **Interfaces provided**: the downstream-steering portion of
  IF-0-SEMEMBEDCONSOL-5
- **Interfaces consumed**: SL-3 refreshed evidence verdict; current roadmap
  DAG and phase ordering for `specs/phase-plans-v7.md`; canonical
  `.phase-loop/` expectation that the next unplanned phase reflects the
  latest durable blocker rather than stale prior assumptions
- **Parallel-safe**: no
- **Tasks**:
  - test: Re-read the post-SL-3 evidence and confirm whether the repaired
    rerun actually exposes a newer blocker beyond the current roadmap tail
    before mutating roadmap steering.
  - impl: If the active blocker is still the exact later Python-script pair,
    leave the roadmap unchanged.
  - impl: If the active blocker advances beyond the pair and no downstream
    phase already covers it, append the nearest truthful downstream recovery
    phase to `specs/phase-plans-v7.md` with the same evidence-first
    structure used by the current SEM* lexical-recovery chain.
  - impl: Keep any roadmap mutation limited to the newly exposed blocker.
    Do not rewrite earlier phases or backfill unrelated sequencing while
    closing this seam.
  - verify: `git diff -- specs/phase-plans-v7.md`

## Verification

- Lane checks:
  - `uv run pytest tests/test_dispatcher.py -q --no-cov -k "create_semantic_embeddings or consolidate_real_performance_data or lexical or bounded or consolidator or script"`
  - `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "create_semantic_embeddings or consolidate_real_performance_data or lexical or interrupted or boundary or consolidator or script"`
  - `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
- Whole-phase checks:
  - `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_repository_commands.py tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "create_semantic_embeddings or consolidate_real_performance_data or lexical or bounded or interrupted or boundary or consolidator or script"`
  - `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  - `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - `sed -n '1,240p' .mcp-index/force_full_exit_trace.json`
  - `sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'`
  - `git diff --check`
  - `git diff --cached --check`

## Acceptance Criteria

- [ ] A refreshed repo-local force-full rerun on the post-SEMVERIFYSIMTAIL
      head either advances durably beyond
      `scripts/create_semantic_embeddings.py ->
      scripts/consolidate_real_performance_data.py` or emits a truthful newer
      blocker before the 120-second watchdog expires.
- [ ] The repair stays narrowly scoped to the exact later Python-script
      pair and the immediate dispatcher/plugin/trace/status/evidence
      plumbing needed to prove it.
- [ ] Both exact scripts remain lexically discoverable with durable
      file-level storage plus bounded symbol or content discoverability for
      `get_repository_info(...)`, `process_repository(...)`,
      `ConsolidatedResult`, and `PerformanceDataConsolidator`.
- [ ] `uv run mcp-index repository status` and
      `force_full_exit_trace.json` stay aligned with the repaired later
      Python-script boundary outcome and do not regress to stale
      SEMVERIFYSIMTAIL wording.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMVERIFYSIMTAIL rerun outcome and the final live verdict for the
      later Python-script pair.
- [ ] If execution reveals a newer blocker beyond the current roadmap tail,
      `specs/phase-plans-v7.md` is updated before closeout so the next
      phase-loop step is truthful.

automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMEMBEDCONSOL.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMEMBEDCONSOL.md
  artifact_state: staged
