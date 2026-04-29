---
phase_loop_plan_version: 1
phase: SEMBENCHDOCS
roadmap: specs/phase-plans-v7.md
roadmap_sha256: 50b3025fd7f2aa0c08ecc34f64f4de343ddd4c4472a796c21e09b8ce2a2962a1
---
# SEMBENCHDOCS: Benchmark Evidence Lexical Recovery

## Context

SEMBENCHDOCS is the phase-44 follow-up for the v7 semantic hardening
roadmap. SEMVALIDEVIDENCE cleared the validation-doc seam, but the refreshed
live repo-local force-full rerun still remained in lexical walking on the
later benchmark-doc pair
`docs/benchmarks/mcp_vs_native_benchmark_fullrepo_fireworks_qwen_voyage_local_iter5_rerun.md ->
docs/benchmarks/production_benchmark.md`.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is the active roadmap, it is tracked and clean in
  this worktree, and its live SHA matches the required
  `50b3025fd7f2aa0c08ecc34f64f4de343ddd4c4472a796c21e09b8ce2a2962a1`.
- Canonical phase-loop state exists under `.phase-loop/`; `.phase-loop/state.json`
  and `.phase-loop/tui-handoff.md` both mark `SEMBENCHDOCS` as the current
  unplanned phase after `SEMVALIDEVIDENCE` closed out with verification
  passed on `78f9cf959c3c73f553317748752fcf94a292a8c1`, with
  `main...origin/main [ahead 83]` and no dirty paths. Legacy
  `.codex/phase-loop/` artifacts are compatibility-only and are not
  authoritative for this run.
- The target artifact `plans/phase-plan-v7-SEMBENCHDOCS.md` did not exist
  before this planning run.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is the active evidence anchor.
  Its latest SEMVALIDEVIDENCE refresh records that the live rerun
  terminalized at `2026-04-29T13:34:20Z`, the durable running trace last
  refreshed at `2026-04-29T13:34:05Z`, the rerun exited with code `124`, and
  the durable trace truthfully terminalized to `status=interrupted`,
  `stage=lexical_walking`, `stage_family=lexical`,
  `blocker_source=lexical_mutation`,
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/docs/benchmarks/mcp_vs_native_benchmark_fullrepo_fireworks_qwen_voyage_local_iter5_rerun.md`,
  and
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/docs/benchmarks/production_benchmark.md`.
- The same evidence records `repository status` already advertising the
  earlier exact validation boundaries while still surfacing the older sync
  error `disk I/O error`. The active blocker therefore remains the benchmark
  doc pair proven by the durable lexical trace, not a reopened validation-doc
  or storage-closeout hypothesis.
- The benchmark docs are small, tracked evidence artifacts rather than large
  hand-written manuals:
  `docs/benchmarks/mcp_vs_native_benchmark_fullrepo_fireworks_qwen_voyage_local_iter5_rerun.md`
  is `20` lines / `2048` bytes and
  `docs/benchmarks/production_benchmark.md` is `46` lines / `3510` bytes.
  Their size is far below `_LIGHTWEIGHT_MARKDOWN_BYTES = 250_000`, so the
  remaining seam is more likely an exact-path Markdown indexing issue than a
  generic large-document cutoff.
- `mcp_server/plugins/markdown_plugin/plugin.py` already has a bounded
  Markdown path surface through `_resolve_lightweight_reason(...)` and
  `_build_lightweight_index_shard(...)`, but today it only fast-paths
  changelog/release-note names, roadmap and phase-plan names, analysis/report
  names, `AGENTS.md`, `README.md`, `ai_docs/*_overview.md`, and the exact
  paths `ai_docs/jedi.md`,
  `docs/validation/ga-closeout-decision.md`, and
  `docs/validation/mre2e-evidence.md`. There is no exact bounded path yet for
  either benchmark doc.
- `mcp_server/cli/repository_commands.py` currently prints lexical boundary
  lines for the earlier fast-test report ignore rule, `ai_docs/*_overview.md`,
  `ai_docs/jedi.md`, the validation-doc pair,
  `scripts/create_multi_repo_visual_report.py`,
  `scripts/quick_mcp_vs_native_validation.py`,
  `tests/test_artifact_publish_race.py`,
  `mcp_server/visualization/quick_charts.py`, and
  `.devcontainer/devcontainer.json`, but it does not yet surface a matching
  benchmark-doc boundary.
- `tests/test_dispatcher.py`, `tests/test_git_index_manager.py`, and
  `tests/test_repository_commands.py` already freeze adjacent bounded Markdown
  and later exact-path trace/status contracts. Meanwhile
  `tests/docs/test_semdogfood_evidence_contract.py` already expects both
  benchmark doc paths and the downstream `SEMBENCHDOCS` steering inside
  `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`. This phase can extend those
  surfaces rather than inventing a new evidence artifact family.

