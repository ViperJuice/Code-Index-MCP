---
phase_loop_plan_version: 1
phase: SEMVERIFYAPIREBOUNDTAIL
roadmap: specs/phase-plans-v7.md
roadmap_sha256: 1a98d69f846cfe8fc9ba627c159df424f0843ffefd4710030e89dafe16f97813
---
# SEMVERIFYAPIREBOUNDTAIL: Verify/API Rebound Phase-Plan Tail Recovery

## Context

SEMVERIFYAPIREBOUNDTAIL is the phase-94 follow-up for the v7 semantic
hardening roadmap. Canonical `.phase-loop/` state is authoritative for this
run: `.phase-loop/state.json` and `.phase-loop/tui-handoff.md` both mark
`SEMVERIFYAPIREBOUNDTAIL` as the current `unplanned` phase after
`SEMLATEPHASEPLANTAIL` closed out on `HEAD`
`42a393c813bac0d025a9c2e9f3726f7ec9a33347` with verification `passed`, a
clean worktree, and `main...origin/main [ahead 183]`. Legacy
`.codex/phase-loop/` artifacts remain compatibility-only and do not
supersede canonical `.phase-loop/` runner state here.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is tracked and clean in this worktree, and
  `sha256sum specs/phase-plans-v7.md` matches the required
  `1a98d69f846cfe8fc9ba627c159df424f0843ffefd4710030e89dafe16f97813`.
- The target artifact `plans/phase-plan-v7-SEMVERIFYAPIREBOUNDTAIL.md` did
  not exist before this planning run.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is the active evidence anchor.
  Its SEMLATEPHASEPLANTAIL rerun block records the current downstream
  lexical blocker precisely: on observed commit
  `e80ecc46df93f5a4ae1bf0966ad675737888f3c9`, the refreshed repo-local
  command
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  advanced beyond the repaired
  `plans/phase-plan-v7-SEMCODEXLOOPRELAPSETAIL.md ->
  plans/phase-plan-v7-SEMGARELTAIL.md` seam; at `2026-04-30T05:36:39Z`,
  `.mcp-index/force_full_exit_trace.json` captured
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMVERIFYSIMTAIL.md`
  with
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMAPIDOCSTAIL.md`;
  at `2026-04-30T05:36:47Z`, `repository status` terminalized that running
  snapshot to `Trace status: interrupted` with the same exact rebound
  pair.
- The same rerun kept semantic state fail-closed rather than masking the
  lexical blocker: `files = 1199`, `code_chunks = 21254`,
  `chunk_summaries = 0`, `semantic_points = 0`, with `Readiness:
  stale_commit`, `Rollout status: partial_index_failure`, `Last sync
  error: disk I/O error`, and `Semantic readiness: summaries_missing`.
- The SEMLATEPHASEPLANTAIL target seam is no longer the active blocker:
  `plans/phase-plan-v7-SEMCODEXLOOPRELAPSETAIL.md ->
  plans/phase-plan-v7-SEMGARELTAIL.md`. The authoritative current-head
  blocker is now the rebound phase-plan seam
  `plans/phase-plan-v7-SEMVERIFYSIMTAIL.md ->
  plans/phase-plan-v7-SEMAPIDOCSTAIL.md`, so older downstream assumptions
  should be treated as stale after the roadmap amendment that introduced
  SEMVERIFYAPIREBOUNDTAIL.
- The two exact blocker files are both tracked phase-loop plan documents
  with similar overall size but different content focus.
  `plans/phase-plan-v7-SEMVERIFYSIMTAIL.md` is `394` lines / `22835`
  bytes and is centered on the later Python-script recovery for
  `scripts/verify_embeddings.py ->
  scripts/claude_code_behavior_simulator.py`.
  `plans/phase-plan-v7-SEMAPIDOCSTAIL.md` is `385` lines / `22454` bytes
  and is centered on the architecture/API Markdown seam
  `docs/architecture/P2B-known-limits.md ->
  docs/api/API-REFERENCE.md`. Both carry phase-loop frontmatter plus long
  `Context`, `Interface Freeze Gates`, `Lane Index & Dependencies`,
  `Verification`, `Acceptance Criteria`, and `Automation Handoff`
  sections.
