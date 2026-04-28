# Phase roadmap v7

## Context

The v6 multi-repo hardening roadmap closed the durable-index and rollout
readiness track. A follow-up dogfood pass against this repository proved that
the lexical, symbol, chunk, and local readiness paths can be rebuilt cleanly,
but it also exposed a semantic-indexing contract gap.

The current implementation contains the intended hook for enriched embedding
text: `SemanticIndexer` reads `chunk_summaries.summary_text` and injects it
into the text sent to the vector embedder. The clean dogfood index, however,
has populated `code_chunks` with no `chunk_summaries`, and `semantic: true`
queries can fall back to lexical behavior without proving that summary-enriched
vectors exist.

The product technique is stricter than "embed code chunks": every semantic
vector should be based on a model-written semantic comment plus the chunk
context. Local compute is the default cost-control posture. The expected local
roles are:

- Enrichment/chat: OpenAI-compatible proxy at `http://ai:8002/v1`, model
  alias `chat`, backed by local Gemma while available and transparently falling
  back to OpenAI `gpt-5.4-mini` on eviction.
- Embedding/vectorization: OpenAI-compatible embedding endpoint at
  `http://ai:8001/v1`, model `Qwen/Qwen3-Embedding-8B`.
- Off-host tailnet access may use `https://ai.taile09692.ts.net`; direct
  cloud workers should not assume the chat upstream is reachable unless a queue
  forward is added.

## Architecture North Star

Semantic indexing must be fail-closed and evidence-backed:

```text
parse/chunk -> Gemma semantic summary -> Qwen embedding -> Qdrant vector -> semantic query
```

Lexical and symbol indexing may remain available when enrichment is down, but
semantic readiness must not be reported when summaries are missing, stale, or
not linked to the vectors. The local Gemma proxy should be the default
enrichment path, with fallback behavior owned by the proxy rather than by
repo-specific caller code.

## Assumptions

- `.mcp-index/current.db` remains the canonical local SQLite store.
- `code_chunks` remains the source of chunk identity and chunk content.
- `chunk_summaries.summary_text` is the canonical semantic comment attached to
  a chunk.
- `semantic_points` is the canonical SQLite linkage from chunks to vector
  point IDs.
- The `oss_high` profile remains the default open/local semantic profile.
- The Qwen embedding model returns 4096-dimensional vectors for the intended
  `oss_high` collection.
- The enrichment proxy accepts OpenAI-compatible chat completion requests at
  `/v1/chat/completions` with `model: "chat"` once correctly addressed.
- A working semantic build may use the proxy fallback to OpenAI, but should
  report which enrichment model/provider produced each summary.

## Non-Goals

- No new stable package release dispatch.
- No broad parser or plugin rewrite.
- No change to the multi-repo topology contract from v3/v6.
- No attempt to make off-tailnet cloud workers call the local chat proxy until
  a queue forward exists.
- No removal of lexical, symbol, or native-search fallback behavior for
  non-semantic readiness states.
- No hardcoded secret values or API keys.

## Cross-Cutting Principles

- Treat enrichment as a required semantic stage, not an optional background
  improvement.
- Prefer explicit readiness states over silent fallback.
- Keep local compute as the default and let the proxy own remote fallback.
- Keep profile fingerprints sensitive to enrichment model, prompt, embedding
  model, vector dimension, and Qdrant collection.
- Keep semantic artifacts reproducible: summaries and vectors should be
  invalidated when the chunk, prompt, enrichment model, or embedding profile
  changes.
- Preserve existing lexical/index durability behavior from v6.
- Add tests around failure modes found during dogfood, not only happy paths.

## Top Interface-Freeze Gates

- IF-0-SEMCONTRACT-1 — Semantic readiness contract: a semantic index is ready
  only when chunks, summaries, embedding vectors, and SQLite vector linkages
  are all present and profile-compatible.
- IF-0-SEMCONFIG-1 — Local semantic profile contract: enrichment and embedding
  are separately configured, with `oss_high` defaulting to `chat` at
  `http://ai:8002/v1` for enrichment and `Qwen/Qwen3-Embedding-8B` at
  `http://ai:8001/v1` for embeddings.
