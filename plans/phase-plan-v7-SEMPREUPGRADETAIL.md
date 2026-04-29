---
phase_loop_plan_version: 1
phase: SEMPREUPGRADETAIL
roadmap: specs/phase-plans-v7.md
roadmap_sha256: 3c61229803a98ef547421aad2e12a4daaa8f7a456a76624e377c7825f48c9f90
---
# SEMPREUPGRADETAIL: Preflight Upgrade Tail Recovery

## Context

SEMPREUPGRADETAIL is the phase-54 follow-up for the v7 semantic hardening
roadmap. Canonical `.phase-loop/` state is authoritative for this run:
`.phase-loop/state.json` and `.phase-loop/tui-handoff.md` both mark
`SEMPREUPGRADETAIL` as the current `unplanned` phase after
`SEMMIXEDPHASETAIL` closed out on `HEAD` `dbfd6cc` with verification
`passed`, a clean worktree, and `main...origin/main [ahead 103]`. Legacy
`.codex/phase-loop/` artifacts are compatibility-only and are not
authoritative here.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is tracked and clean in this worktree, and
  `sha256sum specs/phase-plans-v7.md` matches the required
  `3c61229803a98ef547421aad2e12a4daaa8f7a456a76624e377c7825f48c9f90`.
- The target artifact `plans/phase-plan-v7-SEMPREUPGRADETAIL.md` did not
  exist before this planning run.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is the active evidence anchor.
  Its SEMMIXEDPHASETAIL live-rerun block captures the current downstream
  lexical failure precisely: at evidence time `2026-04-29T16:49:38Z`,
  `force_full_exit_trace.json` showed
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/scripts/preflight_upgrade.sh`
  and
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/scripts/test_mcp_protocol_direct.py`;
  at `2026-04-29T16:49:50Z`, `repository status` terminalized that running
  snapshot to `Trace status: interrupted` with the same script pair.
- The SEMMIXEDPHASETAIL target seam is no longer the active blocker:
  `plans/phase-plan-v7-SEMPHASETAIL.md ->
  plans/phase-plan-v5-gagov.md`. The authoritative current-head blocker is
  now the mixed script tail
  `scripts/preflight_upgrade.sh ->
  scripts/test_mcp_protocol_direct.py`, so older downstream assumptions
  should be treated as stale after the roadmap amendment that introduced
  SEMPREUPGRADETAIL.
- The two exact script files have materially different shapes.
  `scripts/preflight_upgrade.sh` is a small `18`-line, `545`-byte shell
  wrapper that resolves the repo-local Python interpreter and then execs
  `python -m mcp_server.cli preflight_env "$1"`. By contrast,
  `scripts/test_mcp_protocol_direct.py` is a `129`-line, `4008`-byte Python
  harness that launches a subprocess MCP server with hard-coded
  `/workspaces/Code-Index-MCP` paths and performs direct JSON-RPC tool-call
  traffic. This phase therefore crosses shell and Python plugin behavior
  rather than another Markdown-only seam.
- The current exact bounded-path machinery does not yet name this script
  pair. `mcp_server/dispatcher/dispatcher_enhanced.py` only provides
  `_EXACT_BOUNDED_PYTHON_PATHS` entries for earlier rebound files such as
  `scripts/validate_mcp_comprehensive.py`,
  `scripts/migrate_large_index_to_multi_repo.py`, and
  `scripts/check_index_languages.py`. It has no exact bounded shell path
  handling, and the current exact Python list does not include
  `scripts/test_mcp_protocol_direct.py`.
- `scripts/preflight_upgrade.sh` currently falls through the normal `.sh`
  route, which is handled as plaintext by `mcp_server/plugins/simple_text_plugin.py`.
  That plugin stores the full file content and only extracts symbols for
  `.env`-style assignments, so there is no existing exact-path shell shard
  comparable to the dispatcher’s exact bounded Python or JSON helpers.
