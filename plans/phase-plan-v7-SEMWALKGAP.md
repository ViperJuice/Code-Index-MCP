---
phase_loop_plan_version: 1
phase: SEMWALKGAP
roadmap: specs/phase-plans-v7.md
roadmap_sha256: 6643ef1b16dd7077f5031a099b4d85fe5e7749ea5d33fa27ed1e122c83e33af7
---
# SEMWALKGAP: Post-Devcontainer Walk Gap Recovery

## Context

SEMWALKGAP is the phase-41 follow-up for the v7 semantic hardening roadmap.
SEMDEVRELAPSE proved the refreshed live repo-local force-full rerun still times
out with the durable trace re-anchored on `.devcontainer/devcontainer.json`,
but the walk-order evidence on the same head shows the next tail is no longer
purely devcontainer-file-local: it immediately includes
`fast_test_results/fast_report_20250628_193425.md` and then
`test_workspace/real_repos/search_scaling/package.json`.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is the active roadmap, it is tracked and clean in
  this worktree, and `sha256sum specs/phase-plans-v7.md` matches the required
  `6643ef1b16dd7077f5031a099b4d85fe5e7749ea5d33fa27ed1e122c83e33af7`.
- Canonical phase-loop state exists under `.phase-loop/`; `.phase-loop/state.json`
  and `.phase-loop/tui-handoff.md` both mark `SEMWALKGAP` as the current
  `unplanned` phase after `SEMDEVRELAPSE` closed out with verification
  `blocked`, a clean worktree, and `HEAD 869eea9302c687b7b4b496735de74e85a72e95f0`
  on `main...origin/main [ahead 77]`. Legacy `.codex/phase-loop/` artifacts
  are compatibility-only and are not authoritative for this run.
- The target artifact `plans/phase-plan-v7-SEMWALKGAP.md` did not exist before
  this planning run.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is the active evidence anchor. It
  already records the SEMDEVRELAPSE live rerun at `2026-04-29T12:19:54Z`, the
  post-timeout `repository status` rewrite at `2026-04-29T12:21:08Z`, the
  durable trace fields
  `Trace status: interrupted`,
  `Trace stage: lexical_walking`,
  `Trace blocker source: lexical_mutation`, and
  `Last progress path: /home/viperjuice/code/Code-Index-MCP/.devcontainer/devcontainer.json`,
  plus the walk-order probe showing
  `fast_test_results/fast_report_20250628_193425.md` followed by
  `test_workspace/real_repos/search_scaling/package.json`.
- The repo already has a narrow ignore contract for this tail. `.mcp-index-ignore`
  includes both `fast_test_results/fast_report_*.md` and `test_workspace/`,
  `tests/test_ignore_patterns.py` already freezes `IgnorePatternManager` and
  `build_walker_filter(...)` behavior for those patterns, and
  `tests/docs/test_semdogfood_evidence_contract.py` already requires the status
  artifact to mention both the fast-report family and the
  `test_workspace/real_repos/search_scaling/package.json` walk-order evidence.
- The current implementation seam is concrete. `mcp_server/dispatcher/dispatcher_enhanced.py`
  constructs `is_excluded = build_walker_filter(directory)` inside
  `index_directory(...)`, but the recursive `os.walk(...)` path currently does
  not apply that filter to files or non-core ignored directories before lexical
  indexing. The comment above the walk still says ignore patterns are not used
  during indexing, which matches the observed walk-gap evidence better than the
  already-closed `.devcontainer` rebound story.
- Existing coverage is partial but not yet sufficient for this phase.
  `tests/test_dispatcher.py` freezes the generated fast-report family skip,
  `tests/test_git_index_manager.py` freezes that skipped family staying out of
  the durable trace, and `tests/test_repository_commands.py` prints the
  fast-report boundary. The dispatcher, trace, and status surfaces do not yet
  freeze the combined post-devcontainer tail where both the fast-report family
  and the ignored `test_workspace/` subtree must be skipped before the next
  authoritative later path becomes visible.
