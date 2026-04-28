---
phase_loop_plan_version: 1
phase: SEMCOLLECT
roadmap: specs/phase-plans-v7.md
roadmap_sha256: f4ed72be1134fa94d39a4c8ebcbc88904e49cbc527f89dd6e2286be418740a24
---
# SEMCOLLECT: Collection Bootstrap and Semantic Stage Recovery

## Context

SEMCOLLECT is the phase-9 recovery slice for the v7 semantic hardening
roadmap. SEMREADYFIX repaired the default `oss_high` enrichment compatibility
path, but the clean rebuild still stopped before any semantic writes because
the active-profile preflight remained blocked on `collection_missing`.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is tracked and clean in this worktree, and its
  live SHA matches the required
  `f4ed72be1134fa94d39a4c8ebcbc88904e49cbc527f89dd6e2286be418740a24`.
- The checkout is on `main` at `64fa813165c63703c62799a7f06ca44263b68263`,
  the worktree was clean before this planning write, and
  `plans/phase-plan-v7-SEMCOLLECT.md` did not exist before this run.
- The upstream v7 planning chain already exists through
  `plans/phase-plan-v7-SEMREADYFIX.md`; SEMCOLLECT must consume the semantic
  readiness split, active-profile metadata, semantic preflight blocker
  vocabulary, enrichment compatibility repair, strict semantic-stage ordering,
  and semantic-only query contract frozen by SEMCONTRACT through SEMREADYFIX.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` now proves the remaining blocker:
  the 2026-04-28 clean rebuild finished with lexical readiness `ready`, but
  `chunk_summaries=0`, `semantic_points=0`, semantic readiness
  `summaries_missing`, and active-profile preflight blocker
  `collection_missing` for `code_index__oss_high__v1`.
- `_run_semantic_stage(...)` in
  `mcp_server/dispatcher/dispatcher_enhanced.py` already follows the intended
  ordering of lexical persistence first, authoritative summaries second,
  semantic preflight third, and strict vector writes last. Today it exits on
  the preflight blocker before any semantic vector write when the collection is
  missing.
- `run_semantic_preflight(...)` and `check_qdrant_collection(...)` in
  `mcp_server/setup/semantic_preflight.py` intentionally validate Qdrant
  reachability, collection existence, and collection shape without mutating
  the collection. The current blocker payload already says to "Create or
  hydrate the expected semantic collection before vector writes."
- `setup semantic` in `mcp_server/cli/setup_commands.py` can autostart Qdrant
  when the service is unreachable, but it currently stops at reporting the
  missing-collection blocker. There is no narrow operator-facing bootstrap path
  yet for the active profile collection when Qdrant itself is already healthy.
- `SemanticIndexer.__init__(...)` already calls `_ensure_collection()`, and
  `_ensure_collection()` in `mcp_server/utils/semantic_indexer.py` can create
  or recreate the target Qdrant collection with the active profile's vector
  dimension and distance metric once a live client is initialized. Existing
  tests in `tests/test_profile_aware_semantic_indexer.py` also freeze the
  current fail-closed behavior that blocks all upserts when semantic preflight
  carries `collection_missing`.
- `tests/test_repository_commands.py` already proves repository status renders
  semantic readiness, semantic evidence counts, and the preflight blocker.
  `tests/real_world/test_semantic_search.py` already has the repo-local
  dogfood prompts and asserts the expected semantic profile and collection
  metadata when the semantic path is ready, but it still skips on
  `semantic_not_ready`.

Practical planning boundary:

- SEMCOLLECT may add a narrow active-profile collection bootstrap or hydrate
  path, wire that recovery into the strict semantic stage, expose the recovery
  status at setup or status surfaces, rerun the repo-local dogfood rebuild, and
  refresh the semantic dogfood evidence.
- SEMCOLLECT must stay narrowly on collection provisioning or hydration and the
  strict semantic stage that depends on it. It must not widen into semantic
  ranking changes, multi-repo rollout expansion, or unrelated provider-policy
  rewrites beyond the repaired default `oss_high` path.

## Interface Freeze Gates

- [ ] IF-0-SEMCOLLECT-1 - Active-profile collection bootstrap contract: when
      the active semantic profile is otherwise preflight-ready and Qdrant is
      reachable, the repo can create or hydrate the expected
      `code_index__oss_high__v1` collection with the active profile's vector
      shape and namespace without mutating unrelated collections.
- [ ] IF-0-SEMCOLLECT-2 - Strict semantic-stage recovery contract: a clean
      force-full rebuild can advance from authoritative summary generation into
      semantic vector writes for the default local `oss_high` path instead of
      stopping at `collection_missing`, and it records non-zero
      `chunk_summaries` plus non-zero `semantic_points` for the active profile.
- [ ] IF-0-SEMCOLLECT-3 - Operator recovery contract: setup and status
      surfaces expose whether the active collection was missing, created,
      reused, or still blocked, including active profile and collection
      identity plus exact remaining blocker metadata without leaking secrets.
- [ ] IF-0-SEMCOLLECT-4 - Dogfood semantic-ready contract: after collection
      recovery, the fixed repo-local semantic dogfood prompts return
      semantic-path code results with `semantic_source: "semantic"`,
      `semantic_profile_id: "oss_high"`, and
      `semantic_collection_name: "code_index__oss_high__v1"` instead of
      `semantic_not_ready`.
- [ ] IF-0-SEMCOLLECT-5 - Phase boundary contract: SEMCOLLECT changes
      collection bootstrap or hydration, strict semantic stage recovery, and
      the refreshed dogfood evidence only. It does not redesign ranking,
      broaden rollout policy, or change unrelated inference-provider contracts.

## Lane Index & Dependencies

- SL-0 - Collection bootstrap contract tests and fixtures; Depends on: SEMREADYFIX; Blocks: SL-1, SL-2, SL-3; Parallel-safe: no
- SL-1 - Active-profile collection bootstrap implementation; Depends on: SL-0; Blocks: SL-2, SL-3; Parallel-safe: no
- SL-2 - Strict semantic-stage recovery and status acceptance; Depends on: SL-0, SL-1; Blocks: SL-3; Parallel-safe: no
- SL-3 - Dogfood evidence reducer and operator guide refresh; Depends on: SL-0, SL-1, SL-2; Blocks: SEMCOLLECT acceptance; Parallel-safe: no

Lane DAG:

```text
SEMREADYFIX
  -> SL-0 -> SL-1 -> SL-2 -> SL-3 -> SEMCOLLECT acceptance
