---
phase_loop_plan_version: 1
phase: SEMCENTRALIZETAIL
roadmap: specs/phase-plans-v7.md
roadmap_sha256: d8ba84ae8291e902f9f888fee5b51473f4eb352c7b7e20f5806f0def3b750dcc
---
# SEMCENTRALIZETAIL: Centralization Script Tail Recovery

## Context

SEMCENTRALIZETAIL is the phase-80 follow-up for the v7 semantic hardening
roadmap. Canonical `.phase-loop/` runtime exists in this checkout, so it is
the authoritative runner state for this planning run. The current canonical
snapshots agree cleanly: `.phase-loop/state.json` and
`.phase-loop/tui-handoff.md` both identify `SEMCENTRALIZETAIL` as the current
`unplanned` phase for `specs/phase-plans-v7.md`, and the recorded roadmap hash
matches the user-required
`d8ba84ae8291e902f9f888fee5b51473f4eb352c7b7e20f5806f0def3b750dcc`.
Legacy `.codex/phase-loop/` artifacts remain compatibility-only and do not
supersede canonical `.phase-loop/` state here.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is the active roadmap, it is tracked and clean in
  this worktree, and `sha256sum specs/phase-plans-v7.md` matches the required
  `d8ba84ae8291e902f9f888fee5b51473f4eb352c7b7e20f5806f0def3b750dcc`.
- The checkout is on `main...origin/main [ahead 155]` at `HEAD`
  `7040c058c466e37df2a0bbbf0257803eb3470f75`, the worktree is clean before
  this artifact write, and `plans/phase-plan-v7-SEMCENTRALIZETAIL.md` did not
  exist before this run.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is the active evidence anchor.
  Its `SEMINTEGRATIONTAIL Live Rerun Check` block records that the refreshed
  repo-local command
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  advanced durably beyond the cleared integration seam
  `tests/integration/__init__.py ->
  tests/integration/obs/test_obs_smoke.py`
  and later terminalized on a newer script-family tail.
- That same evidence block shows the exact current blocker shape that this
  phase must clear or truthfully supersede: at `2026-04-30T01:13:32Z`,
  `.mcp-index/force_full_exit_trace.json` still showed `status: running`,
  `stage: lexical_walking`,
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/scripts/real_strategic_recommendations.py`,
  and
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/scripts/migrate_to_centralized.py`,
  while at `2026-04-30T01:13:41Z` a refreshed `repository status` terminalized
  the rerun to `Trace status: interrupted` while preserving that same later
  durable script-family pair.
- `repository status` on that same head remained semantically fail-closed
  after the rerun:
  `Readiness: stale_commit`, `Rollout status: partial_index_failure`,
  `Last sync error: disk I/O error`, and
  `Semantic readiness: summaries_missing`. SQLite runtime counts also remained
  `files = 1064`, `code_chunks = 13095`, `chunk_summaries = 0`, and
  `semantic_points = 0`, so this is still a lexical-tail and truth-surface
  slice rather than a semantic-vector recovery phase.
- Repo search found no current references to
  `scripts/real_strategic_recommendations.py` or
  `scripts/migrate_to_centralized.py` inside
  `mcp_server/dispatcher/dispatcher_enhanced.py`,
  `mcp_server/cli/repository_commands.py`,
  `tests/test_dispatcher.py`,
  `tests/test_git_index_manager.py`, or
  `tests/test_repository_commands.py`. The only current repo-local references
  to the exact pair are in `tests/docs/test_semdogfood_evidence_contract.py`
  and the dogfood evidence report, so this phase starts without a frozen
  dispatcher, durable-trace, or CLI contract for the centralization seam.
- `scripts/real_strategic_recommendations.py` is a `965` line script that
  currently exposes top-level enums `RecommendationPriority` and
  `RecommendationCategory`, dataclasses `StrategicRecommendation` and
  `ImplementationRoadmap`, the generator class
  `RealStrategicRecommendationGenerator`, and `main`. Any repair must preserve
  those checked-in surfaces or their discoverability rather than clearing the
  seam by turning the file into an indexing blind spot.
- `scripts/migrate_to_centralized.py` is a `170` line script that currently
  exposes `migrate_repository_index` and `main`, plus index-manager and
  discovery imports that still need lexical discoverability after the repair.
  Any repair must preserve those checked-in surfaces and the script's
  repository-migration intent.