Practical planning boundary:

- SEMBENCHDOCS may implement one exact recovery for
  `docs/benchmarks/mcp_vs_native_benchmark_fullrepo_fireworks_qwen_voyage_local_iter5_rerun.md ->
  docs/benchmarks/production_benchmark.md`: an exact bounded Markdown
  indexing path, the smallest doc-local simplification inside that pair, or
  the minimum combination needed to move the live rerun durably beyond this
  seam.
- SEMBENCHDOCS must stay narrow and evidence-driven. It must not widen into a
  broad `docs/benchmarks/*.md` bypass, repo-wide Markdown lightweight mode,
  semantic-closeout work, or reopening earlier validation/visualization/Python
  seams unless the refreshed rerun directly reaches a newer blocker after this
  benchmark-doc pair is cleared.

## Interface Freeze Gates

- [ ] IF-0-SEMBENCHDOCS-1 - Exact benchmark-doc recovery contract:
      a refreshed repo-local `repository sync --force-full` no longer leaves
      the durable lexical trace on
      `docs/benchmarks/mcp_vs_native_benchmark_fullrepo_fireworks_qwen_voyage_local_iter5_rerun.md ->
      docs/benchmarks/production_benchmark.md`; it either advances durably
      beyond `docs/benchmarks/production_benchmark.md` or emits a truthful
      newer blocker before the 120-second watchdog expires.
- [ ] IF-0-SEMBENCHDOCS-2 - Bounded Markdown repair contract: the chosen
      repair remains limited to the exact benchmark-doc pair and the
      immediate Markdown/status/trace plumbing needed to prove it; it does
      not broaden into arbitrary `docs/benchmarks/*.md`, repo-wide Markdown
      lightweight mode, or a global lexical-timeout retune.
- [ ] IF-0-SEMBENCHDOCS-3 - Lexical discoverability contract: the repaired
      path keeps both benchmark docs represented in stored file content and
      preserves the document/title and heading symbol surface needed for
      repo-local lexical search and definitions, even if heavyweight Markdown
      chunking is reduced or bypassed.
- [ ] IF-0-SEMBENCHDOCS-4 - Trace and operator truthfulness contract:
      `force_full_exit_trace.json`, `EnhancedDispatcher`,
      `GitAwareIndexManager`, and `uv run mcp-index repository status` agree
      on the repaired benchmark-doc outcome and do not regress earlier
      boundary wording for `fast_test_results/fast_report_*.md`,
      `ai_docs/*_overview.md`, `ai_docs/jedi.md`,
      `docs/validation/ga-closeout-decision.md`,
      `docs/validation/mre2e-evidence.md`,
      `scripts/create_multi_repo_visual_report.py`,
      `scripts/quick_mcp_vs_native_validation.py`,
      `tests/test_artifact_publish_race.py`,
      `mcp_server/visualization/quick_charts.py`, or
      `.devcontainer/devcontainer.json`.
- [ ] IF-0-SEMBENCHDOCS-5 - Evidence contract:
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMVALIDEVIDENCE rerun outcome, the repaired SEMBENCHDOCS rerun command
      and timestamps, the refreshed durable trace/status output, and the
      final authoritative verdict for the benchmark-doc blocker.
- [ ] IF-0-SEMBENCHDOCS-6 - Upstream/downstream preservation contract:
      SEMVALIDEVIDENCE and the earlier exact bounded seams remain historically
      valid and closed unless the refreshed rerun directly re-anchors on a
      different later blocker after the benchmark-doc pair is cleared.

## Lane Index & Dependencies

- SL-0 - Benchmark-doc timeout contract and fixture freeze; Depends on: SEMVALIDEVIDENCE; Blocks: SL-1, SL-2, SL-3; Parallel-safe: no
- SL-1 - Exact benchmark-doc bounded recovery or minimal doc-local simplification; Depends on: SL-0; Blocks: SL-2, SL-3; Parallel-safe: no
- SL-2 - Force-full trace and repository-status alignment; Depends on: SL-0, SL-1; Blocks: SL-3; Parallel-safe: no
- SL-3 - Live rerun evidence reducer and closeout refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SEMBENCHDOCS acceptance; Parallel-safe: no

Lane DAG:

```text
SEMVALIDEVIDENCE
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SEMBENCHDOCS acceptance
```

## Lanes

### SL-0 - Benchmark-Doc Timeout Contract And Fixture Freeze

