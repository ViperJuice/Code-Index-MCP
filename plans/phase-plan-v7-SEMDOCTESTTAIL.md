---
phase_loop_plan_version: 1
phase: SEMDOCTESTTAIL
roadmap: specs/phase-plans-v7.md
roadmap_sha256: b3a93d2d3b3a312c1187d343344d16f865b2f77c0686c707154352e24191a57a
---
# SEMDOCTESTTAIL: Docs-Test Tail Recovery

## Context

SEMDOCTESTTAIL is the phase-57 follow-up for the v7 semantic hardening
roadmap. Canonical `.phase-loop/` state is authoritative for this run:
`.phase-loop/state.json` and `.phase-loop/tui-handoff.md` both mark
`SEMDOCTESTTAIL` as the current `unplanned` phase after `SEMEMBEDCONSOL`
closed out on `HEAD` `066c1f4e1a06ebf765fdb3e34e850c7252245de4` with
verification `passed`, a clean worktree, and `main...origin/main [ahead 109]`.
Legacy `.codex/phase-loop/` artifacts are compatibility-only and are not
authoritative here.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is tracked and clean in this worktree, and
  `sha256sum specs/phase-plans-v7.md` matches the required
  `b3a93d2d3b3a312c1187d343344d16f865b2f77c0686c707154352e24191a57a`.
- The target artifact `plans/phase-plan-v7-SEMDOCTESTTAIL.md` did not exist
  before this planning run.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is the active evidence anchor.
  Its SEMEMBEDCONSOL rerun block captures the current downstream lexical
  failure precisely: the refreshed repo-local command
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  started on observed commit `5c0102d`, and at `2026-04-29T17:45:44Z`
  `.mcp-index/force_full_exit_trace.json` showed
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/tests/docs/test_gaclose_evidence_closeout.py`
  with
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/tests/docs/test_p8_deployment_security.py`;
  at `2026-04-29T17:45:52Z`, `repository status` terminalized that running
  snapshot to `Trace status: interrupted` with the same exact pair.
- The SEMEMBEDCONSOL target seam is no longer the active blocker:
  `scripts/create_semantic_embeddings.py ->
  scripts/consolidate_real_performance_data.py`. The authoritative
  current-head blocker is now the later docs/tests pair
  `tests/docs/test_gaclose_evidence_closeout.py ->
  tests/docs/test_p8_deployment_security.py`, so older downstream
  assumptions should be treated as stale.
- The two exact test files are both Python but differ in shape and likely
  indexing cost. `tests/docs/test_gaclose_evidence_closeout.py` is `151`
  lines / `5451` bytes with top-level helpers `_read(...)`,
  `_normalized(...)`, and multiple evidence-assertion test functions.
  `tests/docs/test_p8_deployment_security.py` is `85` lines / `2929` bytes
  with helper functions `_load_lines()`,
  `_security_section_line_range(...)`, and a focused set of deployment-guide
  security assertions.
- The current exact bounded-path machinery does not yet name this docs/tests
  pair. `mcp_server/dispatcher/dispatcher_enhanced.py` already carries
  `_EXACT_BOUNDED_PYTHON_PATHS` for the earlier docs-governance pair
  `tests/docs/test_mre2e_evidence_contract.py ->
  tests/docs/test_gagov_governance_contract.py` plus the later exact
  script-pair recoveries, but it does not include either
  `tests/docs/test_gaclose_evidence_closeout.py` or
  `tests/docs/test_p8_deployment_security.py`.
- `mcp_server/plugins/python_plugin/plugin.py` currently bounds chunking for
  the repaired later script pairs and selected high-cost Python files, but it
  does not include the current docs/tests pair. Both blocker files therefore
  still fall through the normal Python plugin chunking path during lexical
  walking.
- `mcp_server/cli/repository_commands.py` already advertises exact lexical
  boundary messages for the earlier docs-governance pair and the later
  script-pair recoveries, but it has no dedicated helper yet for
  `tests/docs/test_gaclose_evidence_closeout.py ->
  tests/docs/test_p8_deployment_security.py`.
