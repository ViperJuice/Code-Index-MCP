---
phase_loop_plan_version: 1
phase: SEMDOCTRUTHTAIL
roadmap: specs/phase-plans-v7.md
roadmap_sha256: 5bc27c2abdbd027bf9a72118199e991102449a50a4caa5f3b4a25b29fc5d89cf
---
# SEMDOCTRUTHTAIL: Documentation Truth Tail Recovery

## Context

SEMDOCTRUTHTAIL is the phase-62 follow-up for the v7 semantic hardening
roadmap. Canonical `.phase-loop/` state remains authoritative for the runner
snapshot in this checkout, and it still reports `SEMGARELTAIL` as the current
`unplanned` phase on `HEAD`
`07a8bca2dce1aa0b71a28263cfbd9706ece28e6c` with `main...origin/main [ahead 117]`
and no dirty paths. That runner state is stale relative to the tracked
worktree, though: `plans/phase-plan-v7-SEMGARELTAIL.md` already exists and the
active dogfood evidence proves the SEMGARELTAIL seam was cleared. Per the user
request, this run writes the downstream `SEMDOCTRUTHTAIL` artifact now rather
than stopping at the stale runner pointer. Legacy `.codex/phase-loop/`
artifacts remain compatibility-only and do not supersede canonical
`.phase-loop/` state here.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is tracked and clean in this worktree, and
  `sha256sum specs/phase-plans-v7.md` matches the required
  `5bc27c2abdbd027bf9a72118199e991102449a50a4caa5f3b4a25b29fc5d89cf`.
- The target artifact `plans/phase-plan-v7-SEMDOCTRUTHTAIL.md` did not exist
  before this planning run.
- `plans/phase-plan-v7-SEMGARELTAIL.md` already exists and is tracked, so the
  current `.phase-loop/state.json` pointer should be treated as a lagging
  reconciliation state rather than as proof that the phase-61 plan is missing.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is the active evidence anchor.
  Its SEMGARELTAIL rerun block records the current downstream lexical blocker
  precisely: the refreshed repo-local command
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  started on observed commit `a3af755`, and at `2026-04-29T19:33:07Z`
  `.mcp-index/force_full_exit_trace.json` showed
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/tests/docs/test_p23_doc_truth.py`
  with
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/tests/docs/test_semdogfood_evidence_contract.py`;
  at `2026-04-29T19:33:16Z`, `repository status` terminalized that running
  snapshot to `Trace status: interrupted` with the same exact pair while still
  advertising the repaired exact bounded Python surface for the cleared
  `tests/docs/test_garc_rc_soak_contract.py ->
  tests/docs/test_garel_ga_release_contract.py` seam.
- The current blocker files are both Python docs-contract tests, but they are
  materially different in size and contract shape.
  `tests/docs/test_p23_doc_truth.py` is `143` lines / `4539` bytes and freezes
  support-matrix and public-surface truth across `README.md`,
  `docs/GETTING_STARTED.md`, `docs/DOCKER_GUIDE.md`,
  `docs/MCP_CONFIGURATION.md`, `docs/operations/deployment-runbook.md`,
  `docs/security/*.md`, `AGENTS.md`, `CLAUDE.md`, and
  `mcp_server/AGENTS.md` via assertions such as
  `test_active_docs_do_not_contain_stale_strings`,
  `test_active_release_docs_name_stable_surface_and_support_status`, and
  `test_agent_docs_point_to_support_matrix_and_current_install_path`.