```

## Lanes

### SL-0 - Collection Bootstrap Contract Tests And Fixtures

- **Scope**: Freeze the missing-collection recovery behavior before changing
  runtime code so the phase has deterministic tests for bootstrap, strict-stage
  continuation, and non-destructive namespace handling.
- **Owned files**: `tests/test_semantic_preflight.py`, `tests/test_setup_cli.py`, `tests/test_profile_aware_semantic_indexer.py`
- **Interfaces provided**: executable assertions for IF-0-SEMCOLLECT-1,
  IF-0-SEMCOLLECT-3, and the bootstrap preconditions consumed by SL-1 and SL-2
- **Interfaces consumed**: existing `run_semantic_preflight(...)`,
  `check_qdrant_collection(...)`, `setup semantic` text and JSON surfaces,
  `SemanticIndexer._ensure_collection()`, and the current
  `collection_missing` blocker vocabulary from SEMREADYFIX
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_semantic_preflight.py` with synthetic Qdrant
    cases that distinguish "Qdrant reachable but collection missing" from
    collection-shape mismatch and prove the recovery path only targets the
    active profile collection.
  - test: Extend `tests/test_setup_cli.py` so `setup semantic` freezes the
    operator-facing collection bootstrap outcome, including dry-run behavior,
    recovery messaging, and the exact blocker when bootstrap still cannot make
    the active profile writable.
  - test: Extend `tests/test_profile_aware_semantic_indexer.py` so the active
    semantic indexer proves `_ensure_collection()` creates the expected
    collection for the active profile and that semantic upserts remain blocked
    until bootstrap or preflight recovery actually succeeds.
  - impl: Add or refine Qdrant fakes and fixtures so bootstrap-path tests stay
    deterministic and do not require live Qdrant during unit coverage.
  - impl: Keep the assertions narrow to collection bootstrap and semantic-stage
    preconditions; do not use this lane to redesign semantic query semantics.
  - verify: `uv run pytest tests/test_semantic_preflight.py tests/test_setup_cli.py tests/test_profile_aware_semantic_indexer.py -q --no-cov`

