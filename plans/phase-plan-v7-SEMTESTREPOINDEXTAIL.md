---
phase_loop_plan_version: 1
phase: SEMTESTREPOINDEXTAIL
roadmap: specs/phase-plans-v7.md
roadmap_sha256: 571ab175280579f3aa953e5d27aae858065432b5e4258392d76ac1b1d2655d77
---
# SEMTESTREPOINDEXTAIL: Test-Repo Index Script Tail Recovery

## Context

SEMTESTREPOINDEXTAIL is the phase-70 follow-up for the v7 semantic hardening
roadmap. Canonical `.phase-loop/` runtime exists in this checkout, so it is
the authoritative runner state for this planning run. Unlike the stale-snapshot
case in some earlier tail phases, the current canonical snapshots agree here:
`.phase-loop/tui-handoff.md` and `.phase-loop/state.json` both identify
`SEMTESTREPOINDEXTAIL` as the current unplanned phase for
`specs/phase-plans-v7.md`, and the recorded roadmap hash matches the user-
required `571ab175280579f3aa953e5d27aae858065432b5e4258392d76ac1b1d2655d77`.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is the active roadmap, and its live file hash
  matches the required
  `571ab175280579f3aa953e5d27aae858065432b5e4258392d76ac1b1d2655d77`.
- The checkout is on `main...origin/main [ahead 135]` at `HEAD`
  `feecfb60f406`, the worktree is clean before writing this artifact, and
  `plans/phase-plan-v7-SEMTESTREPOINDEXTAIL.md` did not exist before this run.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is the live evidence anchor. Its
  `SEMAIOVERVIEWTAIL Live Rerun Check` block records that the refreshed
  repo-local command
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  advanced beyond the prior
  `ai_docs/black_isort_overview.md -> ai_docs/sqlite_fts5_overview.md`
  seam and then terminalized later at `2026-04-29T22:08:25Z` with
  `Trace status: interrupted` on the exact script pair
  `scripts/check_test_index_schema.py -> scripts/ensure_test_repos_indexed.py`.
- The current force-full operator surface remained fail-closed after that rerun:
  `Readiness: stale_commit`, `Rollout status: partial_index_failure`,
  `Last sync error: disk I/O error`, `Semantic readiness: summaries_missing`,
  and SQLite counts still showed `chunk_summaries = 0` and
  `semantic_points = 0`.
- The two exact script files are both tracked Python utilities under
  `scripts/`. `scripts/check_test_index_schema.py` is a small SQLite schema
  probe that enumerates tables and sample rows for test-repo indexes.
  `scripts/ensure_test_repos_indexed.py` is a legacy-style centralized-index
  helper that discovers `test_repos`, hashes remotes or paths, probes
  `~/.mcp/indexes/<hash>/current.db`, prompts interactively before indexing
  missing repos, and shells out through a hard-coded
  `"python", "PathUtils.get_workspace_root()/scripts/cli/mcp_cli.py"` command
  string. Both files are plausible exact-path lexical hotspots, but they are
  still narrow enough that the first repair target should be the exact pair
  contract rather than a repo-wide Python timeout change.
- `mcp_server/dispatcher/dispatcher_enhanced.py` already carries an
  `_EXACT_BOUNDED_PYTHON_PATHS` map for earlier exact script seams such as
  `scripts/validate_mcp_comprehensive.py`,
  `scripts/check_index_languages.py`,
  `scripts/test_mcp_protocol_direct.py`,
  `scripts/verify_embeddings.py`, and
  `scripts/consolidate_real_performance_data.py`. The new script pair is not
  yet present in that exact bounded path map.
- `mcp_server/cli/repository_commands.py` already has a parallel family of
  exact lexical-boundary printer helpers for those earlier script seams, and
  `tests/test_repository_commands.py` has matching status tests that freeze the
  exact operator wording. There is not yet an equivalent repository-status
  contract for
  `scripts/check_test_index_schema.py -> scripts/ensure_test_repos_indexed.py`.
- `tests/test_dispatcher.py` and `tests/test_git_index_manager.py` already
  contain the recurring tail-phase pattern for exact file-pair progress
  snapshots, closeout handoff persistence, and proof that older blocker pairs
  disappear from later traces once execution advances. The current phase can
  reuse that pattern directly for the new script seam.
- `tests/docs/test_semdogfood_evidence_contract.py` and
  `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` already mention the exact new
  script pair and the downstream roadmap steering to `SEMTESTREPOINDEXTAIL`.
  This phase therefore needs to refresh and preserve that evidence lineage,
  not invent a new reporting surface.

Practical planning boundary:

- SEMTESTREPOINDEXTAIL may tighten exact bounded indexing for the named
  script pair, simplify one or both exact script files only if tests prove a
  file-local structure hotspot, refresh repository-status boundary wording,
  rerun the repo-local force-full sync, and update the semantic dogfood report
  with the final verdict for the exact script seam.
