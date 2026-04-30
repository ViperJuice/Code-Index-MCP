---
phase_loop_plan_version: 1
phase: SEMAPIDOCSTAIL
roadmap: specs/phase-plans-v7.md
roadmap_sha256: 854c268a99181b8c3d2cfc5b2ace8c5dfc9bd11946257542fa139aa10e4104a0
---
# SEMAPIDOCSTAIL: API Docs Markdown Tail Recovery

## Context

SEMAPIDOCSTAIL is the phase-92 follow-up for the v7 semantic hardening
roadmap. Canonical `.phase-loop/` state is authoritative for this run:
`.phase-loop/state.json` and `.phase-loop/tui-handoff.md` both mark
`SEMAPIDOCSTAIL` as the current `unplanned` phase after
`SEMP24PLUGINGATINGTAIL` closed out on `HEAD`
`518d7dc362bb84576df312b2adc95ad701138fb7` with verification `passed`, a
clean worktree, and `main...origin/main [ahead 179]`. Legacy
`.codex/phase-loop/` artifacts remain compatibility-only and do not
supersede canonical `.phase-loop/` runner state here.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is tracked and clean in this worktree, and
  `sha256sum specs/phase-plans-v7.md` matches the required
  `854c268a99181b8c3d2cfc5b2ace8c5dfc9bd11946257542fa139aa10e4104a0`.
- The target artifact `plans/phase-plan-v7-SEMAPIDOCSTAIL.md` did not exist
  before this planning run.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is the active evidence anchor.
  Its SEMP24PLUGINGATINGTAIL rerun block records the current downstream
  lexical blocker precisely: on observed commit `d48e0d2ed5cd89906f1b24c70298e300eabce87c`,
  the refreshed repo-local command
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  advanced beyond the repaired
  `tests/test_p24_plugin_availability.py ->
  tests/test_dispatcher_extension_gating.py` seam; at
  `2026-04-30T04:59:38Z`, `.mcp-index/force_full_exit_trace.json` showed
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/docs/architecture/P2B-known-limits.md`
  with
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/docs/api/API-REFERENCE.md`;
  at `2026-04-30T04:59:53Z`, `repository status` terminalized that running
  snapshot to `Trace status: interrupted` with the same exact pair.
