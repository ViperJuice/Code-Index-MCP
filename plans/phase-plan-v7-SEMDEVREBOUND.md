---
phase_loop_plan_version: 1
phase: SEMDEVREBOUND
roadmap: specs/phase-plans-v7.md
roadmap_sha256: 658d58f4f7999e9964028dd2d39babd0199c11e6020a796fb98bb3572a6901c9
---
# SEMDEVREBOUND: Devcontainer Rebound Lexical Re-Anchor Recovery

## Context

SEMDEVREBOUND is the phase-33 follow-up for the v7 semantic hardening
roadmap. SEMPUBLISHRACE proved the live repo-local `repository sync
--force-full` rerun now advances beyond
`tests/test_artifact_publish_race.py`, but the same rerun later re-anchored on
`.devcontainer/devcontainer.json` and stopped refreshing again with a stale
durable trace.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is the active roadmap, it is tracked and clean in
  this worktree, and `sha256sum specs/phase-plans-v7.md` matches the required
  `658d58f4f7999e9964028dd2d39babd0199c11e6020a796fb98bb3572a6901c9`.
- Canonical phase-loop state exists under `.phase-loop/`; `.phase-loop/state.json`
  and `.phase-loop/tui-handoff.md` both mark `SEMDEVREBOUND` as the current
  `unplanned` phase on the same roadmap SHA, with `SEMPUBLISHRACE` complete,
  a clean worktree before this plan write, and `HEAD`
  `7fc3f0e0231556a5d1788cc571eb5ad4067792a0` on `main...origin/main [ahead 61]`.
- The target artifact `plans/phase-plan-v7-SEMDEVREBOUND.md` did not exist
  before this planning run.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is the active dogfood evidence
  anchor. Its latest SEMPUBLISHRACE snapshot (`2026-04-29T09:31:19Z`,
  observed commit `aec99482`) records a live rerun that advanced beyond the
  prior publish-race seam and later re-anchored on
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/.devcontainer/post_create.sh`
  with
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/.devcontainer/devcontainer.json`.
- The durable trace stopped advancing at `2026-04-29T09:29:40Z`; by
  `2026-04-29T09:30:32Z`, `repository status` already reported
  `Trace freshness: stale-running snapshot`, and the rerun was interrupted
  after evidence capture at `2026-04-29T09:31:19Z`.
- The rebound is real, not a misread of the earlier publish-race blocker:
  the same evidence shows the rerun advancing through later lexical work
  including `tests/test_dispatcher.py`, `tests/root_tests/test_c_plugin_simple.py`,
  `tests/security/fixtures/mock_plugin/__init__.py`, and `ai_docs/qdrant.md`
  before returning to the `.devcontainer` seam.
- `mcp_server/plugins/python_plugin/plugin.py` now carries an exact bounded
  Python path for `tests/test_artifact_publish_race.py`, and
  `mcp_server/cli/repository_commands.py` already reports that exact bounded
  Python boundary. Those SEMPUBLISHRACE surfaces must remain preserved unless
  a fresh rerun directly re-anchors there again.
- `mcp_server/plugins/generic_treesitter_plugin.py` is still the live lexical
  path for `.json` files. It currently always attempts
  `chunk_text(content, self.lang)` and has no exact bounded JSON path helper
  analogous to the Python plugin's `_BOUNDED_CHUNK_PATHS`.
- `mcp_server/cli/repository_commands.py` still prints stale-running freshness
  plus the current `last_progress_path` and `in_flight_path`, but it has no
  explicit `.devcontainer/devcontainer.json` boundary helper today. The only
  current exact bounded lexical operator lines are for fast-test reports,
  `ai_docs/*_overview.md`, `ai_docs/jedi.md`,
  `scripts/create_multi_repo_visual_report.py`, and
  `tests/test_artifact_publish_race.py`.
- The renewed blocker file remains small:
  `.devcontainer/devcontainer.json` is `558` bytes and
  `.devcontainer/post_create.sh` is `425` bytes. The rebound is therefore
  more likely an exact JSON indexing-path or lexical-closeout defect than a
  broad large-file or generic throughput problem.
