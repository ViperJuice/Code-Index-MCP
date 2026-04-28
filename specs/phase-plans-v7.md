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

### Phase 8 — Default Enrichment Compatibility Recovery (SEMREADYFIX)

**Objective**

Repair the default `oss_high` enrichment compatibility path exposed by
SEMDOGFOOD so a clean rebuild can actually generate summaries and vectors with
the intended local-default setup, then rerun the semantic dogfood proof.

**Exit criteria**
- [ ] The default `oss_high` enrichment model and endpoint metadata match a
      chat model that the configured local enrichment service actually serves.
- [ ] Active-profile semantic preflight no longer fails with
      `wrong_chat_model` for the default local dogfood configuration.
- [ ] A clean force-full rebuild of this repository produces non-zero
      `chunk_summaries` and non-zero `semantic_points` for `oss_high`.
- [ ] The repo-local dogfood semantic query harness returns semantic-path
      results for the fixed natural-language prompts instead of
      `semantic_not_ready`.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is refreshed or superseded by a
      post-repair report that records the semantic-ready verdict.

**Scope notes**

This phase is a blocker-repair follow-up for the exact default-profile issue
found in SEMDOGFOOD. It should stay on enrichment profile compatibility,
preflight, rebuild validation, and refreshed dogfood evidence.

**Non-goals**

- No semantic ranking redesign.
- No unrelated artifact rollout changes.
- No new cloud-only fallback path outside the existing local/proxy posture.

**Key files**

- `code-index-mcp.profiles.yaml`
- `mcp_server/config/settings.py`
- `mcp_server/setup/semantic_preflight.py`
- `mcp_server/indexing/summarization.py`
- `docs/guides/semantic-onboarding.md`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `tests/test_semantic_profile_settings.py`
- `tests/test_semantic_preflight.py`
- `tests/real_world/test_semantic_search.py`

**Depends on**
- SEMDOGFOOD

**Produces**
- IF-0-SEMREADYFIX-1 — Default local semantic dogfood recovery contract.

### Phase 9 — Collection Bootstrap and Semantic Stage Recovery (SEMCOLLECT)

**Objective**

Repair the remaining semantic-write bootstrap gap exposed by SEMREADYFIX so a
clean rebuild can actually persist summaries, provision or hydrate the active
Qdrant collection, and advance vectors for `oss_high`.

**Exit criteria**
- [ ] A clean force-full rebuild no longer stops with active-profile preflight
      blocker `collection_missing` for the default local `oss_high` path.
- [ ] `chunk_summaries` becomes non-zero after the rebuild and remains tied to
      the repaired effective enrichment-model audit metadata.
- [ ] `semantic_points` becomes non-zero and links to
      `code_index__oss_high__v1`.
- [ ] Semantic dogfood queries for the fixed prompts return semantic-path code
      results instead of `semantic_not_ready`.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is refreshed again with the
      semantic-ready or exact still-blocked verdict after collection recovery.

**Scope notes**

This phase exists because SEMREADYFIX repaired enrichment compatibility but the
full rebuild still stalled on collection bootstrap and produced zero summaries
and zero vectors. Keep the work narrowly on collection provisioning/hydration
and the strict semantic stage that depends on it.

**Non-goals**

- No semantic ranking redesign.
- No multi-repo rollout expansion.
- No unrelated inference-provider changes beyond the repaired `oss_high`
  default path.

**Key files**

- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/utils/semantic_indexer.py`
- `mcp_server/setup/semantic_preflight.py`
- `mcp_server/cli/setup_commands.py`
- `mcp_server/cli/repository_commands.py`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `docs/guides/semantic-onboarding.md`
- `tests/real_world/test_semantic_search.py`
- `tests/test_repository_commands.py`
- `tests/test_profile_aware_semantic_indexer.py`

**Depends on**
- SEMREADYFIX

**Produces**
- IF-0-SEMCOLLECT-1 — Default local semantic collection bootstrap and semantic-stage recovery contract.

### Phase 10 — Summary Runtime Recovery (SEMSUMFIX)

**Objective**

Repair the newly exposed summary-generation runtime blocker now that
SEMCOLLECT has restored active-profile collection bootstrap and semantic
preflight readiness for `oss_high`.

**Exit criteria**
- [ ] A direct authoritative summary write probe no longer fails on the current
      BAML generator/runtime mismatch, or the summary path is intentionally
      rerouted through a supported local provider path with equivalent audit
      metadata.
- [ ] A clean force-full rebuild produces non-zero `chunk_summaries` for the
      default local `oss_high` path.
- [ ] The same rebuild produces non-zero `semantic_points` linked to
      `code_index__oss_high__v1`.
- [ ] Semantic dogfood queries for the fixed prompts return semantic-path code
      results instead of `semantic_not_ready`.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is refreshed with the repaired
      summary-runtime outcome and final semantic-ready verdict.

**Scope notes**

This phase exists only because SEMCOLLECT cleared the active collection gate,
but the repo-local rebuild still produced zero summaries and zero vectors due
to summary-runtime failure. Keep the work narrowly on the authoritative summary
runtime and the semantic write path it unlocks.

**Non-goals**

- No semantic ranking redesign.
- No multi-repo rollout expansion.
- No unrelated collection-namespace changes after SEMCOLLECT.

**Key files**

- `mcp_server/indexing/summarization.py`
- `mcp_server/config/settings.py`
- `pyproject.toml`
- `uv.lock`
- `docs/guides/semantic-onboarding.md`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `tests/test_summarization.py`
- `tests/real_world/test_semantic_search.py`
- `tests/docs/test_semdogfood_evidence_contract.py`

**Depends on**
- SEMCOLLECT

**Produces**
- IF-0-SEMSUMFIX-1 — Default local summary-runtime and semantic-write recovery contract.

### Phase 11 — Full Sync Summary Coverage Recovery (SEMSYNCFIX)

**Objective**

Repair the remaining full-sync semantic-stage blocker exposed by SEMSUMFIX so a
clean `repository sync --force-full` drains repo-wide authoritative summaries
and can advance vector writes for the active `oss_high` profile.

**Exit criteria**
- [ ] A clean force-full rebuild writes authoritative summaries beyond the
      direct probe subset and increases `chunk_summaries` from the current
      manual-probe-only baseline.
- [ ] The same rebuild produces non-zero `semantic_points` linked to
      `code_index__oss_high__v1`.
- [ ] `uv run mcp-index repository status` reports semantic readiness `ready`
      for the active profile after the rebuild.
- [ ] Semantic dogfood queries for the fixed prompts return semantic-path code
      results instead of `semantic_not_ready`.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is refreshed with the repaired
      full-sync/write-path outcome and final semantic-ready verdict.

**Scope notes**

This phase exists only because SEMSUMFIX proved the direct authoritative
summary runtime can recover from the BAML client/runtime mismatch, but the real
`repository sync --force-full` path still leaves the repo at
`summaries_missing` with only probe-written summary rows. Keep the work
narrowly on full-sync summary coverage, summary-stage scoping, and the strict
semantic readiness accounting that gates vector writes.

**Non-goals**

- No semantic ranking redesign.
- No multi-repo rollout expansion.
- No unrelated profile/configuration changes unless they are required to make
  the repaired summary path execute during full sync.

**Key files**

- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/storage/git_index_manager.py`
- `mcp_server/indexing/summarization.py`
- `docs/guides/semantic-onboarding.md`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `tests/real_world/test_semantic_search.py`
- `tests/docs/test_semdogfood_evidence_contract.py`

**Depends on**
- SEMSUMFIX

**Produces**
- IF-0-SEMSYNCFIX-1 — Default local full-sync summary coverage and semantic-ready rebuild contract.

### Phase 12 — Summary Throughput Recovery (SEMTHROUGHPUT)

**Objective**

Repair the remaining summary-throughput bottleneck exposed by SEMSYNCFIX so the
real `repository sync --force-full` path can finish repo-wide authoritative
summary generation within one rebuild and finally advance semantic vector
writes.