### SL-1 - Active-Profile Collection Bootstrap Implementation

- **Scope**: Add the narrow collection create or hydrate path for the active
  semantic profile so a missing `code_index__oss_high__v1` collection can be
  recovered safely before strict semantic vector writes.
- **Owned files**: `mcp_server/utils/semantic_indexer.py`, `mcp_server/setup/semantic_preflight.py`, `mcp_server/cli/setup_commands.py`
- **Interfaces provided**: IF-0-SEMCOLLECT-1 active-profile collection
  bootstrap contract; IF-0-SEMCOLLECT-3 setup-surface recovery metadata and
  exact remaining blocker semantics
- **Interfaces consumed**: SL-0 contract tests; existing
  `SemanticIndexer._ensure_collection()`, profile registry metadata,
  collection namespace rules, `run_semantic_preflight(...)`,
  `check_qdrant_collection(...)`, and `setup semantic` autostart behavior
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 bootstrap tests first and confirm they reproduce the
    current "Qdrant reachable but collection_missing" behavior before runtime
    changes land.
  - impl: Extract or expose one deterministic helper that can create or
    hydrate the active profile collection using the profile's expected
    collection name, vector dimension, and distance metric without mutating
    unrelated Qdrant collections.
  - impl: Decide the narrow operator entry point for bootstrap inside existing
    surfaces, most likely `setup semantic` and the strict rebuild path,
    instead of introducing a parallel admin workflow.
  - impl: Keep `run_semantic_preflight(...)` primarily diagnostic, but allow
    callers to reuse its active-profile metadata so the bootstrap path and the
    post-bootstrap recheck agree on the same collection identity and blocker
    vocabulary.
  - impl: Preserve fail-closed behavior for all non-bootstrap blockers such as
    profile invalidity, embedding mismatch, or unreachable Qdrant; this lane
    only recovers the active-profile missing-collection path.
  - impl: Surface whether the collection was created, reused, or still blocked
    in the setup output and any structured payloads the strict semantic stage
    consumes later.
  - verify: `uv run pytest tests/test_semantic_preflight.py tests/test_setup_cli.py tests/test_profile_aware_semantic_indexer.py -q --no-cov`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index setup semantic --json --dry-run`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index index check-semantic`

### SL-2 - Strict Semantic-Stage Recovery And Status Acceptance

- **Scope**: Wire the collection bootstrap recovery into the strict semantic
  stage so full rebuilds can persist summaries and vectors for `oss_high`, then
  expose the recovered or still-blocked state through the repo status and
  dogfood query acceptance surfaces.
- **Owned files**: `mcp_server/dispatcher/dispatcher_enhanced.py`, `mcp_server/cli/repository_commands.py`, `tests/test_dispatcher.py`, `tests/test_repository_commands.py`, `tests/real_world/test_semantic_search.py`
- **Interfaces provided**: IF-0-SEMCOLLECT-2 strict semantic-stage recovery
  contract; IF-0-SEMCOLLECT-3 repository-status recovery evidence;
  IF-0-SEMCOLLECT-4 semantic-ready dogfood query acceptance
