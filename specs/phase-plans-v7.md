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

### Phase 18 — AGENTS Lexical Timeout Repair (SEMAGENTS)

**Objective**

Repair the next exact repo-local force-full blocker where lexical indexing now
times out while processing `AGENTS.md`, so the dogfood rebuild can move past
that bounded policy document and either reach semantic closeout or surface the
next narrower downstream blocker.

**Exit criteria**
- [ ] `AGENTS.md` no longer exceeds the lexical timeout during
      `repository sync --force-full`.
- [ ] The lexical timeout watchdog remains active and still fails closed for
      true path-level stalls.
- [ ] The live force-full rerun either completes through indexed-commit
      freshness or exits with a new exact blocker that is narrower than
      `AGENTS.md` lexical processing.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the AGENTS repair,
      the rerun outcome, current-versus-indexed commit evidence, and the
      final ready or still-blocked verdict.

**Scope notes**

Keep this phase narrowly focused on why `AGENTS.md` is now slow enough to trip
the lexical watchdog after SEMANALYSIS cleared
`FINAL_COMPREHENSIVE_MCP_ANALYSIS.md`. Prefer bounded parsing, chunking, or
exclusion-policy fixes over weakening the timeout globally.

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
- SEMANALYSIS

**Produces**
- IF-0-SEMAGENTS-1 — AGENTS lexical timeout repair and rerun evidence contract.

### Phase 19 — README Lexical Timeout Repair (SEMREADME)

**Objective**

Repair the next exact repo-local force-full blocker where lexical indexing now
times out while processing `README.md`, so the dogfood rebuild can move past
that bounded repository guide and either reach semantic closeout or surface the
next narrower downstream blocker.

**Exit criteria**
- [ ] `README.md` no longer exceeds the lexical timeout during
      `repository sync --force-full`.
- [ ] The lexical timeout watchdog remains active and still fails closed for
      true path-level stalls.
- [ ] The live force-full rerun either completes through indexed-commit
      freshness or exits with a new exact blocker that is narrower than
      `README.md` lexical processing.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the README repair,
      the rerun outcome, current-versus-indexed commit evidence, and the
      final ready or still-blocked verdict.

**Scope notes**

Keep this phase narrowly focused on why `README.md` is now slow enough to trip
the lexical watchdog after SEMAGENTS cleared `AGENTS.md`. Prefer bounded
parsing, chunking, or exclusion-policy fixes over weakening the timeout
globally.

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
- SEMAGENTS

**Produces**
- IF-0-SEMREADME-1 — README lexical timeout repair and rerun evidence contract.

### Phase 20 — Post-Lexical Semantic Closeout (SEMCLOSEOUT)

**Objective**

Repair the remaining semantic-stage closeout gap exposed by SEMREADME so a
clean `repository sync --force-full` rebuild that now clears every lexical
timeout also produces authoritative summaries, semantic vectors, and semantic
readiness `ready` for the active `oss_high` profile.

**Exit criteria**
- [ ] A clean force-full rebuild still ends with `Indexed commit` equal to the
      current commit and repository readiness `ready`.
- [ ] The same rebuild produces non-zero `chunk_summaries` and non-zero
      `semantic_points` linked to `code_index__oss_high__v1`.
- [ ] `uv run mcp-index repository status` reports semantic readiness `ready`
      instead of `summaries_missing` for the active profile.
- [ ] Repo-local semantic dogfood queries return semantic-path code results
      instead of skipping on `semantic_not_ready`.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is refreshed with the semantic
      closeout evidence and final semantic-ready or exact still-blocked verdict.

**Scope notes**

This phase exists only because SEMREADME cleared the final lexical timeout and
restored indexed-commit freshness on the current commit, but the live rebuild
still ends with semantic readiness `summaries_missing` and zero summaries or
vectors. Keep the work narrowly on authoritative summary generation, semantic
vector writes, and the strict semantic closeout path now that lexical indexing
is no longer the blocker.

**Non-goals**

- No lexical timeout or Markdown bounded-path work.
- No semantic ranking redesign.
- No multi-repo rollout expansion beyond this repo-local dogfood closeout.

**Key files**

- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/storage/git_index_manager.py`
- `mcp_server/indexing/summarization.py`
- `mcp_server/utils/semantic_indexer.py`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `docs/guides/semantic-onboarding.md`
- `tests/real_world/test_semantic_search.py`
- `tests/docs/test_semdogfood_evidence_contract.py`

**Depends on**
- SEMREADME

**Produces**
- IF-0-SEMCLOSEOUT-1 — Post-lexical semantic summary/vector closeout contract.

### Phase 21 — Semantic Summary Timeout Recovery (SEMTIMEOUT)

**Objective**

Repair the remaining repo-wide summary-timeout blocker exposed by SEMCLOSEOUT
so force-full rebuilds can finish authoritative summary drain on the active
commit instead of failing with `Summary generation timed out before strict
semantic indexing could start`.

**Exit criteria**
- [ ] A force-full rebuild on the active repo no longer exits with
      `Summary generation timed out before strict semantic indexing could start`.
- [ ] Dispatcher summary recovery uses bounded one-batch passes and timeout
      backoff so repo-local semantic progress persists durably without relying
      on one unbounded summary call to drain the whole backlog.
- [ ] `uv run mcp-index repository status` shows the indexed commit can
      advance to the current commit again after the repo-local semantic rerun,
      or it records a narrower post-timeout downstream blocker than summary
      timeout.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is refreshed with the timeout
      recovery evidence, current summary/vector counts, and the new exact
      downstream blocker if semantic closeout is still incomplete.

**Scope notes**

This phase exists only because SEMCLOSEOUT proved partial live summary
persistence (`chunk_summaries` increased) but the real repo-wide force-full
rerun still timed out before strict semantic indexing could start. Keep this
phase narrowly on repo-wide summary pass sizing, timeout recovery, and the
exact live blocker surfaced after timeout is removed.

**Non-goals**

- No lexical timeout or Markdown bounded-path work.
- No semantic ranking redesign.
- No multi-repo rollout expansion beyond this repo-local dogfood recovery.

**Key files**

- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/indexing/summarization.py`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `docs/guides/semantic-onboarding.md`
- `tests/test_dispatcher.py`
- `tests/test_summarization.py`
- `tests/docs/test_semdogfood_evidence_contract.py`

**Depends on**
- SEMCLOSEOUT

**Produces**
- IF-0-SEMTIMEOUT-1 — Repo-wide semantic summary timeout recovery contract.

### Phase 22 — Single-Pass Summary Stall Recovery (SEMPASSSTALL)

**Objective**

Repair the remaining single-pass doc-heavy summary stall exposed by SEMTIMEOUT
so force-full rebuilds can return the bounded continuation blocker promptly
instead of hanging inside one summary pass.

**Exit criteria**
- [ ] A force-full rebuild on the active repo reaches the semantic-stage
      bounded continuation verdict instead of stalling inside a single
      doc-heavy summary pass.
- [ ] Repo-wide doc-like summary batches are sized or checkpointed so one
      batch cannot prevent the dispatcher from reporting continuation metadata.
- [ ] `uv run mcp-index repository status` reports the current exact semantic
      readiness state with summary/vector counts after the live rerun.

**Scope notes**

This phase exists only if SEMTIMEOUT clears the repo-wide handoff gap but the
live force-full rerun still stalls inside a single doc-heavy summary pass before
it can emit the bounded continuation blocker.

**Non-goals**

- No semantic ranking redesign.
- No multi-repo rollout expansion beyond this repo-local dogfood recovery.
- No artifact publishing or GitHub Actions release work.

**Key files**

- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/indexing/summarization.py`
- `mcp_server/storage/git_index_manager.py`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `tests/test_dispatcher.py`
- `tests/test_summarization.py`
- `tests/test_git_index_manager.py`

**Depends on**
- SEMTIMEOUT

**Produces**
- IF-0-SEMPASSSTALL-1 — Repo-wide single-pass summary stall recovery contract.

### Phase 23 — Single-Call Summary Timeout Recovery (SEMCALLTIME)

**Objective**

Repair the newly exposed single-call summary hang uncovered by SEMPASSSTALL so
force-full rebuilds either persist at least one authoritative summary or fail
closed with an exact timeout blocker instead of staying in flight inside the
first summary invocation.

**Exit criteria**
- [ ] A force-full rebuild on the active repo no longer spends multiple minutes
      inside the first repo-scope summary invocation with zero new
      `chunk_summaries`.
- [ ] Repo-scope summary execution applies a bounded per-call timeout or
      equivalent cancellation path that returns an exact blocker when one
      summary call does not complete promptly.
- [ ] `uv run mcp-index repository status` and
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` record the repaired per-call
      behavior together with current summary/vector counts and the exact
      follow-on blocker, if any.

**Scope notes**

This phase exists only if SEMPASSSTALL proves repo-scope passes are narrowed to
one file / one doc-like chunk, but the live force-full rerun still remains in
flight long enough that no authoritative summary is written and no bounded
continuation verdict is returned.

**Non-goals**

- No semantic ranking redesign.
- No multi-repo rollout expansion beyond this repo-local dogfood recovery.
- No artifact publishing or GitHub Actions release work.

**Key files**

- `mcp_server/indexing/summarization.py`
- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/storage/git_index_manager.py`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `tests/test_summarization.py`
- `tests/test_dispatcher.py`
- `tests/test_git_index_manager.py`
- `tests/docs/test_semdogfood_evidence_contract.py`

**Depends on**
- SEMPASSSTALL

**Produces**
- IF-0-SEMCALLTIME-1 — Repo-wide single-call summary timeout recovery contract.

### Phase 24 — Timed-Out Summary Call Exit Recovery (SEMCANCEL)

**Objective**

Repair the remaining live force-full hang uncovered by SEMCALLTIME so a
timed-out repo-scope summary call exits promptly, records the exact blocker on
status surfaces, and does not leave the active SQLite/Qdrant runtime in a
larger zero-summary partial state.

**Exit criteria**
- [ ] A force-full rebuild on the active repo returns promptly after the first
      timed-out repo-scope summary call instead of staying in flight until
      manual termination.
- [ ] `uv run mcp-index repository status` records the exact timed-out-call
      blocker or partial-index-failure follow-on state after the repaired live
      rerun.
- [ ] A terminated or timed-out force-full rerun does not inflate lexical row
      counts while leaving `chunk_summaries = 0` and `semantic_points = 0`.

**Scope notes**

This phase exists only if SEMCALLTIME proves the per-call timeout contract in
unit coverage, but the live repo-local force-full rerun still remains in
flight and continues mutating lexical/runtime state until it is killed
manually.

**Non-goals**

- No semantic ranking redesign.
- No multi-repo rollout expansion beyond this repo-local dogfood recovery.
- No artifact publishing or GitHub Actions release work.

**Key files**

- `mcp_server/indexing/summarization.py`
- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/storage/git_index_manager.py`
- `mcp_server/cli/repository_commands.py`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `tests/test_summarization.py`
- `tests/test_dispatcher.py`
- `tests/test_git_index_manager.py`
- `tests/docs/test_semdogfood_evidence_contract.py`

**Depends on**
- SEMCALLTIME

**Produces**
- IF-0-SEMCANCEL-1 — Timed-out summary call exit and partial-state closeout
  contract.

### Phase 25 — Live Force-Full Exit Trace Recovery (SEMEXITTRACE)

**Objective**

If SEMCANCEL lands its unit-level cancellation and runtime-restore contracts
but the real repo-local `repository sync --force-full` path still does not
return promptly, add precise live-stage tracing and fail-closed shutdown
accounting so operators can see the exact in-flight stage and the command can
persist a narrower blocker without manual guesswork.

**Exit criteria**
- [ ] A live repo-local force-full rerun that still fails to complete now
      persists a precise final stage or in-flight blocker instead of requiring
      manual interpretation of partial SQLite growth.
- [ ] `uv run mcp-index repository status` records whether the hung path was
      still in lexical indexing, summary-call shutdown, or later closeout when
      the command aborted.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` captures the stage-trace
      evidence and whether runtime containment happened before process exit or
      only after external termination.

**Scope notes**

This phase exists only if SEMCANCEL proves the bounded timeout and zero-summary
restore behavior in unit coverage, but the live repo-local force-full rerun on
the active commit still remains in flight long enough that operators must kill
it before the repaired blocker can be persisted.

**Non-goals**

- No new semantic ranking or retrieval work.
- No broader watchdog redesign outside the force-full live tracing path.
- No artifact publishing or release-process changes.

**Key files**

- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/storage/git_index_manager.py`
- `mcp_server/cli/repository_commands.py`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `tests/test_dispatcher.py`
- `tests/test_git_index_manager.py`
- `tests/docs/test_semdogfood_evidence_contract.py`

**Depends on**
- SEMCANCEL

**Produces**
- IF-0-SEMEXITTRACE-1 — Live force-full exit tracing and persisted blocker
  contract.

### Phase 26 — Fast Test Report Lexical Recovery (SEMFASTREPORT)

**Objective**

Repair the next exact live blocker surfaced by SEMEXITTRACE so a repo-local
`repository sync --force-full` rerun does not spend minutes in lexical walking
on generated `fast_test_results/fast_report_*.md` artifacts before semantic
closeout can begin.

**Exit criteria**
- [ ] A live repo-local force-full rerun no longer times out while the durable
      trace is still in lexical walking on `fast_test_results/fast_report_*.md`.
- [ ] If `fast_test_results/` remains indexable, its Markdown/report path uses
      bounded lexical handling that returns promptly enough for the force-full
      run to advance beyond lexical walking.
- [ ] If `fast_test_results/` is judged generated noise, the chosen ignore or
      filtering contract is explicit, tested, and reflected in
      `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`.
- [ ] The refreshed dogfood evidence records whether the next rerun advances
      past lexical walking or preserves a narrower downstream blocker.

**Scope notes**

This phase exists only if SEMEXITTRACE proves the live force-full command is
still blocked in lexical walking and identifies a specific generated
`fast_test_results/fast_report_*.md` path as the most recent durable progress
marker. Keep the repair narrowly on that file family and the lexical/index
filter boundary it exposes.

**Non-goals**

- No semantic ranking or embedding-pipeline redesign.
- No reopening of summary-timeout or runtime-restore work from SEMCALLTIME or
  SEMCANCEL unless the new evidence proves direct contract drift there.
- No artifact publishing or release-process changes.

**Key files**

- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/core/ignore_patterns.py`
- `mcp_server/storage/git_index_manager.py`
- `mcp_server/cli/repository_commands.py`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `tests/test_dispatcher.py`
- `tests/test_git_index_manager.py`
- `tests/docs/test_semdogfood_evidence_contract.py`

**Depends on**
- SEMEXITTRACE

**Produces**
- IF-0-SEMFASTREPORT-1 — Generated fast-test report lexical recovery or
  explicit ignore-boundary contract.

### Phase 27 — Pytest Overview Lexical Recovery (SEMPYTESTOVERVIEW)

**Objective**

Repair the next exact live blocker surfaced by SEMFASTREPORT so a repo-local
`repository sync --force-full` rerun does not remain in lexical walking on
`ai_docs/pytest_overview.md` after the generated fast-test report family is
cleared.

**Exit criteria**
- [ ] A live repo-local force-full rerun no longer leaves the durable trace in
      lexical walking with `ai_docs/pytest_overview.md` as the last progress
      marker.
- [ ] The chosen repair for `ai_docs/pytest_overview.md` is explicit, narrow,
      tested, and preserves indexing for unrelated Markdown/documentation files
      unless new evidence proves they are the next exact blocker.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is refreshed with the
      `ai_docs/pytest_overview.md` rerun outcome and either semantic-stage
      advancement or a still narrower downstream blocker.

**Scope notes**

This phase exists only if SEMFASTREPORT proves the generated
`fast_test_results/fast_report_*.md` family is no longer the active lexical
blocker but the live force-full rerun still stalls on `ai_docs/pytest_overview.md`.
Keep the repair narrowly on that exact document and the lexical handling path
it exercises.

**Non-goals**

- No reopening of the fast-test report ignore boundary unless new evidence
  proves direct drift there.
- No summary-timeout, semantic closeout, release, or rollout-policy work.

**Key files**

- `ai_docs/pytest_overview.md`
- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/storage/git_index_manager.py`
- `mcp_server/cli/repository_commands.py`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `tests/test_dispatcher.py`
- `tests/test_git_index_manager.py`
- `tests/docs/test_semdogfood_evidence_contract.py`

**Depends on**
- SEMFASTREPORT

**Produces**
- IF-0-SEMPYTESTOVERVIEW-1 — Pytest overview lexical recovery and rerun
  evidence contract.

### Phase 28 — Visual Report Script Lexical Recovery (SEMVISUALREPORT)

**Objective**

Carry the live force-full rerun beyond `scripts/create_multi_repo_visual_report.py`
after SEMPYTESTOVERVIEW proves the `ai_docs/pytest_overview.md` seam is no
longer the active lexical blocker.

**Exit criteria**
- [ ] A live repo-local force-full rerun no longer leaves the durable trace on
      `scripts/create_multi_repo_visual_report.py`.
- [ ] The chosen repair for `scripts/create_multi_repo_visual_report.py` stays
      narrow, tested, and does not reopen the `ai_docs/*_overview.md` or
      fast-test report lexical boundaries without direct evidence.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is refreshed with the rerun
      outcome and either semantic-stage advancement or the next exact
      downstream blocker after the visual-report script seam.

**Scope notes**

This phase exists only if SEMPYTESTOVERVIEW proves the bounded
`ai_docs/*_overview.md` repair works but the live force-full rerun still does
not complete and the latest durable lexical progress marker advances to
`scripts/create_multi_repo_visual_report.py`.

**Non-goals**

- No reopening of the `ai_docs/*_overview.md` bounded Markdown path unless new
  evidence proves direct drift there.
- No semantic timeout, release, or rollout-policy work.

**Key files**

