---
phase_loop_plan_version: 1
phase: SEMSCRIPTLANGSTAIL
roadmap: specs/phase-plans-v7.md
roadmap_sha256: 772ef3cf7412e1d26227fc1a7d9fc88454b60950b0a3df926840b36c237f8187
---
# SEMSCRIPTLANGSTAIL: Script Language Audit Tail Rebound Recovery

## Context

SEMSCRIPTLANGSTAIL is the phase-76 follow-up for the v7 semantic hardening
roadmap. Canonical `.phase-loop/` runtime exists in this checkout, so it is
the authoritative runner state for this planning run. The current canonical
snapshots agree cleanly: `.phase-loop/state.json` and
`.phase-loop/tui-handoff.md` both identify `SEMSCRIPTLANGSTAIL` as the
current `unplanned` phase for `specs/phase-plans-v7.md`, and the recorded
roadmap hash matches the user-required
`772ef3cf7412e1d26227fc1a7d9fc88454b60950b0a3df926840b36c237f8187`.
Legacy `.codex/phase-loop/` artifacts remain compatibility-only and do not
supersede canonical `.phase-loop/` state here.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is the active roadmap, and canonical
  `.phase-loop/state.json` records the same required hash
  `772ef3cf7412e1d26227fc1a7d9fc88454b60950b0a3df926840b36c237f8187`.
