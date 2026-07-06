---
phase_loop_plan_version: 1
phase: SEMP24PLUGINGATINGTAIL
roadmap: specs/phase-plans-v7.md
roadmap_sha256: 510f9e07b256cc73e312f5333d7c9dfa5500e98ffe3d19446ccea4b284eae5b8
---
# SEMP24PLUGINGATINGTAIL: P24 Plugin Availability Gating Tail Recovery

## Context

SEMP24PLUGINGATINGTAIL is the phase-91 follow-up for the v7 semantic hardening
roadmap. Canonical `.phase-loop/` runtime exists in this checkout, so it is
the authoritative runner state for this planning run. That canonical state
still reports `SEMCODEXLOOPGARELHEARTBEATREBOUNDTAIL` as the current
`unplanned` phase, but the same canonical runtime and repo-local evidence now
show that the refreshed live rerun moved beyond that earlier seam and exposed
the later exact test-pair blocker
`tests/test_p24_plugin_availability.py ->
tests/test_dispatcher_extension_gating.py`. The user explicitly requested that
this execution-mode planning run write the downstream repo-local plan artifact
for `SEMP24PLUGINGATINGTAIL` now. Legacy `.codex/phase-loop/` artifacts remain
compatibility-only and do not supersede canonical `.phase-loop/` state here.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is the active roadmap and `sha256sum
  specs/phase-plans-v7.md` matches the user-required
  `510f9e07b256cc73e312f5333d7c9dfa5500e98ffe3d19446ccea4b284eae5b8`.
- The checkout is on `main...origin/main [ahead 177]` at `HEAD`
  `0ebd97202ca4092eaea9d6566cf0fc6de667274d`, the worktree is clean before
  this artifact write, and `plans/phase-plan-v7-SEMP24PLUGINGATINGTAIL.md`
  did not exist before this run.
- Canonical `.phase-loop/state.json` and `.phase-loop/tui-handoff.md` still
  point at `SEMCODEXLOOPGARELHEARTBEATREBOUNDTAIL`, but
  `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` and the canonical event ledger
  already record the later rerun truth that this phase is planning against:
  the rerun advanced beyond the legacy compatibility-runtime seam and
  terminalized later at the exact test-pair boundary
  `tests/test_p24_plugin_availability.py ->
  tests/test_dispatcher_extension_gating.py`.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is the active evidence anchor. Its
  `SEMCODEXLOOPGARELHEARTBEATREBOUNDTAIL Live Rerun Check` block records that
  the refreshed repo-local command
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  advanced on observed commit `c4419ef3ddc58e74e4f39cc140665d1e42baf765` and
  exited with code `135`; at `2026-04-30T04:41:27Z`,
  `.mcp-index/force_full_exit_trace.json` still showed
  `status: running`, `stage: lexical_walking`,
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/tests/test_p24_plugin_availability.py`,
  and
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/tests/test_dispatcher_extension_gating.py`;
  at `2026-04-30T04:41:42Z`, `repository status` terminalized the same rerun
  to `Trace status: interrupted` while preserving the same exact pair.
- SQLite runtime counts after that rerun remained
  `files = 1064`, `code_chunks = 13095`, `chunk_summaries = 0`, and
  `semantic_points = 0`, so the live blocker still sits in the pre-semantic
  lexical portion of the rebuild.
- The active pair is materially larger than earlier exact-bounded tail
  fixtures: `tests/test_p24_plugin_availability.py` is `92` lines / `2910`
  bytes and `tests/test_dispatcher_extension_gating.py` is `191` lines /
  `6380` bytes.
- The dispatcher already uses exact bounded Python handling for many prior tail
  files via `_EXACT_BOUNDED_PYTHON_PATHS`, but neither
  `tests/test_p24_plugin_availability.py` nor
  `tests/test_dispatcher_extension_gating.py` is currently in that map.
- The exact-bounded Python shard builder already preserves top-level function
  and class symbols without chunk creation for listed `.py` paths. That makes
  the dispatcher the most plausible first repair surface for this seam if the
  live rerun still stalls on file-local lexical work.
