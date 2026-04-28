---
phase_loop_plan_version: 1
phase: SEMCONFIG
roadmap: specs/phase-plans-v7.md
roadmap_sha256: b8ba13bf3898d59c087f64193fa7415b0f932b34fc002e862d2678d74c1faf0c
---
# SEMCONFIG: Local Enrichment and Embedding Configuration

## Context

SEMCONFIG is the phase-2 configuration freeze for the v7 semantic hardening
roadmap. It turns the SEMCONTRACT readiness model into a concrete local
profile contract for `oss_high`: Gemma/proxy enrichment first, Qwen embedding
second, with a default install path that can actually execute the
OpenAI-compatible local calls those defaults require.

Current repo state gathered during planning:

- `specs/phase-plans-v7.md` is tracked and clean in this worktree, and its live
  SHA matches the required
  `b8ba13bf3898d59c087f64193fa7415b0f932b34fc002e862d2678d74c1faf0c`.
- The checkout is on `main` at `41a88ca`, and the worktree was clean before
  writing this plan.
- `plans/phase-plan-v7-SEMCONTRACT.md` already exists as the upstream v7 phase
  plan, and SEMCONFIG explicitly depends on that semantic-readiness contract.
- `code-index-mcp.profiles.yaml` still points `oss_high` summarization at
  `${VLLM_SUMMARIZATION_BASE_URL:http://win:8002/v1}` with model
  `Qwen/Qwen2.5-Coder-14B-Instruct-AWQ`, while the roadmap north star expects
  enrichment at `http://ai:8002/v1` through the proxy alias `chat`.
- The same profile already points embeddings at
  `${VLLM_EMBEDDING_BASE_URL:http://ai:8001/v1}` with
  `Qwen/Qwen3-Embedding-8B`, so the embedding side is closer to target than
  the enrichment side.
- `Settings.get_semantic_profiles_config()` converts profile YAML into runtime
  profile metadata, but today it only carries embedding-side
  `build_metadata.openai_api_base` and `openai_api_key_env`; it does not
  preserve a separate enrichment endpoint/model/API-key-env contract for the
  active profile.
- `Settings.get_profile_summarization_config()` reads the raw YAML
  summarization block and expands env vars, but it does not currently own the
  legacy-to-new alias shim story for
  `VLLM_SUMMARIZATION_BASE_URL`/`VLLM_EMBEDDING_BASE_URL`.
- `run_semantic_preflight()` currently prefers `settings.openai_api_base`
  before profile-level embedding metadata, and its `effective_config` surface
  reports only the selected profile, provider, Qdrant URL, and a single
  `openai_api_base` field. It does not distinguish enrichment from embedding
  config or report API-key env var names/presence in a redacted way.
- OpenAI-compatible local calls currently rely on the `openai` package in both
  `mcp_server/indexing/summarization.py` and
  `mcp_server/utils/embedding_providers.py`, but `pyproject.toml` still places
  `openai` under the optional `semantic` extra instead of the core dependency
  set.
- `docs/guides/semantic-onboarding.md` still documents `OPENAI_API_BASE` as
  the main local endpoint knob and does not yet explain the new
  enrichment-versus-embedding split or the legacy VLLM compatibility shims the
  roadmap allows.

Practical planning boundary:

- SEMCONFIG may change profile YAML, settings hydration, dependency posture,
  semantic preflight reporting, and operator docs/tests.
- SEMCONFIG must not trigger a rebuild, change semantic query ranking, or add
  cloud-worker forwarding behavior. Those belong to later v7 phases.

## Interface Freeze Gates

- [ ] IF-0-SEMCONFIG-1 - `oss_high` local profile defaults contract:
      `code-index-mcp.profiles.yaml` defines enrichment separately from
      embedding, with summarization defaulting to
      `${SEMANTIC_ENRICHMENT_BASE_URL:http://ai:8002/v1}` and
      `${SEMANTIC_ENRICHMENT_MODEL:chat}`, and embeddings defaulting to
      `${SEMANTIC_EMBEDDING_BASE_URL:http://ai:8001/v1}` with
      `Qwen/Qwen3-Embedding-8B`.