- The Markdown plugin already has a generic lightweight phase-plan route.
  In `mcp_server/plugins/markdown_plugin/plugin.py`,
  `_ROADMAP_MARKDOWN_NAME_RE` matches stems like
  `phase-plan-v7-SEMVERIFYSIMTAIL` and
  `phase-plan-v7-SEMAPIDOCSTAIL`, so this phase should not assume the
  answer is automatically another exact-path exception in
  `_EXACT_BOUNDED_MARKDOWN_PATHS`. Execution should first prove whether the
  remaining watchdog burn is in dispatcher progress accounting, durable
  trace truth, operator-status wording, or a narrower phase-plan-path edge
  case.
- Current operator surfaces still freeze older phase-plan seams instead of
  the active rebound pair. `mcp_server/cli/repository_commands.py`,
  `tests/test_git_index_manager.py`, and `tests/test_repository_commands.py`
  currently advertise and test the earlier
  `plans/phase-plan-v7-SEMCODEXLOOPRELAPSETAIL.md ->
  plans/phase-plan-v7-SEMGARELTAIL.md` boundary, plus historical and
  mixed-version phase-plan boundaries, but not the current
  `plans/phase-plan-v7-SEMVERIFYSIMTAIL.md ->
  plans/phase-plan-v7-SEMAPIDOCSTAIL.md` rebound pair.
- Existing dispatcher coverage is also one seam behind. `tests/test_dispatcher.py`
  already freezes earlier exact-bounded late-v7, historical, and
  mixed-version phase-plan behavior, but repo search during planning did
  not show deterministic fixture coverage for the exact current rebound
  `SEMVERIFYSIMTAIL -> SEMAPIDOCSTAIL` pair.
- `tests/docs/test_semdogfood_evidence_contract.py` already requires the
  checked-in dogfood report to retain the current exact pair and the
  roadmap steering to `SEMVERIFYAPIREBOUNDTAIL`, so this phase should
  refresh the existing evidence artifact rather than inventing a new status
  surface.

Practical planning boundary:

- SEMVERIFYAPIREBOUNDTAIL may tighten exact phase-plan Markdown handling,
  dispatcher lexical progress accounting, durable trace persistence,
  operator status wording, and semantic dogfood evidence needed to prove a
  live rerun either advances beyond
  `plans/phase-plan-v7-SEMVERIFYSIMTAIL.md ->
  plans/phase-plan-v7-SEMAPIDOCSTAIL.md` or surfaces a truthful newer
  blocker.
- SEMVERIFYAPIREBOUNDTAIL must stay narrow and evidence-driven. It must not
  reopen the cleared
  `plans/phase-plan-v7-SEMCODEXLOOPRELAPSETAIL.md ->
  plans/phase-plan-v7-SEMGARELTAIL.md` seam, introduce a blanket
  `plans/phase-plan-v7-*.md` or repo-wide Markdown timeout bypass, or widen
  into unrelated semantic, integration, security, or compatibility work
  unless the refreshed rerun directly proves the blocker has moved again.

## Interface Freeze Gates

- [ ] IF-0-SEMVERIFYAPIREBOUNDTAIL-1 - Rebound phase-plan-tail advance
      contract: a refreshed repo-local force-full rerun on the
      post-SEMLATEPHASEPLANTAIL head no longer terminalizes with the
      durable lexical trace centered on
      `plans/phase-plan-v7-SEMVERIFYSIMTAIL.md ->
      plans/phase-plan-v7-SEMAPIDOCSTAIL.md`; it either advances durably
      beyond that pair or emits a truthful newer blocker before the
      120-second watchdog expires.
- [ ] IF-0-SEMVERIFYAPIREBOUNDTAIL-2 - Exact rebound seam contract: any
      repair introduced by this phase remains limited to the exact rebound
      phase-plan pair and the immediate Markdown or dispatcher or trace or
      status plumbing needed to clear it. The phase must not introduce a
      new blanket `plans/phase-plan-v7-*.md` exemption beyond the
      pre-existing generic lightweight phase-plan naming rule and must not
      reopen the cleared
      `plans/phase-plan-v7-SEMCODEXLOOPRELAPSETAIL.md ->
      plans/phase-plan-v7-SEMGARELTAIL.md` seam without direct evidence.