- The same rerun also hit a large-payload sandbox failure while indexing
  `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
  (`ProtocolError: envelope too large: 21168277 > 16777216 bytes`), but the
  durable lexical trace continued later and did not finish on that status
  document. The active blocker for this phase is therefore still the later
  Markdown seam
  `docs/architecture/P2B-known-limits.md -> docs/api/API-REFERENCE.md`,
  not a generic status-doc bypass problem.
- The current blocker files are both Markdown docs but with very different
  shapes and sizes. `docs/architecture/P2B-known-limits.md` is `47` lines /
  `2340` bytes and freezes deferred process-global dispatcher-state limits
  through headings such as `Status`, `Deferred: Process-Global Dispatcher State`,
  `Impact`, `Why Deferred`, and `Resolution Plan`. `docs/api/API-REFERENCE.md`
  is `926` lines / `20342` bytes and freezes the beta REST surface through
  headings such as `Overview`, `Base URL`, `Authentication`, `API Endpoints`,
  and `POST /auth/login`.
- The narrow Markdown bounded-path machinery already exists but does not yet
  name this later docs seam. `mcp_server/plugins/markdown_plugin/plugin.py`
  already carries exact bounded Markdown entries for
  `docs/validation/ga-closeout-decision.md`,
  `docs/validation/mre2e-evidence.md`,
  `docs/benchmarks/mcp_vs_native_benchmark_fullrepo_fireworks_qwen_voyage_local_iter5_rerun.md`,
  `docs/benchmarks/production_benchmark.md`,
  `docs/markdown-table-of-contents.md`,
  `docs/SUPPORT_MATRIX.md`, and several mixed-version phase-plan seams, but
  it does not include either
  `docs/architecture/P2B-known-limits.md` or
  `docs/api/API-REFERENCE.md`.
- `tests/test_dispatcher.py` and
  `tests/root_tests/test_markdown_production_scenarios.py` already freeze
  bounded Markdown behavior for `README.md`, `ai_docs/*_overview.md`,
  `ai_docs/jedi.md`, and earlier exact Markdown recoveries, but they do not
  yet assert the current `P2B-known-limits.md -> API-REFERENCE.md` pair.
- `mcp_server/cli/repository_commands.py` already advertises exact Markdown
  boundary messages for validation docs, benchmark docs, support docs, mixed
  phase-plan docs, and the earlier P24 Python pair, but it has no dedicated
  helper yet for the current architecture/API-docs seam.
- `tests/test_git_index_manager.py` and `tests/test_repository_commands.py`
  already freeze durable trace and operator wording for the earlier
  Markdown pairs, while `tests/docs/test_semdogfood_evidence_contract.py`
  already requires the SEMP24PLUGINGATINGTAIL rerun narrative that hands off
  to `SEMAPIDOCSTAIL`. It does not yet freeze the SEMAPIDOCSTAIL verdict or
  the exact `P2B-known-limits.md -> API-REFERENCE.md` seam.

Practical planning boundary:

- SEMAPIDOCSTAIL may tighten exact Markdown bounded indexing, dispatcher
  lexical progress accounting, durable trace persistence, operator status
  wording, and semantic dogfood evidence needed to prove a live rerun either
  advances beyond `docs/architecture/P2B-known-limits.md ->
  docs/api/API-REFERENCE.md` or surfaces a truthful newer blocker.
- SEMAPIDOCSTAIL must stay narrow and evidence-driven. It must not reopen
  the cleared P24 Python seam, introduce a blanket `docs/**/*.md` timeout
  bypass, or widen into unrelated architecture/API documentation rewrites
  unless the refreshed rerun directly proves the active blocker requires it.

## Interface Freeze Gates

- [ ] IF-0-SEMAPIDOCSTAIL-1 - Later docs-tail advance contract: a refreshed
      repo-local force-full rerun on the post-SEMP24PLUGINGATINGTAIL head no
      longer terminalizes with the durable lexical trace centered on
      `docs/architecture/P2B-known-limits.md ->
      docs/api/API-REFERENCE.md`; it either advances durably beyond that
      pair or emits a truthful newer blocker before the 120-second watchdog
      expires.
- [ ] IF-0-SEMAPIDOCSTAIL-2 - Exact Markdown seam contract: any repair
      introduced by this phase remains limited to the exact
      `docs/architecture/P2B-known-limits.md ->
      docs/api/API-REFERENCE.md` pair plus the immediate Markdown or
      dispatcher or trace or status plumbing needed to clear it. The phase
      must not become a blanket `docs/**/*.md` fast path and must not reopen
      the cleared
      `tests/test_p24_plugin_availability.py ->
      tests/test_dispatcher_extension_gating.py` seam without direct
      evidence.
- [ ] IF-0-SEMAPIDOCSTAIL-3 - Lexical discoverability contract: both exact
      Markdown docs remain lexically discoverable after the repair,
      including durable file-level storage plus bounded symbol or content
      discoverability for `Deferred: Process-Global Dispatcher State`,
      `Impact`, `Resolution Plan`, `Overview`, `Authentication`,
      `API Endpoints`, and `POST /auth/login`, instead of turning either
      file into an indexing blind spot.
- [ ] IF-0-SEMAPIDOCSTAIL-4 - Durable trace and operator contract:
      `force_full_exit_trace.json` and `uv run mcp-index repository status`
      stay aligned with the repaired outcome for the exact architecture/API
      Markdown pair and do not regress to stale P24-only wording once the
      live rerun advances past it.
- [ ] IF-0-SEMAPIDOCSTAIL-5 - Evidence and downstream steering contract:
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMP24PLUGINGATINGTAIL rerun outcome, the SEMAPIDOCSTAIL rerun command
      and timestamps, the refreshed trace and status output, and the final
      authoritative verdict for the later Markdown docs pair; if execution
      reveals a blocker beyond the current roadmap tail,
      `specs/phase-plans-v7.md` is amended before closeout so the next
      phase-loop step is truthful.

## Lane Index & Dependencies

- SL-0 - Exact architecture/API Markdown seam contract freeze; Depends on: SEMP24PLUGINGATINGTAIL; Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 - Exact Markdown pair bounded indexing repair; Depends on: SL-0; Blocks: SL-2, SL-3, SL-4; Parallel-safe: no
- SL-2 - Durable trace persistence and operator boundary alignment; Depends on: SL-0, SL-1; Blocks: SL-3, SL-4; Parallel-safe: no
- SL-3 - Live rerun evidence reducer and Markdown-tail contract refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SL-4; Parallel-safe: no
- SL-4 - Downstream roadmap steering reducer; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: SEMAPIDOCSTAIL acceptance; Parallel-safe: no

Lane DAG:

```text
SEMP24PLUGINGATINGTAIL
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SL-4 -> SEMAPIDOCSTAIL acceptance
```

## Lanes

### SL-0 - Exact Architecture/API Markdown Seam Contract Freeze

- **Scope**: Freeze the exact
  `docs/architecture/P2B-known-limits.md ->
  docs/api/API-REFERENCE.md` lexical seam in deterministic Markdown
  coverage before runtime changes so this phase proves a narrow repair
  instead of broadening Markdown behavior across the repo.
- **Owned files**: `tests/test_dispatcher.py`, `tests/root_tests/test_markdown_production_scenarios.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMAPIDOCSTAIL-1,
  IF-0-SEMAPIDOCSTAIL-2,
  and IF-0-SEMAPIDOCSTAIL-3 at the Markdown plugin and dispatcher boundary