- `SEMINTEGRATIONTAIL` already proved the older integration seam is no longer
  the active blocker, so this phase should treat renewed integration-tail
  blame as a regression unless the refreshed rerun re-anchors there with
  direct evidence.

Practical planning boundary:

- SEMCENTRALIZETAIL may tighten exact lexical handling for the centralization
  pair in `mcp_server/dispatcher/dispatcher_enhanced.py`, adjust
  `mcp_server/cli/repository_commands.py` or adjacent truth surfaces so the
  durable blocker is reported accurately, make the smallest script-local
  simplification only if tests and the current-head rerun prove the hotspot is
  file-local, refresh the dogfood evidence report, rerun the repo-local
  force-full sync, and extend the roadmap only if a newer blocker appears
  beyond the current tail.
- SEMCENTRALIZETAIL must stay narrow and evidence-driven. It must not reopen
  the repaired integration seam, add a broad `scripts/*.py` or repo-wide
  lexical-timeout bypass, or widen into unrelated semantic, docs-family, or
  release work unless the refreshed rerun proves the blocker has moved again.
- Because the current evidence shows both the raw running trace and the later
  terminalized status output already aligned on the same later script pair,
  execution should first prove whether the real missing contract is exact
  bounded lexical handling, closeout-handoff and status promotion, or the
  smallest file-local simplification inside one of the two scripts before
  mutating broader surfaces.

## Interface Freeze Gates

- [ ] IF-0-SEMCENTRALIZETAIL-1 - Exact centralization-tail advance contract:
      a refreshed repo-local force-full rerun on the
      post-SEMINTEGRATIONTAIL head no longer terminalizes with the durable
      blocker centered on
      `scripts/real_strategic_recommendations.py ->
      scripts/migrate_to_centralized.py`; it either advances durably beyond
      that exact pair or emits a truthful newer blocker before the 120-second
      watchdog expires.
- [ ] IF-0-SEMCENTRALIZETAIL-2 - Narrow repair contract:
      any repair introduced by this phase remains limited to the exact later
      script-family pair and the immediate dispatcher, trace, CLI, evidence,
      and roadmap-steering plumbing needed to clear or truthfully supersede
      it. The phase must not reopen the repaired integration seam without
      direct evidence.
- [ ] IF-0-SEMCENTRALIZETAIL-3 - Script discoverability contract:
      the exact pair remains lexically discoverable with durable file storage
      and stable symbol or text discoverability for
      `RecommendationPriority`,
      `RecommendationCategory`,
      `StrategicRecommendation`,
      `ImplementationRoadmap`,
      `RealStrategicRecommendationGenerator`,
      `migrate_repository_index`,
      and `main` instead of turning either script into an indexing blind spot.
- [ ] IF-0-SEMCENTRALIZETAIL-4 - Durable trace and operator contract:
      `force_full_exit_trace.json` and
      `uv run mcp-index repository status` stay aligned on the current head
      once the integration seam is already cleared, and they do not leave
      stale blame on
      `tests/integration/__init__.py ->
      tests/integration/obs/test_obs_smoke.py`
      or on earlier intermediary script pairs after durable progress has
      already moved to the exact centralization pair.
- [ ] IF-0-SEMCENTRALIZETAIL-5 - Evidence and downstream steering contract:
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMINTEGRATIONTAIL rerun outcome, the SEMCENTRALIZETAIL rerun command
      and timestamps, the refreshed durable trace and status output, and the
      final authoritative verdict for the centralization seam; if execution
      exposes a blocker beyond the current roadmap tail,
      `specs/phase-plans-v7.md` is amended before closeout so `.phase-loop/`
      points to the newest truthful next phase.

## Lane Index & Dependencies

- SL-0 - Exact centralization-tail contract freeze; Depends on: SEMINTEGRATIONTAIL; Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 - Durable trace and repository-status truth fixtures; Depends on: SL-0; Blocks: SL-2, SL-3, SL-4; Parallel-safe: no
- SL-2 - Minimal centralization-tail runtime repair or script-local simplification; Depends on: SL-0, SL-1; Blocks: SL-3, SL-4; Parallel-safe: no
- SL-3 - Live rerun evidence reducer and SEMCENTRALIZETAIL contract refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SL-4; Parallel-safe: no
- SL-4 - Downstream roadmap steering reducer; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: SEMCENTRALIZETAIL acceptance; Parallel-safe: no

