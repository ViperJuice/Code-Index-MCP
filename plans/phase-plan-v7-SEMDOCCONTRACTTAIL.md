---
phase_loop_plan_version: 1
phase: SEMDOCCONTRACTTAIL
roadmap: specs/phase-plans-v7.md
roadmap_sha256: 8ca72546b3b2768908084226aae1c7111194f95f99c1e33b9c92b08d7c0e96f5
---
# SEMDOCCONTRACTTAIL: Docs Contract Tail Recovery

## Context

SEMDOCCONTRACTTAIL is the phase-60 follow-up for the v7 semantic hardening
roadmap. Canonical `.phase-loop/` state is authoritative for this run:
`.phase-loop/state.json` and `.phase-loop/tui-handoff.md` both mark
`SEMDOCCONTRACTTAIL` as the current `unplanned` phase after
`SEMCODEXLOOPTAIL` closed out on `HEAD`
`c53477cfb3fefe90a5c801b6db5712d274402df9` with verification `passed`, a
clean worktree, and `main...origin/main [ahead 115]`. Legacy
`.codex/phase-loop/` artifacts remain compatibility-only and do not
supersede canonical `.phase-loop/` runner state here.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is tracked and clean in this worktree, and
  `sha256sum specs/phase-plans-v7.md` matches the required
  `8ca72546b3b2768908084226aae1c7111194f95f99c1e33b9c92b08d7c0e96f5`.
