---
phase_loop_plan_version: 1
phase: SEMDEVCONTAINER
roadmap: specs/phase-plans-v7.md
roadmap_sha256: b80a1d4d88dda2d044136609fcf466d0d2a1aef9f06c6a035be3e9e19c1b1844
---
# SEMDEVCONTAINER: Devcontainer JSON Lexical Exit Recovery

## Context

SEMDEVCONTAINER is the phase-31 follow-up for the v7 semantic hardening
roadmap. SEMTRACEFRESHNESS repaired stale lexical progress reporting and
proved the durable force-full trace now advances beyond the older
`ai_docs/pytest_overview.md` seam, but the refreshed live rerun still stopped
making forward progress at the next exact lexical blocker:
`.devcontainer/devcontainer.json`.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is tracked and clean in this worktree, and its
  live SHA matches the required
  `b80a1d4d88dda2d044136609fcf466d0d2a1aef9f06c6a035be3e9e19c1b1844`.
- `.phase-loop/state.json` and `.phase-loop/tui-handoff.md` are the
  authoritative runner surfaces in this checkout. They already mark
  `SEMDEVCONTAINER` as the current unplanned phase on the same roadmap SHA,
  with `SEMTRACEFRESHNESS` complete on `HEAD`
  `86357e74509a96aed1d8151130d86d0e7818b4de` and a clean worktree before this
  plan write.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is the active dogfood evidence
  anchor. Its current SEMTRACEFRESHNESS snapshot (`2026-04-29T08:53:23Z`,
  observed commit `8870a23f`) records the live force-full rerun freezing with
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/.devcontainer/post_create.sh`
  and
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/.devcontainer/devcontainer.json`
  after the trace timestamp stopped advancing at `2026-04-29T08:51:28Z`.
- The active blocker file is small, not a generic large-file outlier:
  `.devcontainer/devcontainer.json` is `558` bytes and
  `.devcontainer/post_create.sh` is `425` bytes. The current seam is therefore
  more likely an exact JSON indexing-path or lexical-closeout defect than a
  broad file-size problem.
- `mcp_server/plugins/generic_treesitter_plugin.py` is the live indexing path
  for `.json` files. It currently always attempts `chunk_text(content,
  self.lang)` before persisting chunks and has no exact bounded-path handling
  for `.devcontainer/devcontainer.json`.
- `mcp_server/dispatcher/dispatcher_enhanced.py` already sets
  `stats["in_flight_path"]` before calling `_run_blocking_with_timeout(...)`,
  and that helper should raise `TimeoutError` after
  `MCP_INDEX_LEXICAL_TIMEOUT_SECONDS`. The live dogfood evidence still shows a
  stale running trace parked on the `.devcontainer` seam, so this phase must
  prove either an exact path recovery that exits quickly or a truthful bounded
  blocked closeout for that seam.
- `mcp_server/cli/repository_commands.py` currently surfaces explicit lexical
  boundaries for generated fast-test reports, `ai_docs/*_overview.md`,
  `ai_docs/jedi.md`, and
  `scripts/create_multi_repo_visual_report.py`, but it does not yet surface an
  explicit operator boundary for the exact `.devcontainer/devcontainer.json`
  recovery path.

Practical planning boundary:

- SEMDEVCONTAINER may introduce one exact recovery for the live
  `.devcontainer` seam: an exact bounded JSON indexing path,
  the smallest dispatcher-side lexical closeout repair needed to make timeout
  truthfully terminal for this file family, or the smallest combination needed
  to carry the live rerun past `.devcontainer/devcontainer.json`.
- SEMDEVCONTAINER must stay narrow and evidence-driven. It must not add a
  broad `*.json` or `.devcontainer/*` lexical bypass, reopen earlier Markdown
  or Python bounded-path repairs, or widen into semantic summary/vector work
  before the `.devcontainer` lexical seam exits cleanly.

## Interface Freeze Gates

- [ ] IF-0-SEMDEVCONTAINER-1 - Exact `.devcontainer` blocker contract:
      a repo-local `repository sync --force-full` no longer sits past the
      configured lexical-timeout window with
      `last_progress_path=/home/viperjuice/code/Code-Index-MCP/.devcontainer/post_create.sh`
      and
      `in_flight_path=/home/viperjuice/code/Code-Index-MCP/.devcontainer/devcontainer.json`
      while the durable trace timestamp remains unchanged.
