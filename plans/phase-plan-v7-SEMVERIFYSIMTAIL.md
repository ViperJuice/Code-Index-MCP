---
phase_loop_plan_version: 1
phase: SEMVERIFYSIMTAIL
roadmap: specs/phase-plans-v7.md
roadmap_sha256: fb8bb7749785ba5eade64db2cb9251948d36c5f3dd222e50ed3fe1aef9466be4
---
# SEMVERIFYSIMTAIL: Verify/Simulator Tail Recovery

## Context

SEMVERIFYSIMTAIL is the phase-55 follow-up for the v7 semantic hardening
roadmap. Canonical `.phase-loop/` state is authoritative for this run:
`.phase-loop/state.json` and `.phase-loop/tui-handoff.md` both mark
`SEMVERIFYSIMTAIL` as the current `unplanned` phase after
`SEMPREUPGRADETAIL` closed out on `HEAD` `e266a80db211` with verification
`passed`, a clean worktree, and `main...origin/main [ahead 105]`. Legacy
`.codex/phase-loop/` artifacts are compatibility-only and are not
authoritative here.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is tracked and clean in this worktree, and
  `sha256sum specs/phase-plans-v7.md` matches the required
  `fb8bb7749785ba5eade64db2cb9251948d36c5f3dd222e50ed3fe1aef9466be4`.
- The target artifact `plans/phase-plan-v7-SEMVERIFYSIMTAIL.md` did not
  exist before this planning run.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is the active evidence anchor.
  Its SEMPREUPGRADETAIL live-rerun block captures the current downstream
  lexical failure precisely: the refreshed repo-local command
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  started on observed commit `c240c23e`, and at `2026-04-29T17:07:44Z`
  `force_full_exit_trace.json` showed
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/scripts/verify_embeddings.py`
  with
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/scripts/claude_code_behavior_simulator.py`;
  at `2026-04-29T17:07:52Z`, `repository status` terminalized that running
  snapshot to `Trace status: interrupted` with the same exact pair.
- The SEMPREUPGRADETAIL target seam is no longer the active blocker:
  `scripts/preflight_upgrade.sh ->
  scripts/test_mcp_protocol_direct.py`. The authoritative current-head
  blocker is now the later Python-script seam
  `scripts/verify_embeddings.py ->
  scripts/claude_code_behavior_simulator.py`, so older downstream
  assumptions should be treated as stale after the roadmap amendment that
  introduced SEMVERIFYSIMTAIL.
- The two exact script files have materially different shapes.
  `scripts/verify_embeddings.py` is `136` lines / `5657` bytes and is
  centered on a top-level `verify_embeddings()` function that probes Qdrant
  collections, removes a stale `.lock` file, and prints workspace-specific
  diagnostics. `scripts/claude_code_behavior_simulator.py` is `414` lines /
  `15725` bytes and is centered on the `ClaudeCodeSimulator` class plus a
  series of simulation methods that walk the workspace, read Python files,
  estimate token counts, and query SQLite-backed MCP index state.
- The current exact bounded-path machinery does not yet name this Python
  pair. `mcp_server/dispatcher/dispatcher_enhanced.py` already carries
  `_EXACT_BOUNDED_PYTHON_PATHS` for earlier rebound files such as
  `scripts/validate_mcp_comprehensive.py`,
  `scripts/migrate_large_index_to_multi_repo.py`,
  `scripts/check_index_languages.py`,
  `scripts/test_mcp_protocol_direct.py`,
  `mcp_server/visualization/quick_charts.py`, and the docs governance
  tests, but it does not include either `scripts/verify_embeddings.py` or
  `scripts/claude_code_behavior_simulator.py`.
- `mcp_server/plugins/python_plugin/plugin.py` currently bounds chunking for
  `scripts/create_multi_repo_visual_report.py`,
  `scripts/quick_mcp_vs_native_validation.py`,
  `tests/test_artifact_publish_race.py`, and
  `mcp_server/visualization/quick_charts.py`, but it does not include the
  verify/simulator pair. Both current blocker files therefore still fall
  through the normal Python plugin path during lexical walking.