- IF-0-SEMPREFLIGHT-1 — Semantic preflight contract: enrichment chat,
  embedding dimension, Qdrant collection compatibility, API-key presence, and
  profile fingerprint are checked before semantic vector writes.
- IF-0-SEMPIPE-1 — Full semantic build contract: full sync generates missing
  summaries before embeddings and refuses semantic vector writes when
  enrichment is unavailable.
- IF-0-SEMINCR-1 — Incremental semantic mutation contract: changed chunks
  invalidate summaries and vectors, removed chunks delete stale vector
  linkages, and watcher updates call ctx-aware dispatcher mutations correctly.
- IF-0-SEMQUERY-1 — Semantic query contract: `semantic: true` uses the semantic
  index for ready repositories and returns a semantic-specific readiness error
  when enriched vectors are unavailable.
- IF-0-SEMDOGFOOD-1 — Dogfood evidence contract: a clean rebuild of this repo
  proves populated `chunk_summaries`, populated `semantic_points`, a compatible
  Qdrant collection, and useful natural-language semantic results.

## Phases

### Phase 1 — Semantic Readiness Contract (SEMCONTRACT)

**Objective**

Freeze the semantic readiness model so downstream code can distinguish lexical
readiness from enriched-vector readiness.

**Exit criteria**
- [ ] Semantic readiness states distinguish at least `ready`,
      `enrichment_unavailable`, `summaries_missing`, `vectors_missing`,
      `vector_dimension_mismatch`, `profile_mismatch`, and `semantic_stale`.
- [ ] Documentation states that lexical readiness does not imply semantic
      readiness.
- [ ] Profile fingerprints include enrichment model, enrichment base URL
      identity, prompt template hash, embedding model, vector dimension, and
      Qdrant collection.
- [ ] Tests prove semantic readiness is not ready when `chunk_summaries` is
      empty for an otherwise ready lexical index.
- [ ] Existing `index_unavailable` and native-search fallback semantics remain
      unchanged for non-semantic query failures.

**Scope notes**

This phase should primarily define contracts, status states, docs, and tests.
It should not yet rewire the indexing pipeline.

**Non-goals**

- No vector rebuild.
- No endpoint mutation.
- No release workflow changes.

**Key files**

- `mcp_server/health/repository_readiness.py`
- `mcp_server/artifacts/semantic_profiles.py`
- `mcp_server/artifacts/semantic_namespace.py`
- `mcp_server/storage/sqlite_store.py`
- `mcp_server/cli/tool_handlers.py`
- `docs/guides/semantic-onboarding.md`
- `docs/SUPPORT_MATRIX.md`
- `tests/test_repository_readiness.py`
- `tests/test_semantic_profiles.py`
- `tests/test_artifact_integrity_gate.py`

**Depends on**
- (none)

**Produces**
- IF-0-SEMCONTRACT-1 — Semantic readiness contract.

### Phase 2 — Local Enrichment and Embedding Configuration (SEMCONFIG)

**Objective**

Make the default `oss_high` profile match the intended local architecture:
Gemma/proxy enrichment first, Qwen embedding second, and no optional dependency
gap for OpenAI-compatible local calls.

**Exit criteria**
- [ ] `oss_high` summarization defaults to
      `${SEMANTIC_ENRICHMENT_BASE_URL:http://ai:8002/v1}` and
      `${SEMANTIC_ENRICHMENT_MODEL:chat}`.
- [ ] `oss_high` embedding defaults to
      `${SEMANTIC_EMBEDDING_BASE_URL:http://ai:8001/v1}` and
      `Qwen/Qwen3-Embedding-8B`.
- [ ] Legacy `VLLM_SUMMARIZATION_BASE_URL` and `VLLM_EMBEDDING_BASE_URL`
      remain accepted aliases or are documented as compatibility shims.
- [ ] OpenAI-compatible local inference works in the default install, either
      by moving `openai` to core dependencies or by replacing SDK calls with
      `httpx`.