- SEMTESTREPOINDEXTAIL must stay narrow and evidence-driven. It must not
  reopen the already-cleared `ai_docs` overview seam, generalize to a broad
  `scripts/*.py` bypass, raise the global lexical timeout, or widen into
  unrelated semantic-stage recovery unless the refreshed rerun proves the
  blocker has moved again.
- Because adjacent exact script-tail phases already used exact bounded Python
  handling plus operator wording rather than broad timeout changes, execution
  should first prove whether the current cost is solved by extending the exact
  bounded-path contract for this pair before mutating the scripts themselves.

## Interface Freeze Gates

- [ ] IF-0-SEMTESTREPOINDEXTAIL-1 - Exact test-repo script pair advance
      contract: a refreshed repo-local force-full rerun on the
      post-SEMAIOVERVIEWTAIL head no longer terminalizes with the durable
      lexical trace centered on
      `scripts/check_test_index_schema.py ->
      scripts/ensure_test_repos_indexed.py`; it either advances durably beyond
      that exact pair or emits a truthful newer blocker before the 120-second
      watchdog expires.
- [ ] IF-0-SEMTESTREPOINDEXTAIL-2 - Exact boundary contract: any repair
      introduced by this phase remains limited to the exact named script pair
      and the immediate dispatcher, CLI status, evidence, and file-local
      plumbing needed to clear it. The phase must not reopen the repaired
      `ai_docs/black_isort_overview.md ->
      ai_docs/sqlite_fts5_overview.md` seam or broaden to a general
      `scripts/*.py` bypass without direct evidence.
- [ ] IF-0-SEMTESTREPOINDEXTAIL-3 - Lexical discoverability contract: both
      exact scripts remain lexically discoverable after the repair, including
      durable file storage plus stable lightweight or normal symbol/text
      discoverability for `check_schema`, `check_index_exists`,
      `index_repository`, and `main`, instead of turning either file into an
      indexing blind spot.
- [ ] IF-0-SEMTESTREPOINDEXTAIL-4 - Operator and evidence contract:
      `uv run mcp-index repository status` and
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` stay aligned with the repaired
      outcome for the exact script pair, preserve the already-cleared
      SEMAIOVERVIEWTAIL overview verdict, and record the final authoritative
      rerun outcome for the later test-repo index script seam.

## Lane Index & Dependencies

- SL-0 - Exact test-repo script seam contract freeze; Depends on: SEMAIOVERVIEWTAIL; Blocks: SL-1, SL-2, SL-3; Parallel-safe: no
- SL-1 - Exact bounded script-pair repair or minimal script-local simplification; Depends on: SL-0; Blocks: SL-2, SL-3; Parallel-safe: no
- SL-2 - Repository-status boundary and closeout alignment; Depends on: SL-0, SL-1; Blocks: SL-3; Parallel-safe: no
- SL-3 - Live rerun evidence reducer and SEMTESTREPOINDEXTAIL contract refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SEMTESTREPOINDEXTAIL acceptance; Parallel-safe: no

Lane DAG:

```text
SEMAIOVERVIEWTAIL
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SEMTESTREPOINDEXTAIL acceptance
```

## Lanes

### SL-0 - Exact Test-Repo Script Seam Contract Freeze

- **Scope**: Freeze the exact
  `scripts/check_test_index_schema.py ->
  scripts/ensure_test_repos_indexed.py` lexical seam in dispatcher and
  closeout-trace tests so this phase proves a narrow repair instead of
  assuming the current later-script blocker will disappear on its own.
- **Owned files**: `tests/test_dispatcher.py`, `tests/test_git_index_manager.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMTESTREPOINDEXTAIL-1,
  IF-0-SEMTESTREPOINDEXTAIL-2,
  and the trace-handshake portion of IF-0-SEMTESTREPOINDEXTAIL-4