- [ ] IF-0-SEMVERIFYAPIREBOUNDTAIL-3 - Lexical discoverability contract:
      both exact rebound phase-plan files remain lexically discoverable
      after the repair, including durable file-level storage plus bounded
      document and heading discoverability for frontmatter title and
      high-signal sections such as `Context`, `Interface Freeze Gates`,
      `Lane Index & Dependencies`, `Verification`, `Acceptance Criteria`,
      and `Automation Handoff`, instead of turning either plan into an
      indexing blind spot.
- [ ] IF-0-SEMVERIFYAPIREBOUNDTAIL-4 - Durable trace and operator
      contract: `.mcp-index/force_full_exit_trace.json` and
      `uv run mcp-index repository status` stay aligned with the repaired
      outcome for the exact rebound phase-plan pair and do not regress to
      stale SEMLATEPHASEPLANTAIL-only wording or to the earlier
      `plans/phase-plan-v7-SEMCODEXLOOPRELAPSETAIL.md ->
      plans/phase-plan-v7-SEMGARELTAIL.md` boundary once the live rerun
      has advanced past it.
- [ ] IF-0-SEMVERIFYAPIREBOUNDTAIL-5 - Evidence and downstream steering
      contract: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMLATEPHASEPLANTAIL rerun outcome, the SEMVERIFYAPIREBOUNDTAIL rerun
      command and timestamps, the refreshed trace and status output, and
      the final authoritative verdict for the exact
      `plans/phase-plan-v7-SEMVERIFYSIMTAIL.md ->
      plans/phase-plan-v7-SEMAPIDOCSTAIL.md` pair; if execution reveals a
      blocker beyond the current roadmap tail, `specs/phase-plans-v7.md` is
      amended before closeout so the next phase-loop step is truthful.

## Lane Index & Dependencies

- SL-0 - Exact rebound phase-plan pair fixture freeze; Depends on: SEMLATEPHASEPLANTAIL; Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 - Minimal rebound phase-plan pair execution-path repair; Depends on: SL-0; Blocks: SL-2, SL-3, SL-4; Parallel-safe: no
- SL-2 - Durable trace persistence and operator rebound alignment; Depends on: SL-0, SL-1; Blocks: SL-3, SL-4; Parallel-safe: no
- SL-3 - Live rerun evidence reducer and rebound contract refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SL-4; Parallel-safe: no
- SL-4 - Downstream roadmap steering reducer; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: SEMVERIFYAPIREBOUNDTAIL acceptance; Parallel-safe: no

Lane DAG:

```text
SEMLATEPHASEPLANTAIL
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SL-4 -> SEMVERIFYAPIREBOUNDTAIL acceptance
```

## Lanes

### SL-0 - Exact Rebound Phase-Plan Pair Fixture Freeze

- **Scope**: Freeze the exact
  `plans/phase-plan-v7-SEMVERIFYSIMTAIL.md ->
  plans/phase-plan-v7-SEMAPIDOCSTAIL.md` lexical seam in deterministic
  dispatcher coverage before runtime changes so this phase proves a narrow
  recovery instead of hand-waving around the generic phase-plan family.