- The two blocked test files also expose stable top-level surfaces that must
  remain discoverable if execution chooses a dispatcher-only fix.
  `tests/test_p24_plugin_availability.py` defines `P24_FIELDS` plus the test
  functions `test_availability_has_one_stable_row_per_supported_language`,
  `test_registry_only_sandbox_languages_are_unsupported`,
  `test_missing_optional_dependency_is_machine_readable`,
  `test_availability_rows_expose_default_activation_and_basis_facts`, and
  `test_create_all_plugins_quietly_skips_expected_unavailable`.
  `tests/test_dispatcher_extension_gating.py` defines `REPO_ID`, helper
  functions `_make_db`, `_make_ctx`, `_make_dispatcher_with_plugins`, helper
  classes `FakePyPlugin` and `SpyPlugin`, and the tests
  `test_py_extension_gating_no_plugin_instantiation`,
  `test_no_bm25_row_no_plugin_called`, and
  `test_c_extension_routes_to_c_plugin`.
- Existing behavior under those tests is already meaningful and should not be
  widened accidentally. `mcp_server/plugins/plugin_factory.py` already exposes
  machine-readable plugin availability facts (`state`, `sandbox_supported`,
  `availability_basis`, `activation_mode`, `required_extras`, `remediation`,
  `error_type`), `tests/test_p24_plugin_availability.py` freezes those facts,
  and `tests/test_dispatcher_extension_gating.py` freezes the dispatcher's
  BM25-source-extension gating behavior for `.py` and `.c`.
- `mcp_server/cli/stdio_runner.py` already advertises machine-readable plugin
  availability through `list_plugins`, so any tail recovery here must preserve
  the existing P24/plugin-gating contract rather than simplify the tests by
  weakening their assertions.
- `tests/test_git_index_manager.py`, `tests/test_repository_commands.py`, and
  `tests/docs/test_semdogfood_evidence_contract.py` already carry the durable
  trace, operator-surface, and evidence patterns used in earlier v7 tail
  recoveries. This phase should reuse those patterns for the new exact pair
  rather than inventing a parallel closeout path.

Practical planning boundary:

- SEMP24PLUGINGATINGTAIL may implement one exact recovery for the later test
  pair: add exact bounded Python handling for
  `tests/test_p24_plugin_availability.py` and
  `tests/test_dispatcher_extension_gating.py`, make the smallest test-local
  simplification only if the rerun and targeted tests prove a file-local
  hotspot remains, refresh the durable trace and `repository status` wording
  if the rerun advances beyond the pair, rerun the repo-local force-full sync,
  refresh the dogfood evidence artifact, and extend the roadmap only if the
  repaired run exposes a newer blocker.
- SEMP24PLUGINGATINGTAIL must stay narrow and evidence-driven. It must not
  broaden into generic `tests/*.py` bounded indexing, a blanket plugin-test
  exemption, a weakening of the P24/plugin-availability or extension-gating
  assertions, a reopening of the already-cleared
  `.codex/phase-loop/runs/20260424T225641Z-01-garel-execute/heartbeat.json ->
  .codex/phase-loop/runs/20260425T022006Z-01-garecut-plan/launch.json` seam,
  or a broad change to canonical `.phase-loop/` authority.

## Interface Freeze Gates

- [ ] IF-0-SEMP24PLUGINGATINGTAIL-1 - Exact later test-pair recovery contract:
      a refreshed repo-local force-full rerun on the
      post-SEMCODEXLOOPGARELHEARTBEATREBOUNDTAIL head no longer terminalizes
      with the durable lexical trace centered on
      `tests/test_p24_plugin_availability.py ->
      tests/test_dispatcher_extension_gating.py`; it either advances durably
      beyond `tests/test_dispatcher_extension_gating.py` or emits a truthful
      newer blocker before the 120-second watchdog expires.
- [ ] IF-0-SEMP24PLUGINGATINGTAIL-2 - Exact bounded-repair contract:
      the chosen repair remains limited to the exact named test pair and the
      immediate dispatcher, trace, status, evidence, and roadmap plumbing
      needed to prove it. It does not broaden into generic `tests/*.py`
      bounded indexing, a repo-wide lexical timeout bypass, or a weakening of
      the P24 plugin-availability or extension-gating test contracts.