- **Interfaces consumed**: existing
  `Dispatcher.index_directory(...)`,
  `Dispatcher._index_file_with_lexical_timeout(...)`,
  `GitAwareIndexManager.sync_repository_index(...)`,
  `force_full_exit_trace.json` persistence, the current
  `_EXACT_BOUNDED_PYTHON_PATHS` exact-script lineage, and the checked-in
  contents of `scripts/check_test_index_schema.py` and
  `scripts/ensure_test_repos_indexed.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` with repo-shaped fixtures for the
    exact script pair so lexical progress snapshots freeze the durable handoff
    from `check_test_index_schema.py` into `ensure_test_repos_indexed.py`,
    preserve closeout handoff semantics, and prove later snapshots no longer
    mention older cleared pairs such as the SEMAIOVERVIEWTAIL `ai_docs` seam.
  - test: Extend `tests/test_git_index_manager.py` so a repaired run that
    advances beyond the exact script pair writes a later durable
    `force_full_exit_trace.json` without leaking the old script-pair paths back
    into final closeout state.
  - test: Keep the contract fail-closed for true lexical stalls: if the exact
    pair is not repaired, the tests should still expect blocked lexical
    progress and no indexed-commit advance.
  - impl: Keep fixtures deterministic with small repo-local scripts and
    monkeypatched semantic closeout or `_full_index(...)` behavior rather than
    long-running real waits inside unit coverage.
  - impl: Keep this lane on contract freeze only. Do not edit dispatcher
    implementation, repository-status wording, evidence docs, or the script
    source files here.
  - verify: `uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov -k "check_test_index_schema or ensure_test_repos_indexed or lexical or interrupted or boundary or trace"`

### SL-1 - Exact Bounded Script-Pair Repair Or Minimal Script-Local Simplification

- **Scope**: Implement the smallest repair needed so the live lexical walker no
  longer burns its watchdog budget on the exact
  `scripts/check_test_index_schema.py ->
  scripts/ensure_test_repos_indexed.py` pair.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `scripts/check_test_index_schema.py`, `scripts/ensure_test_repos_indexed.py`
- **Interfaces provided**: IF-0-SEMTESTREPOINDEXTAIL-1 exact script-pair
  advance contract; IF-0-SEMTESTREPOINDEXTAIL-2 exact boundary contract; the
  dispatcher-side portion of IF-0-SEMTESTREPOINDEXTAIL-3
- **Interfaces consumed**: SL-0 exact-pair fixtures; existing
  `_EXACT_BOUNDED_PYTHON_PATHS`; current lexical timeout behavior in
  `_index_file_with_lexical_timeout(...)`; and the current structure of the two
  exact script files
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 dispatcher and trace slice first and confirm whether
    the active cost is best cleared by adding this exact pair to the existing
    bounded Python path family or by the smallest file-local simplification of
    one of the two scripts.
  - impl: Choose one singular repair surface and keep it exact. Acceptable
    examples are adding one or both named files to the existing exact bounded
    Python map in `dispatcher_enhanced.py`, or making the smallest file-local
    simplification to `scripts/check_test_index_schema.py` or
    `scripts/ensure_test_repos_indexed.py` that allows the current watchdog to
    advance beyond the pair.
  - impl: Only edit the script sources if tests prove the active hotspot is
    file-local structure rather than missing exact bounded-path handling.
    Preserve the scripts' intended operational meaning and stable symbol names.
  - impl: Preserve durable file rows plus lexical discoverability for both
    scripts; the repair must not turn either script into an ignored source
    file or silently remove its symbols from indexing.
  - impl: Keep the repair exact-script narrow. Do not add a broad
    `scripts/*.py` bypass, and do not raise the global lexical timeout just to
    move the seam.
  - verify: `rg -n "check_test_index_schema|ensure_test_repos_indexed|EXACT_BOUNDED_PYTHON_PATHS|lexical_timeout" mcp_server/dispatcher/dispatcher_enhanced.py scripts/check_test_index_schema.py scripts/ensure_test_repos_indexed.py`
  - verify: `uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov -k "check_test_index_schema or ensure_test_repos_indexed or lexical or interrupted or boundary or trace"`

### SL-2 - Repository-Status Boundary And Closeout Alignment

- **Scope**: Keep `repository status` truthful and exact once the script-pair
  repair lands, using the same operator-facing boundary vocabulary already used
  for earlier exact script-tail recoveries.
- **Owned files**: `mcp_server/cli/repository_commands.py`, `tests/test_repository_commands.py`
- **Interfaces provided**: the operator-surface portion of
  IF-0-SEMTESTREPOINDEXTAIL-4
- **Interfaces consumed**: SL-1 exact repair behavior; existing
  `force_full_exit_trace` fields (`status`, `stage`, `last_progress_path`,
  `in_flight_path`, `blocker_source`); current repository-status lexical
  boundary helper family in `repository_commands.py`; and the prior exact
  script boundary wording already frozen for neighboring script-tail phases
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_repository_commands.py` with an exact
    SEMTESTREPOINDEXTAIL status fixture so `repository status` prints the new
    boundary line for
    `scripts/check_test_index_schema.py ->
    scripts/ensure_test_repos_indexed.py` and preserves the paired
    `Last progress path` and `In-flight path` evidence.
  - test: Guard against regressions by proving the new exact status line does
    not leak older script seams such as
    `scripts/check_index_languages.py`,
    `scripts/test_mcp_protocol_direct.py`, or
    `scripts/consolidate_real_performance_data.py` into this phase's operator
    output.
  - impl: Add or extend the smallest repository-status boundary helper needed
    to describe the exact script pair consistently with the existing
    "Lexical boundary: using exact bounded Python indexing for ..." family.
  - impl: Keep this lane limited to operator wording and exact-path selection.
    Do not duplicate dispatcher logic here or mutate the dogfood evidence docs
    in this lane.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_repository_commands.py -q --no-cov -k "check_test_index_schema or ensure_test_repos_indexed or lexical or boundary or interrupted or status"`