- **Owned files**: `tests/test_dispatcher.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMVERIFYAPIREBOUNDTAIL-1,
  IF-0-SEMVERIFYAPIREBOUNDTAIL-2,
  and IF-0-SEMVERIFYAPIREBOUNDTAIL-3 at the dispatcher and Markdown plugin
  boundary
- **Interfaces consumed**: existing `Dispatcher.index_directory(...)`;
  `MarkdownPlugin._resolve_lightweight_reason(...)`;
  `MarkdownPlugin._build_lightweight_index_shard(...)`; the current generic
  bounded Markdown routing for roadmap and phase-plan stems; and the
  SEMLATEPHASEPLANTAIL evidence for the exact rebound phase-plan pair
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` with repo-shaped fixtures that
    index exact copies or trimmed representatives of
    `plans/phase-plan-v7-SEMVERIFYSIMTAIL.md` and
    `plans/phase-plan-v7-SEMAPIDOCSTAIL.md`, prove the lexical walker
    records the exact pair in order, and fail if the repair silently turns
    them into an untracked blind spot.
  - test: In the same dispatcher coverage, assert that the repaired path
    keeps document-level and heading-level discoverability for frontmatter
    title plus high-signal sections such as `Context`, `Interface Freeze
    Gates`, `Lane Index & Dependencies`, `Verification`, `Acceptance
    Criteria`, and `Automation Handoff`.
  - test: Add a negative guard that unrelated phase-plan Markdown documents
    outside the exact pair still use the normal generic lightweight-name
    rule or heavy Markdown path as appropriate; the watchdog repair must
    not quietly become a broader `plans/phase-plan-v7-*.md` fast path.
  - impl: Keep fixtures deterministic with repo-local Markdown strings and
    monkeypatched bounded-path instrumentation rather than long-running
    live waits inside unit tests.
  - impl: Keep this lane on contract freeze only. Do not mutate durable
    trace, CLI wording, evidence docs, or roadmap steering here.
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "SEMVERIFYSIMTAIL or SEMAPIDOCSTAIL or phase_plan or markdown or lexical or bounded"`

### SL-1 - Minimal Rebound Phase-Plan Pair Execution-Path Repair

- **Scope**: Implement the smallest dispatcher or Markdown-path repair
  needed so the live lexical walker no longer burns its watchdog budget on
  the exact
  `plans/phase-plan-v7-SEMVERIFYSIMTAIL.md ->
  plans/phase-plan-v7-SEMAPIDOCSTAIL.md` pair.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `mcp_server/plugins/markdown_plugin/plugin.py`
- **Interfaces provided**: IF-0-SEMVERIFYAPIREBOUNDTAIL-2 exact rebound
  seam contract; IF-0-SEMVERIFYAPIREBOUNDTAIL-3 lexical discoverability
  contract
- **Interfaces consumed**: SL-0 phase-plan fixtures; existing generic
  phase-plan routing in `MarkdownPlugin._resolve_lightweight_reason(...)`;
  current single-file lexical progress handling in
  `dispatcher_enhanced.py`; and the existing bounded Markdown persistence
  semantics already used for roadmap, changelog, analysis, AGENTS, README,
  support-docs, docs-tail, and earlier phase-plan documents
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 dispatcher slice first and confirm what still makes
    the exact rebound phase-plan pair expensive in the current force-full
    path even though both stems already match the generic lightweight
    phase-plan rule.
  - impl: Apply the narrowest repair that clears the exact pair. Prefer
    reusing the existing generic bounded Markdown document and heading
    extraction path; only add exact-path logic if the tests and refreshed
    rerun prove the generic phase-plan rule is still insufficient for this
    pair in the live walker.
  - impl: Preserve frontmatter-derived title handling, section-heading
    discoverability, and file-level lexical storage for both exact plans.
    The repair must not reduce the pair to empty opaque files.
  - impl: Do not introduce a new blanket `plans/phase-plan-v7-*.md`
    dispatcher bypass, and do not widen into a repo-wide Markdown timeout
    change that masks other later blockers.
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "SEMVERIFYSIMTAIL or SEMAPIDOCSTAIL or phase_plan or markdown or bounded"`

### SL-2 - Durable Trace Persistence And Operator Rebound Alignment

- **Scope**: Carry the bounded rebound phase-plan repair through durable
  trace persistence and operator status output so the live rerun
  truthfully advances beyond the pair without stale
  SEMLATEPHASEPLANTAIL or older phase-plan-boundary wording.
- **Owned files**: `mcp_server/storage/git_index_manager.py`, `mcp_server/cli/repository_commands.py`, `tests/test_git_index_manager.py`, `tests/test_repository_commands.py`
- **Interfaces provided**: IF-0-SEMVERIFYAPIREBOUNDTAIL-1 rebound
  phase-plan pair advance contract; IF-0-SEMVERIFYAPIREBOUNDTAIL-4
  durable trace and operator contract