- **Interfaces consumed**: existing Markdown bounded-path routing through
  `MarkdownPlugin._resolve_lightweight_reason(...)`,
  `MarkdownPlugin._build_lightweight_index_shard(...)`,
  and `Dispatcher.index_directory(...)`, plus the
  SEMP24PLUGINGATINGTAIL evidence for the exact later Markdown pair
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/root_tests/test_markdown_production_scenarios.py`
    with direct `MarkdownPlugin.indexFile(...)` coverage for the exact
    `docs/architecture/P2B-known-limits.md` and
    `docs/api/API-REFERENCE.md` pair, proving both files stay on a bounded
    path while preserving heading discoverability for the concrete headings
    named in IF-0-SEMAPIDOCSTAIL-3.
  - test: Extend `tests/test_dispatcher.py` with repo-shaped fixtures that
    index exact copies or trimmed representatives of the same two Markdown
    files, assert the heavy Markdown path does not run for the exact pair,
    and fail if the repair silently turns either file into an untracked
    blind spot.
  - test: Add a negative guard that unrelated Markdown files outside the
    exact pair, especially earlier exact Markdown seams and normal docs under
    `docs/`, still use their own existing bounded or heavy handling. The
    repair must not quietly become a repo-wide `docs/**/*.md` fast path.
  - impl: Keep fixtures deterministic with repo-local Markdown strings and
    monkeypatched heavy-path instrumentation rather than long-running live
    waits inside unit tests.
  - impl: Keep this lane on contract freeze only. Do not mutate durable
    trace, CLI wording, evidence docs, or roadmap steering here.
  - verify: `uv run pytest tests/test_dispatcher.py tests/root_tests/test_markdown_production_scenarios.py -q --no-cov -k "p2b or api_reference or semapidocstail or bounded or markdown"`

### SL-1 - Exact Markdown Pair Bounded Indexing Repair

- **Scope**: Implement the smallest Markdown-path repair needed so the live
  lexical walker no longer burns its watchdog budget on the exact
  `docs/architecture/P2B-known-limits.md ->
  docs/api/API-REFERENCE.md` pair.
- **Owned files**: `mcp_server/plugins/markdown_plugin/plugin.py`, `mcp_server/dispatcher/dispatcher_enhanced.py`
- **Interfaces provided**: IF-0-SEMAPIDOCSTAIL-2 exact Markdown seam
  contract; IF-0-SEMAPIDOCSTAIL-3 lexical discoverability contract
- **Interfaces consumed**: SL-0 Markdown seam fixtures; existing exact
  bounded Markdown behavior in
  `MarkdownPlugin._resolve_lightweight_reason(...)`; and existing lexical
  progress surfaces in `Dispatcher.index_directory(...)`
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 Markdown slice first and confirm whether the active
    watchdog burn is caused by the large `docs/api/API-REFERENCE.md` heavy
    path, the handoff between `P2B-known-limits.md` and `API-REFERENCE.md`,
    or a dispatcher progress-accounting quirk after the smaller
    architecture doc.
  - impl: Apply the narrowest repair that clears the exact pair. Prefer
    exact-path bounded Markdown handling over any broad docs-directory or
    file-size-only shortcut, and keep the repair local to the Markdown plugin
    unless dispatcher progress semantics genuinely need adjustment.
  - impl: Preserve content or heading discoverability for
    `docs/architecture/P2B-known-limits.md`, including the deferred
    process-global dispatcher-state table and the `Impact` / `Resolution Plan`
    headings.
  - impl: Preserve top-level heading or content discoverability for
    `docs/api/API-REFERENCE.md`, including `Overview`, `Authentication`,
    `API Endpoints`, and `POST /auth/login`.
  - impl: Do not widen `_EXACT_BOUNDED_MARKDOWN_PATHS` beyond what is needed
    for this exact pair, and do not introduce a repo-wide Markdown timeout
    bypass or blanket payload relaxation that masks later blockers.
  - verify: `uv run pytest tests/test_dispatcher.py tests/root_tests/test_markdown_production_scenarios.py -q --no-cov -k "p2b or api_reference or semapidocstail or bounded or markdown"`

### SL-2 - Durable Trace Persistence And Operator Boundary Alignment

- **Scope**: Carry the exact architecture/API Markdown repair into the
  durable force-full trace and operator status surfaces so runtime reporting
  truthfully distinguishes the cleared pair from any later blocker.
- **Owned files**: `mcp_server/storage/git_index_manager.py`, `mcp_server/cli/repository_commands.py`, `tests/test_git_index_manager.py`, `tests/test_repository_commands.py`
- **Interfaces provided**: IF-0-SEMAPIDOCSTAIL-1 later docs-tail advance
  contract; IF-0-SEMAPIDOCSTAIL-4 durable trace and operator contract
- **Interfaces consumed**: SL-0 fixture expectations; SL-1 repaired exact
  Markdown bounded behavior; existing `force_full_exit_trace.json`
  persistence in `GitAwareIndexManager`; and current operator boundary
  helpers in `repository_commands.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_git_index_manager.py` so durable trace fixtures
    preserve the exact
    `docs/architecture/P2B-known-limits.md ->
    docs/api/API-REFERENCE.md` blocker when it is active and prove the rerun
    advances to a newer blocker without regressing to the cleared P24 Python
    seam.
  - test: Extend `tests/test_repository_commands.py` so `repository status`
    advertises the repaired exact bounded Markdown surface for the
    architecture/API-docs pair and still prints the correct later
    `last_progress_path` and `in_flight_path` when the live blocker moves
    forward.
  - impl: Add the minimal `repository status` helper or wording needed to
    name the exact Markdown pair once the repair is in place, matching the
    style already used for the validation, benchmark, support-docs, and
    mixed-version Markdown seams.
  - impl: Change `mcp_server/storage/git_index_manager.py` only if the live
    rerun proves the generic durable trace contract mishandles this exact
    pair; otherwise keep runtime logic untouched and let tests freeze the
    existing behavior.
  - impl: Preserve truthful terminalization behavior when the live command
    times out or fails later. This lane must not relabel a later blocker as
    if the repaired Markdown seam were still active once the rerun has moved
    on.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "p2b or api_reference or semapidocstail or boundary or interrupted or lexical or markdown"`

