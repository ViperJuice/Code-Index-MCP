---
phase_loop_plan_version: 1
phase: SEMDOCGOV
roadmap: specs/phase-plans-v7.md
roadmap_sha256: 53a81ee692ea0e2e8c949ca54bff0177dfcdefc2b8e1ac9d9e528e3a07d52b5b
---
# SEMDOCGOV: Docs Governance Contract Lexical Recovery

## Context

SEMDOCGOV is the phase-46 follow-up for the v7 semantic hardening roadmap.
SEMARCHIVEWALKGAP proved the archive-tail seam is no longer the active lexical
blocker, but its refreshed live repo-local force-full rerun still terminalized
later in lexical walking on the docs contract-test pair
`tests/docs/test_mre2e_evidence_contract.py ->
tests/docs/test_gagov_governance_contract.py`.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is the active roadmap, it is tracked and clean in
  this worktree, and canonical `.phase-loop/state.json` reports
  `roadmap_sha256`
  `53a81ee692ea0e2e8c949ca54bff0177dfcdefc2b8e1ac9d9e528e3a07d52b5b`.
- Canonical phase-loop state exists under `.phase-loop/`; `.phase-loop/state.json`
  and `.phase-loop/tui-handoff.md` both mark `SEMDOCGOV` as the current
  `unplanned` phase after `SEMARCHIVEWALKGAP` closed out with verification
  `passed`, commit `12848d161ac38ecc8e4f8f9dce09c8f40bba3f1c`, a clean
  worktree, and `main...origin/main [ahead 87]`. Legacy `.codex/phase-loop/`
  artifacts are compatibility-only and are not authoritative for this run.
- The target artifact `plans/phase-plan-v7-SEMDOCGOV.md` did not exist before
  this planning run.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is the active evidence anchor. Its
  SEMARCHIVEWALKGAP live rerun block records the refreshed
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  command, evidence capture at `2026-04-29T14:13:50Z`, durable trace refresh
  at `2026-04-29T14:12:49Z`, exit code `135`, observed commit `9138e0b0`,
  `Trace status: interrupted`, `Trace stage: lexical_walking`,
  `Trace stage family: lexical`, `Trace blocker source: lexical_mutation`,
  `Last progress path:
  /home/viperjuice/code/Code-Index-MCP/tests/docs/test_mre2e_evidence_contract.py`,
  and `In-flight path:
  /home/viperjuice/code/Code-Index-MCP/tests/docs/test_gagov_governance_contract.py`.
- Exact bounded Python handling already exists for a small set of hot paths.
  `mcp_server/dispatcher/dispatcher_enhanced.py` currently freezes
  `tests/root_tests/run_reranking_tests.py`,
  `scripts/validate_mcp_comprehensive.py`, and
  `mcp_server/visualization/quick_charts.py` in
  `_EXACT_BOUNDED_PYTHON_PATHS`, while
  `_build_exact_bounded_python_shard(...)` preserves lexical file storage and
  top-level symbol discoverability for those exact paths.
- Operator status already advertises earlier exact boundaries through
  `mcp_server/cli/repository_commands.py`: `.devcontainer/devcontainer.json`,
  `mcp_server/visualization/quick_charts.py`, validation docs, benchmark
  docs, the archive-tail JSON seam, exact bounded Python paths for later
  scripts/tests, and the ignored `test_workspace/` family. There is no
  docs-contract pair boundary helper or wording yet for
  `tests/docs/test_mre2e_evidence_contract.py ->
  tests/docs/test_gagov_governance_contract.py`.
- Existing coverage is adjacent but incomplete for this phase.
  `tests/test_dispatcher.py`, `tests/test_git_index_manager.py`, and
  `tests/test_repository_commands.py` already freeze the exact bounded
  Python/Markdown/JSON seams and durable trace vocabulary for earlier later
  blockers, while `tests/docs/test_semdogfood_evidence_contract.py` already
  expects the SEMARCHIVEWALKGAP live rerun to hand off to `SEMDOCGOV`.
  What is missing is an execution-ready contract that binds those surfaces to
  this exact docs-test pair.

Practical planning boundary:

