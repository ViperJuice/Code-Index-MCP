---
phase_loop_plan_version: 1
phase: SEMSCRIPTLANGS
roadmap: specs/phase-plans-v7.md
roadmap_sha256: 0073678835f4ba86f2d521db831010b2667d825695a4257839d88f6331f9fbc4
---
# SEMSCRIPTLANGS: Script Language Audit Lexical Recovery

## Context

SEMSCRIPTLANGS is the phase-48 follow-up for the v7 semantic hardening
roadmap. Canonical `.phase-loop/state.json` now marks `SEMSCRIPTLANGS` as the
current `unplanned` phase after `SEMCLAUDECMDS` closed out on `HEAD`
`248dd68d06bced46adc2460c44fbcb2d38e72614` with verification `passed`, a clean
worktree, and `main...origin/main [ahead 91]`. `specs/phase-plans-v7.md` is
tracked and clean in this worktree, and its live SHA matches the roadmap hash
requested for this artifact:
`0073678835f4ba86f2d521db831010b2667d825695a4257839d88f6331f9fbc4`.
Legacy `.codex/phase-loop/` state exists only as compatibility residue and is
not authoritative for this run.

The active blocker evidence is already frozen in
`docs/status/SEMANTIC_DOGFOOD_REBUILD.md`. Its SEMCLAUDECMDS rerun capture at
`2026-04-29T15:03:10Z` records the refreshed repo-local command
`timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
terminalizing later in lexical walking with `Trace status: interrupted`,
`Trace stage: lexical_walking`, `Trace blocker source: lexical_mutation`,
`Last progress path:
/home/viperjuice/code/Code-Index-MCP/scripts/migrate_large_index_to_multi_repo.py`,
and `In-flight path:
/home/viperjuice/code/Code-Index-MCP/scripts/check_index_languages.py`.
SEMCLAUDECMDS therefore satisfied its own acceptance boundary, and the roadmap
now steers execution to this exact later script seam rather than reopening the
older `.claude/commands` boundary.

Repository research narrows the likely repair surface:

- `mcp_server/dispatcher/dispatcher_enhanced.py` already contains a narrow
  exact-bounded Python path mechanism in `_EXACT_BOUNDED_PYTHON_PATHS` plus
  `_build_exact_bounded_python_shard(...)`. That mechanism already covers
  `scripts/validate_mcp_comprehensive.py` and
  `tests/root_tests/run_reranking_tests.py`, which means this phase can likely
  reuse the same dispatcher-side fast path instead of widening the Python
  plugin's generic chunk-bypass rules.
- `mcp_server/plugins/python_plugin/plugin.py::_BOUNDED_CHUNK_PATHS` still
  covers earlier bounded Python files such as
  `scripts/quick_mcp_vs_native_validation.py`,
  `tests/test_artifact_publish_race.py`, and
  `mcp_server/visualization/quick_charts.py`, but it does not cover either
  `scripts/migrate_large_index_to_multi_repo.py` or
  `scripts/check_index_languages.py`. The current exact repair surface is
  therefore dispatcher-local, not a broad plugin policy change.
- `scripts/migrate_large_index_to_multi_repo.py` is materially larger than the
  current blocked companion: `591` lines / `22134` bytes versus
  `scripts/check_index_languages.py` at `58` lines / `1465` bytes. The larger
  script defines `RepositoryMigration`, `LargeIndexMigrator`, and `main()`;
  the smaller language-audit script contains only top-level imperative code and
  no top-level `def` or `class` nodes.
- Existing tests already freeze adjacent later-script behavior, but not this
  exact pair. `tests/test_dispatcher.py` and `tests/test_git_index_manager.py`
  pin the earlier
  `scripts/run_test_batch.py -> scripts/validate_mcp_comprehensive.py` seam,
  and `tests/test_repository_commands.py` already prints exact bounded Python
  boundary wording for the older single-file script recoveries. None of those
  tests yet prove the newer
  `scripts/migrate_large_index_to_multi_repo.py ->
  scripts/check_index_languages.py` boundary or guard against a broad
  `scripts/*.py` shortcut.
- `tests/docs/test_semdogfood_evidence_contract.py` already requires the live
  evidence artifact to retain both script paths, the durable
  `force_full_exit_trace.json` vocabulary, and the roadmap steering mention for
  downstream `SEMSCRIPTLANGS`. What is still missing is the execution-ready
  phase plan that freezes the exact dispatcher/status/evidence work needed to
  clear or truthfully advance beyond this pair.

Practical planning boundary:

- SEMSCRIPTLANGS may add a narrow exact bounded Python repair for the exact
  pair `scripts/migrate_large_index_to_multi_repo.py` and
  `scripts/check_index_languages.py`, keep durable lexical file visibility for
  both files, align `repository status` wording with the repaired boundary,
  rerun the repo-local force-full sync, and refresh the dogfood evidence with
  either a later truthful blocker or proof that the script pair is no longer
  active.
- SEMSCRIPTLANGS must stay tightly scoped to the exact script pair. It must
  not broaden into a blanket `scripts/*.py` fast path, Python-plugin-wide
  chunking bypass, or repo-wide lexical-timeout retune, and it must not reopen
  older `.claude`, docs, benchmark, archive-tail, or root-test seams unless the
  refreshed rerun explicitly re-anchors there again.

## Interface Freeze Gates

- [ ] IF-0-SEMSCRIPTLANGS-1 - Script-pair advance contract:
      a refreshed repo-local force-full rerun on the post-SEMCLAUDECMDS head
      no longer terminalizes with the durable lexical trace centered on
      `scripts/migrate_large_index_to_multi_repo.py ->
      scripts/check_index_languages.py`; it either advances durably beyond
      that pair or emits a truthful newer blocker before the 120-second
      watchdog expires.
- [ ] IF-0-SEMSCRIPTLANGS-2 - Exact Python repair contract:
      any new lexical recovery remains limited to the exact files
      `scripts/migrate_large_index_to_multi_repo.py` and
      `scripts/check_index_languages.py`. It does not broaden into arbitrary
      `scripts/*.py`, a generic audit-script exemption, or a repo-wide
      lexical-timeout retune.
- [ ] IF-0-SEMSCRIPTLANGS-3 - Lexical discoverability contract:
      whichever bounded Python repair is chosen preserves lexical file storage
      and FTS visibility for both files; `scripts/migrate_large_index_to_multi_repo.py`
      must keep durable top-level class/function discoverability, and
      `scripts/check_index_languages.py` may legitimately emit no symbols but
      must remain lexically discoverable as a stored file rather than becoming
      an indexing blind spot.
- [ ] IF-0-SEMSCRIPTLANGS-4 - Durable trace and status contract:
      `force_full_exit_trace.json` and `uv run mcp-index repository status`
      stay truthful about the repaired script-pair boundary. If one or both
      scripts move onto an exact bounded Python path, the status surface must
      explain that exact pair without regressing to stale single-file wording
      from earlier script or root-test seams.
- [ ] IF-0-SEMSCRIPTLANGS-5 - Evidence contract:
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the SEMCLAUDECMDS
      rerun outcome, the SEMSCRIPTLANGS rerun command and timestamps, the
      refreshed durable trace/status output, and the final authoritative verdict
      for the script-pair blocker.

## Lane Index & Dependencies

- SL-0 - Script-pair fixture freeze; Depends on: SEMCLAUDECMDS; Blocks: SL-1, SL-2, SL-3; Parallel-safe: no
- SL-1 - Exact bounded Python repair for the language-audit pair; Depends on: SL-0; Blocks: SL-2, SL-3; Parallel-safe: no
- SL-2 - Operator boundary and durable-trace alignment; Depends on: SL-0, SL-1; Blocks: SL-3; Parallel-safe: no
- SL-3 - Live rerun evidence reducer and downstream steering refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SEMSCRIPTLANGS acceptance; Parallel-safe: no

Lane DAG:

```text
SEMCLAUDECMDS
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SEMSCRIPTLANGS acceptance
```

## Lanes

### SL-0 - Script-Pair Fixture Freeze

- **Scope**: Freeze the exact
  `scripts/migrate_large_index_to_multi_repo.py ->
  scripts/check_index_languages.py` lexical seam in dispatcher and
  force-full-trace tests before runtime changes so this phase proves a narrow
  pair repair rather than a broad script shortcut.
- **Owned files**: `tests/test_dispatcher.py`, `tests/test_git_index_manager.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMSCRIPTLANGS-1,
  IF-0-SEMSCRIPTLANGS-2,
  IF-0-SEMSCRIPTLANGS-3,
  and the durable-trace portion of IF-0-SEMSCRIPTLANGS-4
- **Interfaces consumed**: existing
  `EnhancedDispatcher.index_directory(...)`,
  `Dispatcher._build_exact_bounded_python_shard(...)`,
  `GitAwareIndexManager.sync_repository_index(...)`,
  the current `_EXACT_BOUNDED_PYTHON_PATHS` contract, and the SEMCLAUDECMDS
  evidence for the later script pair
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` with a repo-shaped fixture that
    reproduces the exact pair, proves any repaired path advances past
    `scripts/migrate_large_index_to_multi_repo.py` without leaving
    `scripts/check_index_languages.py` on the heavyweight lexical path, and
    preserves the lexical watchdog for unrelated Python files.
  - test: In the same dispatcher coverage, assert the bounded result keeps
    `RepositoryMigration`, `LargeIndexMigrator`, and `main` discoverable for
    `scripts/migrate_large_index_to_multi_repo.py`, while
    `scripts/check_index_languages.py` keeps zero chunks plus durable FTS/file
    visibility even though it has no top-level function or class definitions.
  - test: Extend `tests/test_git_index_manager.py` so durable force-full trace
    persistence freezes the script-pair handoff and verifies later reruns do
    not regress to the older `.claude/commands` or root-test blocker wording
    once the exact pair is repaired.
  - impl: Keep fixtures deterministic with synthetic script content and
    monkeypatched lexical progress callbacks rather than multi-minute live waits
    inside unit coverage.
  - impl: Keep this lane on contract freeze only. Do not update operator
    status wording or the dogfood evidence artifact here.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov -k "migrate or check_index_languages or lexical or force_full or script"`

### SL-1 - Exact Bounded Python Repair For The Language-Audit Pair

- **Scope**: Implement the smallest exact dispatcher-side repair needed so the
  live lexical walker no longer spends its watchdog budget on
  `scripts/migrate_large_index_to_multi_repo.py ->
  scripts/check_index_languages.py`.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`
- **Interfaces provided**: IF-0-SEMSCRIPTLANGS-2 exact Python repair
  contract; IF-0-SEMSCRIPTLANGS-3 lexical discoverability contract
- **Interfaces consumed**: SL-0 script-pair fixtures; existing
  `_EXACT_BOUNDED_PYTHON_PATHS`; existing
  `_build_exact_bounded_python_shard(...)`; current AST-based top-level symbol
  extraction; and the current heavyweight Python plugin path used for scripts
  that are not exact bounded paths
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 dispatcher slice first and confirm the exact pair still
    falls through to the normal Python indexing path on the current checkout.
  - impl: Choose the narrowest repair surface and keep it exact: extend
    `_EXACT_BOUNDED_PYTHON_PATHS` with
    `scripts/migrate_large_index_to_multi_repo.py` and
    `scripts/check_index_languages.py`, or add an equivalently narrow
    exact-path branch in `_build_exact_bounded_python_shard(...)`. Do not add a
    broad `scripts/` directory rule or widen `Plugin._BOUNDED_CHUNK_PATHS`.
  - impl: Reuse the existing exact bounded Python shard builder so the larger
    migration script preserves top-level class/function discoverability while
    the smaller language-audit script preserves stored file content and lexical
    FTS visibility even if it emits zero symbols.
  - impl: Keep this lane local to the dispatcher. Do not retune the global
    lexical timeout and do not reopen earlier `validate_mcp_comprehensive`,
    `run_reranking_tests`, or `.claude/commands` bounded-path behavior here.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py -q --no-cov -k "migrate or check_index_languages or lexical or bounded or script"`

### SL-2 - Operator Boundary And Durable-Trace Alignment

- **Scope**: Keep the operator-facing status surface aligned with the repaired
  script-pair behavior so `repository status` explains the exact bounded
  Python seam truthfully instead of leaving the pair implicit in raw paths
  alone or regressing to earlier single-file script wording.
- **Owned files**: `mcp_server/cli/repository_commands.py`, `tests/test_repository_commands.py`
- **Interfaces provided**: the operator-surface portion of
  IF-0-SEMSCRIPTLANGS-4 durable trace and status contract
- **Interfaces consumed**: SL-0 script-pair fixture vocabulary; SL-1 chosen
  exact bounded Python repair; existing `_print_force_full_exit_trace(...)`;
  current exact bounded Python boundary helpers for earlier script and root-test
  seams; and current durable trace fields `last_progress_path` /
  `in_flight_path`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_repository_commands.py` so
    `uv run mcp-index repository status` must advertise the exact bounded
    Python seam for
    `scripts/migrate_large_index_to_multi_repo.py ->
    scripts/check_index_languages.py` whenever both files exist and the durable
    trace has already advanced into or beyond that pair.
  - impl: Add the narrowest boundary-printer helper needed for the exact script
    pair and keep it additive beside the existing single-file helpers for
    quick-validation, validate, reranking, and visualization boundaries.
  - impl: Preserve the current durable trace vocabulary. This lane should not
    rename `Trace stage`, `Trace blocker source`, `last_progress_path`, or
    `in_flight_path`; it should only make the script-pair boundary explicit
    when the files are present.
  - impl: Do not broaden status wording into a generic `scripts/*.py` claim or
    a catch-all Python fast-path summary.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_repository_commands.py -q --no-cov -k "migrate or check_index_languages or lexical or boundary or interrupted"`

### SL-3 - Live Rerun Evidence Reducer And Downstream Steering Refresh

- **Scope**: Re-run the repaired repo-local force-full sequence, reduce the
  outcome into the durable semantic dogfood evidence artifact, and record the
  authoritative post-script-pair verdict for the next downstream work.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: IF-0-SEMSCRIPTLANGS-1 script-pair advance contract;
  IF-0-SEMSCRIPTLANGS-4 durable trace and status contract;
  IF-0-SEMSCRIPTLANGS-5 evidence contract
- **Interfaces consumed**: SL-0 script-pair fixture vocabulary; SL-1 repaired
  dispatcher behavior; SL-2 status wording; current SEMCLAUDECMDS evidence; and
  the live repo-local `force_full_exit_trace.json`, `repository status`, and
  SQLite runtime counts after the refreshed rerun
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/docs/test_semdogfood_evidence_contract.py` so the
    evidence artifact must retain the script pair, the SEMSCRIPTLANGS rerun
    command, the refreshed trace/status fields, the phase plan reference, and
    the final verdict for whether the active blocker moved beyond the exact
    language-audit seam.
  - impl: Refresh `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` with the
    SEMCLAUDECMDS observed script-pair blocker, the repaired SEMSCRIPTLANGS
    rerun command and timestamps, the resulting durable trace snapshot, the
    matching `repository status` output, and the final call on whether the
    active blocker advanced beyond `scripts/check_index_languages.py`.
  - impl: If the refreshed rerun reaches a newer blocker after the script pair
    is cleared, record that exact blocker and amend the roadmap at the nearest
    downstream phase that is not already executing before treating any older
    downstream plan or handoff as authoritative.
  - impl: Keep the evidence truthful about lexical-only progress.
    `chunk_summaries` and `semantic_points` may remain zero here; do not imply
    semantic closeout unless the rerun actually leaves lexical walking.
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
  - verify: `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - verify: `sed -n '1,240p' .mcp-index/force_full_exit_trace.json`
  - verify: `sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'`
  - verify: `git diff --check`
  - verify: `git diff --cached --check`

## Verification

- Lane checks:
  - `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov -k "migrate or check_index_languages or lexical or force_full or script"`
  - `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_repository_commands.py -q --no-cov -k "migrate or check_index_languages or lexical or boundary or interrupted"`
  - `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
- Whole-phase checks:
  - `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_repository_commands.py tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "migrate or check_index_languages or lexical or force_full or boundary or interrupted or script"`
  - `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  - `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - `sed -n '1,240p' .mcp-index/force_full_exit_trace.json`
  - `sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'`
  - `git diff --check`
  - `git diff --cached --check`

## Acceptance Criteria

- [ ] A refreshed repo-local force-full rerun on the post-SEMCLAUDECMDS head
      either advances durably beyond
      `scripts/migrate_large_index_to_multi_repo.py ->
      scripts/check_index_languages.py` or emits a truthful newer blocker
      before the 120-second watchdog expires.
- [ ] The repair stays narrowly scoped to the exact
      `scripts/migrate_large_index_to_multi_repo.py` and
      `scripts/check_index_languages.py` pair plus the immediate
      dispatcher/status/evidence plumbing needed to prove it.
- [ ] Lexical file storage and FTS visibility remain intact for both exact
      script paths, and `scripts/migrate_large_index_to_multi_repo.py` keeps
      durable top-level class/function discoverability.
- [ ] `uv run mcp-index repository status` and
      `force_full_exit_trace.json` stay aligned with the repaired script-pair
      outcome and do not regress to stale `.claude` or earlier single-file
      script boundary wording.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the SEMCLAUDECMDS rerun
      outcome and the final live verdict for the language-audit script pair.

automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMSCRIPTLANGS.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMSCRIPTLANGS.md
  artifact_state: staged
