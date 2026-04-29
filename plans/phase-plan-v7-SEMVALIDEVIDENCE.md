---
phase_loop_plan_version: 1
phase: SEMVALIDEVIDENCE
roadmap: specs/phase-plans-v7.md
roadmap_sha256: f7c0adf3a7a81b2503fc08d546623a67456817324cf409adfc5043d2cfba6f7d
---
# SEMVALIDEVIDENCE: Validation Evidence Lexical Recovery

## Context

SEMVALIDEVIDENCE is the phase-43 follow-up for the v7 semantic hardening
roadmap. SEMQUICKCHARTS closed out on the canonical `.phase-loop/` line, but
the refreshed repo-local force-full rerun still timed out in lexical walking
on the later validation-doc pair
`docs/validation/ga-closeout-decision.md ->
docs/validation/mre2e-evidence.md`.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is the active roadmap, it is tracked and clean in
  this worktree, and its live SHA matches the required
  `f7c0adf3a7a81b2503fc08d546623a67456817324cf409adfc5043d2cfba6f7d`.
- Canonical phase-loop state exists under `.phase-loop/`; `.phase-loop/state.json`
  and `.phase-loop/tui-handoff.md` both mark `SEMVALIDEVIDENCE` as the current
  unplanned phase after `SEMQUICKCHARTS` closed out with verification passed,
  a clean worktree, and `main...origin/main [ahead 81]`. Legacy
  `.codex/phase-loop/` artifacts are compatibility-only and are not
  authoritative for this run.
- The target artifact `plans/phase-plan-v7-SEMVALIDEVIDENCE.md` did not exist
  before this planning run.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is the active evidence anchor. Its
  latest SEMQUICKCHARTS refresh records that the rerun terminalized at
  `2026-04-29T13:16:35Z`, the durable running trace last refreshed at
  `2026-04-29T13:16:25Z`, the rerun exited with code `124`, and the durable
  trace truthfully terminalized to `status=interrupted`,
  `stage=lexical_walking`, `stage_family=lexical`,
  `blocker_source=lexical_mutation`,
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/docs/validation/ga-closeout-decision.md`,
  and
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/docs/validation/mre2e-evidence.md`.
- The same evidence records `repository status` already advertising the prior
  visualization repair
  (`Lexical boundary: using exact bounded Python indexing for mcp_server/visualization/quick_charts.py`)
  and SQLite runtime counts after the rerun of
  `files = 1114`, `code_chunks = 28182`, `chunk_summaries = 0`, and
  `semantic_points = 0`. The repo therefore still fails before semantic
  summary/vector closeout begins.
- The active validation docs are small but exact-path specific:
  `docs/validation/ga-closeout-decision.md` is `2740` bytes and
  `docs/validation/mre2e-evidence.md` is `5041` bytes. Both are historical
  evidence artifacts under `docs/validation/`, not generated throwaways.
- `mcp_server/plugins/markdown_plugin/plugin.py` already has a bounded
  Markdown path surface through `_resolve_lightweight_reason(...)` and
  `_build_lightweight_index_shard(...)`, but today it only fast-paths
  changelog/release notes, roadmap/phase-plan docs, analysis/report docs,
  `AGENTS.md`, `README.md`, `ai_docs/*_overview.md`, and `ai_docs/jedi.md`.
  There is no exact bounded path yet for either validation doc.
- `mcp_server/cli/repository_commands.py` currently prints lexical boundary
  lines for the older bounded Markdown and Python seams, including
  `ai_docs/*_overview.md`, `ai_docs/jedi.md`,
  `scripts/create_multi_repo_visual_report.py`,
  `scripts/quick_mcp_vs_native_validation.py`,
  `tests/test_artifact_publish_race.py`,
  `mcp_server/visualization/quick_charts.py`, and
  `.devcontainer/devcontainer.json`, but it does not yet surface a matching
  validation-doc boundary.
- `tests/test_dispatcher.py` already freezes bounded Markdown behavior for
  `ai_docs/*_overview.md` and `ai_docs/jedi.md`, while
  `tests/test_git_index_manager.py`, `tests/test_repository_commands.py`, and
  `tests/docs/test_semdogfood_evidence_contract.py` already freeze the later
  lexical-pair trace and dogfood evidence patterns for adjacent phases. The
  validation-doc pair can extend those exact surfaces instead of inventing a
  new recovery path.