### SL-3 - Live Rerun Evidence Reducer And Markdown-Tail Contract Refresh

- **Scope**: Refresh the real dogfood evidence after the Markdown repair so
  the active blocker report matches the repaired runtime rather than stale
  SEMP24PLUGINGATINGTAIL assumptions.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: the evidence portion of
  IF-0-SEMAPIDOCSTAIL-5
- **Interfaces consumed**: SL-2 durable trace and repository-status output;
  live rerun command output; existing SEMP24PLUGINGATINGTAIL evidence block;
  and the current evidence-contract assertions in
  `tests/docs/test_semdogfood_evidence_contract.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/docs/test_semdogfood_evidence_contract.py` only as
    needed so the evidence artifact must retain the
    SEMP24PLUGINGATINGTAIL rerun outcome, the active SEMAPIDOCSTAIL phase
    name, the exact current Markdown pair verdict, and any newly exposed
    downstream steering after execution.
  - impl: Run a fresh repo-local force-full rerun after SL-1 and SL-2 land,
    then capture the rerun command, observed commit, timeout or completion
    timestamp, durable trace snapshot, `repository status` output, and SQLite
    counts in `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`.
  - impl: If the repaired rerun still times out, record the exact later
    blocker pair or family that replaced
    `docs/architecture/P2B-known-limits.md ->
    docs/api/API-REFERENCE.md` instead of leaving the old architecture/API
    seam as the active narrative.
  - impl: Keep this lane on evidence reduction. Do not back-edit older phase
    narratives except where the new rerun explicitly supersedes the active
    blocker statement.
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "SEMAPIDOCSTAIL or P2B or API_REFERENCE or p24"`

### SL-4 - Downstream Roadmap Steering Reducer

- **Scope**: Keep the roadmap and next phase-loop step truthful if the
  repaired live rerun proves a blocker beyond the current roadmap tail.
- **Owned files**: `specs/phase-plans-v7.md`
- **Interfaces provided**: the downstream-steering portion of
  IF-0-SEMAPIDOCSTAIL-5
- **Interfaces consumed**: SL-3 refreshed evidence verdict; current roadmap
  DAG and phase ordering for `specs/phase-plans-v7.md`; and canonical
  `.phase-loop/` expectations that the next unplanned phase reflects the
  latest durable blocker rather than stale SEMP24PLUGINGATINGTAIL
  assumptions
- **Parallel-safe**: no
- **Tasks**:
  - test: Re-read the post-SL-3 evidence and confirm whether the repaired
    rerun actually exposes a newer blocker beyond the current roadmap tail
    before mutating roadmap steering.
  - impl: If the active blocker remains inside the current
    SEMAPIDOCSTAIL architecture/API Markdown family or the rerun completes
    the lexical closeout, leave the roadmap unchanged.
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
  - `uv run pytest tests/test_dispatcher.py tests/root_tests/test_markdown_production_scenarios.py -q --no-cov -k "p2b or api_reference or semapidocstail or bounded or markdown"`
  - `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "p2b or api_reference or semapidocstail or boundary or interrupted or lexical or markdown"`
  - `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "SEMAPIDOCSTAIL or P2B or API_REFERENCE or p24"`
- Whole-phase checks:
  - `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/root_tests/test_markdown_production_scenarios.py tests/test_git_index_manager.py tests/test_repository_commands.py tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "p2b or api_reference or semapidocstail or bounded or boundary or interrupted or markdown"`
  - `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  - `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - `sed -n '1,240p' .mcp-index/force_full_exit_trace.json`
  - `sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'`
  - `git diff --check`
  - `git diff --cached --check`