- [ ] IF-0-SEMCONFIG-2 - Compatibility-shim and runtime-metadata contract:
      legacy `VLLM_SUMMARIZATION_BASE_URL` and `VLLM_EMBEDDING_BASE_URL`
      remain accepted only as compatibility shims, and runtime settings expose
      separate enrichment and embedding endpoint/model/API-key-env metadata for
      the active profile without logging secret values.
- [ ] IF-0-SEMCONFIG-3 - Default-install local-call contract:
      the default `uv sync --locked` install can execute the repo's
      OpenAI-compatible enrichment and embedding code paths without requiring
      the optional `semantic` extra just to import the local client stack.
- [ ] IF-0-SEMCONFIG-4 - Preflight and docs contract:
      semantic preflight and onboarding/setup docs describe the new local
      enrichment-versus-embedding split, use the selected profile's resolved
      endpoints, and report API-key env var names/presence only, never secret
      values.

## Lane Index & Dependencies

- SL-0 - Profile defaults and settings hydration; Depends on: (none); Blocks: SL-2, SL-3; Parallel-safe: no
- SL-1 - Default-install OpenAI-compatible dependency posture; Depends on: (none); Blocks: SL-2, SL-3; Parallel-safe: yes
- SL-2 - Preflight redaction and selected-profile surfacing; Depends on: SL-0, SL-1; Blocks: SL-3; Parallel-safe: no
- SL-3 - Docs and contract reducer; Depends on: SL-0, SL-1, SL-2; Blocks: SEMPREFLIGHT; Parallel-safe: no

Lane DAG:

```text
SL-0 ----.
         +--> SL-2 --> SL-3 --> SEMPREFLIGHT
SL-1 ----'
```

## Lanes

### SL-0 - Profile Defaults And Settings Hydration

- **Scope**: Rewrite the `oss_high` source-of-truth profile defaults and make
  settings hydration preserve distinct enrichment and embedding config,
  including legacy VLLM alias handling.
- **Owned files**: `code-index-mcp.profiles.yaml`, `mcp_server/config/settings.py`, `tests/test_semantic_profile_settings.py`
- **Interfaces provided**: IF-0-SEMCONFIG-1; IF-0-SEMCONFIG-2 profile-shape and
  runtime-metadata portions; resolved per-profile enrichment config from
  `Settings.get_profile_summarization_config(...)`; resolved embedding metadata
  carried through `Settings.get_semantic_profiles_config(...)`
- **Interfaces consumed**: SEMCONTRACT fingerprint/readiness contract; existing
  `_expand_env_vars(...)`; existing profile YAML structure for `summarization`,
  `serving.vllm`, `vector_store`, and `auth`
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_semantic_profile_settings.py` so `oss_high`
    defaults resolve to `http://ai:8002/v1` plus `chat` for enrichment and
    `http://ai:8001/v1` plus `Qwen/Qwen3-Embedding-8B` for embeddings.
  - test: Add coverage proving legacy `VLLM_SUMMARIZATION_BASE_URL` and
    `VLLM_EMBEDDING_BASE_URL` still override the same surfaces when the new
    `SEMANTIC_ENRICHMENT_BASE_URL` / `SEMANTIC_EMBEDDING_BASE_URL` vars are
    unset, but the new vars win when both are present.
  - test: Add coverage proving the hydrated profile metadata preserves separate
    enrichment and embedding API-key env var names and does not silently fall
    back to the stale `win:8002` or Qwen Coder summarization defaults.
  - impl: Update `code-index-mcp.profiles.yaml` so `oss_high` becomes the
    roadmap's local profile source of truth: proxy/Gemma enrichment via
    `model: "chat"` at `http://ai:8002/v1`, Qwen embedding via
    `http://ai:8001/v1`, and no baked-in `win:8002` hostname.
  - impl: Keep the profile shape explicit: enrichment stays under
    `summarization`, embeddings stay under the profile provider/serving path,
    and API-key env vars remain config names rather than secret values.
  - impl: Add narrow alias-resolution helpers in `settings.py` so the runtime
    honors legacy `VLLM_*` base-url env vars as shims while making
    `SEMANTIC_ENRICHMENT_*` / `SEMANTIC_EMBEDDING_BASE_URL` the primary names.
  - impl: Expand hydrated profile metadata so downstream preflight and status
    code can tell enrichment endpoint/model/API-key-env apart from embedding
    endpoint/model/API-key-env without re-reading raw YAML.
  - impl: Do not add rebuild triggers, readiness classification changes, or
    query-routing changes here.
  - verify: `uv run pytest tests/test_semantic_profile_settings.py -q --no-cov`