- `mcp_server/storage/git_index_manager.py` remains the authoritative durable
  trace writer, and `mcp_server/cli/repository_commands.py` remains the
  operator-facing truth surface. This phase should keep both aligned with the
  repaired walker behavior so the next blocker is either a later exact indexed
  path or an explicit bounded exclusion, not another misleading
  `.devcontainer/devcontainer.json` re-anchor.

Practical planning boundary:

- SEMWALKGAP may tighten recursive walker filtering, lexical progress emission,
  durable trace persistence, operator boundary wording, and the dogfood
  evidence artifact needed to prove the post-devcontainer tail is skipped or
  surfaced truthfully.
- SEMWALKGAP must stay narrow and evidence-driven. It must not reopen the older
  `.devcontainer/post_create.sh -> .devcontainer/devcontainer.json` rebound,
  the later script/root-test seams, or general semantic-closeout work unless a
  refreshed rerun reaches those later exact blockers again.

## Interface Freeze Gates

- [ ] IF-0-SEMWALKGAP-1 - Post-devcontainer walk-gap recovery contract:
      a refreshed repo-local `repository sync --force-full` on the
      post-SEMDEVRELAPSE head no longer leaves the durable lexical trace
      stranded on `.devcontainer/devcontainer.json` once the recursive walk has
      already moved into ignored post-devcontainer tail content; it must either
      advance durably to the next later included path or fail closed with a
      truthful newer blocker before the 120-second watchdog expires.
- [ ] IF-0-SEMWALKGAP-2 - Bounded exclusion contract:
      any tail-skipping repair remains limited to the already-declared
      repo-local ignore families
      `fast_test_results/fast_report_*.md` and `test_workspace/` plus their
      immediate walker/status plumbing; it does not broaden into a new
      repo-wide ignore policy, blanket JSON exemptions, or unrelated timeout
      retuning.
- [ ] IF-0-SEMWALKGAP-3 - Durable trace and operator truthfulness contract:
      `EnhancedDispatcher`, `GitAwareIndexManager`, `force_full_exit_trace.json`,
      and `uv run mcp-index repository status` agree on the repaired
      post-devcontainer outcome, and ignored tail paths do not become the
      active `last_progress_path` or `in_flight_path`.
- [ ] IF-0-SEMWALKGAP-4 - Evidence contract:
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the SEMDEVRELAPSE
      walk-order evidence, the repaired SEMWALKGAP rerun command and timestamps,
      the final durable trace/status verdict, and whether the next authoritative
      blocker is a later exact indexed path or an explicit bounded exclusion.
- [ ] IF-0-SEMWALKGAP-5 - Upstream/downstream preservation contract:
      the earlier devcontainer rebound and the later script/root-test seams
      remain historically valid and closed unless the refreshed rerun directly
      re-anchors on one of those later exact blockers again.

## Lane Index & Dependencies

- SL-0 - Post-devcontainer tail fixture freeze; Depends on: SEMDEVRELAPSE; Blocks: SL-1, SL-2, SL-3; Parallel-safe: no
- SL-1 - Recursive walker filter and trace progression repair; Depends on: SL-0; Blocks: SL-2, SL-3; Parallel-safe: no
- SL-2 - Repository-status bounded-exclusion alignment; Depends on: SL-0, SL-1; Blocks: SL-3; Parallel-safe: no
- SL-3 - Live rerun evidence reducer and closeout refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SEMWALKGAP acceptance; Parallel-safe: no

Lane DAG:

```text
SEMDEVRELAPSE
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SEMWALKGAP acceptance
```

## Lanes

### SL-0 - Post-Devcontainer Tail Fixture Freeze

- **Scope**: Freeze the combined post-devcontainer tail in unit coverage so
  this phase proves the dispatcher, durable trace, and ignore-manager behavior
  around `fast_test_results/fast_report_*.md` and `test_workspace/` instead of
  treating the problem as another `.devcontainer/devcontainer.json` file-local
  regression.