- **Interfaces consumed**: SL-0 dispatcher fixtures; SL-1 repaired bounded
  Markdown behavior; existing `GitAwareIndexManager._full_index(...)`,
  `GitAwareIndexManager.sync_repository_index(...)`,
  `_print_force_full_exit_trace(...)`; and the current exact-boundary
  status helpers for earlier v7-only, historical, and mixed-version
  phase-plan seams in `repository_commands.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_git_index_manager.py` so force-full durable
    trace persistence freezes the exact
    `plans/phase-plan-v7-SEMVERIFYSIMTAIL.md ->
    plans/phase-plan-v7-SEMAPIDOCSTAIL.md` handoff and proves later reruns
    do not regress to stale
    `plans/phase-plan-v7-SEMCODEXLOOPRELAPSETAIL.md ->
    plans/phase-plan-v7-SEMGARELTAIL.md` or other earlier phase-plan
    wording once execution advances past them.
  - test: Extend `tests/test_repository_commands.py` so
    `uv run mcp-index repository status` must advertise the exact rebound
    phase-plan Markdown boundary
    `plans/phase-plan-v7-SEMVERIFYSIMTAIL.md ->
    plans/phase-plan-v7-SEMAPIDOCSTAIL.md` when both files exist and the
    durable trace has already advanced into or beyond that pair.
  - impl: Add the smallest boundary-printer and durable-trace alignment
    needed for the exact rebound pair beside the existing support-docs,
    docs-tail, historical, mixed-version, and earlier phase-plan helpers.
  - impl: Preserve the current trace vocabulary fields `Trace status`,
    `Trace stage`, `Trace stage family`, `Trace blocker source`,
    `last_progress_path`, and `in_flight_path`; this lane should only
    align them with the repaired rebound phase-plan pair outcome.
  - impl: Do not generalize status wording into all phase-plan docs or a
    generic Markdown fast-path claim; the operator surface should stay
    exact.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "SEMVERIFYSIMTAIL or SEMAPIDOCSTAIL or phase_plan or lexical or interrupted or boundary"`

### SL-3 - Live Rerun Evidence Reducer And Rebound Contract Refresh

- **Scope**: Refresh the real dogfood evidence after the rebound
  phase-plan repair so the active blocker report matches the repaired
  runtime rather than stale SEMLATEPHASEPLANTAIL assumptions.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: the evidence portion of
  IF-0-SEMVERIFYAPIREBOUNDTAIL-5
- **Interfaces consumed**: SL-2 durable trace and repository-status
  output; live rerun command output; existing SEMLATEPHASEPLANTAIL
  evidence block; and the current evidence-contract assertions in
  `tests/docs/test_semdogfood_evidence_contract.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/docs/test_semdogfood_evidence_contract.py` only as
    needed so the evidence artifact must retain the
    SEMLATEPHASEPLANTAIL rerun outcome, the active
    SEMVERIFYAPIREBOUNDTAIL phase name, the exact current rebound
    phase-plan pair verdict, and any newly exposed downstream steering
    after execution.
  - impl: Run a fresh repo-local force-full rerun after SL-1 and SL-2 land,
    then capture the rerun command, observed commit, timeout or completion
    timestamp, durable trace snapshot, `repository status` output, and
    SQLite counts in `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`.
  - impl: If the repaired rerun still times out, record the exact later
    blocker pair or family that replaced
    `plans/phase-plan-v7-SEMVERIFYSIMTAIL.md ->
    plans/phase-plan-v7-SEMAPIDOCSTAIL.md` instead of leaving the old
    current pair or the earlier SEMLATEPHASEPLANTAIL seam as the active
    narrative.
  - impl: Keep this lane on evidence reduction. Do not back-edit older
    phase narratives except where the new rerun explicitly supersedes the
    active blocker statement.
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "SEMVERIFYAPIREBOUNDTAIL or SEMLATEPHASEPLANTAIL or SEMVERIFYSIMTAIL or SEMAPIDOCSTAIL or phase_plan"`

### SL-4 - Downstream Roadmap Steering Reducer

- **Scope**: Keep the roadmap and next phase-loop step truthful if the
  repaired live rerun proves a blocker beyond the current roadmap tail.