- **Scope**: Freeze the exact
  `docs/benchmarks/mcp_vs_native_benchmark_fullrepo_fireworks_qwen_voyage_local_iter5_rerun.md ->
  docs/benchmarks/production_benchmark.md` lexical seam in unit coverage so
  this phase proves a bounded benchmark-doc repair instead of only moving the
  live timeout somewhere less visible.
- **Owned files**: `tests/test_dispatcher.py`, `tests/test_git_index_manager.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMBENCHDOCS-1,
  IF-0-SEMBENCHDOCS-2,
  IF-0-SEMBENCHDOCS-3,
  and IF-0-SEMBENCHDOCS-6
- **Interfaces consumed**: existing
  `EnhancedDispatcher.index_directory(...)`,
  `MarkdownPlugin.indexFile(...)`,
  `MarkdownPlugin._resolve_lightweight_reason(...)`,
  `MarkdownPlugin._build_lightweight_index_shard(...)`,
  `GitAwareIndexManager._make_force_full_progress_callback(...)`,
  `GitAwareIndexManager.sync_repository_index(...)`,
  and the current SEMVALIDEVIDENCE evidence wording for the benchmark-doc pair
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` with repo-shaped fixtures for
    `docs/benchmarks/mcp_vs_native_benchmark_fullrepo_fireworks_qwen_voyage_local_iter5_rerun.md`
    and `docs/benchmarks/production_benchmark.md` that prove the repaired
    path preserves stored file rows, document/title symbols, heading symbols,
    and FTS-backed file content while avoiding the heavy Markdown path for
    that exact pair.
  - test: Freeze negative assertions in `tests/test_dispatcher.py` so earlier
    bounded Markdown seams (`ai_docs/*_overview.md`, `ai_docs/jedi.md`, and
    the validation-doc pair) plus the later visualization/Python seams do not
    silently regress while this benchmark pair is added.
  - test: Extend `tests/test_git_index_manager.py` so durable force-full trace
    persistence freezes the benchmark-doc pair as
    `last_progress_path -> in_flight_path`, preserves truthful interrupted
    finalization semantics, and requires the final durable trace to move past
    `docs/benchmarks/production_benchmark.md` or expose a newer later blocker.
  - impl: Use synthetic dispatcher progress and durable-trace payloads rather
    than a live multi-minute rerun inside unit coverage.
  - impl: Keep this lane focused on contract freeze only. Do not update
    operator-status wording or the dogfood evidence artifact here.
  - verify: `uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov -k "benchmark or markdown or lexical or force_full or trace or bounded or production_benchmark or voyage_local_iter5_rerun"`

### SL-1 - Exact Benchmark-Doc Bounded Recovery Or Minimal Doc-Local Simplification

- **Scope**: Implement the smallest exact repair needed so the later
  benchmark-doc pair can complete lexical indexing under the existing
  watchdog without broadening repo-wide Markdown behavior.
- **Owned files**: `mcp_server/plugins/markdown_plugin/plugin.py`, `docs/benchmarks/mcp_vs_native_benchmark_fullrepo_fireworks_qwen_voyage_local_iter5_rerun.md`, `docs/benchmarks/production_benchmark.md`
- **Interfaces provided**: IF-0-SEMBENCHDOCS-1 exact benchmark-doc
  recovery contract; IF-0-SEMBENCHDOCS-2 bounded Markdown repair
  contract; IF-0-SEMBENCHDOCS-3 lexical discoverability contract