- The checkout is on `main...origin/main [ahead 147]` at `HEAD`
  `cdcbdb1c82ba374f415588d5eecdd1d0679c4a06`, the worktree is clean before
  this artifact write, and `plans/phase-plan-v7-SEMSCRIPTLANGSTAIL.md` did
  not exist before this run.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is the active evidence anchor.
  Its `SEMEDITRETRIEVALTAIL Live Rerun Check` block records that the refreshed
  repo-local command
  `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  advanced on observed commit
  `cd1d50f4a7f3e563922e9eb87d2b4f6d7dd621ab`, moved durably beyond
  `scripts/analyze_claude_code_edits.py -> scripts/verify_mcp_retrieval.py`,
  and then terminalized later at `2026-04-29T23:55:57Z` with the durable
  lexical trace already anchored on
  `scripts/migrate_large_index_to_multi_repo.py ->
  scripts/check_index_languages.py`.
- That same evidence block also shows the current ambiguity that this phase
  must resolve truthfully: at `2026-04-29T23:55:48Z`,
  `.mcp-index/force_full_exit_trace.json` still showed `status: running`,
  `stage: lexical_walking`,
  `last_progress_path=/home/viperjuice/code/Code-Index-MCP/scripts/check_index_languages.py`,
  and `in_flight_path=null`. The live run therefore no longer blames the
  cleared edit/retrieval seam, but it also does not yet prove whether the
  remaining timeout is still truly pair-local or whether lexical walking has
  already finished and the closeout handoff is what is being durably
  under-reported.
- SQLite runtime counts after that rerun remained
  `files = 1064`, `code_chunks = 13095`, `chunk_summaries = 0`, and
  `semantic_points = 0`, so semantic summaries and vectors still have not
  resumed; this remains a pre-semantic blocker or handoff-truthfulness slice.
- The script-language pair is not starting from a missing exact bounded-path
  contract. `mcp_server/dispatcher/dispatcher_enhanced.py` already carries
  exact bounded Python entries for
  `scripts/migrate_large_index_to_multi_repo.py` and
  `scripts/check_index_languages.py`, and
  `mcp_server/cli/repository_commands.py` already prints the exact operator
  boundary
  `scripts/migrate_large_index_to_multi_repo.py -> scripts/check_index_languages.py`
  when both files are present.
- Existing deterministic coverage already proves most of the original
  SEMSCRIPTLANGS contract:
  `tests/test_dispatcher.py` binds both files to exact bounded lexical
  indexing, preserves discoverability, and includes a closeout-handoff fixture
  for the pair; `tests/test_git_index_manager.py` already exercises a
  force-full trace that moves past the pair; and
  `tests/test_repository_commands.py` already freezes the exact status wording
  for the pair.
- What is not yet frozen for this rebound slice is the later-phase truth
  contract: once the edit/retrieval seam is cleared, the current-head rerun
  must either prove the script-language pair is still the real active blocker
  or promote the next truthful closeout or later-path blocker instead of
  leaving the pair as a stale placeholder simply because it was the last exact
  bounded lexical file seen before timeout.
- `scripts/migrate_large_index_to_multi_repo.py` is still materially larger
  than `scripts/check_index_languages.py` and continues to expose stable
  top-level surfaces such as `RepositoryMigration`, `LargeIndexMigrator`, and
  `main`, while `scripts/check_index_languages.py` remains a small imperative
  audit script with no top-level `def` or `class` nodes. Any repair must
  preserve those discoverability expectations.
- `tests/docs/test_semdogfood_evidence_contract.py` and the evidence report
  already mention `SEMSCRIPTLANGSTAIL` as the next downstream steering
  decision, but there is not yet a phase-local evidence block or phase-plan
  artifact for this rebound slice.

Practical planning boundary:

- SEMSCRIPTLANGSTAIL may tighten the exact bounded-path or closeout-handoff
  behavior for `scripts/migrate_large_index_to_multi_repo.py` and
  `scripts/check_index_languages.py`, make the smallest script-local
  simplification only if tests and the current-head rerun prove residual cost
  is still pair-local, refresh durable trace persistence and
  `repository status` wording, rerun the repo-local force-full sync, refresh
  the dogfood evidence report, and extend the roadmap only if a newer blocker
  appears beyond the current tail.
- SEMSCRIPTLANGSTAIL must stay narrow and evidence-driven. It must not reopen
  the already-cleared
  `scripts/analyze_claude_code_edits.py -> scripts/verify_mcp_retrieval.py`
  seam, add a broad `scripts/*.py` or repo-wide lexical-timeout bypass, or
  widen into unrelated semantic or release work unless the refreshed rerun
  proves the blocker has moved again.
- Because the pair already has exact bounded lexical coverage, execution
  should first prove whether the remaining timeout is still pair-local or
  whether lexical walking has already completed and the real missing contract
  is durable closeout-stage or later-blocker promotion.

## Interface Freeze Gates

- [ ] IF-0-SEMSCRIPTLANGSTAIL-1 - Exact rebound pair advance contract:
      a refreshed repo-local force-full rerun on the post-SEMEDITRETRIEVALTAIL
      head no longer terminalizes with the durable trace centered on
      `scripts/migrate_large_index_to_multi_repo.py ->
      scripts/check_index_languages.py`; it either advances durably beyond
      that exact pair or emits a truthful newer blocker before the
      120-second watchdog expires.
- [ ] IF-0-SEMSCRIPTLANGSTAIL-2 - Rebound truth contract:
      any repair introduced by this phase remains limited to the exact named
      script pair and the immediate dispatcher, closeout-trace, operator
      status, evidence, and roadmap-steering plumbing needed to clear or
      truthfully supersede it. If the current exact bounded pair already
      finishes lexical work, the phase must promote the real later blocker
      instead of layering a second generic script bypass or reopening the
      cleared edit/retrieval seam.
- [ ] IF-0-SEMSCRIPTLANGSTAIL-3 - Lexical discoverability contract:
      both exact scripts remain lexically discoverable after the repair,
      including durable file storage plus stable symbol and text
      discoverability for the currently checked-in script surfaces
      (`RepositoryMigration`, `LargeIndexMigrator`, `migrate_repository`,
      and `main`) while `scripts/check_index_languages.py` remains stored and
      FTS-visible even if it emits zero symbols.
- [ ] IF-0-SEMSCRIPTLANGSTAIL-4 - Durable closeout-trace and operator
      contract:
      `force_full_exit_trace.json`, `GitAwareIndexManager`, and
      `uv run mcp-index repository status` stay aligned once the later
      edit/retrieval seam is already cleared. When the last lexical progress
      sits on `scripts/check_index_languages.py` and no later
      `in_flight_path` survives, the persisted trace and CLI output must
      truthfully distinguish a still-active script-language rebound from a
      post-lexical closeout or later blocker, and must not regress to stale
      SEMEDITRETRIEVALTAIL-only wording.
- [ ] IF-0-SEMSCRIPTLANGSTAIL-5 - Evidence and downstream steering contract:
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMEDITRETRIEVALTAIL rerun outcome, the SEMSCRIPTLANGSTAIL rerun command
      and timestamps, the refreshed durable trace/status output, and the final
      authoritative verdict for the rebound seam; if execution exposes a
      blocker beyond the current roadmap tail, `specs/phase-plans-v7.md` is
      amended before closeout so `.phase-loop/` points to the newest truthful
      next phase instead of stopping at a stale tail.

## Lane Index & Dependencies

- SL-0 - Rebound seam truth contract freeze; Depends on: SEMEDITRETRIEVALTAIL; Blocks: SL-1, SL-2, SL-3, SL-4; Parallel-safe: no
- SL-1 - Exact rebound pair runtime repair or minimal script-local simplification; Depends on: SL-0; Blocks: SL-2, SL-3, SL-4; Parallel-safe: no
- SL-2 - Durable closeout-trace persistence and operator boundary alignment; Depends on: SL-0, SL-1; Blocks: SL-3, SL-4; Parallel-safe: no
- SL-3 - Live rerun evidence reducer and SEMSCRIPTLANGSTAIL contract refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SL-4; Parallel-safe: no
- SL-4 - Downstream roadmap steering reducer; Depends on: SL-0, SL-1, SL-2, SL-3; Blocks: SEMSCRIPTLANGSTAIL acceptance; Parallel-safe: no

Lane DAG:

```text
SEMEDITRETRIEVALTAIL
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SL-4 -> SEMSCRIPTLANGSTAIL acceptance
```

## Lanes

### SL-0 - Rebound Seam Truth Contract Freeze

- **Scope**: Freeze the exact rebound shape where the later
  `scripts/analyze_claude_code_edits.py -> scripts/verify_mcp_retrieval.py`
  seam is already cleared, the script-language pair is already exact-bounded,
  and the force-full run times out with `last_progress_path` already on
  `scripts/check_index_languages.py` so execution can prove whether the active
  gap is still pair-local or already a closeout-handoff truthfulness problem.
- **Owned files**: `tests/test_dispatcher.py`
- **Interfaces provided**: executable assertions for
  IF-0-SEMSCRIPTLANGSTAIL-1,
  IF-0-SEMSCRIPTLANGSTAIL-2,
  and IF-0-SEMSCRIPTLANGSTAIL-3 at the dispatcher boundary
- **Interfaces consumed**: existing `Dispatcher.index_directory(...)`,
  `_EXACT_BOUNDED_PYTHON_PATHS`,
  `_build_exact_bounded_python_shard(...)`,
  the current checked-in content shape of
  `scripts/migrate_large_index_to_multi_repo.py` and
  `scripts/check_index_languages.py`,
  and the existing closeout-handoff fixtures for the script-language and
  edit/retrieval seams
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend or tighten `tests/test_dispatcher.py` so the rebound fixture
    proves the exact script-language pair preserves durable file rows, stable
    symbols for `migrate_large_index_to_multi_repo.py`, zero chunks for both
    files, and FTS-backed discoverability while the later
    edit/retrieval pair is absent from the rebound snapshots.
  - test: Add explicit rebound assertions that when semantic closeout has not
    yet emitted later progress, dispatcher snapshots still promote the pair
    into `force_full_closeout_handoff` instead of leaving the last snapshot as
    stale `lexical_walking` with ambiguous ownership of the timeout.
  - test: Fail if the rebound repair would turn either script into an ignored
    lexical blind spot or would reintroduce stale
    `scripts/analyze_claude_code_edits.py ->
    scripts/verify_mcp_retrieval.py` wording into the later snapshots.
  - impl: Keep fixtures deterministic with repo-local Python strings and
    synthetic semantic-closeout failures rather than long-running live waits
    inside unit coverage.
  - impl: Keep this lane on contract freeze only. Do not mutate dispatcher
    implementation, script sources, git-index-manager persistence, CLI wording,
    evidence docs, or roadmap steering here.
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "migrate_large_index_to_multi_repo or check_index_languages or script_language_audit or rebound or closeout_handoff or bounded"`

### SL-1 - Exact Rebound Pair Runtime Repair Or Minimal Script-Local Simplification

- **Scope**: Implement the smallest repair needed so the current-head
  force-full rerun no longer burns its watchdog budget on the rebound
  `scripts/migrate_large_index_to_multi_repo.py ->
  scripts/check_index_languages.py` seam or leaves that seam as a stale
  placeholder once lexical work is already complete.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `scripts/migrate_large_index_to_multi_repo.py`, `scripts/check_index_languages.py`
- **Interfaces provided**: IF-0-SEMSCRIPTLANGSTAIL-1 exact rebound pair
  advance contract; IF-0-SEMSCRIPTLANGSTAIL-2 rebound truth contract;
  IF-0-SEMSCRIPTLANGSTAIL-3 lexical discoverability contract
- **Interfaces consumed**: SL-0 rebound fixtures; existing
  `_EXACT_BOUNDED_PYTHON_PATHS`; current lexical timeout and progress-callback
  behavior in `index_directory(...)`; and the current structure of the two
  exact scripts
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 dispatcher slice first and determine whether the
    rebound still requires a pair-local runtime change or whether the exact
    bounded path already completes lexical work and the remaining issue is only
    downstream truth-surface persistence.
  - impl: If the rebound is still pair-local, choose one singular repair
    surface and keep it exact: either tighten the dispatcher's exact bounded
    handoff for this pair or make the smallest script-local simplification to
    `scripts/migrate_large_index_to_multi_repo.py` or
    `scripts/check_index_languages.py` that allows the current watchdog to
    advance beyond the pair.
  - impl: Only edit the script sources if tests and the current-head rerun
    prove the hotspot is still file-local structure rather than stale
    post-lexical bookkeeping. Preserve the scripts' intended operational
    meaning, current artifact names, and stable helper symbol surfaces.
  - impl: If the exact bounded path already suffices at the dispatcher layer,
    keep the script files unchanged and leave the remaining truth-surface work
    to SL-2 and SL-3 instead of widening the repair.
  - verify: `rg -n "migrate_large_index_to_multi_repo|check_index_languages|force_full_closeout_handoff|_EXACT_BOUNDED_PYTHON_PATHS" mcp_server/dispatcher/dispatcher_enhanced.py scripts/migrate_large_index_to_multi_repo.py scripts/check_index_languages.py tests/test_dispatcher.py`
  - verify: `uv run pytest tests/test_dispatcher.py -q --no-cov -k "migrate_large_index_to_multi_repo or check_index_languages or script_language_audit or rebound or closeout_handoff or bounded"`

### SL-2 - Durable Closeout-Trace Persistence And Operator Boundary Alignment

- **Scope**: Make the durable force-full trace and operator-visible status
  truthful when the rebound pair is already exact-bounded and the live rerun
  either clears it or stalls immediately after it.
- **Owned files**: `mcp_server/storage/git_index_manager.py`, `mcp_server/cli/repository_commands.py`, `tests/test_git_index_manager.py`, `tests/test_repository_commands.py`
- **Interfaces provided**: IF-0-SEMSCRIPTLANGSTAIL-4 durable closeout-trace
  and operator contract
- **Interfaces consumed**: SL-0 rebound fixture vocabulary; SL-1 chosen
  rebound repair or no-op decision; existing force-full trace persistence in
  `GitAwareIndexManager.sync_repository_index(...)`; current
  `_print_force_full_exit_trace(...)`; and the existing exact bounded
  script-language boundary helper in `repository_commands.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_git_index_manager.py` so a force-full rerun that
    has already advanced through the script-language pair but times out before
    later semantic or closeout progress persists the truthful later stage
    instead of leaving the durable trace pinned to stale `lexical_walking`
    blame on `scripts/check_index_languages.py`.
  - test: Extend `tests/test_repository_commands.py` so
    `uv run mcp-index repository status` distinguishes a still-active
    script-language rebound from a post-lexical closeout stall, while keeping
    the exact bounded pair wording and excluding stale
    `scripts/analyze_claude_code_edits.py ->
    scripts/verify_mcp_retrieval.py` output once the rerun has advanced
    beyond it.
  - impl: Preserve the fail-closed readiness vocabulary and current durable
    trace field names. This lane should not rename `Trace status`,
    `Trace stage`, `Trace blocker source`, `last_progress_path`, or
    `in_flight_path`; it should only make the rebound-versus-closeout truth
    explicit and durable on the current head.
  - impl: Keep the CLI boundary wording additive and exact. Do not broaden it
    into a generic `scripts/*.py` claim or a catch-all explanation for all
    late script tails.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "migrate_large_index_to_multi_repo or check_index_languages or script_language_audit or rebound or closeout or interrupted or boundary"`

### SL-3 - Live Rerun Evidence Reducer And SEMSCRIPTLANGSTAIL Contract Refresh

- **Scope**: Re-run the repaired repo-local force-full sequence, reduce the
  outcome into the durable semantic dogfood evidence artifact, and record the
  authoritative verdict for whether the rebound pair is still active or has
  already yielded to a later blocker.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: IF-0-SEMSCRIPTLANGSTAIL-1 exact rebound pair
  advance contract; IF-0-SEMSCRIPTLANGSTAIL-4 durable closeout-trace and
  operator contract; IF-0-SEMSCRIPTLANGSTAIL-5 evidence contract
- **Interfaces consumed**: SL-0 rebound fixtures; SL-1 chosen rebound repair
  or no-op decision; SL-2 trace/status wording; current SEMEDITRETRIEVALTAIL
  evidence; and the live repo-local `force_full_exit_trace.json`,
  `repository status`, SQLite counts, and rerun exit status from the current
  head
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/docs/test_semdogfood_evidence_contract.py` so the
    report must name `plans/phase-plan-v7-SEMSCRIPTLANGSTAIL.md`, carry a
    `## SEMSCRIPTLANGSTAIL Live Rerun Check` block, preserve the
    SEMEDITRETRIEVALTAIL rerun lineage, and record the exact rebound pair plus
    whichever later truth the refreshed rerun proves.
  - impl: Run the current-head force-full command once after the code lanes are
    ready, capture the resulting `force_full_exit_trace.json`,
    `repository status`, and SQLite counts, and reduce them into one
    authoritative evidence block that says whether the pair is still the
    blocker or whether the run has moved later.
  - impl: If the rerun still names the rebound pair, the report must include
    why that attribution remains truthful on the current head; if the rerun
    moves later, the report must say the script-language rebound is no longer
    the active blocker and preserve the exact newer blocker or closeout stage.
  - impl: Keep this lane limited to the dogfood evidence artifact and its test.
    Do not mutate the roadmap here; SL-4 owns any required downstream
    phase-tail amendment.
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "SEMSCRIPTLANGSTAIL or SEMEDITRETRIEVALTAIL or migrate_large_index_to_multi_repo or check_index_languages or script_language_audit"`
  - verify: `timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - verify: `sed -n '1,240p' .mcp-index/force_full_exit_trace.json`
  - verify: `sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'`

### SL-4 - Downstream Roadmap Steering Reducer

- **Scope**: Keep the v7 roadmap truthful if the refreshed current-head rerun
  exposes a blocker beyond the present roadmap tail.
- **Owned files**: `specs/phase-plans-v7.md`
- **Interfaces provided**: the roadmap-steering portion of
  IF-0-SEMSCRIPTLANGSTAIL-5
- **Interfaces consumed**: SL-3 live rerun verdict; current phase-76 tail
  position in `specs/phase-plans-v7.md`; and canonical `.phase-loop/`
  expectation that the roadmap names the next unplanned phase truthfully
- **Parallel-safe**: no
- **Tasks**:
  - test: Re-read the end of `specs/phase-plans-v7.md` after the SL-3 rerun
    and only amend it if the refreshed current-head evidence proves a blocker
    beyond `scripts/migrate_large_index_to_multi_repo.py ->
    scripts/check_index_languages.py`.
  - impl: If the rerun reveals a newer blocker, append one downstream phase
    with the same exact-pair specificity used elsewhere in v7 and update any
    affected execution notes so `.phase-loop/` does not stop on a stale tail.
  - impl: If the rerun keeps the rebound pair as the active truthful blocker,
    leave the roadmap unchanged and record that decision explicitly in the
    execution closeout and evidence.
  - impl: Keep this lane reducer-only. Do not reopen earlier phase-plan,
    docs, or script families that the rerun did not re-anchor on.
  - verify: `rg -n "SEMSCRIPTLANGSTAIL|scripts/migrate_large_index_to_multi_repo.py|scripts/check_index_languages.py" specs/phase-plans-v7.md docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
  - verify: `git diff -- specs/phase-plans-v7.md`

## Verification

Planning-only run: do not execute these during plan creation. Run them during
`codex-execute-phase` or manual SEMSCRIPTLANGSTAIL execution.

Lane-specific checks:

```bash
uv run pytest tests/test_dispatcher.py -q --no-cov -k "migrate_large_index_to_multi_repo or check_index_languages or script_language_audit or rebound or closeout_handoff or bounded"
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_git_index_manager.py tests/test_repository_commands.py -q --no-cov -k "migrate_large_index_to_multi_repo or check_index_languages or script_language_audit or rebound or closeout or interrupted or boundary"
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov -k "SEMSCRIPTLANGSTAIL or SEMEDITRETRIEVALTAIL or migrate_large_index_to_multi_repo or check_index_languages or script_language_audit"
timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
sed -n '1,240p' .mcp-index/force_full_exit_trace.json
sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'
```

Whole-phase regression commands:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest \
  tests/test_dispatcher.py \
  tests/test_git_index_manager.py \
  tests/test_repository_commands.py \
  tests/docs/test_semdogfood_evidence_contract.py \
  -q --no-cov -k "migrate_large_index_to_multi_repo or check_index_languages or script_language_audit or rebound or closeout_handoff or closeout or bounded or interrupted or boundary"
timeout 120s env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
git status --short -- plans/phase-plan-v7-SEMSCRIPTLANGSTAIL.md docs/status/SEMANTIC_DOGFOOD_REBUILD.md specs/phase-plans-v7.md
git diff --check
git diff --cached --check
```

## Acceptance Criteria

- [ ] A refreshed repo-local force-full rerun on the post-SEMEDITRETRIEVALTAIL
      head either advances durably beyond
      `scripts/migrate_large_index_to_multi_repo.py ->
      scripts/check_index_languages.py`
      or emits a truthful newer blocker before the 120-second watchdog
      expires.
- [ ] The chosen repair for the later script-language rebound seam stays
      narrow, tested, and does not reopen the already-cleared
      `scripts/analyze_claude_code_edits.py ->
      scripts/verify_mcp_retrieval.py`
      boundary without direct evidence.
- [ ] Both exact scripts remain lexically discoverable with durable file
      storage and stable symbol/text discoverability for the current checked-in
      script surfaces.
- [ ] `force_full_exit_trace.json` and
      `uv run mcp-index repository status` stay aligned with the repaired
      outcome for the exact rebound pair; if lexical walking has already
      completed, they truthfully promote the later closeout or successor
      blocker instead of leaving stale blame on
      `scripts/check_index_languages.py`.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMEDITRETRIEVALTAIL rerun outcome and the final live verdict for the
      later script-language rebound pair.
- [ ] If the rerun exposes a blocker beyond the current roadmap tail,
      `specs/phase-plans-v7.md` is updated before closeout so the next
      phase-loop step stays truthful.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMSCRIPTLANGSTAIL.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMSCRIPTLANGSTAIL.md
  artifact_state: staged
```
