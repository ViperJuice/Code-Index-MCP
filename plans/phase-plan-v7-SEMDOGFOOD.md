---
phase_loop_plan_version: 1
phase: SEMDOGFOOD
roadmap: specs/phase-plans-v7.md
roadmap_sha256: b8ba13bf3898d59c087f64193fa7415b0f932b34fc002e862d2678d74c1faf0c
---
# SEMDOGFOOD: Clean Semantic Dogfood Rebuild

## Context

SEMDOGFOOD is the phase-7 evidence closeout for the v7 semantic hardening
roadmap. SEMQUERY froze the ready-path semantic query contract; this phase
must prove the contract survives a clean rebuild of this repository with the
local `oss_high` semantic defaults instead of relying on targeted unit tests
or previously dirty runtime state.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is tracked and clean in this worktree, and its
  live SHA matches the required
  `b8ba13bf3898d59c087f64193fa7415b0f932b34fc002e862d2678d74c1faf0c`.
- The checkout is on `main` at `5c8c087`, the worktree is clean before writing
  this plan, and `main...origin/main` is ahead by 7 commits.
- `plans/phase-plan-v7-SEMCONTRACT.md`,
  `plans/phase-plan-v7-SEMCONFIG.md`,
  `plans/phase-plan-v7-SEMPREFLIGHT.md`,
  `plans/phase-plan-v7-SEMPIPE.md`,
  `plans/phase-plan-v7-SEMINCR.md`, and
  `plans/phase-plan-v7-SEMQUERY.md` already exist as the upstream v7 planning
  chain. SEMDOGFOOD must consume their readiness vocabulary, profile contract,
  summary-first build ordering, incremental invalidation behavior, and
  semantic-only query semantics instead of redefining them.
- `docs/status/DOGFOOD_INDEX_RESET_2026_04_27.md` already records the prior
  clean lexical/index reset proof, including explicit protection of shared
  `qdrant_storage/`, a forced full sync timing, and post-commit incremental
  sync timings. That report does not yet prove populated `chunk_summaries`,
  populated `semantic_points`, active-profile collection compatibility,
  semantic-path query relevance, or a final semantic dogfood verdict.
- `SQLiteStore.get_semantic_readiness_evidence(...)` in
  `mcp_server/storage/sqlite_store.py` already exposes the durable evidence
  this phase needs for the rebuilt repo: total chunks, summary counts, missing
  summaries, vector-link counts, missing vectors, matching collection links,
  and collection mismatches for the active profile.
- `build_health_row(...)` in `mcp_server/health/repo_status.py` already
  computes separate `semantic_readiness`, `semantic_ready`, and semantic
  evidence metadata for repo health surfaces, but `uv run mcp-index repository
  status` currently prints lexical readiness and semantic preflight only. It
  does not show the semantic readiness state or the summary/vector evidence
  counts that the roadmap wants in the final dogfood report.
- `tests/test_repository_commands.py` already covers rollout/query surface
  output and semantic preflight rendering for the status command, so it is the
  narrow place to freeze any new lexical-vs-semantic readiness output without
  widening into unrelated CLI work.
- `tests/real_world/test_semantic_search.py` currently proves semantic-source
  behavior on synthetic repositories and optional live env-backed queries, but
  it does not yet freeze a repo-local dogfood query set for this checkout or a
  comparison between lexical, symbol, fuzzy, and semantic outcomes after a
  clean rebuild.
- `docs/guides/semantic-onboarding.md` already explains semantic readiness,
  preflight, build ordering, and query semantics, but it stops short of a
  stable dogfood evidence artifact or an operator-facing readiness verdict for
  multi-repo local dogfooding with the local Qwen/Gemma stack.

Practical planning boundary:

- SEMDOGFOOD may expose the existing semantic readiness/evidence state more
  clearly in the repo status surface, tighten the repo-local real-world query
  guard used for dogfood validation, run the clean rebuild, and publish a
  durable report plus light guide follow-up.
- SEMDOGFOOD must stay evidence-heavy. It should not introduce new semantic
  indexing architecture, new query-routing behavior, release automation, or
  Qdrant collection deletion beyond the repo-local reset boundary already
  established by the prior dogfood report unless a concrete acceptance blocker
  is discovered during execution.

