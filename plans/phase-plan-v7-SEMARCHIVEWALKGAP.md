---
phase_loop_plan_version: 1
phase: SEMARCHIVEWALKGAP
roadmap: specs/phase-plans-v7.md
roadmap_sha256: 7db8ed16ea19690956e4ca49cd27fef3f606f5cf3f12c6b051198beb93b5e12c
---
# SEMARCHIVEWALKGAP: Archive Tail Walk-Gap Recovery

## Context

SEMARCHIVEWALKGAP is the phase-45 follow-up for the v7 semantic hardening
roadmap. SEMBENCHDOCS proved the benchmark-doc pair is no longer the active
lexical blocker, but its refreshed live repo-local force-full rerun still
terminalized later in lexical walking with the durable trace stranded on
`analysis_archive/scripts_archive/scripts_test_files/verify_mcp_fix.py` and
no surviving later `in_flight_path`.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is the active roadmap, it is tracked and clean in
  this worktree, and canonical `.phase-loop/state.json` reports the required
  `roadmap_sha256`
  `7db8ed16ea19690956e4ca49cd27fef3f606f5cf3f12c6b051198beb93b5e12c`.
- Canonical phase-loop state exists under `.phase-loop/`; `.phase-loop/state.json`
  and `.phase-loop/tui-handoff.md` both mark `SEMARCHIVEWALKGAP` as the
  current `unplanned` phase after `SEMBENCHDOCS` closed out with verification
  `passed`, commit `816b8f84c1aef71c6c70f143d703f4f184033c25`, a clean
  worktree, and `main...origin/main [ahead 85]`. Legacy `.codex/phase-loop/`
  artifacts are compatibility-only and are not authoritative for this run.
- The target artifact `plans/phase-plan-v7-SEMARCHIVEWALKGAP.md` did not exist
  before this planning run.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is the active evidence anchor. Its
  SEMBENCHDOCS live rerun block records the refreshed
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  command, exit code `124`, observed commit `7282e341`, durable trace rewrite
  to `Trace status: interrupted`, `Trace stage: lexical_walking`,
  `Trace stage family: lexical`, `Trace blocker source: lexical_mutation`,
  `Last progress path: /home/viperjuice/code/Code-Index-MCP/analysis_archive/scripts_archive/scripts_test_files/verify_mcp_fix.py`,
  `In-flight path: null`, and the later oversized-file warning for
  `/home/viperjuice/code/Code-Index-MCP/analysis_archive/semantic_vs_sql_comparison_1750926162.json`.
- The current archive tail is concrete and asymmetrical. The predecessor Python
  file `analysis_archive/scripts_archive/scripts_test_files/verify_mcp_fix.py`
  is only `289` lines / `11037` bytes, while the apparent successor JSON
  artifact `analysis_archive/semantic_vs_sql_comparison_1750926162.json` is
  `8157` lines / `32983030` bytes. That points at a later archive-tail handoff
  or exact-file handling problem, not a generic Python regression on
  `verify_mcp_fix.py` itself.
- Exact bounded JSON handling already exists, but only for one path today.
  `GenericTreeSitterPlugin._EXACT_BOUNDED_JSON_PATHS` currently contains only
  `.devcontainer/devcontainer.json`, and
  `tests/test_dispatcher.py` already freezes that dispatcher fast-path by
  asserting the heavy JSON plugin path is bypassed while lexical file storage
  remains discoverable.
- Operator status already exposes several earlier exact boundaries through
  `mcp_server/cli/repository_commands.py`: `.devcontainer/devcontainer.json`,
  `mcp_server/visualization/quick_charts.py`, the validation doc pair, the
  benchmark doc pair, and the ignored `test_workspace/` family. There is no
  archive-tail boundary helper or archive-tail wording yet, and the current
  trace output prints `Last progress path` without a successor when
  `in_flight_path` is `null`.
- Existing coverage is adjacent but incomplete for this phase. 
  `tests/test_dispatcher.py`, `tests/test_git_index_manager.py`, and
  `tests/test_repository_commands.py` already freeze exact bounded JSON,
  visualization, benchmark-doc, ignored-tail, and `in_flight_path=None`
  contracts. `tests/docs/test_semdogfood_evidence_contract.py` already expects
  both archive-tail paths plus the downstream steering to
  `SEMARCHIVEWALKGAP`. What is missing is an execution-ready contract that
  binds those surfaces to this specific archive-tail walk gap.