## Acceptance Criteria

- [ ] A refreshed repo-local force-full rerun on the post-SEMP24PLUGINGATINGTAIL
      head either advances durably beyond the later
      `docs/architecture/P2B-known-limits.md ->
      docs/api/API-REFERENCE.md` pair or emits a truthful newer blocker
      before the 120-second watchdog expires.
- [ ] The repair stays narrowly scoped to the exact architecture/API Markdown
      pair and the immediate Markdown or dispatcher or trace or status or
      evidence plumbing needed to prove it.
- [ ] The repaired Markdown surfaces remain lexically discoverable with
      durable file-level storage plus bounded heading or content
      discoverability for the key P2B and API-reference headings named
      above.
- [ ] `uv run mcp-index repository status` and
      `force_full_exit_trace.json` stay aligned with the repaired
      architecture/API-docs outcome and do not regress to stale
      SEMP24PLUGINGATINGTAIL-only wording.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMP24PLUGINGATINGTAIL rerun outcome and the final live verdict for the
      later architecture/API Markdown pair.
- [ ] If execution reveals a newer blocker beyond the current roadmap tail,
      `specs/phase-plans-v7.md` is updated before closeout so the next
      phase-loop step is truthful.

automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMAPIDOCSTAIL.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMAPIDOCSTAIL.md
  artifact_state: staged