### SL-1 - Default-Install OpenAI-Compatible Dependency Posture

- **Scope**: Close the default-install dependency gap for local
  OpenAI-compatible enrichment and embedding calls without widening the phase
  into a transport rewrite.
- **Owned files**: `pyproject.toml`, `uv.lock`, `mcp_server/utils/embedding_providers.py`, `tests/test_summarization.py`, `tests/test_semantic_indexer_registry.py`
- **Interfaces provided**: IF-0-SEMCONFIG-3; importable default-install
  OpenAI-compatible client path for `ChunkWriter` and
  `OpenAICompatibleEmbeddingProvider`
- **Interfaces consumed**: existing `openai` SDK call sites in
  `mcp_server/indexing/summarization.py` and
  `mcp_server/utils/embedding_providers.py`; SL-0 profile defaults for
  `oss_high`
- **Parallel-safe**: yes
- **Tasks**:
  - test: Add or extend lightweight regression coverage so the local
    OpenAI-compatible embedding path and summarization path remain importable
    and mockable after dependency changes.
  - test: Keep `tests/test_summarization.py` focused on summarizer config/model
    behavior, and use `tests/test_semantic_indexer_registry.py` as the
    regression harness for repo-scoped embedding provider creation.
  - impl: Promote `openai` from the optional `semantic` extra to the core
    dependency set in `pyproject.toml`, then refresh `uv.lock` to keep the
    locked install truthful.
  - impl: Update any remaining local-call remediation strings that still imply
    operators must install extra semantic deps just to reach an
    OpenAI-compatible endpoint from the default install.
  - impl: Keep the transport choice stable in this phase: do not replace the
    current SDK path with an `httpx` rewrite unless a narrower dependency-only
    fix proves impossible during execution.
  - impl: Avoid widening into provider-behavior changes for Voyage, reranking,
    or semantic query execution.
  - verify: `uv run pytest tests/test_summarization.py tests/test_semantic_indexer_registry.py -q --no-cov`
  - verify: `uv sync --locked`

### SL-2 - Preflight Redaction And Selected-Profile Surfacing

- **Scope**: Make semantic preflight use the selected profile's resolved local
  endpoints and expose redacted enrichment/embedding config details without
  leaking secret values.
- **Owned files**: `mcp_server/setup/semantic_preflight.py`, `tests/test_semantic_preflight.py`, `tests/test_setup_cli.py`
- **Interfaces provided**: IF-0-SEMCONFIG-2 runtime-reporting portion;
  IF-0-SEMCONFIG-4 preflight-reporting portion; `SemanticPreflightReport`
  `effective_config` fields that distinguish enrichment from embedding and show
  env-var names/presence only
- **Interfaces consumed**: SL-0 resolved enrichment and embedding metadata;
  SL-1 default-install local client posture; existing
  `run_semantic_preflight(...)`, `check_openai_compatible(...)`, and setup CLI
  JSON/text output
