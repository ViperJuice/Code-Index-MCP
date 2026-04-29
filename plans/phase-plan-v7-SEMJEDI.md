---
phase_loop_plan_version: 1
phase: SEMJEDI
roadmap: specs/phase-plans-v7.md
roadmap_sha256: b2065c49ecb72a5aa5856a30fa37f1ef75fc33e33c911bbd2aeeffeaed176f49
---
# SEMJEDI: Jedi AI Doc Lexical Recovery

## Context

SEMJEDI is the phase-29 contingency follow-up for the v7 semantic hardening
roadmap. SEMVISUALREPORT proved the exact bounded Python repair for
`scripts/create_multi_repo_visual_report.py`, but the live repo-local
force-full rerun still did not complete and the durable lexical progress
marker advanced to `ai_docs/jedi.md`.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is tracked and clean in this worktree, and its
  live SHA matches the required
  `b2065c49ecb72a5aa5856a30fa37f1ef75fc33e33c911bbd2aeeffeaed176f49`.
- The checkout is on `main` at `1ee1969`, `main...origin/main` is ahead by
  `53` commits, the worktree is clean before writing this artifact, and
  `plans/phase-plan-v7-SEMJEDI.md` did not exist before this run.
- `plans/phase-plan-v7-SEMVISUALREPORT.md` already exists as the direct
  upstream v7 phase plan, and `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
  already records SEMVISUALREPORT acceptance plus roadmap steering to
  `SEMJEDI` as the nearest downstream phase.
- The current dogfood report's SEMVISUALREPORT evidence snapshot records a
  durable `force_full_exit_trace.json` with `stage=lexical_walking`,
  `stage_family=lexical`, `blocker_source=lexical_mutation`, and
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/ai_docs/jedi.md`.
  The same report still shows `chunk_summaries = 0` and `semantic_points = 0`,
  so semantic-stage work has not started.
- `ai_docs/jedi.md` is a tracked Markdown document of `1096` lines and about
  `35.2KB` (`35239` bytes). It is not large enough to trigger the current
  `_LIGHTWEIGHT_MARKDOWN_BYTES = 250_000` fast path by size alone.
- `MarkdownPlugin._resolve_lightweight_reason(...)` currently has bounded
  Markdown rules for changelogs, roadmaps/phase plans, analysis reports,
  `AGENTS.md`, `README.md`, and `ai_docs/*_overview.md`. There is no exact
  bounded rule today for `ai_docs/jedi.md` or a narrower Jedi-reference class.
- `tests/test_dispatcher.py` and
  `tests/root_tests/test_markdown_production_scenarios.py` already cover the
  existing bounded Markdown contracts and the exact visual-report Python
  boundary, so SEMJEDI can extend the same bounded-indexing pattern without
  inventing a new lexical architecture.
- `mcp_server/cli/repository_commands.py` currently prints the fast-test
  report boundary, the `ai_docs/*_overview.md` bounded Markdown boundary, the
  exact visual-report Python boundary, and the durable force-full exit trace.
  It does not yet explain a Jedi-specific bounded Markdown repair or a later
  downstream blocker after `ai_docs/jedi.md`.

Practical planning boundary:

- SEMJEDI may introduce one exact repair for `ai_docs/jedi.md`: an exact
  bounded Markdown path in the plugin layer, a minimal file-local source
  simplification that lets the normal Markdown path complete under the current
  watchdog, or the smallest combination needed to carry the live force-full
  rerun beyond this seam.
- SEMJEDI must keep the repair narrow and evidence-driven. It must not add a
  broad `ai_docs/*.md` rule, a repo-wide Markdown fast path, a global lexical
  timeout increase, or unrelated semantic/ranking/release work.

## Interface Freeze Gates

- [ ] IF-0-SEMJEDI-1 - Exact Jedi blocker contract: repo-local
      `mcp-index repository sync --force-full` no longer leaves the durable
      lexical trace on `ai_docs/jedi.md`, and the repair is explicitly tied to
      that file or a stricter documentation class it belongs to.
- [ ] IF-0-SEMJEDI-2 - Bounded Markdown handling contract: the chosen repair
      preserves lexical discoverability for `ai_docs/jedi.md` through stored
      file content plus document and heading symbols; it does not introduce a
      broad `ai_docs/*.md`, `*.md`, or repository-wide Markdown ignore or
      fast-path bypass.