- `tests/docs/test_semdogfood_evidence_contract.py` is `407` lines / `22413`
  bytes and freezes the structure and wording of
  `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, including required headings,
  timestamps, exact lexical-boundary strings, verification command blocks,
  runtime-path reporting, and downstream roadmap-steering claims through
  `test_semdogfood_report_exists_and_names_required_evidence_sections`,
  `test_semdogfood_report_records_trace_freshness_recovery_and_roadmap_steering`,
  and
  `test_semdogfood_report_preserves_command_level_verification_and_runtime_paths`.
- The current exact bounded-path machinery does not yet name this later docs
  truth and dogfood-evidence pair.
  `mcp_server/dispatcher/dispatcher_enhanced.py` already carries
  `_EXACT_BOUNDED_PYTHON_PATHS` for the earlier docs-governance pair, the
  later docs-test pair, the SEMDOCCONTRACTTAIL pair, the SEMGARELTAIL pair,
  and the mock-plugin fixture pair, but it does not include either
  `tests/docs/test_p23_doc_truth.py` or
  `tests/docs/test_semdogfood_evidence_contract.py`.
- `mcp_server/plugins/python_plugin/plugin.py` currently bounds chunking for
  the repaired script seams, the earlier docs pairs, the SEMDOCCONTRACTTAIL
  pair, the SEMGARELTAIL pair, the mock-plugin fixtures, and
  `mcp_server/visualization/quick_charts.py`, but it does not include the
  current
  `test_p23_doc_truth.py -> test_semdogfood_evidence_contract.py` seam.
- `mcp_server/cli/repository_commands.py` already advertises exact lexical
  boundary lines for the earlier docs, script, JSON, mock-plugin,
  SEMDOCCONTRACTTAIL, and SEMGARELTAIL seams, but it has no dedicated helper
  yet for
  `tests/docs/test_p23_doc_truth.py ->
  tests/docs/test_semdogfood_evidence_contract.py`.
- Existing tests are adjacent but incomplete for this seam.
  `tests/test_dispatcher.py`, `tests/test_git_index_manager.py`, and
  `tests/test_repository_commands.py` already freeze the earlier docs pairs,
  the SEMDOCCONTRACTTAIL pair, the SEMGARELTAIL pair, and the mock-plugin
  recovery. `tests/docs/test_semdogfood_evidence_contract.py` already expects
  the dogfood evidence artifact to preserve the newly exposed
  `test_p23_doc_truth.py -> test_semdogfood_evidence_contract.py` blocker and
  to mention downstream steering to `SEMDOCTRUTHTAIL`, but its current
  heading and plan-path expectations are still anchored on the SEMGARELTAIL
  evidence shape.
- SQLite runtime counts after the SEMGARELTAIL rerun remained
  `files = 1152`, `code_chunks = 28182`, `chunk_summaries = 0`, and
  `semantic_points = 0`, so this phase must stay explicitly lexical and
  evidence-local rather than widening back into semantic-stage hypotheses.

Practical planning boundary:

- SEMDOCTRUTHTAIL may tighten exact documentation-truth tail handling,
  dispatcher lexical progress accounting, direct Python-plugin bounded chunk
  behavior, durable trace persistence, operator status wording, and the
  semantic dogfood evidence artifact needed to prove a live rerun either
  advances beyond
  `tests/docs/test_p23_doc_truth.py ->
  tests/docs/test_semdogfood_evidence_contract.py` or surfaces a truthful
  newer blocker.
- SEMDOCTRUTHTAIL must stay narrow and evidence-driven. It must not reopen the
  repaired SEMGARELTAIL seam, introduce a blanket `tests/docs/**/*.py` fast
  path, rewrite unrelated public docs truth claims, or collapse the evidence
  contract into vague smoke assertions unless the refreshed rerun directly
  proves the active blocker requires that narrower local change.

## Interface Freeze Gates

- [ ] IF-0-SEMDOCTRUTHTAIL-1 - Later documentation-truth tail advance
      contract: a refreshed repo-local force-full rerun on the
      post-SEMGARELTAIL head no longer terminalizes with the durable lexical
      trace centered on
      `tests/docs/test_p23_doc_truth.py ->
      tests/docs/test_semdogfood_evidence_contract.py`; it either advances
      durably beyond that pair or emits a truthful newer blocker before the
      120-second watchdog expires.
- [ ] IF-0-SEMDOCTRUTHTAIL-2 - Exact boundary contract: any repair introduced
      by this phase remains limited to the exact documentation-truth and
      dogfood-evidence pair plus the immediate dispatcher or plugin or trace
      or status or evidence plumbing needed to clear it. The phase must not
      become a blanket `tests/docs/**/*.py` fast path and must not reopen the
      repaired
      `tests/docs/test_garc_rc_soak_contract.py ->
      tests/docs/test_garel_ga_release_contract.py` seam without direct
      evidence.
- [ ] IF-0-SEMDOCTRUTHTAIL-3 - Lexical discoverability contract: both exact
      docs-contract files remain lexically discoverable after the repair,
      including durable file-level storage plus bounded symbol or content
      discoverability for
      `test_active_docs_do_not_contain_stale_strings`,
      `test_active_release_docs_name_stable_surface_and_support_status`,
      `test_agent_docs_point_to_support_matrix_and_current_install_path`,
      `test_semdogfood_report_exists_and_names_required_evidence_sections`,
      `test_semdogfood_report_records_trace_freshness_recovery_and_roadmap_steering`,
      and
      `test_semdogfood_report_preserves_command_level_verification_and_runtime_paths`,
      instead of turning either file into an indexing blind spot.
- [ ] IF-0-SEMDOCTRUTHTAIL-4 - Durable trace and operator contract:
      `force_full_exit_trace.json` and `uv run mcp-index repository status`
      stay aligned with the repaired outcome for the exact later docs-truth
      pair and do not regress to stale SEMGARELTAIL-only wording once the
      live rerun advances past it.
- [ ] IF-0-SEMDOCTRUTHTAIL-5 - Evidence and contract-refresh contract:
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the SEMGARELTAIL rerun
      outcome, the SEMDOCTRUTHTAIL rerun command and timestamps, the refreshed
      trace and status output, and the final authoritative verdict for the
      later docs-truth pair; any edits to
      `tests/docs/test_p23_doc_truth.py` or
      `tests/docs/test_semdogfood_evidence_contract.py` must preserve the
      intended truth-contract coverage while reducing only the active lexical
      hotspot.
- [ ] IF-0-SEMDOCTRUTHTAIL-6 - Downstream steering contract: if execution
      reveals a blocker beyond the current roadmap tail, `specs/phase-plans-v7.md`
      is amended before closeout so the next phase-loop step is truthful.

## Lane Index & Dependencies

- SL-0 - Exact documentation-truth fixture freeze; Depends on: SEMGARELTAIL; Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 - Exact documentation-truth bounded indexing repair; Depends on: SL-0; Blocks: SL-2, SL-3, SL-4; Parallel-safe: no
- SL-2 - Durable trace persistence and operator boundary alignment; Depends on: SL-0, SL-1; Blocks: SL-3, SL-4; Parallel-safe: no
- SL-3 - Live rerun evidence reducer and contract refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SL-4; Parallel-safe: no
- SL-4 - Downstream roadmap steering reducer; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: SEMDOCTRUTHTAIL acceptance; Parallel-safe: no

Lane DAG:

```text
SEMGARELTAIL
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SL-4 -> SEMDOCTRUTHTAIL acceptance
```

## Lanes

### SL-0 - Exact Documentation-Truth Fixture Freeze

- **Scope**: Freeze the exact
  `tests/docs/test_p23_doc_truth.py ->
  tests/docs/test_semdogfood_evidence_contract.py` lexical seam in
  deterministic dispatcher coverage before runtime changes so this phase
  proves a narrow repair instead of hand-waving around all later docs tests
  or all status-evidence contracts.
- **Owned files**: `tests/test_dispatcher.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMDOCTRUTHTAIL-1,
  IF-0-SEMDOCTRUTHTAIL-2,
  and IF-0-SEMDOCTRUTHTAIL-3
