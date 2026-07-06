---
phase_loop_plan_version: 1
phase: SEMPREFLIGHT
roadmap: specs/phase-plans-v7.md
roadmap_sha256: b8ba13bf3898d59c087f64193fa7415b0f932b34fc002e862d2678d74c1faf0c
---
# SEMPREFLIGHT: Semantic Preflight and Fail-Closed Gates

## Context

SEMPREFLIGHT is the phase-3 fail-closed gate for the v7 semantic hardening
roadmap. It should turn the SEMCONFIG profile defaults into concrete operator
and runtime checks that can prove enrichment, embedding, and Qdrant collection
compatibility before later phases are allowed to write semantic vectors.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is tracked in this worktree, and its live SHA
  matches the required
  `b8ba13bf3898d59c087f64193fa7415b0f932b34fc002e862d2678d74c1faf0c`.
- The checkout is on `main` at `8cac8f9` and is clean before writing this
  plan, with `main...origin/main [ahead 3]`.
- `plans/phase-plan-v7-SEMCONTRACT.md` and
  `plans/phase-plan-v7-SEMCONFIG.md` already exist as the upstream v7 phase
  plans, and SEMPREFLIGHT explicitly depends on the configuration and metadata
  surfaces that SEMCONFIG froze.
- `run_semantic_preflight(...)` currently validates profile parsing, one
  embedding endpoint reachability check, and generic Qdrant reachability. It
  does not send an enrichment chat smoke, does not validate returned embedding
  dimension against the selected profile, and does not inspect the target
  Qdrant collection's name, vector size, or distance metric.
- The preflight report shape currently exposes `qdrant`, `embedding`, and
  `profiles` plus `overall_ready`; it does not carry a structured blocker that
  later semantic build paths can treat as a fail-closed "do not write vectors"
  contract.
- `setup semantic` and `mcp-index index check-semantic` currently print the
  shallow preflight result. Strict mode fails only on the aggregate
  `overall_ready` boolean, so operators do not get a deterministic blocker that
  names wrong chat model, missing API-key env-var presence, collection-missing,
  or collection-shape mismatch separately.
- Repository status surfaces currently distinguish lexical readiness from
  semantic readiness based on durable local evidence, but they do not also
  surface runtime semantic preflight blockers for the active profile. A repo can
  therefore look semantically stale or incomplete without telling the operator
  whether the selected local endpoints and Qdrant collection are safe for the
  next semantic build attempt.
- `SemanticIndexer._ensure_collection()` already knows how to compare Qdrant
  vector size and distance against the active semantic profile, and
  `SemanticNamespaceResolver` already normalizes collection identity, so this
  phase can reuse those contracts instead of inventing a second collection
  policy.

Practical planning boundary:

- SEMPREFLIGHT may deepen the semantic preflight probes, add a structured
  semantic-write blocker, wire the CLI/status surfaces to that blocker, and
  document the resulting operator contract.
- SEMPREFLIGHT must stay read-only with respect to semantic content: no summary
  generation, no semantic vector writes, no full repository sync, and no query
  ranking changes. Those belong to SEMPIPE and later phases.

## Interface Freeze Gates

- [ ] IF-0-SEMPREFLIGHT-1 - Enrichment smoke contract: semantic preflight sends
      a redacted OpenAI-compatible chat smoke to the selected profile's
      enrichment endpoint using the configured chat model and reports only
      metadata such as endpoint, model, API-key env-var name, env-var presence,
      and failure class.
- [ ] IF-0-SEMPREFLIGHT-2 - Embedding dimension contract: semantic preflight
      sends an embedding smoke to the selected profile's embedding endpoint and
      refuses semantic-write readiness when the returned vector dimension does
      not match the active semantic profile.
- [ ] IF-0-SEMPREFLIGHT-3 - Qdrant collection contract: semantic preflight
      verifies collection existence, normalized collection identity, vector
      size, and distance metric for the selected profile namespace without
      creating or mutating the collection during the check.
- [ ] IF-0-SEMPREFLIGHT-4 - Structured blocker contract: semantic preflight
      returns a deterministic blocker payload for semantic vector writes,
      including failing checks, remediation, and a machine-readable
      `can_write_semantic_vectors` or equivalent fail-closed surface that later
      build phases can consume directly.