- `scripts/create_multi_repo_visual_report.py`
- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/storage/git_index_manager.py`
- `mcp_server/cli/repository_commands.py`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `tests/test_dispatcher.py`
- `tests/test_git_index_manager.py`
- `tests/docs/test_semdogfood_evidence_contract.py`

**Depends on**
- SEMPYTESTOVERVIEW

**Produces**
- IF-0-SEMVISUALREPORT-1 — Visual report script lexical recovery and rerun
  evidence contract.

### Phase 29 — Jedi AI Doc Lexical Recovery (SEMJEDI)

**Objective**

Carry the live force-full rerun beyond `ai_docs/jedi.md` after
SEMVISUALREPORT proves the exact bounded Python repair cleared
`scripts/create_multi_repo_visual_report.py` but the lexical walk still does
not complete.

**Exit criteria**
- [ ] A live repo-local force-full rerun no longer leaves the durable trace on
      `ai_docs/jedi.md`.
- [ ] The chosen repair for `ai_docs/jedi.md` stays narrow, tested, and does
      not reopen the `scripts/create_multi_repo_visual_report.py`,
      `ai_docs/*_overview.md`, or fast-test report lexical boundaries without
      direct evidence.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is refreshed with the rerun
      outcome and either semantic-stage advancement or the next exact
      downstream blocker after `ai_docs/jedi.md`.

**Scope notes**

This phase exists only if SEMVISUALREPORT proves the exact bounded Python
repair for `scripts/create_multi_repo_visual_report.py` works but the live
force-full rerun still does not complete and the latest durable lexical
progress marker advances to `ai_docs/jedi.md`.

**Non-goals**

- No reopening of the visual-report-script bounded Python path unless new
  evidence proves direct drift there.
- No semantic timeout, release, or rollout-policy work.

**Key files**

- `ai_docs/jedi.md`
- `mcp_server/plugins/markdown_plugin/plugin.py`
- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/storage/git_index_manager.py`
- `mcp_server/cli/repository_commands.py`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `tests/test_dispatcher.py`
- `tests/test_git_index_manager.py`
- `tests/test_repository_commands.py`
- `tests/docs/test_semdogfood_evidence_contract.py`

**Depends on**
- SEMVISUALREPORT

**Produces**
- IF-0-SEMJEDI-1 — Jedi AI doc lexical recovery and rerun evidence contract.

### Phase 30 — Force-Full Trace Freshness Recovery (SEMTRACEFRESHNESS)

**Objective**

Repair the remaining live force-full handoff gap exposed by SEMJEDI so a
repo-local rerun either refreshes `force_full_exit_trace.json` beyond the
older `ai_docs/pytest_overview.md` marker or names the true current in-flight
blocker instead of hanging with stale lexical progress.

**Exit criteria**
- [ ] A live repo-local force-full rerun no longer hangs with
      `force_full_exit_trace.json` frozen at
      `last_progress_path=/home/viperjuice/code/Code-Index-MCP/ai_docs/pytest_overview.md`
      and `in_flight_path=null`.
- [ ] The durable trace refreshes to a later lexical or semantic stage with a
      current in-flight path, or the command exits cleanly with a completed or
      bounded blocked trace.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is refreshed with the
      trace-freshness evidence, the rerun outcome, and the next exact blocker
      if semantic-stage work still does not begin.

**Scope notes**

This phase exists only because SEMJEDI proved the exact bounded Markdown path
for `ai_docs/jedi.md`, but the live force-full rerun on 2026-04-29 still hung
for more than two minutes while the durable trace remained stuck on the older
`ai_docs/pytest_overview.md` progress marker and never populated a current
`in_flight_path`.

**Non-goals**

- No reopening of the exact `ai_docs/jedi.md` bounded Markdown path unless new
  evidence proves direct drift there.
- No reopening of the fast-test report, `ai_docs/*_overview.md`, or
  visual-report-script lexical repairs unless the refreshed trace directly
  re-anchors on one of those seams.
- No semantic summary timeout or vector-write work before the live trace is
  trustworthy again.

**Key files**

- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/storage/git_index_manager.py`
- `mcp_server/cli/repository_commands.py`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `tests/test_dispatcher.py`
- `tests/test_git_index_manager.py`
- `tests/test_repository_commands.py`
- `tests/docs/test_semdogfood_evidence_contract.py`

**Depends on**
- SEMJEDI

**Produces**
- IF-0-SEMTRACEFRESHNESS-1 — Force-full trace freshness and downstream blocker
  evidence contract.

### Phase 31 — Devcontainer JSON Lexical Exit Recovery (SEMDEVCONTAINER)

**Objective**

Repair the next exact live lexical blocker exposed by SEMTRACEFRESHNESS so a
repo-local force-full rerun no longer leaves the durable trace parked on
`.devcontainer/devcontainer.json` past the configured lexical-timeout window.

**Exit criteria**
- [ ] A live repo-local force-full rerun no longer remains on
      `last_progress_path=/home/viperjuice/code/Code-Index-MCP/.devcontainer/post_create.sh`
      and `in_flight_path=/home/viperjuice/code/Code-Index-MCP/.devcontainer/devcontainer.json`
      with an unchanged `trace_timestamp` after the configured lexical timeout
      window.
- [ ] The rerun either completes the `.devcontainer/devcontainer.json` lexical
      seam and advances into later lexical or semantic work, or exits with a
      bounded lexical blocker that still names that exact file family
      truthfully.
- [ ] Operator status, tests, and dogfood evidence stay aligned with the
      configured timeout window and the exact `.devcontainer` blocker shape.

**Scope notes**

This phase exists only because SEMTRACEFRESHNESS repaired stale
`last_progress_path` reporting from the earlier `ai_docs/pytest_overview.md`
failure, but the refreshed live rerun on 2026-04-29 still stopped refreshing
at the later `.devcontainer/devcontainer.json` seam.

**Non-goals**

- No reopening of the exact `ai_docs/jedi.md`, `ai_docs/*_overview.md`,
  fast-test report, or visual-report-script lexical repairs unless new
  evidence re-anchors there.
- No semantic summary or vector-write work before the live `.devcontainer`
  lexical blocker exits cleanly or advances past that seam.
- No broad repo-wide timeout retuning beyond what is needed to make this exact
  blocker surface truthfully and fail closed.

**Key files**

- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/cli/repository_commands.py`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `tests/test_dispatcher.py`
- `tests/test_repository_commands.py`
- `tests/docs/test_semdogfood_evidence_contract.py`

**Depends on**
- SEMTRACEFRESHNESS

**Produces**
- IF-0-SEMDEVCONTAINER-1 — `.devcontainer` lexical exit and blocker evidence
  contract.

### Phase 32 — Artifact Publish Race Lexical Exit Recovery (SEMPUBLISHRACE)

**Objective**

Repair the next exact live lexical blocker exposed by SEMDEVCONTAINER so a
repo-local force-full rerun no longer leaves the durable trace parked on
`tests/test_artifact_publish_race.py` past the configured lexical-timeout
window.

**Exit criteria**
- [ ] A live repo-local force-full rerun no longer remains on
      `last_progress_path=/home/viperjuice/code/Code-Index-MCP/tests/test_benchmarks.py`
      and
      `in_flight_path=/home/viperjuice/code/Code-Index-MCP/tests/test_artifact_publish_race.py`
      with an unchanged `trace_timestamp` after the configured lexical timeout
      window.
- [ ] The rerun either completes the
      `tests/test_artifact_publish_race.py` lexical seam and advances into
      later lexical or semantic work, or exits with a bounded lexical blocker
      that still names that exact file family truthfully.
- [ ] Operator status, tests, and dogfood evidence stay aligned with the
      configured timeout window and the exact
      `tests/test_artifact_publish_race.py` blocker shape.

**Scope notes**

This phase exists only because SEMDEVCONTAINER proved the live force-full
rerun now advances beyond `.devcontainer/devcontainer.json`, but the refreshed
rerun on 2026-04-29 still stopped refreshing at the later
`tests/test_artifact_publish_race.py` seam.

**Non-goals**

- No reopening of the exact `.devcontainer/devcontainer.json`,
  `ai_docs/jedi.md`, `ai_docs/*_overview.md`, fast-test report, or
  visual-report-script lexical repairs unless new evidence re-anchors there.
- No semantic summary or vector-write work before the live
  `tests/test_artifact_publish_race.py` lexical blocker exits cleanly or
  advances past that seam.
- No broad repo-wide timeout retuning beyond what is needed to make this exact
  blocker surface truthfully and fail closed.

**Key files**

- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/cli/repository_commands.py`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `tests/test_dispatcher.py`
- `tests/test_repository_commands.py`
- `tests/docs/test_semdogfood_evidence_contract.py`

**Depends on**
- SEMDEVCONTAINER

**Produces**
- IF-0-SEMPUBLISHRACE-1 — `tests/test_artifact_publish_race.py` lexical exit
  and blocker evidence contract.

### Phase 33 — Devcontainer Rebound Lexical Re-Anchor Recovery (SEMDEVREBOUND)

**Objective**

Repair the renewed exact lexical blocker exposed after SEMPUBLISHRACE so a
repo-local force-full rerun no longer advances beyond
`tests/test_artifact_publish_race.py` only to re-anchor on
`.devcontainer/devcontainer.json` with a stale durable trace.

**Exit criteria**
- [ ] A live repo-local force-full rerun no longer remains on
      `last_progress_path=/home/viperjuice/code/Code-Index-MCP/.devcontainer/post_create.sh`
      and
      `in_flight_path=/home/viperjuice/code/Code-Index-MCP/.devcontainer/devcontainer.json`
      with an unchanged `trace_timestamp` after the configured lexical-timeout
      window once the rerun has already advanced beyond
      `tests/test_artifact_publish_race.py`.
- [ ] The rerun either completes the renewed `.devcontainer/devcontainer.json`
      lexical seam and advances into later lexical or semantic work, or exits
      with a bounded lexical blocker that still names that exact file family
      truthfully.
- [ ] Operator status, tests, and dogfood evidence stay aligned with the
      configured timeout window and the renewed
      `.devcontainer/devcontainer.json` blocker shape after the
      `tests/test_artifact_publish_race.py` seam is cleared.

**Scope notes**

This phase exists only because SEMPUBLISHRACE proved the live force-full rerun
no longer remains on `tests/test_artifact_publish_race.py`, but the same live
rerun later re-anchored on `.devcontainer/devcontainer.json` with a stale
running snapshot on 2026-04-29.

**Non-goals**

- No reopening of `tests/test_artifact_publish_race.py`, `ai_docs/jedi.md`,
  `ai_docs/*_overview.md`, fast-test report, or visual-report-script lexical
  repairs unless fresh evidence re-anchors there again.
- No semantic summary or vector-write work before the renewed
  `.devcontainer/devcontainer.json` lexical blocker exits cleanly or advances
  past that seam.
- No broad repo-wide timeout retuning beyond what is needed to make this exact
  blocker surface truthfully and fail closed.

**Key files**

- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/cli/repository_commands.py`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `tests/test_dispatcher.py`
- `tests/test_repository_commands.py`
- `tests/docs/test_semdogfood_evidence_contract.py`

**Depends on**
- SEMPUBLISHRACE

**Produces**
- IF-0-SEMDEVREBOUND-1 — renewed `.devcontainer/devcontainer.json` lexical
  re-anchor and blocker evidence contract.

### Phase 34 — Script Rebound Lexical Re-Anchor Recovery (SEMSCRIPTREBOUND)

**Objective**

Repair the next exact lexical blocker exposed after SEMDEVREBOUND so a
repo-local force-full rerun no longer clears `.devcontainer/devcontainer.json`
only to re-anchor on `scripts/quick_mcp_vs_native_validation.py` with a stale
durable trace.

**Exit criteria**
- [ ] A live repo-local force-full rerun no longer remains on
      `last_progress_path=/home/viperjuice/code/Code-Index-MCP/scripts/rerun_failed_native_tests.py`
      and
      `in_flight_path=/home/viperjuice/code/Code-Index-MCP/scripts/quick_mcp_vs_native_validation.py`
      with an unchanged `trace_timestamp` after the configured lexical-timeout
      window once the rerun has already advanced beyond
      `.devcontainer/devcontainer.json`.
- [ ] The rerun either completes the renewed
      `scripts/quick_mcp_vs_native_validation.py` lexical seam and advances
      into later lexical or semantic work, or exits with a bounded lexical
      blocker that still names that exact script pair truthfully.
- [ ] Operator status, tests, and dogfood evidence stay aligned with the
      configured timeout window and the renewed script-pair blocker shape
      after `.devcontainer/devcontainer.json` is cleared.

**Scope notes**

This phase exists only because SEMDEVREBOUND proved the live force-full rerun
no longer remains on `.devcontainer/devcontainer.json`, but the same live
rerun later re-anchored on `scripts/quick_mcp_vs_native_validation.py` with a
stale running snapshot on 2026-04-29.

**Non-goals**

- No reopening of `.devcontainer/devcontainer.json`,
  `tests/test_artifact_publish_race.py`, `ai_docs/jedi.md`,
  `ai_docs/*_overview.md`, fast-test report, or visual-report-script lexical
  repairs unless fresh evidence re-anchors there again.
- No semantic summary or vector-write work before the renewed
  `scripts/quick_mcp_vs_native_validation.py` lexical blocker exits cleanly or
  advances past that seam.
- No broad repo-wide timeout retuning beyond what is needed to make this exact
  blocker surface truthfully and fail closed.

**Key files**

- `mcp_server/plugins/python_plugin/plugin.py`
- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/cli/repository_commands.py`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `tests/test_dispatcher.py`
- `tests/test_repository_commands.py`
- `tests/docs/test_semdogfood_evidence_contract.py`

**Depends on**
- SEMDEVREBOUND

**Produces**
- IF-0-SEMSCRIPTREBOUND-1 — renewed
  `scripts/quick_mcp_vs_native_validation.py` lexical re-anchor and blocker
  evidence contract.

### Phase 35 — Force-Full Semantic Closeout Disk I/O Recovery (SEMDISKIO)

**Objective**

Repair the next downstream blocker exposed after SEMSCRIPTREBOUND so a
repo-local force-full rerun no longer clears the renewed
`scripts/quick_mcp_vs_native_validation.py` lexical seam only to fail in
final semantic closeout with `disk I/O error` before any summaries or vectors
are written.

**Exit criteria**
- [ ] A live repo-local force-full rerun no longer ends with
      `Trace stage: force_full_failed`,
      `Trace stage family: final_closeout`,
      `Trace blocker source: final_closeout`, and `Last sync error: disk I/O error`
      on the active commit after lexical walking has already advanced beyond
      `scripts/quick_mcp_vs_native_validation.py`.
- [ ] The rerun either completes semantic closeout far enough to write
      non-zero `chunk_summaries` or exits with a narrower semantic-stage
      blocker that names the real storage or closeout failure truthfully.
- [ ] Operator status, tests, and dogfood evidence stay aligned with the
      final-closeout failure mode and no longer claim that the active blocker
      is lexical once the script rebound seam has been cleared.

**Scope notes**

This phase exists only because SEMSCRIPTREBOUND proved the live force-full
rerun now advances far beyond the renewed script seam and later exits from
semantic closeout with `disk I/O error` on 2026-04-29.

**Non-goals**

- No reopening of `scripts/quick_mcp_vs_native_validation.py`,
  `.devcontainer/devcontainer.json`, `tests/test_artifact_publish_race.py`,
  `ai_docs/jedi.md`, `ai_docs/*_overview.md`, fast-test report, or
  visual-report-script lexical repairs unless fresh evidence re-anchors there
  again.
- No silent downgrade back to lexical success when semantic closeout fails.
- No unrelated semantic ranking or profile-default redesign unless the
  closeout failure proves those surfaces are the direct cause.

**Key files**

- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/storage/sqlite_store.py`
- `mcp_server/storage/git_index_manager.py`
- `mcp_server/cli/repository_commands.py`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `tests/test_dispatcher.py`
- `tests/test_repository_commands.py`
- `tests/docs/test_semdogfood_evidence_contract.py`

**Depends on**
- SEMSCRIPTREBOUND

**Produces**
- IF-0-SEMDISKIO-1 — post-lexical semantic closeout disk-I/O blocker and
  evidence contract.

### Phase 36 — Devcontainer Stale-Trace Rebound Recovery (SEMDEVSTALE)

**Objective**

Repair the renewed live lexical stall exposed during SEMDISKIO validation so a
repo-local force-full rerun no longer leaves a stale-running trace on
`.devcontainer/devcontainer.json` with `in_flight_path=null` before semantic
closeout can be exercised on the current head.

**Exit criteria**
- [ ] A refreshed repo-local force-full rerun on the post-SEMDISKIO head no
      longer remains on `Trace stage: lexical_walking`,
      `Trace freshness: stale-running snapshot`, and
      `Last progress path: /home/viperjuice/code/Code-Index-MCP/.devcontainer/devcontainer.json`.
- [ ] `force_full_exit_trace.json` and `uv run mcp-index repository status`
      either advance durably beyond `.devcontainer/devcontainer.json` or fail
      closed with a new exact lexical blocker that names the real renewed
      stall source.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is refreshed with the
      SEMDISKIO code/test repair, the renewed stale-running evidence on commit
      `c8b2d724`, and the final live verdict for the repaired rerun.

**Scope notes**

This phase exists only because the SEMDISKIO code-path repair landed, but the
live rerun started during SEMDISKIO validation on observed commit `c8b2d724`
never reached semantic closeout and instead left a stale-running lexical trace
on `.devcontainer/devcontainer.json` at `2026-04-29T10:35:02Z`.

**Non-goals**

- No reopening of the SEMDISKIO storage-closeout classification or runtime
  restore contract unless a refreshed rerun reaches final closeout again.
- No unrelated semantic ranking, summary-timeout, or profile-default changes
  unless the renewed lexical stall proves they are directly involved.

**Key files**

- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/storage/git_index_manager.py`
- `mcp_server/cli/repository_commands.py`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `tests/test_dispatcher.py`
- `tests/test_git_index_manager.py`
- `tests/test_repository_commands.py`

**Depends on**
- SEMDISKIO

**Produces**
- IF-0-SEMDEVSTALE-1 — renewed `.devcontainer/devcontainer.json`
  stale-trace lexical recovery and evidence contract.

### Phase 37 — Post-Devcontainer Test Stale-Trace Recovery (SEMTESTSTALE)

**Objective**

Repair the later live lexical/crash blocker exposed after SEMDEVSTALE clears
`.devcontainer/devcontainer.json`, so a repo-local force-full rerun no longer
exits unexpectedly and leaves a stale-running lexical trace on
`tests/test_reindex_resume.py` after advancing through
`tests/test_deployment_runbook_shape.py`.

**Exit criteria**
- [ ] A refreshed repo-local force-full rerun on the post-SEMDEVSTALE head no
      longer remains on `Trace stage: lexical_walking`,
      `Trace freshness: stale-running snapshot`, and
      `In-flight path: /home/viperjuice/code/Code-Index-MCP/tests/test_reindex_resume.py`
      after the process has already exited.
- [ ] `force_full_exit_trace.json` and `uv run mcp-index repository status`
      either fail closed with the true later blocker or advance durably beyond
      `tests/test_reindex_resume.py` into the next exact stage.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is refreshed with the
      SEMDEVSTALE handoff repair, the later
      `tests/test_deployment_runbook_shape.py -> tests/test_reindex_resume.py`
      stale-running evidence on commit `7e547c77`, and the final live verdict
      for the repaired rerun.

**Scope notes**

This phase exists only because SEMDEVSTALE cleared the renewed
`.devcontainer/devcontainer.json` stale seam, but the refreshed live rerun on
observed commit `7e547c77` exited abnormally and left the durable trace frozen
in lexical walking on a later exact test-file pair.

**Non-goals**

- No reopening of the `.devcontainer/devcontainer.json` exact-boundary repair
  unless the later test-path blocker re-anchors there again.
- No reopening of the SEMDISKIO storage-closeout contract unless a refreshed
  rerun reaches semantic closeout again.

**Key files**

- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/storage/git_index_manager.py`
- `mcp_server/cli/repository_commands.py`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `tests/test_dispatcher.py`
- `tests/test_git_index_manager.py`
- `tests/test_repository_commands.py`

**Depends on**
- SEMDEVSTALE

**Produces**
- IF-0-SEMTESTSTALE-1 — later test-path stale-trace lexical recovery and
  evidence contract.

### Phase 38 — Post-Test Script Abort Trace Recovery (SEMSCRIPTABORT)

**Objective**

Repair the later repo-local force-full abort exposed after SEMTESTSTALE clears
the stale-running test pair, so a rerun no longer exits with code `135` after
advancing into
`scripts/run_test_batch.py -> scripts/validate_mcp_comprehensive.py` without a
truthful final blocker.

**Exit criteria**
- [ ] A refreshed repo-local force-full rerun on the post-SEMTESTSTALE head no
      longer exits with code `135` after advancing to
      `scripts/run_test_batch.py -> scripts/validate_mcp_comprehensive.py`
      without either completing or naming a later exact blocker truthfully.
- [ ] `force_full_exit_trace.json` and `uv run mcp-index repository status`
      either advance durably beyond
      `scripts/run_test_batch.py -> scripts/validate_mcp_comprehensive.py`
      or fail closed with the real later script-family blocker.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is refreshed with the
      SEMTESTSTALE liveness repair, the later script-pair evidence on commit
      `a186b352`, and the final live verdict for the repaired rerun.

**Scope notes**

This phase exists only because SEMTESTSTALE proved the later
`tests/test_deployment_runbook_shape.py -> tests/test_reindex_resume.py`
stale-running seam is cleared, but the refreshed live rerun on observed commit
`a186b352` later exited with code `135` after advancing into an exact
script-family pair.

**Non-goals**

- No reopening of the cleared later test-pair stale-trace repair unless the
  live rerun re-anchors there again.
- No reopening of earlier `.devcontainer`, publish-race, or quick-validation
  exact-boundary slices unless the live rerun re-anchors there again.

**Key files**

- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/storage/git_index_manager.py`
- `mcp_server/cli/repository_commands.py`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `tests/test_dispatcher.py`
- `tests/test_git_index_manager.py`
- `tests/test_repository_commands.py`

**Depends on**
- SEMTESTSTALE

**Produces**
- IF-0-SEMSCRIPTABORT-1 — later script-family abort trace recovery and
  evidence contract.

### Phase 39 — Post-Script Root-Test Abort Trace Recovery (SEMROOTTESTABORT)

**Objective**

Repair or truthfully classify the later repo-local force-full abort exposed
after SEMSCRIPTABORT clears
`scripts/run_test_batch.py -> scripts/validate_mcp_comprehensive.py`, so a
rerun no longer exits with code `135` after advancing into
`tests/root_tests/test_voyage_api.py -> tests/root_tests/run_reranking_tests.py`
without an exact downstream blocker.

**Exit criteria**
- [ ] A refreshed repo-local force-full rerun on the post-SEMSCRIPTABORT head
      no longer exits with code `135` after advancing to
      `tests/root_tests/test_voyage_api.py -> tests/root_tests/run_reranking_tests.py`
      without either completing or naming a later exact blocker truthfully.
- [ ] `force_full_exit_trace.json` and `uv run mcp-index repository status`
      either advance durably beyond
      `tests/root_tests/test_voyage_api.py -> tests/root_tests/run_reranking_tests.py`
      or fail closed with the real later root-test blocker.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is refreshed with the
      SEMSCRIPTABORT repair, the later root-test-pair evidence on commit
      `098c1ad1`, and the final live verdict for the rerun.

**Scope notes**

This phase exists only because SEMSCRIPTABORT proved the later
`scripts/run_test_batch.py -> scripts/validate_mcp_comprehensive.py`
script seam is cleared, but the refreshed live rerun on observed commit
`098c1ad1` later exited with code `135` after advancing into an exact
root-test pair.

**Non-goals**

- No reopening of the cleared later script-pair seam unless the live rerun
  re-anchors there again.
- No reopening of earlier `.devcontainer`, publish-race, quick-validation, or
  later test-pair stale-trace slices unless the live rerun re-anchors there
  again.

**Key files**

- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/storage/git_index_manager.py`
- `mcp_server/cli/repository_commands.py`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `tests/test_dispatcher.py`
- `tests/test_git_index_manager.py`
- `tests/test_repository_commands.py`

**Depends on**
- SEMSCRIPTABORT

**Produces**
- IF-0-SEMROOTTESTABORT-1 — later root-test abort trace recovery and evidence
  contract.

### Phase 40 — Renewed Devcontainer Lexical Relapse Recovery (SEMDEVRELAPSE)

**Objective**

Repair the renewed repo-local force-full lexical relapse exposed after
SEMROOTTESTABORT hardens the later root-test seam, so a refreshed rerun on the
new head no longer re-anchors early on `.devcontainer/devcontainer.json`
before it can reach the later script/root-test families.

**Exit criteria**
- [ ] A refreshed repo-local force-full rerun on the post-SEMROOTTESTABORT
      head no longer stalls or terminates with the durable trace re-anchored
      on `Last progress path:
      /home/viperjuice/code/Code-Index-MCP/.devcontainer/devcontainer.json`
      while still in `Trace stage: lexical_walking`.
- [ ] `force_full_exit_trace.json` and `uv run mcp-index repository status`
      either advance durably beyond `.devcontainer/devcontainer.json` on the
      new head or fail closed with a newer exact blocker that is truthful for
      the refreshed rerun.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` is refreshed with the
      SEMROOTTESTABORT coverage landing, the renewed `.devcontainer`
      relapse evidence on commit `a4120401`, and the final live verdict for
      the repaired rerun.

**Scope notes**

This phase exists only because SEMROOTTESTABORT proved the later
`tests/root_tests/test_voyage_api.py ->
tests/root_tests/run_reranking_tests.py` seam is now frozen correctly, but
the refreshed live rerun on observed commit `a4120401` never reached that pair
and instead re-anchored earlier on `.devcontainer/devcontainer.json`.

**Non-goals**

- No reopening of the later root-test seam unless a refreshed rerun reaches it
  again and exposes a newer blocker.
- No reopening of the cleared later script-pair seam unless the live rerun
  re-anchors there again.
- No widening into semantic-closeout or summary/vector work unless the
  refreshed rerun clears the renewed `.devcontainer` relapse first.

**Key files**

- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/storage/git_index_manager.py`
- `mcp_server/cli/repository_commands.py`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `tests/test_dispatcher.py`
- `tests/test_git_index_manager.py`
- `tests/test_repository_commands.py`

**Depends on**
- SEMROOTTESTABORT

**Produces**
- IF-0-SEMDEVRELAPSE-1 — renewed `.devcontainer/devcontainer.json` lexical
  relapse recovery and evidence contract.

### Phase 41 — Post-Devcontainer Walk Gap Recovery (SEMWALKGAP)

**Objective**

Repair the post-devcontainer force-full visibility gap exposed by
SEMDEVRELAPSE, so a refreshed rerun on the new head no longer appears stuck on
`.devcontainer/devcontainer.json` when lexical walking has actually moved into
the long tail that follows that boundary.

**Exit criteria**
- [ ] A refreshed repo-local force-full rerun on the post-SEMDEVRELAPSE head
      either advances durably to a later exact path after
      `.devcontainer/devcontainer.json` or emits a truthful newer blocker
      before the 120-second watchdog expires.
- [ ] The next authoritative blocker after `.devcontainer/devcontainer.json`
      is identified as either a later exact indexed path or a deliberate
      bounded exclusion or visibility rule for the post-devcontainer tail.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the walk-order
      evidence showing `.devcontainer/devcontainer.json` followed by the
      post-devcontainer tail and the final live verdict for the repaired rerun.

**Scope notes**

This phase exists only if SEMDEVRELAPSE proves the same-file devcontainer
relapse still appears in the durable trace even though walk-order evidence
shows `.devcontainer/devcontainer.json` is followed by generated fast-report
artifacts and `test_workspace/real_repos/**` content before the next later
exact blocker becomes visible.

**Non-goals**

- No reopening of the earlier `.devcontainer/post_create.sh ->
  .devcontainer/devcontainer.json` rebound contract.
- No reopening of later script or root-test seams unless a refreshed rerun
  reaches them again and exposes a newer blocker.
- No widening into semantic-closeout or summary/vector work unless the
  post-devcontainer lexical walk gap is cleared first.

**Key files**

- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/storage/git_index_manager.py`
- `mcp_server/cli/repository_commands.py`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `tests/test_dispatcher.py`
- `tests/test_git_index_manager.py`
- `tests/test_repository_commands.py`

**Depends on**
- SEMDEVRELAPSE

**Produces**
- IF-0-SEMWALKGAP-1 — post-devcontainer walk-gap recovery and evidence
  contract.

### Phase 42 — Visualization Quick Charts Lexical Recovery (SEMQUICKCHARTS)

**Objective**

Repair the later lexical blocker exposed by SEMWALKGAP so a refreshed rerun on
the new head no longer times out with the durable trace stalled on
`mcp_server/visualization/__init__.py ->
mcp_server/visualization/quick_charts.py`.

**Exit criteria**
- [ ] A refreshed repo-local force-full rerun on the post-SEMWALKGAP head
      either advances durably beyond
      `mcp_server/visualization/quick_charts.py` or emits a truthful newer
      blocker before the 120-second watchdog expires.
- [ ] The repair stays narrowly scoped to the exact visualization pair
      `mcp_server/visualization/__init__.py ->
      mcp_server/visualization/quick_charts.py` plus the immediate
      dispatcher/trace/status plumbing needed to prove the outcome.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the SEMWALKGAP rerun
      outcome and the final live verdict for the visualization blocker.

**Scope notes**

This phase exists only if SEMWALKGAP proves the post-devcontainer tail is
skipped truthfully but the refreshed live rerun still remains in lexical
walking on the later visualization pair.

**Non-goals**

- No reopening of the post-devcontainer ignore-tail recovery once the live
  rerun has advanced beyond `.devcontainer/devcontainer.json`.
- No widening into semantic-closeout or summary/vector work unless the later
  visualization blocker is cleared first.
- No reopening of older exact seams unless a refreshed rerun reaches them
  again and exposes a different newer blocker.

**Key files**

- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/storage/git_index_manager.py`
- `mcp_server/cli/repository_commands.py`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `tests/test_dispatcher.py`
- `tests/test_git_index_manager.py`
- `tests/test_repository_commands.py`

**Depends on**
- SEMWALKGAP

**Produces**
- IF-0-SEMQUICKCHARTS-1 — visualization quick-charts lexical recovery and
  evidence contract.

### Phase 43 — Validation Evidence Lexical Recovery (SEMVALIDEVIDENCE)

**Objective**

Repair the next exact lexical blocker exposed by SEMQUICKCHARTS so a refreshed
rerun on the new head no longer times out with the durable trace stalled on
`docs/validation/ga-closeout-decision.md ->
docs/validation/mre2e-evidence.md`.

**Exit criteria**
- [ ] A refreshed repo-local force-full rerun on the post-SEMQUICKCHARTS head
      either advances durably beyond
      `docs/validation/mre2e-evidence.md` or emits a truthful newer blocker
      before the 120-second watchdog expires.
- [ ] The repair stays narrowly scoped to the exact validation-doc pair
      `docs/validation/ga-closeout-decision.md ->
      docs/validation/mre2e-evidence.md` plus the immediate
      dispatcher/trace/status plumbing needed to prove the outcome.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the SEMQUICKCHARTS
      rerun outcome and the final live verdict for the validation-doc blocker.

**Scope notes**

This phase exists only if SEMQUICKCHARTS proves the visualization pair is no
longer the active lexical blocker but the refreshed live rerun still remains in
lexical walking on the later validation-doc seam.

**Non-goals**

- No reopening of the visualization quick-charts recovery once the live rerun
  has advanced beyond `mcp_server/visualization/quick_charts.py`.
- No widening into semantic-closeout or summary/vector work unless the later
  validation-doc blocker is cleared first.
- No reopening of older exact seams unless a refreshed rerun reaches them
  again and exposes a different newer blocker.

**Key files**

- `mcp_server/plugins/markdown_plugin/plugin.py`
- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/storage/git_index_manager.py`
- `mcp_server/cli/repository_commands.py`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `tests/test_dispatcher.py`
- `tests/test_git_index_manager.py`
- `tests/test_repository_commands.py`
- `tests/docs/test_semdogfood_evidence_contract.py`

**Depends on**
- SEMQUICKCHARTS

**Produces**
- IF-0-SEMVALIDEVIDENCE-1 — validation-doc lexical recovery and evidence
  contract.

### Phase 44 — Benchmark Evidence Lexical Recovery (SEMBENCHDOCS)

**Objective**

Repair the next exact lexical blocker exposed by SEMVALIDEVIDENCE so a
refreshed rerun on the new head no longer times out with the durable trace
stalled on
`docs/benchmarks/mcp_vs_native_benchmark_fullrepo_fireworks_qwen_voyage_local_iter5_rerun.md ->
docs/benchmarks/production_benchmark.md`.

**Exit criteria**
- [ ] A refreshed repo-local force-full rerun on the post-SEMVALIDEVIDENCE
      head either advances durably beyond
      `docs/benchmarks/production_benchmark.md` or emits a truthful newer
      blocker before the 120-second watchdog expires.
- [ ] The repair stays narrowly scoped to the exact benchmark-doc pair
      `docs/benchmarks/mcp_vs_native_benchmark_fullrepo_fireworks_qwen_voyage_local_iter5_rerun.md ->
      docs/benchmarks/production_benchmark.md` plus the immediate
      dispatcher/trace/status plumbing needed to prove the outcome.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMVALIDEVIDENCE rerun outcome and the final live verdict for the
      benchmark-doc blocker.

**Scope notes**

This phase exists only if SEMVALIDEVIDENCE proves the validation-doc pair is no
longer the active lexical blocker but the refreshed live rerun still remains
in lexical walking on the later benchmark-doc seam.

**Non-goals**

- No reopening of the validation-doc recovery once the live rerun has advanced
  beyond `docs/validation/mre2e-evidence.md`.
- No widening into repo-wide benchmark-doc bypasses or semantic-closeout work
  unless the exact benchmark-doc blocker is cleared first.
- No reopening of older exact seams unless a refreshed rerun reaches them
  again and exposes a different newer blocker.

**Key files**

- `mcp_server/plugins/markdown_plugin/plugin.py`
- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/storage/git_index_manager.py`
- `mcp_server/cli/repository_commands.py`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `tests/test_dispatcher.py`
- `tests/test_git_index_manager.py`
- `tests/test_repository_commands.py`
- `tests/docs/test_semdogfood_evidence_contract.py`

**Depends on**
- SEMVALIDEVIDENCE

**Produces**
- IF-0-SEMBENCHDOCS-1 — benchmark-doc lexical recovery and evidence contract.

### Phase 45 — Archive Tail Walk-Gap Recovery (SEMARCHIVEWALKGAP)

**Objective**

Repair the next downstream lexical/trace gap exposed by SEMBENCHDOCS so a
refreshed rerun on the new head no longer terminalizes under the 120-second
watchdog with the durable trace stuck at
`analysis_archive/scripts_archive/scripts_test_files/verify_mcp_fix.py`
without a surviving later `in_flight_path`.

**Exit criteria**
- [ ] A refreshed repo-local force-full rerun on the post-SEMBENCHDOCS head
      either advances durably beyond
      `analysis_archive/scripts_archive/scripts_test_files/verify_mcp_fix.py`
      or emits a truthful newer blocker before the 120-second watchdog
      expires.
- [ ] The repair stays narrowly scoped to the later archive-tail walk-gap and
      the immediate dispatcher/trace/status plumbing needed to prove it.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the SEMBENCHDOCS
      rerun outcome and the final live verdict for the archive-tail blocker.

**Scope notes**

This phase exists only if SEMBENCHDOCS proves the benchmark-doc pair is no
longer the active lexical blocker but the refreshed live rerun still
terminalizes later in lexical walking around the archive tail without a
trustworthy successor file.

**Non-goals**

- No reopening of the benchmark-doc recovery once the live rerun has advanced
  beyond `docs/benchmarks/production_benchmark.md`.
- No blanket ignore rule for `analysis_archive/` or repo-wide lexical timeout
  retune unless the archive-tail blocker is proven to require it.
- No reopening of older exact seams unless a refreshed rerun reaches them
  again and exposes a different newer blocker.

**Key files**

- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/storage/git_index_manager.py`
- `mcp_server/cli/repository_commands.py`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `tests/test_dispatcher.py`
- `tests/test_git_index_manager.py`
- `tests/test_repository_commands.py`
- `tests/docs/test_semdogfood_evidence_contract.py`

**Depends on**
- SEMBENCHDOCS

**Produces**
- IF-0-SEMARCHIVEWALKGAP-1 — archive-tail walk-gap recovery and evidence
  contract.

### Phase 46 — Docs Governance Contract Lexical Recovery (SEMDOCGOV)

**Objective**

Repair the next downstream lexical blocker exposed by SEMARCHIVEWALKGAP so a
refreshed rerun on the new head no longer terminalizes under the 120-second
watchdog on
`tests/docs/test_mre2e_evidence_contract.py ->
tests/docs/test_gagov_governance_contract.py`.

**Exit criteria**
- [ ] A refreshed repo-local force-full rerun on the post-SEMARCHIVEWALKGAP
      head either advances durably beyond
      `tests/docs/test_mre2e_evidence_contract.py ->
      tests/docs/test_gagov_governance_contract.py` or emits a truthful newer
      blocker before the 120-second watchdog expires.
- [ ] The repair stays narrowly scoped to the docs-test contract pair and the
      immediate dispatcher/trace/status plumbing needed to prove it.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMARCHIVEWALKGAP rerun outcome and the final live verdict for the
      docs-test blocker.

**Scope notes**

This phase exists only if SEMARCHIVEWALKGAP proves the archive-tail seam is no
longer the active lexical blocker but the refreshed live rerun still
terminalizes later in lexical walking on the docs contract-test pair.

**Non-goals**

- No reopening of the archive-tail recovery once the live rerun has advanced
  beyond `analysis_archive/semantic_vs_sql_comparison_1750926162.json`.
- No broad `tests/docs/*.py` exemption or repo-wide lexical timeout retune
  unless the refreshed rerun proves the blocker requires it.
- No reopening of older benchmark, visualization, devcontainer, or
  archive-tail seams unless the refreshed rerun reaches them again and exposes
  a different newer blocker.

**Key files**

- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/storage/git_index_manager.py`
- `mcp_server/cli/repository_commands.py`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `tests/test_dispatcher.py`
- `tests/test_git_index_manager.py`
- `tests/test_repository_commands.py`
- `tests/docs/test_semdogfood_evidence_contract.py`

**Depends on**
- SEMARCHIVEWALKGAP

**Produces**
- IF-0-SEMDOCGOV-1 — docs governance contract lexical recovery and evidence
  contract.

### Phase 47 — Claude Command Lexical Recovery (SEMCLAUDECMDS)

**Objective**

Repair the next downstream lexical blocker exposed by SEMDOCGOV so a refreshed
rerun on the new head no longer terminalizes under the 120-second watchdog on
`.claude/commands/execute-lane.md ->
.claude/commands/plan-phase.md`.

**Exit criteria**
- [ ] A refreshed repo-local force-full rerun on the post-SEMDOCGOV head
      either advances durably beyond
      `.claude/commands/execute-lane.md ->
      .claude/commands/plan-phase.md` or emits a truthful newer blocker
      before the 120-second watchdog expires.
- [ ] The repair stays narrowly scoped to the `.claude/commands` markdown pair
      and the immediate dispatcher/trace/status plumbing needed to prove it.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the SEMDOCGOV rerun
      outcome and the final live verdict for the `.claude/commands` blocker.

**Scope notes**

This phase exists only if SEMDOCGOV proves the docs contract-test pair is no
longer the active lexical blocker but the refreshed live rerun still
terminalizes later in lexical walking on the `.claude/commands` markdown pair.

**Non-goals**

- No reopening of the docs-governance recovery once the live rerun has
  advanced beyond
  `tests/docs/test_mre2e_evidence_contract.py ->
  tests/docs/test_gagov_governance_contract.py`.
- No broad `.claude/**/*.md` exemption or repo-wide lexical timeout retune
  unless the refreshed rerun proves the blocker requires it.
- No reopening of older benchmark, visualization, devcontainer, archive-tail,
  or docs-governance seams unless the refreshed rerun reaches them again and
  exposes a different newer blocker.

**Key files**

- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/storage/git_index_manager.py`
- `mcp_server/cli/repository_commands.py`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `tests/test_dispatcher.py`
- `tests/test_git_index_manager.py`
- `tests/test_repository_commands.py`
- `tests/docs/test_semdogfood_evidence_contract.py`