- [ ] IF-0-SEMP24PLUGINGATINGTAIL-3 - Lexical discoverability contract:
      both exact test files remain lexically discoverable after the repair,
      including durable file storage plus top-level function/class symbol
      discoverability for the helper and test surfaces already present in
      `tests/test_dispatcher_extension_gating.py`, function-symbol
      discoverability for the test surfaces in
      `tests/test_p24_plugin_availability.py`, and FTS-backed text
      discoverability for stable constants such as `P24_FIELDS` and `REPO_ID`.
- [ ] IF-0-SEMP24PLUGINGATINGTAIL-4 - Durable trace and operator truthfulness
      contract:
      `force_full_exit_trace.json`, `GitAwareIndexManager`, and
      `uv run mcp-index repository status` agree on the repaired outcome for
      the exact later test pair and do not regress to stale
      SEMCODEXLOOPGARELHEARTBEATREBOUNDTAIL-era wording once the rerun
      advances beyond it.
- [ ] IF-0-SEMP24PLUGINGATINGTAIL-5 - Evidence and downstream steering
      contract:
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMCODEXLOOPGARELHEARTBEATREBOUNDTAIL rerun outcome, the repaired
      SEMP24PLUGINGATINGTAIL rerun command and timestamps, the refreshed
      durable trace and status output, and the final authoritative verdict for
      `tests/test_p24_plugin_availability.py ->
      tests/test_dispatcher_extension_gating.py`; if execution exposes a
      blocker beyond the current roadmap tail, `specs/phase-plans-v7.md` is
      amended before closeout so `.phase-loop/` does not stop on a stale tail.

## Lane Index & Dependencies

- SL-0 - Exact P24 test-pair fixture freeze; Depends on: SEMCODEXLOOPGARELHEARTBEATREBOUNDTAIL; Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 - Exact P24 test-pair bounded Python recovery or minimal test-local simplification; Depends on: SL-0; Blocks: SL-2, SL-3, SL-4; Parallel-safe: no
- SL-2 - Durable force-full trace and repository-status alignment; Depends on: SL-0, SL-1; Blocks: SL-3, SL-4; Parallel-safe: no
- SL-3 - Live rerun evidence reducer and P24 tail contract refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SL-4; Parallel-safe: no
- SL-4 - Downstream roadmap steering reducer; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: SEMP24PLUGINGATINGTAIL acceptance; Parallel-safe: no

Lane DAG:

```text
SEMCODEXLOOPGARELHEARTBEATREBOUNDTAIL
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SL-4 -> SEMP24PLUGINGATINGTAIL acceptance
```

## Lanes

### SL-0 - Exact P24 Test-Pair Fixture Freeze

- **Scope**: Freeze the exact later
  `tests/test_p24_plugin_availability.py ->
  tests/test_dispatcher_extension_gating.py` lexical seam in deterministic
  dispatcher coverage before runtime changes so this phase proves a narrow
  P24-tail recovery instead of hand-waving around test files generally.