- Existing tests already freeze adjacent behavior but not this exact later
  pair. `tests/test_dispatcher.py` covers the earlier docs-governance pair and
  the later exact script seams; `tests/test_git_index_manager.py` and
  `tests/test_repository_commands.py` preserve durable trace and operator
  wording for those earlier boundaries; and
  `tests/docs/test_semdogfood_evidence_contract.py` already expects the
  dogfood evidence artifact to retain the current docs/tests pair and the
  roadmap steering to downstream phase `SEMDOCTESTTAIL`.

Practical planning boundary:

- SEMDOCTESTTAIL may tighten exact docs-test tail handling, dispatcher lexical
  progress accounting, durable trace persistence, operator status wording, and
  the semantic dogfood evidence artifact needed to prove a live rerun either
  advances beyond
  `tests/docs/test_gaclose_evidence_closeout.py ->
  tests/docs/test_p8_deployment_security.py` or surfaces a truthful newer
  blocker.
- SEMDOCTESTTAIL must stay narrow and evidence-driven. It must not reopen the
  repaired embed/consolidation recovery, introduce a blanket
  `tests/docs/*.py` fast path, retune the repo-wide lexical watchdog, or
  reopen the older docs-governance seam
  `tests/docs/test_mre2e_evidence_contract.py ->
  tests/docs/test_gagov_governance_contract.py` unless the refreshed rerun
  directly re-anchors there again.

## Interface Freeze Gates

- [ ] IF-0-SEMDOCTESTTAIL-1 - Later docs-test tail advance contract:
      a refreshed repo-local force-full rerun on the post-SEMEMBEDCONSOL
      head no longer terminalizes with the durable lexical trace centered on
      `tests/docs/test_gaclose_evidence_closeout.py ->
      tests/docs/test_p8_deployment_security.py`; it either advances durably
      beyond that pair or emits a truthful newer blocker before the
      120-second watchdog expires.
- [ ] IF-0-SEMDOCTESTTAIL-2 - Exact boundary contract:
      any repair introduced by this phase remains limited to the exact
      docs/tests pair plus the immediate dispatcher/plugin/trace/status
      plumbing needed to clear it. The phase must not introduce a new blanket
      `tests/docs/*.py` fast path, and it must not reopen the prior
      `scripts/create_semantic_embeddings.py ->
      scripts/consolidate_real_performance_data.py` seam without direct
      evidence.
- [ ] IF-0-SEMDOCTESTTAIL-3 - Lexical discoverability contract:
      both exact docs/tests files remain lexically discoverable after the
      repair, including durable file-level storage plus bounded symbol or
      content discoverability for
      `test_decision_artifact_links_prerequisite_evidence_and_verification`,
      `test_support_matrix_freezes_claim_tiers_and_topology_limits`,
      `test_security_heading_present`, and
      `test_mcp_access_controls_subsection_present`, instead of turning either
      file into an indexing blind spot.
- [ ] IF-0-SEMDOCTESTTAIL-4 - Durable trace and operator contract:
      `force_full_exit_trace.json` and `uv run mcp-index repository status`
      stay aligned with the repaired outcome for the exact later docs/tests
      pair and do not regress to stale SEMEMBEDCONSOL-only wording once the
      live rerun advances past it.
- [ ] IF-0-SEMDOCTESTTAIL-5 - Evidence and downstream steering contract:
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the SEMEMBEDCONSOL
      rerun outcome, the SEMDOCTESTTAIL rerun command and timestamps, the
      refreshed trace/status output, and the final authoritative verdict for
      the later docs/tests pair; if execution reveals a blocker beyond the
      current roadmap tail, `specs/phase-plans-v7.md` is amended before
      closeout so the next phase-loop step is truthful.

## Lane Index & Dependencies