- `tests/docs/test_semdogfood_evidence_contract.py` currently still anchors
  the report to `plans/phase-plan-v7-SEMPUBLISHRACE.md` while also naming
  `SEMDEVREBOUND` as the next downstream phase. This phase must advance the
  evidence artifact to the new plan path after execution without erasing the
  prior trace-freshness and publish-race lineage.

Practical planning boundary:

- SEMDEVREBOUND may introduce the smallest exact recovery needed for the
  renewed `.devcontainer/devcontainer.json` seam: an exact bounded JSON
  indexing path, the smallest dispatcher-side lexical closeout repair needed
  to make timeout truthfully terminal for this file family, or the smallest
  combination needed to carry the live rerun past the renewed `.devcontainer`
  re-anchor.
- SEMDEVREBOUND must stay narrow and evidence-driven. It must not reopen
  `tests/test_artifact_publish_race.py`, `ai_docs/jedi.md`,
  `ai_docs/*_overview.md`, the fast-test-report boundary, the visual-report
  boundary, or summary/vector phases unless the refreshed rerun directly
  re-anchors there again.

## Interface Freeze Gates

- [ ] IF-0-SEMDEVREBOUND-1 - Exact rebound trace contract:
      after the rerun has already advanced beyond
      `tests/test_artifact_publish_race.py`, a live repo-local
      `repository sync --force-full` no longer remains past the configured
      lexical-timeout window with
      `last_progress_path=/home/viperjuice/code/Code-Index-MCP/.devcontainer/post_create.sh`
      and
      `in_flight_path=/home/viperjuice/code/Code-Index-MCP/.devcontainer/devcontainer.json`
      while the durable trace timestamp stays unchanged.
- [ ] IF-0-SEMDEVREBOUND-2 - Exact bounded recovery contract:
      if this phase introduces a path-specific JSON recovery, it stays limited
      to `.devcontainer/devcontainer.json` or a stricter exact alias,
      preserves operator-visible indexing of that file family, and does not
      broaden into arbitrary `.json` files, repo-wide config files, or the
      whole `.devcontainer/` directory.
- [ ] IF-0-SEMDEVREBOUND-3 - Truthful lexical closeout contract:
      if the live rerun still cannot progress past the renewed `.devcontainer`
      seam, the durable trace and dispatcher stats exit with a bounded lexical
      blocker or timeout verdict that still names that exact file family
      truthfully instead of leaving a stale `status=running` snapshot behind.
- [ ] IF-0-SEMDEVREBOUND-4 - Operator status contract:
      `uv run mcp-index repository status` remains aligned with the configured
      timeout window, preserves the existing exact bounded lexical wording for
      `tests/test_artifact_publish_race.py` and older seams, and adds any new
      `.devcontainer` boundary line only if the implementation actually
      introduces that exact recovery path.
- [ ] IF-0-SEMDEVREBOUND-5 - Evidence contract:
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the rebound repair,
      the live rerun command and outcome, the durable trace timestamps and
      paths, and whether the rerun advances into later lexical or semantic
      work or exits with a new narrower blocker.
- [ ] IF-0-SEMDEVREBOUND-6 - Upstream-boundary preservation contract:
      SEMPUBLISHRACE, SEMFASTREPORT, SEMPYTESTOVERVIEW, SEMVISUALREPORT,
      SEMJEDI, and SEMTRACEFRESHNESS remain closed unless the refreshed rerun
      directly re-anchors on one of those exact seams again.

## Lane Index & Dependencies

- SL-0 - Renewed devcontainer rebound contract and fixture freeze; Depends on: SEMPUBLISHRACE; Blocks: SL-1, SL-2, SL-3; Parallel-safe: no
- SL-1 - Exact devcontainer rebound repair; Depends on: SL-0; Blocks: SL-2, SL-3; Parallel-safe: no
- SL-2 - Repository-status boundary alignment and blocker truthfulness; Depends on: SL-0, SL-1; Blocks: SL-3; Parallel-safe: no
- SL-3 - Dogfood evidence reducer and rerun refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SEMDEVREBOUND acceptance; Parallel-safe: no

