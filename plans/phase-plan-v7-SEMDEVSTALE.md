---
phase_loop_plan_version: 1
phase: SEMDEVSTALE
roadmap: specs/phase-plans-v7.md
roadmap_sha256: 4a1b1d902c66a842066e09d2a1a776d047ae328ae10e388f729620b8fa62fecc
---
# SEMDEVSTALE: Devcontainer Stale-Trace Rebound Recovery

## Context

SEMDEVSTALE is the phase-36 follow-up for the v7 semantic hardening roadmap.
SEMDISKIO completed the intended storage-closeout code/test repair, but its
verification rerun on observed commit `c8b2d724` never reached semantic
closeout. Instead, the live repo-local
`uv run mcp-index repository sync --force-full` trace stopped advancing at
`2026-04-29T10:35:02Z` with `Trace stage: lexical_walking`,
`Trace freshness: stale-running snapshot`, and
`Last progress path: /home/viperjuice/code/Code-Index-MCP/.devcontainer/devcontainer.json`.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is the active roadmap, it is tracked and clean in
  this worktree, and `sha256sum specs/phase-plans-v7.md` matches the required
  `4a1b1d902c66a842066e09d2a1a776d047ae328ae10e388f729620b8fa62fecc`.
- Canonical phase-loop state exists under `.phase-loop/`; `.phase-loop/state.json`
  and `.phase-loop/tui-handoff.md` both mark `SEMDEVSTALE` as the current
  `unplanned` phase on the same roadmap SHA after `SEMDISKIO` completed and its
  live verification blocked on the renewed stale lexical trace. Legacy
  `.codex/phase-loop/` state exists only for compatibility and is not
  authoritative for this run.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is the current evidence anchor. It
  already records the SEMDISKIO code/test repair, the renewed stale-running
  `.devcontainer/devcontainer.json` evidence on `c8b2d724`, and the roadmap
  steering decision that makes `SEMDEVSTALE` the next downstream slice.
- The current code still carries an exact `.devcontainer/devcontainer.json`
  boundary in both `mcp_server/plugins/generic_treesitter_plugin.py` and
  `mcp_server/cli/repository_commands.py`. This phase must determine whether
  the renewed stall is inside that exact bounded JSON path, or in the
  lexical-to-semantic handoff that follows after the file already finished and
  left `in_flight_path=null`.
- `mcp_server/dispatcher/dispatcher_enhanced.py` owns the live `last_progress_path`
  and `in_flight_path` mutations and emits force-full progress snapshots.
  `mcp_server/storage/git_index_manager.py` persists those snapshots into
  `.mcp-index/force_full_exit_trace.json` and is therefore the authoritative
  place to repair stale-running trace progression or fail-closed terminalization.
- `mcp_server/cli/repository_commands.py` already distinguishes missing traces
  from stale-running ones and prints the exact bounded lexical-boundary lines
  accumulated by earlier phases. This phase must preserve those earlier boundary
  lines while restoring truthful live or terminal reporting for the renewed
  `.devcontainer` rebound.

Practical planning boundary:

- SEMDEVSTALE may tighten the exact `.devcontainer/devcontainer.json` indexing
  path, the dispatcher's lexical-to-semantic handoff, force-full trace
  progression/terminalization, repository-status reporting, and the dogfood
  evidence artifact needed to prove the rerun either clears the seam or
  exposes the next exact blocker.
- SEMDEVSTALE must stay narrow and evidence-driven. It must not reopen the
  earlier fast-report, `ai_docs/*_overview.md`, `ai_docs/jedi.md`,
  `tests/test_artifact_publish_race.py`, `scripts/quick_mcp_vs_native_validation.py`,
  or SEMDISKIO storage-closeout contracts unless the refreshed rerun directly
  re-anchors there again.

## Interface Freeze Gates

- [ ] IF-0-SEMDEVSTALE-1 - Renewed stale-trace contract:
      a refreshed repo-local `repository sync --force-full` no longer remains
      beyond the lexical-timeout freshness window with
      `Trace stage: lexical_walking`,
      `Trace freshness: stale-running snapshot`,
      `Last progress path: /home/viperjuice/code/Code-Index-MCP/.devcontainer/devcontainer.json`,
      and `in_flight_path=null`.
