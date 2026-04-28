---
phase_loop_plan_version: 1
phase: SEMSUMFIX
roadmap: specs/phase-plans-v7.md
roadmap_sha256: bf4d2a4fd76720dc893a1ae6133c87eef52e1a69a39aded96d5e762e901bacd5
---
# SEMSUMFIX: Summary Runtime Recovery

## Context

SEMSUMFIX is the phase-10 recovery slice for the v7 semantic hardening
roadmap. SEMCOLLECT repaired the active `oss_high` collection bootstrap path
and restored active-profile semantic preflight readiness, but the repo-local
rebuild still left semantic evidence at zero because authoritative summary
generation is currently broken at runtime.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is tracked and clean in this worktree, and its
  live SHA matches the required
  `bf4d2a4fd76720dc893a1ae6133c87eef52e1a69a39aded96d5e762e901bacd5`.
- The checkout is on `main` at `c9aac94965d7`, the worktree was clean before
  this planning write, and `plans/phase-plan-v7-SEMSUMFIX.md` did not exist
  before this run.
- The upstream v7 planning and execution chain already exists through
  `plans/phase-plan-v7-SEMCOLLECT.md`; SEMSUMFIX must consume the semantic
  readiness split, local-default enrichment compatibility repair, collection
  bootstrap recovery, strict summary-before-vector ordering, and semantic-only
  query contract frozen by SEMCONTRACT through SEMCOLLECT instead of
  redefining them.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` now proves the current blocker
  precisely: the 2026-04-28 rebuild completed with lexical readiness `ready`,
  active-profile preflight `ready`, collection bootstrap `reused`,
  `chunk_summaries=0`, `semantic_points=0`, semantic readiness
  `summaries_missing`, and semantic dogfood queries still fail closed with
  `code: "semantic_not_ready"`.
- The same evidence artifact records the direct summary-runtime failure that
  moved the roadmap to this phase: the generated BAML client in
  `mcp_server/indexing/baml_client/baml_client/__init__.py` declares
  `__version__ = "0.220.0"`, while the locked environment currently installs
  `baml-py 0.221.0`, and the live probe reports that mismatch as the blocking
  authoritative summary failure.
- `mcp_server/indexing/summarization.py` already contains two relevant runtime
  paths: `ChunkWriter.summarize_chunk(...)` can fall back from BAML to the
  profile-configured direct OpenAI-compatible API path, but
  `FileBatchSummarizer._call_batch_api(...)` still imports the generated BAML
  client first for authoritative file-batch summarization.
- `FileBatchSummarizer.summarize_file_chunks(...)` already has the intended
  non-destructive fallback structure: batch-call failures delegate to the
  topological per-chunk path, and persisted summary rows already record
  authoritative/profile/provider audit metadata via `_persist_summary(...)`.
- `tests/test_summarization.py` already freezes the current profile-model
  audit metadata and large-file fallback behavior, but it does not yet freeze
  the generated-client/runtime mismatch path or prove that authoritative
  summary writes still succeed when the batch BAML runtime is unavailable.
- `tests/real_world/test_semantic_search.py`,
  `tests/docs/test_semdogfood_evidence_contract.py`, and
  `docs/guides/semantic-onboarding.md` are already the repo-local dogfood and
  operator evidence surfaces that must flip from "collection repaired but
  summary runtime broken" to a repaired semantic-ready or exact still-blocked
  verdict.

Practical planning boundary:

- SEMSUMFIX may repair the authoritative summary runtime by aligning the BAML
  generated client/runtime pair or by intentionally routing authoritative
  summaries through the already supported local profile-direct path with the
  same audit metadata contract.
- SEMSUMFIX may rerun the clean repo-local rebuild, confirm summary and vector
  counts become non-zero, refresh the semantic dogfood evidence, and tighten
  the operator troubleshooting guidance around the repaired path.
- SEMSUMFIX must stay narrowly on authoritative summary runtime recovery and
  the semantic write path it unlocks. It must not widen into semantic ranking
  redesign, multi-repo rollout expansion, or unrelated collection/preflight
  contract changes already handled by SEMREADYFIX and SEMCOLLECT.

## Interface Freeze Gates

- [ ] IF-0-SEMSUMFIX-1 - Supported authoritative summary runtime contract:
      `FileBatchSummarizer.summarize_file_chunks(...)` can produce
      authoritative summary rows for the default local `oss_high` path without
      failing on the current BAML generator/runtime mismatch, either because
      the generated client and installed runtime are aligned or because the
      authoritative path is intentionally rerouted through the supported local
      profile-direct API path.
- [ ] IF-0-SEMSUMFIX-2 - Authoritative audit parity contract: whichever
      runtime path writes authoritative summaries must preserve the existing
      audit metadata contract for `provider_name`, `llm_model`, `profile_id`,
      `prompt_fingerprint`, configured model, effective model, and resolution
      strategy so semantic invalidation and dogfood evidence remain
      trustworthy.
- [ ] IF-0-SEMSUMFIX-3 - Full rebuild semantic recovery contract: after the
      summary-runtime repair, a clean force-full rebuild under `oss_high`
      yields non-zero `chunk_summaries`, non-zero `semantic_points`, and
      semantic dogfood queries return semantic-path implementation results
      instead of `semantic_not_ready`.
- [ ] IF-0-SEMSUMFIX-4 - Operator evidence contract:
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` and
      `docs/guides/semantic-onboarding.md` state which authoritative summary
      runtime path was repaired, how to verify it, and the final semantic-ready
      or exact still-blocked verdict after the rebuild.