- [ ] IF-0-SEMPREFLIGHT-5 - Operator/status surfacing contract: `setup
      semantic`, `mcp-index index check-semantic`, and repository readiness
      surfaces show the active-profile semantic preflight result and blocker
      without printing secret values or requiring a full index run.

## Lane Index & Dependencies

- SL-0 - Core semantic preflight probes and blocker model; Depends on: (none); Blocks: SL-1, SL-2, SL-3; Parallel-safe: no
- SL-1 - Operator CLI and check-semantic surfacing; Depends on: SL-0; Blocks: SL-3; Parallel-safe: yes
- SL-2 - Repository readiness and repo-status semantic preflight surfacing; Depends on: SL-0; Blocks: SL-3; Parallel-safe: yes
- SL-3 - Docs and contract reducer; Depends on: SL-0, SL-1, SL-2; Blocks: SEMPIPE; Parallel-safe: no

Lane DAG:

```text
SL-0 ----> SL-1 --.
   \               \
    `--> SL-2 ------> SL-3 --> SEMPIPE
```

## Lanes

### SL-0 - Core Semantic Preflight Probes And Blocker Model

- **Scope**: Expand semantic preflight itself so it proves enrichment,
  embedding, and Qdrant collection compatibility for the selected profile and
  emits a structured fail-closed blocker for semantic vector writes.
- **Owned files**: `mcp_server/setup/semantic_preflight.py`, `mcp_server/artifacts/semantic_namespace.py`, `tests/test_semantic_preflight.py`
- **Interfaces provided**: IF-0-SEMPREFLIGHT-1; IF-0-SEMPREFLIGHT-2;
  IF-0-SEMPREFLIGHT-3; IF-0-SEMPREFLIGHT-4; `SemanticPreflightReport` fields
  that distinguish enrichment, embedding, collection, and blocker outcomes for
  the selected profile
- **Interfaces consumed**: SEMCONFIG resolved enrichment and embedding metadata;
  `SemanticProfileRegistry`; `SemanticNamespaceResolver`; active profile vector
  dimension/distance contract; existing `SemanticIndexer` collection-shape
  expectations
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_semantic_preflight.py` so preflight sends a
    redacted OpenAI-compatible chat smoke to the selected profile enrichment
    endpoint using `model: "chat"` and reports unreachable-proxy failures
    without leaking secret values.
  - test: Add coverage proving preflight rejects a wrong chat model, an
    embedding-dimension mismatch, a missing collection, and a missing API-key
    env var with distinct structured blocker reasons instead of one generic
    warning string.
  - test: Add coverage proving Qdrant collection inspection validates the
    selected profile namespace, vector size, and distance metric without
    mutating Qdrant state.
  - test: Keep redaction strict: serialized report and blocker payloads may
    expose env-var names and presence booleans only, never the secret values.
  - impl: Add an explicit enrichment probe that uses the selected profile's
    resolved enrichment endpoint/model rather than treating enrichment as
    metadata-only.
  - impl: Add an explicit embedding smoke that validates returned vector length
    against the active semantic profile's `vector_dimension`.
  - impl: Add a Qdrant collection probe that checks collection existence plus
    shape against the selected profile's normalized collection identity and
    distance metric, reusing the existing namespace and semantic-indexer
    contracts where practical.
  - impl: Introduce a structured blocker surface on the preflight report so
    downstream execution can tell whether semantic vector writes are allowed and
    exactly which prerequisite failed.
  - impl: Keep the phase read-only for semantic content. Do not create
    collections, generate summaries, or write semantic vectors here.
  - verify: `uv run pytest tests/test_semantic_preflight.py -q --no-cov`

### SL-1 - Operator CLI And Check-Semantic Surfacing

- **Scope**: Make operator-facing semantic setup commands expose the deeper
  preflight contract and structured blocker clearly without widening into full
  indexing or gateway orchestration.
- **Owned files**: `mcp_server/cli/setup_commands.py`, `mcp_server/cli/index_management.py`, `tests/test_setup_cli.py`, `tests/test_index_management.py`
- **Interfaces provided**: IF-0-SEMPREFLIGHT-5 CLI/setup surfaces; strict-mode
  failure semantics driven by the structured semantic-write blocker; human and
  JSON output that names enrichment, embedding, collection, and blocker status