Practical planning boundary:

- SEMVALIDEVIDENCE may implement one exact recovery for
  `docs/validation/ga-closeout-decision.md ->
  docs/validation/mre2e-evidence.md`: an exact bounded Markdown indexing path,
  the smallest doc-local simplification inside that pair, or the minimum
  combination needed to move the live rerun durably beyond this seam.
- SEMVALIDEVIDENCE must stay narrow and evidence-driven. It must not widen
  into a broad `docs/validation/*.md` bypass, repo-wide Markdown lightweight
  mode, semantic-closeout work, or reopening earlier visualization/Python/JSON
  seams unless the refreshed rerun directly reaches a newer blocker after this
  validation-doc pair is cleared.

## Interface Freeze Gates

- [ ] IF-0-SEMVALIDEVIDENCE-1 - Exact validation-doc recovery contract:
      a refreshed repo-local `repository sync --force-full` no longer leaves
      the durable lexical trace on
      `docs/validation/ga-closeout-decision.md ->
      docs/validation/mre2e-evidence.md`; it either advances durably beyond
      `docs/validation/mre2e-evidence.md` or emits a truthful newer blocker
      before the 120-second watchdog expires.
- [ ] IF-0-SEMVALIDEVIDENCE-2 - Bounded Markdown repair contract: the chosen
      repair remains limited to the exact validation-doc pair and the immediate
      markdown/status/trace plumbing needed to prove it; it does not broaden
      into arbitrary `docs/validation/*.md`, repo-wide Markdown lightweight
      mode, or a global lexical-timeout retune.
- [ ] IF-0-SEMVALIDEVIDENCE-3 - Lexical discoverability contract: the repaired
      path keeps both validation docs represented in stored file content and
      preserves the document/title and heading symbol surface needed for
      repo-local lexical search and definitions, even if heavyweight Markdown
      chunking is reduced or bypassed.
- [ ] IF-0-SEMVALIDEVIDENCE-4 - Trace and operator truthfulness contract:
      `force_full_exit_trace.json`, `GitAwareIndexManager`, and
      `uv run mcp-index repository status` agree on the repaired
      validation-doc outcome and do not regress earlier exact boundary wording
      for `ai_docs/*_overview.md`, `ai_docs/jedi.md`,
      `scripts/create_multi_repo_visual_report.py`,
      `scripts/quick_mcp_vs_native_validation.py`,
      `tests/test_artifact_publish_race.py`,
      `mcp_server/visualization/quick_charts.py`, or
      `.devcontainer/devcontainer.json`.
- [ ] IF-0-SEMVALIDEVIDENCE-5 - Evidence contract:
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the SEMQUICKCHARTS
      rerun outcome, the repaired SEMVALIDEVIDENCE rerun command and
      timestamps, the refreshed durable trace/status output, and the final
      authoritative verdict for the validation-doc blocker.
- [ ] IF-0-SEMVALIDEVIDENCE-6 - Upstream/downstream preservation contract:
      SEMQUICKCHARTS and the earlier exact bounded seams remain historically
      valid and closed unless the refreshed rerun directly re-anchors on a
      different later blocker after the validation-doc pair is cleared.

## Lane Index & Dependencies

- SL-0 - Validation-doc timeout contract and fixture freeze; Depends on: SEMQUICKCHARTS; Blocks: SL-1, SL-2, SL-3; Parallel-safe: no
- SL-1 - Exact validation-doc bounded recovery or minimal doc-local simplification; Depends on: SL-0; Blocks: SL-2, SL-3; Parallel-safe: no
- SL-2 - Force-full trace and repository-status alignment; Depends on: SL-0, SL-1; Blocks: SL-3; Parallel-safe: no
- SL-3 - Live rerun evidence reducer and closeout refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SEMVALIDEVIDENCE acceptance; Parallel-safe: no

Lane DAG:

```text
SEMQUICKCHARTS
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SEMVALIDEVIDENCE acceptance
```

## Lanes

### SL-0 - Validation-Doc Timeout Contract And Fixture Freeze