- [ ] Runtime config can express API-key env vars without logging secret
      values.
- [ ] Tests assert the default profile does not point at `win:8002` or a Qwen
      Coder summarization model.

**Scope notes**

This phase owns configuration shape, dependency posture, settings parsing, and
documentation. It should keep the proxy as the fallback abstraction; caller
code should send `model: "chat"` and not implement its own OpenAI fallback.

**Non-goals**

- No full reindex.
- No semantic query ranking changes.
- No cloud-worker chat forwarder.

**Key files**

- `code-index-mcp.profiles.yaml`
- `mcp_server/config/settings.py`
- `mcp_server/indexing/summarization.py`
- `mcp_server/setup/semantic_preflight.py`
- `pyproject.toml`
- `uv.lock`
- `docs/guides/semantic-onboarding.md`
- `tests/test_semantic_profile_settings.py`
- `tests/test_summarization.py`
- `tests/test_semantic_preflight.py`

**Depends on**
- SEMCONTRACT

**Produces**
- IF-0-SEMCONFIG-1 — Local semantic profile contract.

### Phase 3 — Semantic Preflight and Fail-Closed Gates (SEMPREFLIGHT)

**Objective**

Add operator and runtime checks that prevent semantic vector writes unless the
enrichment, embedding, and Qdrant surfaces are compatible.

**Exit criteria**
- [ ] Preflight sends a redacted OpenAI-compatible chat smoke to the enrichment
      endpoint using `model: "chat"`.
- [ ] Preflight sends an embedding smoke to the Qwen endpoint and validates
      vector dimension against the profile.
- [ ] Qdrant collection checks verify collection existence, vector size,
      distance, and profile namespace.
- [ ] Preflight reports API-key env var presence without printing secret
      values.
- [ ] Semantic preflight can return a structured blocker before vector writes.
- [ ] Tests cover unreachable enrichment proxy, wrong chat model, embedding
      dimension mismatch, missing collection, and missing API key env var.

**Scope notes**

This phase should integrate with existing `mcp-index index check-semantic` and
repository readiness surfaces without running a full index.

**Non-goals**

- No summary generation.
- No vector writes.
- No external credential creation.

**Key files**

- `mcp_server/setup/semantic_preflight.py`
- `mcp_server/cli/index_management.py`
- `mcp_server/cli/repository_commands.py`
- `mcp_server/health/repository_readiness.py`
- `mcp_server/artifacts/semantic_namespace.py`
- `tests/test_semantic_preflight.py`
- `tests/test_repository_commands.py`

**Depends on**
- SEMCONFIG

**Produces**
- IF-0-SEMPREFLIGHT-1 — Semantic preflight contract.

### Phase 4 — Enrichment-First Full Semantic Pipeline (SEMPIPE)

**Objective**

Wire full repository sync so summaries are generated before semantic vectors
and semantic vector writes are refused when summaries cannot be produced.

**Exit criteria**
- [ ] Full semantic sync groups chunks by file and runs the configured
      enrichment writer before embedding.
- [ ] `chunk_summaries` is populated before Qwen embedding starts.
- [ ] Semantic embedding input includes `summary_text` plus bounded chunk
      context.
- [ ] If enrichment fails, lexical/chunk indexing may complete but semantic
      readiness is not ready and semantic vectors are not advanced.
- [ ] `semantic_points` is populated for written vectors.
- [ ] Summary rows record model/provider metadata sufficient for audit and
      invalidation.
- [ ] Tests prove no Qdrant upsert happens when summaries are missing in
      default semantic mode.

**Scope notes**

This phase owns the full build path. It may reuse `ComprehensiveChunkWriter`
and `FileBatchSummarizer`, but the full sync path must make them mandatory for
semantic mode rather than relying on lazy search-triggered summaries.

**Non-goals**

- No query ranking changes.
- No watcher/incremental semantics beyond shared helper extraction.
- No release dispatch.

**Key files**