- [ ] IF-0-SEMDEVSTALE-2 - Exact bounded recovery contract:
      if this phase keeps or changes the `.devcontainer/devcontainer.json`
      special handling, it stays limited to that exact path or a stricter alias
      and does not broaden into arbitrary `.json` files, the whole
      `.devcontainer/` directory, or repo-wide timeout tuning.
- [ ] IF-0-SEMDEVSTALE-3 - Force-full handoff truthfulness contract:
      once the live rerun reaches `.devcontainer/devcontainer.json`, the
      dispatcher and git-aware trace either advance durably into the next stage
      or fail closed with a new exact blocker; they must not leave a completed
      `.devcontainer/devcontainer.json` marker frozen as a stale-running lexical
      snapshot.
- [ ] IF-0-SEMDEVSTALE-4 - Operator and evidence contract:
      `force_full_exit_trace.json`, `uv run mcp-index repository status`, and
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` stay aligned on the rerun
      command, timestamps, progress paths, current-versus-indexed commit
      evidence, summary/vector counts, and the final repaired verdict.

## Lane Index & Dependencies

- SL-0 - Renewed stale-trace fixture freeze; Depends on: SEMDISKIO; Blocks: SL-1, SL-2, SL-3; Parallel-safe: no
- SL-1 - Exact devcontainer boundary or handoff repair; Depends on: SL-0; Blocks: SL-2, SL-3; Parallel-safe: no
- SL-2 - Force-full trace and repository-status alignment; Depends on: SL-0, SL-1; Blocks: SL-3; Parallel-safe: no
- SL-3 - Live rerun evidence reducer and closeout refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SEMDEVSTALE acceptance; Parallel-safe: no

Lane DAG:

```text
SEMDISKIO
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SEMDEVSTALE acceptance
```

## Lanes

### SL-0 - Renewed Stale-Trace Fixture Freeze

- **Scope**: Freeze the current `.devcontainer/devcontainer.json` stale-running
  trace shape in dispatcher and git-manager coverage so this phase proves the
  renewed regression exactly instead of relying on the older SEMDEVREBOUND
  `post_create.sh -> devcontainer.json` in-flight fixture.
- **Owned files**: `tests/test_dispatcher.py`, `tests/test_git_index_manager.py`
- **Interfaces provided**: executable assertions for IF-0-SEMDEVSTALE-1 and IF-0-SEMDEVSTALE-3
- **Interfaces consumed**: existing
  `EnhancedDispatcher.index_directory(...)`,
  `EnhancedDispatcher._index_file_with_lexical_timeout(...)`,
  `GitAwareIndexManager._make_force_full_progress_callback(...)`,
  `GitAwareIndexManager._write_force_full_exit_trace(...)`,
  `GitAwareIndexManager._trace_blocker_source(...)`, and the current
  SEMDISKIO evidence wording for `.devcontainer/devcontainer.json`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` with a repo-shaped fixture that
    freezes the renewed regression where `.devcontainer/devcontainer.json`
    becomes the latest completed lexical path and the rerun still never emits a
    durable downstream handoff.
  - test: Extend `tests/test_git_index_manager.py` so force-full progress
    persistence freezes the stale-running shape after the exact `.devcontainer`
    marker, including `Trace freshness: stale-running snapshot`,
    `last_progress_path=.devcontainer/devcontainer.json`, and no
    `in_flight_path`.
  - test: Require negative assertions that older exact seams such as
    `tests/test_artifact_publish_race.py`,
    `scripts/quick_mcp_vs_native_validation.py`, and the SEMDISKIO
    `storage_closeout` contract do not silently become the active blocker again
    under this renewed fixture.
  - impl: Use synthetic dispatcher progress and durable-trace payloads rather
    than a live multi-minute rerun in unit coverage.
  - impl: Keep this lane focused on contract freeze only. Do not update
    repository-status formatting or the dogfood evidence artifact here.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov -k "devcontainer or stale or lexical or force_full or trace"`

### SL-1 - Exact Devcontainer Boundary Or Handoff Repair

- **Scope**: Implement the smallest exact code repair needed so the renewed
  `.devcontainer/devcontainer.json` seam no longer leaves the force-full rerun
  parked on a stale lexical snapshot after the file already completed.
- **Owned files**: `mcp_server/plugins/generic_treesitter_plugin.py`, `mcp_server/dispatcher/dispatcher_enhanced.py`
- **Interfaces provided**: IF-0-SEMDEVSTALE-1 renewed stale-trace contract;
  IF-0-SEMDEVSTALE-2 exact bounded recovery contract;
  IF-0-SEMDEVSTALE-3 force-full handoff truthfulness contract
- **Interfaces consumed**: SL-0 renewed stale-trace fixtures; the exact bounded
  JSON helper in `GenericTreeSitterPlugin`; dispatcher lexical progress and
  semantic handoff logic; existing `last_progress_path` / `in_flight_path`
  accounting; and the live SEMDISKIO evidence showing the completed
  `.devcontainer/devcontainer.json` marker with `in_flight_path=null`
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 dispatcher and git-manager slices first and confirm the
    current checkout still lacks a truthful downstream handoff after the exact
    `.devcontainer/devcontainer.json` boundary is hit.
  - impl: Determine whether the renewed stall is still caused by the exact
    bounded JSON handling itself or by the handoff that should happen after the
    file finishes. Repair only that exact seam.
  - impl: If the root cause is the `.devcontainer/devcontainer.json` bounded
    path, keep the fix limited to that exact path or a stricter alias instead
    of broadening to all `.json` files or all `.devcontainer/*` files.
  - impl: If the root cause is the post-file handoff, keep the fix local to
    dispatcher progress emission or terminalization and do not add a
    speculative path exemption.
  - impl: Preserve the previously closed exact boundaries for
    `tests/test_artifact_publish_race.py`,
    `scripts/quick_mcp_vs_native_validation.py`,
    `ai_docs/jedi.md`, and the earlier overview/report families. Do not reopen
    those phases unless the refreshed rerun directly re-anchors there again.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py -q --no-cov -k "devcontainer or stale or lexical or timeout"`
  - verify: `rg -n "devcontainer|last_progress_path|in_flight_path|chunk_text|lexical_walking" mcp_server/plugins/generic_treesitter_plugin.py mcp_server/dispatcher/dispatcher_enhanced.py tests/test_dispatcher.py`

### SL-2 - Force-Full Trace And Repository-Status Alignment

- **Scope**: Keep the persisted force-full trace and operator-facing status
  surface aligned with the repaired `.devcontainer` seam so stale-running,
  lexical, and later semantic-stage verdicts stay truthful.
- **Owned files**: `mcp_server/storage/git_index_manager.py`, `mcp_server/cli/repository_commands.py`, `tests/test_repository_commands.py`
- **Interfaces provided**: IF-0-SEMDEVSTALE-3 force-full handoff truthfulness contract;
  IF-0-SEMDEVSTALE-4 operator and evidence contract
- **Interfaces consumed**: SL-0 git-manager fixture freeze; SL-1 exact repair
  choice; existing repository-status boundary helpers for
  `.devcontainer/devcontainer.json`,
  `tests/test_artifact_publish_race.py`,
  `scripts/quick_mcp_vs_native_validation.py`, and the SEMDISKIO
  `storage_closeout` reporting path
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_repository_commands.py` so `repository status`
    freezes the renewed `.devcontainer/devcontainer.json` stale marker, then
    proves the repaired path either advances beyond that marker or exits with a
    new exact blocker instead of continuing to report a stale lexical snapshot.
  - impl: Tighten `GitAwareIndexManager` progress persistence only as needed so
    the force-full trace advances or terminalizes truthfully after the repaired
    `.devcontainer` seam, without regressing the SEMDISKIO storage-closeout
    reporting that is still needed if a later rerun reaches final closeout
    again.
  - impl: Tighten `mcp_server/cli/repository_commands.py` only as needed so the
    operator surface stays aligned with the exact repaired seam and preserves
    older lexical boundary lines from prior phases.
  - impl: Keep fail-closed semantics intact. If the live rerun still blocks,
    surface the true later blocker rather than claiming storage-closeout,
    semantic readiness, or lexical success early.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_repository_commands.py -q --no-cov -k "devcontainer or stale-running or force_full or boundary"`
  - verify: `rg -n "devcontainer|Trace freshness|Last progress path|In-flight path|storage_closeout|lexical_walking" mcp_server/storage/git_index_manager.py mcp_server/cli/repository_commands.py tests/test_repository_commands.py`

### SL-3 - Live Rerun Evidence Reducer And Closeout Refresh

- **Scope**: Re-run the repaired repo-local force-full path, reduce the real
  outcome into the dogfood evidence artifact, and keep the final closeout
  narrative aligned with the actual post-repair rerun.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: IF-0-SEMDEVSTALE-4 operator and evidence contract
- **Interfaces consumed**: SL-0 fixture vocabulary; SL-1 exact repair outcome;
  SL-2 repository-status and force-full trace fields; current-versus-indexed
  commit evidence; SQLite summary/vector counts; and the current roadmap
  steering from `SEMDISKIO` to `SEMDEVSTALE`
- **Parallel-safe**: no
- **Tasks**:
  - test: Update `tests/docs/test_semdogfood_evidence_contract.py` so the
    report now cites `plans/phase-plan-v7-SEMDEVSTALE.md`, preserves the
    earlier lexical-boundary lineage, and records the renewed stale-running
    `.devcontainer/devcontainer.json` evidence plus the repaired rerun outcome.
  - impl: Re-run the repo-local force-full command with the same strict
    watchdog posture used by the recent semantic dogfood phases and capture the
    resulting trace, status output, commit evidence, and runtime counts.
  - impl: Refresh `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` with the rerun
    command, timestamps, `force_full_exit_trace.json` fields, repository-status
    lines, current-versus-indexed commit evidence, and the final verdict:
    either the `.devcontainer` stale seam is cleared and a later exact blocker
    is named, or the renewed seam still fails closed with truthful repaired
    reporting.
  - impl: If no broader docs are needed, record that decision in the status
    artifact rather than widening this phase into general documentation cleanup.
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
  - verify: `env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - verify: `sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'`

## Verification

Planning-only run: do not execute these during plan creation. Run them during
`codex-execute-phase` or manual SEMDEVSTALE execution.

Lane-specific checks:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov -k "devcontainer or stale or lexical or force_full or trace"
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_repository_commands.py -q --no-cov -k "devcontainer or stale-running or force_full or boundary"
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
rg -n "devcontainer|last_progress_path|in_flight_path|Trace freshness|storage_closeout|lexical_walking" \
  mcp_server/plugins/generic_treesitter_plugin.py \
  mcp_server/dispatcher/dispatcher_enhanced.py \
  mcp_server/storage/git_index_manager.py \
  mcp_server/cli/repository_commands.py \
  docs/status/SEMANTIC_DOGFOOD_REBUILD.md \
  tests/test_dispatcher.py \
  tests/test_git_index_manager.py \
  tests/test_repository_commands.py \
  tests/docs/test_semdogfood_evidence_contract.py
```

Whole-phase regression commands:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest \
  tests/test_dispatcher.py \
  tests/test_git_index_manager.py \
  tests/test_repository_commands.py \
  tests/docs/test_semdogfood_evidence_contract.py \
  -q --no-cov
env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
python - <<'PY'
from pathlib import Path
trace = Path(".mcp-index") / "force_full_exit_trace.json"
print(trace.read_text() if trace.exists() else "missing")
PY
sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'
git status --short -- specs/phase-plans-v7.md plans/phase-plan-v7-SEMDEVSTALE.md
```

## Acceptance Criteria

- [ ] A live repo-local force-full rerun no longer remains beyond the
      lexical-timeout freshness window with a stale-running
      `.devcontainer/devcontainer.json` marker and `in_flight_path=null`.
- [ ] The repaired code path stays exact: it remains limited to the
      `.devcontainer/devcontainer.json` seam or the immediate handoff after it,
      without broadening into arbitrary `.json` files, all `.devcontainer/*`
      files, or repo-wide timeout retuning.
- [ ] `force_full_exit_trace.json` and `uv run mcp-index repository status`
      either advance durably beyond `.devcontainer/devcontainer.json` or fail
      closed with a new exact blocker, while preserving the earlier lexical
      boundary lines and the SEMDISKIO storage-closeout reporting surface.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` cites
      `plans/phase-plan-v7-SEMDEVSTALE.md` and records the renewed stale trace,
      the repaired rerun outcome, and the next exact blocker if semantic
      closeout still is not reached on the active head.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v7-SEMDEVSTALE.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMDEVSTALE.md
  artifact_state: staged
```