- `mcp_server/cli/repository_commands.py` already advertises exact lexical
  boundary messages for earlier bounded Python, shell/Python, Markdown, and
  JSON seams, including
  `scripts/preflight_upgrade.sh -> scripts/test_mcp_protocol_direct.py`,
  but it has no dedicated helper yet for
  `scripts/verify_embeddings.py ->
  scripts/claude_code_behavior_simulator.py`.
- Existing tests already freeze adjacent boundary behavior but not this
  exact later Python-script pair. `tests/test_dispatcher.py` covers earlier
  exact bounded Python, shell/Python, JSON, and Markdown seams;
  `tests/test_git_index_manager.py` and `tests/test_repository_commands.py`
  preserve durable trace and operator wording for those earlier script
  boundaries; and `tests/docs/test_semdogfood_evidence_contract.py` already
  expects the dogfood evidence artifact to retain the current verify/sim
  pair and the roadmap steering to downstream phase `SEMVERIFYSIMTAIL`.

Practical planning boundary:

- SEMVERIFYSIMTAIL may tighten exact Python-script tail handling,
  dispatcher lexical progress accounting, durable trace persistence,
  operator status wording, and the semantic dogfood evidence artifact needed
  to prove a live rerun either advances beyond
  `scripts/verify_embeddings.py ->
  scripts/claude_code_behavior_simulator.py` or surfaces a truthful newer
  blocker.
- SEMVERIFYSIMTAIL must stay narrow and evidence-driven. It must not reopen
  the repaired mixed shell/Python recovery, introduce a broad
  `scripts/*.py` exemption, retune the repo-wide lexical watchdog, or
  reopen older ai-docs, Markdown, benchmark, visualization, devcontainer,
  archive-tail, docs-governance, or script-language seams unless the
  refreshed rerun directly re-anchors there again.

## Interface Freeze Gates

- [ ] IF-0-SEMVERIFYSIMTAIL-1 - Later Python-script tail advance contract:
      a refreshed repo-local force-full rerun on the post-SEMPREUPGRADETAIL
      head no longer terminalizes with the durable lexical trace centered on
      `scripts/verify_embeddings.py ->
      scripts/claude_code_behavior_simulator.py`; it either advances
      durably beyond that pair or emits a truthful newer blocker before the
      120-second watchdog expires.
- [ ] IF-0-SEMVERIFYSIMTAIL-2 - Exact boundary contract:
      any repair introduced by this phase remains limited to the exact
      verify/simulator Python pair plus the immediate dispatcher/plugin
      plumbing needed to clear it. The phase must not introduce a new
      blanket `scripts/*.py` fast path, and it must not reopen the prior
      `scripts/preflight_upgrade.sh ->
      scripts/test_mcp_protocol_direct.py` seam without direct evidence.
- [ ] IF-0-SEMVERIFYSIMTAIL-3 - Lexical discoverability contract:
      both exact scripts remain lexically discoverable after the repair,
      including durable file-level storage plus bounded symbol or content
      discoverability for `verify_embeddings()` and the
      `ClaudeCodeSimulator` class or its top-level scenario surfaces,
      instead of turning either file into an indexing blind spot.
- [ ] IF-0-SEMVERIFYSIMTAIL-4 - Durable trace and operator contract:
      `force_full_exit_trace.json` and `uv run mcp-index repository status`
      stay aligned with the repaired outcome for the exact later
      Python-script pair and do not regress to stale SEMPREUPGRADETAIL-only
      wording once the live rerun advances past it.
- [ ] IF-0-SEMVERIFYSIMTAIL-5 - Evidence and downstream steering contract:
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMPREUPGRADETAIL rerun outcome, the SEMVERIFYSIMTAIL rerun command
      and timestamps, the refreshed trace/status output, and the final
      authoritative verdict for the later Python-script pair; if execution
      reveals a blocker beyond the current roadmap tail, `specs/phase-plans-v7.md`
      is amended before closeout so the next phase-loop step is truthful.