- `mcp_server/storage/git_index_manager.py`
- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/indexing/summarization.py`
- `mcp_server/utils/semantic_indexer.py`
- `mcp_server/storage/sqlite_store.py`
- `mcp_server/cli/tool_handlers.py`
- `tests/test_git_index_manager.py`
- `tests/test_dispatcher.py`
- `tests/test_summarization.py`
- `tests/test_profile_aware_semantic_indexer.py`

**Depends on**
- SEMPREFLIGHT

**Produces**
- IF-0-SEMPIPE-1 — Full semantic build contract.

### Phase 5 — Incremental Semantic Invalidation and Watcher Repair (SEMINCR)

**Objective**

Make changed, moved, deleted, and watched files preserve the enrichment-first
semantic contract without stale summaries or stale vectors.

**Exit criteria**
- [ ] Changed chunks invalidate old summaries when chunk content, prompt hash,
      enrichment model, or profile fingerprint changes.
- [ ] Changed chunks regenerate summaries before re-embedding.
- [ ] Deleted chunks remove `chunk_summaries`, `semantic_points`, and Qdrant
      points where applicable.
- [ ] Move/rename behavior preserves or invalidates summaries according to
      content hash and profile fingerprint.
- [ ] File watcher reindex/remove calls use the ctx-aware dispatcher signature
      and no longer raise `EnhancedDispatcher.remove_file()` argument errors.
- [ ] Tests cover add, modify, delete, rename, prompt-change invalidation, and
      watcher-triggered remove/reindex.

**Scope notes**

This phase should reuse the full-pipeline helper from SEMPIPE so incremental
and full indexing do not drift.

**Non-goals**

- No branch topology expansion.
- No new watcher backend.
- No semantic ranking changes.

**Key files**

- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/watcher/file_watcher.py`
- `mcp_server/watcher_multi_repo.py`
- `mcp_server/storage/git_index_manager.py`
- `mcp_server/storage/sqlite_store.py`
- `mcp_server/utils/semantic_indexer.py`
- `tests/test_watcher.py`
- `tests/test_watcher_multi_repo.py`
- `tests/test_semantic_stale_vector_cleanup.py`
- `tests/test_incremental_indexer.py`

**Depends on**
- SEMPIPE

**Produces**
- IF-0-SEMINCR-1 — Incremental semantic mutation contract.

### Phase 6 — Semantic Query Routing and Result Quality (SEMQUERY)

**Objective**

Ensure `semantic: true` actually uses enriched semantic vectors for ready
repositories and reports an explicit semantic readiness refusal otherwise.

**Exit criteria**
- [ ] Registered repository semantic queries use the profile-specific Qdrant
      collection when semantic readiness is ready.
- [ ] `semantic: true` does not silently return lexical results when semantic
      readiness is unavailable.
- [ ] Response metadata indicates semantic source, profile, collection, and
      fallback/refusal status.
- [ ] Symbol and lexical query behavior remains unchanged for
      `semantic: false`.
- [ ] Ranking avoids phase-plan/document mentions outranking code definitions
      for definition-like symbol queries.
- [ ] Tests cover semantic ready, summaries missing, vectors missing, wrong
      collection dimension, and explicit lexical fallback requests.

**Scope notes**

This phase owns query routing and result metadata. It should not rebuild the
index except in tests.

**Non-goals**

- No new embedding model.
- No broad reranker rollout.
- No user-facing UI.

**Key files**

- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/cli/tool_handlers.py`
- `mcp_server/utils/semantic_indexer.py`
- `mcp_server/health/repository_readiness.py`
- `tests/test_tool_handlers_readiness.py`
- `tests/test_dispatcher.py`
- `tests/real_world/test_semantic_search.py`
- `tests/test_benchmark_query_regressions.py`

**Depends on**
- SEMINCR

**Produces**
- IF-0-SEMQUERY-1 — Semantic query contract.

### Phase 7 — Clean Semantic Dogfood Rebuild (SEMDOGFOOD)

**Objective**

Rebuild this repository from scratch and prove the full enrichment-first
semantic index works end to end with local compute defaults.

**Exit criteria**
- [ ] Stale repo-local semantic artifacts are cleared without deleting shared
      live Qdrant service data unexpectedly.
- [ ] Full sync records timing, max RSS, index size, summary count, vector
      count, and Qdrant collection metadata.
- [ ] `chunk_summaries` is populated for the rebuilt repo.
- [ ] `semantic_points` is populated and points resolve to the
      `code_index__oss_high__v1` collection.
- [ ] Natural-language semantic queries use the semantic path and return
      relevant code results.
- [ ] Lexical, symbol, fuzzy, and semantic queries are compared in a short
      dogfood report.
- [ ] Final readiness reports lexical ready and semantic ready separately.
- [ ] The report states whether this repo is ready to dogfood Code-Index-MCP
      against multiple local repos using the local Qwen/Gemma setup.

**Scope notes**

This phase is evidence-heavy. It should run real commands, collect metrics, and
write a status report, but it should not introduce new architecture unless an
acceptance blocker is discovered.

**Non-goals**

- No package release dispatch.
- No direct `main` push bypassing branch protection.
- No deletion of shared Qdrant collections unless the operator explicitly asks.

**Key files**

- `docs/status/`
- `docs/guides/semantic-onboarding.md`
- `mcp_server/cli/`
- `mcp_server/setup/semantic_preflight.py`
- `tests/real_world/test_semantic_search.py`
- `.mcp-index/current.db` (generated, not tracked)

**Depends on**
- SEMQUERY

**Produces**
- IF-0-SEMDOGFOOD-1 — Dogfood evidence contract.

## Phase Dependency DAG

```text
SEMCONTRACT
  -> SEMCONFIG
  -> SEMPREFLIGHT
  -> SEMPIPE
  -> SEMINCR
  -> SEMQUERY
  -> SEMDOGFOOD
```

## Execution Notes

- SEMCONTRACT should be planned first because it freezes the semantic readiness
  states used by every later phase.
- SEMCONFIG can start immediately after SEMCONTRACT and should stay narrowly
  scoped to settings, profile defaults, dependency posture, and docs.
- SEMPREFLIGHT should not execute before SEMCONFIG, because it depends on the
  final names of enrichment and embedding configuration knobs.
- SEMPIPE is the first phase that may run real enrichment and vector-write
  paths.
- SEMINCR should reuse SEMPIPE helpers instead of creating a parallel
  incremental-only enrichment implementation.
- SEMQUERY should wait for the index mutation paths to produce trustworthy
  semantic artifacts.
- SEMDOGFOOD should be the only phase that performs the full clean rebuild and
  broad natural-language result-quality check.

## Verification

```bash
# SEMCONTRACT
uv run pytest tests/test_repository_readiness.py tests/test_semantic_profiles.py tests/test_artifact_integrity_gate.py -q --no-cov

# SEMCONFIG
uv run pytest tests/test_semantic_profile_settings.py tests/test_summarization.py tests/test_semantic_preflight.py -q --no-cov

# SEMPREFLIGHT
uv run pytest tests/test_semantic_preflight.py tests/test_repository_commands.py -q --no-cov
uv run mcp-index index check-semantic

# SEMPIPE
uv run pytest tests/test_git_index_manager.py tests/test_dispatcher.py tests/test_summarization.py tests/test_profile_aware_semantic_indexer.py -q --no-cov

# SEMINCR
uv run pytest tests/test_watcher.py tests/test_watcher_multi_repo.py tests/test_semantic_stale_vector_cleanup.py tests/test_incremental_indexer.py -q --no-cov

# SEMQUERY
uv run pytest tests/test_tool_handlers_readiness.py tests/test_dispatcher.py tests/real_world/test_semantic_search.py tests/test_benchmark_query_regressions.py -q --no-cov

# SEMDOGFOOD
uv run mcp-index repository sync --force-full
uv run mcp-index repository status
uv run mcp-index preflight
sqlite3 .mcp-index/current.db 'select count(*) from chunk_summaries; select count(*) from semantic_points;'
```