- The target artifact `plans/phase-plan-v7-SEMDOCCONTRACTTAIL.md` did not
  exist before this planning run.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is the active evidence anchor.
  Its SEMCODEXLOOPTAIL rerun block records the current downstream lexical
  blocker precisely: on observed commit `3d627c33`, the refreshed repo-local
  command `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  advanced beyond the repaired legacy `.codex/phase-loop` family and, at
  `2026-04-29T18:52:49Z`, `.mcp-index/force_full_exit_trace.json` showed
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/tests/docs/test_semincr_contract.py`
  with
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/tests/docs/test_gabase_ga_readiness_contract.py`;
  at `2026-04-29T18:52:55Z`, `repository status` terminalized that running
  snapshot to `Trace status: interrupted` with the same exact pair.
- The current blocker files are both Python docs-contract tests but have
  different shapes and likely different indexing cost.
  `tests/docs/test_semincr_contract.py` is `18` lines / `882` bytes and
  freezes `docs/guides/semantic-onboarding.md` contract language through
  `test_semincr_docs_freeze_incremental_mutation_contract` and
  `test_semincr_docs_stay_out_of_query_routing_and_dogfood_claims`.
  `tests/docs/test_gabase_ga_readiness_contract.py` is `155` lines /
  `4477` bytes and freezes `docs/validation/ga-readiness-checklist.md`,
  support-tier wording, topology claims, and runbook references through
  checks such as `test_checklist_exists_with_required_sections_and_baseline`,
  `test_checklist_distinguishes_input_and_refresh_evidence`, and
  `test_public_docs_remain_pre_ga_and_route_to_canonical_artifacts`.
- The current exact bounded-path machinery does not yet name this later
  docs contract pair. `mcp_server/dispatcher/dispatcher_enhanced.py`
  already carries exact bounded Python entries for the earlier
  `tests/docs/test_mre2e_evidence_contract.py ->
  tests/docs/test_gagov_governance_contract.py` pair, the later
  `tests/docs/test_gaclose_evidence_closeout.py ->
  tests/docs/test_p8_deployment_security.py` pair, and the mock-plugin
  fixture pair, but it does not include either
  `tests/docs/test_semincr_contract.py` or
  `tests/docs/test_gabase_ga_readiness_contract.py`.
- `mcp_server/plugins/python_plugin/plugin.py` currently bounds chunking for
  the repaired script pairs, earlier docs-contract pairs, and the
  mock-plugin fixtures, but it does not include the current
  `test_semincr_contract.py -> test_gabase_ga_readiness_contract.py` seam.
- `mcp_server/cli/repository_commands.py` already advertises exact lexical
  boundary messages for the earlier docs-governance pair, the later docs-test
  pair, the mock-plugin pair, and the legacy `.codex/phase-loop` family, but
  it has no dedicated helper yet for the current docs contract-test pair.
- Existing tests are adjacent but incomplete for this seam.
  `tests/test_dispatcher.py`, `tests/test_git_index_manager.py`, and
  `tests/test_repository_commands.py` already freeze the earlier docs
  pairs and later lexical-tail recoveries, while
  `tests/docs/test_semdogfood_evidence_contract.py` already expects the live
  evidence artifact to preserve the SEMCODEXLOOPTAIL rerun outcome, the
  later `test_semincr_contract.py ->
  test_gabase_ga_readiness_contract.py` blocker, and downstream steering to
  `SEMDOCCONTRACTTAIL`.

Practical planning boundary:

- SEMDOCCONTRACTTAIL may tighten exact docs contract-test tail handling,
  dispatcher lexical progress accounting, durable trace persistence, operator
  status wording, and the semantic dogfood evidence needed to prove a live
  rerun either advances beyond
  `tests/docs/test_semincr_contract.py ->
  tests/docs/test_gabase_ga_readiness_contract.py` or surfaces a truthful
  newer blocker.
- SEMDOCCONTRACTTAIL must stay narrow and evidence-driven. It must not reopen
  the repaired legacy `.codex/phase-loop` compatibility-runtime recovery,
  introduce a blanket `tests/docs/**/*.py` bypass, or widen into unrelated
  docs or GA-planning changes unless the refreshed rerun directly proves the
  active blocker requires them.

## Interface Freeze Gates

- [ ] IF-0-SEMDOCCONTRACTTAIL-1 - Later docs contract-test tail advance
      contract: a refreshed repo-local force-full rerun on the
      post-SEMCODEXLOOPTAIL head no longer terminalizes with the durable
      lexical trace centered on
      `tests/docs/test_semincr_contract.py ->
      tests/docs/test_gabase_ga_readiness_contract.py`; it either advances
      durably beyond that pair or emits a truthful newer blocker before the
      120-second watchdog expires.
- [ ] IF-0-SEMDOCCONTRACTTAIL-2 - Exact boundary contract: any repair
      introduced by this phase remains limited to the exact later docs
      contract-test pair plus the immediate dispatcher or plugin or trace or
      status plumbing needed to clear it. The phase must not become a blanket
      `tests/docs/**/*.py` fast path and must not reopen the repaired legacy
      `.codex/phase-loop` family without direct evidence.
- [ ] IF-0-SEMDOCCONTRACTTAIL-3 - Lexical discoverability contract: both
      exact docs contract-test files remain lexically discoverable after the
      repair, including durable file-level storage plus bounded symbol or
      content discoverability for
      `test_semincr_docs_freeze_incremental_mutation_contract`,
      `test_semincr_docs_stay_out_of_query_routing_and_dogfood_claims`,
      `test_checklist_exists_with_required_sections_and_baseline`,
      `test_checklist_distinguishes_input_and_refresh_evidence`, and
      `test_public_docs_remain_pre_ga_and_route_to_canonical_artifacts`,
      instead of turning either file into an indexing blind spot.
- [ ] IF-0-SEMDOCCONTRACTTAIL-4 - Durable trace and operator contract:
      `force_full_exit_trace.json` and `uv run mcp-index repository status`
      stay aligned with the repaired outcome for the exact later docs
      contract-test pair and do not regress to stale SEMCODEXLOOPTAIL-only
      wording once the live rerun advances past it.
- [ ] IF-0-SEMDOCCONTRACTTAIL-5 - Evidence and downstream steering contract:
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMCODEXLOOPTAIL rerun outcome, the SEMDOCCONTRACTTAIL rerun command and
      timestamps, the refreshed trace and status output, and the final
      authoritative verdict for the later docs contract-test pair; if
      execution reveals a blocker beyond the current roadmap tail,
      `specs/phase-plans-v7.md` is amended before closeout so the next
      phase-loop step is truthful.

## Lane Index & Dependencies

- SL-0 - Exact later docs contract-test fixture freeze; Depends on: SEMCODEXLOOPTAIL; Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 - Exact docs contract-test bounded indexing repair; Depends on: SL-0; Blocks: SL-2, SL-3, SL-4; Parallel-safe: no
- SL-2 - Durable trace persistence and operator boundary alignment; Depends on: SL-0, SL-1; Blocks: SL-3, SL-4; Parallel-safe: no
- SL-3 - Live rerun evidence reducer and contract refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SL-4; Parallel-safe: no
- SL-4 - Downstream roadmap steering reducer; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: SEMDOCCONTRACTTAIL acceptance; Parallel-safe: no

Lane DAG:

```text
SEMCODEXLOOPTAIL
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SL-4 -> SEMDOCCONTRACTTAIL acceptance
```

## Lanes

### SL-0 - Exact Later Docs Contract-Test Fixture Freeze

- **Scope**: Freeze the exact
  `tests/docs/test_semincr_contract.py ->
  tests/docs/test_gabase_ga_readiness_contract.py` lexical seam in
  deterministic dispatcher coverage before runtime changes so this phase
  proves a narrow repair instead of hand-waving around all `tests/docs`
  Python files.
- **Owned files**: `tests/test_dispatcher.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMDOCCONTRACTTAIL-1,
  IF-0-SEMDOCCONTRACTTAIL-2,
  and IF-0-SEMDOCCONTRACTTAIL-3 at the dispatcher or plugin boundary