- **Interfaces consumed**: existing
  `Dispatcher.index_directory(...)`,
  `Dispatcher._build_exact_bounded_python_shard(...)`,
  normal Python routing through `Plugin.indexFile(...)`,
  and the SEMGARELTAIL evidence for the exact later documentation-truth pair
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` with repo-shaped fixtures that
    index exact copies or trimmed representatives of
    `tests/docs/test_p23_doc_truth.py` and
    `tests/docs/test_semdogfood_evidence_contract.py`, prove the lexical
    walker records the exact pair in order, and fail if the repair silently
    turns either file into an untracked blind spot.
  - test: In the same dispatcher coverage, assert that the P23 truth test
    remains symbol or content discoverable for
    `test_active_docs_do_not_contain_stale_strings`,
    `test_active_release_docs_name_stable_surface_and_support_status`, and
    `test_agent_docs_point_to_support_matrix_and_current_install_path`, and
    that the SEMDOGFOOD evidence test remains symbol or content discoverable
    for its three top-level contract tests named above.
  - test: Add a negative guard that unrelated Python files outside the exact
    pair, especially the repaired SEMDOCCONTRACTTAIL pair, the repaired
    SEMGARELTAIL pair, and the cleared mock-plugin fixtures, still use their
    own existing bounded or normal handling. The repair must not quietly
    become a broader `tests/docs/**/*.py` fast path.
  - impl: Keep fixtures deterministic with repo-local Python strings and
    monkeypatched bounded-path instrumentation rather than long-running live
    waits inside unit tests.
  - impl: Keep this lane on contract freeze only. Do not mutate durable
    trace, CLI wording, evidence docs, or roadmap steering here.
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "p23 or semdogfood or doc_truth or evidence_contract or lexical or bounded"`