Practical planning boundary:

- SEMARCHIVEWALKGAP may tighten exact archive-tail JSON handling, lexical
  progress emission, durable trace persistence, operator status wording, and
  the dogfood evidence artifact needed to prove the rerun either advances
  beyond `verify_mcp_fix.py` or truthfully surfaces the real later archive
  blocker.
- SEMARCHIVEWALKGAP must stay narrow and evidence-driven. It must not widen
  into a blanket `analysis_archive/` ignore rule, repo-wide JSON lightweight
  policy, general timeout retuning, or reopening older benchmark/visualization/
  devcontainer/script/root-test seams unless the refreshed rerun directly
  re-anchors there again.

## Interface Freeze Gates

- [ ] IF-0-SEMARCHIVEWALKGAP-1 - Archive-tail advance contract:
      a refreshed repo-local `repository sync --force-full` on the
      post-SEMBENCHDOCS head no longer terminalizes with the durable lexical
      trace stranded on
      `analysis_archive/scripts_archive/scripts_test_files/verify_mcp_fix.py`
      and no later survivor; it either advances durably beyond that path or
      emits a truthful newer archive-tail blocker before the 120-second
      watchdog expires.
- [ ] IF-0-SEMARCHIVEWALKGAP-2 - Exact archive-tail repair contract:
      any new recovery remains limited to
      `analysis_archive/scripts_archive/scripts_test_files/verify_mcp_fix.py`,
      `analysis_archive/semantic_vs_sql_comparison_1750926162.json`, and the
      immediate dispatcher/plugin/trace/status plumbing needed to prove their
      handoff; it does not broaden into arbitrary `analysis_archive/**/*.json`,
      repo-wide JSON exemptions, or a global lexical-timeout retune.
- [ ] IF-0-SEMARCHIVEWALKGAP-3 - Lexical discoverability contract:
      whichever archive-tail repair is chosen preserves lexical file storage
      and searchability for the exact archive path(s) it bounds; the repair
      must not silently turn the archive JSON or the archive verifier script
      into untracked lexical blind spots.
- [ ] IF-0-SEMARCHIVEWALKGAP-4 - Durable trace truthfulness contract:
      `EnhancedDispatcher`, `GitAwareIndexManager`, and
      `force_full_exit_trace.json` preserve a truthful archive-tail handoff.
      If the next successor is bounded or skipped, the persisted trace and
      status surface must explain that exact archive-tail outcome rather than
      leaving an ambiguous `in_flight_path=null` with no bounded-successor
      explanation.
- [ ] IF-0-SEMARCHIVEWALKGAP-5 - Operator boundary contract:
      `uv run mcp-index repository status` stays aligned with the repaired
      archive-tail behavior, preserves the existing boundary lines for
      `.devcontainer/devcontainer.json`,
      `mcp_server/visualization/quick_charts.py`,
      `docs/validation/ga-closeout-decision.md`,
      `docs/validation/mre2e-evidence.md`,
      `docs/benchmarks/mcp_vs_native_benchmark_fullrepo_fireworks_qwen_voyage_local_iter5_rerun.md -> docs/benchmarks/production_benchmark.md`,
      `scripts/quick_mcp_vs_native_validation.py`,
      `scripts/validate_mcp_comprehensive.py`,
      `tests/test_artifact_publish_race.py`,
      `tests/root_tests/run_reranking_tests.py`, and
      `test_workspace/`, and adds no misleading archive-tail copy.
- [ ] IF-0-SEMARCHIVEWALKGAP-6 - Evidence contract:
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the SEMBENCHDOCS rerun
      outcome, the repaired SEMARCHIVEWALKGAP rerun command and timestamps,
      the refreshed durable trace/status output, and the final authoritative
      verdict for the archive-tail blocker.
- [ ] IF-0-SEMARCHIVEWALKGAP-7 - Upstream/downstream preservation contract:
      SEMBENCHDOCS and the earlier bounded seams remain historically valid and
      closed unless the refreshed rerun directly re-anchors on a different
      later blocker after the archive-tail pair is cleared.

## Lane Index & Dependencies

- SL-0 - Archive-tail fixture freeze; Depends on: SEMBENCHDOCS; Blocks: SL-1, SL-2, SL-3; Parallel-safe: no
- SL-1 - Exact archive-tail repair or bounded-successor capture; Depends on: SL-0; Blocks: SL-2, SL-3; Parallel-safe: no
- SL-2 - Repository-status and durable-trace archive alignment; Depends on: SL-0, SL-1; Blocks: SL-3; Parallel-safe: no
- SL-3 - Live rerun evidence reducer and closeout refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SEMARCHIVEWALKGAP acceptance; Parallel-safe: no