- `scripts/test_mcp_protocol_direct.py` currently falls through the normal
  Python plugin path because `mcp_server/plugins/python_plugin/plugin.py`
  only bounds chunks for
  `scripts/create_multi_repo_visual_report.py`,
  `scripts/quick_mcp_vs_native_validation.py`,
  `tests/test_artifact_publish_race.py`, and
  `mcp_server/visualization/quick_charts.py`.
- `mcp_server/cli/repository_commands.py` already advertises exact lexical
  boundary messages for the earlier Markdown seams and the prior exact
  bounded Python pair
  `scripts/migrate_large_index_to_multi_repo.py ->
  scripts/check_index_languages.py`, but it has no dedicated helper yet for
  `scripts/preflight_upgrade.sh -> scripts/test_mcp_protocol_direct.py`.
- The roadmap’s phase-54 key-file list still carries
  `mcp_server/plugins/markdown_plugin/plugin.py` forward from the prior
  phase-plan seam lineage. Current repo evidence shows the active blocker is
  no longer Markdown-specific, so this plan keeps `markdown_plugin`
  read-only unless execution re-proves that it is still on the critical
  path.
- Existing tests already freeze adjacent boundary behavior but not this
  exact mixed script pair. `tests/test_dispatcher.py` covers earlier exact
  bounded Python, JSON, and Markdown seams; `tests/test_git_index_manager.py`
  and `tests/test_repository_commands.py` preserve durable trace and
  operator wording for the earlier exact script-language pair; and
  `tests/docs/test_semdogfood_evidence_contract.py` already expects the
  dogfood evidence artifact to carry the new script pair and the roadmap
  steering to downstream phase `SEMPREUPGRADETAIL`.

Practical planning boundary:

- SEMPREUPGRADETAIL may tighten the exact shell/Python script-tail handling,
  dispatcher lexical progress accounting, durable trace persistence,
  operator status wording, and the semantic dogfood evidence artifact needed
  to prove a live rerun either advances beyond
  `scripts/preflight_upgrade.sh ->
  scripts/test_mcp_protocol_direct.py` or surfaces a truthful newer blocker.
- SEMPREUPGRADETAIL must stay narrow and evidence-driven. It must not reopen
  the repaired mixed-version phase-plan recovery, introduce a broad
  `scripts/*.py` or `*.sh` exemption, retune the repo-wide lexical watchdog,
  or reopen older ai-docs, Markdown, benchmark, visualization, devcontainer,
  archive-tail, docs-governance, or script-language seams unless the
  refreshed rerun directly re-anchors there again.

## Interface Freeze Gates

- [ ] IF-0-SEMPREUPGRADETAIL-1 - Mixed script tail advance contract:
      a refreshed repo-local force-full rerun on the post-SEMMIXEDPHASETAIL
      head no longer terminalizes with the durable lexical trace centered on
      `scripts/preflight_upgrade.sh ->
      scripts/test_mcp_protocol_direct.py`; it either advances durably
      beyond that pair or emits a truthful newer blocker before the
      120-second watchdog expires.
- [ ] IF-0-SEMPREUPGRADETAIL-2 - Exact boundary contract:
      any repair introduced by this phase remains limited to the exact shell
      and Python script pair plus the immediate dispatcher/plugin plumbing
      needed to clear it. The phase must not introduce a new blanket
      `scripts/*.py` or `*.sh` fast path, and it must not reopen the prior
      mixed-version phase-plan seam without direct evidence.
- [ ] IF-0-SEMPREUPGRADETAIL-3 - Lexical discoverability contract:
      both exact scripts remain lexically discoverable after the repair,
      including full-file storage plus bounded symbol or content
      discoverability for the shell wrapper command path and the Python MCP
      protocol harness, instead of turning either file into an indexing
      blind spot.
- [ ] IF-0-SEMPREUPGRADETAIL-4 - Durable trace and operator contract:
      `force_full_exit_trace.json` and `uv run mcp-index repository status`
      stay aligned with the repaired outcome for the exact mixed script pair
      and do not regress to stale SEMMIXEDPHASETAIL-only wording once the
      live rerun advances past it.