Lane DAG:

```text
SEMPUBLISHRACE
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SEMDEVREBOUND acceptance
```

## Lanes

### SL-0 - Renewed Devcontainer Rebound Contract And Fixture Freeze

- **Scope**: Freeze the renewed `.devcontainer/post_create.sh ->
  .devcontainer/devcontainer.json` rebound shape in dispatcher coverage so this
  phase proves an exact recovery after the publish-race seam was cleared
  instead of only shifting the stale running trace elsewhere.
- **Owned files**: `tests/test_dispatcher.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMDEVREBOUND-1 through IF-0-SEMDEVREBOUND-3
- **Interfaces consumed**: existing
  `EnhancedDispatcher.index_directory(...)`,
  `EnhancedDispatcher._index_file_with_lexical_timeout(...)`,
  `_run_blocking_with_timeout(...)`,
  the current `.devcontainer/post_create.sh` plus
  `.devcontainer/devcontainer.json` blocker vocabulary from
  `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, and the existing exact bounded
  Python seam for `tests/test_artifact_publish_race.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` with a repo-shaped rebound fixture
    that freezes the current exact `.devcontainer` seam after a prior lexical
    step has already advanced beyond `tests/test_artifact_publish_race.py`.
  - test: Require the rebound fixture to prove the repaired path either
    completes lexical indexing for `.devcontainer/devcontainer.json` or
    returns a bounded lexical timeout/error instead of leaving the durable
    trace parked as a stale `status=running` snapshot.
  - test: Keep the fixture exact. Use repo-local
    `.devcontainer/post_create.sh` and `.devcontainer/devcontainer.json`
    inputs rather than broad `.json` fixtures so the contract stays tied to
    the live rebound evidence.
  - test: Keep negative assertions that unrelated `.json` files and the
    already-closed `tests/test_artifact_publish_race.py` seam do not inherit a
    new exact `.devcontainer` policy accidentally.
  - impl: Use monkeypatched chunker or dispatcher behavior and synthetic
    durable-trace payloads rather than multi-minute live waits inside unit
    coverage.
  - impl: Keep this lane focused on dispatcher contract freeze only. Do not
    update the operator status surface or the dogfood evidence artifact here.
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "devcontainer or lexical or timeout or artifact_publish_race"`

### SL-1 - Exact Devcontainer Rebound Repair

- **Scope**: Implement the smallest exact recovery needed so the renewed
  `.devcontainer/devcontainer.json` seam no longer leaves the live force-full
  rerun parked past the configured lexical-timeout window after the
  publish-race seam has already been cleared.
- **Owned files**: `mcp_server/plugins/generic_treesitter_plugin.py`, `mcp_server/dispatcher/dispatcher_enhanced.py`
- **Interfaces provided**: IF-0-SEMDEVREBOUND-1 exact rebound trace
  contract; IF-0-SEMDEVREBOUND-2 exact bounded recovery contract;
  IF-0-SEMDEVREBOUND-3 truthful lexical closeout contract
- **Interfaces consumed**: SL-0 rebound fixtures; the generic JSON plugin's
  unconditional `chunk_text(content, self.lang)` path; dispatcher lexical
  timeout handling; existing `last_progress_path` / `in_flight_path`
  accounting; and the live rebound evidence for
  `.devcontainer/post_create.sh -> .devcontainer/devcontainer.json`
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 dispatcher slice first and confirm the current
    checkout still has no exact bounded `.devcontainer` recovery or truthful
    terminal closeout under the frozen rebound fixture.
  - impl: Prefer the smallest exact repair that matches the live evidence. If
    the JSON chunking path is the root cause, add an exact normalized-path
    helper for `.devcontainer/devcontainer.json` or a stricter alias rather
    than a broad `.json` or `.devcontainer/*` bypass.
  - impl: If the live evidence shows the real defect is lexical-timeout
    closeout rather than JSON chunking itself, keep the fix local to
    dispatcher terminalization and do not add a speculative bounded-path
    exemption.
  - impl: Preserve operator-visible indexing for the renewed `.devcontainer`
    seam. Do not solve the stall by silently dropping the file from storage,
    progress reporting, or the repository-status trace.
  - impl: Preserve the existing exact bounded Python seam for
    `tests/test_artifact_publish_race.py` and the older Markdown/script seams.
    Do not reopen those earlier phases unless the refreshed live rerun
    directly re-anchors there again.
  - impl: Do not broaden to all `.json` files, all `.devcontainer/*` files,
    or a repo-wide timeout retune. Any allowlist or fast path must stay
    specific to the renewed rebound seam and be documented by code shape and
    tests.
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "devcontainer or lexical or timeout"`
  - verify: `rg -n "devcontainer|chunk_text|in_flight_path|last_progress_path" mcp_server/plugins/generic_treesitter_plugin.py mcp_server/dispatcher/dispatcher_enhanced.py tests/test_dispatcher.py`

### SL-2 - Repository-Status Boundary Alignment And Blocker Truthfulness

- **Scope**: Keep the operator-facing status surface aligned with the renewed
  `.devcontainer` repair and the true live or terminal state of the rerun.
- **Owned files**: `mcp_server/cli/repository_commands.py`, `tests/test_repository_commands.py`
- **Interfaces provided**: IF-0-SEMDEVREBOUND-4 operator status contract
- **Interfaces consumed**: SL-0 rebound fixtures; SL-1 exact repair choice;
  existing boundary helpers for fast-test reports, `ai_docs/*_overview.md`,
  `ai_docs/jedi.md`, `scripts/create_multi_repo_visual_report.py`, and
  `tests/test_artifact_publish_race.py`; plus the current durable
  stale-running trace rendering
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_repository_commands.py` so `repository status`
    freezes the renewed `.devcontainer/post_create.sh ->
    .devcontainer/devcontainer.json` rebound trace while preserving the
    existing exact bounded Python line for `tests/test_artifact_publish_race.py`.
  - test: Preserve the existing lexical-boundary lines for generated fast-test
    reports, `ai_docs/*_overview.md`, `ai_docs/jedi.md`,
    `scripts/create_multi_repo_visual_report.py`, and
    `tests/test_artifact_publish_race.py` so this phase remains additive.
  - test: Require stale-running freshness, `last_progress_path`, and
    `in_flight_path` output to stay truthful whether the renewed `.devcontainer`
    repair fully clears the seam or only makes timeout closeout bounded and
    explicit.
  - impl: If SL-1 introduces an exact `.devcontainer` bounded path, add the
    matching minimal repository-status boundary helper so operators can see
    that this rebound seam is intentional and exact.
  - impl: If SL-1 solves the issue entirely in timeout closeout without an
    exact bounded path, keep this lane limited to truthful blocker/freshness
    rendering and do not add misleading `.devcontainer` boundary copy.
  - impl: Keep timeout semantics fail-closed and preserve the existing
    publish-race boundary wording; if the live rerun still blocks after the
    repair, report the true downstream blocker rather than claiming lexical or
    semantic readiness early.
  - verify: `uv run pytest tests/test_repository_commands.py -q --no-cov -k "devcontainer or force_full or boundary or stale-running"`
  - verify: `rg -n "devcontainer|artifact_publish_race|Lexical boundary|Trace freshness|Last progress path|In-flight path" mcp_server/cli/repository_commands.py tests/test_repository_commands.py`

### SL-3 - Dogfood Evidence Reducer And Rerun Refresh

- **Scope**: Refresh the repo-local dogfood report so it records the rebound
  repair, the live rerun outcome, and the next exact blocker if semantic-stage
  work still does not begin.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: IF-0-SEMDEVREBOUND-5 evidence contract;
  IF-0-SEMDEVREBOUND-6 upstream-boundary preservation contract
- **Interfaces consumed**: SL-1 exact rebound repair; SL-2 repository-status
  wording; roadmap SEMDEVREBOUND exit criteria; prior SEMTRACEFRESHNESS and
  SEMPUBLISHRACE evidence lineage; and the older fast-report,
  `ai_docs/*_overview.md`, exact Jedi, and visual-report boundary history
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/docs/test_semdogfood_evidence_contract.py` so the
    refreshed report cites `plans/phase-plan-v7-SEMDEVREBOUND.md`, the live
    rerun command and timestamps, the renewed
    `.devcontainer/post_create.sh` plus
    `.devcontainer/devcontainer.json` trace pair, and the next exact blocker
    if semantic-stage work still does not begin.
  - test: Require the report to preserve the older trace-freshness and
    publish-race lineage while making clear that the active seam is now the
    renewed `.devcontainer` lexical re-anchor.
  - test: Require the report to say whether the rerun advanced into later
    lexical work, reached semantic closeout, or exited with a new narrower
    bounded blocker after the rebound repair.
  - impl: Refresh `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` with the live
    rerun command, observed commit IDs, durable trace contents,
    repository-status output, and the steering verdict after the renewed
    `.devcontainer` seam is repaired or truthfully terminalized.
  - impl: Keep the report factual and durable. Record exact timestamps,
    `last_progress_path`, `in_flight_path`, trace `status`, stage family,
    blocker source, and chunk/vector counts without claiming semantic success
    before the evidence exists.
  - impl: If the rerun still does not begin semantic work, name the next exact
    blocker directly and keep SEMDEVREBOUND itself scoped to the renewed
    `.devcontainer` seam once that seam is no longer a stale-running trace.
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
  - verify: `rg -n "SEMDEVREBOUND|devcontainer.json|Trace status|Trace stage|Last progress path|In-flight path|next exact blocker" docs/status/SEMANTIC_DOGFOOD_REBUILD.md tests/docs/test_semdogfood_evidence_contract.py`

## Verification

Planning-only run: do not execute these during plan creation. Run them during
`codex-execute-phase` or manual SEMDEVREBOUND execution.

Lane-specific checks:

```bash
uv run pytest tests/test_dispatcher.py -q --no-cov -k "devcontainer or lexical or timeout or artifact_publish_race"
uv run pytest tests/test_repository_commands.py -q --no-cov -k "devcontainer or force_full or boundary or stale-running"
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
rg -n "devcontainer|artifact_publish_race|Lexical boundary|Trace freshness|Last progress path|In-flight path|SEMDEVREBOUND" \
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
git status --short -- specs/phase-plans-v7.md plans/phase-plan-v7-SEMDEVREBOUND.md
```

## Acceptance Criteria

- [ ] A live repo-local force-full rerun no longer remains past the configured
      lexical-timeout window with
      `last_progress_path=/home/viperjuice/code/Code-Index-MCP/.devcontainer/post_create.sh`
      and
      `in_flight_path=/home/viperjuice/code/Code-Index-MCP/.devcontainer/devcontainer.json`
      once the rerun has already advanced beyond
      `tests/test_artifact_publish_race.py`.
- [ ] The chosen repair for the renewed `.devcontainer/devcontainer.json` seam
      stays exact or narrower than that file family, is covered by targeted
      tests, and does not broaden into a repo-wide `.json` or config-file
      bypass.
- [ ] The rerun either completes the renewed `.devcontainer/devcontainer.json`
      lexical seam and advances into later lexical or semantic work, or exits
      with a bounded lexical blocker that still names that exact file family
      truthfully.
- [ ] `uv run mcp-index repository status` remains aligned with the configured
      timeout window, preserves the existing exact bounded
      `tests/test_artifact_publish_race.py` wording and older boundary lines,
      and adds `.devcontainer` boundary copy only if that exact repair is
      active.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is refreshed with the rebound
      repair evidence, the rerun outcome, and the next exact blocker if
      semantic-stage work still does not begin.
- [ ] SEMPUBLISHRACE, SEMFASTREPORT, SEMPYTESTOVERVIEW, SEMVISUALREPORT,
      SEMJEDI, and SEMTRACEFRESHNESS remain closed unless the refreshed rerun
      directly re-anchors on one of those exact seams again.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v7-SEMDEVREBOUND.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMDEVREBOUND.md
  artifact_state: staged
```