- [ ] IF-0-SEMJEDI-3 - Markdown watchdog preservation contract: the Markdown
      heavy-path timeout watchdog remains active for unrelated Markdown files,
      and the existing changelog, roadmap, analysis-report, `AGENTS.md`,
      `README.md`, `ai_docs/*_overview.md`, and visual-report-script boundaries
      remain intact.
- [ ] IF-0-SEMJEDI-4 - Force-full downstream handoff contract: after the
      repair, a repo-local force-full rerun advances beyond `ai_docs/jedi.md`
      and either reaches a later lexical or semantic stage or names a new
      exact downstream blocker that is narrower than the current Jedi seam.
- [ ] IF-0-SEMJEDI-5 - Status and evidence contract:
      `uv run mcp-index repository status` and
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` record the chosen Jedi repair,
      the rerun command and outcome, the refreshed durable trace, and whether
      semantic-stage work finally begins or a still-narrower downstream
      blocker remains.
- [ ] IF-0-SEMJEDI-6 - Upstream-boundary preservation contract: SEMFASTREPORT,
      SEMPYTESTOVERVIEW, and SEMVISUALREPORT remain closed as explicit upstream
      boundaries and are not reopened unless the rerun produces new direct
      evidence.

## Lane Index & Dependencies

- SL-0 - Jedi Markdown timeout contract and fixture freeze; Depends on: SEMVISUALREPORT; Blocks: SL-1, SL-2, SL-3; Parallel-safe: no
- SL-1 - Exact Jedi Markdown repair at plugin or source layer; Depends on: SL-0; Blocks: SL-2, SL-3; Parallel-safe: no
- SL-2 - Force-full lexical handoff and repository-status clarity; Depends on: SL-0, SL-1; Blocks: SL-3; Parallel-safe: no
- SL-3 - Dogfood evidence reducer and rerun refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SEMJEDI acceptance; Parallel-safe: no

Lane DAG:

```text
SEMVISUALREPORT
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SEMJEDI acceptance
```

## Lanes

### SL-0 - Jedi Markdown Timeout Contract And Fixture Freeze

- **Scope**: Freeze the exact `ai_docs/jedi.md` lexical seam before
  implementation so this phase proves a bounded Jedi repair instead of only
  moving the live timeout somewhere less visible.
- **Owned files**: `tests/test_dispatcher.py`, `tests/test_git_index_manager.py`, `tests/test_repository_commands.py`, `tests/root_tests/test_markdown_production_scenarios.py`
- **Interfaces provided**: executable assertions for IF-0-SEMJEDI-1 through
  IF-0-SEMJEDI-4
- **Interfaces consumed**: existing `MarkdownPlugin.indexFile(...)`,
  `MarkdownPlugin._resolve_lightweight_reason(...)`,
  `MarkdownPlugin._build_lightweight_index_shard(...)`,
  `EnhancedDispatcher.index_directory(...)`,
  `GitAwareIndexManager.sync_repository_index(...)`,
  `repository status` force-full trace rendering, and the tracked
  `ai_docs/jedi.md` file shape from the current checkout
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` with a deterministic
    `ai_docs/jedi.md` fixture that freezes the current seam and proves the
    repaired path finishes lexical indexing for that file without suppressing
    the watchdog for unrelated Markdown files.
  - test: Extend `tests/root_tests/test_markdown_production_scenarios.py` so
    the chosen exact bounded repair preserves document and heading symbol
    discoverability for `ai_docs/jedi.md`, records an explicit lightweight
    reason when applicable, and does not silently broaden to unrelated
    `ai_docs/*.md` content.
  - test: Extend `tests/test_git_index_manager.py` so a force-full rerun
    proves the durable trace no longer reports `ai_docs/jedi.md` as the active
    lexical blocker after the repair while still refusing to advance the
    indexed commit for a genuine downstream blocker.
  - test: Extend `tests/test_repository_commands.py` so `repository status`
    continues to render the fast-report, overview-doc, and visual-report
    boundaries while explaining the Jedi repair or the new downstream blocker
    narrowly.
  - impl: Keep fixtures deterministic with monkeypatched plugin or dispatcher
    behavior and repo-local doc-shaped content rather than long live waits
    inside unit coverage.
  - impl: Keep this lane focused on contract freeze. Do not update live
    dogfood evidence or rerun the force-full command here.
  - verify: `uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_repository_commands.py tests/root_tests/test_markdown_production_scenarios.py -q --no-cov`