- [ ] IF-0-SEMDEVCONTAINER-2 - Exact bounded recovery contract:
      if this phase introduces a path-specific indexing fast path, it stays
      limited to `.devcontainer/devcontainer.json` or a stricter exact file
      family, preserves lexical discoverability for the stored file content,
      and does not broaden to arbitrary `.json` files or the whole
      `.devcontainer/` directory.
- [ ] IF-0-SEMDEVCONTAINER-3 - Truthful lexical closeout contract:
      if the live rerun still cannot progress past the `.devcontainer` seam,
      the durable trace and dispatcher stats exit with a bounded lexical
      blocker or timeout verdict that still names that exact file family
      truthfully instead of leaving a stale `status=running` snapshot behind.
- [ ] IF-0-SEMDEVCONTAINER-4 - Operator surface contract:
      `uv run mcp-index repository status` remains aligned with the configured
      timeout window, preserves prior lexical boundary wording from
      SEMFASTREPORT, SEMPYTESTOVERVIEW, SEMVISUALREPORT, and SEMJEDI, and adds
      any new `.devcontainer` boundary wording only if the implementation
      actually introduces that exact recovery path.
- [ ] IF-0-SEMDEVCONTAINER-5 - Evidence contract:
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the chosen
      `.devcontainer` repair, the live rerun command and outcome, the durable
      trace timestamps and paths, and whether the rerun advances into later
      lexical or semantic work or exits with a new narrower blocker.
- [ ] IF-0-SEMDEVCONTAINER-6 - Upstream-boundary preservation contract:
      SEMFASTREPORT, SEMPYTESTOVERVIEW, SEMVISUALREPORT, SEMJEDI, and
      SEMTRACEFRESHNESS remain closed unless the refreshed rerun directly
      re-anchors on one of those exact seams.

## Lane Index & Dependencies

- SL-0 - Devcontainer lexical seam contract and fixture freeze; Depends on: SEMTRACEFRESHNESS; Blocks: SL-1, SL-2, SL-3; Parallel-safe: no
- SL-1 - Exact devcontainer JSON lexical exit repair; Depends on: SL-0; Blocks: SL-2, SL-3; Parallel-safe: no
- SL-2 - Repository-status boundary and blocker truthfulness alignment; Depends on: SL-0, SL-1; Blocks: SL-3; Parallel-safe: no
- SL-3 - Dogfood evidence reducer and rerun refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SEMDEVCONTAINER acceptance; Parallel-safe: no

Lane DAG:

```text
SEMTRACEFRESHNESS
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SEMDEVCONTAINER acceptance
```

## Lanes

### SL-0 - Devcontainer Lexical Seam Contract And Fixture Freeze

- **Scope**: Freeze the live `.devcontainer/post_create.sh ->
  .devcontainer/devcontainer.json` blocker shape before implementation so this
  phase proves an exact recovery instead of only moving the stale running
  trace somewhere else.