Lane DAG:

```text
SEMBENCHDOCS
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SEMARCHIVEWALKGAP acceptance
```

## Lanes

### SL-0 - Archive-Tail Fixture Freeze

- **Scope**: Freeze the exact archive-tail handoff in unit coverage so this
  phase proves the later
  `verify_mcp_fix.py -> semantic_vs_sql_comparison_1750926162.json`
  seam and its `in_flight_path=null` truthfulness problem, not a generic
  archive-directory or Python regression.
- **Owned files**: `tests/test_dispatcher.py`, `tests/test_git_index_manager.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMARCHIVEWALKGAP-1,
  IF-0-SEMARCHIVEWALKGAP-2,
  IF-0-SEMARCHIVEWALKGAP-3,
  IF-0-SEMARCHIVEWALKGAP-4,
  and IF-0-SEMARCHIVEWALKGAP-7
- **Interfaces consumed**: existing
  `EnhancedDispatcher.index_directory(...)`,
  `EnhancedDispatcher._index_file_with_lexical_timeout(...)`,
  `GenericTreeSitterPlugin.uses_exact_bounded_json_path(...)`,
  `GitAwareIndexManager._make_force_full_progress_callback(...)`,
  `GitAwareIndexManager._write_force_full_exit_trace(...)`,
  `GitAwareIndexManager._finalize_running_force_full_trace_as_interrupted(...)`,
  and the current SEMBENCHDOCS evidence wording for
  `verify_mcp_fix.py`, the oversized archive JSON warning, and
  `in_flight_path=null`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` with a repo-shaped fixture for
    `analysis_archive/scripts_archive/scripts_test_files/verify_mcp_fix.py`
    plus
    `analysis_archive/semantic_vs_sql_comparison_1750926162.json` that proves
    the repaired archive tail either preserves the JSON successor as the
    authoritative later path or records a truthful bounded-successor outcome
    instead of dropping to `in_flight_path=null` without explanation.
  - test: Freeze negative assertions in `tests/test_dispatcher.py` so earlier
    bounded seams for `.devcontainer/devcontainer.json`,
    `mcp_server/visualization/quick_charts.py`, the validation-doc pair, the
    benchmark-doc pair, and `test_workspace/` do not silently regress while
    the archive-tail seam is added.
  - test: Extend `tests/test_git_index_manager.py` so durable force-full trace
    persistence freezes the archive-tail handoff, including preserved
    `last_progress_path=verify_mcp_fix.py`, truthful
    `blocker_source=lexical_mutation`, explicit handling for
    `in_flight_path=None`, and a requirement that any `null` successor be
    paired with the exact bounded archive-tail explanation that SL-2 will
    surface.
  - impl: Use synthetic dispatcher progress and synthetic durable-trace
    payloads rather than a live multi-minute rerun inside unit coverage.
  - impl: Keep this lane focused on contract freeze only. Do not update CLI
    wording or the dogfood evidence artifact here.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov -k "analysis_archive or verify_mcp_fix or semantic_vs_sql_comparison_1750926162 or lexical or force_full or json or trace or bounded"`

### SL-1 - Exact Archive-Tail Repair Or Bounded-Successor Capture

- **Scope**: Implement the smallest exact repair needed so the later archive
  tail no longer collapses into `verify_mcp_fix.py` with no surviving
  successor under the lexical watchdog.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `mcp_server/plugins/generic_treesitter_plugin.py`, `mcp_server/storage/git_index_manager.py`
- **Interfaces provided**: IF-0-SEMARCHIVEWALKGAP-1 archive-tail advance contract;
  IF-0-SEMARCHIVEWALKGAP-2 exact archive-tail repair contract;
  IF-0-SEMARCHIVEWALKGAP-3 lexical discoverability contract;
  IF-0-SEMARCHIVEWALKGAP-4 durable trace truthfulness contract
- **Interfaces consumed**: SL-0 archive-tail fixtures; existing
  `_EXACT_BOUNDED_JSON_PATHS`,
  `GenericTreeSitterPlugin.uses_exact_bounded_json_path(...)`,
  current lexical progress emission in `index_directory(...)`,
  durable `last_progress_path` / `in_flight_path` persistence, and the live
  evidence showing the archive JSON warning without a surviving later path
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 dispatcher and git-manager slices first and confirm the
    current checkout still lacks a truthful durable successor after
    `verify_mcp_fix.py` on the current head.
  - impl: Determine whether the narrowest repair belongs in exact bounded JSON
    handling for
    `analysis_archive/semantic_vs_sql_comparison_1750926162.json`,
    archive-tail lexical progress emission after the JSON candidate is seen,
    durable trace finalization when the candidate is bounded or skipped, or
    the smallest combination required to keep the successor truth visible.
  - impl: If an exact bounded JSON repair is chosen, keep it exact to
    `analysis_archive/semantic_vs_sql_comparison_1750926162.json` and reuse
    the existing bounded-JSON mechanism. Do not introduce a broad
    `analysis_archive/**/*.json`, all-large-JSON, or repo-wide JSON fast-path.
  - impl: Preserve lexical file storage and discoverability for any archive
    path placed on a bounded fast-path. The repair must not silently drop the
    archive JSON or the archive verifier script from `files`, FTS-backed
    content, or basic symbol/file lookup.
  - impl: If the JSON still cannot safely survive as `in_flight_path`, add the
    smallest truthful trace metadata or handoff needed so the later archive
    blocker is explicit instead of collapsing into an unexplained `null`
    successor.
  - impl: Preserve the already-closed exact bounded paths for
    `.devcontainer/devcontainer.json` and
    `mcp_server/visualization/quick_charts.py`, plus the existing benchmark
    and validation Markdown contracts.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov -k "analysis_archive or verify_mcp_fix or semantic_vs_sql_comparison_1750926162 or lexical or force_full or json or trace or bounded"`
  - verify: `rg -n "semantic_vs_sql_comparison_1750926162|verify_mcp_fix|_EXACT_BOUNDED_JSON_PATHS|uses_exact_bounded_json_path|last_progress_path|in_flight_path|lexical_mutation|force_full" mcp_server/dispatcher/dispatcher_enhanced.py mcp_server/plugins/generic_treesitter_plugin.py mcp_server/storage/git_index_manager.py tests/test_dispatcher.py tests/test_git_index_manager.py`

