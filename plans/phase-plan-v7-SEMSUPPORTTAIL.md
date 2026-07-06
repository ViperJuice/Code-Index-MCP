---
phase_loop_plan_version: 1
phase: SEMSUPPORTTAIL
roadmap: specs/phase-plans-v7.md
roadmap_sha256: f78c780c094767cd0e3348a99a8cc92301033eb763e358fb2f239c2efdab2108
---
# SEMSUPPORTTAIL: Support Docs Tail Recovery

## Context

SEMSUPPORTTAIL is the phase-63 follow-up for the v7 semantic hardening roadmap.
Canonical `.phase-loop/` state is authoritative for this run, but it currently
reports `SEMDOCTRUTHTAIL` as the current `blocked` phase on `HEAD`
`a7a71f2404750f62ba0bffa08d86627c8998b56d` with
`main...origin/main [ahead 120]`, `human_required: true`, and blocker class
`dirty_worktree_conflict`. The same canonical state already lists
`SEMSUPPORTTAIL` as `unplanned`, and the user explicitly requested that this
execution-mode planning run write the downstream repo-local plan artifact now.
Legacy `.codex/phase-loop/` artifacts remain compatibility-only and do not
supersede canonical `.phase-loop/` state here.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is tracked and currently staged in this worktree,
  and `sha256sum specs/phase-plans-v7.md` matches the required
  `f78c780c094767cd0e3348a99a8cc92301033eb763e358fb2f239c2efdab2108`.
- Canonical `.phase-loop/state.json` and `.phase-loop/tui-handoff.md` agree
  that the runner is blocked on unowned dirty paths
  `.index_metadata.json`,
  `.mcp-index/force_full_exit_trace.json`,
  `.mcp-index/semantic_qdrant/.lock`, and
  `.mcp-index/semantic_qdrant/meta.json`.
  That blocker does not prevent writing this requested plan artifact, but it
  does prevent claiming the downstream phase is immediately runnable.