- **Parallel-safe**: no
- **Tasks**:
  - test: Extend `tests/test_semantic_preflight.py` so the selected profile's
    embedding endpoint is preferred over the global `settings.openai_api_base`
    fallback when profile metadata is present.
  - test: Add coverage proving preflight reports enrichment and embedding
    API-key env var names plus presence booleans, but never includes raw secret
    values in `details`, `effective_config`, or warnings.
  - test: Extend `tests/test_setup_cli.py` so `setup semantic --json` preserves
    the redacted config shape and strict-mode behavior with the new
    enrichment-versus-embedding fields.
  - impl: Reorder profile resolution in `run_semantic_preflight(...)` so the
    selected profile's resolved embedding base URL wins, with the global
    `OPENAI_API_BASE`/settings fallback used only when the profile truly omits
    one.
  - impl: Add redacted enrichment config to the report alongside embedding
    config: endpoint, model, API-key env var name, and env-var presence.
  - impl: Keep reporting metadata-only. Secret values, tokens, and API keys
    must never appear in preflight output, warnings, or CLI JSON.
  - impl: Keep Qdrant checks and semantic readiness gating behavior unchanged;
    this lane only fixes selected-profile config surfacing and redaction.
  - verify: `uv run pytest tests/test_semantic_preflight.py tests/test_setup_cli.py -q --no-cov`

### SL-3 - Docs And Contract Reducer

- **Scope**: Reduce the SEMCONFIG runtime contract into operator-facing docs and
  a docs-level guard without widening into later semantic pipeline behavior.
- **Owned files**: `docs/guides/semantic-onboarding.md`, `docs/tools/cli-setup-reference.md`, `tests/docs/test_semconfig_contract.py`
- **Interfaces provided**: IF-0-SEMCONFIG-4 docs surface; onboarding/setup
  language that names `SEMANTIC_ENRICHMENT_BASE_URL`,
  `SEMANTIC_ENRICHMENT_MODEL`, `SEMANTIC_EMBEDDING_BASE_URL`, and the legacy
  VLLM shim behavior
- **Interfaces consumed**: SL-0 resolved profile defaults and alias policy;
  SL-1 default-install dependency posture; SL-2 redacted preflight/effective
  config wording; roadmap SEMCONFIG exit criteria
- **Parallel-safe**: no
- **Tasks**:
  - test: Add a docs contract test that requires onboarding/setup docs to name
    the enrichment-versus-embedding split, the new default local endpoints, and
    the legacy `VLLM_*` compatibility-shim posture.
  - test: Require docs to avoid recommending the stale `win:8002` host or the
    Qwen Coder summarization model as the default `oss_high` configuration.
  - impl: Update `docs/guides/semantic-onboarding.md` so operators see the new
    local architecture clearly: proxy/Gemma enrichment at `ai:8002`, Qwen
    embeddings at `ai:8001`, profile-selected preflight, and redacted API-key
    env reporting.
  - impl: Update `docs/tools/cli-setup-reference.md` so `setup semantic`
    reflects profile-selected endpoint checks rather than a single generic
    `OPENAI_API_BASE` surface.
  - impl: Keep docs bounded to configuration and preflight behavior. Do not
    pull in later-phase claims about semantic rebuilds, vector invalidation, or
    ranking quality.
  - verify: `uv run pytest tests/docs/test_semconfig_contract.py -q --no-cov`
  - verify: `rg -n "SEMANTIC_ENRICHMENT_BASE_URL|SEMANTIC_ENRICHMENT_MODEL|SEMANTIC_EMBEDDING_BASE_URL|VLLM_SUMMARIZATION_BASE_URL|VLLM_EMBEDDING_BASE_URL|ai:8002|Qwen/Qwen3-Embedding-8B" docs/guides/semantic-onboarding.md docs/tools/cli-setup-reference.md tests/docs/test_semconfig_contract.py`

## Verification

Planning-only run: do not execute these during plan creation. Run them during
`codex-execute-phase` or manual SEMCONFIG execution.