- **Owned files**: `tests/test_dispatcher.py`, `tests/test_git_index_manager.py`, `tests/test_ignore_patterns.py`
- **Interfaces provided**: executable assertions for IF-0-SEMWALKGAP-1,
  IF-0-SEMWALKGAP-2, IF-0-SEMWALKGAP-3, and IF-0-SEMWALKGAP-5
- **Interfaces consumed**: existing
  `build_walker_filter(...)`,
  `IgnorePatternManager.should_ignore(...)`,
  `EnhancedDispatcher.index_directory(...)`,
  `GitAwareIndexManager._make_force_full_progress_callback(...)`,
  `GitAwareIndexManager._write_force_full_exit_trace(...)`,
  and the current SEMDEVRELAPSE evidence wording for the
  `.devcontainer/devcontainer.json -> fast_test_results -> test_workspace`
  walk order
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` with a repo-shaped fixture that
    reproduces the post-devcontainer tail order, proves
    `.devcontainer/devcontainer.json` is followed only by ignored fast-report
    and `test_workspace/` content, and requires lexical walking to advance to
    the next included file instead of re-anchoring on the devcontainer marker.
  - test: Extend `tests/test_git_index_manager.py` so durable force-full trace
    persistence freezes the repaired tail behavior: ignored fast-report and
    `test_workspace/` paths do not become the active `last_progress_path` or
    `in_flight_path`, and the next authoritative later included path is what
    survives in the durable trace.
  - test: Extend `tests/test_ignore_patterns.py` so absolute and relative
    walker-filter checks explicitly cover both
    `fast_test_results/fast_report_*.md` and
    `test_workspace/real_repos/search_scaling/package.json` under the repo root.
  - impl: Use synthetic walk order and synthetic trace payloads rather than a
    live multi-minute rerun in unit coverage.
  - impl: Keep this lane focused on contract freeze only. Do not update CLI
    boundary wording or the dogfood evidence artifact here.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_ignore_patterns.py -q --no-cov -k "devcontainer or fast_report or test_workspace or lexical or force_full or trace or ignore"`

### SL-1 - Recursive Walker Filter And Trace Progression Repair

- **Scope**: Implement the smallest exact repair needed so recursive lexical
  walking actually applies the existing repo-local ignore contract to the
  post-devcontainer tail and advances durable progress to the next included
  path instead of repeatedly surfacing `.devcontainer/devcontainer.json`.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `mcp_server/storage/git_index_manager.py`
- **Interfaces provided**: IF-0-SEMWALKGAP-1 post-devcontainer walk-gap recovery contract;
  IF-0-SEMWALKGAP-2 bounded exclusion contract;
  IF-0-SEMWALKGAP-3 durable trace and operator truthfulness contract