**Exit criteria**
- [ ] The full-sync summary path no longer stalls on large markdown/plaintext
      files after the BAML runtime mismatch fallback is triggered.
- [ ] A clean force-full rebuild clears the repo-wide `summaries_missing`
      blocker and produces non-zero `semantic_points` for
      `code_index__oss_high__v1`.
- [ ] `uv run mcp-index repository status` reports semantic readiness `ready`
      for the active profile after the repaired rebuild.
- [ ] Repo-local semantic dogfood queries return semantic-path results instead
      of `semantic_not_ready`.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the throughput repair
      evidence and final semantic-ready or exact still-blocked verdict.

**Scope notes**

This phase exists only because SEMSYNCFIX repaired the scoped full-sync summary
selection and strict stage retry contract, but the live dogfood rebuild still
left semantic readiness at `summaries_missing` after summary coverage advanced
only partway through large documentation/spec files. Keep the work narrowly on
summary batching/recovery throughput and the proof needed to show the same
force-full rebuild now clears the summary gate.

**Non-goals**

- No semantic ranking redesign.
- No multi-repo rollout expansion.
- No unrelated profile/configuration changes outside the summary throughput
  recovery path.

**Key files**

- `mcp_server/indexing/summarization.py`
- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `docs/guides/semantic-onboarding.md`
- `tests/test_summarization.py`
- `tests/test_dispatcher.py`
- `tests/docs/test_semdogfood_evidence_contract.py`
- `tests/real_world/test_semantic_search.py`

**Depends on**
- SEMSYNCFIX

**Produces**
- IF-0-SEMTHROUGHPUT-1 — Default local full-sync summary throughput and semantic-ready rebuild contract.

### Phase 13 — Force-Full Semantic Stall Recovery (SEMSTALLFIX)

**Objective**

Repair the remaining force-full rebuild stall exposed by SEMTHROUGHPUT so one
clean `repository sync --force-full` run can finish on the current commit,
refresh the registered index, and either reach semantic readiness `ready` or
emit an exact post-summary blocker without hanging mid-run.

**Exit criteria**
- [ ] The default force-full rebuild no longer plateaus for long periods after
      summary counts stop moving on the large markdown/plaintext backlog.
- [ ] A clean force-full rebuild updates the indexed commit to the current
      commit instead of leaving repository readiness at `stale_commit`.
- [ ] The rebuild either produces non-zero `semantic_points` with semantic
      readiness `ready`, or it fails closed with an exact post-summary blocker
      that is narrower than summary-throughput recovery.
- [ ] Repo-local semantic dogfood queries either return semantic-path results
      or surface the exact new blocker contract without ambiguous failures.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the stall evidence,
      remediation, and final ready or still-blocked verdict.

**Scope notes**

This phase exists only if SEMTHROUGHPUT improves oversized-file summary
recovery but the live force-full rebuild still does not complete cleanly on
the active commit. Keep the work narrowly on force-full completion, commit
freshness, and post-summary semantic-stage handoff.

**Non-goals**

- No semantic ranking redesign.
- No multi-repo rollout expansion.
- No unrelated profile/configuration changes outside the stuck force-full path.

**Key files**

- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/storage/git_index_manager.py`
- `mcp_server/indexing/summarization.py`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `docs/guides/semantic-onboarding.md`
- `tests/test_dispatcher.py`
- `tests/test_git_index_manager.py`
- `tests/real_world/test_semantic_search.py`

**Depends on**
- SEMTHROUGHPUT

**Produces**
- IF-0-SEMSTALLFIX-1 — Force-full rebuild completion and indexed-commit freshness contract.

### Phase 14 — Low-Level Force-Full Stall Forensics (SEMIOWAIT)

**Objective**

Investigate and repair the remaining repo-local force-full stall that persists
after SEMSTALLFIX’s dispatcher/git-index-manager bounds, so a clean
`repository sync --force-full` run cannot remain stuck below the semantic-stage
accounting path without surfacing a precise lexical/storage/runtime blocker.

**Exit criteria**
- [ ] A repo-local force-full rebuild either completes through lexical,
      summary, and semantic closeout, or exits fail-closed with an exact
      blocker narrower than SEMSTALLFIX’s dispatcher-stage contracts.
- [ ] The live rebuild no longer remains stuck for minutes with unchanged
      `chunk_summaries` / `semantic_points` counts while `mcp-index repository sync`
      stays active.
- [ ] If the residual stall is in SQLite, WAL/checkpoint, file-read, or other
      lexical/storage work below dispatcher stage accounting, that layer now
      exposes bounded diagnostics and a deterministic exit path.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the SEMSTALLFIX repair,
      the residual low-level stall evidence, and the final ready or still-blocked
      verdict after SEMIOWAIT.

**Scope notes**

This phase exists only if SEMSTALLFIX repairs semantic-stage accounting and
force-full closeout semantics in tests, but the real repo-local rebuild still
hangs below that layer during lexical/storage/runtime work. Keep the work
narrowly on the live force-full execution path, storage/runtime forensics, and
bounded blocker surfacing.

**Non-goals**

- No semantic ranking redesign.
- No multi-repo rollout expansion.
- No unrelated profile/configuration changes outside the live force-full stall path.

**Key files**

- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/storage/git_index_manager.py`
- `mcp_server/storage/sqlite_store.py`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `docs/guides/semantic-onboarding.md`
- `tests/test_dispatcher.py`
- `tests/test_git_index_manager.py`
- `tests/docs/test_semdogfood_evidence_contract.py`

**Depends on**
- SEMSTALLFIX

**Produces**
- IF-0-SEMIOWAIT-1 — Low-level force-full stall diagnostics and bounded exit contract.

### Phase 15 — Changelog Lexical Timeout Repair (SEMCHANGELOG)

**Objective**

Repair the now-exact repo-local force-full blocker where lexical indexing times
out while processing `CHANGELOG.md`, so the dogfood rebuild can move past the
low-level lexical path and either reach semantic closeout or surface the next
bounded downstream blocker.

**Exit criteria**
- [ ] `CHANGELOG.md` no longer exceeds the lexical timeout during
      `repository sync --force-full`.
- [ ] The lexical timeout watchdog remains active and still fails closed for
      true path-level stalls.
- [ ] The live force-full rerun either completes through indexed-commit
      freshness or exits with a new exact blocker that is narrower than
      `CHANGELOG.md` lexical processing.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the changelog repair,
      the rerun outcome, current-versus-indexed commit evidence, and the final
      ready or still-blocked verdict.

**Scope notes**

Keep this phase narrowly focused on why `CHANGELOG.md` is slow enough to trip
the lexical watchdog during the live full rebuild. Prefer bounded parsing,
chunking, or exclusion-policy fixes over weakening the timeout globally.

**Non-goals**

- No semantic ranking redesign.
- No broad document-processing rewrite.
- No global timeout increase that hides path-level stalls.
- No unrelated cleanup of dogfood runtime artifacts.

**Key files**

- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/storage/git_index_manager.py`
- `mcp_server/plugin_system/`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `docs/guides/semantic-onboarding.md`
- `tests/test_dispatcher.py`
- `tests/test_git_index_manager.py`
- `tests/docs/test_semdogfood_evidence_contract.py`

**Depends on**
- SEMIOWAIT

**Produces**
- IF-0-SEMCHANGELOG-1 — Changelog lexical timeout repair and rerun evidence contract.

### Phase 16 — Roadmap Lexical Timeout Repair (SEMROADMAP)

**Objective**

Repair the next exact repo-local force-full blocker where lexical indexing now
times out while processing `ROADMAP.md`, so the dogfood rebuild can move past
that large Markdown document and either reach semantic closeout or surface the
next bounded downstream blocker.

**Exit criteria**
- [ ] `ROADMAP.md` no longer exceeds the lexical timeout during
      `repository sync --force-full`.
- [ ] The lexical timeout watchdog remains active and still fails closed for
      true path-level stalls.
- [ ] The live force-full rerun either completes through indexed-commit
      freshness or exits with a new exact blocker that is narrower than
      `ROADMAP.md` lexical processing.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the roadmap repair,
      the rerun outcome, current-versus-indexed commit evidence, and the final
      ready or still-blocked verdict.

**Scope notes**

Keep this phase narrowly focused on why `ROADMAP.md` is now slow enough to trip
the lexical watchdog after SEMCHANGELOG cleared `CHANGELOG.md`. Prefer bounded
parsing, chunking, or exclusion-policy fixes over weakening the timeout
globally.

**Non-goals**

- No semantic ranking redesign.
- No broad document-processing rewrite.
- No global timeout increase that hides path-level stalls.
- No unrelated cleanup of dogfood runtime artifacts.

**Key files**

- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/storage/git_index_manager.py`
- `mcp_server/plugin_system/`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `docs/guides/semantic-onboarding.md`
- `tests/test_dispatcher.py`
- `tests/test_git_index_manager.py`
- `tests/docs/test_semdogfood_evidence_contract.py`

**Depends on**
- SEMCHANGELOG

**Produces**
- IF-0-SEMROADMAP-1 — Roadmap lexical timeout repair and rerun evidence contract.

### Phase 17 — Final Analysis Lexical Timeout Repair (SEMANALYSIS)

**Objective**

Repair the next exact repo-local force-full blocker where lexical indexing now
times out while processing `FINAL_COMPREHENSIVE_MCP_ANALYSIS.md`, so the
dogfood rebuild can move past that bounded Markdown document and either reach
semantic closeout or surface the next narrower downstream blocker.

**Exit criteria**
- [ ] `FINAL_COMPREHENSIVE_MCP_ANALYSIS.md` no longer exceeds the lexical
      timeout during `repository sync --force-full`.
- [ ] The lexical timeout watchdog remains active and still fails closed for
      true path-level stalls.
- [ ] The live force-full rerun either completes through indexed-commit
      freshness or exits with a new exact blocker that is narrower than
      `FINAL_COMPREHENSIVE_MCP_ANALYSIS.md` lexical processing.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the final-analysis
      repair, the rerun outcome, current-versus-indexed commit evidence, and
      the final ready or still-blocked verdict.

**Scope notes**

Keep this phase narrowly focused on why
`FINAL_COMPREHENSIVE_MCP_ANALYSIS.md` is now slow enough to trip the lexical
watchdog after SEMROADMAP cleared `ROADMAP.md`. Prefer bounded parsing,
chunking, or exclusion-policy fixes over weakening the timeout globally.

**Non-goals**

- No semantic ranking redesign.
- No broad document-processing rewrite.
- No global timeout increase that hides path-level stalls.
- No unrelated cleanup of dogfood runtime artifacts.

**Key files**

- `mcp_server/plugins/markdown_plugin/plugin.py`
- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/storage/git_index_manager.py`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `docs/guides/semantic-onboarding.md`
- `tests/test_dispatcher.py`
- `tests/test_git_index_manager.py`
- `tests/docs/test_semdogfood_evidence_contract.py`

**Depends on**
- SEMROADMAP

**Produces**
- IF-0-SEMANALYSIS-1 — Final-analysis lexical timeout repair and rerun evidence contract.

## Phase Dependency DAG

```text
SEMCONTRACT
  -> SEMCONFIG
  -> SEMPREFLIGHT
  -> SEMPIPE
  -> SEMINCR
  -> SEMQUERY
  -> SEMDOGFOOD
  -> SEMREADYFIX
  -> SEMCOLLECT
  -> SEMSUMFIX
  -> SEMSYNCFIX
  -> SEMTHROUGHPUT
  -> SEMSTALLFIX
  -> SEMIOWAIT
  -> SEMCHANGELOG
  -> SEMROADMAP
  -> SEMANALYSIS
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
- SEMREADYFIX exists only if SEMDOGFOOD proves the default local dogfood path
  is still blocked; it should repair that blocker and then rerun the dogfood
  proof instead of widening into unrelated semantic work.