- **Interfaces consumed**: existing
  `Dispatcher.index_directory(...)`,
  `Dispatcher._build_exact_bounded_python_shard(...)`,
  normal Python routing through `Plugin.indexFile(...)`,
  and the SEMCODEXLOOPTAIL evidence for the exact later docs contract-test
  pair
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` with repo-shaped fixtures that
    index exact copies or trimmed representatives of
    `tests/docs/test_semincr_contract.py` and
    `tests/docs/test_gabase_ga_readiness_contract.py`, prove the lexical
    walker records the exact pair in order, and fail if the repair silently
    turns either file into an untracked blind spot.
  - test: In the same dispatcher coverage, assert that the SEMINCR docs test
    remains symbol or content discoverable for
    `test_semincr_docs_freeze_incremental_mutation_contract` and
    `test_semincr_docs_stay_out_of_query_routing_and_dogfood_claims`, and
    that the GABASE checklist test remains symbol or content discoverable for
    `test_checklist_exists_with_required_sections_and_baseline` and
    `test_public_docs_remain_pre_ga_and_route_to_canonical_artifacts`.
  - test: Add a negative guard that unrelated Python files outside the exact
    pair, especially the earlier docs-governance pair, the later docs-test
    pair, and the cleared mock-plugin fixtures, still use their own existing
    bounded or normal handling. The repair must not quietly become a broader
    `tests/docs/**/*.py` fast path.
  - impl: Keep fixtures deterministic with repo-local Python strings and
    monkeypatched bounded-path instrumentation rather than long-running live
    waits inside unit tests.
  - impl: Keep this lane on contract freeze only. Do not mutate durable
    trace, CLI wording, evidence docs, or roadmap steering here.
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "semincr or gabase or docs_contract or readiness or lexical or bounded"`

### SL-1 - Exact Docs Contract-Test Bounded Indexing Repair

- **Scope**: Implement the smallest dispatcher and Python-plugin repair
  needed so the live lexical walker no longer burns its watchdog budget on
  the exact
  `tests/docs/test_semincr_contract.py ->
  tests/docs/test_gabase_ga_readiness_contract.py` pair.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `mcp_server/plugins/python_plugin/plugin.py`
- **Interfaces provided**: IF-0-SEMDOCCONTRACTTAIL-2 exact boundary
  contract; IF-0-SEMDOCCONTRACTTAIL-3 lexical discoverability contract