- SL-0 - Exact later docs-test fixture freeze; Depends on: SEMEMBEDCONSOL; Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 - Exact docs-test bounded indexing repair; Depends on: SL-0; Blocks: SL-2, SL-3, SL-4; Parallel-safe: no
- SL-2 - Durable trace persistence and operator boundary alignment; Depends on: SL-0, SL-1; Blocks: SL-3, SL-4; Parallel-safe: no
- SL-3 - Live rerun evidence reducer and contract refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SL-4; Parallel-safe: no
- SL-4 - Downstream roadmap steering reducer; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: SEMDOCTESTTAIL acceptance; Parallel-safe: no

Lane DAG:

```text
SEMEMBEDCONSOL
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SL-4 -> SEMDOCTESTTAIL acceptance
```

## Lanes

### SL-0 - Exact Later Docs-Test Fixture Freeze

- **Scope**: Freeze the exact
  `tests/docs/test_gaclose_evidence_closeout.py ->
  tests/docs/test_p8_deployment_security.py` lexical seam in deterministic
  dispatcher coverage before runtime changes so this phase proves a narrow
  repair instead of hand-waving around all `tests/docs` Python files.
- **Owned files**: `tests/test_dispatcher.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMDOCTESTTAIL-1,
  IF-0-SEMDOCTESTTAIL-2,
  and IF-0-SEMDOCTESTTAIL-3 at the dispatcher/plugin boundary
- **Interfaces consumed**: existing
  `Dispatcher.index_directory(...)`,
  `Dispatcher._build_exact_bounded_python_shard(...)`,
  normal Python routing through `Plugin.indexFile(...)`,
  and the SEMEMBEDCONSOL evidence for the exact later docs/tests pair
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` with a repo-shaped fixture that
    indexes exact copies or trimmed representatives of
    `tests/docs/test_gaclose_evidence_closeout.py` and
    `tests/docs/test_p8_deployment_security.py`, proves the lexical walker
    records the exact pair in order, and fails if the repair silently turns
    either file into an untracked blind spot.
  - test: In the same dispatcher coverage, assert that the GACLOSE docs test
    remains symbol or content discoverable for
    `test_decision_artifact_links_prerequisite_evidence_and_verification`
    and that the P8 deployment-security test remains symbol or content
    discoverable for `test_security_heading_present` and
    `test_mcp_access_controls_subsection_present` after the repair.
  - test: Add a negative guard that unrelated Python files outside the exact
    pair, especially the earlier docs-governance tests, still use their own
    existing bounded or normal handling. The watchdog repair must not quietly
    become a broader `tests/docs/*.py` fast path.
  - impl: Keep fixtures deterministic with repo-local Python strings and
    monkeypatched bounded-path instrumentation rather than long-running live
    waits inside unit tests.
  - impl: Keep this lane on contract freeze only. Do not mutate durable
    trace, CLI wording, evidence docs, or roadmap steering here.
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "gaclose_evidence_closeout or p8_deployment_security or lexical or bounded or deployment or security or docs"`

### SL-1 - Exact Docs-Test Bounded Indexing Repair

- **Scope**: Implement the smallest dispatcher and Python-plugin repair
  needed so the live lexical walker no longer burns its watchdog budget on
  the exact
  `test_gaclose_evidence_closeout.py -> test_p8_deployment_security.py`
  docs/tests pair.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `mcp_server/plugins/python_plugin/plugin.py`
- **Interfaces provided**: IF-0-SEMDOCTESTTAIL-2 exact boundary contract;
  IF-0-SEMDOCTESTTAIL-3 lexical discoverability contract
- **Interfaces consumed**: SL-0 later docs-test fixtures; existing exact
  bounded Python behavior in
  `Dispatcher._build_exact_bounded_python_shard(...)`; and the current
  Python bounded chunk rules in `Plugin._BOUNDED_CHUNK_PATHS`
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 dispatcher slice first and confirm which side of the
    pair still consumes watchdog budget in the current force-full path: the
    larger GACLOSE evidence test, the smaller P8 deployment-security test, or
    the handoff between them.
  - impl: Apply the narrowest repair that clears the exact pair. Prefer
    exact-path bounded handling over any broad docs-test shortcut, and keep
    the repair local to the dispatcher or the relevant Python plugin path.
  - impl: Preserve content discoverability for
    `tests/docs/test_gaclose_evidence_closeout.py`, including its historical
    evidence assertions and helper surfaces, instead of reducing the file to
    an opaque skipped artifact.
  - impl: Preserve top-level symbol or content discoverability for
    `tests/docs/test_p8_deployment_security.py`, including
    `_security_section_line_range(...)`,
    `test_security_heading_present`, and
    `test_mcp_access_controls_subsection_present`.
  - impl: Do not widen `_EXACT_BOUNDED_PYTHON_PATHS` or
    `Plugin._BOUNDED_CHUNK_PATHS` beyond what is needed for this exact
    pair, and do not introduce a repo-wide Python timeout or global plaintext
    bypass that masks later blockers.
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "gaclose_evidence_closeout or p8_deployment_security or lexical or bounded or deployment or security or docs"`