- SEMDOCGOV may tighten exact docs-test Python handling, lexical progress
  emission, durable trace persistence, operator status wording, and the
  dogfood evidence artifact needed to prove the rerun either advances beyond
  `tests/docs/test_gagov_governance_contract.py` or truthfully surfaces the
  real later blocker.
- SEMDOCGOV must stay narrow and evidence-driven. It must not widen into a
  blanket `tests/docs/*.py` exemption, repo-wide Python timeout retune, or
  reopening earlier archive-tail/benchmark/validation/visualization/
  devcontainer seams unless the refreshed rerun directly re-anchors there
  again.

## Interface Freeze Gates

- [ ] IF-0-SEMDOCGOV-1 - Docs-test pair advance contract:
      a refreshed repo-local `repository sync --force-full` on the
      post-SEMARCHIVEWALKGAP head no longer terminalizes with the durable
      lexical trace centered on
      `tests/docs/test_mre2e_evidence_contract.py ->
      tests/docs/test_gagov_governance_contract.py`; it either advances
      durably beyond that pair or emits a truthful newer blocker before the
      120-second watchdog expires.
- [ ] IF-0-SEMDOCGOV-2 - Exact docs-test repair contract:
      any new recovery remains limited to
      `tests/docs/test_mre2e_evidence_contract.py`,
      `tests/docs/test_gagov_governance_contract.py`, and the immediate
      dispatcher/trace/status plumbing needed to prove their handoff; it does
      not broaden into arbitrary `tests/docs/*.py`, repo-wide Python
      exemptions, or a global lexical-timeout retune.
- [ ] IF-0-SEMDOCGOV-3 - Lexical discoverability contract:
      whichever docs-test repair is chosen preserves lexical file storage and
      searchability for the exact docs-test path(s) it bounds; the repair
      must not silently turn those contract tests into lexical blind spots.
- [ ] IF-0-SEMDOCGOV-4 - Durable trace truthfulness contract:
      `EnhancedDispatcher`, `GitAwareIndexManager`, and
      `force_full_exit_trace.json` preserve a truthful docs-test handoff. If
      the second file is bounded or skipped, the persisted trace and status
      surface must explain that exact docs-test outcome rather than leaving an
      ambiguous stale blocker or misleading generic Python wording.
- [ ] IF-0-SEMDOCGOV-5 - Operator boundary contract:
      `uv run mcp-index repository status` stays aligned with the repaired
      docs-test behavior, preserves the existing boundary lines for
      `.devcontainer/devcontainer.json`,
      `mcp_server/visualization/quick_charts.py`,
      `docs/validation/ga-closeout-decision.md`,
      `docs/validation/mre2e-evidence.md`,
      `docs/benchmarks/mcp_vs_native_benchmark_fullrepo_fireworks_qwen_voyage_local_iter5_rerun.md -> docs/benchmarks/production_benchmark.md`,
      `analysis_archive/scripts_archive/scripts_test_files/verify_mcp_fix.py ->
      analysis_archive/semantic_vs_sql_comparison_1750926162.json`,
      `scripts/quick_mcp_vs_native_validation.py`,
      `scripts/validate_mcp_comprehensive.py`,
      `tests/test_artifact_publish_race.py`,
      `tests/root_tests/run_reranking_tests.py`, and `test_workspace/`, and
      adds no misleading generic `tests/docs` copy.
- [ ] IF-0-SEMDOCGOV-6 - Evidence contract:
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMARCHIVEWALKGAP rerun outcome, the repaired SEMDOCGOV rerun command
      and timestamps, the refreshed durable trace/status output, and the
      final authoritative verdict for the docs-test blocker.
- [ ] IF-0-SEMDOCGOV-7 - Upstream/downstream preservation contract:
      SEMARCHIVEWALKGAP and the earlier bounded seams remain historically
      valid and closed unless the refreshed rerun directly re-anchors on a
      different later blocker after the docs-test pair is cleared.

## Lane Index & Dependencies