- **Interfaces consumed**: SL-0 later docs contract-test fixtures; existing
  exact bounded Python behavior in
  `Dispatcher._build_exact_bounded_python_shard(...)`; and the current
  Python bounded chunk rules in `Plugin._BOUNDED_CHUNK_PATHS`
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 dispatcher slice first and confirm which side of the
    pair still consumes watchdog budget in the current force-full path: the
    smaller SEMINCR docs contract test, the larger GABASE readiness test, or
    the handoff between them.
  - impl: Apply the narrowest repair that clears the exact pair. Prefer
    exact-path bounded handling over any broad docs-test shortcut, and keep
    the repair local to the dispatcher or the relevant Python plugin path.
  - impl: Preserve content discoverability for
    `tests/docs/test_semincr_contract.py`, including the incremental mutation
    contract phrases and the explicit guard that the section does not claim
    dogfood rebuild evidence.
  - impl: Preserve top-level symbol or content discoverability for
    `tests/docs/test_gabase_ga_readiness_contract.py`, including
    `test_checklist_distinguishes_input_and_refresh_evidence`,
    `test_support_matrix_and_runbooks_share_tier_labels_and_topology_language`,
    and `test_runbooks_point_future_ga_work_to_checklist_and_refresh_artifacts`.
  - impl: Do not widen `_EXACT_BOUNDED_PYTHON_PATHS` or
    `Plugin._BOUNDED_CHUNK_PATHS` beyond what is needed for this exact pair,
    and do not introduce a repo-wide docs-test timeout or global plaintext
    bypass that masks later blockers.
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "semincr or gabase or docs_contract or readiness or lexical or bounded"`

### SL-2 - Durable Trace Persistence And Operator Boundary Alignment

- **Scope**: Carry the exact later docs contract-test repair into the durable
  force-full trace and operator status surfaces so runtime reporting
  truthfully distinguishes the cleared pair from any later blocker.
- **Owned files**: `mcp_server/storage/git_index_manager.py`, `mcp_server/cli/repository_commands.py`, `tests/test_git_index_manager.py`, `tests/test_repository_commands.py`
- **Interfaces provided**: IF-0-SEMDOCCONTRACTTAIL-1 later docs
  contract-test tail advance contract; IF-0-SEMDOCCONTRACTTAIL-4 durable
  trace and operator contract
- **Interfaces consumed**: SL-0 fixture expectations; SL-1 repaired exact
  docs contract-test bounded indexing behavior; existing
  `force_full_exit_trace.json` persistence in `GitAwareIndexManager`; and
  current operator boundary helpers in `repository_commands.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_git_index_manager.py` so durable trace fixtures
    preserve the exact
    `tests/docs/test_semincr_contract.py ->
    tests/docs/test_gabase_ga_readiness_contract.py` blocker when it is
    active and prove the rerun advances to a newer blocker without regressing
    to the cleared SEMCODEXLOOPTAIL legacy `.codex/phase-loop` family.
  - test: Extend `tests/test_repository_commands.py` so `repository status`
    advertises the repaired exact bounded lexical surface for the later docs
    contract-test pair and still prints the correct later
    `last_progress_path` and `in_flight_path` when the live blocker moves
    forward.
  - impl: Add the minimal `repository status` helper or wording needed to
    name the exact docs contract-test pair once the repair is in place,
    matching the style already used for the earlier docs, script, JSON, and
    legacy-tail boundaries.
  - impl: Preserve truthful terminalization behavior when the live command
    times out or fails later. This lane must not relabel a later blocker as
    if the repaired docs contract-test seam were still active once the rerun
    has moved on.
  - impl: Keep existing boundary wording for the legacy `.codex/phase-loop`
    family, the earlier docs pairs, the mock-plugin fixtures, and the script
    recoveries intact unless the rerun directly proves one of those surfaces
    has regressed.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "semincr or gabase or docs_contract or readiness or boundary or interrupted or lexical"`

### SL-3 - Live Rerun Evidence Reducer And Contract Refresh

- **Scope**: Refresh the real dogfood evidence after the docs contract-test
  repair so the active blocker report matches the repaired runtime rather
  than stale SEMCODEXLOOPTAIL assumptions.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: the evidence portion of
  IF-0-SEMDOCCONTRACTTAIL-5