### SL-2 - Durable Trace Persistence And Operator Boundary Alignment

- **Scope**: Carry the exact later docs/tests repair into the durable
  force-full trace and operator status surfaces so runtime reporting
  truthfully distinguishes the cleared pair from any later blocker.
- **Owned files**: `mcp_server/storage/git_index_manager.py`, `mcp_server/cli/repository_commands.py`, `tests/test_git_index_manager.py`, `tests/test_repository_commands.py`
- **Interfaces provided**: IF-0-SEMDOCTESTTAIL-1 later docs-test tail
  advance contract; IF-0-SEMDOCTESTTAIL-4 durable trace and operator
  contract
- **Interfaces consumed**: SL-0 fixture expectations; SL-1 repaired exact
  docs-test bounded indexing behavior; existing `force_full_exit_trace.json`
  persistence in `GitAwareIndexManager`; and current operator boundary
  helpers in `repository_commands.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_git_index_manager.py` so durable trace fixtures
    preserve the exact
    `tests/docs/test_gaclose_evidence_closeout.py ->
    tests/docs/test_p8_deployment_security.py` blocker when it is active
    and prove the rerun advances to a newer blocker without regressing to
    the cleared SEMEMBEDCONSOL seam.
  - test: Extend `tests/test_repository_commands.py` so `repository status`
    advertises the repaired exact bounded lexical surface for the later
    docs/tests pair and still prints the correct later
    `last_progress_path` and `in_flight_path` when the live blocker moves
    forward.
  - impl: Add the minimal `repository status` helper or wording needed to
    name the exact docs/tests pair once the repair is in place, matching the
    existing style used for the earlier docs-governance pair and later exact
    script seams.
  - impl: Preserve truthful terminalization behavior when the live command
    times out or fails later. This lane must not relabel a later blocker as if
    the docs/tests seam were still active once the rerun has moved on.
  - impl: Keep earlier boundary wording for
    `tests/docs/test_mre2e_evidence_contract.py ->
    tests/docs/test_gagov_governance_contract.py` and
    `scripts/create_semantic_embeddings.py ->
    scripts/consolidate_real_performance_data.py` intact unless the rerun
    directly proves one of those seams has regressed.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "gaclose_evidence_closeout or p8_deployment_security or lexical or interrupted or boundary or deployment or security or docs"`

### SL-3 - Live Rerun Evidence Reducer And Contract Refresh

- **Scope**: Refresh the real dogfood evidence after the exact later
  docs/tests repair so the active blocker report matches the repaired runtime
  rather than stale SEMEMBEDCONSOL assumptions.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: the evidence portion of
  IF-0-SEMDOCTESTTAIL-5
- **Interfaces consumed**: SL-2 durable trace and repository-status output;
  live rerun command output; existing SEMEMBEDCONSOL evidence block; and the
  current evidence-contract assertions in
  `tests/docs/test_semdogfood_evidence_contract.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/docs/test_semdogfood_evidence_contract.py` only as
    needed so the status artifact must retain the exact current blocker pair,
    the SEMDOCTESTTAIL phase name, and any newly exposed downstream steering
    after execution.
  - impl: Run a fresh repo-local force-full rerun after SL-1 and SL-2 land,
    then capture the rerun command, observed commit, timeout or completion
    timestamp, durable trace snapshot, `repository status` output, and SQLite
    counts in `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`.
  - impl: If the repaired rerun still times out, record the exact later
    blocker pair that replaced
    `tests/docs/test_gaclose_evidence_closeout.py ->
    tests/docs/test_p8_deployment_security.py` rather than leaving the older
    pair as the active narrative.
  - impl: Keep this lane on evidence reduction. Do not back-edit older phase
    narratives except where the new rerun explicitly supersedes the active
    blocker statement.
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`