### SL-1 - Exact Documentation-Truth Bounded Indexing Repair

- **Scope**: Implement the smallest dispatcher and Python-plugin repair needed
  so the live lexical walker no longer burns its watchdog budget on the exact
  `tests/docs/test_p23_doc_truth.py ->
  tests/docs/test_semdogfood_evidence_contract.py` pair.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `mcp_server/plugins/python_plugin/plugin.py`
- **Interfaces provided**: IF-0-SEMDOCTRUTHTAIL-2 exact boundary contract;
  IF-0-SEMDOCTRUTHTAIL-3 lexical discoverability contract
- **Interfaces consumed**: SL-0 later documentation-truth fixtures; existing
  exact bounded Python behavior in
  `Dispatcher._build_exact_bounded_python_shard(...)`; and the current Python
  bounded chunk rules in `Plugin._BOUNDED_CHUNK_PATHS`
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 dispatcher slice first and confirm which side of the
    pair still consumes watchdog budget in the current force-full path: the
    smaller P23 truth contract, the much larger SEMDOGFOOD evidence contract,
    or the handoff between them.
  - impl: Apply the narrowest repair that clears the exact pair. Prefer
    exact-path bounded handling over any broader docs-test shortcut, and keep
    the repair local to the dispatcher or the relevant Python plugin path.
  - impl: Preserve content discoverability for
    `tests/docs/test_p23_doc_truth.py`, including the support-matrix column
    assertions, stale-string guards, stable-surface assertions, and AGENTS
    install-path checks, instead of reducing the file to an opaque skipped
    artifact.
  - impl: Preserve top-level symbol or content discoverability for
    `tests/docs/test_semdogfood_evidence_contract.py`, including the required
    evidence headings, roadmap-steering strings, verification command blocks,
    and lexical-boundary assertions already frozen there.
  - impl: Do not widen `_EXACT_BOUNDED_PYTHON_PATHS` or
    `Plugin._BOUNDED_CHUNK_PATHS` beyond what is needed for this exact pair,
    and do not add a repo-wide docs timeout or generic plaintext bypass that
    would mask later blockers.
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "p23 or semdogfood or doc_truth or evidence_contract or lexical or bounded"`

### SL-2 - Durable Trace Persistence And Operator Boundary Alignment

- **Scope**: Carry the exact later documentation-truth repair into the durable
  force-full trace and operator status surfaces so runtime reporting
  truthfully distinguishes the cleared pair from any later blocker.
- **Owned files**: `mcp_server/storage/git_index_manager.py`, `mcp_server/cli/repository_commands.py`, `tests/test_git_index_manager.py`, `tests/test_repository_commands.py`
- **Interfaces provided**: IF-0-SEMDOCTRUTHTAIL-1 later documentation-truth
  tail advance contract; IF-0-SEMDOCTRUTHTAIL-4 durable trace and operator
  contract
- **Interfaces consumed**: SL-0 fixture expectations; SL-1 repaired exact
  documentation-truth bounded indexing behavior; existing
  `force_full_exit_trace.json` persistence in `GitAwareIndexManager`; and
  current operator boundary helpers in `repository_commands.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_git_index_manager.py` so durable trace fixtures
    preserve the exact
    `tests/docs/test_p23_doc_truth.py ->
    tests/docs/test_semdogfood_evidence_contract.py` blocker when it is
    active and prove the rerun advances to a newer blocker without regressing
    to the cleared SEMGARELTAIL boundary.
  - test: Extend `tests/test_repository_commands.py` so `repository status`
    advertises the repaired exact bounded lexical surface for the later
    documentation-truth pair and still prints the correct later
    `last_progress_path` and `in_flight_path` when the live blocker moves
    forward.
  - impl: Add the narrowest operator helper needed to describe
    `tests/docs/test_p23_doc_truth.py ->
    tests/docs/test_semdogfood_evidence_contract.py` consistently with the
    earlier exact-boundary messages.
  - impl: Keep trace persistence and CLI messaging aligned on the same exact
    pair name and avoid stale SEMGARELTAIL-only wording once the rerun moves
    past the GA release docs seam.
  - impl: Do not widen trace persistence or status reporting into unrelated
    semantic readiness or rollout status changes while closing this lexical
    seam.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "p23 or semdogfood or doc_truth or evidence_contract or boundary or interrupted or lexical"`