- **Owned files**: `tests/test_dispatcher.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMP24PLUGINGATINGTAIL-1,
  IF-0-SEMP24PLUGINGATINGTAIL-2,
  and IF-0-SEMP24PLUGINGATINGTAIL-3 at the dispatcher exact-bounded Python
  boundary
- **Interfaces consumed**: existing
  `EnhancedDispatcher.index_directory(...)`,
  `_EXACT_BOUNDED_PYTHON_PATHS`,
  `_build_exact_bounded_python_shard(...)`,
  the current checked-in content shapes of
  `tests/test_p24_plugin_availability.py` and
  `tests/test_dispatcher_extension_gating.py`,
  and the SEMCODEXLOOPGARELHEARTBEATREBOUNDTAIL evidence for the later pair
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` with repo-shaped fixtures for the
    exact two test files that prove a bounded Python recovery preserves stored
    file rows, top-level function/class symbols, and FTS-backed file content
    for the pair without generating ordinary lexical chunks.
  - test: Assert that the repaired path preserves discoverability for the
    current P24 helper and test surfaces, including
    `test_availability_has_one_stable_row_per_supported_language`,
    `test_missing_optional_dependency_is_machine_readable`,
    `_make_db`, `_make_ctx`, `FakePyPlugin`, `SpyPlugin`, and
    `test_py_extension_gating_no_plugin_instantiation`, while keeping
    constants like `P24_FIELDS` and `REPO_ID` text-discoverable.
  - test: Add negative guards so earlier exact-bounded Python, shell, JSON,
    and JSONL tail fixtures do not silently regress while the P24 pair is
    added.
  - impl: Keep fixtures deterministic with repo-local Python strings and
    synthetic lexical metadata rather than live 120-second reruns inside unit
    coverage.
  - impl: Keep this lane on contract freeze only. Do not mutate dispatcher
    implementation, the blocked test files, trace/status surfaces, evidence
    docs, or roadmap steering here.
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "p24 or plugin_availability or extension_gating or bounded or lexical or discoverability"`

### SL-1 - Exact P24 Test-Pair Bounded Python Recovery Or Minimal Test-Local Simplification

- **Scope**: Implement the smallest exact repair needed so the current-head
  force-full rerun no longer burns its watchdog budget on the later
  `tests/test_p24_plugin_availability.py ->
  tests/test_dispatcher_extension_gating.py` seam.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `tests/test_p24_plugin_availability.py`, `tests/test_dispatcher_extension_gating.py`
- **Interfaces provided**: IF-0-SEMP24PLUGINGATINGTAIL-1 exact later test-pair
  recovery contract; IF-0-SEMP24PLUGINGATINGTAIL-2 exact bounded-repair
  contract; IF-0-SEMP24PLUGINGATINGTAIL-3 lexical discoverability contract
- **Interfaces consumed**: SL-0 exact-pair fixtures; existing
  `_EXACT_BOUNDED_PYTHON_PATHS`; current AST-only exact-bounded Python symbol
  extraction in `_build_exact_bounded_python_shard(...)`; current structures
  of `tests/test_p24_plugin_availability.py` and
  `tests/test_dispatcher_extension_gating.py`; and the existing P24/plugin
  availability and extension-gating behavior those files freeze
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 dispatcher slice first and confirm whether the current
    checkout still reproduces the later P24 test-pair seam or simply leaves
    the exact-bounded recovery path unimplemented for these files.
  - impl: Prefer a dispatcher-only fix first by adding the exact two test
    paths to `_EXACT_BOUNDED_PYTHON_PATHS` if that is sufficient to preserve
    discoverability and let the current watchdog move on.
  - impl: Only edit `tests/test_p24_plugin_availability.py` or
    `tests/test_dispatcher_extension_gating.py` if targeted tests and the
    current-head rerun prove a remaining file-local hotspot after the
    dispatcher change. Any test-local simplification must preserve the current
    P24/plugin-availability and extension-gating assertions, helper shapes,
    and stable symbol/text surfaces.
  - impl: Do not weaken the plugin-availability row schema, state vocabulary,
    optional-extra remediation assertions, sandbox-unsupported expectations,
    or `.py`/`.c` source-extension gating behavior just to clear the lexical
    tail.
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "p24 or plugin_availability or extension_gating or bounded or lexical"`
  - verify: `uv run pytest tests/test_p24_plugin_availability.py tests/test_dispatcher_extension_gating.py -q --no-cov`
  - verify: `rg -n "test_p24_plugin_availability.py|test_dispatcher_extension_gating.py|_EXACT_BOUNDED_PYTHON_PATHS|P24_FIELDS|REPO_ID|PluginFactory|get_plugin_availability|run_gated_fallback" mcp_server/dispatcher/dispatcher_enhanced.py tests/test_p24_plugin_availability.py tests/test_dispatcher_extension_gating.py`

### SL-2 - Durable Force-Full Trace And Repository-Status Alignment

- **Scope**: Make the durable force-full trace and operator-visible status
  truthful when the later P24 test pair is already exact-bounded and the live
  rerun either clears it or stalls immediately after it.
- **Owned files**: `mcp_server/storage/git_index_manager.py`, `mcp_server/cli/repository_commands.py`, `tests/test_git_index_manager.py`, `tests/test_repository_commands.py`
- **Interfaces provided**: IF-0-SEMP24PLUGINGATINGTAIL-4 durable trace and
  operator truthfulness contract