- **Interfaces consumed**: SL-0 bootstrap assertions; SL-1 collection
  bootstrap helper and outcome metadata; existing `_run_semantic_stage(...)`,
  `index_files_batch(...)`, repo status semantic evidence surfaces, and the
  fixed dogfood prompts from SEMDOGFOOD or SEMREADYFIX
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_dispatcher.py` so `_run_semantic_stage(...)`
    proves a missing active collection can be recovered through the narrow
    bootstrap path, after which summaries and strict vector writes continue in
    order instead of stopping at `collection_missing`.
  - test: Extend `tests/test_repository_commands.py` so repository status can
    distinguish "semantic still blocked on collection bootstrap" from
    "semantic recovered and ready" while preserving the existing semantic
    readiness and evidence output shape.
  - test: Update the repo-local dogfood case in
    `tests/real_world/test_semantic_search.py` so the post-rebuild acceptance
    path requires semantic-path hits for the fixed prompts once semantic
    readiness is restored, while still emitting the exact blocker when the repo
    is not yet ready.
  - impl: Refactor `_run_semantic_stage(...)` so the semantic pipeline can
    invoke the SL-1 bootstrap helper when summaries are ready, Qdrant is
    reachable, and the only remaining blocker is the missing active collection.
  - impl: Re-run or refresh the semantic preflight after bootstrap before
    calling `index_files_batch(...)` so strict semantic writes stay fail-closed
    on any remaining blocker and continue only when the collection really
    matches the active profile.
  - impl: Preserve the current additive semantic-stage reporting and
    readiness-query behavior; this lane should enrich recovery evidence, not
    introduce a second semantic status model.
  - verify: `uv run pytest tests/test_dispatcher.py tests/test_repository_commands.py -q --no-cov`
  - verify: `SEMANTIC_SEARCH_ENABLED=true CODE_INDEX_DOGFOOD_REPO=. OPENAI_API_KEY=dummy-local-key uv run pytest tests/real_world/test_semantic_search.py -q --no-cov`
  - verify: `/usr/bin/time -v env SEMANTIC_SEARCH_ENABLED=true SEMANTIC_DEFAULT_PROFILE=oss_high OPENAI_API_KEY=dummy-local-key QDRANT_URL=http://localhost:6333 uv run mcp-index repository sync --force-full`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - verify: `sqlite3 .mcp-index/current.db 'select count(*) from chunk_summaries; select count(*) from semantic_points;'`

### SL-3 - Dogfood Evidence Reducer And Operator Guide Refresh

- **Scope**: Refresh the durable semantic dogfood evidence and operator
  guidance so the repo records whether collection recovery made local
  multi-repo semantic dogfooding ready or exactly what blocker remains.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `docs/guides/semantic-onboarding.md`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: refreshed SEMCOLLECT evidence for
  IF-0-SEMCOLLECT-2, IF-0-SEMCOLLECT-3, and IF-0-SEMCOLLECT-4; final operator
  guidance for the repaired or still-blocked local `oss_high` path
- **Interfaces consumed**: SL-1 bootstrap outcome metadata; SL-2 rebuild
  timings, summary/vector counts, semantic-ready status outputs, and dogfood
  query results; prior `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` evidence and
  reset boundary
- **Parallel-safe**: no
- **Tasks**:
  - test: Update `tests/docs/test_semdogfood_evidence_contract.py` so the
    refreshed report must cite `plans/phase-plan-v7-SEMCOLLECT.md`, record the
    collection bootstrap or hydrate outcome, capture non-zero
    `chunk_summaries` and non-zero `semantic_points` when recovery succeeds,
    and state the final semantic-ready or exact still-blocked verdict.
  - test: Require `docs/guides/semantic-onboarding.md` to explain how to
    interpret the active collection bootstrap state alongside lexical
    readiness, semantic readiness, and semantic preflight.
  - impl: Refresh `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` after the
    SEMCOLLECT rebuild with timings, active collection identity, summary and
    vector counts, semantic query outcomes for the fixed prompts, and the
    final readiness verdict.
  - impl: Update `docs/guides/semantic-onboarding.md` so operators know which
    setup or status surfaces prove collection recovery succeeded and when to
    expect semantic dogfood queries to remain fail-closed.
  - impl: If execution still cannot restore semantic readiness, record the
    exact remaining blocker, collection state, and evidence instead of widening
    this phase into unrelated semantic work.
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
  - verify: `rg -n "SEMCOLLECT|collection_missing|chunk_summaries|semantic_points|code_index__oss_high__v1|semantic readiness|setup semantic" docs/status/SEMANTIC_DOGFOOD_REBUILD.md docs/guides/semantic-onboarding.md tests/docs/test_semdogfood_evidence_contract.py`