## Interface Freeze Gates

- [ ] IF-0-SEMDOGFOOD-1 - Dogfood evidence contract: a clean rebuild of this
      repo proves populated `chunk_summaries`, populated `semantic_points`,
      `code_index__oss_high__v1` collection compatibility, semantic-path
      natural-language retrieval, and a written verdict on whether local
      multi-repo dogfooding is ready.
- [ ] IF-0-SEMDOGFOOD-2 - Reset-boundary contract: repo-local stale index
      artifacts may be cleared for the rebuild, but shared live Qdrant service
      data is preserved unless the operator explicitly asks otherwise.
- [ ] IF-0-SEMDOGFOOD-3 - Readiness-report contract: final status output and
      final docs distinguish lexical readiness, semantic readiness, and active
      profile preflight instead of collapsing them into one readiness claim.
- [ ] IF-0-SEMDOGFOOD-4 - Query-comparison contract: the dogfood report
      compares lexical, symbol, fuzzy, and semantic queries on a fixed repo-
      local query set and shows that semantic queries stay on the semantic
      path with relevant implementation results.
- [ ] IF-0-SEMDOGFOOD-5 - Phase boundary contract: SEMDOGFOOD captures
      evidence, narrow status surfacing, and documentation only. It must not
      reopen semantic build/query architecture unless execution exposes a real
      blocker that prevents the acceptance proof.

## Lane Index & Dependencies

- SL-0 - Repository status semantic evidence surfacing; Depends on: (none); Blocks: SL-1, SL-2; Parallel-safe: no
- SL-1 - Repo-local semantic dogfood query guard; Depends on: SL-0; Blocks: SL-2; Parallel-safe: no
- SL-2 - Dogfood evidence reducer and guide closeout; Depends on: SL-0, SL-1; Blocks: (none); Parallel-safe: no

Lane DAG:

```text
SL-0 --> SL-1 --> SL-2
   \               ^
    `--------------'
```

## Lanes

### SL-0 - Repository Status Semantic Evidence Surfacing

- **Scope**: Surface the already-computed semantic readiness state and durable
  summary/vector evidence through the repository status command so the dogfood
  report can cite lexical readiness, semantic readiness, and active-profile
  preflight separately from one canonical status surface.
- **Owned files**: `mcp_server/cli/repository_commands.py`, `tests/test_repository_commands.py`
- **Interfaces provided**: IF-0-SEMDOGFOOD-3 lexical-vs-semantic readiness
  output; active-profile evidence fields for summary counts, vector-link
  counts, collection agreement, and semantic remediation wording in the status
  command
- **Interfaces consumed**: existing `build_health_row(...)` semantic fields;
  `ReadinessClassifier.classify_semantic_registered(...)`; existing status
  command output contract; `SQLiteStore.get_semantic_readiness_evidence(...)`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_repository_commands.py` so `uv run mcp-index
    repository status` proves it prints lexical readiness, semantic readiness,
    and active-profile semantic evidence separately rather than only lexical
    readiness plus preflight.
  - test: Add status-output coverage proving the semantic evidence section
    includes summary counts, vector-link counts, missing summaries, missing
    vectors, and collection mismatch or match metadata when available.
  - test: Preserve current rollout/query surface and semantic preflight output
    assertions so the new readiness lines do not regress existing operator
    status behavior.
  - impl: Update `mcp_server/cli/repository_commands.py` to render the
    semantic readiness state from `get_repository_status(...)` alongside the
    existing lexical readiness line and semantic preflight block.
  - impl: Render the existing semantic evidence payload in a compact,
    operator-readable shape that distinguishes ready evidence from remediation
    cases without inventing a new status taxonomy.
  - impl: Keep this lane bounded to status surfacing. Do not mutate the
    semantic classifier, rebuild flow, or query-routing behavior here.
  - verify: `uv run pytest tests/test_repository_commands.py -q --no-cov`

### SL-1 - Repo-Local Semantic Dogfood Query Guard

- **Scope**: Freeze the repo-local semantic dogfood query set used during the
  clean rebuild so the final report can compare lexical, symbol, fuzzy, and
  semantic results against known implementation targets instead of relying on
  ad hoc prompts.