## Lane Index & Dependencies

- SL-0 - Exact later Python-script fixture freeze; Depends on: SEMPREUPGRADETAIL; Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 - Exact verify/simulator bounded indexing repair; Depends on: SL-0; Blocks: SL-2, SL-3, SL-4; Parallel-safe: no
- SL-2 - Durable trace persistence and operator boundary alignment; Depends on: SL-0, SL-1; Blocks: SL-3, SL-4; Parallel-safe: no
- SL-3 - Live rerun evidence reducer and contract refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SL-4; Parallel-safe: no
- SL-4 - Downstream roadmap steering reducer; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: SEMVERIFYSIMTAIL acceptance; Parallel-safe: no

Lane DAG:

```text
SEMPREUPGRADETAIL
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SL-4 -> SEMVERIFYSIMTAIL acceptance
```

## Lanes

### SL-0 - Exact Later Python-Script Fixture Freeze

- **Scope**: Freeze the exact
  `scripts/verify_embeddings.py ->
  scripts/claude_code_behavior_simulator.py` lexical seam in deterministic
  dispatcher coverage before runtime changes so this phase proves a narrow
  repair instead of hand-waving around all Python scripts.
- **Owned files**: `tests/test_dispatcher.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMVERIFYSIMTAIL-1,
  IF-0-SEMVERIFYSIMTAIL-2,
  and IF-0-SEMVERIFYSIMTAIL-3 at the dispatcher/plugin boundary
- **Interfaces consumed**: existing
  `Dispatcher.index_directory(...)`,
  `Dispatcher._build_exact_bounded_python_shard(...)`,
  normal Python routing through `Plugin.indexFile(...)`,
  and the SEMPREUPGRADETAIL evidence for the exact later Python-script pair
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` with a repo-shaped fixture that
    indexes exact copies or trimmed representatives of
    `scripts/verify_embeddings.py` and
    `scripts/claude_code_behavior_simulator.py`, proves the lexical walker
    records the exact pair in order, and fails if the repair silently turns
    either file into an untracked blind spot.
  - test: In the same dispatcher coverage, assert that
    `verify_embeddings.py` remains content-discoverable and that the
    simulator file remains symbol or content discoverable for
    `ClaudeCodeSimulator` plus at least one scenario method after the
    repair.
  - test: Add a negative guard that unrelated Python scripts outside the
    exact pair still use the normal bounded or full Python handling. The
    watchdog repair must not quietly become a broader `scripts/*.py` fast
    path.
  - impl: Keep fixtures deterministic with repo-local Python strings and
    monkeypatched bounded-path instrumentation rather than long-running live
    waits inside unit tests.
  - impl: Keep this lane on contract freeze only. Do not mutate durable
    trace, CLI wording, evidence docs, or roadmap steering here.
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "verify_embeddings or claude_code_behavior_simulator or lexical or bounded or simulator or script"`

### SL-1 - Exact Verify/Simulator Bounded Indexing Repair

- **Scope**: Implement the smallest dispatcher and Python-plugin repair
  needed so the live lexical walker no longer burns its watchdog budget on
  the exact `verify_embeddings.py -> claude_code_behavior_simulator.py`
  script pair.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `mcp_server/plugins/python_plugin/plugin.py`
- **Interfaces provided**: IF-0-SEMVERIFYSIMTAIL-2 exact boundary contract;
  IF-0-SEMVERIFYSIMTAIL-3 lexical discoverability contract
- **Interfaces consumed**: SL-0 later Python-script fixtures; existing exact
  bounded Python behavior in
  `Dispatcher._build_exact_bounded_python_shard(...)`; and the current
  Python bounded chunk rules in `Plugin._BOUNDED_CHUNK_PATHS`
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 dispatcher slice first and confirm which side of the
    pair still consumes watchdog budget in the current force-full path:
    the smaller Qdrant verification script, the larger simulator file, or
    the handoff between them.
  - impl: Apply the narrowest repair that clears the exact pair. Prefer
    exact-path bounded handling over any broad script-family shortcut, and
    keep the repair local to the dispatcher or the relevant Python plugin
    path.
  - impl: Preserve content discoverability for
    `scripts/verify_embeddings.py`, including the `verify_embeddings()`
    entry point and its Qdrant verification flow, instead of reducing the
    file to an opaque skipped artifact.
  - impl: Preserve top-level symbol or content discoverability for
    `scripts/claude_code_behavior_simulator.py`, including the
    `ClaudeCodeSimulator` class and its retrieval-simulation surfaces.
  - impl: Do not widen `_EXACT_BOUNDED_PYTHON_PATHS` or
    `Plugin._BOUNDED_CHUNK_PATHS` beyond what is needed for this exact
    pair, and do not introduce a repo-wide Python timeout or global
    plaintext bypass that masks later blockers.
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "verify_embeddings or claude_code_behavior_simulator or lexical or bounded or simulator or script"`