### SL-3 - Live Rerun Evidence Reducer And Contract Refresh

- **Scope**: Refresh the dogfood evidence and the exact docs-truth contract
  files so the current head records the SEMGARELTAIL outcome and the final
  live verdict for the later
  `test_p23_doc_truth.py -> test_semdogfood_evidence_contract.py` seam.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_p23_doc_truth.py`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: IF-0-SEMDOCTRUTHTAIL-1 later documentation-truth
  tail advance contract; IF-0-SEMDOCTRUTHTAIL-3 lexical discoverability
  contract; IF-0-SEMDOCTRUTHTAIL-5 evidence and contract-refresh contract
- **Interfaces consumed**: SL-0 fixture expectations; SL-1 exact bounded
  repair; SL-2 trace and operator wording; current evidence structure in
  `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`; and the current public-doc truth
  contract frozen by `tests/docs/test_p23_doc_truth.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Update `tests/docs/test_semdogfood_evidence_contract.py` so it
    requires the SEMGARELTAIL rerun outcome, the SEMDOCTRUTHTAIL plan path,
    the SEMDOCTRUTHTAIL rerun command and timestamps, the repaired exact
    lexical-boundary wording for
    `tests/docs/test_p23_doc_truth.py ->
    tests/docs/test_semdogfood_evidence_contract.py`, and the correct next
    downstream steering if a newer blocker appears beyond the current roadmap
    tail.
  - test: Keep `tests/docs/test_p23_doc_truth.py` aligned with the intended
    public-doc truth contract. Only change it if the refreshed rerun or the
    bounded indexing proof shows a narrower local contract edit is necessary
    to clear the active lexical hotspot without diluting the assertions.
  - impl: Refresh `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` with the
    SEMGARELTAIL acceptance outcome, the SEMDOCTRUTHTAIL live rerun command,
    timestamps, trace snapshot, repository-status output, runtime counts, and
    final verdict for the later documentation-truth pair.
  - impl: If the active hotspot is inside the literal-heavy evidence-contract
    file rather than the routing layer, keep any edit to
    `tests/docs/test_semdogfood_evidence_contract.py` local and
    contract-preserving: reduce only duplicated literal mass or fixture shape
    that the rerun proves is active, while preserving exact evidence claims.
  - impl: Do not rewrite unrelated public docs, historical evidence anchors,
    or older SEM* roadmap-steering strings that are not implicated by the
    refreshed rerun.
  - verify: `uv run pytest tests/docs/test_p23_doc_truth.py tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
  - verify: `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - verify: `sed -n '1,240p' .mcp-index/force_full_exit_trace.json`
  - verify: `sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'`