- **Owned files**: `tests/real_world/test_semantic_search.py`, `tests/test_benchmark_query_regressions.py`
- **Interfaces provided**: IF-0-SEMDOGFOOD-4 fixed natural-language and
  identifier-shaped query cases for this repo; semantic-path result
  expectations including `semantic_source`, collection identity, and relevant
  implementation-file hits for dogfood prompts
- **Interfaces consumed**: SEMQUERY semantic-only response contract; existing
  real-world semantic test harness; existing query-regression fixtures around
  semantic relevance and implementation-file preference; repo-local targets
  such as `mcp_server/setup/semantic_preflight.py`,
  `mcp_server/cli/repository_commands.py`, and related semantic build/query
  code paths
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_benchmark_query_regressions.py` with the fixed
    repo-local dogfood prompts and expected implementation targets that should
    remain relevant after the clean rebuild.
  - test: Extend `tests/real_world/test_semantic_search.py` with an opt-in
    repo-local dogfood case that, after a rebuilt semantic index is present,
    asserts semantic-path results stay source-backed and return relevant
    implementation files for natural-language prompts.
  - test: Freeze at least one lexical-or-symbol comparison case so the report
    can contrast semantic retrieval against non-semantic paths on the same
    query set instead of inventing a second prompt list during execution.
  - impl: Keep the dogfood query harness limited to test fixtures and query
    expectations. Do not add a new production CLI/report command just to drive
    the comparison.
  - impl: Reuse the existing semantic test harness and environment gating
    rather than creating a parallel dogfood-only execution framework.
  - impl: Keep this lane at the validation boundary only. Do not change the
    semantic query contract that SEMQUERY already froze.
  - verify: `uv run pytest tests/test_benchmark_query_regressions.py -q --no-cov`
  - verify: `SEMANTIC_SEARCH_ENABLED=true CODE_INDEX_DOGFOOD_REPO=. uv run pytest tests/real_world/test_semantic_search.py -q --no-cov`

### SL-2 - Dogfood Evidence Reducer And Guide Closeout

- **Scope**: Run the clean semantic rebuild with the local `oss_high` defaults,
  capture timings and durable evidence, compare query modes on the fixed
  dogfood query set, and publish the final SEMDOGFOOD report plus a concise
  guide update that points operators at the evidence and status surfaces.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `docs/guides/semantic-onboarding.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: IF-0-SEMDOGFOOD-1 durable rebuild evidence; IF-0-SEMDOGFOOD-2 reset-boundary record; IF-0-SEMDOGFOOD-3 final lexical-vs-semantic readiness narrative; IF-0-SEMDOGFOOD-4 lexical/symbol/fuzzy/semantic comparison summary; final dogfood verdict for local multi-repo usage