- [ ] IF-0-SEMPREUPGRADETAIL-5 - Evidence and downstream steering contract:
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMMIXEDPHASETAIL rerun outcome, the SEMPREUPGRADETAIL rerun command
      and timestamps, the refreshed trace/status output, and the final
      authoritative verdict for the script pair; if execution reveals a
      blocker beyond the current roadmap tail, `specs/phase-plans-v7.md` is
      amended before closeout so the next phase-loop step is truthful.

## Lane Index & Dependencies

- SL-0 - Exact mixed script fixture freeze; Depends on: SEMMIXEDPHASETAIL; Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 - Exact shell and Python bounded indexing repair; Depends on: SL-0; Blocks: SL-2, SL-3, SL-4; Parallel-safe: no
- SL-2 - Durable trace persistence and operator boundary alignment; Depends on: SL-0, SL-1; Blocks: SL-3, SL-4; Parallel-safe: no
- SL-3 - Live rerun evidence reducer and contract refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SL-4; Parallel-safe: no
- SL-4 - Downstream roadmap steering reducer; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: SEMPREUPGRADETAIL acceptance; Parallel-safe: no

Lane DAG:

```text
SEMMIXEDPHASETAIL
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SL-4 -> SEMPREUPGRADETAIL acceptance
```

## Lanes

### SL-0 - Exact Mixed Script Fixture Freeze

- **Scope**: Freeze the exact
  `scripts/preflight_upgrade.sh ->
  scripts/test_mcp_protocol_direct.py` lexical seam in deterministic
  dispatcher coverage before runtime changes so this phase proves a narrow
  repair instead of hand-waving around all scripts.
- **Owned files**: `tests/test_dispatcher.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMPREUPGRADETAIL-1,
  IF-0-SEMPREUPGRADETAIL-2,
  and IF-0-SEMPREUPGRADETAIL-3 at the dispatcher/plugin boundary
- **Interfaces consumed**: existing
  `Dispatcher.index_directory(...)`,
  `Dispatcher._build_exact_bounded_python_shard(...)`,
  normal `.sh` routing through `SimpleTextPlugin.indexFile(...)`,
  normal Python routing through `Plugin.indexFile(...)`,
  and the SEMMIXEDPHASETAIL evidence for the exact mixed script pair
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` with a repo-shaped fixture that
    indexes exact copies or trimmed representatives of
    `scripts/preflight_upgrade.sh` and
    `scripts/test_mcp_protocol_direct.py`, proves the lexical walker records
    the exact pair in order, and fails if the repair silently turns either
    file into an untracked blind spot.
  - test: In the same dispatcher coverage, assert that the shell wrapper
    remains content-discoverable and the Python harness remains
    symbol-discoverable after the repair, including preservation of the
    subprocess-launching `test_mcp_protocol` surface.
  - test: Add a negative guard that unrelated script files outside the exact
    pair still use the normal generic script handling. The watchdog repair
    must not quietly become a broader `scripts/*.py` or `*.sh` fast path.
  - impl: Keep fixtures deterministic with repo-local script strings and
    monkeypatched bounded-path instrumentation rather than long-running live
    waits inside unit tests.
  - impl: Keep this lane on contract freeze only. Do not mutate durable
    trace, CLI wording, evidence docs, or roadmap steering here.
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "preflight_upgrade or test_mcp_protocol_direct or lexical or bounded or shell or script"`

### SL-1 - Exact Shell And Python Bounded Indexing Repair

- **Scope**: Implement the smallest dispatcher and plugin-path repair needed
  so the live lexical walker no longer burns its watchdog budget on the
  exact `preflight_upgrade.sh -> test_mcp_protocol_direct.py` script pair.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `mcp_server/plugins/python_plugin/plugin.py`, `mcp_server/plugins/simple_text_plugin.py`
- **Interfaces provided**: IF-0-SEMPREUPGRADETAIL-2 exact boundary contract;
  IF-0-SEMPREUPGRADETAIL-3 lexical discoverability contract
- **Interfaces consumed**: SL-0 mixed script fixtures; existing exact
  bounded Python behavior in
  `Dispatcher._build_exact_bounded_python_shard(...)`; existing Python
  bounded chunk rules in `Plugin._BOUNDED_CHUNK_PATHS`; and the current
  plaintext shell route in `SimpleTextPlugin.indexFile(...)`
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 dispatcher slice first and confirm which side of the
    pair still consumes watchdog budget in the current force-full path:
    the shell wrapper, the Python protocol harness, or the handoff between
    them.
  - impl: Apply the narrowest repair that clears the exact pair. Prefer
    exact-path bounded handling over any broad script-family shortcut, and
    keep the repair local to the dispatcher or the relevant shell/Python
    plugin path.
  - impl: Preserve content discoverability for
    `scripts/preflight_upgrade.sh`, including the wrapper’s delegated
    `python -m mcp_server.cli preflight_env` behavior, instead of reducing
    the shell file to an opaque skipped artifact.
  - impl: Preserve top-level symbol or content discoverability for
    `scripts/test_mcp_protocol_direct.py`, including the
    `test_mcp_protocol` entry point and its subprocess/server setup flow.
  - impl: Do not widen `Plugin._BOUNDED_CHUNK_PATHS` or
    `_EXACT_BOUNDED_PYTHON_PATHS` beyond what is needed for this exact pair,
    and do not introduce a repo-wide shell timeout or global plaintext
    bypass that masks later blockers.
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "preflight_upgrade or test_mcp_protocol_direct or lexical or bounded or shell or script"`