- **Interfaces consumed**: SL-0 fixture vocabulary; SL-1 chosen repair or
  no-op decision; existing force-full trace persistence in
  `GitAwareIndexManager.sync_repository_index(...)`; current
  `_print_force_full_exit_trace(...)`; and existing status-output patterns for
  later bounded lexical seams
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_git_index_manager.py` so a force-full rerun that
    has already advanced through `tests/test_p24_plugin_availability.py` but
    times out on or beyond `tests/test_dispatcher_extension_gating.py`
    persists the truthful later stage and exact pair instead of regressing to
    the earlier legacy compatibility-runtime seam.
  - test: Extend `tests/test_repository_commands.py` so
    `uv run mcp-index repository status` reports the repaired later test-pair
    boundary truthfully, keeps `Trace status: interrupted` behavior correct
    for interrupted traces, and excludes stale
    `garel-execute heartbeat.json -> garecut-plan launch.json` blame once the
    rerun has advanced beyond it.
  - impl: Preserve the fail-closed readiness vocabulary and current durable
    trace field names. This lane should not rename `Trace status`,
    `Trace stage`, `Trace blocker source`, `last_progress_path`, or
    `in_flight_path`; it should only keep the later P24 pair or its truthful
    successor durable on the current head.
  - impl: Keep any new CLI boundary wording additive and exact. Do not broaden
    it into a generic explanation for all test files.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "p24 or plugin_availability or extension_gating or interrupted or boundary or lexical"`

### SL-3 - Live Rerun Evidence Reducer And P24 Tail Contract Refresh

- **Scope**: Re-run the repaired repo-local force-full sequence, reduce the
  outcome into the durable semantic dogfood evidence artifact, and record the
  authoritative verdict for whether the later P24 pair is still active or has
  already yielded to a newer blocker.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: IF-0-SEMP24PLUGINGATINGTAIL-1 exact later test-pair
  recovery contract; IF-0-SEMP24PLUGINGATINGTAIL-4 durable trace and operator
  truthfulness contract; IF-0-SEMP24PLUGINGATINGTAIL-5 evidence contract
- **Interfaces consumed**: SL-0 fixtures; SL-1 chosen repair or no-op
  decision; SL-2 trace/status wording; the current
  SEMCODEXLOOPGARELHEARTBEATREBOUNDTAIL evidence block; and the live repo-local
  `force_full_exit_trace.json`, `repository status`, SQLite counts, and rerun
  exit status from the current head
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/docs/test_semdogfood_evidence_contract.py` so the
    report must name `plans/phase-plan-v7-SEMP24PLUGINGATINGTAIL.md`, carry a
    `## SEMP24PLUGINGATINGTAIL Live Rerun Check` block, preserve the
    SEMCODEXLOOPGARELHEARTBEATREBOUNDTAIL lineage, and record the exact P24
    pair plus whichever later truth the refreshed rerun proves.
  - impl: Run the current-head force-full command once after the code lanes are
    ready, capture the resulting `force_full_exit_trace.json`,
    `repository status`, and SQLite counts, and reduce them into one
    authoritative evidence block that says whether the pair is still the
    blocker or whether the run has moved later.
  - impl: If the rerun still names the P24 pair, the report must include why
    that attribution remains truthful on the current head; if the rerun moves
    later, the report must say the P24 tail is no longer the active blocker
    and preserve the exact newer blocker or later closeout stage.
  - impl: Keep this lane limited to the dogfood evidence artifact and its test.
    Do not mutate the roadmap here; SL-4 owns any required downstream
    phase-tail amendment.
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "SEMP24PLUGINGATINGTAIL or SEMCODEXLOOPGARELHEARTBEATREBOUNDTAIL or plugin_availability or extension_gating"`
  - verify: `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - verify: `sed -n '1,240p' .mcp-index/force_full_exit_trace.json`
  - verify: `sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'`

### SL-4 - Downstream Roadmap Steering Reducer

- **Scope**: Keep the v7 roadmap truthful if the refreshed current-head rerun
  exposes a blocker beyond the present roadmap tail.
- **Owned files**: `specs/phase-plans-v7.md`
- **Interfaces provided**: the roadmap-steering portion of
  IF-0-SEMP24PLUGINGATINGTAIL-5