### SL-3 - Live Rerun Evidence Reducer And SEMTESTREPOINDEXTAIL Contract Refresh

- **Scope**: Refresh the repo-local dogfood report so it records the chosen
  exact script-pair repair, the rerun outcome, and the final live verdict for
  this later seam without reopening the already-cleared overview boundary.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: the evidence portion of
  IF-0-SEMTESTREPOINDEXTAIL-4
- **Interfaces consumed**: SL-1 chosen repair; SL-2 exact repository-status
  wording; the current SEMAIOVERVIEWTAIL evidence lineage; and the live rerun
  outputs from
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`,
  `uv run mcp-index repository status`, and
  `.mcp-index/force_full_exit_trace.json`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/docs/test_semdogfood_evidence_contract.py` so the
    refreshed report cites `plans/phase-plan-v7-SEMTESTREPOINDEXTAIL.md`,
    `scripts/check_test_index_schema.py`,
    `scripts/ensure_test_repos_indexed.py`, the chosen exact repair, and the
    final authoritative verdict for the later script seam.
  - test: Require the report to preserve the already-cleared
    SEMAIOVERVIEWTAIL overview verdict and to state plainly whether the live
    rerun advanced beyond the exact script pair or exposed a newer blocker
    later in lexical, summary, or semantic closeout.
  - impl: Update `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` with the live
    SEMTESTREPOINDEXTAIL rerun command, timestamps, refreshed trace snapshot,
    repository-status terminalization, and current SQLite counts so the report
    proves the exact final state of the force-full rebuild.
  - impl: If the rerun advances to a later blocker, make the report name that
    blocker exactly and mark the script seam as cleared. If the rerun still
    ends at the exact pair, keep the report truthful and do not pretend the
    boundary is repaired.
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "SEMTESTREPOINDEXTAIL or check_test_index_schema or ensure_test_repos_indexed or script"`
  - verify: `rg -n "SEMTESTREPOINDEXTAIL|check_test_index_schema|ensure_test_repos_indexed|SEMAIOVERVIEWTAIL|force_full_exit_trace|Trace status|roadmap now adds downstream phase" docs/status/SEMANTIC_DOGFOOD_REBUILD.md tests/docs/test_semdogfood_evidence_contract.py`

## Verification

Planning-only run: do not execute these during plan creation. Run them during
`codex-execute-phase` or manual SEMTESTREPOINDEXTAIL execution.

Lane-specific checks:

```bash
uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov -k "check_test_index_schema or ensure_test_repos_indexed or lexical or interrupted or boundary or trace"
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_repository_commands.py -q --no-cov -k "check_test_index_schema or ensure_test_repos_indexed or lexical or boundary or interrupted or status"
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "SEMTESTREPOINDEXTAIL or check_test_index_schema or ensure_test_repos_indexed or script"
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
  -q --no-cov -k "check_test_index_schema or ensure_test_repos_indexed or lexical or interrupted or boundary or trace or script"
timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
git status --short -- plans/phase-plan-v7-SEMTESTREPOINDEXTAIL.md docs/status/SEMANTIC_DOGFOOD_REBUILD.md
git diff --check
git diff --cached --check
```

## Acceptance Criteria

- [ ] A refreshed repo-local force-full rerun on the post-SEMAIOVERVIEWTAIL
      head either advances durably beyond
      `scripts/check_test_index_schema.py ->
      scripts/ensure_test_repos_indexed.py`
      or emits a truthful newer blocker before the 120-second watchdog expires.
- [ ] The chosen repair for the later test-repo index script seam stays narrow,
      tested, and does not reopen the already-cleared
      `ai_docs/black_isort_overview.md ->
      ai_docs/sqlite_fts5_overview.md`
      boundary without direct evidence.
- [ ] Both exact scripts remain lexically discoverable with durable file
      storage and stable symbol/text discoverability for the currently checked-
      in script surfaces.
- [ ] `uv run mcp-index repository status` and
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` stay aligned with the repaired
      outcome for the exact script pair and preserve the already-cleared
      SEMAIOVERVIEWTAIL overview verdict.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMAIOVERVIEWTAIL rerun outcome and the final live verdict for the later
      test-repo index script pair.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v7-SEMTESTREPOINDEXTAIL.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMTESTREPOINDEXTAIL.md
  artifact_state: staged
```