- **Interfaces consumed**: SL-0 benchmark-doc fixtures; existing
  `_resolve_lightweight_reason(...)`,
  `_build_lightweight_index_shard(...)`,
  the current heading/table structure in
  `docs/benchmarks/mcp_vs_native_benchmark_fullrepo_fireworks_qwen_voyage_local_iter5_rerun.md`,
  and the current heading/table structure in
  `docs/benchmarks/production_benchmark.md`
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 dispatcher and git-index-manager slices first and
    confirm the current checkout still reproduces the later benchmark-doc seam
    or leaves the exact repair path unimplemented.
  - impl: Determine whether the minimal repair belongs in the Markdown plugin
    exact bounded-path surface, the benchmark docs themselves, or the
    smallest combination required to let lexical indexing finish on
    `docs/benchmarks/production_benchmark.md`.
  - impl: If a bounded-path repair is chosen, keep it exact to
    `docs/benchmarks/mcp_vs_native_benchmark_fullrepo_fireworks_qwen_voyage_local_iter5_rerun.md`,
    `docs/benchmarks/production_benchmark.md`, or that immediate pair. Do not
    introduce a broad `docs/benchmarks/*.md`, repository-wide Markdown
    lightweight mode, or a generic documentation exemption.
  - impl: If a doc-local simplification is chosen, preserve the benchmark
    evidence meaning, top-level headings, and table/citation intent of both
    artifacts. This phase is about lexical recoverability, not a rewrite of
    the benchmark record.
  - impl: Preserve lexical file storage and document/heading symbol
    discoverability for both benchmark docs; the repair must not turn either
    document into an ignored file or silently remove it from lexical FTS.
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "benchmark or markdown or production_benchmark or voyage_local_iter5_rerun or bounded"`
  - verify: `rg -n "mcp_vs_native_benchmark_fullrepo_fireworks_qwen_voyage_local_iter5_rerun|production_benchmark|_resolve_lightweight_reason|lightweight_reason|benchmark" mcp_server/plugins/markdown_plugin/plugin.py docs/benchmarks/mcp_vs_native_benchmark_fullrepo_fireworks_qwen_voyage_local_iter5_rerun.md docs/benchmarks/production_benchmark.md tests/test_dispatcher.py`

### SL-2 - Force-Full Trace And Repository-Status Alignment

- **Scope**: Carry the chosen benchmark-doc repair through durable trace
  closeout and keep the operator-facing status surface aligned with the exact
  later blocker or recovery outcome.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `mcp_server/storage/git_index_manager.py`, `mcp_server/cli/repository_commands.py`, `tests/test_repository_commands.py`
- **Interfaces provided**: IF-0-SEMBENCHDOCS-4 trace and operator
  truthfulness contract; IF-0-SEMBENCHDOCS-6 upstream/downstream
  preservation contract
- **Interfaces consumed**: SL-0 fixture vocabulary; SL-1 chosen repair; the
  current force-full trace writer/finalizer; existing fast-report, ai-doc,
  validation-doc, visualization, and devcontainer boundary helpers; and the
  current lexical trace/status wording in `repository status`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_repository_commands.py` so `repository status`
    freezes the exact benchmark-doc pair and proves the repaired path either
    advances beyond `docs/benchmarks/production_benchmark.md` or reports the
    real later blocker without falling back to stale-running wording or
    boundary copy from older phases.
  - impl: Thread the chosen benchmark-doc repair through dispatcher progress,
    durable trace writing, and repository-status wording only as needed so
    operators can tell whether the pair now uses an exact bounded Markdown
    path, completed normally, or exposed a newer exact blocker.
  - impl: If SL-1 introduces an exact benchmark-doc bounded path, add only the
    matching minimal operator boundary line. If SL-1 resolves the seam through
    doc-local simplification alone, keep this lane limited to truthful
    trace/status rendering and do not add misleading boundary copy.
  - impl: Preserve the existing boundary lines for
    `fast_test_results/fast_report_*.md`,
    `ai_docs/*_overview.md`,
    `ai_docs/jedi.md`,
    `docs/validation/ga-closeout-decision.md`,
    `docs/validation/mre2e-evidence.md`,
    `scripts/create_multi_repo_visual_report.py`,
    `scripts/quick_mcp_vs_native_validation.py`,
    `tests/test_artifact_publish_race.py`,
    `mcp_server/visualization/quick_charts.py`, and
    `.devcontainer/devcontainer.json`.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "benchmark or boundary or force_full or interrupted or production_benchmark or voyage_local_iter5_rerun"`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - verify: `python - <<'PY'
from pathlib import Path
trace = Path(".mcp-index") / "force_full_exit_trace.json"
print(trace.read_text() if trace.exists() else "missing")
PY`

### SL-3 - Live Rerun Evidence Reducer And Closeout Refresh

- **Scope**: Re-run the repaired repo-local force-full sequence, reduce the
  outcome into the durable dogfood evidence artifact, and refresh the docs
  evidence contract so the benchmark-doc recovery and its downstream verdict
  are easy to distinguish from the earlier validation-doc blocker state.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: IF-0-SEMBENCHDOCS-5 evidence contract
- **Interfaces consumed**: SL-0 benchmark-doc seam wording; SL-1 benchmark
  repair; SL-2 rerun command, durable trace, and repository-status verdict;
  existing SEMVALIDEVIDENCE evidence sections and command-level verification
  format inside `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/docs/test_semdogfood_evidence_contract.py` so the
    status artifact must cite `plans/phase-plan-v7-SEMBENCHDOCS.md`, the
    benchmark-doc pair, the repaired rerun command and timestamps, the
    durable trace/status fields, and the final authoritative blocker or
    advancement verdict.
  - impl: Append a new SEMBENCHDOCS rerun section to
    `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` that records the
    SEMVALIDEVIDENCE benchmark-doc seam, the live rerun outcome on the new
    head, and whether the blocker moved beyond
    `docs/benchmarks/production_benchmark.md`.
  - impl: Keep the evidence artifact append-only and historically honest. Do
    not rewrite prior phase sections to imply that SEMVALIDEVIDENCE itself
    cleared the benchmark-doc pair.
  - impl: If the repaired rerun exposes a newer exact blocker, record that
    blocker precisely and mark older downstream assumptions stale instead of
    speculating about semantic closeout.
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
  - verify: `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - verify: `sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'`