- **Interfaces consumed**: SL-0 post-devcontainer tail fixtures; existing
  `build_walker_filter(...)`; current recursive `os.walk(...)` pruning inside
  `index_directory(...)`; existing lexical progress emission; durable trace
  write/finalization semantics; and the SEMDEVRELAPSE live evidence showing the
  walker still appears stuck on `.devcontainer/devcontainer.json`
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 dispatcher, git-manager, and ignore-pattern slices first
    and confirm the current checkout still allows the post-devcontainer tail to
    leak into lexical walking without advancing the authoritative later path.
  - impl: Wire `build_walker_filter(directory)` into the recursive walker so
    repo-local ignore patterns are applied to both candidate files and
    non-core ignored subtrees during lexical indexing, not just in status/docs
    interpretation.
  - impl: Keep the repair exact. Reuse the existing ignore families
    `fast_test_results/fast_report_*.md` and `test_workspace/`; do not add new
    generic JSON, Markdown, or test-file exemptions unless the fixtures prove a
    narrower later seam still remains after those existing ignores are honored.
  - impl: Ensure ignored tail paths do not increment the durable lexical
    progress markers in a way that can overwrite the next real included path.
    If a trace update is needed, keep it limited to truthful progression after
    skipped files rather than adding a new blocker taxonomy.
  - impl: Preserve the already-closed exact bounded paths for
    `.devcontainer/devcontainer.json`,
    `scripts/quick_mcp_vs_native_validation.py`,
    `scripts/validate_mcp_comprehensive.py`,
    `tests/test_artifact_publish_race.py`, and
    `tests/root_tests/run_reranking_tests.py`.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_ignore_patterns.py -q --no-cov -k "devcontainer or fast_report or test_workspace or lexical or force_full or trace or ignore"`
  - verify: `rg -n "build_walker_filter|test_workspace|fast_test_results|last_progress_path|in_flight_path|force_full_closeout_handoff|lexical_walking|bounded_path_reason" mcp_server/dispatcher/dispatcher_enhanced.py mcp_server/storage/git_index_manager.py tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_ignore_patterns.py`

### SL-2 - Repository-Status Bounded-Exclusion Alignment

- **Scope**: Keep the operator-facing status surface aligned with the repaired
  walker so `repository status` explains the bounded post-devcontainer tail
  truthfully and does not imply `.devcontainer/devcontainer.json` is still the
  active blocker when the next relevant paths are ignored fixture repos or a
  later exact included file.
- **Owned files**: `mcp_server/cli/repository_commands.py`, `tests/test_repository_commands.py`
- **Interfaces provided**: IF-0-SEMWALKGAP-2 bounded exclusion contract;
  IF-0-SEMWALKGAP-3 durable trace and operator truthfulness contract;
  IF-0-SEMWALKGAP-5 upstream/downstream preservation contract
- **Interfaces consumed**: SL-0 post-devcontainer tail fixture vocabulary;
  SL-1 repaired walker behavior; current boundary printers for fast reports,
  AI-docs, script boundaries, artifact-publish, and devcontainer JSON; plus the
  current `_print_force_full_exit_trace(...)` rendering path
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_repository_commands.py` so `repository status`
    freezes the combined post-devcontainer tail and proves the surface reports
    either the next later included path or the existing bounded exclusions
    truthfully, without regressing earlier exact boundary copy.
  - impl: Add or refine operator wording only as needed so the existing
    repo-local ignore families are visible in status output alongside the
    durable trace. If the repaired walker now advances to a later included
    path, keep the wording focused on that later path and the bounded tail;
    do not invent a new exact-boundary message for ignored files.
  - impl: Preserve the current boundary lines for
    `fast_test_results/fast_report_*.md`,
    `ai_docs/*_overview.md`,
    `ai_docs/jedi.md`,
    `scripts/create_multi_repo_visual_report.py`,
    `scripts/quick_mcp_vs_native_validation.py`,
    `scripts/validate_mcp_comprehensive.py`,
    `tests/test_artifact_publish_race.py`, and
    `.devcontainer/devcontainer.json`.
  - impl: Keep fail-closed semantics intact. If the live rerun still blocks
    after the ignored tail is skipped, surface the true later blocker rather
    than claiming lexical success, semantic readiness, or closeout readiness
    early.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_repository_commands.py -q --no-cov -k "devcontainer or fast_report or test_workspace or force_full or interrupted or boundary"`
  - verify: `rg -n "fast_test_results|test_workspace|Trace status|Trace stage|Trace blocker source|Last progress path|In-flight path|devcontainer.json|validate_mcp_comprehensive|run_reranking_tests" mcp_server/cli/repository_commands.py tests/test_repository_commands.py`

### SL-3 - Live Rerun Evidence Reducer And Closeout Refresh

- **Scope**: Re-run the repaired repo-local force-full path, reduce the real
  outcome into the dogfood evidence artifact, and keep the closeout narrative
  aligned with the actual post-devcontainer tail behavior after the walker
  repair.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: IF-0-SEMWALKGAP-4 evidence contract;
  IF-0-SEMWALKGAP-5 upstream/downstream preservation contract
- **Interfaces consumed**: SL-0 fixture vocabulary; SL-1 repaired walker/trace
  outcome; SL-2 repository-status boundary wording; current-versus-indexed
  commit evidence; SQLite runtime counts; and the current roadmap steering from
  `SEMDEVRELAPSE` to `SEMWALKGAP`
- **Parallel-safe**: no
- **Tasks**:
  - test: Update `tests/docs/test_semdogfood_evidence_contract.py` so the
    report cites `plans/phase-plan-v7-SEMWALKGAP.md`, preserves the earlier
    lexical-boundary lineage, and records the post-devcontainer walk-gap
    evidence plus the repaired rerun outcome.
  - impl: Re-run the repo-local force-full command with the same strict
    watchdog posture used by the recent semantic dogfood phases and capture the
    resulting durable trace, status output, exit code or later blocker
    classification, commit evidence, and runtime counts.
  - impl: Refresh `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` with the
    SEMDEVRELAPSE walk-order evidence, the repaired SEMWALKGAP rerun command,
    timestamps, `force_full_exit_trace.json` fields, repository-status lines,
    current-versus-indexed commit evidence, and the final verdict: either the
    post-devcontainer tail is now skipped and a later exact blocker is named,
    or the same tail still needs a truthful bounded exclusion explanation.
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
`codex-execute-phase` or manual SEMWALKGAP execution.

Lane-specific checks:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_ignore_patterns.py -q --no-cov -k "devcontainer or fast_report or test_workspace or lexical or force_full or trace or ignore"
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_repository_commands.py -q --no-cov -k "devcontainer or fast_report or test_workspace or force_full or interrupted or boundary"
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
rg -n "build_walker_filter|test_workspace|fast_test_results|last_progress_path|in_flight_path|force_full_closeout_handoff|Trace blocker source|devcontainer.json|validate_mcp_comprehensive|run_reranking_tests" \
  mcp_server/dispatcher/dispatcher_enhanced.py \
  mcp_server/storage/git_index_manager.py \
  mcp_server/cli/repository_commands.py \
  tests/test_dispatcher.py \
  tests/test_git_index_manager.py \
  tests/test_ignore_patterns.py \
  tests/test_repository_commands.py \
  tests/docs/test_semdogfood_evidence_contract.py
```