- **Interfaces consumed**: SL-0 `SemanticPreflightReport` enrichment,
  embedding, collection, and blocker fields; existing Qdrant autostart flow
- **Parallel-safe**: yes
- **Tasks**:
  - test: Extend `tests/test_setup_cli.py` so `setup semantic --json` exposes
    the structured blocker plus enrichment/embedding/collection checks, and
    text output names the next operator action when semantic writes are blocked.
  - test: Add `tests/test_index_management.py` coverage for `mcp-index index
    check-semantic` proving it renders the richer preflight state and exits
    predictably in strict-mode blocker scenarios.
  - test: Preserve the current autostart-Qdrant retry flow while ensuring the
    second preflight pass still reports the same structured blocker schema.
  - impl: Update `setup semantic` output so it reports enrichment smoke,
    embedding smoke, collection validation, and the semantic-write blocker
    rather than only `overall_ready`.
  - impl: Update `index check-semantic` to show the same active-profile
    preflight contract and blocker data instead of dumping only the old shallow
    `effective_config` payload.
  - impl: Keep strict mode fail-closed on the structured blocker contract, not
    just an unqualified boolean, while preserving the existing dry-run and JSON
    behaviors.
  - impl: Do not widen this lane into gateway startup behavior or repository
    sync orchestration.
  - verify: `uv run pytest tests/test_setup_cli.py tests/test_index_management.py -q --no-cov`

### SL-2 - Repository Readiness And Repo-Status Semantic Preflight Surfacing

- **Scope**: Surface active-profile semantic preflight blockers through
  repository readiness and `repository status` output without changing the
  existing durable semantic-readiness contract or requiring a full index run.
- **Owned files**: `mcp_server/health/repository_readiness.py`, `mcp_server/health/repo_status.py`, `mcp_server/cli/repository_commands.py`, `tests/test_health_surface.py`, `tests/test_repository_commands.py`
- **Interfaces provided**: IF-0-SEMPREFLIGHT-5 repository-status portion;
  additive readiness/status fields that distinguish durable semantic readiness
  from active-profile semantic preflight blocker state
- **Interfaces consumed**: SL-0 structured blocker and selected-profile
  enrichment/embedding/collection results; existing `SemanticReadiness`,
  `build_health_row(...)`, and `repository status` CLI rendering
- **Parallel-safe**: yes
- **Tasks**:
  - test: Extend `tests/test_health_surface.py` so health rows keep the
    existing lexical and durable semantic readiness fields while also exposing
    additive semantic preflight blocker metadata for the active profile.
  - test: Extend `tests/test_repository_commands.py` so `repository status`
    prints semantic preflight status/remediation when the active profile has a
    runtime blocker such as missing collection or wrong vector size.
  - test: Keep non-semantic rollout/query readiness fields stable so this lane
    does not regress the existing local-only, stale-commit, or
    safe-fallback-native-search behavior.
  - impl: Add a narrow runtime semantic-preflight surface to readiness/status
    serialization instead of overloading the existing durable
    `semantic_readiness` states.
  - impl: Update `build_health_row(...)` and `repository status` rendering so
    operators can see both "what durable semantic evidence exists" and "whether
    the current profile endpoints/collection are safe for the next semantic
    write attempt."
  - impl: Keep this lane additive and fail-closed. Do not start indexing, do
    not create collections, and do not collapse runtime preflight blockers into
    lexical `index_unavailable`.
  - verify: `uv run pytest tests/test_health_surface.py tests/test_repository_commands.py -q --no-cov`

### SL-3 - Docs And Contract Reducer

- **Scope**: Reduce the SEMPREFLIGHT operator/runtime gate into docs and a docs
  contract test without pulling full semantic build behavior forward from
  SEMPIPE.
- **Owned files**: `docs/guides/semantic-onboarding.md`, `docs/tools/cli-setup-reference.md`, `tests/docs/test_sempreflight_contract.py`
- **Interfaces provided**: docs that describe enrichment smoke, embedding
  dimension validation, Qdrant collection validation, API-key presence
  reporting, and the semantic-write blocker contract for active profiles
- **Interfaces consumed**: SL-0 blocker semantics; SL-1 CLI output language;
  SL-2 repository-status wording; roadmap SEMPREFLIGHT exit criteria