**Depends on**
- SEMDOCGOV

**Produces**
- IF-0-SEMCLAUDECMDS-1 — Claude command lexical recovery and evidence
  contract.

### Phase 48 — Script Language Audit Lexical Recovery (SEMSCRIPTLANGS)

**Objective**

Repair the next downstream lexical blocker exposed by SEMCLAUDECMDS so a
refreshed rerun on the new head no longer terminalizes under the 120-second
watchdog on
`scripts/migrate_large_index_to_multi_repo.py ->
scripts/check_index_languages.py`.

**Exit criteria**
- [ ] A refreshed repo-local force-full rerun on the post-SEMCLAUDECMDS head
      either advances durably beyond
      `scripts/migrate_large_index_to_multi_repo.py ->
      scripts/check_index_languages.py` or emits a truthful newer blocker
      before the 120-second watchdog expires.
- [ ] The repair stays narrowly scoped to the exact script pair and the
      immediate dispatcher/trace/status/evidence plumbing needed to prove it.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the SEMCLAUDECMDS
      rerun outcome and the final live verdict for the later script-pair
      blocker.

**Scope notes**

This phase exists only if SEMCLAUDECMDS proves the `.claude/commands` pair is
no longer the active lexical blocker but the refreshed live rerun still
terminalizes later in lexical walking on the exact script pair
`scripts/migrate_large_index_to_multi_repo.py ->
scripts/check_index_languages.py`.