- **Interfaces consumed**: SL-2 durable trace and repository-status output;
  live rerun command output; existing SEMCODEXLOOPTAIL evidence block; and
  the current evidence-contract assertions in
  `tests/docs/test_semdogfood_evidence_contract.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/docs/test_semdogfood_evidence_contract.py` only as
    needed so the evidence artifact must retain the SEMCODEXLOOPTAIL rerun
    outcome, the active SEMDOCCONTRACTTAIL phase name, the exact current
    docs contract-test verdict, and any newly exposed downstream steering
    after execution.
  - impl: Run a fresh repo-local force-full rerun after SL-1 and SL-2 land,
    then capture the rerun command, observed commit, timeout or completion
    timestamp, durable trace snapshot, `repository status` output, and SQLite
    counts in `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`.
  - impl: If the repaired rerun still times out, record the exact later
    blocker pair or family that replaced the current docs contract-test pair
    instead of leaving the old `test_semincr_contract.py ->
    test_gabase_ga_readiness_contract.py` pair as the active narrative.
  - impl: Keep this lane on evidence reduction. Do not back-edit older phase
    narratives except where the new rerun explicitly supersedes the active
    blocker statement.
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`

### SL-4 - Downstream Roadmap Steering Reducer

- **Scope**: Keep the roadmap and next phase-loop step truthful if the
  repaired live rerun proves a blocker beyond the current roadmap tail.
- **Owned files**: `specs/phase-plans-v7.md`
- **Interfaces provided**: the downstream-steering portion of
  IF-0-SEMDOCCONTRACTTAIL-5
- **Interfaces consumed**: SL-3 refreshed evidence verdict; current roadmap
  DAG and phase ordering for `specs/phase-plans-v7.md`; and canonical
  `.phase-loop/` expectations that the next unplanned phase reflects the
  latest durable blocker rather than stale SEMCODEXLOOPTAIL assumptions
- **Parallel-safe**: no
- **Tasks**:
  - test: Re-read the post-SL-3 evidence and confirm whether the repaired
    rerun actually exposes a newer blocker beyond the current roadmap tail
    before mutating roadmap steering.
  - impl: If the active blocker remains inside the current
    SEMDOCCONTRACTTAIL docs contract-test family or the rerun completes the
    lexical closeout, leave the roadmap unchanged.
  - impl: If the active blocker advances beyond the current roadmap tail and
    no downstream phase already covers it, append the nearest truthful
    downstream recovery phase to `specs/phase-plans-v7.md` with the same
    evidence-first structure used by the current SEM* lexical-recovery chain.
  - impl: Keep any roadmap mutation limited to the newly exposed blocker. Do
    not rewrite earlier phases or backfill unrelated sequencing while
    closing this seam.
  - verify: `git diff -- specs/phase-plans-v7.md`

## Verification

- Lane checks:
  - `uv run pytest tests/test_dispatcher.py -q --no-cov -k "semincr or gabase or docs_contract or readiness or lexical or bounded"`
  - `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "semincr or gabase or docs_contract or readiness or boundary or interrupted or lexical"`
  - `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
- Whole-phase checks:
  - `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_repository_commands.py tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "semincr or gabase or docs_contract or readiness or lexical or bounded or boundary or interrupted"`
  - `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  - `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - `sed -n '1,240p' .mcp-index/force_full_exit_trace.json`
  - `sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'`
  - `git diff --check`
  - `git diff --cached --check`

## Acceptance Criteria

- [ ] A refreshed repo-local force-full rerun on the post-SEMCODEXLOOPTAIL
      head either advances durably beyond the later
      `tests/docs/test_semincr_contract.py ->
      tests/docs/test_gabase_ga_readiness_contract.py` pair or emits a
      truthful newer blocker before the 120-second watchdog expires.
- [ ] The repair stays narrowly scoped to the exact docs contract-test pair
      and the immediate dispatcher or plugin or trace or status or evidence
      plumbing needed to prove it.
- [ ] The repaired docs contract-test surfaces remain lexically discoverable
      with durable file-level storage plus bounded content discoverability for
      the key SEMINCR and GABASE contract assertions named above.
- [ ] `uv run mcp-index repository status` and
      `force_full_exit_trace.json` stay aligned with the repaired docs
      contract-test outcome and do not regress to stale SEMCODEXLOOPTAIL-only
      wording.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMCODEXLOOPTAIL rerun outcome and the final live verdict for the later
      docs contract-test pair.
- [ ] If execution reveals a newer blocker beyond the current roadmap tail,
      `specs/phase-plans-v7.md` is updated before closeout so the next
      phase-loop step is truthful.

automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMDOCCONTRACTTAIL.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMDOCCONTRACTTAIL.md
  artifact_state: staged