### SL-1 - Exact Jedi Markdown Repair At Plugin Or Source Layer

- **Scope**: Implement one exact recovery for `ai_docs/jedi.md` so Markdown
  lexical indexing can finish under the live watchdog without weakening the
  repo-wide document indexing posture.
- **Owned files**: `mcp_server/plugins/markdown_plugin/plugin.py`, `ai_docs/jedi.md`
- **Interfaces provided**: IF-0-SEMJEDI-1 exact Jedi blocker contract;
  IF-0-SEMJEDI-2 bounded Markdown handling contract;
  IF-0-SEMJEDI-3 Markdown watchdog preservation contract at the repair point
- **Interfaces consumed**: SL-0 Jedi timeout tests; existing
  `_resolve_lightweight_reason(...)`, lightweight symbol extraction, full
  Markdown AST and chunking path, and the current content shape of
  `ai_docs/jedi.md`
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 Markdown slice first and confirm the current Jedi
    fixture still takes the standard Markdown indexing path that leaves this
    file as the durable lexical progress marker.
  - impl: Choose one singular repair surface and keep it explicit: either add
    an exact bounded Markdown rule for `ai_docs/jedi.md` inside the plugin
    layer, or make the smallest file-local source simplification that lets the
    normal Markdown indexing path complete under the existing watchdog.
  - impl: Preserve stored file rows plus document and heading symbol
    discoverability for `ai_docs/jedi.md`; the repair must not turn the file
    into an ignored source document or silently remove it from lexical FTS.
  - impl: Keep the repair exact-file or exact-file-class narrow. Do not add a
    broad `ai_docs/*.md`, `docs/**/*.md`, or repository-wide Markdown chunking
    bypass.
  - impl: If a file-local documentation edit is chosen, preserve the Jedi
    reference content and avoid opportunistic formatting churn. This phase is
    about lexical recoverability, not documentation redesign.
  - verify: `uv run pytest tests/root_tests/test_markdown_production_scenarios.py tests/test_dispatcher.py -q --no-cov`

### SL-2 - Force-Full Lexical Handoff And Repository-Status Clarity

- **Scope**: Carry the chosen Jedi repair through force-full closeout and keep
  the operator-facing status surface aligned with the exact repair that was
  made.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `mcp_server/storage/git_index_manager.py`, `mcp_server/cli/repository_commands.py`
- **Interfaces provided**: IF-0-SEMJEDI-4 force-full downstream handoff
  contract; IF-0-SEMJEDI-5 repository-status clarity contract
- **Interfaces consumed**: SL-0 dispatcher/git-index-manager/status fixtures;
  SL-1 chosen Jedi repair; existing lexical progress snapshot fields, durable
  `force_full_exit_trace.json` persistence, and the current SEMFASTREPORT /
  SEMPYTESTOVERVIEW / SEMVISUALREPORT status wording for earlier boundaries
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 git-index-manager and repository-status slice first and
    keep the durable trace vocabulary stable while moving the lexical handoff
    forward from `ai_docs/jedi.md`.
  - impl: Thread the chosen repair through the dispatcher and git-index-manager
    only as needed so the rerun can advance beyond `ai_docs/jedi.md`.
  - impl: Preserve the existing force-full trace fields, fail-closed
    indexed-commit behavior, and lexical watchdog semantics. This lane should
    move the handoff forward, not rename stages or declare readiness early.
  - impl: Tighten `repository status` only as needed so operators can tell
    whether the Jedi file now uses an exact bounded Markdown path, completed
    normally, or exposed a new exact downstream blocker.
  - impl: If SL-1 alone is sufficient and no runtime code change is required,
    record that no-op outcome in execution notes and keep this lane scoped to
    status wording plus live rerun proof.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov`
  - verify: `env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - verify: `python - <<'PY'
from pathlib import Path
print((Path(".mcp-index") / "force_full_exit_trace.json").read_text())
PY`

### SL-3 - Dogfood Evidence Reducer And Rerun Refresh

- **Scope**: Refresh the repo-local dogfood report so it records the chosen
  Jedi repair, the rerun outcome, and the next exact downstream status after
  this Markdown seam is cleared.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: IF-0-SEMJEDI-5 status and evidence contract;
  IF-0-SEMJEDI-6 upstream-boundary preservation contract