**Non-goals**

- No reopening of the `.claude/commands` recovery once the live rerun has
  advanced beyond
  `.claude/commands/execute-lane.md ->
  .claude/commands/plan-phase.md`.
- No broad `scripts/*.py` exemption or repo-wide lexical timeout retune unless
  the refreshed rerun proves the blocker requires it.
- No reopening of older benchmark, visualization, devcontainer, archive-tail,
  docs-governance, or `.claude` seams unless the refreshed rerun reaches them
  again and exposes a different newer blocker.

**Key files**

- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/storage/git_index_manager.py`
- `mcp_server/cli/repository_commands.py`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `tests/test_dispatcher.py`
- `tests/test_git_index_manager.py`
- `tests/test_repository_commands.py`
- `tests/docs/test_semdogfood_evidence_contract.py`

**Depends on**
- SEMCLAUDECMDS

**Produces**
- IF-0-SEMSCRIPTLANGS-1 — script language-audit lexical recovery and evidence
  contract.

### Phase 49 — Phase Plan Markdown Lexical Recovery (SEMPHASEPLANS)

**Objective**

Repair the next downstream lexical blocker exposed by SEMSCRIPTLANGS so a
refreshed rerun on the new head no longer terminalizes under the 120-second
watchdog on
`plans/phase-plan-v7-SEMPREFLIGHT.md ->
plans/phase-plan-v7-SEMDOCGOV.md`.

**Exit criteria**
- [ ] A refreshed repo-local force-full rerun on the post-SEMSCRIPTLANGS head
      either advances durably beyond
      `plans/phase-plan-v7-SEMPREFLIGHT.md ->
      plans/phase-plan-v7-SEMDOCGOV.md` or emits a truthful newer blocker
      before the 120-second watchdog expires.
- [ ] The repair stays narrowly scoped to the exact phase-plan markdown pair
      and the immediate dispatcher/trace/status/evidence plumbing needed to
      prove it.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the SEMSCRIPTLANGS
      rerun outcome and the final live verdict for the later phase-plan pair
      blocker.

**Scope notes**

This phase exists only if SEMSCRIPTLANGS proves the script language-audit pair
is no longer the active lexical blocker but the refreshed live rerun still
terminalizes later in lexical walking on the exact phase-plan markdown pair
`plans/phase-plan-v7-SEMPREFLIGHT.md ->
plans/phase-plan-v7-SEMDOCGOV.md`.

**Non-goals**

- No reopening of the script language-audit recovery once the live rerun has
  advanced beyond
  `scripts/migrate_large_index_to_multi_repo.py ->
  scripts/check_index_languages.py`.
- No broad `plans/phase-plan-v7-*.md` exemption or repo-wide lexical timeout
  retune unless the refreshed rerun proves the blocker requires it.
- No reopening of older benchmark, visualization, devcontainer, archive-tail,
  docs-governance, `.claude`, or script-language seams unless the refreshed
  rerun reaches them again and exposes a different newer blocker.

**Key files**

- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/storage/git_index_manager.py`
- `mcp_server/cli/repository_commands.py`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `tests/test_dispatcher.py`
- `tests/test_git_index_manager.py`
- `tests/test_repository_commands.py`
- `tests/docs/test_semdogfood_evidence_contract.py`

**Depends on**
- SEMSCRIPTLANGS

**Produces**
- IF-0-SEMPHASEPLANS-1 — phase-plan markdown lexical recovery and evidence
  contract.

### Phase 50 — Cross-Version Phase Plan Lexical Recovery (SEMCROSSPLANS)

**Objective**

Repair the next downstream lexical blocker exposed by SEMPHASEPLANS so a
refreshed rerun on the new head no longer terminalizes under the 120-second
watchdog on
`plans/phase-plan-v5-garecut.md ->
plans/phase-plan-v7-SEMWALKGAP.md`.

**Exit criteria**
- [ ] A refreshed repo-local force-full rerun on the post-SEMPHASEPLANS head
      either advances durably beyond
      `plans/phase-plan-v5-garecut.md ->
      plans/phase-plan-v7-SEMWALKGAP.md` or emits a truthful newer blocker
      before the 120-second watchdog expires.
- [ ] The repair stays narrowly scoped to the exact cross-version phase-plan
      pair and the immediate dispatcher/trace/status/evidence plumbing needed
      to prove it.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the SEMPHASEPLANS
      rerun outcome and the final live verdict for the later cross-version
      phase-plan blocker.

**Scope notes**

This phase exists only if SEMPHASEPLANS proves the earlier v7-only
phase-plan markdown pair is no longer the active lexical blocker but the
refreshed live rerun still terminalizes later in lexical walking on the exact
cross-version phase-plan pair
`plans/phase-plan-v5-garecut.md ->
plans/phase-plan-v7-SEMWALKGAP.md`.

**Non-goals**

- No reopening of the earlier
  `plans/phase-plan-v7-SEMPREFLIGHT.md ->
  plans/phase-plan-v7-SEMDOCGOV.md` recovery once the live rerun has advanced
  beyond that pair.
- No broad `plans/phase-plan-*.md` exemption or repo-wide lexical timeout
  retune unless the refreshed rerun proves the blocker requires it.
- No reopening of older benchmark, visualization, devcontainer, archive-tail,
  docs-governance, `.claude`, or script-language seams unless the refreshed
  rerun reaches them again and exposes a different newer blocker.

**Key files**

- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/storage/git_index_manager.py`
- `mcp_server/cli/repository_commands.py`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `tests/test_dispatcher.py`
- `tests/test_git_index_manager.py`
- `tests/test_repository_commands.py`
- `tests/docs/test_semdogfood_evidence_contract.py`

**Depends on**
- SEMPHASEPLANS

**Produces**
- IF-0-SEMCROSSPLANS-1 — cross-version phase-plan lexical recovery and
  evidence contract.

### Phase 51 — Late V7 Phase Plan Lexical Recovery (SEMPHASETAIL)

**Objective**

Repair the next downstream lexical blocker exposed by SEMCROSSPLANS so a
refreshed rerun on the new head no longer terminalizes under the 120-second
watchdog on
`plans/phase-plan-v7-SEMSYNCFIX.md ->
plans/phase-plan-v7-SEMVISUALREPORT.md`.

**Exit criteria**
- [ ] A refreshed repo-local force-full rerun on the post-SEMCROSSPLANS head
      either advances durably beyond
      `plans/phase-plan-v7-SEMSYNCFIX.md ->
      plans/phase-plan-v7-SEMVISUALREPORT.md` or emits a truthful newer
      blocker before the 120-second watchdog expires.
- [ ] The repair stays narrowly scoped to the exact later v7-only phase-plan
      pair and the immediate dispatcher/trace/status/evidence plumbing needed
      to prove it.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the SEMCROSSPLANS
      rerun outcome and the final live verdict for the later v7-only
      phase-plan blocker.

**Scope notes**

This phase exists only if SEMCROSSPLANS proves the earlier cross-version
phase-plan pair is no longer the active lexical blocker but the refreshed live
rerun still terminalizes later in lexical walking on the exact v7-only
phase-plan pair
`plans/phase-plan-v7-SEMSYNCFIX.md ->
plans/phase-plan-v7-SEMVISUALREPORT.md`.

**Non-goals**

- No reopening of the earlier cross-version recovery once the live rerun has
  advanced beyond
  `plans/phase-plan-v5-garecut.md ->
  plans/phase-plan-v7-SEMWALKGAP.md`.
- No broad `plans/phase-plan-v7-*.md` exemption or repo-wide lexical timeout
  retune unless the refreshed rerun proves the blocker requires it.
- No reopening of older benchmark, visualization, devcontainer, archive-tail,
  docs-governance, `.claude`, or script-language seams unless the refreshed
  rerun reaches them again and exposes a different newer blocker.

**Key files**

- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/storage/git_index_manager.py`
- `mcp_server/cli/repository_commands.py`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `tests/test_dispatcher.py`
- `tests/test_git_index_manager.py`
- `tests/test_repository_commands.py`
- `tests/docs/test_semdogfood_evidence_contract.py`

**Depends on**
- SEMCROSSPLANS

**Produces**
- IF-0-SEMPHASETAIL-1 — late v7-only phase-plan lexical recovery and evidence
  contract.

### Phase 52 — Historical Phase Plan Tail Recovery (SEMLEGACYPLANS)

**Objective**

Repair the next downstream lexical blocker exposed by SEMPHASETAIL so a
refreshed rerun on the new head no longer terminalizes under the 120-second
watchdog on
`plans/phase-plan-v6-WATCH.md ->
plans/phase-plan-v1-p19.md`.

**Exit criteria**
- [ ] A refreshed repo-local force-full rerun on the post-SEMPHASETAIL head
      either advances durably beyond
      `plans/phase-plan-v6-WATCH.md ->
      plans/phase-plan-v1-p19.md` or emits a truthful newer blocker before
      the 120-second watchdog expires.
- [ ] The repair stays narrowly scoped to the exact historical phase-plan pair
      and the immediate dispatcher/trace/status/evidence plumbing needed to
      prove it.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the SEMPHASETAIL
      rerun outcome and the final live verdict for the newly exposed
      historical phase-plan blocker.

**Scope notes**

This phase exists only if SEMPHASETAIL proves the later v7-only phase-plan
pair is no longer the active lexical blocker but the refreshed live rerun
still terminalizes later in lexical walking on the exact historical
phase-plan pair
`plans/phase-plan-v6-WATCH.md ->
plans/phase-plan-v1-p19.md`.

**Non-goals**

- No reopening of the earlier late v7-only recovery once the live rerun has
  advanced beyond
  `plans/phase-plan-v7-SEMSYNCFIX.md ->
  plans/phase-plan-v7-SEMVISUALREPORT.md`.
- No broad `plans/phase-plan-*.md` exemption or repo-wide lexical timeout
  retune unless the refreshed rerun proves the blocker requires it.
- No reopening of older benchmark, visualization, devcontainer, archive-tail,
  docs-governance, `.claude`, or script-language seams unless the refreshed
  rerun reaches them again and exposes a different newer blocker.

**Key files**

- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/storage/git_index_manager.py`
- `mcp_server/cli/repository_commands.py`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `tests/test_dispatcher.py`
- `tests/test_git_index_manager.py`
- `tests/test_repository_commands.py`
- `tests/docs/test_semdogfood_evidence_contract.py`

**Depends on**
- SEMPHASETAIL

**Produces**
- IF-0-SEMLEGACYPLANS-1 — historical phase-plan lexical recovery and evidence
  contract.

### Phase 53 — Mixed-Version Phase Plan Tail Recovery (SEMMIXEDPHASETAIL)

**Objective**

Repair the next downstream lexical blocker exposed by SEMLEGACYPLANS so a
refreshed rerun on the new head no longer terminalizes under the 120-second
watchdog on
`plans/phase-plan-v7-SEMPHASETAIL.md ->
plans/phase-plan-v5-gagov.md`.

**Exit criteria**
- [ ] A refreshed repo-local force-full rerun on the post-SEMLEGACYPLANS head
      either advances durably beyond
      `plans/phase-plan-v7-SEMPHASETAIL.md ->
      plans/phase-plan-v5-gagov.md` or emits a truthful newer blocker before
      the 120-second watchdog expires.
- [ ] The repair stays narrowly scoped to the exact mixed-version phase-plan
      pair and the immediate dispatcher/trace/status/evidence plumbing needed
      to prove it.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the SEMLEGACYPLANS
      rerun outcome and the final live verdict for the newly exposed
      mixed-version phase-plan blocker.

**Scope notes**

This phase exists only if SEMLEGACYPLANS proves the historical
`plans/phase-plan-v6-WATCH.md -> plans/phase-plan-v1-p19.md` seam is cleared
but the refreshed live rerun still terminalizes later in lexical walking on
the exact mixed-version phase-plan pair
`plans/phase-plan-v7-SEMPHASETAIL.md ->
plans/phase-plan-v5-gagov.md`.

**Non-goals**

- No reopening of the historical `WATCH -> p19` recovery once the live rerun
  has advanced beyond that seam.
- No broad `plans/phase-plan-*.md` exemption or repo-wide lexical timeout
  retune unless the refreshed rerun proves the blocker requires it.
- No reopening of older benchmark, visualization, devcontainer, archive-tail,
  docs-governance, `.claude`, or script-language seams unless the refreshed
  rerun reaches them again and exposes a different newer blocker.

**Key files**

- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/storage/git_index_manager.py`
- `mcp_server/cli/repository_commands.py`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `tests/test_dispatcher.py`
- `tests/test_git_index_manager.py`
- `tests/test_repository_commands.py`
- `tests/docs/test_semdogfood_evidence_contract.py`

**Depends on**
- SEMLEGACYPLANS

**Produces**
- IF-0-SEMMIXEDPHASETAIL-1 — mixed-version phase-plan lexical recovery and
  evidence contract.

### Phase 54 — Preflight Upgrade Tail Recovery (SEMPREUPGRADETAIL)

**Objective**

Carry the live force-full rerun beyond the later mixed script tail exposed
after SEMMIXEDPHASETAIL:
`scripts/preflight_upgrade.sh -> scripts/test_mcp_protocol_direct.py`.

**Exit criteria**
- [ ] A refreshed repo-local force-full rerun on the post-SEMMIXEDPHASETAIL
      head either advances durably beyond
      `scripts/preflight_upgrade.sh -> scripts/test_mcp_protocol_direct.py`
      or emits a truthful newer blocker before the 120-second watchdog
      expires.
- [ ] The chosen repair for the
      `scripts/preflight_upgrade.sh -> scripts/test_mcp_protocol_direct.py`
      seam stays narrow, tested, and does not reopen the earlier
      mixed-version phase-plan recovery without direct evidence.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the SEMMIXEDPHASETAIL
      rerun outcome and the final live verdict for the later script blocker
      pair.

**Scope notes**

This phase exists only if SEMMIXEDPHASETAIL proves the mixed-version
`plans/phase-plan-v7-SEMPHASETAIL.md -> plans/phase-plan-v5-gagov.md` seam is
cleared and subsequent reruns advance beyond any transient ai-docs waypoint,
but the refreshed live rerun still terminalizes later in lexical walking on
`scripts/preflight_upgrade.sh -> scripts/test_mcp_protocol_direct.py`.

**Non-goals**

- No reopening of the mixed-version phase-plan recovery once the live rerun
  has advanced beyond that seam.
- No broad reopening of earlier ai-docs seams such as
  `ai_docs/*_overview.md`, `ai_docs/jedi.md`, or
  `ai_docs/qdrant.md` unless the refreshed rerun proves the active blocker
  requires it.
- No repo-wide lexical timeout retune unless the refreshed rerun proves this
  later mixed script seam cannot be cleared with a narrower repair.

**Key files**

- `mcp_server/plugins/markdown_plugin/plugin.py`
- `mcp_server/storage/git_index_manager.py`
- `mcp_server/cli/repository_commands.py`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `tests/test_dispatcher.py`
- `tests/test_git_index_manager.py`
- `tests/test_repository_commands.py`
- `tests/docs/test_semdogfood_evidence_contract.py`

**Depends on**
- SEMMIXEDPHASETAIL

**Produces**
- IF-0-SEMPREUPGRADETAIL-1 — mixed script tail lexical recovery and evidence
  contract.

### Phase 55 — Verify/Simulator Tail Recovery (SEMVERIFYSIMTAIL)

**Objective**

Carry the live force-full rerun beyond the later Python script tail exposed
after SEMPREUPGRADETAIL:
`scripts/verify_embeddings.py -> scripts/claude_code_behavior_simulator.py`.

**Exit criteria**
- [ ] A refreshed repo-local force-full rerun on the post-SEMPREUPGRADETAIL
      head either advances durably beyond
      `scripts/verify_embeddings.py ->
      scripts/claude_code_behavior_simulator.py` or emits a truthful newer
      blocker before the 120-second watchdog expires.
- [ ] The chosen repair for the
      `scripts/verify_embeddings.py ->
      scripts/claude_code_behavior_simulator.py` seam stays narrow, tested,
      and does not reopen the repaired
      `scripts/preflight_upgrade.sh ->
      scripts/test_mcp_protocol_direct.py` boundary without direct evidence.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMPREUPGRADETAIL rerun outcome and the final live verdict for the
      later Python-script blocker pair.

**Scope notes**

This phase exists only if SEMPREUPGRADETAIL proves the mixed shell/Python
`scripts/preflight_upgrade.sh -> scripts/test_mcp_protocol_direct.py` seam is
cleared, but the refreshed live rerun still terminalizes later in lexical
walking on
`scripts/verify_embeddings.py -> scripts/claude_code_behavior_simulator.py`.

**Non-goals**

- No reopening of the repaired preflight-upgrade script recovery once the live
  rerun has advanced beyond that seam.
- No broad reopening of earlier script families such as
  `scripts/migrate_large_index_to_multi_repo.py ->
  scripts/check_index_languages.py` or
  `scripts/preflight_upgrade.sh ->
  scripts/test_mcp_protocol_direct.py` unless the refreshed rerun proves the
  active blocker requires it.
- No repo-wide lexical timeout retune unless the refreshed rerun proves this
  later Python-script seam cannot be cleared with a narrower repair.

**Key files**

- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/plugins/python_plugin/plugin.py`
- `mcp_server/storage/git_index_manager.py`
- `mcp_server/cli/repository_commands.py`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `tests/test_dispatcher.py`
- `tests/test_git_index_manager.py`
- `tests/test_repository_commands.py`
- `tests/docs/test_semdogfood_evidence_contract.py`

**Depends on**
- SEMPREUPGRADETAIL

**Produces**
- IF-0-SEMVERIFYSIMTAIL-1 — later Python-script lexical recovery and
  evidence contract.

### Phase 56 — Embed/Consolidation Tail Recovery (SEMEMBEDCONSOL)

**Objective**

Carry the live force-full rerun beyond the later Python script tail exposed
after SEMVERIFYSIMTAIL:
`scripts/create_semantic_embeddings.py -> scripts/consolidate_real_performance_data.py`.

**Exit criteria**
- [ ] A refreshed repo-local force-full rerun on the post-SEMVERIFYSIMTAIL
      head either advances durably beyond
      `scripts/create_semantic_embeddings.py ->
      scripts/consolidate_real_performance_data.py` or emits a truthful newer
      blocker before the 120-second watchdog expires.
- [ ] The chosen repair for the
      `scripts/create_semantic_embeddings.py ->
      scripts/consolidate_real_performance_data.py` seam stays narrow, tested,
      and does not reopen the repaired
      `scripts/verify_embeddings.py ->
      scripts/claude_code_behavior_simulator.py` boundary without direct
      evidence.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMVERIFYSIMTAIL rerun outcome and the final live verdict for the later
      Python-script blocker pair.

**Scope notes**

This phase exists only if SEMVERIFYSIMTAIL proves the later Python-script
`scripts/verify_embeddings.py -> scripts/claude_code_behavior_simulator.py`
seam is cleared, but the refreshed live rerun still terminalizes later in
lexical walking on
`scripts/create_semantic_embeddings.py -> scripts/consolidate_real_performance_data.py`.

**Non-goals**

- No reopening of the repaired verify/simulator script recovery once the live
  rerun has advanced beyond that seam.
- No broad reopening of earlier script families such as
  `scripts/preflight_upgrade.sh -> scripts/test_mcp_protocol_direct.py` or
  `scripts/migrate_large_index_to_multi_repo.py ->
  scripts/check_index_languages.py` unless the refreshed rerun proves the
  active blocker requires it.
- No repo-wide lexical timeout retune unless the refreshed rerun proves this
  later Python-script seam cannot be cleared with a narrower repair.

**Key files**

- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/plugins/python_plugin/plugin.py`
- `mcp_server/storage/git_index_manager.py`
- `mcp_server/cli/repository_commands.py`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `tests/test_dispatcher.py`
- `tests/test_git_index_manager.py`
- `tests/test_repository_commands.py`
- `tests/docs/test_semdogfood_evidence_contract.py`

**Depends on**
- SEMVERIFYSIMTAIL

**Produces**
- IF-0-SEMEMBEDCONSOL-1 — later Python-script lexical recovery and evidence
  contract.

### Phase 57 — Docs-Test Tail Recovery (SEMDOCTESTTAIL)

**Objective**

Carry the live force-full rerun beyond the later tests/docs tail exposed after
SEMEMBEDCONSOL:
`tests/docs/test_gaclose_evidence_closeout.py -> tests/docs/test_p8_deployment_security.py`.

**Exit criteria**
- [ ] A refreshed repo-local force-full rerun on the post-SEMEMBEDCONSOL
      head either advances durably beyond
      `tests/docs/test_gaclose_evidence_closeout.py ->
      tests/docs/test_p8_deployment_security.py` or emits a truthful newer
      blocker before the 120-second watchdog expires.
- [ ] The chosen repair for the
      `tests/docs/test_gaclose_evidence_closeout.py ->
      tests/docs/test_p8_deployment_security.py` seam stays narrow, tested,
      and does not reopen the repaired
      `scripts/create_semantic_embeddings.py ->
      scripts/consolidate_real_performance_data.py` boundary without direct
      evidence.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMEMBEDCONSOL rerun outcome and the final live verdict for the later
      tests/docs blocker pair.

**Scope notes**

This phase exists only if SEMEMBEDCONSOL proves the later Python-script
`scripts/create_semantic_embeddings.py ->
scripts/consolidate_real_performance_data.py` seam is cleared, but the
refreshed live rerun still terminalizes later in lexical walking on
`tests/docs/test_gaclose_evidence_closeout.py ->
tests/docs/test_p8_deployment_security.py`.

**Non-goals**

- No reopening of the repaired embed/consolidation script recovery once the
  live rerun has advanced beyond that seam.
- No broad reopening of earlier tests/docs or documentation-governance phases
  such as
  `tests/docs/test_mre2e_evidence_contract.py ->
  tests/docs/test_gagov_governance_contract.py` unless the refreshed rerun
  proves the active blocker requires it.
- No repo-wide lexical timeout retune unless the refreshed rerun proves this
  later tests/docs seam cannot be cleared with a narrower repair.

**Key files**

- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/plugins/python_plugin/plugin.py`
- `mcp_server/storage/git_index_manager.py`
- `mcp_server/cli/repository_commands.py`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `tests/test_dispatcher.py`
- `tests/test_git_index_manager.py`
- `tests/test_repository_commands.py`
- `tests/docs/test_semdogfood_evidence_contract.py`

**Depends on**
- SEMEMBEDCONSOL

**Produces**
- IF-0-SEMDOCTESTTAIL-1 — later tests/docs lexical recovery and evidence
  contract.

### Phase 58 — Mock Plugin Fixture Tail Recovery (SEMMOCKPLUGIN)

**Objective**

Carry the live force-full rerun beyond the later security-fixture tail exposed
after SEMDOCTESTTAIL:
`tests/security/fixtures/mock_plugin/plugin.py ->
tests/security/fixtures/mock_plugin/__init__.py`.

**Exit criteria**
- [ ] A refreshed repo-local force-full rerun on the post-SEMDOCTESTTAIL
      head either advances durably beyond
      `tests/security/fixtures/mock_plugin/plugin.py ->
      tests/security/fixtures/mock_plugin/__init__.py` or emits a truthful
      newer blocker before the 120-second watchdog expires.
- [ ] The chosen repair for the
      `tests/security/fixtures/mock_plugin/plugin.py ->
      tests/security/fixtures/mock_plugin/__init__.py` seam stays narrow,
      tested, and does not reopen the repaired
      `tests/docs/test_gaclose_evidence_closeout.py ->
      tests/docs/test_p8_deployment_security.py` boundary without direct
      evidence.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMDOCTESTTAIL rerun outcome and the final live verdict for the later
      security-fixture blocker pair.

**Scope notes**

This phase exists only if SEMDOCTESTTAIL proves the later tests/docs
`tests/docs/test_gaclose_evidence_closeout.py ->
tests/docs/test_p8_deployment_security.py` seam is cleared, but the
refreshed live rerun still terminalizes later in lexical walking on
`tests/security/fixtures/mock_plugin/plugin.py ->
tests/security/fixtures/mock_plugin/__init__.py`.

**Non-goals**

- No reopening of the repaired docs-test recovery once the live rerun has
  advanced beyond that seam.
- No broad reopening of earlier security, sandbox, or plugin-system phases
  unless the refreshed rerun proves the active blocker requires it.
- No repo-wide lexical timeout retune unless the refreshed rerun proves this
  later security-fixture seam cannot be cleared with a narrower repair.

**Key files**

- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/plugins/python_plugin/plugin.py`
- `mcp_server/storage/git_index_manager.py`
- `mcp_server/cli/repository_commands.py`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `tests/test_dispatcher.py`
- `tests/test_git_index_manager.py`
- `tests/test_repository_commands.py`
- `tests/docs/test_semdogfood_evidence_contract.py`

**Depends on**
- SEMDOCTESTTAIL

**Produces**
- IF-0-SEMMOCKPLUGIN-1 — later security-fixture lexical recovery and evidence
  contract.

### Phase 59 — Legacy Codex Phase-Loop Tail Recovery (SEMCODEXLOOPTAIL)

**Objective**

Carry the live force-full rerun beyond the later legacy `.codex/phase-loop`
JSON tail exposed after SEMMOCKPLUGIN:
`.codex/phase-loop/runs/20260424T180441Z-01-gagov-execute/launch.json ->
.codex/phase-loop/runs/20260427T071807Z-02-artpub-execute/terminal-summary.json`.

**Exit criteria**
- [ ] A refreshed repo-local force-full rerun on the post-SEMMOCKPLUGIN head
      either advances durably beyond the legacy
      `.codex/phase-loop/.../launch.json ->
      .codex/phase-loop/.../terminal-summary.json` pair or emits a truthful
      newer blocker before the 120-second watchdog expires.
- [ ] The chosen repair for the legacy `.codex/phase-loop` JSON seam stays
      narrow, tested, and does not reopen the repaired
      `tests/security/fixtures/mock_plugin/plugin.py ->
      tests/security/fixtures/mock_plugin/__init__.py` boundary without direct
      evidence.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the SEMMOCKPLUGIN
      rerun outcome and the final live verdict for the later legacy
      `.codex/phase-loop` blocker pair.

**Scope notes**

This phase exists only if SEMMOCKPLUGIN proves the later security-fixture
`tests/security/fixtures/mock_plugin/plugin.py ->
tests/security/fixtures/mock_plugin/__init__.py` seam is cleared, but the
refreshed live rerun still terminalizes later in lexical walking on a legacy
`.codex/phase-loop` runtime artifact pair such as
`.codex/phase-loop/runs/20260424T180441Z-01-gagov-execute/launch.json ->
.codex/phase-loop/runs/20260427T071807Z-02-artpub-execute/terminal-summary.json`.

**Non-goals**

- No reopening of the repaired mock-plugin fixture recovery once the live
  rerun has advanced beyond that seam.
- No broad reopening of canonical `.phase-loop/` runtime behavior unless the
  refreshed rerun proves the active blocker requires it.
- No blanket ignore for `.codex/**` unless the refreshed rerun proves the
  active blocker cannot be cleared with a narrower legacy-runtime repair.

**Key files**

- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/cli/repository_commands.py`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `tests/test_dispatcher.py`
- `tests/test_git_index_manager.py`
- `tests/test_repository_commands.py`
- `tests/docs/test_semdogfood_evidence_contract.py`

**Depends on**
- SEMMOCKPLUGIN

**Produces**
- IF-0-SEMCODEXLOOPTAIL-1 — later legacy `.codex/phase-loop` lexical recovery
  and evidence contract.

### Phase 60 — Docs Contract Tail Recovery (SEMDOCCONTRACTTAIL)

**Objective**

Carry the live force-full rerun beyond the later docs contract-test pair exposed
after SEMCODEXLOOPTAIL:
`tests/docs/test_semincr_contract.py ->
tests/docs/test_gabase_ga_readiness_contract.py`.

**Exit criteria**
- [ ] A refreshed repo-local force-full rerun on the post-SEMCODEXLOOPTAIL head
      either advances durably beyond the
      `tests/docs/test_semincr_contract.py ->
      tests/docs/test_gabase_ga_readiness_contract.py` pair or emits a truthful
      newer blocker before the 120-second watchdog expires.
- [ ] The chosen repair for the docs contract-test tail stays narrow, tested,
      and does not reopen the repaired legacy `.codex/phase-loop`
      compatibility-runtime boundary without direct evidence.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the SEMCODEXLOOPTAIL
      rerun outcome and the final live verdict for the later docs contract-test
      pair.

**Scope notes**

This phase exists only if SEMCODEXLOOPTAIL proves the legacy
`.codex/phase-loop` compatibility-runtime family is cleared, but the refreshed
live rerun still terminalizes later in lexical walking on a docs contract-test
pair such as
`tests/docs/test_semincr_contract.py ->
tests/docs/test_gabase_ga_readiness_contract.py`.

**Non-goals**

- No reopening of the repaired legacy `.codex/phase-loop` compatibility-runtime
  recovery once the live rerun has advanced beyond that family.
- No broad reopening of unrelated docs tests unless the refreshed rerun proves
  the active blocker requires them.
- No blanket `tests/docs/**/*.py` bypass unless the refreshed rerun proves the
  active blocker cannot be cleared with a narrower contract-tail repair.

**Key files**

- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/cli/repository_commands.py`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `tests/test_dispatcher.py`
- `tests/test_git_index_manager.py`
- `tests/test_repository_commands.py`
- `tests/docs/test_semdogfood_evidence_contract.py`

**Depends on**
- SEMCODEXLOOPTAIL

**Produces**
- IF-0-SEMDOCCONTRACTTAIL-1 — later docs contract-test lexical recovery and
  evidence contract.

### Phase 61 — GA Release Docs Tail Recovery (SEMGARELTAIL)

**Objective**

Carry the live force-full rerun beyond the later GA release docs contract-test
pair exposed after SEMDOCCONTRACTTAIL:
`tests/docs/test_garc_rc_soak_contract.py ->
tests/docs/test_garel_ga_release_contract.py`.

**Exit criteria**
- [ ] A refreshed repo-local force-full rerun on the post-SEMDOCCONTRACTTAIL
      head either advances durably beyond the
      `tests/docs/test_garc_rc_soak_contract.py ->
      tests/docs/test_garel_ga_release_contract.py` pair or emits a truthful
      newer blocker before the 120-second watchdog expires.
- [ ] The chosen repair for the GA release docs contract-test tail stays
      narrow, tested, and does not reopen the repaired
      `tests/docs/test_semincr_contract.py ->
      tests/docs/test_gabase_ga_readiness_contract.py` boundary without direct
      evidence.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMDOCCONTRACTTAIL rerun outcome and the final live verdict for the later
      GA release docs contract-test pair.

**Scope notes**

This phase exists only if SEMDOCCONTRACTTAIL proves the later docs
contract-test pair
`tests/docs/test_semincr_contract.py ->
tests/docs/test_gabase_ga_readiness_contract.py` is cleared, but the refreshed
live rerun still terminalizes later in lexical walking on a GA release docs
contract-test pair such as
`tests/docs/test_garc_rc_soak_contract.py ->
tests/docs/test_garel_ga_release_contract.py`.

**Non-goals**

- No reopening of the repaired SEMDOCCONTRACTTAIL docs contract recovery once
  the live rerun has advanced beyond that seam.
- No broad reopening of unrelated release docs or validation artifacts unless
  the refreshed rerun proves the active blocker requires them.
- No blanket `tests/docs/**/*.py` bypass unless the refreshed rerun proves the
  active blocker cannot be cleared with a narrower GA-release-docs repair.

**Key files**

- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/cli/repository_commands.py`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `tests/test_dispatcher.py`
- `tests/test_git_index_manager.py`
- `tests/test_repository_commands.py`
- `tests/docs/test_semdogfood_evidence_contract.py`

**Depends on**
- SEMDOCCONTRACTTAIL

**Produces**
- IF-0-SEMGARELTAIL-1 — later GA release docs contract-test lexical recovery
  and evidence contract.

### Phase 62 — Documentation Truth Tail Recovery (SEMDOCTRUTHTAIL)

**Objective**

Carry the live force-full rerun beyond the later documentation-truth and
evidence-contract pair exposed after SEMGARELTAIL:
`tests/docs/test_p23_doc_truth.py ->
tests/docs/test_semdogfood_evidence_contract.py`.

**Exit criteria**
- [ ] A refreshed repo-local force-full rerun on the post-SEMGARELTAIL head
      either advances durably beyond the
      `tests/docs/test_p23_doc_truth.py ->
      tests/docs/test_semdogfood_evidence_contract.py` pair or emits a
      truthful newer blocker before the 120-second watchdog expires.
- [ ] The chosen repair for the documentation-truth tail stays narrow, tested,
      and does not reopen the repaired
      `tests/docs/test_garc_rc_soak_contract.py ->
      tests/docs/test_garel_ga_release_contract.py` boundary without direct
      evidence.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the SEMGARELTAIL rerun
      outcome and the final live verdict for the later documentation-truth
      contract-test pair.

**Scope notes**

This phase exists only if SEMGARELTAIL proves the later GA release docs
contract-test pair
`tests/docs/test_garc_rc_soak_contract.py ->
tests/docs/test_garel_ga_release_contract.py` is cleared, but the refreshed
live rerun still terminalizes later in lexical walking on a documentation
truth and dogfood-evidence pair such as
`tests/docs/test_p23_doc_truth.py ->
tests/docs/test_semdogfood_evidence_contract.py`.

**Non-goals**

- No reopening of the repaired SEMGARELTAIL GA release docs recovery once the
  live rerun has advanced beyond that seam.
- No broad reopening of unrelated docs truth, release docs, or evidence
  artifacts unless the refreshed rerun proves the active blocker requires
  them.
- No blanket `tests/docs/**/*.py` bypass unless the refreshed rerun proves the
  active blocker cannot be cleared with a narrower documentation-truth repair.

**Key files**

- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/cli/repository_commands.py`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `tests/test_dispatcher.py`
- `tests/test_git_index_manager.py`
- `tests/test_repository_commands.py`
- `tests/docs/test_p23_doc_truth.py`
- `tests/docs/test_semdogfood_evidence_contract.py`

**Depends on**
- SEMGARELTAIL

**Produces**
- IF-0-SEMDOCTRUTHTAIL-1 — later documentation-truth lexical recovery and
  evidence contract.

### Phase 63 — Support Docs Tail Recovery (SEMSUPPORTTAIL)

**Objective**

Carry the live force-full rerun beyond the later support-docs Markdown pair
exposed after SEMDOCTRUTHTAIL:
`docs/markdown-table-of-contents.md ->
docs/SUPPORT_MATRIX.md`.

**Exit criteria**
- [ ] A refreshed repo-local force-full rerun on the post-SEMDOCTRUTHTAIL
      head either advances durably beyond the
      `docs/markdown-table-of-contents.md ->
      docs/SUPPORT_MATRIX.md` pair or emits a truthful newer blocker before
      the 120-second watchdog expires.
- [ ] The chosen repair for the support-docs tail stays narrow, tested, and
      does not reopen the repaired
      `tests/docs/test_p23_doc_truth.py ->
      tests/docs/test_semdogfood_evidence_contract.py` boundary without
      direct evidence.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the SEMDOCTRUTHTAIL
      rerun outcome and the final live verdict for the later support-docs
      Markdown pair.

**Scope notes**

This phase exists only if SEMDOCTRUTHTAIL proves the later documentation
truth and dogfood-evidence pair
`tests/docs/test_p23_doc_truth.py ->
tests/docs/test_semdogfood_evidence_contract.py` is cleared, but the
refreshed live rerun still terminalizes later in lexical walking on a
support-docs Markdown pair such as
`docs/markdown-table-of-contents.md ->
docs/SUPPORT_MATRIX.md`.

**Non-goals**

- No reopening of the repaired SEMDOCTRUTHTAIL docs-truth recovery once the
  live rerun has advanced beyond that seam.
- No broad reopening of unrelated docs truth, agent docs, release docs, or
  evidence artifacts unless the refreshed rerun proves the active blocker
  requires them.
- No blanket `docs/*.md` or support-docs bypass unless the refreshed rerun
  proves the active blocker cannot be cleared with a narrower Markdown-path
  repair.

**Key files**

- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/cli/repository_commands.py`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `docs/markdown-table-of-contents.md`
- `docs/SUPPORT_MATRIX.md`
- `tests/test_dispatcher.py`
- `tests/test_git_index_manager.py`
- `tests/test_repository_commands.py`
- `tests/docs/test_p23_doc_truth.py`
- `tests/docs/test_semdogfood_evidence_contract.py`

**Depends on**
- SEMDOCTRUTHTAIL

**Produces**
- IF-0-SEMSUPPORTTAIL-1 — later support-docs Markdown lexical recovery and
  evidence contract.

### Phase 64 — Historical V1 Plan Tail Recovery (SEMV1PLANTAIL)

**Objective**

Carry the live force-full rerun beyond the later historical v1 phase-plan pair
exposed after SEMSUPPORTTAIL:
`plans/phase-plan-v1-p13.md ->
plans/phase-plan-v1-p3.md`.

**Exit criteria**
- [ ] A refreshed repo-local force-full rerun on the post-SEMSUPPORTTAIL head
      either advances durably beyond the
      `plans/phase-plan-v1-p13.md ->
      plans/phase-plan-v1-p3.md` pair or emits a truthful newer blocker before
      the 120-second watchdog expires.
- [ ] The chosen repair for the historical v1 plan tail stays narrow, tested,
      and does not reopen the repaired
      `docs/markdown-table-of-contents.md ->
      docs/SUPPORT_MATRIX.md` boundary without direct evidence.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the SEMSUPPORTTAIL
      rerun outcome and the final live verdict for the later historical v1
      phase-plan pair.

**Scope notes**

This phase exists only if SEMSUPPORTTAIL proves the support-docs Markdown pair
`docs/markdown-table-of-contents.md ->
docs/SUPPORT_MATRIX.md` is cleared, but the refreshed live rerun still
terminalizes later in lexical walking on a historical v1 phase-plan pair such
as `plans/phase-plan-v1-p13.md ->
plans/phase-plan-v1-p3.md`.

**Non-goals**

- No reopening of the repaired SEMSUPPORTTAIL support-doc recovery once the
  live rerun has advanced beyond that seam.
- No broad reopening of unrelated plan artifacts, roadmap docs, or evidence
  artifacts unless the refreshed rerun proves the active blocker requires
  them.
- No blanket `plans/phase-plan-v1-*.md` bypass unless the refreshed rerun
  proves the active blocker cannot be cleared with a narrower Markdown-path
  repair.

**Key files**

- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/plugins/markdown_plugin/plugin.py`
- `mcp_server/cli/repository_commands.py`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `plans/phase-plan-v1-p13.md`
- `plans/phase-plan-v1-p3.md`
- `tests/test_dispatcher.py`
- `tests/test_git_index_manager.py`
- `tests/test_repository_commands.py`
- `tests/docs/test_semdogfood_evidence_contract.py`

**Depends on**
- SEMSUPPORTTAIL

**Produces**
- IF-0-SEMV1PLANTAIL-1 — later historical v1 phase-plan lexical recovery and
  evidence contract.

### Phase 65 — SEMJEDI/P4 Tail Recovery (SEMJEDIP4TAIL)

**Objective**

Carry the live force-full rerun beyond the later mixed-generation phase-plan
pair exposed after SEMV1PLANTAIL:
`plans/phase-plan-v7-SEMJEDI.md ->
plans/phase-plan-v1-p4.md`.

**Exit criteria**
- [ ] A refreshed repo-local force-full rerun on the post-SEMV1PLANTAIL head
      either advances durably beyond the
      `plans/phase-plan-v7-SEMJEDI.md ->
      plans/phase-plan-v1-p4.md` pair or emits a truthful newer blocker before
      the 120-second watchdog expires.
- [ ] The chosen repair for the SEMJEDI/P4 tail stays narrow, tested, and
      does not reopen the repaired
      `plans/phase-plan-v1-p13.md ->
      plans/phase-plan-v1-p3.md` boundary without direct evidence.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the SEMV1PLANTAIL
      rerun outcome and the final live verdict for the later
      `plans/phase-plan-v7-SEMJEDI.md ->
      plans/phase-plan-v1-p4.md` phase-plan pair.

**Scope notes**

This phase exists only if SEMV1PLANTAIL proves the later historical v1
phase-plan pair
`plans/phase-plan-v1-p13.md ->
plans/phase-plan-v1-p3.md` is cleared, but the refreshed live rerun still
terminalizes later in lexical walking on a mixed-generation phase-plan pair
such as `plans/phase-plan-v7-SEMJEDI.md ->
plans/phase-plan-v1-p4.md`.

**Non-goals**

- No reopening of the repaired SEMV1PLANTAIL historical-v1 plan recovery once
  the live rerun has advanced beyond that seam.
- No broad reopening of unrelated plan artifacts, roadmap docs, or evidence
  artifacts unless the refreshed rerun proves the active blocker requires
  them.
- No blanket `plans/phase-plan-*.md` bypass unless the refreshed rerun proves
  the active blocker cannot be cleared with a narrower Markdown-path repair.

**Key files**

- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/plugins/markdown_plugin/plugin.py`
- `mcp_server/cli/repository_commands.py`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `plans/phase-plan-v7-SEMJEDI.md`
- `plans/phase-plan-v1-p4.md`
- `tests/test_dispatcher.py`
- `tests/test_git_index_manager.py`
- `tests/test_repository_commands.py`
- `tests/docs/test_semdogfood_evidence_contract.py`

**Depends on**
- SEMV1PLANTAIL

**Produces**
- IF-0-SEMJEDIP4TAIL-1 — later SEMJEDI/P4 lexical recovery and evidence
  contract.

### Phase 66 — Crossplans Dogfood Tail Recovery (SEMCROSSDOGTAIL)

**Objective**

Carry the live force-full rerun beyond the later modern v7 phase-plan pair
exposed after SEMJEDIP4TAIL:
`plans/phase-plan-v7-SEMCROSSPLANS.md ->
plans/phase-plan-v7-SEMDOGFOOD.md`.

**Exit criteria**
- [ ] A refreshed repo-local force-full rerun on the post-SEMJEDIP4TAIL head
      either advances durably beyond the
      `plans/phase-plan-v7-SEMCROSSPLANS.md ->
      plans/phase-plan-v7-SEMDOGFOOD.md` pair or emits a truthful newer
      blocker before the 120-second watchdog expires.
- [ ] The chosen repair for the SEMCROSSPLANS/SEMDOGFOOD tail stays narrow,
      tested, and does not reopen the repaired
      `plans/phase-plan-v7-SEMJEDI.md ->
      plans/phase-plan-v1-p4.md` boundary without direct evidence.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the SEMJEDIP4TAIL
      rerun outcome and the final live verdict for the later
      `plans/phase-plan-v7-SEMCROSSPLANS.md ->
      plans/phase-plan-v7-SEMDOGFOOD.md` phase-plan pair.

**Scope notes**

This phase exists only if SEMJEDIP4TAIL proves the later mixed-generation
phase-plan pair
`plans/phase-plan-v7-SEMJEDI.md ->
plans/phase-plan-v1-p4.md` is cleared, but the refreshed live rerun still
terminalizes later in lexical walking on a modern v7 phase-plan pair such as
`plans/phase-plan-v7-SEMCROSSPLANS.md ->
plans/phase-plan-v7-SEMDOGFOOD.md`.

**Non-goals**

- No reopening of the repaired SEMJEDIP4TAIL mixed-generation plan recovery
  once the live rerun has advanced beyond that seam.
- No broad reopening of unrelated roadmap, evidence, or semantic-onboarding
  artifacts unless the refreshed rerun proves the active blocker requires
  them.
- No blanket `plans/phase-plan-v7-*.md` bypass unless the refreshed rerun
  proves the active blocker cannot be cleared with a narrower Markdown-path
  repair.

**Key files**

- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/plugins/markdown_plugin/plugin.py`
- `mcp_server/cli/repository_commands.py`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `plans/phase-plan-v7-SEMCROSSPLANS.md`
- `plans/phase-plan-v7-SEMDOGFOOD.md`
- `tests/test_dispatcher.py`
- `tests/test_git_index_manager.py`
- `tests/test_repository_commands.py`
- `tests/docs/test_semdogfood_evidence_contract.py`

**Depends on**
- SEMJEDIP4TAIL

**Produces**
- IF-0-SEMCROSSDOGTAIL-1 — later SEMCROSSPLANS/SEMDOGFOOD lexical recovery
  and evidence contract.

### Phase 67 — Optimized Final Report Tail Recovery (SEMOPTREPORTTAIL)

**Objective**

Carry the live force-full rerun beyond the later generated optimized-report
pair exposed after SEMCROSSDOGTAIL:
`final_optimized_report_final_report_1750958096/final_report_data.json ->
final_optimized_report_final_report_1750958096/FINAL_OPTIMIZED_ANALYSIS_REPORT.md`.

**Exit criteria**
- [ ] A refreshed repo-local force-full rerun on the post-SEMCROSSDOGTAIL
      head either advances durably beyond the
      `final_optimized_report_final_report_1750958096/final_report_data.json ->
      final_optimized_report_final_report_1750958096/FINAL_OPTIMIZED_ANALYSIS_REPORT.md`
      pair or emits a truthful newer blocker before the 120-second watchdog
      expires.
- [ ] The chosen repair for the generated optimized-report tail stays narrow,
      tested, and does not reopen the repaired
      `plans/phase-plan-v7-SEMCROSSPLANS.md ->
      plans/phase-plan-v7-SEMDOGFOOD.md` boundary without direct evidence.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the SEMCROSSDOGTAIL
      rerun outcome and the final live verdict for the generated optimized
      report pair.

**Scope notes**

This phase exists only if SEMCROSSDOGTAIL proves the later modern v7
phase-plan pair
`plans/phase-plan-v7-SEMCROSSPLANS.md ->
plans/phase-plan-v7-SEMDOGFOOD.md` is cleared, but the refreshed live rerun
still terminalizes later in lexical walking on the generated optimized-report
pair
`final_optimized_report_final_report_1750958096/final_report_data.json ->
final_optimized_report_final_report_1750958096/FINAL_OPTIMIZED_ANALYSIS_REPORT.md`.

**Non-goals**

- No reopening of the repaired SEMCROSSDOGTAIL phase-plan recovery once the
  live rerun has advanced beyond that seam.
- No blanket ignore or bypass for generated optimized reports unless the
  refreshed rerun proves the active blocker cannot be cleared with a narrower
  exact-path or exact-family contract.
- No reopening of unrelated semantic-stage or roadmap work unless the
  refreshed rerun proves the active blocker has moved again.

**Key files**

- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/cli/repository_commands.py`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `tests/test_dispatcher.py`
- `tests/test_git_index_manager.py`
- `tests/test_repository_commands.py`
- `tests/docs/test_semdogfood_evidence_contract.py`
- `final_optimized_report_final_report_1750958096/final_report_data.json`
- `final_optimized_report_final_report_1750958096/FINAL_OPTIMIZED_ANALYSIS_REPORT.md`

**Depends on**
- SEMCROSSDOGTAIL

**Produces**
- IF-0-SEMOPTREPORTTAIL-1 — generated optimized-report lexical recovery and
  evidence contract.

### Phase 68 — Fixture Tail Recovery (SEMFIXTURETAIL)

**Objective**

Carry the live force-full rerun beyond the later fixture seam exposed after
SEMOPTREPORTTAIL:
`tests/fixtures/multi_repo.py ->
tests/fixtures/files/test_files/example.c`.

**Exit criteria**
- [ ] A refreshed repo-local force-full rerun on the post-SEMOPTREPORTTAIL
      head either advances durably beyond the
      `tests/fixtures/multi_repo.py ->
      tests/fixtures/files/test_files/example.c`
      pair or emits a truthful newer blocker before the 120-second watchdog
      expires.
- [ ] The chosen repair for the fixture tail stays narrow, tested, and does
      not reopen the repaired
      `final_optimized_report_final_report_1750958096/final_report_data.json ->
      final_optimized_report_final_report_1750958096/FINAL_OPTIMIZED_ANALYSIS_REPORT.md`
      boundary without direct evidence.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the SEMOPTREPORTTAIL
      rerun outcome and the final live verdict for the fixture pair.

**Scope notes**

This phase exists only if SEMOPTREPORTTAIL proves the generated optimized-report
pair is cleared, but the refreshed live rerun still terminalizes later in
lexical walking on the fixture pair
`tests/fixtures/multi_repo.py ->
tests/fixtures/files/test_files/example.c`.

**Non-goals**

- No reopening of the repaired SEMOPTREPORTTAIL generated-report recovery once
  the live rerun has advanced beyond that seam.
- No blanket ignore or bypass for all fixture files unless the refreshed rerun
  proves the active blocker cannot be cleared with a narrower exact-path or
  exact-pair contract.
- No reopening of unrelated semantic-stage or roadmap work unless the
  refreshed rerun proves the active blocker has moved again.

**Key files**

- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/cli/repository_commands.py`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `tests/test_dispatcher.py`
- `tests/test_git_index_manager.py`
- `tests/test_repository_commands.py`
- `tests/docs/test_semdogfood_evidence_contract.py`
- `tests/fixtures/multi_repo.py`
- `tests/fixtures/files/test_files/example.c`

**Depends on**
- SEMOPTREPORTTAIL

**Produces**
- IF-0-SEMFIXTURETAIL-1 — fixture-pair lexical recovery and evidence
  contract.

### Phase 69 — AI Docs Overview Tail Recovery (SEMAIOVERVIEWTAIL)

**Objective**

Carry the live force-full rerun beyond the later `ai_docs` overview seam
exposed after SEMFIXTURETAIL:
`ai_docs/black_isort_overview.md ->
ai_docs/sqlite_fts5_overview.md`.

**Exit criteria**
- [ ] A refreshed repo-local force-full rerun on the post-SEMFIXTURETAIL head
      either advances durably beyond the
      `ai_docs/black_isort_overview.md ->
      ai_docs/sqlite_fts5_overview.md`
      pair or emits a truthful newer blocker before the 120-second watchdog
      expires.
- [ ] The chosen repair for the later `ai_docs` overview seam stays narrow,
      tested, and does not reopen the already-cleared
      `tests/fixtures/multi_repo.py ->
      tests/fixtures/files/test_files/example.c`
      boundary without direct evidence.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the SEMFIXTURETAIL
      rerun outcome and the final live verdict for the later `ai_docs`
      overview pair.

**Scope notes**

This phase exists only if SEMFIXTURETAIL proves the fixture pair is cleared,
but the refreshed live rerun still terminalizes later in lexical walking on
`ai_docs/black_isort_overview.md ->
ai_docs/sqlite_fts5_overview.md`.

**Non-goals**

- No reopening of the cleared fixture-tail recovery once the live rerun has
  advanced beyond
  `tests/fixtures/multi_repo.py ->
  tests/fixtures/files/test_files/example.c`.
- No blanket reopening of the earlier `ai_docs/*_overview.md` boundary unless
  the refreshed rerun proves the active blocker cannot be cleared with a
  narrower exact-pair contract.
- No reopening of unrelated semantic-stage or roadmap work unless the
  refreshed rerun proves the active blocker has moved again.

**Key files**

- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/cli/repository_commands.py`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `tests/test_dispatcher.py`
- `tests/test_git_index_manager.py`
- `tests/test_repository_commands.py`
- `tests/docs/test_semdogfood_evidence_contract.py`
- `ai_docs/black_isort_overview.md`
- `ai_docs/sqlite_fts5_overview.md`

**Depends on**
- SEMFIXTURETAIL

**Produces**
- IF-0-SEMAIOVERVIEWTAIL-1 — exact later `ai_docs` overview recovery and
  evidence contract.

### Phase 70 — Test-Repo Index Script Tail Recovery (SEMTESTREPOINDEXTAIL)

**Objective**

Carry the live force-full rerun beyond the later Python script seam exposed
after SEMAIOVERVIEWTAIL:
`scripts/check_test_index_schema.py ->
scripts/ensure_test_repos_indexed.py`.

**Exit criteria**
- [ ] A refreshed repo-local force-full rerun on the post-SEMAIOVERVIEWTAIL
      head either advances durably beyond the
      `scripts/check_test_index_schema.py ->
      scripts/ensure_test_repos_indexed.py`
      pair or emits a truthful newer blocker before the 120-second watchdog
      expires.
- [ ] The chosen repair for the later test-repo index script seam stays
      narrow, tested, and does not reopen the already-cleared
      `ai_docs/black_isort_overview.md ->
      ai_docs/sqlite_fts5_overview.md`
      boundary without direct evidence.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMAIOVERVIEWTAIL rerun outcome and the final live verdict for the later
      test-repo index script pair.

**Scope notes**

This phase exists only if SEMAIOVERVIEWTAIL proves the later `ai_docs`
overview pair is cleared, but the refreshed live rerun still terminalizes
later in lexical walking on
`scripts/check_test_index_schema.py ->
scripts/ensure_test_repos_indexed.py`.

**Non-goals**

- No reopening of the cleared `ai_docs` overview recovery once the live rerun
  has advanced beyond
  `ai_docs/black_isort_overview.md ->
  ai_docs/sqlite_fts5_overview.md`.
- No blanket reopening of unrelated script families unless the refreshed
  rerun proves the active blocker cannot be cleared with a narrower exact-path
  or exact-pair contract.
- No reopening of unrelated semantic-stage or roadmap work unless the
  refreshed rerun proves the active blocker has moved again.

**Key files**

- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/cli/repository_commands.py`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `tests/test_dispatcher.py`
- `tests/test_git_index_manager.py`
- `tests/test_repository_commands.py`
- `tests/docs/test_semdogfood_evidence_contract.py`
- `scripts/check_test_index_schema.py`
- `scripts/ensure_test_repos_indexed.py`

**Depends on**
- SEMAIOVERVIEWTAIL

**Produces**
- IF-0-SEMTESTREPOINDEXTAIL-1 — exact later test-repo index script recovery
  and evidence contract.

### Phase 71 — Missing-Repo Semantic Index Script Tail Recovery (SEMMISSINGREPOSEMTAIL)

**Objective**

Carry the live force-full rerun beyond the later Python script seam exposed
after SEMTESTREPOINDEXTAIL:
`scripts/index_missing_repos_semantic.py ->
scripts/identify_working_indexes.py`.

**Exit criteria**
- [ ] A refreshed repo-local force-full rerun on the post-SEMTESTREPOINDEXTAIL
      head either advances durably beyond the
      `scripts/index_missing_repos_semantic.py ->
      scripts/identify_working_indexes.py`
      pair or emits a truthful newer blocker before the 120-second watchdog
      expires.
- [ ] The chosen repair for the later missing-repo semantic index script seam
      stays narrow, tested, and does not reopen the already-cleared
      `scripts/check_test_index_schema.py ->
      scripts/ensure_test_repos_indexed.py`
      boundary without direct evidence.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMTESTREPOINDEXTAIL rerun outcome and the final live verdict for the
      later missing-repo semantic index script pair.

**Scope notes**

This phase exists only if SEMTESTREPOINDEXTAIL proves the later test-repo
index script pair is cleared, but the refreshed live rerun still terminalizes
later in lexical walking on
`scripts/index_missing_repos_semantic.py ->
scripts/identify_working_indexes.py`.

**Non-goals**

- No reopening of the cleared test-repo index script recovery once the live
  rerun has advanced beyond
  `scripts/check_test_index_schema.py ->
  scripts/ensure_test_repos_indexed.py`.
- No blanket reopening of unrelated script families unless the refreshed
  rerun proves the active blocker cannot be cleared with a narrower exact-path
  or exact-pair contract.
- No reopening of unrelated semantic-stage or roadmap work unless the
  refreshed rerun proves the active blocker has moved again.

**Key files**

- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/cli/repository_commands.py`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `tests/test_dispatcher.py`
- `tests/test_git_index_manager.py`
- `tests/test_repository_commands.py`
- `tests/docs/test_semdogfood_evidence_contract.py`
- `scripts/index_missing_repos_semantic.py`
- `scripts/identify_working_indexes.py`

**Depends on**
- SEMTESTREPOINDEXTAIL

**Produces**
- IF-0-SEMMISSINGREPOSEMTAIL-1 — exact later missing-repo semantic index
  script recovery and evidence contract.

### Phase 72 — Utility Script Verification Tail Recovery (SEMUTILVERIFYTAIL)

**Objective**

Carry the live force-full rerun beyond the later Python utility-script seam
exposed after SEMMISSINGREPOSEMTAIL:
`scripts/utilities/prepare_index_for_upload.py ->
scripts/utilities/verify_tool_usage.py`.

**Exit criteria**
- [ ] A refreshed repo-local force-full rerun on the post-SEMMISSINGREPOSEMTAIL
      head either advances durably beyond the
      `scripts/utilities/prepare_index_for_upload.py ->
      scripts/utilities/verify_tool_usage.py`
      pair or emits a truthful newer blocker before the 120-second watchdog
      expires.
- [ ] The chosen repair for the later utility-script verification seam stays
      narrow, tested, and does not reopen the already-cleared
      `scripts/index_missing_repos_semantic.py ->
      scripts/identify_working_indexes.py`
      boundary without direct evidence.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMMISSINGREPOSEMTAIL rerun outcome and the final live verdict for the
      later utility-script verification pair.

**Scope notes**

This phase exists only if SEMMISSINGREPOSEMTAIL proves the later missing-repo
semantic index script pair is cleared, but the refreshed live rerun still
terminalizes later in lexical walking on
`scripts/utilities/prepare_index_for_upload.py ->
scripts/utilities/verify_tool_usage.py`.

**Non-goals**

- No reopening of the cleared missing-repo semantic index script recovery once
  the live rerun has advanced beyond
  `scripts/index_missing_repos_semantic.py ->
  scripts/identify_working_indexes.py`.
- No blanket reopening of unrelated utility or script families unless the
  refreshed rerun proves the active blocker cannot be cleared with a narrower
  exact-path or exact-pair contract.
- No reopening of unrelated semantic-stage or roadmap work unless the
  refreshed rerun proves the active blocker has moved again.

**Key files**

- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/cli/repository_commands.py`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `tests/test_dispatcher.py`
- `tests/test_git_index_manager.py`
- `tests/test_repository_commands.py`
- `tests/docs/test_semdogfood_evidence_contract.py`
- `scripts/utilities/prepare_index_for_upload.py`
- `scripts/utilities/verify_tool_usage.py`

**Depends on**
- SEMMISSINGREPOSEMTAIL

**Produces**
- IF-0-SEMUTILVERIFYTAIL-1 — exact later utility-script verification recovery
  and evidence contract.

### Phase 73 — Qdrant Mapping And Claude Report Tail Recovery (SEMQDRANTREPORTTAIL)

**Objective**

Carry the live force-full rerun beyond the later exact Python script seam
exposed after SEMUTILVERIFYTAIL:
`scripts/map_repos_to_qdrant.py ->
scripts/create_claude_code_aware_report.py`.

**Exit criteria**
- [ ] A refreshed repo-local force-full rerun on the post-SEMUTILVERIFYTAIL
      head either advances durably beyond the
      `scripts/map_repos_to_qdrant.py ->
      scripts/create_claude_code_aware_report.py`
      pair or emits a truthful newer blocker before the 120-second watchdog
      expires.
- [ ] The chosen repair for the later Qdrant/report script seam stays narrow,
      tested, and does not reopen the already-cleared
      `scripts/utilities/prepare_index_for_upload.py ->
      scripts/utilities/verify_tool_usage.py`
      boundary without direct evidence.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMUTILVERIFYTAIL rerun outcome and the final live verdict for the later
      Qdrant/report script pair.

**Scope notes**

This phase exists only if SEMUTILVERIFYTAIL proves the later utility-script
verification pair is cleared, but the refreshed live rerun still terminalizes
later in lexical walking on
`scripts/map_repos_to_qdrant.py ->
scripts/create_claude_code_aware_report.py`.

**Non-goals**

- No reopening of the cleared utility-script verification recovery once the
  live rerun has advanced beyond
  `scripts/utilities/prepare_index_for_upload.py ->
  scripts/utilities/verify_tool_usage.py`.
- No blanket reopening of unrelated script families unless the refreshed rerun
  proves the active blocker cannot be cleared with a narrower exact-path or
  exact-pair contract.
- No reopening of unrelated semantic-stage or release work unless the
  refreshed rerun proves the active blocker has moved again.

**Key files**

- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/cli/repository_commands.py`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `tests/test_dispatcher.py`
- `tests/test_git_index_manager.py`
- `tests/test_repository_commands.py`
- `tests/docs/test_semdogfood_evidence_contract.py`
- `scripts/map_repos_to_qdrant.py`
- `scripts/create_claude_code_aware_report.py`

**Depends on**
- SEMUTILVERIFYTAIL

**Produces**
- IF-0-SEMQDRANTREPORTTAIL-1 — exact later Qdrant/report script recovery and
  evidence contract.

### Phase 74 — Optimized Analysis Upload Tail Recovery (SEMOPTUPLOADTAIL)

**Objective**

Carry the live force-full rerun beyond the later exact Python script seam
exposed after SEMQDRANTREPORTTAIL:
`scripts/execute_optimized_analysis.py ->
scripts/index-artifact-upload-v2.py`.

**Exit criteria**
- [ ] A refreshed repo-local force-full rerun on the post-SEMQDRANTREPORTTAIL
      head either advances durably beyond the
      `scripts/execute_optimized_analysis.py ->
      scripts/index-artifact-upload-v2.py`
      pair or emits a truthful newer blocker before the 120-second watchdog
      expires.
- [ ] The chosen repair for the later optimized-analysis/upload script seam
      stays narrow, tested, and does not reopen the already-cleared
      `scripts/map_repos_to_qdrant.py ->
      scripts/create_claude_code_aware_report.py`
      boundary without direct evidence.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMQDRANTREPORTTAIL rerun outcome and the final live verdict for the
      later optimized-analysis/upload script pair.

**Scope notes**

This phase exists only if SEMQDRANTREPORTTAIL proves the later Qdrant/report
pair is cleared, but the refreshed live rerun still terminalizes later in
lexical walking on
`scripts/execute_optimized_analysis.py ->
scripts/index-artifact-upload-v2.py`.

**Non-goals**

- No reopening of the cleared Qdrant/report recovery once the live rerun has
  advanced beyond
  `scripts/map_repos_to_qdrant.py ->
  scripts/create_claude_code_aware_report.py`.
- No blanket reopening of unrelated script families unless the refreshed rerun
  proves the active blocker cannot be cleared with a narrower exact-path or
  exact-pair contract.
- No reopening of unrelated semantic-stage or release work unless the
  refreshed rerun proves the active blocker has moved again.

**Key files**

- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/cli/repository_commands.py`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `tests/test_dispatcher.py`
- `tests/test_git_index_manager.py`
- `tests/test_repository_commands.py`
- `tests/docs/test_semdogfood_evidence_contract.py`
- `scripts/execute_optimized_analysis.py`
- `scripts/index-artifact-upload-v2.py`

**Depends on**
- SEMQDRANTREPORTTAIL

**Produces**
- IF-0-SEMOPTUPLOADTAIL-1 — exact later optimized-analysis/upload script
  recovery and evidence contract.

### Phase 75 — Edit Analysis And Retrieval Tail Recovery (SEMEDITRETRIEVALTAIL)

**Objective**

Carry the live force-full rerun beyond the later exact Python script seam
exposed after SEMOPTUPLOADTAIL:
`scripts/analyze_claude_code_edits.py ->
scripts/verify_mcp_retrieval.py`.

**Exit criteria**
- [ ] A refreshed repo-local force-full rerun on the post-SEMOPTUPLOADTAIL
      head either advances durably beyond the
      `scripts/analyze_claude_code_edits.py ->
      scripts/verify_mcp_retrieval.py`
      pair or emits a truthful newer blocker before the 120-second watchdog
      expires.
- [ ] The chosen repair for the later edit-analysis/retrieval script seam
      stays narrow, tested, and does not reopen the already-cleared
      `scripts/execute_optimized_analysis.py ->
      scripts/index-artifact-upload-v2.py`
      boundary without direct evidence.
- [ ] `docs/status/SEMANTIC_DOGFOOD_REBUILD.md` records the
      SEMOPTUPLOADTAIL rerun outcome and the final live verdict for the later
      edit-analysis/retrieval script pair.

**Scope notes**

This phase exists only if SEMOPTUPLOADTAIL proves the later
optimized-analysis/upload pair is cleared, but the refreshed live rerun still
terminalizes later in lexical walking on
`scripts/analyze_claude_code_edits.py ->
scripts/verify_mcp_retrieval.py`.

**Non-goals**

- No reopening of the cleared optimized-analysis/upload recovery once the live
  rerun has advanced beyond
  `scripts/execute_optimized_analysis.py ->
  scripts/index-artifact-upload-v2.py`.
- No blanket reopening of unrelated script families unless the refreshed rerun
  proves the active blocker cannot be cleared with a narrower exact-path or
  exact-pair contract.
- No reopening of unrelated semantic-stage or release work unless the
  refreshed rerun proves the active blocker has moved again.

**Key files**

- `mcp_server/dispatcher/dispatcher_enhanced.py`
- `mcp_server/cli/repository_commands.py`
- `docs/status/SEMANTIC_DOGFOOD_REBUILD.md`
- `tests/test_dispatcher.py`
- `tests/test_git_index_manager.py`
- `tests/test_repository_commands.py`
- `tests/docs/test_semdogfood_evidence_contract.py`
- `scripts/analyze_claude_code_edits.py`
- `scripts/verify_mcp_retrieval.py`

**Depends on**
- SEMOPTUPLOADTAIL

**Produces**
- IF-0-SEMEDITRETRIEVALTAIL-1 — exact later edit-analysis/retrieval script
  recovery and evidence contract.

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
  -> SEMAGENTS
  -> SEMREADME
  -> SEMCLOSEOUT
  -> SEMTIMEOUT
  -> SEMPASSSTALL
  -> SEMCALLTIME
  -> SEMCANCEL
  -> SEMEXITTRACE
  -> SEMFASTREPORT
  -> SEMPYTESTOVERVIEW
  -> SEMVISUALREPORT
  -> SEMJEDI
  -> SEMTRACEFRESHNESS
  -> SEMDEVCONTAINER
  -> SEMPUBLISHRACE
  -> SEMDEVREBOUND
  -> SEMSCRIPTREBOUND
  -> SEMDISKIO
  -> SEMDEVSTALE
  -> SEMTESTSTALE
  -> SEMSCRIPTABORT
  -> SEMROOTTESTABORT
  -> SEMDEVRELAPSE
  -> SEMWALKGAP
  -> SEMQUICKCHARTS
  -> SEMVALIDEVIDENCE
  -> SEMBENCHDOCS
  -> SEMARCHIVEWALKGAP
  -> SEMDOCGOV
  -> SEMCLAUDECMDS
  -> SEMSCRIPTLANGS
  -> SEMPHASEPLANS
  -> SEMCROSSPLANS
  -> SEMPHASETAIL
  -> SEMLEGACYPLANS
  -> SEMMIXEDPHASETAIL
  -> SEMPREUPGRADETAIL
  -> SEMVERIFYSIMTAIL
  -> SEMEMBEDCONSOL
  -> SEMDOCTESTTAIL
  -> SEMMOCKPLUGIN
  -> SEMCODEXLOOPTAIL
  -> SEMDOCCONTRACTTAIL
  -> SEMGARELTAIL
  -> SEMDOCTRUTHTAIL
  -> SEMSUPPORTTAIL
  -> SEMV1PLANTAIL
  -> SEMJEDIP4TAIL
  -> SEMCROSSDOGTAIL
  -> SEMOPTREPORTTAIL
  -> SEMFIXTURETAIL
  -> SEMAIOVERVIEWTAIL
  -> SEMTESTREPOINDEXTAIL
  -> SEMMISSINGREPOSEMTAIL
  -> SEMUTILVERIFYTAIL
  -> SEMQDRANTREPORTTAIL
  -> SEMOPTUPLOADTAIL
  -> SEMEDITRETRIEVALTAIL
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
- SEMPYTESTOVERVIEW should amend the roadmap immediately if the live rerun
  clears `ai_docs/pytest_overview.md` and exposes a later exact lexical seam.
- SEMVISUALREPORT should amend the roadmap immediately if the live rerun clears
  `scripts/create_multi_repo_visual_report.py` and exposes a later exact
  lexical seam such as `ai_docs/jedi.md`.
- SEMJEDI should amend the roadmap immediately if the live rerun clears
  `ai_docs/jedi.md` but exposes a later exact blocker or a trace-freshness
  failure that changes the next downstream phase.
- SEMDEVREBOUND should amend the roadmap immediately if the live rerun clears
  `.devcontainer/devcontainer.json` but exposes a later exact blocker such as
  `scripts/quick_mcp_vs_native_validation.py`.
- SEMSCRIPTREBOUND should amend the roadmap immediately if the live rerun
  clears `scripts/quick_mcp_vs_native_validation.py` but exposes a later
  semantic closeout blocker such as `disk I/O error` during
  `force_full_failed`.
- SEMDISKIO should amend the roadmap immediately if the refreshed live rerun
  fails to reach semantic closeout on the current head and instead leaves a
  renewed stale-running lexical trace, because the next repair is then no
  longer a storage-closeout slice.
- SEMSCRIPTABORT should amend the roadmap immediately if the refreshed live
  rerun clears `scripts/run_test_batch.py ->
  scripts/validate_mcp_comprehensive.py` but exposes a later exact blocker
  such as `tests/root_tests/test_voyage_api.py ->
  tests/root_tests/run_reranking_tests.py`.
- SEMROOTTESTABORT should amend the roadmap immediately if the refreshed live
  rerun on the new head fails to reach the later root-test pair and instead
  re-anchors earlier on `.devcontainer/devcontainer.json`, because the next
  repair is then no longer root-test-local and any older downstream plan is
  stale.
- SEMDEVRELAPSE should amend the roadmap immediately if the refreshed live
  rerun still terminalizes on the same-file
  `.devcontainer/devcontainer.json` marker but walk-order evidence shows the
  next unexplained gap sits in the long post-devcontainer tail, because the
  next repair is then no longer devcontainer-file-local and any older
  downstream assumption is stale.
- SEMWALKGAP should amend the roadmap immediately if the refreshed live rerun
  clears the post-devcontainer ignore tail but exposes a later exact lexical
  blocker such as
  `mcp_server/visualization/__init__.py ->
  mcp_server/visualization/quick_charts.py`.
- SEMVALIDEVIDENCE should amend the roadmap immediately if the refreshed live
  rerun clears the validation-doc pair but exposes a later exact lexical
  blocker such as
  `docs/benchmarks/mcp_vs_native_benchmark_fullrepo_fireworks_qwen_voyage_local_iter5_rerun.md ->
  docs/benchmarks/production_benchmark.md`.
- SEMBENCHDOCS should amend the roadmap immediately if the refreshed live
  rerun clears the benchmark-doc pair but still terminalizes later in lexical
  walking with `last_progress_path` at
  `analysis_archive/scripts_archive/scripts_test_files/verify_mcp_fix.py`
  and no surviving later `in_flight_path`, because the next repair is then an
  archive-tail walk-gap slice rather than a benchmark-doc-local blocker.
- SEMPHASEPLANS should amend the roadmap immediately if the refreshed live
  rerun clears
  `plans/phase-plan-v7-SEMPREFLIGHT.md ->
  plans/phase-plan-v7-SEMDOCGOV.md` but exposes a later exact blocker such as
  `plans/phase-plan-v5-garecut.md ->
  plans/phase-plan-v7-SEMWALKGAP.md`.
- SEMCROSSPLANS should amend the roadmap immediately if the refreshed live
  rerun clears
  `plans/phase-plan-v5-garecut.md ->
  plans/phase-plan-v7-SEMWALKGAP.md` but exposes a later exact blocker such as
  `plans/phase-plan-v7-SEMSYNCFIX.md ->
  plans/phase-plan-v7-SEMVISUALREPORT.md`.
- SEMPHASETAIL should amend the roadmap immediately if the refreshed live
  rerun clears
  `plans/phase-plan-v7-SEMSYNCFIX.md ->
  plans/phase-plan-v7-SEMVISUALREPORT.md` but exposes a later exact blocker
  such as
  `plans/phase-plan-v6-WATCH.md ->
  plans/phase-plan-v1-p19.md`.
- SEMLEGACYPLANS should amend the roadmap immediately if the refreshed live
  rerun clears
  `plans/phase-plan-v6-WATCH.md ->
  plans/phase-plan-v1-p19.md` but exposes a later exact blocker such as
  `plans/phase-plan-v7-SEMPHASETAIL.md ->
  plans/phase-plan-v5-gagov.md`.
- SEMARCHIVEWALKGAP should amend the roadmap immediately if the refreshed live
  rerun clears the archive-tail seam but exposes a later exact lexical blocker
  such as
  `tests/docs/test_mre2e_evidence_contract.py ->
  tests/docs/test_gagov_governance_contract.py`, because the next repair is
  then no longer archive-tail-local and any older downstream assumption is
  stale.
- SEMCLAUDECMDS should amend the roadmap immediately if the refreshed live
  rerun clears `.claude/commands/execute-lane.md ->
  .claude/commands/plan-phase.md` but exposes a later exact script pair such
  as `scripts/migrate_large_index_to_multi_repo.py ->
  scripts/check_index_languages.py`.
- SEMSCRIPTLANGS should amend the roadmap immediately if the refreshed live
  rerun clears `scripts/migrate_large_index_to_multi_repo.py ->
  scripts/check_index_languages.py` but exposes a later exact phase-plan
  markdown pair such as `plans/phase-plan-v7-SEMPREFLIGHT.md ->
  plans/phase-plan-v7-SEMDOCGOV.md`.
- SEMREADYFIX exists only if SEMDOGFOOD proves the default local dogfood path
  is still blocked; it should repair that blocker and then rerun the dogfood
  proof instead of widening into unrelated semantic work.
- SEMCROSSDOGTAIL should amend the roadmap immediately if the refreshed live
  rerun clears
  `plans/phase-plan-v7-SEMCROSSPLANS.md ->
  plans/phase-plan-v7-SEMDOGFOOD.md` but exposes a later exact blocker such as
  `final_optimized_report_final_report_1750958096/final_report_data.json ->
  final_optimized_report_final_report_1750958096/FINAL_OPTIMIZED_ANALYSIS_REPORT.md`.
- SEMOPTREPORTTAIL exists only if SEMCROSSDOGTAIL proves the modern phase-plan
  pair is cleared but the live rerun still remains in lexical walking on the
  generated optimized-report pair
  `final_optimized_report_final_report_1750958096/final_report_data.json ->
  final_optimized_report_final_report_1750958096/FINAL_OPTIMIZED_ANALYSIS_REPORT.md`;
  it should repair that exact generated-report seam or preserve the next exact
  downstream blocker instead of reopening earlier phase-plan work.