### SL-2 - Durable Trace Persistence And Operator Boundary Alignment

- **Scope**: Carry the exact mixed script repair into the durable
  force-full trace and operator status surfaces so runtime reporting
  truthfully distinguishes the cleared pair from any later blocker.
- **Owned files**: `mcp_server/storage/git_index_manager.py`, `mcp_server/cli/repository_commands.py`, `tests/test_git_index_manager.py`, `tests/test_repository_commands.py`
- **Interfaces provided**: IF-0-SEMPREUPGRADETAIL-1 mixed script tail
  advance contract; IF-0-SEMPREUPGRADETAIL-4 durable trace and operator
  contract
- **Interfaces consumed**: SL-0 fixture expectations; SL-1 repaired shell
  and Python bounded indexing behavior; existing `force_full_exit_trace.json`
  persistence in `GitAwareIndexManager`; and current operator boundary
  helpers in `repository_commands.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_git_index_manager.py` so durable trace fixtures
    preserve the exact
    `scripts/preflight_upgrade.sh ->
    scripts/test_mcp_protocol_direct.py` blocker when it is active and prove
    the rerun advances to a newer blocker without regressing to the cleared
    SEMMIXEDPHASETAIL seam.
  - test: Extend `tests/test_repository_commands.py` so `repository status`
    advertises the repaired exact bounded lexical surface for the script
    pair and still prints the correct later `last_progress_path` and
    `in_flight_path` when the live blocker moves forward.
  - impl: Add the minimal `repository status` helper or wording needed to
    name the exact script pair once the repair is in place, matching the
    existing style used for earlier exact bounded Markdown, Python, and JSON
    seams.
  - impl: Keep durable trace progression truthful. If the rerun reveals a
    newer blocker, preserve that later path pair instead of pinning the
    trace or operator output to the repaired script pair.
  - impl: Keep the repair narrow. Do not reopen older boundary helpers for
    ai-docs, phase plans, benchmark docs, or the earlier script-language
    audit pair unless the refreshed rerun directly re-anchors there again.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "preflight_upgrade or test_mcp_protocol_direct or lexical or interrupted or boundary or script"`

### SL-3 - Live Rerun Evidence Reducer And Contract Refresh

- **Scope**: Re-run the repo-local force-full workflow after the exact mixed
  script repair, capture the resulting trace and operator evidence, and fold
  the outcome into the durable semantic dogfood evidence artifact.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: IF-0-SEMPREUPGRADETAIL-1 mixed script tail
  advance contract; IF-0-SEMPREUPGRADETAIL-4 durable trace and operator
  contract; the evidence portion of IF-0-SEMPREUPGRADETAIL-5
- **Interfaces consumed**: SL-0 mixed script fixtures; SL-1 repaired
  dispatcher/plugin behavior; SL-2 durable trace and status wording; the
  current SEMMIXEDPHASETAIL evidence block; and the live repo-local
  `force_full_exit_trace.json`, `repository status`, and SQLite runtime
  counts after the refreshed rerun
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/docs/test_semdogfood_evidence_contract.py` so the
    evidence artifact must retain the exact
    `scripts/preflight_upgrade.sh ->
    scripts/test_mcp_protocol_direct.py` pair, the SEMPREUPGRADETAIL rerun
    command, the refreshed trace/status fields, the phase plan reference,
    and the final verdict on whether the active blocker moved beyond the
    script tail.
  - test: In the same docs contract, require the semantic dogfood evidence
    to preserve the earlier mixed-version phase-plan seam and transient
    ai-docs waypoint while adding the new script seam and any truthful
    downstream successor.
  - impl: Refresh `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` with the
    SEMMIXEDPHASETAIL observed script blocker, the repaired
    SEMPREUPGRADETAIL rerun command and timestamps, the resulting durable
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
  IF-0-SEMPREUPGRADETAIL-5