- SL-0 - Docs-test pair fixture freeze; Depends on: SEMARCHIVEWALKGAP; Blocks: SL-1, SL-2, SL-3; Parallel-safe: no
- SL-1 - Exact docs-test pair repair or bounded-successor capture; Depends on: SL-0; Blocks: SL-2, SL-3; Parallel-safe: no
- SL-2 - Repository-status and durable-trace docs alignment; Depends on: SL-0, SL-1; Blocks: SL-3; Parallel-safe: no
- SL-3 - Live rerun evidence reducer and closeout refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SEMDOCGOV acceptance; Parallel-safe: no

Lane DAG:

```text
SEMARCHIVEWALKGAP
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SEMDOCGOV acceptance
```

## Lanes

### SL-0 - Docs-Test Pair Fixture Freeze

- **Scope**: Freeze the exact docs-contract pair in unit coverage so this
  phase proves the later
  `tests/docs/test_mre2e_evidence_contract.py ->
  tests/docs/test_gagov_governance_contract.py` seam and its durable-trace
  handoff, not a generic `tests/docs` or Python regression.
- **Owned files**: `tests/test_dispatcher.py`, `tests/test_git_index_manager.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMDOCGOV-1,
  IF-0-SEMDOCGOV-2,
  IF-0-SEMDOCGOV-3,
  IF-0-SEMDOCGOV-4,
  and IF-0-SEMDOCGOV-7
- **Interfaces consumed**: existing
  `_EXACT_BOUNDED_PYTHON_PATHS`,
  `EnhancedDispatcher._build_exact_bounded_python_shard(...)`,
  `EnhancedDispatcher.index_directory(...)`,
  `GitAwareIndexManager._make_force_full_progress_callback(...)`,
  `GitAwareIndexManager._write_force_full_exit_trace(...)`,
  `GitAwareIndexManager._finalize_running_force_full_trace_as_interrupted(...)`,
  and the current SEMARCHIVEWALKGAP evidence wording for the docs-test pair
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` with a repo-shaped fixture for
    `tests/docs/test_mre2e_evidence_contract.py` plus
    `tests/docs/test_gagov_governance_contract.py` that proves the repaired
    docs pair either advances cleanly past both files or preserves a truthful
    `last_progress_path` / `in_flight_path` handoff instead of collapsing into
    a generic Python timeout narrative.
  - test: Freeze negative assertions in `tests/test_dispatcher.py` so earlier
    exact bounded seams for `.devcontainer/devcontainer.json`,
    `mcp_server/visualization/quick_charts.py`,
    `analysis_archive/semantic_vs_sql_comparison_1750926162.json`,
    validation docs, benchmark docs, and `test_workspace/` do not silently
    regress while the docs-test seam is added.
  - test: Extend `tests/test_git_index_manager.py` so durable force-full trace
    persistence freezes the docs-test handoff, including preserved
    `last_progress_path=test_mre2e_evidence_contract.py`, truthful
    `in_flight_path=test_gagov_governance_contract.py` while the pair is
    active, and a requirement that any later `interrupted` or advanced trace
    stays consistent with the repaired docs-test seam.
  - impl: Use synthetic dispatcher progress and synthetic durable-trace
    payloads rather than a live multi-minute rerun inside unit coverage.
  - impl: Keep this lane focused on contract freeze only. Do not update CLI
    wording or the dogfood evidence artifact here.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov -k "mre2e or gagov or docs or lexical or force_full or python or trace or bounded"`

### SL-1 - Exact Docs-Test Pair Repair Or Bounded-Successor Capture

- **Scope**: Implement the smallest exact repair needed so the later docs
  contract-test pair no longer owns the durable lexical blocker under the
  watchdog.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `mcp_server/storage/git_index_manager.py`
- **Interfaces provided**: IF-0-SEMDOCGOV-1 docs-test pair advance contract;
  IF-0-SEMDOCGOV-2 exact docs-test repair contract;
  IF-0-SEMDOCGOV-3 lexical discoverability contract;
  IF-0-SEMDOCGOV-4 durable trace truthfulness contract
- **Interfaces consumed**: SL-0 docs-test fixtures; existing exact bounded
  Python machinery in `_EXACT_BOUNDED_PYTHON_PATHS` and
  `_build_exact_bounded_python_shard(...)`; current lexical progress emission
  in `index_directory(...)`; durable `last_progress_path` /
  `in_flight_path` persistence; and the live evidence showing the rerun
  terminalizing on the docs-test pair
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 dispatcher and git-manager slices first and confirm the
    current checkout still lacks an exact docs-test repair for
    `tests/docs/test_mre2e_evidence_contract.py ->
    tests/docs/test_gagov_governance_contract.py`.
  - impl: Determine whether the narrowest repair belongs in exact bounded
    Python handling for one or both docs-test files, docs-test lexical
    progress emission after the first file completes, durable trace
    finalization when the second file is bounded, or the smallest
    combination required to keep the successor truth visible.
  - impl: If exact bounded Python handling is chosen, keep it exact to
    `tests/docs/test_mre2e_evidence_contract.py` and
    `tests/docs/test_gagov_governance_contract.py` by extending the existing
    `_EXACT_BOUNDED_PYTHON_PATHS` mechanism. Do not introduce a broad
    `tests/docs/*.py`, all-test-file, or repo-wide Python fast-path.
  - impl: Preserve lexical file storage and discoverability for any docs-test
    path placed on a bounded fast-path. The repair must not silently drop the
    docs contract tests from `files`, FTS-backed content, or basic
    symbol/file lookup.
  - impl: If the second docs-test file still cannot safely survive as the
    active `in_flight_path`, add the smallest truthful trace metadata or
    handoff needed so the later blocker is explicit instead of collapsing into
    misleading generic timeout wording.
  - impl: Preserve the already-closed exact bounded paths for
    `scripts/validate_mcp_comprehensive.py`,
    `tests/root_tests/run_reranking_tests.py`,
    `mcp_server/visualization/quick_charts.py`, and the archive-tail JSON
    seam, plus the existing validation/benchmark Markdown contracts.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov -k "mre2e or gagov or docs or lexical or force_full or python or trace or bounded"`
  - verify: `rg -n "test_mre2e_evidence_contract|test_gagov_governance_contract|_EXACT_BOUNDED_PYTHON_PATHS|_build_exact_bounded_python_shard|last_progress_path|in_flight_path|lexical_mutation|force_full" mcp_server/dispatcher/dispatcher_enhanced.py mcp_server/storage/git_index_manager.py tests/test_dispatcher.py tests/test_git_index_manager.py`

### SL-2 - Repository-Status And Durable-Trace Docs Alignment

- **Scope**: Keep the operator-facing status surface aligned with the repaired
  docs-test behavior so `repository status` explains the exact docs-pair
  boundary truthfully instead of silently falling back to generic Python or
  stale archive-tail wording.
- **Owned files**: `mcp_server/cli/repository_commands.py`, `tests/test_repository_commands.py`
- **Interfaces provided**: IF-0-SEMDOCGOV-4 durable trace truthfulness contract;
  IF-0-SEMDOCGOV-5 operator boundary contract;
  IF-0-SEMDOCGOV-7 upstream/downstream preservation contract
- **Interfaces consumed**: SL-0 docs-test fixture vocabulary; SL-1 chosen
  repair; current `_print_force_full_exit_trace(...)`; current boundary
  helpers for devcontainer JSON, visualization quick charts, validation docs,
  benchmark docs, archive-tail JSON, exact bounded Python paths, and
  `test_workspace/`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_repository_commands.py` so `repository status`
    freezes the docs-test seam and proves the surface reports the exact
    `tests/docs/test_mre2e_evidence_contract.py ->
    tests/docs/test_gagov_governance_contract.py` boundary truthfully once
    the repair is active.
  - test: Require negative assertions that status output does not regress to
    archive-tail, benchmark-doc, visualization, devcontainer, or generic
    `tests/docs` wording once the docs-test fixture is active.
  - impl: Add or refine operator wording only as needed so the docs-test pair
    outcome is explicit. If a new helper is needed, keep it exact to the two
    docs-test files; do not add a generic `tests/docs/` or `.py` boundary
    printer.
  - impl: Preserve the current boundary lines for
    `.devcontainer/devcontainer.json`,
    `mcp_server/visualization/quick_charts.py`,
    `docs/validation/ga-closeout-decision.md`,
    `docs/validation/mre2e-evidence.md`,
    `docs/benchmarks/mcp_vs_native_benchmark_fullrepo_fireworks_qwen_voyage_local_iter5_rerun.md -> docs/benchmarks/production_benchmark.md`,
    `analysis_archive/scripts_archive/scripts_test_files/verify_mcp_fix.py ->
    analysis_archive/semantic_vs_sql_comparison_1750926162.json`,
    `scripts/quick_mcp_vs_native_validation.py`,
    `scripts/validate_mcp_comprehensive.py`,
    `tests/test_artifact_publish_race.py`,
    `tests/root_tests/run_reranking_tests.py`, and `test_workspace/`.
  - impl: Keep fail-closed semantics intact. If the live rerun still blocks
    after the docs-test repair, surface the true later blocker rather than
    claiming lexical success, semantic readiness, or closeout readiness early.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_repository_commands.py -q --no-cov -k "mre2e or gagov or docs or force_full or interrupted or boundary or python"`
  - verify: `rg -n "test_mre2e_evidence_contract|test_gagov_governance_contract|Trace status|Trace stage|Trace blocker source|Last progress path|In-flight path|Lexical boundary" mcp_server/cli/repository_commands.py tests/test_repository_commands.py`

### SL-3 - Live Rerun Evidence Reducer And Closeout Refresh

- **Scope**: Re-run the repaired repo-local force-full path, reduce the real
  docs-test outcome into the dogfood evidence artifact, and keep the closeout
  narrative aligned with the actual current-head blocker after the docs-test
  repair.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: IF-0-SEMDOCGOV-6 evidence contract;
  IF-0-SEMDOCGOV-7 upstream/downstream preservation contract
- **Interfaces consumed**: SL-0 docs-test fixture vocabulary; SL-1 repaired
  docs-test behavior; SL-2 status wording; current SEMARCHIVEWALKGAP evidence;
  current phase roadmap steering for `SEMDOCGOV`; and the live repo-local
  `force_full_exit_trace.json`, `repository status`, and SQLite runtime counts
  after the rerun
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/docs/test_semdogfood_evidence_contract.py` so the
    evidence artifact must retain the docs-test pair, the SEMDOCGOV rerun
    command, the refreshed trace/status fields, the final verdict for whether
    the active blocker moved beyond the pair, and the downstream steering text
    after the live rerun.
  - impl: Refresh `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` with the
    SEMARCHIVEWALKGAP observed docs-test blocker, the repaired SEMDOCGOV
    rerun command and timestamps, the resulting durable trace snapshot, the
    matching `repository status` output, and the final call on whether the
    active blocker moved beyond the docs contract-test pair.
  - impl: If the refreshed rerun reaches a newer blocker after the docs-test
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
  - `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov -k "mre2e or gagov or docs or lexical or force_full or python or trace or bounded"`
  - `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_repository_commands.py -q --no-cov -k "mre2e or gagov or docs or force_full or interrupted or boundary or python"`
  - `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
- Whole-phase checks:
  - `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_repository_commands.py tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
  - `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  - `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - `sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'`
  - `git diff --check`
  - `git diff --cached --check`

## Acceptance Criteria

- [ ] A refreshed repo-local force-full rerun on the post-SEMARCHIVEWALKGAP
      head either advances durably beyond
      `tests/docs/test_mre2e_evidence_contract.py ->
      tests/docs/test_gagov_governance_contract.py` or emits a truthful newer
      blocker before the 120-second watchdog expires.
- [ ] The repair stays narrowly scoped to the docs-test contract pair and the
      immediate dispatcher/trace/status plumbing needed to prove it.
- [ ] If either docs-test file is bounded or otherwise short-circuited, the
      durable trace and `repository status` surfaces explain that exact
      docs-test outcome truthfully instead of falling back to stale generic
      Python or archive-tail wording.
- [ ] Lexical file storage and discoverability remain intact for the exact
      docs-test path(s) touched by the repair.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMARCHIVEWALKGAP rerun outcome and the final live verdict for the
      docs-test blocker.

automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMDOCGOV.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMDOCGOV.md
  artifact_state: staged