### SL-2 - Durable Trace Persistence And Operator Boundary Alignment

- **Scope**: Carry the exact later Python-script repair into the durable
  force-full trace and operator status surfaces so runtime reporting
  truthfully distinguishes the cleared pair from any later blocker.
- **Owned files**: `mcp_server/storage/git_index_manager.py`, `mcp_server/cli/repository_commands.py`, `tests/test_git_index_manager.py`, `tests/test_repository_commands.py`
- **Interfaces provided**: IF-0-SEMVERIFYSIMTAIL-1 later Python-script tail
  advance contract; IF-0-SEMVERIFYSIMTAIL-4 durable trace and operator
  contract
- **Interfaces consumed**: SL-0 fixture expectations; SL-1 repaired exact
  Python bounded indexing behavior; existing `force_full_exit_trace.json`
  persistence in `GitAwareIndexManager`; and current operator boundary
  helpers in `repository_commands.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_git_index_manager.py` so durable trace fixtures
    preserve the exact
    `scripts/verify_embeddings.py ->
    scripts/claude_code_behavior_simulator.py` blocker when it is active
    and prove the rerun advances to a newer blocker without regressing to
    the cleared SEMPREUPGRADETAIL seam.
  - test: Extend `tests/test_repository_commands.py` so `repository status`
    advertises the repaired exact bounded lexical surface for the later
    Python-script pair and still prints the correct later
    `last_progress_path` and `in_flight_path` when the live blocker moves
    forward.
  - impl: Add the minimal `repository status` helper or wording needed to
    name the exact verify/simulator pair once the repair is in place,
    matching the existing style used for earlier exact bounded Python,
    shell/Python, Markdown, and JSON seams.
  - impl: Keep durable trace progression truthful. If the rerun reveals a
    newer blocker, preserve that later path pair instead of pinning the
    trace or operator output to the repaired verify/simulator pair.
  - impl: Keep the repair narrow. Do not reopen older boundary helpers for
    ai-docs, phase plans, benchmark docs, visualization, or the earlier
    script-language and preflight-upgrade pairs unless the refreshed rerun
    directly re-anchors there again.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "verify_embeddings or claude_code_behavior_simulator or lexical or interrupted or boundary or simulator or script"`

### SL-3 - Live Rerun Evidence Reducer And Contract Refresh

- **Scope**: Re-run the repo-local force-full workflow after the exact later
  Python-script repair, capture the resulting trace and operator evidence,
  and fold the outcome into the durable semantic dogfood evidence artifact.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: IF-0-SEMVERIFYSIMTAIL-1 later Python-script tail
  advance contract; IF-0-SEMVERIFYSIMTAIL-4 durable trace and operator
  contract; the evidence portion of IF-0-SEMVERIFYSIMTAIL-5
- **Interfaces consumed**: SL-0 later Python-script fixtures; SL-1 repaired
  dispatcher/plugin behavior; SL-2 durable trace and status wording; the
  current SEMPREUPGRADETAIL evidence block; and the live repo-local
  `force_full_exit_trace.json`, `repository status`, and SQLite runtime
  counts after the refreshed rerun
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/docs/test_semdogfood_evidence_contract.py` so the
    evidence artifact must retain the exact
    `scripts/verify_embeddings.py ->
    scripts/claude_code_behavior_simulator.py` pair, the
    SEMVERIFYSIMTAIL rerun command, the refreshed trace/status fields, the
    phase plan reference, and the final verdict on whether the active
    blocker moved beyond the later Python-script seam.
  - test: In the same docs contract, require the semantic dogfood evidence
    to preserve the earlier preflight-upgrade script seam while adding the
    new verify/simulator seam and any truthful downstream successor.
  - impl: Refresh `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` with the
    SEMPREUPGRADETAIL observed later Python-script blocker, the repaired
    SEMVERIFYSIMTAIL rerun command and timestamps, the resulting durable
    trace snapshot, the matching `repository status` output, and the final
    call on whether the active blocker advanced beyond the exact pair.
  - impl: Keep the evidence truthful about lexical-only progress.
    `chunk_summaries` and `semantic_points` may remain zero here; do not
    imply semantic closeout unless the rerun actually leaves lexical
    walking.
  - impl: If the refreshed rerun exposes a newer blocker, record the exact
    new blocker and stop treating older downstream assumptions as
    authoritative.
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
  - verify: `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - verify: `sed -n '1,240p' .mcp-index/force_full_exit_trace.json`
  - verify: `sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'`

