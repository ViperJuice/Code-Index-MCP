---
phase_loop_plan_version: 1
phase: SEMREADYFIX
roadmap: specs/phase-plans-v7.md
roadmap_sha256: f68bc32dc1934fd6837fbd5682fbccd69856b608bc97ca027f758089f49e2aaa
---
# SEMREADYFIX: Default Enrichment Compatibility Recovery

## Context

SEMREADYFIX is the phase-8 blocker-repair follow-up for the v7 semantic
hardening roadmap. SEMDOGFOOD already completed the clean rebuild proof and
recorded the concrete blocker in `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`:
the repo rebuilt to lexical readiness, but semantic readiness stayed
`summaries_missing`, active-profile preflight stayed `blocked`, and the
default local `oss_high` enrichment path failed with `wrong_chat_model`.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is tracked and clean in this worktree, and its
  live SHA matches the required
  `f68bc32dc1934fd6837fbd5682fbccd69856b608bc97ca027f758089f49e2aaa`.
- The checkout is on `main` at `c4e7877`, and `main...origin/main` is ahead by
  8 commits before writing this plan.
- The upstream v7 planning chain already exists through
  `plans/phase-plan-v7-SEMDOGFOOD.md`; this phase must consume the semantic
  readiness states, profile-default contract, preflight fail-closed behavior,
  enrichment-first build order, and semantic-only query routing frozen by
  SEMCONTRACT through SEMDOGFOOD instead of redefining them.
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` now proves the failure mode this
  phase must repair: a clean force-full rebuild finished successfully but left
  `chunk_summaries=0`, `semantic_points=0`, semantic readiness
  `summaries_missing`, and semantic queries fail-closed with
  `code: "semantic_not_ready"`.
- `code-index-mcp.profiles.yaml` and `mcp_server/config/settings.py` already
  advertise the intended local-default enrichment path for `oss_high` as
  `${SEMANTIC_ENRICHMENT_BASE_URL:http://ai:8002/v1}` with
  `${SEMANTIC_ENRICHMENT_MODEL:chat}`, while the embedding path remains
  `${SEMANTIC_EMBEDDING_BASE_URL:http://ai:8001/v1}` with
  `Qwen/Qwen3-Embedding-8B`.
- `mcp_server/setup/semantic_preflight.py` currently sends the enrichment
  smoke directly to `/chat/completions` with the configured model name and
  classifies a model-rejection response as `wrong_chat_model`, but it does not
  yet expose or reuse an effective model-resolution contract for the active
  enrichment endpoint.
- `mcp_server/indexing/summarization.py` uses the profile-configured
  `base_url` and `model_name` directly for the profile endpoint path and
  stores `llm_model` audit metadata, but it does not yet guarantee that the
  model used for authoritative summary writes matches the same compatibility
  decision preflight made.
- `tests/test_semantic_profile_settings.py`, `tests/test_semantic_preflight.py`,
  and `tests/test_summarization.py` already freeze the current `oss_high`
  default metadata, preflight blocker vocabulary, and summary audit metadata,
  so they are the narrow contract tests to extend before mutating runtime
  behavior.
- `tests/real_world/test_semantic_search.py` already has a repo-local dogfood
  harness for the repaired semantic query path, but today it skips when
  semantic readiness remains blocked; the final SEMREADYFIX evidence must turn
  that path into a semantic-path success case for the fixed prompts.

Practical planning boundary:

- SEMREADYFIX may probe the local enrichment endpoint, repair the active
  `oss_high` enrichment compatibility contract, align preflight and summary
  writes on the same effective model decision, rerun the clean dogfood rebuild,
  and refresh the dogfood evidence plus concise operator guidance.
- SEMREADYFIX must stay narrowly on enrichment compatibility, preflight,
  semantic summary/vector generation, and refreshed dogfood proof. It must not
  widen into semantic ranking redesign, reranker rollout, multi-repo topology
  changes, or new cloud-only fallback behavior.

## Interface Freeze Gates

- [ ] IF-0-SEMREADYFIX-1 - Effective enrichment target contract:
      `run_semantic_preflight(...).effective_config["enrichment"]` reports the
      active enrichment `base_url`, the configured model identifier, and the
      effective model identifier actually used for the chat smoke; summary
      generation for the active profile must use that same effective model
      decision.
- [ ] IF-0-SEMREADYFIX-2 - Wrong-chat-model blocker contract:
      `wrong_chat_model` is emitted only after the active enrichment endpoint
      cannot satisfy the configured/default `oss_high` chat target through the
      chosen compatibility path, and the failure payload includes enough
      redacted metadata to explain which model IDs were considered without
      printing secrets.
- [ ] IF-0-SEMREADYFIX-3 - Authoritative summary audit contract:
      repaired `chunk_summaries` rows record the active profile, enrichment
      base URL, and actual enrichment model used for the write so semantic
      invalidation and the dogfood report can prove which local/default path
      generated the summaries.
- [ ] IF-0-SEMREADYFIX-4 - Repaired dogfood proof contract:
      after the compatibility repair, a clean force-full rebuild of this repo
      under `oss_high` yields non-zero `chunk_summaries`, non-zero
      `semantic_points`, active-profile preflight no longer blocked on
      `wrong_chat_model`, and the fixed repo-local semantic dogfood prompts
      return semantic-path results instead of `semantic_not_ready`.

## Lane Index & Dependencies

- SL-0 - Enrichment compatibility contract tests; Depends on: SEMDOGFOOD; Blocks: SL-1, SL-2; Parallel-safe: no
- SL-1 - Default `oss_high` enrichment compatibility implementation; Depends on: SL-0; Blocks: SL-2; Parallel-safe: no
- SL-2 - Repaired dogfood rerun and evidence reducer; Depends on: SL-0, SL-1; Blocks: SEMREADYFIX acceptance; Parallel-safe: no

Lane DAG:

```text
SEMDOGFOOD
  -> SL-0 -> SL-1 -> SL-2 -> SEMREADYFIX acceptance
```

## Lanes

### SL-0 - Enrichment Compatibility Contract Tests

- **Scope**: Freeze the effective-model compatibility behavior for the default
  `oss_high` enrichment path before changing runtime code.
- **Owned files**: `tests/test_semantic_profile_settings.py`, `tests/test_semantic_preflight.py`, `tests/test_summarization.py`
- **Interfaces provided**: executable assertions for IF-0-SEMREADYFIX-1,
  IF-0-SEMREADYFIX-2, and IF-0-SEMREADYFIX-3
- **Interfaces consumed**: pre-existing `Settings.get_semantic_profiles_config`,
  `Settings.get_profile_summarization_config`, `run_semantic_preflight(...)`,
  `check_enrichment_chat(...)`, `ChunkWriter._call_profile_api(...)`, and
  summary audit metadata persistence
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_semantic_profile_settings.py` so the default
    `oss_high` contract freezes the configured enrichment endpoint/model
    metadata separately from any effective runtime model choice and preserves
    the existing `SEMANTIC_*` over `VLLM_*` precedence rules.
  - test: Extend `tests/test_semantic_preflight.py` with synthetic
    `/models`-discovery cases that cover exact configured-model success,
    compatibility-resolution success for the default local chat target, and a
    terminal `wrong_chat_model` failure when no acceptable chat model can be
    derived.
  - test: Extend `tests/test_summarization.py` so authoritative summary audit
    metadata proves the persisted `llm_model` and profile/base-url metadata
    match the effective enrichment model decision used for the profile endpoint
    path.
  - impl: Reuse mocks around `_http_get_json`, `_http_post_json`, and the
    summarizer profile endpoint path; keep these tests deterministic and free
    of live network dependence.
  - verify: `uv run pytest tests/test_semantic_profile_settings.py tests/test_semantic_preflight.py tests/test_summarization.py -q --no-cov`

### SL-1 - Default `oss_high` Enrichment Compatibility Implementation

- **Scope**: Repair the default local `oss_high` enrichment path so preflight
  and authoritative summary generation agree on a chat model that the active
  enrichment endpoint can actually serve.
- **Owned files**: `code-index-mcp.profiles.yaml`, `mcp_server/config/settings.py`, `mcp_server/artifacts/semantic_profiles.py`, `mcp_server/setup/semantic_preflight.py`, `mcp_server/indexing/summarization.py`
- **Interfaces provided**: IF-0-SEMREADYFIX-1 effective enrichment target
  contract; IF-0-SEMREADYFIX-2 wrong-chat-model blocker contract;
  IF-0-SEMREADYFIX-3 summary audit metadata contract
- **Interfaces consumed**: SL-0 contract tests; existing `oss_high`
  profile/default metadata; existing preflight blocker vocabulary;
  existing summary audit metadata persistence; local enrichment endpoint
  metadata from `GET http://ai:8002/v1/models`
- **Parallel-safe**: no
- **Tasks**:
  - test: Run the SL-0 compatibility tests first and confirm the current
    implementation still reproduces the `wrong_chat_model` default-path
    failure.
  - impl: Add one deterministic effective-model resolution path for the active
    enrichment endpoint that can prove which chat model will be used for the
    default `oss_high` path without widening into a general provider rewrite.
  - impl: Keep the configured/default metadata and the effective runtime model
    choice distinct: the code should expose both in preflight/audit surfaces
    when compatibility resolution is needed, while preserving existing env-var
    precedence and embedding defaults.
  - impl: Update `run_semantic_preflight(...)` and `check_enrichment_chat(...)`
    so the fail-closed blocker is emitted only after the effective-model
    resolution path cannot produce a served chat model for the active endpoint,
    and so `effective_config["enrichment"]` reports the configured and
    effective model identifiers plus redacted compatibility evidence.
  - impl: Update the profile-endpoint path in
    `mcp_server/indexing/summarization.py` so authoritative summary writes use
    the same effective enrichment model decision and persist the actual model
    used in audit metadata.
  - impl: If execution proves the repo-default `chat` alias is not actually
    served by the local enrichment endpoint, repair the repo-default
    `oss_high` metadata or its deterministic translation path inside this lane;
    do not leave the default profile dependent on ad hoc per-run overrides.
  - impl: Preserve the current fallback ordering to Cerebras, Anthropic, or
    OpenAI when the profile endpoint itself is unavailable; this phase is about
    default local compatibility, not a new fallback policy.
  - verify: `uv run pytest tests/test_semantic_profile_settings.py tests/test_semantic_preflight.py tests/test_summarization.py -q --no-cov`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index index check-semantic`
  - verify: `curl -s http://ai:8002/v1/models`

### SL-2 - Repaired Dogfood Rerun And Evidence Reducer

- **Scope**: Rerun the clean semantic dogfood rebuild with the repaired
  default `oss_high` enrichment path, prove semantic-path success for the
  fixed prompts, and refresh the durable operator evidence.
- **Owned files**: `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`, `docs/guides/semantic-onboarding.md`, `tests/real_world/test_semantic_search.py`, `tests/docs/test_semdogfood_evidence_contract.py`
- **Interfaces provided**: IF-0-SEMREADYFIX-4 repaired dogfood proof contract
- **Interfaces consumed**: SL-0 compatibility assertions; SL-1 effective
  enrichment target and summary audit metadata; existing SEMDOGFOOD report and
  repo-local reset boundary; `uv run mcp-index repository sync --force-full`;
  `uv run mcp-index repository status`; `uv run mcp-index preflight`; repo-local
  semantic dogfood prompts in `tests/real_world/test_semantic_search.py`
- **Parallel-safe**: no
- **Tasks**:
  - test: Update `tests/real_world/test_semantic_search.py` so the repo-local
    dogfood harness becomes a real semantic-path acceptance check after the
    repair instead of only a skip-on-not-ready guard, while still remaining
    opt-in for environments that do not target this repo.
  - test: Update `tests/docs/test_semdogfood_evidence_contract.py` so the
    refreshed report must cite `plans/phase-plan-v7-SEMREADYFIX.md`, record the
    repaired enrichment model/provider decision, show non-zero
    `chunk_summaries` and `semantic_points`, and state the post-repair
    semantic-ready verdict.
  - impl: Re-run the clean repo-local reset boundary and force-full sync using
    the repaired default `oss_high` path, preserving shared live
    `qdrant_storage/` unless a new explicit destructive blocker appears.
  - impl: Capture the repaired preflight output, repository status output,
    rebuild timing/max-RSS/index-size metrics, summary/vector counts, and the
    effective enrichment model/provider metadata in
    `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`.
  - impl: Re-run the fixed semantic dogfood prompts and summarize lexical,
    symbol, fuzzy, and semantic outcomes after the repair, proving the
    semantic path returns relevant implementation files rather than
    `semantic_not_ready`.
  - impl: Update `docs/guides/semantic-onboarding.md` so operators can see the
    difference between configured enrichment model metadata, effective runtime
    enrichment model choice, and the dogfood evidence artifact to consult after
    a clean rebuild.
  - impl: If the repaired rebuild still fails semantic readiness, record the
    exact remaining blocker and evidence in the report instead of widening into
    unrelated semantic work.
  - verify: `SEMANTIC_SEARCH_ENABLED=true CODE_INDEX_DOGFOOD_REPO=. uv run pytest tests/real_world/test_semantic_search.py -q --no-cov`
  - verify: `uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status`
  - verify: `env OPENAI_API_KEY=dummy-local-key uv run mcp-index preflight`
  - verify: `sqlite3 .mcp-index/current.db 'select count(*) from chunk_summaries; select count(*) from semantic_points;'`

## Verification

Planning-only run: do not execute these during plan creation. Run them during
`codex-execute-phase` or manual SEMREADYFIX execution.

Lane-specific checks:

```bash
uv run pytest tests/test_semantic_profile_settings.py tests/test_semantic_preflight.py tests/test_summarization.py -q --no-cov
env OPENAI_API_KEY=dummy-local-key uv run mcp-index index check-semantic
SEMANTIC_SEARCH_ENABLED=true CODE_INDEX_DOGFOOD_REPO=. uv run pytest tests/real_world/test_semantic_search.py -q --no-cov
uv run pytest tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
```

Evidence commands:

```bash
curl -s http://ai:8002/v1/models
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
env OPENAI_API_KEY=dummy-local-key uv run mcp-index preflight
/usr/bin/time -v env \
  SEMANTIC_SEARCH_ENABLED=true \
  SEMANTIC_DEFAULT_PROFILE=oss_high \
  OPENAI_API_KEY=dummy-local-key \
  QDRANT_URL=http://localhost:6333 \
  uv run mcp-index repository sync --force-full
sqlite3 .mcp-index/current.db \
  'select count(*) as chunk_summaries from chunk_summaries; select count(*) as semantic_points from semantic_points;'
du -sh .mcp-index qdrant_storage 2>/dev/null
```

Whole-phase regression commands:

```bash
uv run pytest \
  tests/test_semantic_profile_settings.py \
  tests/test_semantic_preflight.py \
  tests/test_summarization.py \
  tests/docs/test_semdogfood_evidence_contract.py \
  -q --no-cov
SEMANTIC_SEARCH_ENABLED=true CODE_INDEX_DOGFOOD_REPO=. uv run pytest tests/real_world/test_semantic_search.py -q --no-cov
git status --short -- specs/phase-plans-v7.md plans/phase-plan-v7-SEMREADYFIX.md
```

## Acceptance Criteria

- [ ] The default `oss_high` enrichment endpoint/model contract is repaired so
      the active local enrichment service can actually serve the chat model
      path used for dogfood.
- [ ] Active-profile semantic preflight no longer fails with
      `wrong_chat_model` for the default local dogfood configuration.
- [ ] Preflight and authoritative summary generation use the same effective
      enrichment model decision, and summary audit metadata records the actual
      model/provider/base-url details used for writes.
- [ ] A clean force-full rebuild of this repository produces non-zero
      `chunk_summaries` and non-zero `semantic_points` for `oss_high`.
- [ ] The repo-local semantic dogfood prompts return semantic-path results for
      the fixed natural-language prompts instead of `semantic_not_ready`.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is refreshed with the repaired
      semantic-ready verdict, rebuild metrics, summary/vector counts, and the
      effective enrichment model/provider metadata used during the run.
- [ ] `docs/guides/semantic-onboarding.md` tells operators how to interpret the
      configured enrichment model, the effective runtime enrichment model, and
      the refreshed dogfood evidence.
- [ ] SEMREADYFIX stays bounded to default enrichment compatibility, preflight,
      rebuild validation, and refreshed dogfood evidence; it does not widen
      into semantic ranking redesign or unrelated rollout changes.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v7-SEMREADYFIX.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMREADYFIX.md
  artifact_state: staged
```