- SEMOPTREPORTTAIL should amend the roadmap immediately if the refreshed live
  rerun clears the generated optimized-report pair but exposes a later exact
  blocker such as
  `tests/fixtures/multi_repo.py ->
  tests/fixtures/files/test_files/example.c`.
- SEMFIXTURETAIL exists only if SEMOPTREPORTTAIL proves the generated
  optimized-report pair is cleared but the live rerun still remains in lexical
  walking on
  `tests/fixtures/multi_repo.py ->
  tests/fixtures/files/test_files/example.c`; it should repair that exact
  fixture seam or preserve the next exact downstream blocker instead of
  reopening earlier generated-report work.
- SEMFIXTURETAIL should amend the roadmap immediately if the refreshed live
  rerun clears the fixture pair but exposes a later exact blocker such as
  `ai_docs/black_isort_overview.md ->
  ai_docs/sqlite_fts5_overview.md`.
- SEMAIOVERVIEWTAIL exists only if SEMFIXTURETAIL proves the fixture pair is
  cleared but the live rerun still remains in lexical walking on
  `ai_docs/black_isort_overview.md ->
  ai_docs/sqlite_fts5_overview.md`; it should repair that exact later
  `ai_docs` pair or preserve the next exact downstream blocker instead of
  reopening earlier fixture or optimized-report work.
- SEMAIOVERVIEWTAIL should amend the roadmap immediately if the refreshed live
  rerun clears the later `ai_docs` overview pair but exposes a later exact
  blocker such as
  `scripts/check_test_index_schema.py ->
  scripts/ensure_test_repos_indexed.py`.
- SEMTESTREPOINDEXTAIL exists only if SEMAIOVERVIEWTAIL proves the later
  `ai_docs` overview pair is cleared but the live rerun still remains in
  lexical walking on
  `scripts/check_test_index_schema.py ->
  scripts/ensure_test_repos_indexed.py`; it should repair that exact later
  script pair or preserve the next exact downstream blocker instead of
  reopening earlier overview, fixture, or optimized-report work.
- SEMTESTREPOINDEXTAIL should amend the roadmap immediately if the refreshed
  live rerun clears the later test-repo index script pair but exposes a later
  exact blocker such as
  `scripts/index_missing_repos_semantic.py ->
  scripts/identify_working_indexes.py`.
- SEMMISSINGREPOSEMTAIL exists only if SEMTESTREPOINDEXTAIL proves the later
  test-repo index script pair is cleared but the live rerun still remains in
  lexical walking on
  `scripts/index_missing_repos_semantic.py ->
  scripts/identify_working_indexes.py`; it should repair that exact later
  script pair or preserve the next exact downstream blocker instead of
  reopening earlier overview or test-repo index work.
- SEMMISSINGREPOSEMTAIL should amend the roadmap immediately if the refreshed
  live rerun clears the later missing-repo semantic index script pair but
  exposes a later exact blocker such as
  `scripts/utilities/prepare_index_for_upload.py ->
  scripts/utilities/verify_tool_usage.py`.
- SEMUTILVERIFYTAIL exists only if SEMMISSINGREPOSEMTAIL proves the later
  missing-repo semantic index script pair is cleared but the live rerun still
  remains in lexical walking on
  `scripts/utilities/prepare_index_for_upload.py ->
  scripts/utilities/verify_tool_usage.py`; it should repair that exact later
  utility-script pair or preserve the next exact downstream blocker instead of
  reopening earlier missing-repo or test-repo index work.
- SEMUTILVERIFYTAIL should amend the roadmap immediately if the refreshed live
  rerun clears the later utility-script verification pair but exposes a later
  exact blocker such as
  `scripts/map_repos_to_qdrant.py ->
  scripts/create_claude_code_aware_report.py`.
- SEMQDRANTREPORTTAIL exists only if SEMUTILVERIFYTAIL proves the later
  utility-script verification pair is cleared but the live rerun still remains
  in lexical walking on
  `scripts/map_repos_to_qdrant.py ->
  scripts/create_claude_code_aware_report.py`; it should repair that exact
  later Qdrant/report pair or preserve the next exact downstream blocker
  instead of reopening earlier utility, missing-repo, or test-repo index
  work.
- SEMQDRANTREPORTTAIL should amend the roadmap immediately if the refreshed
  live rerun clears the later Qdrant/report pair but exposes a later exact
  blocker such as
  `scripts/execute_optimized_analysis.py ->
  scripts/index-artifact-upload-v2.py`.
- SEMOPTUPLOADTAIL exists only if SEMQDRANTREPORTTAIL proves the later
  Qdrant/report pair is cleared but the live rerun still remains in lexical
  walking on
  `scripts/execute_optimized_analysis.py ->
  scripts/index-artifact-upload-v2.py`; it should repair that exact later
  optimized-analysis/upload pair or preserve the next exact downstream blocker
  instead of reopening earlier Qdrant/report, utility, missing-repo, or
  test-repo index work.
- SEMOPTUPLOADTAIL should amend the roadmap immediately if the refreshed live
  rerun clears the later optimized-analysis/upload pair but exposes a later
  exact blocker such as
  `scripts/analyze_claude_code_edits.py ->
  scripts/verify_mcp_retrieval.py`.
- SEMEDITRETRIEVALTAIL exists only if SEMOPTUPLOADTAIL proves the later
  optimized-analysis/upload pair is cleared but the live rerun still remains
  in lexical walking on
  `scripts/analyze_claude_code_edits.py ->
  scripts/verify_mcp_retrieval.py`; it should repair that exact later
  edit-analysis/retrieval pair or preserve the next exact downstream blocker
  instead of reopening earlier optimized-analysis/upload, Qdrant/report,
  utility, missing-repo, or test-repo index work.
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
- SEMAGENTS exists only if SEMANALYSIS clears
  `FINAL_COMPREHENSIVE_MCP_ANALYSIS.md` but the live force-full rerun still
  times out on another bounded Markdown or policy document such as
  `AGENTS.md`; it should repair that exact file path or preserve a still
  narrower downstream blocker.
- SEMREADME exists only if SEMAGENTS clears `AGENTS.md` but the live
  force-full rerun still times out on another bounded Markdown document such
  as `README.md`; it should repair that exact file path or preserve a still
  narrower downstream blocker.
- SEMCLOSEOUT exists only if SEMREADME clears the final lexical timeout but
  the live rerun still remains blocked on semantic closeout; it should repair
  summary persistence, strict semantic vector linkage, or preserve the next
  exact semantic-stage blocker instead of reopening lexical work.
- SEMTIMEOUT exists only if SEMCLOSEOUT proves semantic summary persistence is
  live but the repo-wide force-full rerun still fails on summary timeout
  before strict vector linkage can start; it should tighten repo-wide summary
  pass sizing/backoff and then preserve the next exact downstream blocker.
- SEMPASSSTALL exists only if SEMTIMEOUT clears the repo-wide handoff gap but
  the live force-full rerun still stalls inside a single doc-heavy summary
  pass before it can emit the bounded continuation blocker; it should tighten
  per-pass doc-style chunk sizing or emit intra-pass progress so the current
  semantic-stage blocker returns promptly.
- SEMCALLTIME exists only if SEMPASSSTALL narrows repo-scope work to one file
  and one doc-like chunk but the live force-full rerun still remains in flight
  inside that first summary call with zero new `chunk_summaries`; it should
  add an exact per-call timeout/cancellation blocker instead of letting the
  force-full sync appear hung.
- SEMCANCEL exists only if SEMCALLTIME proves the exact timeout blocker in unit
  coverage but the live force-full rerun still does not exit promptly and can
  leave enlarged zero-summary lexical/runtime state after manual termination;
  it should repair cancellation/cleanup and preserve the next exact blocker
  only if that repaired live exit path still fails closed.
- SEMEXITTRACE exists only if SEMCANCEL proves bounded cancellation and
  zero-summary runtime restore behavior in tests, but the live force-full
  command still does not return promptly enough to persist that repaired
  blocker on the active commit; it should narrow the remaining hang to an
  exact live stage and persisted fail-closed status rather than repeating the
  same blind rerun.
- SEMFASTREPORT exists only if SEMEXITTRACE proves the live force-full blocker
  is still in lexical walking and the durable trace points at generated
  `fast_test_results/fast_report_*.md` output; it should repair that exact
  file family or make the ignore boundary explicit before reopening broader
  lexical or semantic work.
- SEMPYTESTOVERVIEW exists only if SEMFASTREPORT proves the fast-test report
  family is cleared but the live force-full rerun still remains in lexical
  walking on `ai_docs/pytest_overview.md`; it should repair that exact file
  path or preserve a still narrower downstream blocker.
- SEMJEDI exists only if SEMVISUALREPORT proves the exact bounded Python path
  for `scripts/create_multi_repo_visual_report.py` works but the live
  force-full rerun still remains in lexical walking on `ai_docs/jedi.md`; it
  should repair that exact file path or preserve a still narrower downstream
  blocker.
- SEMTRACEFRESHNESS exists only if SEMJEDI clears `ai_docs/jedi.md` but the
  live force-full rerun still hangs while the durable trace remains frozen on
  an older progress marker without naming the current in-flight blocker.
- SEMTRACEFRESHNESS should amend the roadmap immediately if the refreshed live
  trace proves a later exact lexical blocker such as
  `.devcontainer/devcontainer.json`.
- SEMDEVCONTAINER exists only if SEMTRACEFRESHNESS refreshes the live
  force-full trace beyond `ai_docs/pytest_overview.md` but the rerun still
  remains in lexical walking on `.devcontainer/devcontainer.json` past the
  configured timeout window; it should repair that exact seam or preserve a
  still narrower downstream blocker.
- SEMDEVCONTAINER should amend the roadmap immediately if the refreshed live
  rerun clears `.devcontainer/devcontainer.json` but exposes a later exact
  lexical blocker such as `tests/test_artifact_publish_race.py`.
- SEMPUBLISHRACE exists only if SEMDEVCONTAINER proves the
  `.devcontainer/devcontainer.json` seam is cleared but the live force-full
  rerun still remains in lexical walking on
  `tests/test_artifact_publish_race.py`; it should repair that exact file path
  or preserve a still narrower downstream blocker.
- SEMPUBLISHRACE should amend the roadmap immediately if the refreshed live
  rerun clears `tests/test_artifact_publish_race.py` but later re-anchors on a
  different exact lexical seam such as `.devcontainer/devcontainer.json`.
- SEMDEVSTALE exists only if SEMDISKIO’s repaired live rerun never reaches the
  intended disk-I/O closeout seam and instead re-anchors on a renewed stale
  lexical trace at `.devcontainer/devcontainer.json`.
- SEMTESTSTALE exists only if SEMDEVSTALE clears
  `.devcontainer/devcontainer.json`, but the refreshed live rerun still exits
  unexpectedly and leaves a stale-running lexical trace on the later exact
  test-file pair
  `tests/test_deployment_runbook_shape.py -> tests/test_reindex_resume.py`.
- SEMTESTSTALE should amend the roadmap immediately if the refreshed live
  rerun clears the later test-file stale-trace seam but exits again on a later
  exact script-family blocker such as
  `scripts/run_test_batch.py -> scripts/validate_mcp_comprehensive.py`.
- SEMPHASETAIL exists only if SEMCROSSPLANS proves the earlier cross-version
  phase-plan pair is cleared but the refreshed live rerun still terminalizes
  later in lexical walking on
  `plans/phase-plan-v7-SEMSYNCFIX.md ->
  plans/phase-plan-v7-SEMVISUALREPORT.md`.
- SEMLEGACYPLANS exists only if SEMPHASETAIL proves the later v7-only
  phase-plan pair is cleared but the refreshed live rerun still terminalizes
  later in lexical walking on
  `plans/phase-plan-v6-WATCH.md ->
  plans/phase-plan-v1-p19.md`.
- SEMMIXEDPHASETAIL exists only if SEMLEGACYPLANS proves the historical
  `plans/phase-plan-v6-WATCH.md -> plans/phase-plan-v1-p19.md` seam is
  cleared but the refreshed live rerun still terminalizes later in lexical
  walking on
  `plans/phase-plan-v7-SEMPHASETAIL.md ->
  plans/phase-plan-v5-gagov.md`.
- SEMPREUPGRADETAIL exists only if SEMMIXEDPHASETAIL proves the
  mixed-version `plans/phase-plan-v7-SEMPHASETAIL.md ->
  plans/phase-plan-v5-gagov.md` seam is cleared and later reruns advance
  beyond any transient ai-docs waypoint, but the refreshed live rerun still
  terminalizes later in lexical walking on
  `scripts/preflight_upgrade.sh ->
  scripts/test_mcp_protocol_direct.py`.
- SEMPREUPGRADETAIL should amend the roadmap immediately if the refreshed live
  rerun clears
  `scripts/preflight_upgrade.sh ->
  scripts/test_mcp_protocol_direct.py` but exposes a later exact Python-script
  blocker such as
  `scripts/verify_embeddings.py ->
  scripts/claude_code_behavior_simulator.py`.
- SEMVERIFYSIMTAIL exists only if SEMPREUPGRADETAIL proves the
  `scripts/preflight_upgrade.sh ->
  scripts/test_mcp_protocol_direct.py` seam is cleared but the refreshed live
  rerun still terminalizes later in lexical walking on
  `scripts/verify_embeddings.py ->
  scripts/claude_code_behavior_simulator.py`.
- SEMVERIFYSIMTAIL should amend the roadmap immediately if the refreshed live
  rerun clears
  `scripts/verify_embeddings.py ->
  scripts/claude_code_behavior_simulator.py` but exposes a later exact
  Python-script blocker such as
  `scripts/create_semantic_embeddings.py ->
  scripts/consolidate_real_performance_data.py`.
- SEMEMBEDCONSOL exists only if SEMVERIFYSIMTAIL proves the
  `scripts/verify_embeddings.py ->
  scripts/claude_code_behavior_simulator.py` seam is cleared but the refreshed
  live rerun still terminalizes later in lexical walking on
  `scripts/create_semantic_embeddings.py ->
  scripts/consolidate_real_performance_data.py`.
- SEMEMBEDCONSOL should amend the roadmap immediately if the refreshed live
  rerun clears
  `scripts/create_semantic_embeddings.py ->
  scripts/consolidate_real_performance_data.py` but exposes a later exact
  tests/docs blocker such as
  `tests/docs/test_gaclose_evidence_closeout.py ->
  tests/docs/test_p8_deployment_security.py`.
- SEMDOCTESTTAIL exists only if SEMEMBEDCONSOL proves the
  `scripts/create_semantic_embeddings.py ->
  scripts/consolidate_real_performance_data.py` seam is cleared but the
  refreshed live rerun still terminalizes later in lexical walking on
  `tests/docs/test_gaclose_evidence_closeout.py ->
  tests/docs/test_p8_deployment_security.py`.
- SEMDOCTESTTAIL should amend the roadmap immediately if the refreshed live
  rerun clears
  `tests/docs/test_gaclose_evidence_closeout.py ->
  tests/docs/test_p8_deployment_security.py` but exposes a later security
  fixture blocker such as
  `tests/security/fixtures/mock_plugin/plugin.py ->
  tests/security/fixtures/mock_plugin/__init__.py`.
- SEMMOCKPLUGIN exists only if SEMDOCTESTTAIL proves the
  `tests/docs/test_gaclose_evidence_closeout.py ->
  tests/docs/test_p8_deployment_security.py` seam is cleared but the
  refreshed live rerun still terminalizes later in lexical walking on
  `tests/security/fixtures/mock_plugin/plugin.py ->
  tests/security/fixtures/mock_plugin/__init__.py`.
- SEMMOCKPLUGIN should amend the roadmap immediately if the refreshed live
  rerun clears
  `tests/security/fixtures/mock_plugin/plugin.py ->
  tests/security/fixtures/mock_plugin/__init__.py` but exposes a later legacy
  `.codex/phase-loop` blocker such as
  `.codex/phase-loop/runs/20260424T180441Z-01-gagov-execute/launch.json ->
  .codex/phase-loop/runs/20260427T071807Z-02-artpub-execute/terminal-summary.json`.
- SEMCODEXLOOPTAIL should amend the roadmap immediately if the refreshed live
  rerun clears the legacy `.codex/phase-loop` compatibility-runtime family but
  exposes a later exact lexical blocker such as
  `tests/docs/test_semincr_contract.py ->
  tests/docs/test_gabase_ga_readiness_contract.py`.
- SEMDOCCONTRACTTAIL should amend the roadmap immediately if the refreshed live
  rerun clears
  `tests/docs/test_semincr_contract.py ->
  tests/docs/test_gabase_ga_readiness_contract.py` but exposes a later exact
  docs contract-test blocker such as
  `tests/docs/test_garc_rc_soak_contract.py ->
  tests/docs/test_garel_ga_release_contract.py`.
- SEMGARELTAIL exists only if SEMDOCCONTRACTTAIL proves the
  `tests/docs/test_semincr_contract.py ->
  tests/docs/test_gabase_ga_readiness_contract.py` seam is cleared but the
  refreshed live rerun still terminalizes later in lexical walking on
  `tests/docs/test_garc_rc_soak_contract.py ->
  tests/docs/test_garel_ga_release_contract.py`.
- SEMGARELTAIL should amend the roadmap immediately if the refreshed live
  rerun clears
  `tests/docs/test_garc_rc_soak_contract.py ->
  tests/docs/test_garel_ga_release_contract.py` but exposes a later exact docs
  truth and evidence blocker such as
  `tests/docs/test_p23_doc_truth.py ->
  tests/docs/test_semdogfood_evidence_contract.py`.
- SEMDOCTRUTHTAIL exists only if SEMGARELTAIL proves the
  `tests/docs/test_garc_rc_soak_contract.py ->
  tests/docs/test_garel_ga_release_contract.py` seam is cleared but the
  refreshed live rerun still terminalizes later in lexical walking on
  `tests/docs/test_p23_doc_truth.py ->
  tests/docs/test_semdogfood_evidence_contract.py`.

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

# SEMPASSSTALL
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_summarization.py tests/test_dispatcher.py tests/test_git_index_manager.py -q --no-cov
env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
sqlite3 .mcp-index/current.db 'select count(*) from chunk_summaries; select count(*) from semantic_points;'

# SEMCALLTIME
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_summarization.py tests/test_dispatcher.py tests/test_git_index_manager.py tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
sqlite3 .mcp-index/current.db 'select count(*) from chunk_summaries; select count(*) from semantic_points;'

# SEMCANCEL
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_summarization.py tests/test_dispatcher.py tests/test_git_index_manager.py tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'

# SEMEXITTRACE
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/test_repository_commands.py tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
python - <<'PY'
from pathlib import Path
print((Path(".mcp-index") / "force_full_exit_trace.json").read_text())
PY
sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'

# SEMFASTREPORT
env OPENAI_API_KEY=dummy-local-key uv run pytest tests/test_dispatcher.py tests/test_git_index_manager.py tests/docs/test_semdogfood_evidence_contract.py -q --no-cov
env OPENAI_API_KEY=dummy-local-key MCP_INDEX_LEXICAL_TIMEOUT_SECONDS=5 uv run mcp-index repository sync --force-full
env OPENAI_API_KEY=dummy-local-key uv run mcp-index repository status
python - <<'PY'
from pathlib import Path
print((Path(".mcp-index") / "force_full_exit_trace.json").read_text())
PY
sqlite3 .mcp-index/current.db 'select count(*) from files; select count(*) from code_chunks; select count(*) from chunk_summaries; select count(*) from semantic_points;'
```