- **Owned files**: `tests/test_dispatcher.py`, `tests/test_repository_commands.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMDEVCONTAINER-1 through IF-0-SEMDEVCONTAINER-4
- **Interfaces consumed**: existing
  `EnhancedDispatcher.index_directory(...)`,
  `EnhancedDispatcher._index_file_with_lexical_timeout(...)`,
  `_run_blocking_with_timeout(...)`,
  `repository status` force-full trace rendering, and the current
  `.devcontainer/post_create.sh` plus `.devcontainer/devcontainer.json`
  blocker vocabulary from `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` with a deterministic
    `.devcontainer/devcontainer.json` fixture that freezes the current seam
    and proves the repaired path either finishes lexical indexing for that
    file or returns a bounded lexical timeout/error instead of leaving the
    trace parked as a stale running snapshot.
  - test: Keep the dispatcher fixture exact. Use a repo-local
    `.devcontainer/post_create.sh` predecessor plus `.devcontainer/devcontainer.json`
    target rather than broad JSON fixtures so the contract stays tied to the
    live blocker shape.
  - test: Extend `tests/test_repository_commands.py` so `repository status`
    proves the exact `.devcontainer` blocker wording, timeout freshness, and
    any new exact boundary message without regressing the existing fast-report,
    `ai_docs/*_overview.md`, exact Jedi, or exact visual-report wording.
  - impl: Keep fixtures deterministic with monkeypatched chunker or dispatcher
    behavior and synthetic durable-trace payloads rather than multi-minute live
    waits inside unit coverage.
  - impl: Keep this lane focused on contract freeze only. Do not update live
    dogfood evidence or run the real force-full command here.
  - verify: `uv run pytest tests/test_dispatcher.py tests/test_repository_commands.py -q --no-cov`

### SL-1 - Exact Devcontainer JSON Lexical Exit Repair

- **Scope**: Implement the smallest exact recovery needed so
  `.devcontainer/devcontainer.json` no longer leaves the live force-full trace
  parked past the configured lexical-timeout window.
- **Owned files**: `mcp_server/plugins/generic_treesitter_plugin.py`, `mcp_server/dispatcher/dispatcher_enhanced.py`
- **Interfaces provided**: IF-0-SEMDEVCONTAINER-1 exact `.devcontainer`
  blocker contract; IF-0-SEMDEVCONTAINER-2 exact bounded recovery contract;
  IF-0-SEMDEVCONTAINER-3 truthful lexical closeout contract
- **Interfaces consumed**: SL-0 dispatcher/status fixtures; the generic JSON
  plugin's unconditional `chunk_text(content, self.lang)` path; dispatcher
  lexical timeout handling and `last_progress_path` / `in_flight_path`
  accounting
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 dispatcher slice first and confirm the current
    `.devcontainer/devcontainer.json` path still has no exact bounded recovery
    or truthful terminal closeout under the frozen fixture.
  - impl: Add the smallest exact `.devcontainer` recovery that matches the
    live evidence. Prefer an exact bounded JSON indexing path if that clears
    the seam while preserving stored file content and minimal lexical
    discoverability.
  - impl: If the live evidence shows the real defect is lexical timeout
    closeout rather than the JSON chunking path itself, keep the fix local to
    dispatcher timeout/terminalization and do not add a speculative file-path
    bypass.
  - impl: Do not broaden to all `.json` files, all `.devcontainer/*` files, or
    a repo-wide timeout retune. Any exact-path allowlist or fast path must be
    documented by code shape and tests as specific to this seam.
  - impl: Preserve existing lexical accounting semantics for prior bounded-path
    phases and keep the fail-closed timeout posture intact for unrelated JSON
    or config files.
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "devcontainer or lexical or timeout"`

### SL-2 - Repository-Status Boundary And Blocker Truthfulness Alignment

- **Scope**: Keep the operator-facing status surface aligned with the chosen
  `.devcontainer` repair and the true live or terminal state of the rerun.
- **Owned files**: `mcp_server/cli/repository_commands.py`
- **Interfaces provided**: IF-0-SEMDEVCONTAINER-4 operator surface contract
- **Interfaces consumed**: SL-0 repository-status fixtures; SL-1 exact
  recovery behavior; existing boundary helpers for fast-test reports,
  `ai_docs/*_overview.md`, `ai_docs/jedi.md`, and
  `scripts/create_multi_repo_visual_report.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 repository-status slice first and keep current rollout,
    query-surface, and durable-trace vocabulary stable while adding the
    smallest operator wording needed for the exact `.devcontainer` repair.
  - impl: If SL-1 introduces an exact bounded recovery path, add a matching
    explicit lexical-boundary line for `.devcontainer/devcontainer.json` so
    operators can see that this seam is intentional and exact.
  - impl: If SL-1 solves the issue entirely in timeout closeout without an
    exact bounded path, keep this lane limited to truthful blocker/freshness
    rendering and do not add misleading boundary copy.
  - impl: Preserve existing stale-running detection against
    `MCP_INDEX_LEXICAL_TIMEOUT_SECONDS` and keep earlier boundary wording
    unchanged unless the live rerun directly re-anchors there.
  - verify: `uv run pytest tests/test_repository_commands.py -q --no-cov -k "devcontainer or force_full or boundary"`
  - verify: `rg -n "devcontainer|Lexical boundary|Trace freshness|In-flight path|Last progress path" mcp_server/cli/repository_commands.py tests/test_repository_commands.py`

### SL-3 - Dogfood Evidence Reducer And Rerun Refresh

- **Scope**: Refresh the repo-local dogfood report so it records the
  `.devcontainer` repair, the live rerun outcome, and the next exact blocker
  if semantic-stage work still does not begin.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: IF-0-SEMDEVCONTAINER-5 evidence contract;
  IF-0-SEMDEVCONTAINER-6 upstream-boundary preservation contract
- **Interfaces consumed**: SL-1 exact repair; SL-2 repository-status wording;
  roadmap SEMDEVCONTAINER exit criteria; prior SEMFASTREPORT,
  SEMPYTESTOVERVIEW, SEMVISUALREPORT, SEMJEDI, and SEMTRACEFRESHNESS evidence
  lineage
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/docs/test_semdogfood_evidence_contract.py` so the
    refreshed report cites `plans/phase-plan-v7-SEMDEVCONTAINER.md`, the live
    rerun command and timestamps, the `.devcontainer/post_create.sh` and
    `.devcontainer/devcontainer.json` trace pair, and the next exact blocker
    if semantic-stage work still does not begin.
  - test: Require the report to preserve the older fast-report,
    `ai_docs/*_overview.md`, exact Jedi, exact visual-report, and trace
    freshness evidence lineage while making clear that the active seam is now
    the `.devcontainer` lexical exit gap.
  - test: Require the report to say whether the rerun advanced into later
    lexical work, reached semantic closeout, or exited with a new narrower
    bounded blocker after the `.devcontainer` repair.
  - impl: Refresh `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` with the live rerun
    command, observed commit IDs, durable trace contents, repository-status
    output, and the steering verdict after the `.devcontainer` seam is
    repaired or truthfully terminalized.
  - impl: Keep the report factual and durable. Record exact timestamps,
    `last_progress_path`, `in_flight_path`, trace `status`, stage family,
    blocker source, and chunk/vector counts without claiming semantic success
    before the evidence exists.
  - impl: If the rerun still does not begin semantic work, name the next exact
    blocker directly and keep SEMDEVCONTAINER itself scoped to the
    `.devcontainer` seam once that seam is no longer a stale-running trace.
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
  - verify: `rg -n "SEMDEVCONTAINER|devcontainer.json|Trace status|Trace stage|Last progress path|In-flight path|next exact blocker" docs/status/SEMANTIC_DOGFOOD_REBUILD.md tests/docs/test_semdogfood_evidence_contract.py`

## Verification

Planning-only run: do not execute these during plan creation. Run them during
`codex-execute-phase` or manual SEMDEVCONTAINER execution.

Lane-specific checks:

```bash
uv run pytest tests/test_dispatcher.py tests/test_repository_commands.py -q --no-cov
uv run pytest tests/test_dispatcher.py -q --no-cov -k "devcontainer or lexical or timeout"
uv run pytest tests/test_repository_commands.py -q --no-cov -k "devcontainer or force_full or boundary"
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
rg -n "devcontainer|Lexical boundary|Trace freshness|Last progress path|In-flight path|SEMDEVCONTAINER" \
  mcp_server/plugins/generic_treesitter_plugin.py \
  mcp_server/dispatcher/dispatcher_enhanced.py \
  mcp_server/cli/repository_commands.py \
  docs/status/SEMANTIC_DOGFOOD_REBUILD.md \
  tests/test_dispatcher.py \
  tests/test_repository_commands.py \
  tests/docs/test_semdogfood_evidence_contract.py
```

Whole-phase regression commands:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest \
  tests/test_dispatcher.py \
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
git status --short -- specs/phase-plans-v7.md plans/phase-plan-v7-SEMDEVCONTAINER.md
```

## Acceptance Criteria

- [ ] A live repo-local force-full rerun no longer remains past the configured
      lexical-timeout window with
      `last_progress_path=/home/viperjuice/code/Code-Index-MCP/.devcontainer/post_create.sh`
      and
      `in_flight_path=/home/viperjuice/code/Code-Index-MCP/.devcontainer/devcontainer.json`
      while the durable trace timestamp stays unchanged.
- [ ] The rerun either completes the `.devcontainer/devcontainer.json` lexical
      seam and advances into later lexical or semantic work, or exits with a
      bounded lexical blocker that still names that exact file family
      truthfully.
- [ ] `uv run mcp-index repository status` remains aligned with the configured
      timeout window and the chosen `.devcontainer` recovery, without
      regressing older exact lexical-boundary wording from prior phases.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is refreshed with the
      `.devcontainer` repair evidence, the rerun outcome, and the next exact
      blocker if semantic-stage work still does not begin.
- [ ] SEMFASTREPORT, SEMPYTESTOVERVIEW, SEMVISUALREPORT, SEMJEDI, and
      SEMTRACEFRESHNESS remain closed unless the refreshed rerun directly
      re-anchors on one of those exact seams.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v7-SEMDEVCONTAINER.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMDEVCONTAINER.md
  artifact_state: staged
```