### SL-4 - Downstream Roadmap Steering Reducer

- **Scope**: Keep the roadmap and next phase-loop step truthful if the
  repaired live rerun proves a blocker beyond the current roadmap tail.
- **Owned files**: `specs/phase-plans-v7.md`
- **Interfaces provided**: the downstream-steering portion of
  IF-0-SEMDOCTRUTHTAIL-6
- **Interfaces consumed**: SL-3 refreshed evidence verdict; current roadmap
  DAG and phase ordering for `specs/phase-plans-v7.md`; the already tracked
  `plans/phase-plan-v7-SEMGARELTAIL.md`; and canonical `.phase-loop/`
  expectations that the next unplanned phase reflects the latest durable
  blocker rather than stale SEMGARELTAIL assumptions
- **Parallel-safe**: no
- **Tasks**:
  - test: Re-read the post-SL-3 evidence and confirm whether the repaired
    rerun actually exposes a newer blocker beyond the current roadmap tail
    before mutating roadmap steering.
  - impl: If the active blocker remains inside the current SEMDOCTRUTHTAIL
    documentation-truth family or the rerun completes the lexical closeout,
    leave the roadmap unchanged.
  - impl: If the active blocker advances beyond the current roadmap tail and
    no downstream phase already covers it, append the nearest truthful
    downstream recovery phase to `specs/phase-plans-v7.md` with the same
    evidence-first structure used by the current SEM* lexical-recovery chain.
  - impl: Keep any roadmap mutation limited to the newly exposed blocker. Do
    not rewrite earlier phases or backfill unrelated sequencing while closing
    this seam.
  - verify: `git diff -- specs/phase-plans-v7.md`

## Verification

- Lane checks:
  - `uv run pytest tests/test_dispatcher.py -q --no-cov -k "p23 or semdogfood or doc_truth or evidence_contract or lexical or bounded"`
  - `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "p23 or semdogfood or doc_truth or evidence_contract or boundary or interrupted or lexical"`
  - `uv run pytest tests/docs/test_p23_doc_truth.py tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
- Whole-phase checks:
  - `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_repository_commands.py tests/docs/test_p23_doc_truth.py tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "p23 or semdogfood or doc_truth or evidence or lexical or bounded or boundary or interrupted"`
  - `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  - `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - `sed -n '1,240p' .mcp-index/force_full_exit_trace.json`
  - `sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'`
  - `git diff --check`
  - `git diff --cached --check`

## Acceptance Criteria

- [ ] A refreshed repo-local force-full rerun on the post-SEMGARELTAIL head
      either advances durably beyond the later
      `tests/docs/test_p23_doc_truth.py ->
      tests/docs/test_semdogfood_evidence_contract.py` pair or emits a
      truthful newer blocker before the 120-second watchdog expires.
- [ ] The repair stays narrowly scoped to the exact documentation-truth and
      dogfood-evidence pair and the immediate dispatcher or plugin or trace or
      status or evidence plumbing needed to prove it.
- [ ] The repaired documentation-truth surfaces remain lexically discoverable
      with durable file-level storage plus bounded content discoverability for
      the key P23 and SEMDOGFOOD assertions named above.
- [ ] `uv run mcp-index repository status` and
      `force_full_exit_trace.json` stay aligned with the repaired
      documentation-truth outcome and do not regress to stale
      SEMGARELTAIL-only wording.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMGARELTAIL rerun outcome and the final live verdict for the later
      documentation-truth pair.
- [ ] If execution reveals a newer blocker beyond the current roadmap tail,
      `specs/phase-plans-v7.md` is updated before closeout so the next
      phase-loop step is truthful.

automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMDOCTRUTHTAIL.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMDOCTRUTHTAIL.md
  artifact_state: staged