- **Parallel-safe**: no
- **Tasks**:
  - test: Add a docs contract test that requires onboarding/setup docs to name
    the enrichment chat smoke, embedding dimension validation, Qdrant
    collection checks, and metadata-only API-key reporting.
  - test: Require docs to state that semantic preflight can block semantic
    vector writes before SEMPIPE and that the phase remains read-only with
    respect to summaries/vectors.
  - impl: Update `docs/guides/semantic-onboarding.md` so it explains what
    `setup semantic` now proves for `oss_high`: chat reachability, embedding
    dimension match, collection namespace/shape match, and blocker semantics.
  - impl: Update `docs/tools/cli-setup-reference.md` so `setup semantic` and
    `index check-semantic` describe the structured blocker and the separate
    collection validation step.
  - impl: Keep docs bounded to preflight and fail-closed gating. Do not claim
    that this phase writes summaries or vectors.
  - verify: `uv run pytest tests/docs/test_sempreflight_contract.py -q --no-cov`
  - verify: `rg -n "chat smoke|embedding|vector dimension|collection|api-key|blocker|write semantic vectors" docs/guides/semantic-onboarding.md docs/tools/cli-setup-reference.md tests/docs/test_sempreflight_contract.py`

## Verification

Planning-only run: do not execute these during plan creation. Run them during
`codex-execute-phase` or manual SEMPREFLIGHT execution.

Lane-specific checks:

```bash
uv run pytest tests/test_semantic_preflight.py -q --no-cov
uv run pytest tests/test_setup_cli.py tests/test_index_management.py -q --no-cov
uv run pytest tests/test_health_surface.py tests/test_repository_commands.py -q --no-cov
uv run pytest tests/docs/test_sempreflight_contract.py -q --no-cov
rg -n "SemanticPreflightReport|chat|embedding|collection|vector_dimension|distance_metric|can_write_semantic_vectors|semantic preflight" \
  mcp_server/setup/semantic_preflight.py \
  mcp_server/artifacts/semantic_namespace.py \
  mcp_server/cli/setup_commands.py \
  mcp_server/cli/index_management.py \
  mcp_server/health/repository_readiness.py \
  mcp_server/health/repo_status.py \
  mcp_server/cli/repository_commands.py \
  docs/guides/semantic-onboarding.md \
  docs/tools/cli-setup-reference.md \
  tests/test_semantic_preflight.py \
  tests/test_setup_cli.py \
  tests/test_index_management.py \
  tests/test_health_surface.py \
  tests/test_repository_commands.py \
  tests/docs/test_sempreflight_contract.py
```

Whole-phase regression commands:

```bash
uv run pytest \
  tests/test_semantic_preflight.py \
  tests/test_setup_cli.py \
  tests/test_index_management.py \
  tests/test_health_surface.py \
  tests/test_repository_commands.py \
  tests/docs/test_sempreflight_contract.py \
  -q --no-cov
git status --short -- specs/phase-plans-v7.md plans/phase-plan-v7-SEMPREFLIGHT.md
```

## Acceptance Criteria

- [ ] Preflight sends a redacted OpenAI-compatible chat smoke to the selected
      enrichment endpoint using the configured chat model and reports metadata
      only.
- [ ] Preflight sends an embedding smoke to the selected embedding endpoint and
      rejects semantic-write readiness when returned vector dimension does not
      match the active semantic profile.
- [ ] Qdrant collection validation checks existence, normalized collection
      identity, vector size, and distance metric for the active profile
      namespace.
- [ ] Preflight reports API-key env-var names and presence only; no secret
      values appear in warnings, details, JSON output, or blocker payloads.
- [ ] Semantic preflight returns a structured fail-closed blocker that later
      semantic build phases can treat as "do not write vectors yet."
- [ ] `setup semantic`, `mcp-index index check-semantic`, and `repository
      status` surface the active-profile preflight result and remediation
      without requiring a full index run.
- [ ] Tests cover unreachable enrichment proxy, wrong chat model, embedding
      dimension mismatch, missing collection, and missing API key env var.
- [ ] SEMPREFLIGHT stays preflight-only: no summary generation, no semantic
      vector writes, and no full semantic sync.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v7-SEMPREFLIGHT.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMPREFLIGHT.md
  artifact_state: staged
```