### SL-4 - Downstream Roadmap Steering Reducer

- **Scope**: Keep the roadmap and next phase-loop step truthful if the
  repaired live rerun proves a newer blocker beyond the current roadmap tail.
- **Owned files**: `specs/phase-plans-v7.md`
- **Interfaces provided**: the downstream-steering portion of
  IF-0-SEMDOCTESTTAIL-5
- **Interfaces consumed**: SL-3 refreshed evidence verdict; current roadmap
  DAG and phase ordering for `specs/phase-plans-v7.md`; canonical
  `.phase-loop/` expectation that the next unplanned phase reflects the
  latest durable blocker rather than stale prior assumptions
- **Parallel-safe**: no
- **Tasks**:
  - test: Re-read the post-SL-3 evidence and confirm whether the repaired
    rerun actually exposes a newer blocker beyond the current roadmap tail
    before mutating roadmap steering.
  - impl: If the active blocker is still the exact later docs/tests pair,
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
  - `uv run pytest tests/test_dispatcher.py -q --no-cov -k "gaclose_evidence_closeout or p8_deployment_security or lexical or bounded or deployment or security or docs"`
  - `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "gaclose_evidence_closeout or p8_deployment_security or lexical or interrupted or boundary or deployment or security or docs"`
  - `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
- Whole-phase checks:
  - `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_repository_commands.py tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "gaclose_evidence_closeout or p8_deployment_security or lexical or bounded or interrupted or boundary or deployment or security or docs"`
  - `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  - `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - `sed -n '1,240p' .mcp-index/force_full_exit_trace.json`
  - `sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'`
  - `git diff --check`
  - `git diff --cached --check`

## Acceptance Criteria

- [ ] A refreshed repo-local force-full rerun on the post-SEMEMBEDCONSOL
      head either advances durably beyond
      `tests/docs/test_gaclose_evidence_closeout.py ->
      tests/docs/test_p8_deployment_security.py` or emits a truthful newer
      blocker before the 120-second watchdog expires.
- [ ] The repair stays narrowly scoped to the exact later docs/tests pair
      and the immediate dispatcher/plugin/trace/status/evidence plumbing
      needed to prove it.
- [ ] Both exact docs/tests files remain lexically discoverable with durable
      file-level storage plus bounded symbol or content discoverability for
      `test_decision_artifact_links_prerequisite_evidence_and_verification`,
      `test_support_matrix_freezes_claim_tiers_and_topology_limits`,
      `test_security_heading_present`, and
      `test_mcp_access_controls_subsection_present`.
- [ ] `uv run mcp-index repository status` and
      `force_full_exit_trace.json` stay aligned with the repaired later
      docs/tests boundary outcome and do not regress to stale
      SEMEMBEDCONSOL wording.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the SEMEMBEDCONSOL
      rerun outcome and the final live verdict for the later docs/tests pair.
- [ ] If execution reveals a newer blocker beyond the current roadmap tail,
      `specs/phase-plans-v7.md` is updated before closeout so the next
      phase-loop step is truthful.

automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMDOCTESTTAIL.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMDOCTESTTAIL.md
  artifact_state: staged