- **Interfaces consumed**: SL-1 chosen Jedi repair; SL-2 rerun command,
  durable trace, and repository-status wording; roadmap SEMJEDI exit criteria;
  prior SEMFASTREPORT, SEMPYTESTOVERVIEW, and SEMVISUALREPORT evidence lineage
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/docs/test_semdogfood_evidence_contract.py` so the
    refreshed report cites `plans/phase-plan-v7-SEMJEDI.md`, the chosen
    `ai_docs/jedi.md` repair, the rerun outcome, and whether the repo advanced
    beyond lexical walking or exposed a new exact downstream blocker.
  - test: Require the report to preserve the existing fast-test report,
    `ai_docs/*_overview.md`, and exact visual-report-script evidence lineage
    while making clear that none of those upstream seams is the active blocker
    anymore.
  - test: Require the refreshed report to state whether semantic-stage work
    finally began or which narrower blocker replaced `ai_docs/jedi.md`.
  - impl: Refresh `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` with the new live
    rerun command, trace snapshot, repository-status output, and the steering
    verdict after the Jedi seam is cleared.
  - impl: Keep the report factual and durable. Record observed commit IDs,
    trace timestamps, stage family, blocker source, and chunk/vector counts
    without claiming semantic success before the evidence exists.
  - impl: If the rerun exposes a new downstream blocker, state it exactly and
    make clear that SEMJEDI itself is complete because the active seam moved
    past `ai_docs/jedi.md`.
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
  - verify: `rg -n "SEMJEDI|ai_docs/jedi.md|force_full_exit_trace|Trace stage|Trace blocker source|semantic-stage|downstream blocker" docs/status/SEMANTIC_DOGFOOD_REBUILD.md tests/docs/test_semdogfood_evidence_contract.py`

## Verification

Planning-only run: do not execute these during plan creation. Run them during
`codex-execute-phase` or manual SEMJEDI execution.

Lane-specific checks:

```bash
uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_repository_commands.py tests/root_tests/test_markdown_production_scenarios.py -q --no-cov
uv run pytest tests/root_tests/test_markdown_production_scenarios.py tests/test_dispatcher.py -q --no-cov
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
rg -n "jedi.md|lightweight_reason|force_full_exit_trace|Lexical boundary|SEMJEDI" \
  mcp_server/plugins/markdown_plugin/plugin.py \
  mcp_server/dispatcher/dispatcher_enhanced.py \
  mcp_server/storage/git_index_manager.py \
  mcp_server/cli/repository_commands.py \
  docs/status/SEMANTIC_DOGFOOD_REBUILD.md \
  tests/test_dispatcher.py \
  tests/test_git_index_manager.py \
  tests/test_repository_commands.py \
  tests/root_tests/test_markdown_production_scenarios.py \
  tests/docs/test_semdogfood_evidence_contract.py
```

Whole-phase regression commands:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest \
  tests/test_dispatcher.py \
  tests/test_git_index_manager.py \
  tests/test_repository_commands.py \
  tests/root_tests/test_markdown_production_scenarios.py \
  tests/docs/test_semdogfood_evidence_contract.py \
  -q --no-cov
env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
python - <<'PY'
from pathlib import Path
print((Path(".mcp-index") / "force_full_exit_trace.json").read_text())
PY
sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'
git status --short -- specs/phase-plans-v7.md plans/phase-plan-v7-SEMJEDI.md
```

## Acceptance Criteria

- [ ] A live repo-local force-full rerun no longer leaves the durable trace on
      `ai_docs/jedi.md`.
- [ ] The chosen repair for `ai_docs/jedi.md` stays narrow, tested, and does
      not reopen the visual-report-script, `ai_docs/*_overview.md`,
      fast-report, README, roadmap, changelog, analysis-report, or
      `AGENTS.md` lexical boundaries without direct evidence.
- [ ] `ai_docs/jedi.md` remains lexically discoverable through stored file
      content plus document and heading symbols after the repair.
- [ ] Repository status and the durable force-full trace make clear whether the
      Jedi file now uses an exact bounded Markdown path, completed normally, or
      exposed a new exact downstream blocker.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is refreshed with the rerun
      outcome and either semantic-stage advancement or the next exact
      downstream blocker after `ai_docs/jedi.md`.
- [ ] Tests prove the repair is exact-path narrow and preserves watchdog
      coverage for unrelated Markdown files.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v7-SEMJEDI.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMJEDI.md
  artifact_state: staged
```