- **Interfaces consumed**: SL-3 refreshed evidence verdict; current roadmap
  DAG and phase ordering for `specs/phase-plans-v7.md`; canonical
  `.phase-loop/` expectation that the next unplanned phase reflects the
  latest durable blocker rather than stale prior assumptions
- **Parallel-safe**: no
- **Tasks**:
  - test: Re-read the post-SL-3 evidence and confirm whether the repaired
    rerun actually exposes a newer blocker beyond the current roadmap tail
    before mutating roadmap steering.
  - impl: If the active blocker is still the exact mixed script pair, leave
    the roadmap unchanged.
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
  - `uv run pytest tests/test_dispatcher.py -q --no-cov -k "preflight_upgrade or test_mcp_protocol_direct or lexical or bounded or shell or script"`
  - `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "preflight_upgrade or test_mcp_protocol_direct or lexical or interrupted or boundary or script"`
  - `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
- Whole-phase checks:
  - `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_repository_commands.py tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "preflight_upgrade or test_mcp_protocol_direct or lexical or bounded or shell or script or interrupted or boundary"`
  - `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  - `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - `sed -n '1,240p' .mcp-index/force_full_exit_trace.json`
  - `sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'`
  - `git diff --check`
  - `git diff --cached --check`

## Acceptance Criteria

- [ ] A refreshed repo-local force-full rerun on the post-SEMMIXEDPHASETAIL
      head either advances durably beyond
      `scripts/preflight_upgrade.sh ->
      scripts/test_mcp_protocol_direct.py` or emits a truthful newer
      blocker before the 120-second watchdog expires.
- [ ] The repair stays narrowly scoped to the exact shell and Python script
      pair and the immediate dispatcher/plugin/trace/status/evidence
      plumbing needed to prove it.
- [ ] Both exact scripts remain lexically discoverable with durable
      file-level storage plus bounded symbol or content discoverability for
      the shell wrapper and the Python MCP protocol harness.
- [ ] `uv run mcp-index repository status` and
      `force_full_exit_trace.json` stay aligned with the repaired mixed
      script boundary outcome and do not regress to stale
      SEMMIXEDPHASETAIL wording.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMMIXEDPHASETAIL rerun outcome and the final live verdict for the
      mixed script pair.
- [ ] If execution reveals a newer blocker beyond the current roadmap tail,
      `specs/phase-plans-v7.md` is updated before closeout so the next
      phase-loop step is truthful.

automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMPREUPGRADETAIL.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMPREUPGRADETAIL.md
  artifact_state: staged