### SL-2 - Repository-Status And Durable-Trace Archive Alignment

- **Scope**: Keep the operator-facing status surface aligned with the repaired
  archive-tail behavior so `repository status` explains the exact archive
  blocker or bounded successor truthfully instead of printing a dead-end
  `Last progress path` with no archive-tail interpretation.
- **Owned files**: `mcp_server/cli/repository_commands.py`, `tests/test_repository_commands.py`
- **Interfaces provided**: IF-0-SEMARCHIVEWALKGAP-4 durable trace truthfulness contract;
  IF-0-SEMARCHIVEWALKGAP-5 operator boundary contract;
  IF-0-SEMARCHIVEWALKGAP-7 upstream/downstream preservation contract
- **Interfaces consumed**: SL-0 archive-tail fixture vocabulary; SL-1 chosen
  repair; current `_print_force_full_exit_trace(...)`; current boundary
  helpers for devcontainer JSON, visualization quick charts, validation docs,
  benchmark docs, exact bounded Python paths, and `test_workspace/`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_repository_commands.py` so `repository status`
    freezes the archive-tail seam and proves the surface reports either the
    preserved JSON successor or the exact bounded archive-tail explanation
    truthfully when `in_flight_path` is `null`.
  - test: Require negative assertions that status output does not regress to
    benchmark-doc, visualization, devcontainer, or generic large-JSON wording
    once the archive-tail fixture is active.
  - impl: Add or refine operator wording only as needed so the archive-tail
    outcome is explicit. If a new helper is needed, keep it exact to
    `analysis_archive/scripts_archive/scripts_test_files/verify_mcp_fix.py`
    and
    `analysis_archive/semantic_vs_sql_comparison_1750926162.json`; do not add
    a generic `analysis_archive/` or `.json` boundary printer.
  - impl: Preserve the current boundary lines for
    `.devcontainer/devcontainer.json`,
    `mcp_server/visualization/quick_charts.py`,
    `docs/validation/ga-closeout-decision.md`,
    `docs/validation/mre2e-evidence.md`,
    `docs/benchmarks/mcp_vs_native_benchmark_fullrepo_fireworks_qwen_voyage_local_iter5_rerun.md -> docs/benchmarks/production_benchmark.md`,
    `scripts/quick_mcp_vs_native_validation.py`,
    `scripts/validate_mcp_comprehensive.py`,
    `tests/test_artifact_publish_race.py`,
    `tests/root_tests/run_reranking_tests.py`, and
    `test_workspace/`.
  - impl: Keep fail-closed semantics intact. If the live rerun still blocks
    after the archive-tail repair, surface the true later blocker rather than
    claiming lexical success, semantic readiness, or closeout readiness early.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_repository_commands.py -q --no-cov -k "analysis_archive or verify_mcp_fix or semantic_vs_sql_comparison_1750926162 or force_full or interrupted or boundary or json"`
  - verify: `rg -n "verify_mcp_fix|semantic_vs_sql_comparison_1750926162|Trace status|Trace stage|Trace blocker source|Last progress path|In-flight path|Lexical boundary" mcp_server/cli/repository_commands.py tests/test_repository_commands.py`