- **Interfaces consumed**: SL-0 repository status output and semantic evidence
  fields; SL-1 fixed dogfood query cases; prior `docs/status/DOGFOOD_INDEX_RESET_2026_04_27.md`
  reset boundary; `uv run mcp-index repository sync --force-full`; `uv run
  mcp-index repository status`; `uv run mcp-index preflight`; `sqlite3
  .mcp-index/current.db`; active-profile preflight/collection metadata from
  `mcp_server/setup/semantic_preflight.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Add `tests/docs/test_semdogfood_evidence_contract.py` asserting the
    final report exists, names `plans/phase-plan-v7-SEMDOGFOOD.md`, records the
    repo-local reset boundary, includes rebuild timing and max-RSS evidence,
    captures `chunk_summaries` and `semantic_points` counts, records the
    `code_index__oss_high__v1` collection identity, compares lexical/symbol/
    fuzzy/semantic queries, and states the final dogfood verdict plus
    verification commands.
  - test: Require the semantic onboarding guide to link the SEMDOGFOOD report
    and to explain that lexical readiness, semantic readiness, and active-
    profile preflight are distinct operator checks.
  - impl: Rebuild from a clean repo-local index state, preserving shared live
    `qdrant_storage/` unless an execution-time blocker requires explicit human
    approval to go further.
  - impl: Capture forced full-sync timing, wall-clock timing, max RSS, index
    size, summary count, vector-link count, semantic collection metadata, and
    the post-rebuild lexical/semantic/preflight status outputs in
    `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`.
  - impl: Run the fixed query set across lexical, symbol, fuzzy, and semantic
    modes after the rebuild and summarize the implementation-file relevance and
    semantic-path evidence in the same report.
  - impl: Update `docs/guides/semantic-onboarding.md` with a short operator
    note pointing at the SEMDOGFOOD report and the separate readiness surfaces;
    keep the guide bounded to operational interpretation rather than product
    marketing claims.
  - impl: If execution uncovers a real blocker to acceptance, record it in the
    report with precise evidence instead of widening into unrelated semantic
    architecture work.
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
  - verify: `rg -n "SEMANTIC_DOGFOOD_REBUILD|lexical readiness|semantic readiness|active-profile preflight|code_index__oss_high__v1|semantic_points|chunk_summaries" docs/status/SEMANTIC_DOGFOOD_REBUILD.md docs/guides/semantic-onboarding.md tests/docs/test_semdogfood_evidence_contract.py`

## Verification

Planning-only run: do not execute these during plan creation. Run them during
`codex-execute-phase` or manual SEMDOGFOOD execution.

Lane-specific checks:

```bash
uv run pytest tests/test_repository_commands.py -q --no-cov
uv run pytest tests/test_benchmark_query_regressions.py -q --no-cov
SEMANTIC_SEARCH_ENABLED=true CODE_INDEX_DOGFOOD_REPO=. uv run pytest tests/real_world/test_semantic_search.py -q --no-cov
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
```

Evidence commands:

```bash
/usr/bin/time -v env \
  SEMANTIC_SEARCH_ENABLED=true \
  SEMANTIC_DEFAULT_PROFILE=oss_high \
  VLLM_EMBEDDING_BASE_URL=http://ai:8001/v1 \
  OPENAI_API_KEY=dummy-local-key \
  QDRANT_URL=http://localhost:6333 \
  uv run mcp-index repository sync --force-full
uv run mcp-index repository status
uv run mcp-index preflight
sqlite3 .mcp-index/current.db \
  'select count(*) as chunk_summaries from chunk_summaries; select count(*) as semantic_points from semantic_points;'
du -sh .mcp-index qdrant_storage 2>/dev/null
```

Whole-phase regression commands:

```bash
uv run pytest \
  tests/test_repository_commands.py \
  tests/test_benchmark_query_regressions.py \
  tests/docs/test_semdogfood_evidence_contract.py \
  -q --no-cov
SEMANTIC_SEARCH_ENABLED=true CODE_INDEX_DOGFOOD_REPO=. uv run pytest tests/real_world/test_semantic_search.py -q --no-cov
git status --short -- specs/phase-plans-v7.md plans/phase-plan-v7-SEMDOGFOOD.md
```

## Acceptance Criteria

- [ ] Repo-local stale semantic artifacts can be cleared for the rebuild
      without deleting shared live Qdrant service data unexpectedly.
- [ ] The forced full sync records timing, max RSS, index size, summary count,
      vector-link count, and active-profile Qdrant collection metadata in a
      durable report.
- [ ] `chunk_summaries` is populated for the rebuilt repo and the evidence is
      captured in the final report.
- [ ] `semantic_points` is populated for the rebuilt repo and the evidence
      shows links resolving to `code_index__oss_high__v1`.
- [ ] Natural-language semantic queries use the semantic path and return
      relevant implementation results for the fixed repo-local dogfood query
      set.
- [ ] The final report compares lexical, symbol, fuzzy, and semantic query
      results using the same fixed query set.
- [ ] Final status and documentation report lexical readiness, semantic
      readiness, and active-profile preflight separately.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` states whether this repo is
      ready to dogfood Code-Index-MCP against multiple local repos with the
      local Qwen/Gemma setup, including any remaining blocker if the answer is
      no.
- [ ] SEMDOGFOOD stays evidence-heavy and does not broaden into unrelated
      semantic architecture changes unless a concrete acceptance blocker
      requires a targeted follow-on fix.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v7-SEMDOGFOOD.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMDOGFOOD.md
  artifact_state: staged
```