- **Scope**: Freeze the exact
  `docs/validation/ga-closeout-decision.md ->
  docs/validation/mre2e-evidence.md` lexical seam in unit coverage so this
  phase proves a bounded validation-doc repair instead of only moving the live
  timeout somewhere less visible.
- **Owned files**: `tests/test_dispatcher.py`, `tests/test_git_index_manager.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMVALIDEVIDENCE-1,
  IF-0-SEMVALIDEVIDENCE-2,
  IF-0-SEMVALIDEVIDENCE-3,
  and IF-0-SEMVALIDEVIDENCE-6
- **Interfaces consumed**: existing
  `EnhancedDispatcher.index_directory(...)`,
  `MarkdownPlugin.indexFile(...)`,
  `MarkdownPlugin._resolve_lightweight_reason(...)`,
  `MarkdownPlugin._build_lightweight_index_shard(...)`,
  `GitAwareIndexManager._make_force_full_progress_callback(...)`,
  `GitAwareIndexManager.sync_repository_index(...)`,
  and the current SEMQUICKCHARTS evidence wording for the validation-doc pair
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` with repo-shaped fixtures for
    `docs/validation/ga-closeout-decision.md` and
    `docs/validation/mre2e-evidence.md` that prove the repaired path preserves
    stored file rows, document/title symbols, heading symbols, and FTS-backed
    file content while avoiding the heavy Markdown path for that exact pair.
  - test: Freeze negative assertions in `tests/test_dispatcher.py` so earlier
    bounded Markdown seams (`ai_docs/*_overview.md`, `ai_docs/jedi.md`) and
    the earlier visualization/Python seams do not silently regress while this
    pair is added.
  - test: Extend `tests/test_git_index_manager.py` so durable force-full trace
    persistence freezes the validation-doc pair as
    `last_progress_path -> in_flight_path`, preserves truthful interrupted
    finalization semantics, and requires the final durable trace to move past
    `docs/validation/mre2e-evidence.md` or expose a newer later blocker.
  - impl: Use synthetic dispatcher progress and durable-trace payloads rather
    than a live multi-minute rerun inside unit coverage.
  - impl: Keep this lane focused on contract freeze only. Do not update
    operator-status wording or the dogfood evidence artifact here.
  - verify: `uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov -k "validation or markdown or lexical or force_full or trace or bounded or mre2e or ga_closeout"`

### SL-1 - Exact Validation-Doc Bounded Recovery Or Minimal Doc-Local Simplification

- **Scope**: Implement the smallest exact repair needed so the later
  validation-doc pair can complete lexical indexing under the existing
  watchdog without broadening repo-wide Markdown behavior.
- **Owned files**: `mcp_server/plugins/markdown_plugin/plugin.py`, `docs/validation/ga-closeout-decision.md`, `docs/validation/mre2e-evidence.md`
- **Interfaces provided**: IF-0-SEMVALIDEVIDENCE-1 exact validation-doc
  recovery contract; IF-0-SEMVALIDEVIDENCE-2 bounded Markdown repair
  contract; IF-0-SEMVALIDEVIDENCE-3 lexical discoverability contract