Lane DAG:

```text
SEMINTEGRATIONTAIL
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SL-4 -> SEMCENTRALIZETAIL acceptance
```

## Lanes

### SL-0 - Exact Centralization-Tail Contract Freeze

- **Scope**: Freeze the exact
  `scripts/real_strategic_recommendations.py ->
  scripts/migrate_to_centralized.py`
  lexical seam in deterministic dispatcher coverage so this phase proves a
  narrow repair instead of assuming the later blocker will clear on its own.
- **Owned files**: `tests/test_dispatcher.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMCENTRALIZETAIL-1,
  IF-0-SEMCENTRALIZETAIL-2, and
  IF-0-SEMCENTRALIZETAIL-3 at the dispatcher boundary
- **Interfaces consumed**: existing
  `Dispatcher.index_directory(...)`,
  `_EXACT_BOUNDED_PYTHON_PATHS`,
  lexical file metadata storage,
  and the current checked-in content shape of
  `scripts/real_strategic_recommendations.py` and
  `scripts/migrate_to_centralized.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` with repo-shaped fixtures for
    `scripts/real_strategic_recommendations.py`,
    `scripts/migrate_to_centralized.py`, and a control script so the chosen
    narrow repair preserves durable file rows, stable symbol storage, zero
    code chunks for any exact-bounded path choice, and FTS-backed lexical
    discoverability for the exact pair.
  - test: Add explicit assertions that
    `RecommendationPriority`,
    `RecommendationCategory`,
    `StrategicRecommendation`,
    `ImplementationRoadmap`,
    `RealStrategicRecommendationGenerator`,
    `migrate_repository_index`,
    and `main` remain discoverable after the repair.
  - test: Add negative guards that the cleared integration pair
    `tests/integration/__init__.py ->
    tests/integration/obs/test_obs_smoke.py`
    does not silently reappear as the active lexical boundary once the
    centralization fixtures are introduced.
  - test: Fail if the repair would clear the seam by turning either target
    script into an ignored lexical blind spot or by widening the matcher to a
    generic `scripts/*.py` bypass.
  - impl: Keep fixtures deterministic with repo-local Python strings and
    synthetic indexing assertions rather than live long-running force-full
    waits inside unit coverage.
  - impl: Keep this lane on contract freeze only. Do not mutate dispatcher or
    CLI implementation, the checked-in scripts, evidence docs, or roadmap
    steering here.
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "real_strategic or migrate_to_centralized or centralize_tail or lexical or bounded"`

### SL-1 - Durable Trace And Repository-Status Truth Fixtures

- **Scope**: Freeze the exact centralization pair at the durable trace and
  operator surface so execution can distinguish a real later script-tail
  repair from a report that still blames cleared integration or intermediary
  script files after durable progress has already moved later.
- **Owned files**: `tests/test_git_index_manager.py`, `tests/test_repository_commands.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMCENTRALIZETAIL-1,
  IF-0-SEMCENTRALIZETAIL-2, and
  IF-0-SEMCENTRALIZETAIL-4
- **Interfaces consumed**: existing durable trace lifecycle in
  `GitAwareIndexManager`; repository-status interrupted and stale-running
  output; the repaired integration boundary wording; and the current
  later-pair evidence from `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_git_index_manager.py` so a lexical rerun that
    has already advanced beyond the cleared integration seam can surface the
    exact centralization pair truthfully, then promote a later blocker or
    closeout status when that centralization seam has been cleared.
  - test: Extend `tests/test_repository_commands.py` so
    `uv run mcp-index repository status` can be frozen against the exact
    `scripts/real_strategic_recommendations.py ->
    scripts/migrate_to_centralized.py`
    pair rather than leaving the active blocker on the earlier integration
    pair once the durable terminal status has already moved later.
  - test: Keep negative guards that the repaired integration boundary remains
    intact and that SEMINTEGRATIONTAIL-era blame does not regress into the
    active blocker once the centralization fixtures are introduced.
  - impl: Model closeout and successor promotion with synthetic trace payloads
    or monkeypatched manager behavior rather than live `sync --force-full`
    execution inside unit tests.
  - impl: Keep this lane fixture-only. Do not update production dispatcher,
    CLI, evidence, or roadmap code here.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "real_strategic or migrate_to_centralized or centralize_tail or interrupted or boundary or closeout_handoff"`

### SL-2 - Minimal Centralization-Tail Runtime Repair Or Script-Local Simplification

- **Scope**: Implement the smallest repair needed so the current-head
  force-full rerun no longer leaves
  `scripts/real_strategic_recommendations.py ->
  scripts/migrate_to_centralized.py`
  as the active lexical watchdog tail.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `mcp_server/cli/repository_commands.py`, `scripts/real_strategic_recommendations.py`, `scripts/migrate_to_centralized.py`
- **Interfaces provided**: IF-0-SEMCENTRALIZETAIL-1 exact centralization-tail
  advance contract; IF-0-SEMCENTRALIZETAIL-2 narrow repair contract;
  IF-0-SEMCENTRALIZETAIL-3 script discoverability contract; and
  IF-0-SEMCENTRALIZETAIL-4 durable trace and operator contract
- **Interfaces consumed**: SL-0 dispatcher fixtures; SL-1 durable trace and
  repository-status fixtures; existing `_EXACT_BOUNDED_PYTHON_PATHS`; current
  lexical timeout behavior in `Dispatcher.index_directory(...)`; current
  repository-status wording; and the checked-in structure of the script pair
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 and SL-1 slices first and determine whether the active
    cost is best cleared by exact lexical handling for the centralization
    pair, closeout-handoff and status-truth repair, or the smallest
    file-local simplification inside one of the two scripts.
  - impl: Choose one singular repair surface and keep it exact. Acceptable
    examples are adding the exact pair to the existing bounded lexical
    handling in `dispatcher_enhanced.py`, tightening
    `repository status` truth promotion so the exact pair is reported
    accurately, or making the smallest script-local simplification that
    allows the current watchdog to advance beyond the pair.
  - impl: Only edit `scripts/real_strategic_recommendations.py` or
    `scripts/migrate_to_centralized.py` if tests and the current-head rerun
    prove the active hotspot is file-local structure rather than missing
    dispatcher or truth-surface handling.
  - impl: Preserve the later scripts' intended operational meaning,
    `RecommendationPriority`,
    `RecommendationCategory`,
    `StrategicRecommendation`,
    `ImplementationRoadmap`,
    `RealStrategicRecommendationGenerator`,
    `migrate_repository_index`,
    and `main`, plus current output filenames and migration intent.
  - impl: Do not clear the seam with a broad `scripts/*.py` bypass, a generic
    index-ignore rule, or a repair that reopens the cleared integration seam.
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "real_strategic or migrate_to_centralized or centralize_tail or lexical or bounded"`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "real_strategic or migrate_to_centralized or centralize_tail or interrupted or boundary or closeout_handoff"`

### SL-3 - Live Rerun Evidence Reducer And SEMCENTRALIZETAIL Contract Refresh

- **Scope**: Refresh the dogfood evidence artifact so it records the
  authoritative current-head verdict for the exact centralization seam after
  the narrow runtime repair lands.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: IF-0-SEMCENTRALIZETAIL-5 evidence contract
- **Interfaces consumed**: SL-2 repair outcome; live outputs from
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`,
  `uv run mcp-index repository status`,
  `.mcp-index/force_full_exit_trace.json`, and SQLite runtime counts; plus the
  prior SEMINTEGRATIONTAIL evidence block
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/docs/test_semdogfood_evidence_contract.py` so the
    evidence contract requires the SEMINTEGRATIONTAIL rerun outcome, the exact
    centralization pair, the SEMCENTRALIZETAIL rerun commands, and the
    updated verification sequence.
  - impl: Update `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` with a dedicated
    `SEMCENTRALIZETAIL` evidence block that records the refreshed rerun
    timestamps, exact trace and status output, SQLite counts, and the final
    authoritative verdict for
    `scripts/real_strategic_recommendations.py ->
    scripts/migrate_to_centralized.py`.
  - impl: If the rerun still names the exact centralization pair, the report
    must explain why that attribution remains truthful on the current head; if
    the rerun moves later, the report must say the centralization seam is no
    longer the active blocker and preserve the exact newer blocker or
    closeout-stage attribution.
  - impl: Preserve the same-head readiness, rollout-status, last-sync-error,
    and semantic-readiness lines unless the refreshed live probes prove they
    changed.
  - impl: Keep this lane limited to the dogfood evidence artifact and its
    test. Do not mutate the roadmap here; SL-4 owns any required downstream
    phase-tail amendment.
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "SEMINTEGRATIONTAIL or SEMCENTRALIZETAIL or real_strategic or migrate_to_centralized"`
  - verify: `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - verify: `sed -n '1,240p' .mcp-index/force_full_exit_trace.json`
  - verify: `sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'`

### SL-4 - Downstream Roadmap Steering Reducer

- **Scope**: Keep the v7 roadmap truthful if the refreshed current-head rerun
  exposes a blocker beyond the present roadmap tail.
- **Owned files**: `specs/phase-plans-v7.md`
- **Interfaces provided**: the roadmap-steering portion of
  IF-0-SEMCENTRALIZETAIL-5
- **Interfaces consumed**: SL-3 live rerun verdict; current phase-80 tail
  position in `specs/phase-plans-v7.md`; and canonical `.phase-loop/`
  expectation that the roadmap names the next unplanned phase truthfully
- **Parallel-safe**: no
- **Tasks**:
  - test: Re-read the end of `specs/phase-plans-v7.md` after the SL-3 rerun
    and only amend it if the refreshed current-head evidence proves a blocker
    beyond
    `scripts/real_strategic_recommendations.py ->
    scripts/migrate_to_centralized.py`.
  - impl: If the rerun reveals a newer blocker, append one downstream phase
    with the same exact-pair specificity and evidence-first structure used
    elsewhere in the v7 lexical-recovery chain so `.phase-loop/` does not stop
    on a stale centralization tail.
  - impl: If the rerun keeps the centralization pair as the active truthful
    blocker, leave the roadmap unchanged and record that decision explicitly
    in the execution closeout and evidence.
  - impl: Keep this lane reducer-only. Do not reopen earlier integration,
    docs, script-family, or semantic phases that the rerun did not re-anchor
    on.
  - verify: `rg -n "SEMCENTRALIZETAIL|scripts/real_strategic_recommendations\\.py|scripts/migrate_to_centralized\\.py" specs/phase-plans-v7.md docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
  - verify: `git diff -- specs/phase-plans-v7.md`

## Verification

Planning-only run: do not execute these during plan creation. Run them during
`codex-execute-phase` or manual SEMCENTRALIZETAIL execution.

Lane-specific checks:

```bash
uv run pytest tests/test_dispatcher.py -q --no-cov -k "real_strategic or migrate_to_centralized or centralize_tail or lexical or bounded"
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "real_strategic or migrate_to_centralized or centralize_tail or interrupted or boundary or closeout_handoff"
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "SEMINTEGRATIONTAIL or SEMCENTRALIZETAIL or real_strategic or migrate_to_centralized"
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
  -q --no-cov -k "real_strategic or migrate_to_centralized or centralize_tail or lexical or bounded or interrupted or boundary or closeout_handoff"
timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
sed -n '1,240p' .mcp-index/force_full_exit_trace.json
git status --short -- plans/phase-plan-v7-SEMCENTRALIZETAIL.md docs/status/SEMANTIC_DOGFOOD_REBUILD.md specs/phase-plans-v7.md
git diff --check
git diff --cached --check
```

## Acceptance Criteria

- [ ] A refreshed repo-local force-full rerun on the
      post-SEMINTEGRATIONTAIL head either advances durably beyond
      `scripts/real_strategic_recommendations.py ->
      scripts/migrate_to_centralized.py`
      or emits a truthful newer blocker before the 120-second watchdog
      expires.
- [ ] The chosen repair for the later centralization seam stays narrow,
      tested, and does not reopen the repaired integration seam without direct
      evidence.
- [ ] The exact script pair remains lexically discoverable with durable file
      storage and stable symbol or text discoverability for the checked-in
      recommendation-generator and centralization-migration surfaces.
- [ ] `force_full_exit_trace.json` and
      `uv run mcp-index repository status` stay aligned with the repaired
      outcome for the exact centralization pair and do not leave stale blame
      on the cleared integration seam or on earlier intermediary script files
      after durable progress has already moved later.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMINTEGRATIONTAIL rerun outcome and the final live verdict for the
      exact centralization pair.
- [ ] If execution reveals a newer blocker beyond the current roadmap tail,
      `specs/phase-plans-v7.md` is updated before closeout so the next
      phase-loop step stays truthful.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMCENTRALIZETAIL.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMCENTRALIZETAIL.md
  artifact_state: staged
```