### SL-4 - Downstream Roadmap Steering Reducer

- **Scope**: Keep the roadmap and next phase-loop step truthful if the
  repaired live rerun proves a newer blocker beyond the current roadmap
  tail.
- **Owned files**: `specs/phase-plans-v7.md`
- **Interfaces provided**: the downstream-steering portion of
  IF-0-SEMVERIFYSIMTAIL-5
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
  - `uv run pytest tests/test_dispatcher.py -q --no-cov -k "verify_embeddings or claude_code_behavior_simulator or lexical or bounded or simulator or script"`
  - `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "verify_embeddings or claude_code_behavior_simulator or lexical or interrupted or boundary or simulator or script"`
  - `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
- Whole-phase checks:
  - `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_repository_commands.py tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "verify_embeddings or claude_code_behavior_simulator or lexical or bounded or interrupted or boundary or simulator or script"`
  - `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  - `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - `sed -n '1,240p' .mcp-index/force_full_exit_trace.json`
  - `sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'`
  - `git diff --check`
  - `git diff --cached --check`

## Acceptance Criteria

- [ ] A refreshed repo-local force-full rerun on the post-SEMPREUPGRADETAIL
      head either advances durably beyond
      `scripts/verify_embeddings.py ->
      scripts/claude_code_behavior_simulator.py` or emits a truthful newer
      blocker before the 120-second watchdog expires.
- [ ] The repair stays narrowly scoped to the exact later Python-script
      pair and the immediate dispatcher/plugin/trace/status/evidence
      plumbing needed to prove it.
- [ ] Both exact scripts remain lexically discoverable with durable
      file-level storage plus bounded symbol or content discoverability for
      `verify_embeddings()` and `ClaudeCodeSimulator`.
- [ ] `uv run mcp-index repository status` and
      `force_full_exit_trace.json` stay aligned with the repaired later
      Python-script boundary outcome and do not regress to stale
      SEMPREUPGRADETAIL wording.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMPREUPGRADETAIL rerun outcome and the final live verdict for the
      later Python-script pair.
- [ ] If execution reveals a newer blocker beyond the current roadmap tail,
      `specs/phase-plans-v7.md` is updated before closeout so the next
      phase-loop step is truthful.

automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMVERIFYSIMTAIL.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMVERIFYSIMTAIL.md
  artifact_state: staged