## Verification

Lane-level verification during execution:

```bash
uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov -k "benchmark or markdown or lexical or force_full or trace or bounded or production_benchmark or voyage_local_iter5_rerun"
uv run pytest tests/test_dispatcher.py -q --no-cov -k "benchmark or markdown or production_benchmark or voyage_local_iter5_rerun or bounded"
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "benchmark or boundary or force_full or interrupted or production_benchmark or voyage_local_iter5_rerun"
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
rg -n "mcp_vs_native_benchmark_fullrepo_fireworks_qwen_voyage_local_iter5_rerun|production_benchmark|_resolve_lightweight_reason|lightweight_reason|Lexical boundary|Trace status|Trace stage|Trace blocker source|Last progress path|In-flight path|validation|quick_charts|fast_report" \
  mcp_server/plugins/markdown_plugin/plugin.py \
  mcp_server/dispatcher/dispatcher_enhanced.py \
  mcp_server/storage/git_index_manager.py \
  mcp_server/cli/repository_commands.py \
  docs/benchmarks/mcp_vs_native_benchmark_fullrepo_fireworks_qwen_voyage_local_iter5_rerun.md \
  docs/benchmarks/production_benchmark.md \
  tests/test_dispatcher.py \
  tests/test_git_index_manager.py \
  tests/test_repository_commands.py \
  tests/docs/test_semdogfood_evidence_contract.py
```

Whole-phase live verification after code changes:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest \
  tests/test_dispatcher.py \
  tests/test_git_index_manager.py \
  tests/test_repository_commands.py \
  tests/docs/test_semdogfood_evidence_contract.py \
  -q --no-cov
timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
python - <<'PY'
from pathlib import Path
trace = Path(".mcp-index") / "force_full_exit_trace.json"
print(trace.read_text() if trace.exists() else "missing")
PY
sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'
git status --short -- specs/phase-plans-v7.md plans/phase-plan-v7-SEMBENCHDOCS.md docs/status/SEMANTIC_DOGFOOD_REBUILD.md
```

## Acceptance Criteria

- [ ] A refreshed repo-local force-full rerun on the post-SEMVALIDEVIDENCE
      head no longer leaves the durable lexical trace on
      `docs/benchmarks/mcp_vs_native_benchmark_fullrepo_fireworks_qwen_voyage_local_iter5_rerun.md ->
      docs/benchmarks/production_benchmark.md`; it either advances beyond
      `docs/benchmarks/production_benchmark.md` or fails closed with a
      truthful newer blocker before the 120-second watchdog expires.
- [ ] The repair remains bounded to the exact benchmark-doc pair and the
      immediate Markdown/status/trace plumbing needed to prove it, without
      broadening into `docs/benchmarks/*.md`, repo-wide Markdown lightweight
      mode, or unrelated timeout retunes.
- [ ] Both benchmark docs remain discoverable through stored file content and
      preserve their document/heading symbol surface after the repair, even if
      heavyweight Markdown chunking is reduced.
- [ ] `force_full_exit_trace.json` and
      `uv run mcp-index repository status` agree on the repaired outcome and
      do not regress earlier boundary wording for
      `fast_test_results/fast_report_*.md`,
      `ai_docs/*_overview.md`,
      `ai_docs/jedi.md`,
      `docs/validation/ga-closeout-decision.md`,
      `docs/validation/mre2e-evidence.md`,
      `scripts/create_multi_repo_visual_report.py`,
      `scripts/quick_mcp_vs_native_validation.py`,
      `tests/test_artifact_publish_race.py`,
      `mcp_server/visualization/quick_charts.py`, or
      `.devcontainer/devcontainer.json`.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` cites
      `plans/phase-plan-v7-SEMBENCHDOCS.md` and records the
      SEMVALIDEVIDENCE benchmark-doc evidence, the repaired SEMBENCHDOCS
      rerun, and the final authoritative blocker or advancement verdict.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v7-SEMBENCHDOCS.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMBENCHDOCS.md
  artifact_state: staged
```