### SL-3 - Live Rerun Evidence Reducer And Closeout Refresh

- **Scope**: Re-run the repaired repo-local force-full path, reduce the real
  archive-tail outcome into the dogfood evidence artifact, and keep the
  closeout narrative aligned with the actual current-head blocker after the
  archive-tail repair.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: IF-0-SEMARCHIVEWALKGAP-6 evidence contract;
  IF-0-SEMARCHIVEWALKGAP-7 upstream/downstream preservation contract
- **Interfaces consumed**: SL-0 archive-tail fixture vocabulary; SL-1 repaired
  archive-tail behavior; SL-2 status wording; current SEMBENCHDOCS evidence;
  current phase roadmap steering for `SEMARCHIVEWALKGAP`; and the live
  repo-local `force_full_exit_trace.json`, `repository status`, and SQLite
  runtime counts after the rerun
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/docs/test_semdogfood_evidence_contract.py` so the
    evidence artifact must retain both archive-tail paths, the archive-tail
    rerun command, the refreshed trace/status fields, the final verdict for
    whether the successor survived, and the downstream-steering text after the
    live rerun.
  - impl: Refresh `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` with the
    SEMBENCHDOCS observed archive-tail blocker, the repaired
    SEMARCHIVEWALKGAP rerun command and timestamps, the resulting durable trace
    snapshot, the matching `repository status` output, and the final call on
    whether the active blocker moved beyond the archive tail.
  - impl: If the refreshed rerun reaches a newer blocker after the archive
    pair is cleared, record that exact blocker and amend the roadmap at the
    nearest downstream phase that is not already executing before treating any
    older downstream plan as authoritative.
  - impl: Keep the evidence truthful about lexical-only progress.
    `chunk_summaries` and `semantic_points` may remain zero here; do not imply
    semantic closeout if the rerun still exits in lexical walking.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
  - verify: `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - verify: `sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'`
  - verify: `git diff --check`
  - verify: `git diff --cached --check`

## Verification

- Lane checks:
  - `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov -k "analysis_archive or verify_mcp_fix or semantic_vs_sql_comparison_1750926162 or lexical or force_full or json or trace or bounded"`
  - `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_repository_commands.py -q --no-cov -k "analysis_archive or verify_mcp_fix or semantic_vs_sql_comparison_1750926162 or force_full or interrupted or boundary or json"`
  - `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
- Whole-phase checks:
  - `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_repository_commands.py tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
  - `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  - `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - `sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'`
  - `git diff --check`
  - `git diff --cached --check`

## Acceptance Criteria

- [ ] A refreshed repo-local force-full rerun on the post-SEMBENCHDOCS head
      either advances durably beyond
      `analysis_archive/scripts_archive/scripts_test_files/verify_mcp_fix.py`
      or emits a truthful newer blocker before the 120-second watchdog
      expires.
- [ ] The repair stays narrowly scoped to the later archive-tail walk gap and
      the immediate dispatcher/plugin/trace/status plumbing needed to prove it.
- [ ] If the archive JSON successor is bounded or skipped, the durable trace
      and `repository status` surfaces explain that exact archive-tail outcome
      truthfully instead of leaving an unexplained `in_flight_path=null`.
- [ ] Lexical file storage and discoverability remain intact for the exact
      archive path(s) touched by the repair.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the SEMBENCHDOCS rerun
      outcome and the final live verdict for the archive-tail blocker.

automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMARCHIVEWALKGAP.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMARCHIVEWALKGAP.md
  artifact_state: staged