- **Interfaces consumed**: SL-0 validation-doc fixtures; existing
  `_resolve_lightweight_reason(...)`,
  `_build_lightweight_index_shard(...)`,
  the current heading/frontmatter structure in
  `docs/validation/ga-closeout-decision.md`,
  and the current heading/frontmatter structure in
  `docs/validation/mre2e-evidence.md`
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 dispatcher and git-index-manager slices first and
    confirm the current checkout still reproduces the later validation-doc seam
    or leaves the exact repair path unimplemented.
  - impl: Determine whether the minimal repair belongs in the Markdown plugin
    exact bounded-path surface, the validation docs themselves, or the
    smallest combination required to let lexical indexing finish on
    `docs/validation/mre2e-evidence.md`.
  - impl: If a bounded-path repair is chosen, keep it exact to
    `docs/validation/ga-closeout-decision.md`,
    `docs/validation/mre2e-evidence.md`, or that immediate pair. Do not
    introduce a broad `docs/validation/*.md`, repository-wide Markdown
    lightweight mode, or a generic documentation exemption.
  - impl: If a doc-local simplification is chosen, preserve the historical
    evidence meaning, top-level headings, and link/citation intent of both
    validation artifacts. This phase is about lexical recoverability, not a
    rewrite of the validation record.
  - impl: Preserve lexical file storage and document/heading symbol
    discoverability for both validation docs; the repair must not turn either
    document into an ignored file or silently remove it from lexical FTS.
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "validation or markdown or mre2e or ga_closeout or bounded"`
  - verify: `rg -n "ga-closeout-decision|mre2e-evidence|_resolve_lightweight_reason|lightweight_reason|heading|title|validation" mcp_server/plugins/markdown_plugin/plugin.py docs/validation/ga-closeout-decision.md docs/validation/mre2e-evidence.md tests/test_dispatcher.py`

### SL-2 - Force-Full Trace And Repository-Status Alignment

- **Scope**: Carry the chosen validation-doc repair through durable trace
  closeout and keep the operator-facing status surface aligned with the exact
  later blocker or recovery outcome.
- **Owned files**: `mcp_server/storage/git_index_manager.py`, `mcp_server/cli/repository_commands.py`, `tests/test_repository_commands.py`
- **Interfaces provided**: IF-0-SEMVALIDEVIDENCE-4 trace and operator
  truthfulness contract; IF-0-SEMVALIDEVIDENCE-6 upstream/downstream
  preservation contract
- **Interfaces consumed**: SL-0 fixture vocabulary; SL-1 chosen repair; the
  current force-full trace writer/finalizer; `_print_ai_docs_overview_boundary(...)`;
  `_print_jedi_markdown_boundary(...)`; existing boundary helpers for the
  later Python/JSON seams; and the current lexical trace/status wording in
  `repository status`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_repository_commands.py` so `repository status`
    freezes the exact validation-doc pair and proves the repaired path either
    advances beyond `docs/validation/mre2e-evidence.md` or reports the real
    later blocker without falling back to stale-running wording or boundary
    copy from older phases.
  - impl: Thread the chosen validation-doc repair through durable trace
    writing and repository-status wording only as needed so operators can tell
    whether the pair now uses an exact bounded Markdown path, completed
    normally, or exposed a newer exact blocker.
  - impl: If SL-1 introduces an exact validation-doc bounded path, add only
    the matching minimal operator boundary line. If SL-1 resolves the seam
    through doc-local simplification alone, keep this lane limited to truthful
    trace/status rendering and do not add misleading boundary copy.
  - impl: Preserve the existing boundary lines for `ai_docs/*_overview.md`,
    `ai_docs/jedi.md`,
    `scripts/create_multi_repo_visual_report.py`,
    `scripts/quick_mcp_vs_native_validation.py`,
    `tests/test_artifact_publish_race.py`,
    `mcp_server/visualization/quick_charts.py`, and
    `.devcontainer/devcontainer.json`.
  - impl: Keep fail-closed semantics intact. If the live rerun still blocks,
    surface the true later blocker rather than claiming lexical or semantic
    readiness early.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_repository_commands.py -q --no-cov -k "validation or markdown or boundary or force_full or interrupted or mre2e or ga_closeout"`
  - verify: `rg -n "ga-closeout-decision|mre2e-evidence|Lexical boundary|Trace status|Trace stage|Trace blocker source|Last progress path|In-flight path|quick_charts|devcontainer" mcp_server/storage/git_index_manager.py mcp_server/cli/repository_commands.py tests/test_repository_commands.py`

### SL-3 - Live Rerun Evidence Reducer And Closeout Refresh

- **Scope**: Re-run the repaired repo-local force-full path, reduce the real
  outcome into the dogfood evidence artifact, and keep the closeout narrative
  aligned with the actual post-repair validation-doc rerun.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: IF-0-SEMVALIDEVIDENCE-5 evidence contract;
  IF-0-SEMVALIDEVIDENCE-6 upstream/downstream preservation contract
- **Interfaces consumed**: SL-0 fixture vocabulary; SL-1 chosen repair; SL-2
  rerun command, durable trace, and repository-status wording; current versus
  indexed commit evidence; SQLite runtime counts; and the current roadmap
  steering from `SEMQUICKCHARTS` to `SEMVALIDEVIDENCE`
- **Parallel-safe**: no
- **Tasks**:
  - test: Update `tests/docs/test_semdogfood_evidence_contract.py` so the
    report cites `plans/phase-plan-v7-SEMVALIDEVIDENCE.md`, preserves the
    earlier lexical-boundary lineage, and records the validation-doc rerun
    outcome.
  - test: Require the report to preserve the existing SEMQUICKCHARTS
    visualization evidence and make clear that the validation-doc pair, not
    `mcp_server/visualization/quick_charts.py`, is the active seam for this
    phase.
  - impl: Re-run the repo-local force-full command with the same strict
    watchdog posture used by the recent semantic dogfood phases and capture the
    resulting durable trace, status output, exit code or newer blocker
    classification, commit evidence, and runtime counts.
  - impl: Refresh `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` with the
    SEMQUICKCHARTS validation-doc evidence, the repaired SEMVALIDEVIDENCE
    rerun command, timestamps, `force_full_exit_trace.json` fields,
    repository-status lines, current-versus-indexed commit evidence, and the
    final verdict: either the rerun now moves durably beyond
    `docs/validation/mre2e-evidence.md`, or a newer exact blocker is named.
  - impl: If no broader docs are needed, record that decision in the status
    artifact rather than widening this phase into general documentation
    cleanup.
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
  - verify: `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - verify: `python - <<'PY'
from pathlib import Path
trace = Path(".mcp-index") / "force_full_exit_trace.json"
print(trace.read_text() if trace.exists() else "missing")
PY`
  - verify: `sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'`