Lane-specific checks:

```bash
uv run pytest tests/test_semantic_profile_settings.py -q --no-cov
uv run pytest tests/test_summarization.py tests/test_semantic_indexer_registry.py -q --no-cov
uv run pytest tests/test_semantic_preflight.py tests/test_setup_cli.py -q --no-cov
uv run pytest tests/docs/test_semconfig_contract.py -q --no-cov
uv sync --locked
rg -n "SEMANTIC_ENRICHMENT_BASE_URL|SEMANTIC_ENRICHMENT_MODEL|SEMANTIC_EMBEDDING_BASE_URL|VLLM_SUMMARIZATION_BASE_URL|VLLM_EMBEDDING_BASE_URL|win:8002|Qwen/Qwen2.5-Coder-14B-Instruct-AWQ|openai_api_base|api_key_env" \
  code-index-mcp.profiles.yaml \
  mcp_server/config/settings.py \
  mcp_server/utils/embedding_providers.py \
  mcp_server/setup/semantic_preflight.py \
  docs/guides/semantic-onboarding.md \
  docs/tools/cli-setup-reference.md \
  tests/test_semantic_profile_settings.py \
  tests/test_summarization.py \
  tests/test_semantic_preflight.py \
  tests/test_setup_cli.py \
  tests/test_semantic_indexer_registry.py \
  tests/docs/test_semconfig_contract.py
```

Whole-phase regression commands:

```bash
uv run pytest \
  tests/test_semantic_profile_settings.py \
  tests/test_summarization.py \
  tests/test_semantic_indexer_registry.py \
  tests/test_semantic_preflight.py \
  tests/test_setup_cli.py \
  tests/docs/test_semconfig_contract.py \
  -q --no-cov
git status --short -- specs/phase-plans-v7.md plans/phase-plan-v7-SEMCONFIG.md
```

## Acceptance Criteria

- [ ] `oss_high` defaults enrichment to
      `${SEMANTIC_ENRICHMENT_BASE_URL:http://ai:8002/v1}` with model
      `${SEMANTIC_ENRICHMENT_MODEL:chat}` and defaults embeddings to
      `${SEMANTIC_EMBEDDING_BASE_URL:http://ai:8001/v1}` with
      `Qwen/Qwen3-Embedding-8B`.
- [ ] Tests prove the default profile no longer points at `win:8002` or the
      Qwen Coder summarization model.
- [ ] Legacy `VLLM_SUMMARIZATION_BASE_URL` and `VLLM_EMBEDDING_BASE_URL`
      remain supported only as compatibility shims, with the new semantic env
      vars taking precedence when both are configured.
- [ ] Runtime settings and preflight surfaces expose separate enrichment and
      embedding endpoint/model/API-key-env metadata without logging secret
      values.
- [ ] `run_semantic_preflight(...)` uses the selected profile's resolved local
      endpoint data instead of collapsing everything onto one generic
      `OPENAI_API_BASE` value when profile metadata is present.
- [ ] The default `uv sync --locked` install includes the dependency posture
      needed for local OpenAI-compatible enrichment and embedding calls.
- [ ] Docs explain the local proxy/Gemma enrichment path, the Qwen embedding
      path, the selected-profile preflight behavior, and the VLLM compatibility
      shims.
- [ ] SEMCONFIG stays configuration-focused: no full reindex, no semantic
      ranking changes, and no cloud-worker chat forwarder work.

## Automation Handoff

```yaml
automation:
  status: planned
  next_skill: codex-execute-phase
  next_command: codex-execute-phase plans/phase-plan-v7-SEMCONFIG.md
  next_model_hint: execute
  next_effort_hint: medium
  human_required: false
  blocker_class: none
  blocker_summary: none
  required_human_inputs: []
  verification_status: not_run
  artifact: /home/viperjuice/code/Code-Index-MCP/plans/phase-plan-v7-SEMCONFIG.md
  artifact_state: staged
```