- **Interfaces consumed**: SL-3 live rerun verdict; current phase-91 tail
  position in `specs/phase-plans-v7.md`; and canonical `.phase-loop/`
  expectation that the roadmap names the next unplanned phase truthfully
- **Parallel-safe**: no
- **Tasks**:
  - test: Re-read the end of `specs/phase-plans-v7.md` after the SL-3 rerun
    and only amend it if the refreshed current-head evidence proves a blocker
    beyond `tests/test_p24_plugin_availability.py ->
    tests/test_dispatcher_extension_gating.py`.
  - impl: If the rerun reveals a newer blocker, append one downstream phase
    with the same exact-pair specificity used elsewhere in v7 and update any
    affected execution notes so `.phase-loop/` does not stop on a stale tail.
  - impl: If the rerun keeps the P24 pair as the active truthful blocker,
    leave the roadmap unchanged and record that decision explicitly in the
    execution closeout and evidence.
  - impl: Keep this lane reducer-only. Do not reopen earlier phase-plan,
    compatibility-runtime, or integration families that the rerun did not
    re-anchor on.
  - verify: `rg -n "SEMP24PLUGINGATINGTAIL|tests/test_p24_plugin_availability.py|tests/test_dispatcher_extension_gating.py" specs/phase-plans-v7.md docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
  - verify: `git diff -- specs/phase-plans-v7.md`

## Verification

Planning-only run: do not execute these during plan creation. Run them during
`codex-execute-phase` or manual SEMP24PLUGINGATINGTAIL execution.

Lane-specific checks:

```bash
uv run pytest tests/test_dispatcher.py -q --no-cov -k "p24 or plugin_availability or extension_gating or bounded or lexical or discoverability"
uv run pytest tests/test_p24_plugin_availability.py tests/test_dispatcher_extension_gating.py -q --no-cov
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "p24 or plugin_availability or extension_gating or interrupted or boundary or lexical"
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "SEMP24PLUGINGATINGTAIL or SEMCODEXLOOPGARELHEARTBEATREBOUNDTAIL or plugin_availability or extension_gating"
timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
sed -n '1,240p' .mcp-index/force_full_exit_trace.json
sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'
```

Whole-phase regression commands:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest \
  tests/test_dispatcher.py \
  tests/test_p24_plugin_availability.py \
  tests/test_dispatcher_extension_gating.py \
  tests/test_git_index_manager.py \
  tests/test_repository_commands.py \
  tests/docs/test_semdogfood_evidence_contract.py \
  -q --no-cov -k "p24 or plugin_availability or extension_gating or bounded or lexical or interrupted or boundary"
timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
git status --short -- plans/phase-plan-v7-SEMP24PLUGINGATINGTAIL.md docs/status/SEMANTIC_DOGFOOD_REBUILD.md specs/phase-plans-v7.md
git diff --check
git diff --cached --check
```

## Acceptance Criteria

- [ ] A refreshed repo-local force-full rerun on the
      post-SEMCODEXLOOPGARELHEARTBEATREBOUNDTAIL head either advances durably
      beyond
      `tests/test_dispatcher_extension_gating.py`
      or emits a truthful newer blocker before the 120-second watchdog
      expires.
- [ ] The chosen repair for the later P24 test-pair seam stays narrow, tested,
      and does not weaken the current plugin-availability or extension-gating
      test contracts.
- [ ] Both exact test files remain lexically discoverable with durable file
      storage, stable top-level helper/test symbol discoverability, and
      FTS-backed text discoverability for `P24_FIELDS` and `REPO_ID`.
- [ ] `force_full_exit_trace.json` and
      `uv run mcp-index repository status` stay aligned with the repaired
      outcome for the exact later P24 pair and do not regress to stale
      SEMCODEXLOOPGARELHEARTBEATREBOUNDTAIL-era blame once the rerun advances
      beyond it.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMCODEXLOOPGARELHEARTBEATREBOUNDTAIL rerun outcome and the final live
      verdict for the later P24 test-pair seam.
- [ ] If the rerun exposes a blocker beyond the current roadmap tail,
      `specs/phase-plans-v7.md` is updated before closeout so the next
      phase-loop step stays truthful.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMP24PLUGINGATINGTAIL.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMP24PLUGINGATINGTAIL.md
  artifact_state: staged
```