- **Owned files**: `specs/phase-plans-v7.md`
- **Interfaces provided**: the downstream-steering portion of
  IF-0-SEMVERIFYAPIREBOUNDTAIL-5
- **Interfaces consumed**: SL-3 refreshed evidence verdict; current
  roadmap DAG and phase ordering for `specs/phase-plans-v7.md`; and
  canonical `.phase-loop/` expectations that the next unplanned phase
  reflects the latest durable blocker rather than stale
  SEMLATEPHASEPLANTAIL assumptions
- **Parallel-safe**: no
- **Tasks**:
  - test: Re-read the post-SL-3 evidence and confirm whether the repaired
    rerun actually exposes a newer blocker beyond the current roadmap tail
    before mutating roadmap steering.
  - impl: If the active blocker remains inside the current
    SEMVERIFYAPIREBOUNDTAIL phase-plan family or the rerun completes
    lexical closeout, leave the roadmap unchanged.
  - impl: If the active blocker advances beyond the current roadmap tail
    and no downstream phase already covers it, append the nearest truthful
    downstream recovery phase to `specs/phase-plans-v7.md` with the same
    evidence-first structure used by the current SEM* lexical-recovery
    chain.
  - impl: Keep any roadmap mutation limited to the newly exposed blocker.
    Do not rewrite earlier phases or backfill unrelated sequencing while
    closing this seam.
  - verify: `git diff -- specs/phase-plans-v7.md`

## Verification

- Lane checks:
  - `uv run pytest tests/test_dispatcher.py -q --no-cov -k "SEMVERIFYSIMTAIL or SEMAPIDOCSTAIL or phase_plan or markdown or lexical or bounded"`
  - `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "SEMVERIFYSIMTAIL or SEMAPIDOCSTAIL or phase_plan or lexical or interrupted or boundary"`
  - `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "SEMVERIFYAPIREBOUNDTAIL or SEMLATEPHASEPLANTAIL or SEMVERIFYSIMTAIL or SEMAPIDOCSTAIL or phase_plan"`
- Whole-phase checks:
  - `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_repository_commands.py tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "SEMVERIFYAPIREBOUNDTAIL or SEMLATEPHASEPLANTAIL or SEMVERIFYSIMTAIL or SEMAPIDOCSTAIL or phase_plan or markdown or lexical or bounded or interrupted or boundary"`
  - `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  - `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - `sed -n '1,240p' .mcp-index/force_full_exit_trace.json`
  - `sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'`
  - `git status --short -- plans/phase-plan-v7-SEMVERIFYAPIREBOUNDTAIL.md docs/status/SEMANTIC_DOGFOOD_REBUILD.md specs/phase-plans-v7.md`
  - `git diff --check`
  - `git diff --cached --check`

## Acceptance Criteria

- [ ] A refreshed repo-local force-full rerun on the
      post-SEMLATEPHASEPLANTAIL head either advances durably beyond
      `plans/phase-plan-v7-SEMVERIFYSIMTAIL.md ->
      plans/phase-plan-v7-SEMAPIDOCSTAIL.md` or emits a truthful newer
      blocker before the 120-second watchdog expires.
- [ ] The repair stays narrowly scoped to the exact rebound phase-plan pair
      and the immediate dispatcher or Markdown or trace or status or
      evidence plumbing needed to prove it.
- [ ] Both exact rebound phase-plan files remain lexically discoverable
      with durable file storage plus bounded document and heading
      discoverability.
- [ ] `uv run mcp-index repository status` and
      `.mcp-index/force_full_exit_trace.json` stay aligned with the repaired
      rebound phase-plan boundary outcome and do not regress to stale
      SEMLATEPHASEPLANTAIL or earlier phase-plan-pair wording.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMLATEPHASEPLANTAIL rerun outcome and the final live verdict for the
      exact rebound phase-plan pair.
- [ ] If execution reveals a newer blocker beyond the current roadmap tail,
      `specs/phase-plans-v7.md` is updated before closeout so the next
      phase-loop step is truthful.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMVERIFYAPIREBOUNDTAIL.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMVERIFYAPIREBOUNDTAIL.md
  artifact_state: staged
```