## Lane Index & Dependencies

- SL-0 - Summary runtime contract tests and probe fixture; Depends on: SEMCOLLECT; Blocks: SL-1, SL-2; Parallel-safe: no
- SL-1 - Authoritative summary runtime recovery implementation; Depends on: SL-0; Blocks: SL-2; Parallel-safe: no
- SL-2 - Semantic rebuild proof and operator evidence reducer; Depends on: SL-0, SL-1; Blocks: SEMSUMFIX acceptance; Parallel-safe: no

Lane DAG:

```text
SEMCOLLECT
  -> SL-0 -> SL-1 -> SL-2 -> SEMSUMFIX acceptance
```

## Lanes

### SL-0 - Summary Runtime Contract Tests And Probe Fixture

- **Scope**: Freeze the authoritative summary-runtime failure and the accepted
  recovery contract before mutating runtime code or dependency state.
- **Owned files**: `tests/test_summarization.py`
- **Interfaces provided**: executable assertions for IF-0-SEMSUMFIX-1 and
  IF-0-SEMSUMFIX-2
- **Interfaces consumed**: existing `ChunkWriter._call_profile_api(...)`,
  `ChunkWriter._build_summary_audit_metadata(...)`,
  `FileBatchSummarizer._call_batch_api(...)`,
  `FileBatchSummarizer._summarize_topological(...)`,
  `FileBatchSummarizer.summarize_file_chunks(...)`, and the generated BAML
  client version guard in
  `mcp_server/indexing/baml_client/baml_client/__init__.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_summarization.py` with a deterministic
    authoritative-summary failure case that simulates the current generated
    client/runtime mismatch and proves the batch path either fails in the
    currently observed way or is recovered through the intended supported
    path.
  - test: Add a contract test proving that when the authoritative batch path
    recovers from a BAML runtime failure, persisted rows still land as
    `is_authoritative=1` and preserve `provider_name`, `llm_model`,
    `profile_id`, configured model, effective model, and prompt fingerprint.
  - test: Add a narrow probe-fixture test for the repo-default `oss_high`
    summarization config so execution can reproduce the live blocker and then
    prove the repaired path without depending on the full rebuild first.
  - impl: Reuse monkeypatched `_call_batch_api`, `_summarize_topological`,
    and direct profile API shims instead of introducing live-network unit
    dependencies.
  - impl: Keep this lane focused on authoritative summary runtime behavior; do
    not use it to redesign semantic vector writes or readiness semantics.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_summarization.py -q --no-cov`

### SL-1 - Authoritative Summary Runtime Recovery Implementation

- **Scope**: Repair the default local authoritative summary runtime so the
  `oss_high` rebuild can populate `chunk_summaries` again without weakening
  audit metadata or semantic-stage ordering.
- **Owned files**: `mcp_server/indexing/summarization.py`, `mcp_server/config/settings.py`, `pyproject.toml`, `uv.lock`, `mcp_server/indexing/baml_client/baml_client/**`
- **Interfaces provided**: IF-0-SEMSUMFIX-1 supported authoritative summary
  runtime contract; IF-0-SEMSUMFIX-2 authoritative audit parity contract
- **Interfaces consumed**: SL-0 contract tests; existing local-default
  `oss_high` summarization config from
  `Settings.get_profile_summarization_config(...)`; current BAML-generated
  client version contract; existing direct profile API path and audit metadata
  persistence in `ChunkWriter`
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 unit slice first and confirm it reproduces the current
    authoritative summary-runtime blocker before changing runtime behavior or
    dependency state.
  - impl: Choose one supported repair path and keep it singular:
    either align the generated BAML client/runtime pair used by authoritative
    summaries, or deliberately route authoritative summaries through the
    existing profile-direct local path with equivalent audit metadata.
  - impl: If the repair path is dependency or generated-client alignment, keep
    the change narrowly scoped to the bundled BAML client/versioned dependency
    surface needed for `SummarizeFileChunks` and `SummarizeChunkAlone`; do not
    widen into unrelated package upgrades.
  - impl: If the repair path is a deliberate authoritative runtime reroute,
    make `FileBatchSummarizer.summarize_file_chunks(...)` and any helper it
    relies on recover deterministically through the supported direct profile
    path or topological path when the batch BAML runtime is unavailable, while
    preserving `is_authoritative=1` persistence and the same profile/effective
    model audit metadata contract.
  - impl: Keep `Settings.get_profile_summarization_config(...)` and the
    repo-default `oss_high` config stable unless an execution-proven runtime
    gap requires a narrow config or dependency correction for the chosen
    supported path.
  - impl: Do not introduce a new semantic mode flag or a separate summary
    runtime surface; SEMSUMFIX should repair the existing authoritative path
    used by rebuilds.
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_summarization.py -q --no-cov`
  - verify: `uv sync --locked`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run python - <<'PY'
import asyncio
from mcp_server.config.settings import get_settings
from mcp_server.indexing.summarization import ComprehensiveChunkWriter

settings = get_settings()
profile_id = settings.get_semantic_default_profile()
writer = ComprehensiveChunkWriter(
    db_path=".mcp-index/current.db",
    qdrant_client=None,
    summarization_config={
        **settings.get_profile_summarization_config(profile_id),
        "profile_id": profile_id,
    },
)
result = asyncio.run(writer.process_scope(limit=5))
print(result.to_dict())
PY`

### SL-2 - Semantic Rebuild Proof And Operator Evidence Reducer

- **Scope**: Re-run the clean semantic rebuild with the repaired authoritative
  summary runtime, prove that summaries and vectors now populate, and refresh
  the durable dogfood and operator evidence.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `docs/guides/semantic-onboarding.md`, `tests/real_world/test_semantic_search.py`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: IF-0-SEMSUMFIX-3 full rebuild semantic recovery
  contract; IF-0-SEMSUMFIX-4 operator evidence contract
- **Interfaces consumed**: SL-0 authoritative runtime assertions; SL-1 repaired
  authoritative summary runtime and audit metadata; existing rebuild commands,
  repo-local dogfood prompts, semantic readiness/status output, and durable
  evidence structure from SEMCOLLECT
- **Parallel-safe**: no
- **Tasks**:
  - test: Update `tests/real_world/test_semantic_search.py` so the repo-local
    dogfood acceptance case now requires semantic-path results for the fixed
    prompts once the repaired rebuild finishes, while still surfacing the exact
    blocker if execution proves semantic readiness is still not restored.
  - test: Update `tests/docs/test_semdogfood_evidence_contract.py` so the
    refreshed report must cite `plans/phase-plan-v7-SEMSUMFIX.md`, record the
    chosen authoritative summary-runtime repair, and require non-zero
    `chunk_summaries` plus non-zero `semantic_points` when recovery succeeds.
  - impl: Re-run the clean repo-local rebuild using the repaired default local
    `oss_high` path, capture the direct summary probe outcome, and confirm the
    rebuild now writes summaries before vectors.
  - impl: Refresh `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` with the repaired
    summary-runtime outcome, rebuild timing and memory metrics, post-rebuild
    `chunk_summaries` and `semantic_points` counts, repository status output,
    semantic query outcomes, and the final semantic-ready or exact still-blocked
    verdict.
  - impl: Update `docs/guides/semantic-onboarding.md` so operators can see how
    to distinguish collection bootstrap readiness from summary-runtime health,
    and so the troubleshooting section explains the supported repair chosen in
    SL-1 plus the post-rebuild commands to verify it.
  - impl: If the repaired rebuild still fails to produce summaries or vectors,
    record the exact remaining blocker and command evidence in the report
    instead of widening into ranking, multi-repo, or unrelated semantic work.
  - verify: `SEMANTIC_SEARCH_ENABLED=true CODE_INDEX_DOGFOOD_REPO=. OPENAI_API_KEY=dummy-local-key uv run pytest tests/real_world/test_semantic_search.py -q --no-cov`
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - verify: `sqlite3 .mcp-index/current.db 'select count(*) as chunk_summaries from chunk_summaries; select count(*) as semantic_points from semantic_points;'`

## Verification

Planning-only run: do not execute these during plan creation. Run them during
`codex-execute-phase` or manual SEMSUMFIX execution.

Lane-specific checks:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_summarization.py -q --no-cov
uv sync --locked
env OPENAI_API_KEY=dummy-local-key uv run python - <<'PY'
import asyncio
from mcp_server.config.settings import get_settings
from mcp_server.indexing.summarization import ComprehensiveChunkWriter

settings = get_settings()
profile_id = settings.get_semantic_default_profile()
writer = ComprehensiveChunkWriter(
    db_path=".mcp-index/current.db",
    qdrant_client=None,
    summarization_config={
        **settings.get_profile_summarization_config(profile_id),
        "profile_id": profile_id,
    },
)
result = asyncio.run(writer.process_scope(limit=5))
print(result.to_dict())
PY
SEMANTIC_SEARCH_ENABLED=true CODE_INDEX_DOGFOOD_REPO=. OPENAI_API_KEY=dummy-local-key uv run pytest tests/real_world/test_semantic_search.py -q --no-cov
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
```

Evidence commands:

```bash
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
env OPENAI_API_KEY=dummy-local-key uv run mcp-index preflight
sqlite3 .mcp-index/current.db \
  'select count(*) as chunk_summaries from chunk_summaries; select count(*) as semantic_points from semantic_points;'
```

Whole-phase regression commands:

```bash
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_summarization.py tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
SEMANTIC_SEARCH_ENABLED=true CODE_INDEX_DOGFOOD_REPO=. OPENAI_API_KEY=dummy-local-key uv run pytest tests/real_world/test_semantic_search.py -q --no-cov
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
git status --short -- specs/phase-plans-v7.md plans/phase-plan-v7-SEMSUMFIX.md
```

## Acceptance Criteria

- [ ] A direct authoritative summary probe for the default local `oss_high`
      path no longer fails on the current BAML generator/runtime mismatch, or
      the authoritative summary path is intentionally rerouted through a
      supported local provider path with equivalent audit metadata.
- [ ] A clean force-full rebuild produces non-zero `chunk_summaries`.
- [ ] The same rebuild produces non-zero `semantic_points` linked to
      `code_index__oss_high__v1`.
- [ ] Semantic dogfood queries for the fixed prompts return semantic-path code
      results instead of `semantic_not_ready`.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is refreshed with the repaired
      summary-runtime outcome and final semantic-ready or exact still-blocked
      verdict.
- [ ] `docs/guides/semantic-onboarding.md` explains how to verify the repaired
      authoritative summary runtime separately from collection bootstrap and
      semantic preflight.
- [ ] SEMSUMFIX stays bounded to authoritative summary runtime recovery and
      the semantic write path it unlocks; it does not widen into semantic
      ranking redesign, multi-repo rollout expansion, or unrelated collection
      namespace changes.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v7-SEMSUMFIX.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMSUMFIX.md
  artifact_state: staged
```