- The target artifact `plans/phase-plan-v7-SEMSUPPORTTAIL.md` did not exist
  before this planning run.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is the active evidence anchor. Its
  SEMDOCTRUTHTAIL rerun block records the current downstream lexical blocker
  precisely: the refreshed repo-local command
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  started on observed commit `a7a71f24`, and at `2026-04-29T19:51:51Z`
  `.mcp-index/force_full_exit_trace.json` showed
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/docs/markdown-table-of-contents.md`
  with
  `in_flight_path=/home/viperjuice/code/Code-Index-MCP/docs/SUPPORT_MATRIX.md`;
  at `2026-04-29T19:52:03Z`, `repository status` terminalized that running
  snapshot to `Trace status: interrupted` with the same exact support-doc pair
  while advertising the repaired exact bounded Python surface for the cleared
  `tests/docs/test_p23_doc_truth.py ->
  tests/docs/test_semdogfood_evidence_contract.py` seam.
- The blocked support docs are both Markdown but they have materially different
  shapes.
  `docs/markdown-table-of-contents.md` is `202` lines / `9529` bytes and is a
  generated inventory with many headings and tables.
  `docs/SUPPORT_MATRIX.md` is `145` lines / `18517` bytes and is the canonical
  GASUPPORT surface with large language and install-surface tables. Both files
  are far below `_LIGHTWEIGHT_MARKDOWN_BYTES = 250_000`, so the active seam is
  not a generic size cutoff.
- `mcp_server/plugins/markdown_plugin/plugin.py` already has lightweight-name
  routes for changelog, roadmap, analysis, `AGENTS.md`, `README.md`, and
  `ai_docs/*_overview.md`, plus exact bounded Markdown paths for
  `.claude/commands/execute-lane.md`,
  `.claude/commands/plan-phase.md`,
  `ai_docs/jedi.md`,
  `docs/validation/ga-closeout-decision.md`,
  `docs/validation/mre2e-evidence.md`,
  `docs/benchmarks/mcp_vs_native_benchmark_fullrepo_fireworks_qwen_voyage_local_iter5_rerun.md`,
  `docs/benchmarks/production_benchmark.md`,
  `plans/phase-plan-v7-SEMPHASETAIL.md`,
  `plans/phase-plan-v5-gagov.md`,
  `plans/phase-plan-v6-WATCH.md`, and
  `plans/phase-plan-v1-p19.md`.
  It does not yet include either
  `docs/markdown-table-of-contents.md` or `docs/SUPPORT_MATRIX.md`, and their
  stems do not match an existing bounded-name rule.
- `mcp_server/cli/repository_commands.py` already prints exact bounded Markdown
  lexical boundaries for `ai_docs/jedi.md`, validation docs, benchmark docs,
  `.claude/commands`, and selected phase-plan pairs, but it does not yet expose
  a matching support-doc boundary for
  `docs/markdown-table-of-contents.md -> docs/SUPPORT_MATRIX.md`.
- Existing tests are adjacent but incomplete for this seam.
  `tests/test_dispatcher.py` covers current bounded Markdown routing,
  `tests/test_git_index_manager.py` and `tests/test_repository_commands.py`
  freeze durable trace and status wording for earlier seams, and
  `tests/docs/test_semdogfood_evidence_contract.py` already requires the
  evidence artifact to retain both support-doc paths and downstream steering to
  `SEMSUPPORTTAIL`. `tests/docs/test_p23_doc_truth.py` already freezes the
  support-matrix columns, stable-surface wording, and agent-doc links that must
  survive any doc-local simplification in this phase.

Practical planning boundary:

- SEMSUPPORTTAIL may implement one exact recovery for
  `docs/markdown-table-of-contents.md -> docs/SUPPORT_MATRIX.md`: an exact
  bounded Markdown indexing path, the smallest doc-local simplification inside
  that pair, or the minimum combination needed to move the live rerun durably
  beyond `docs/SUPPORT_MATRIX.md`.
- SEMSUPPORTTAIL must stay narrow and evidence-driven. It must not widen into a
  blanket `docs/*.md` or support-doc bypass, repo-wide Markdown lightweight
  mode, a reopening of the repaired SEMDOCTRUTHTAIL docs-truth seam, or a
  silent clearing of the canonical `.phase-loop` dirty-worktree blocker via
  legacy compatibility artifacts.

## Interface Freeze Gates

- [ ] IF-0-SEMSUPPORTTAIL-1 - Exact support-doc recovery contract:
      a refreshed repo-local force-full rerun on the post-SEMDOCTRUTHTAIL head
      no longer terminalizes with the durable lexical trace centered on
      `docs/markdown-table-of-contents.md -> docs/SUPPORT_MATRIX.md`; it either
      advances durably beyond `docs/SUPPORT_MATRIX.md` or emits a truthful newer
      blocker before the 120-second watchdog expires.
- [ ] IF-0-SEMSUPPORTTAIL-2 - Bounded Markdown repair contract:
      the chosen repair remains limited to the exact support-doc pair and the
      immediate Markdown or dispatcher or trace or status or evidence plumbing
      needed to prove it; it does not broaden into arbitrary `docs/*.md`,
      repo-wide Markdown lightweight mode, or a generic support-doc exemption.
- [ ] IF-0-SEMSUPPORTTAIL-3 - Lexical discoverability contract:
      both support docs remain lexically discoverable after the repair,
      including durable file storage plus document-title or heading symbols and
      stored text needed for support-matrix and documentation-index lookup,
      instead of turning either file into an indexing blind spot.
- [ ] IF-0-SEMSUPPORTTAIL-4 - Trace and operator truthfulness contract:
      `force_full_exit_trace.json`, `EnhancedDispatcher`,
      `GitAwareIndexManager`, and `uv run mcp-index repository status` agree on
      the repaired support-doc outcome and do not regress to stale
      SEMDOCTRUTHTAIL-only boundary wording once the live rerun advances beyond
      the pair.
- [ ] IF-0-SEMSUPPORTTAIL-5 - Evidence and contract-refresh contract:
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the SEMDOCTRUTHTAIL
      rerun outcome, the repaired SEMSUPPORTTAIL rerun command and timestamps,
      the refreshed durable trace and status output, and the final
      authoritative verdict for the support-doc blocker; any edits to
      `tests/docs/test_p23_doc_truth.py` must preserve the canonical support
      statement and required table columns while reducing only the active
      lexical hotspot.
- [ ] IF-0-SEMSUPPORTTAIL-6 - Downstream steering and runner-truth contract:
      if execution reveals a blocker beyond the current roadmap tail,
      `specs/phase-plans-v7.md` is amended before closeout so the next
      phase-loop step is truthful; if the only remaining stop is the canonical
      `.phase-loop` dirty-worktree blocker, that blocker remains explicit in the
      closeout handoff instead of being masked by compatibility artifacts.

## Lane Index & Dependencies

- SL-0 - Exact support-doc fixture freeze; Depends on: SEMDOCTRUTHTAIL; Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 - Exact support-doc bounded Markdown recovery or minimal doc-local simplification; Depends on: SL-0; Blocks: SL-2, SL-3, SL-4; Parallel-safe: no
- SL-2 - Force-full trace and repository-status alignment; Depends on: SL-0, SL-1; Blocks: SL-3, SL-4; Parallel-safe: no
- SL-3 - Live rerun evidence reducer and support-doc contract refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SL-4; Parallel-safe: no
- SL-4 - Downstream roadmap steering reducer; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: SEMSUPPORTTAIL acceptance; Parallel-safe: no

Lane DAG:

```text
SEMDOCTRUTHTAIL
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SL-4 -> SEMSUPPORTTAIL acceptance
```

## Lanes

### SL-0 - Exact Support-Doc Fixture Freeze

- **Scope**: Freeze the exact
  `docs/markdown-table-of-contents.md -> docs/SUPPORT_MATRIX.md` lexical seam
  in deterministic dispatcher coverage before runtime changes so this phase
  proves a narrow support-doc recovery instead of hand-waving around Markdown
  generally.
- **Owned files**: `tests/test_dispatcher.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMSUPPORTTAIL-1,
  IF-0-SEMSUPPORTTAIL-2,
  and IF-0-SEMSUPPORTTAIL-3 at the dispatcher/Markdown boundary
- **Interfaces consumed**: existing
  `EnhancedDispatcher.index_directory(...)`,
  `MarkdownPlugin._resolve_lightweight_reason(...)`,
  `MarkdownPlugin._build_lightweight_index_shard(...)`,
  `MarkdownPlugin.indexFile(...)`,
  and the SEMDOCTRUTHTAIL evidence for the later support-doc pair
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` with repo-shaped fixtures for
    `docs/markdown-table-of-contents.md` and `docs/SUPPORT_MATRIX.md` that
    prove the repaired path preserves stored file rows, document-title symbols,
    heading symbols, and FTS-backed file content while avoiding the heavy
    Markdown path for the exact support-doc pair.
  - test: Add negative guards so earlier bounded Markdown seams
    (`ai_docs/*_overview.md`, `ai_docs/jedi.md`, validation docs, benchmark
    docs, `.claude/commands`, and existing phase-plan pairs) plus the repaired
    SEMDOCTRUTHTAIL Python seam do not silently regress while the support-doc
    pair is added.
  - test: Assert that `docs/SUPPORT_MATRIX.md` remains discoverable for the
    required support and surface table headers, and that
    `docs/markdown-table-of-contents.md` retains its document title and current
    navigation headings after the repair.
  - impl: Keep fixtures deterministic with repo-local Markdown strings and
    monkeypatched bounded-path instrumentation rather than long-running live
    waits inside unit tests.
  - impl: Keep this lane on contract freeze only. Do not mutate durable trace,
    CLI wording, evidence docs, or roadmap steering here.
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "support_matrix or markdown_table_of_contents or support_docs or markdown or lexical or bounded"`

### SL-1 - Exact Support-Doc Bounded Markdown Recovery Or Minimal Doc-Local Simplification

- **Scope**: Implement the smallest exact repair needed so the later
  support-doc pair can complete lexical indexing under the existing watchdog
  without broadening repo-wide Markdown behavior.
- **Owned files**: `mcp_server/plugins/markdown_plugin/plugin.py`, `docs/markdown-table-of-contents.md`, `docs/SUPPORT_MATRIX.md`
- **Interfaces provided**: IF-0-SEMSUPPORTTAIL-1 exact support-doc recovery
  contract; IF-0-SEMSUPPORTTAIL-2 bounded Markdown repair contract;
  IF-0-SEMSUPPORTTAIL-3 lexical discoverability contract
- **Interfaces consumed**: SL-0 support-doc fixtures; existing
  `_resolve_lightweight_reason(...)`,
  `_build_lightweight_index_shard(...)`,
  the current heading and table structure in
  `docs/markdown-table-of-contents.md`,
  and the current heading and table structure in `docs/SUPPORT_MATRIX.md`
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 dispatcher slice first and confirm whether the current
    checkout still reproduces the later support-doc seam or simply leaves the
    exact repair path unimplemented.
  - impl: Determine whether the minimal repair belongs in
    `_EXACT_BOUNDED_MARKDOWN_PATHS`, the support docs themselves, or the
    smallest combination required to let lexical indexing finish on
    `docs/SUPPORT_MATRIX.md`.
  - impl: If a bounded-path repair is chosen, keep it exact to
    `docs/markdown-table-of-contents.md` and `docs/SUPPORT_MATRIX.md`. Do not
    introduce a broad `docs/*.md`, repository-wide Markdown lightweight mode,
    or generic support-doc fast path.
  - impl: If a doc-local simplification is chosen, preserve the support-matrix
    contract frozen by `tests/docs/test_p23_doc_truth.py`: the required support
    and install-surface table headers, stable-surface wording, topology and
    readiness caveats, and the canonical release-boundary references. Preserve
    the navigation value and top-level headings of
    `docs/markdown-table-of-contents.md`.
  - impl: Preserve lexical file storage and document/heading discoverability
    for both support docs. The repair must not turn either document into an
    ignored file or silently remove it from lexical FTS.
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "support_matrix or markdown_table_of_contents or support_docs or markdown or bounded"`
  - verify: `rg -n "markdown-table-of-contents|SUPPORT_MATRIX|_EXACT_BOUNDED_MARKDOWN_PATHS|_resolve_lightweight_reason|support matrix|Claim tiers|Machine-checkable support facts" mcp_server/plugins/markdown_plugin/plugin.py docs/markdown-table-of-contents.md docs/SUPPORT_MATRIX.md tests/test_dispatcher.py`

### SL-2 - Force-Full Trace And Repository-Status Alignment

- **Scope**: Carry the chosen support-doc repair through durable trace closeout
  and keep the operator-facing status surface aligned with the exact later
  blocker or recovery outcome.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `mcp_server/storage/git_index_manager.py`, `mcp_server/cli/repository_commands.py`, `tests/test_git_index_manager.py`, `tests/test_repository_commands.py`
- **Interfaces provided**: IF-0-SEMSUPPORTTAIL-4 trace and operator
  truthfulness contract; the runner-truth portion of IF-0-SEMSUPPORTTAIL-6
- **Interfaces consumed**: SL-0 support-doc fixture vocabulary; SL-1 chosen
  repair; the current force-full trace writer and finalizer; existing Markdown
  boundary helpers for `ai_docs`, validation docs, benchmark docs,
  `.claude/commands`, and phase-plan pairs; and the current lexical
  trace/status wording in `repository status`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_git_index_manager.py` so durable force-full trace
    persistence freezes the support-doc pair as
    `last_progress_path -> in_flight_path`, preserves truthful interrupted
    finalization semantics, and requires the final durable trace to move past
    `docs/SUPPORT_MATRIX.md` or expose a newer later blocker.
  - test: Extend `tests/test_repository_commands.py` so
    `uv run mcp-index repository status` must advertise the exact support-doc
    Markdown boundary
    `docs/markdown-table-of-contents.md -> docs/SUPPORT_MATRIX.md` when both
    files exist and the durable trace has already advanced into or beyond that
    pair.
  - impl: Add the smallest boundary printer and trace-alignment logic needed
    for the exact support-doc pair beside the existing validation, benchmark,
    `.claude`, phase-plan, script, JSON, and ignored-`test_workspace/` helpers.
  - impl: Preserve the current trace vocabulary fields `Trace status`,
    `Trace stage`, `Trace stage family`, `Trace blocker source`,
    `last_progress_path`, and `in_flight_path`; this lane should only align
    them with the repaired support-doc outcome.
  - impl: Do not generalize status wording into all support docs or all
    Markdown files, and do not treat the canonical `.phase-loop`
    dirty-worktree blocker as resolved unless closeout explicitly resolves the
    same unowned dirty paths.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "support_matrix or markdown_table_of_contents or support_docs or lexical or interrupted or boundary"`

### SL-3 - Live Rerun Evidence Reducer And Support-Doc Contract Refresh

- **Scope**: Re-run the repaired repo-local force-full sequence, reduce the
  outcome into the durable semantic dogfood evidence artifact, and keep the
  support-doc truth contract aligned with the exact current-head verdict.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_p23_doc_truth.py`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: IF-0-SEMSUPPORTTAIL-1 exact support-doc recovery
  contract; IF-0-SEMSUPPORTTAIL-3 lexical discoverability contract;
  IF-0-SEMSUPPORTTAIL-5 evidence and contract-refresh contract
- **Interfaces consumed**: SL-0 support-doc fixture expectations; SL-1 chosen
  repair; SL-2 trace and operator wording; the current evidence structure in
  `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`; and the current support-matrix
  truth contract frozen by `tests/docs/test_p23_doc_truth.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/docs/test_semdogfood_evidence_contract.py` so the
    evidence artifact must retain the SEMDOCTRUTHTAIL rerun outcome, the
    `SEMSUPPORTTAIL` plan path, the SEMSUPPORTTAIL rerun command and
    timestamps, the repaired exact lexical-boundary wording for
    `docs/markdown-table-of-contents.md -> docs/SUPPORT_MATRIX.md`, and the
    correct downstream steering if a newer blocker appears beyond the current
    roadmap tail.
  - test: Keep `tests/docs/test_p23_doc_truth.py` aligned with the intended
    public-doc truth contract. Only change it if the refreshed rerun or the
    chosen doc-local repair proves a narrower local contract edit is necessary
    to clear the active lexical hotspot without diluting the canonical support
    statement.
  - impl: Refresh `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` with the
    SEMDOCTRUTHTAIL acceptance outcome, the SEMSUPPORTTAIL live rerun command,
    timestamps, trace snapshot, repository-status output, runtime counts, and
    final verdict for the later support-doc pair.
  - impl: Keep the evidence truthful about lexical-only progress.
    `chunk_summaries` and `semantic_points` may remain zero here; do not imply
    semantic closeout, GA support expansion, or a clean phase-loop closeout
    unless the rerun and closeout artifacts actually prove those outcomes.
  - impl: If the active hotspot turns out to be duplicated literal structure in
    one of the support docs rather than the routing layer, keep any doc-local
    edit exact and contract-preserving: reduce only the structure that the live
    rerun proves is active while preserving support-matrix claims and current
    documentation navigation intent.
  - verify: `uv run pytest tests/docs/test_p23_doc_truth.py tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
  - verify: `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - verify: `sed -n '1,240p' .mcp-index/force_full_exit_trace.json`
  - verify: `sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'`

### SL-4 - Downstream Roadmap Steering Reducer

- **Scope**: Keep the roadmap and next phase-loop step truthful if the repaired
  live rerun proves a blocker beyond the current roadmap tail, while preserving
  the current canonical closeout blocker if it remains the only stop.
- **Owned files**: `specs/phase-plans-v7.md`
- **Interfaces provided**: IF-0-SEMSUPPORTTAIL-6 downstream steering and
  runner-truth contract
- **Interfaces consumed**: SL-3 refreshed evidence verdict; current roadmap DAG
  and phase ordering for `specs/phase-plans-v7.md`; the already staged
  SEMSUPPORTTAIL-era roadmap bytes; and canonical `.phase-loop/` expectations
  that the next unplanned phase reflects the latest durable blocker rather than
  stale prior assumptions
- **Parallel-safe**: no
- **Tasks**:
  - test: Re-read the post-SL-3 evidence and confirm whether the repaired rerun
    actually exposes a newer blocker beyond the current roadmap tail before
    mutating roadmap steering.
  - impl: If the active blocker remains the exact support-doc pair, leave the
    roadmap unchanged.
  - impl: If the support-doc seam is cleared and the only remaining stop is the
    canonical `.phase-loop` dirty-worktree blocker, leave the roadmap unchanged
    and keep that blocker explicit in the closeout handoff.
  - impl: If the active blocker advances beyond the current roadmap tail and no
    downstream phase already covers it, append the nearest truthful downstream
    recovery phase to `specs/phase-plans-v7.md` with the same evidence-first
    structure used by the current SEM* lexical-recovery chain.
  - impl: Keep any roadmap mutation limited to the newly exposed blocker and
    preserve the already staged SEMSUPPORTTAIL-era edits instead of rewriting
    earlier phases.
  - verify: `git diff -- specs/phase-plans-v7.md`

## Verification

- Lane checks:
  - `uv run pytest tests/test_dispatcher.py -q --no-cov -k "support_matrix or markdown_table_of_contents or support_docs or markdown or lexical or bounded"`
  - `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "support_matrix or markdown_table_of_contents or support_docs or lexical or interrupted or boundary"`
  - `uv run pytest tests/docs/test_p23_doc_truth.py tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
- Whole-phase checks:
  - `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_repository_commands.py tests/docs/test_p23_doc_truth.py tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "support_matrix or markdown_table_of_contents or support_docs or markdown or lexical or bounded or interrupted or boundary"`
  - `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  - `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - `sed -n '1,240p' .mcp-index/force_full_exit_trace.json`
  - `sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'`
  - `git diff --check`
  - `git diff --cached --check`

## Acceptance Criteria

- [ ] A refreshed repo-local force-full rerun on the post-SEMDOCTRUTHTAIL head
      either advances durably beyond
      `docs/markdown-table-of-contents.md -> docs/SUPPORT_MATRIX.md` or emits a
      truthful newer blocker before the 120-second watchdog expires.
- [ ] The repair stays narrowly scoped to the exact support-doc pair and the
      immediate Markdown or dispatcher or trace or status or evidence plumbing
      needed to prove it.
- [ ] Both support docs remain lexically discoverable with durable file storage
      plus bounded document and heading discoverability, and
      `docs/SUPPORT_MATRIX.md` retains the canonical support and install-surface
      table headers required by `tests/docs/test_p23_doc_truth.py`.
- [ ] `uv run mcp-index repository status` and
      `force_full_exit_trace.json` stay aligned with the repaired support-doc
      outcome and do not regress to stale SEMDOCTRUTHTAIL-only wording.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the SEMDOCTRUTHTAIL
      rerun outcome and the final live verdict for the later support-doc pair.
- [ ] If execution reveals a newer blocker beyond the current roadmap tail,
      `specs/phase-plans-v7.md` is updated before closeout so the next
      phase-loop step is truthful; otherwise any remaining canonical
      `.phase-loop` dirty-worktree blocker stays explicit until resolved.

automation:
  status: blocked
  next_skill: none
  next_command: none
  next_model_hint: execute
  next_effort_hint: medium
  human_required: true
  blocker_class: dirty_worktree_conflict
  blocker_summary: Phase reported verified dirty closeout but left dirty paths that are not closeout-safe. (unowned dirty paths: .index_metadata.json, .mcp-index/force_full_exit_trace.json, .mcp-index/semantic_qdrant/.lock, .mcp-index/semantic_qdrant/meta.json)
  required_human_inputs:
    - Review or isolate unowned dirty paths before rerunning the loop: .index_metadata.json, .mcp-index/force_full_exit_trace.json, .mcp-index/semantic_qdrant/.lock, .mcp-index/semantic_qdrant/meta.json
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMSUPPORTTAIL.md
  artifact_state: staged