Whole-phase live verification after code changes:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest \
  tests/test_dispatcher.py \
  tests/test_git_index_manager.py \
  tests/test_ignore_patterns.py \
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
git status --short -- specs/phase-plans-v7.md plans/phase-plan-v7-SEMWALKGAP.md
```

## Acceptance Criteria

- [ ] A refreshed repo-local force-full rerun on the post-SEMDEVRELAPSE head
      no longer leaves the durable lexical trace stranded on
      `.devcontainer/devcontainer.json` once the recursive walk has already
      moved into the ignored post-devcontainer tail; it either advances to a
      later included path or fails closed with a truthful newer blocker before
      the 120-second watchdog expires.
- [ ] The repair remains bounded to the existing repo-local ignore families
      `fast_test_results/fast_report_*.md` and `test_workspace/` plus their
      immediate walker/status plumbing, without broadening into new repo-wide
      ignore policy, blanket JSON exemptions, or unrelated timeout retuning.
- [ ] `force_full_exit_trace.json` and
      `uv run mcp-index repository status` agree on the repaired outcome, and
      ignored fast-report or `test_workspace/` paths do not become the active
      durable progress marker.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` cites
      `plans/phase-plan-v7-SEMWALKGAP.md` and records the SEMDEVRELAPSE
      walk-order evidence, the repaired SEMWALKGAP rerun, and the final
      authoritative blocker or bounded-exclusion verdict.
- [ ] Earlier devcontainer rebound work and later script/root-test seam repairs
      remain preserved unless the refreshed rerun directly re-anchors on one
      of those later exact blockers again.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v7-SEMWALKGAP.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMWALKGAP.md
  artifact_state: staged
```