## Verification

Planning-only run: do not execute these during plan creation. Run them during
`codex-execute-phase` or manual SEMCOLLECT execution.

Lane-specific checks:

```bash
uv run pytest tests/test_semantic_preflight.py tests/test_setup_cli.py tests/test_profile_aware_semantic_indexer.py -q --no-cov
uv run pytest tests/test_dispatcher.py tests/test_repository_commands.py -q --no-cov
SEMANTIC_SEARCH_ENABLED=true CODE_INDEX_DOGFOOD_REPO=. OPENAI_API_KEY=dummy-local-key uv run pytest tests/real_world/test_semantic_search.py -q --no-cov
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
```

Evidence commands:

```bash
env OPENAI_API_KEY=dummy-local-key uv run mcp-index setup semantic --json --dry-run
env OPENAI_API_KEY=dummy-local-key uv run mcp-index index check-semantic
/usr/bin/time -v env \
  SEMANTIC_SEARCH_ENABLED=true \
  SEMANTIC_DEFAULT_PROFILE=oss_high \
  OPENAI_API_KEY=dummy-local-key \
  QDRANT_URL=http://localhost:6333 \
  uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
env OPENAI_API_KEY=dummy-local-key uv run mcp-index preflight
sqlite3 .mcp-index/current.db \
  'select count(*) as chunk_summaries from chunk_summaries; select count(*) as semantic_points from semantic_points;'
curl -s http://localhost:6333/collections/code_index__oss_high__v1
```

Whole-phase regression commands:

```bash
uv run pytest \
  tests/test_semantic_preflight.py \
  tests/test_setup_cli.py \
  tests/test_profile_aware_semantic_indexer.py \
  tests/test_dispatcher.py \
  tests/test_repository_commands.py \
  tests/docs/test_semdogfood_evidence_contract.py \
  -q --no-cov
SEMANTIC_SEARCH_ENABLED=true CODE_INDEX_DOGFOOD_REPO=. OPENAI_API_KEY=dummy-local-key uv run pytest tests/real_world/test_semantic_search.py -q --no-cov
git status --short -- specs/phase-plans-v7.md plans/phase-plan-v7-SEMCOLLECT.md
```

## Acceptance Criteria

- [ ] A clean force-full rebuild no longer stops with active-profile preflight
      blocker `collection_missing` for the default local `oss_high` path.
- [ ] The repo can create or hydrate `code_index__oss_high__v1` for the active
      profile without mutating unrelated collections or broadening the phase
      into general Qdrant administration.
- [ ] `chunk_summaries` becomes non-zero after the rebuild and remains tied to
      the repaired effective enrichment-model audit metadata from SEMREADYFIX.
- [ ] `semantic_points` becomes non-zero and links to
      `code_index__oss_high__v1`.
- [ ] Semantic dogfood queries for the fixed prompts return semantic-path code
      results instead of `semantic_not_ready`.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is refreshed again with the
      semantic-ready or exact still-blocked verdict after collection recovery.
- [ ] `docs/guides/semantic-onboarding.md` tells operators how collection
      bootstrap or hydration relates to semantic preflight, semantic readiness,
      and the final dogfood evidence.
- [ ] SEMCOLLECT stays bounded to collection bootstrap or hydration, strict
      semantic-stage recovery, and refreshed dogfood evidence; it does not
      widen into semantic ranking redesign or multi-repo rollout expansion.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v7-SEMCOLLECT.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMCOLLECT.md
  artifact_state: staged
```