- SEMCOLLECT exists only if SEMREADYFIX proves enrichment compatibility is
  repaired but semantic writes still cannot advance because the active
  collection/bootstrap path is missing or disconnected from the rebuild.
- SEMSUMFIX exists only if SEMCOLLECT proves the active collection gate is
  repaired but authoritative summary generation still cannot run for the live
  rebuild.
- SEMSYNCFIX exists only if SEMSUMFIX proves the direct authoritative summary
  runtime is repaired but the real full-sync path or readiness accounting still
  leaves the repo at `summaries_missing`.
- SEMTHROUGHPUT exists only if SEMSYNCFIX proves the scoped full-sync summary
  drain is repaired but the live rebuild still cannot clear repo-wide summary
  coverage fast enough to reach semantic vector writes in one force-full pass.
- SEMSTALLFIX exists only if SEMTHROUGHPUT improves large-file summary
  recovery but the live force-full rebuild still does not complete cleanly on
  the active commit or still cannot hand off from summary completion into
  semantic vector writes.
- SEMIOWAIT exists only if SEMSTALLFIX tightens dispatcher-stage and closeout
  contracts in tests, but the real repo-local force-full rebuild still hangs
  below that layer without surfacing a precise blocker.
- SEMCHANGELOG exists only if SEMIOWAIT narrows the opaque low-level stall to a
  deterministic `CHANGELOG.md` lexical timeout; it should repair that exact file
  path or preserve a narrower downstream blocker.
- SEMROADMAP exists only if SEMCHANGELOG clears `CHANGELOG.md` but the live
  force-full rerun still times out on another bounded Markdown document such
  as `ROADMAP.md`; it should repair that exact file path or preserve a still
  narrower downstream blocker.
- SEMANALYSIS exists only if SEMROADMAP clears `ROADMAP.md` but the live
  force-full rerun still times out on another bounded Markdown document such
  as `FINAL_COMPREHENSIVE_MCP_ANALYSIS.md`; it should repair that exact file
  path or preserve a still narrower downstream blocker.

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

# SEMREADYFIX
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
env OPENAI_API_KEY=dummy-local-key uv run mcp-index index check-semantic
SEMANTIC_SEARCH_ENABLED=true CODE_INDEX_DOGFOOD_REPO=. uv run pytest tests/real_world/test_semantic_search.py -q --no-cov

# SEMCOLLECT
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
env OPENAI_API_KEY=dummy-local-key uv run mcp-index index check-semantic
sqlite3 .mcp-index/current.db 'select count(*) from chunk_summaries; select count(*) from semantic_points;'
SEMANTIC_SEARCH_ENABLED=true CODE_INDEX_DOGFOOD_REPO=. uv run pytest tests/real_world/test_semantic_search.py -q --no-cov

# SEMSUMFIX
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_summarization.py -q --no-cov
env OPENAI_API_KEY=dummy-local-key uv run python - <<'PY'
...
PY
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
sqlite3 .mcp-index/current.db 'select count(*) from chunk_summaries; select count(*) from semantic_points;'
SEMANTIC_SEARCH_ENABLED=true CODE_INDEX_DOGFOOD_REPO=. uv run pytest tests/real_world/test_semantic_search.py -q --no-cov

# SEMSYNCFIX
env OPENAI_API_KEY=dummy-local-key uv run python - <<'PY'
...
PY
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
sqlite3 .mcp-index/current.db 'select count(*) from chunk_summaries; select count(*) from semantic_points;'
RUN_REAL_WORLD_TESTS=1 SEMANTIC_SEARCH_ENABLED=true CODE_INDEX_DOGFOOD_REPO=. OPENAI_API_KEY=dummy-local-key uv run --extra dev python -m pytest tests/real_world/test_semantic_search.py -q --no-cov -k repo_local_dogfood_queries_stay_on_semantic_path -rs
```