## Verification

Planning-only work is complete once this artifact is written and staged. Do
not execute the commands below during plan creation; run them during
`codex-execute-phase` or manual SEMVALIDEVIDENCE execution.

Lane-specific checks:

```bash
uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov -k "validation or markdown or lexical or force_full or trace or bounded or mre2e or ga_closeout"
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_repository_commands.py -q --no-cov -k "validation or markdown or boundary or force_full or interrupted or mre2e or ga_closeout"
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
rg -n "ga-closeout-decision|mre2e-evidence|_resolve_lightweight_reason|lightweight_reason|Lexical boundary|Trace status|Trace stage|Trace blocker source|Last progress path|In-flight path|quick_charts|devcontainer" \
  mcp_server/plugins/markdown_plugin/plugin.py \
  mcp_server/storage/git_index_manager.py \
  mcp_server/cli/repository_commands.py \
  docs/validation/ga-closeout-decision.md \
  docs/validation/mre2e-evidence.md \
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
git status --short -- specs/phase-plans-v7.md plans/phase-plan-v7-SEMVALIDEVIDENCE.md docs/status/SEMANTIC_DOGFOOD_REBUILD.md
```

## Acceptance Criteria

- [ ] A refreshed repo-local force-full rerun on the post-SEMQUICKCHARTS head
      no longer leaves the durable lexical trace on
      `docs/validation/ga-closeout-decision.md ->
      docs/validation/mre2e-evidence.md`; it either advances beyond
      `docs/validation/mre2e-evidence.md` or fails closed with a truthful
      newer blocker before the 120-second watchdog expires.
- [ ] The repair remains bounded to the exact validation-doc pair and the
      immediate Markdown/status/trace plumbing needed to prove it, without
      broadening into `docs/validation/*.md`, repo-wide Markdown lightweight
      mode, or unrelated timeout retunes.
- [ ] Both validation docs remain discoverable through stored file content and
      preserve their document/heading symbol surface after the repair, even if
      heavyweight Markdown chunking is reduced.
- [ ] `force_full_exit_trace.json` and
      `uv run mcp-index repository status` agree on the repaired outcome and do
      not regress earlier exact boundary wording for
      `ai_docs/*_overview.md`, `ai_docs/jedi.md`,
      `scripts/create_multi_repo_visual_report.py`,
      `scripts/quick_mcp_vs_native_validation.py`,
      `tests/test_artifact_publish_race.py`,
      `mcp_server/visualization/quick_charts.py`, or
      `.devcontainer/devcontainer.json`.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` cites
      `plans/phase-plan-v7-SEMVALIDEVIDENCE.md` and records the
      SEMQUICKCHARTS validation-doc evidence, the repaired
      SEMVALIDEVIDENCE rerun, and the final authoritative blocker or
      advancement verdict.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v7-SEMVALIDEVIDENCE.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMVALIDEVIDENCE.md
  artifact_state: staged
```
