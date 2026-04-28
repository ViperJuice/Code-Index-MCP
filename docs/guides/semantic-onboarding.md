# Semantic Onboarding

Semantic search readiness is stricter than ordinary indexed search readiness.
A repository can be lexically ready for `search_code` and `symbol_lookup` while
still being semantically not ready. Semantic readiness is fail-closed and is
reported separately from lexical readiness.

Semantic readiness requires all of the following durable local evidence for the
active semantic profile:

- `code_chunks` exist for the indexed repository.
- `chunk_summaries` exist for those chunks.
- `semantic_points` link those chunks to vectors for the active profile.
- the stored vector metadata matches the current profile fingerprint, vector
  dimension, and collection identity.

When any of those checks fail, semantic readiness reports a specific not-ready
state such as `summaries_missing`, `vectors_missing`,
`vector_dimension_mismatch`, `profile_mismatch`, or `semantic_stale`. Lexical
readiness does not imply semantic readiness.

This guide shows how to set up semantic search for Code-Index-MCP with:

- local Qdrant (auto-started via Docker)
- a profile-selected enrichment endpoint for chunk summaries
- a profile-selected embedding endpoint for vectorization

## Quick Start

```bash
python scripts/cli/mcp_cli.py setup semantic
```

The command performs preflight checks and, by default, starts local Qdrant if it is not reachable.
For the active profile, the preflight is fail-closed: it can block semantic
vector writes before `SEMPIPE` if chat reachability, embedding dimension, or
collection shape do not match the configured contract.

## Where Settings Live

Configuration precedence:

1. CLI flags (`setup semantic --qdrant-url ...`)
2. Environment variables (`.env`)
3. `code-index-mcp.profiles.yaml`
4. `SEMANTIC_PROFILES_JSON`
5. Built-in defaults

> **Tip**: Keep profile-local endpoints in `code-index-mcp.profiles.yaml`. Global
> `OPENAI_API_BASE` remains only a fallback for older flows and should not be the
> primary way to steer `oss_high`.

## Key Environment Variables

- `SEMANTIC_SEARCH_ENABLED=true`
- `SEMANTIC_AUTOSTART_QDRANT=true`
- `SEMANTIC_STRICT_MODE=false`
- `SEMANTIC_PREFLIGHT_TIMEOUT_SECONDS=10`
- `QDRANT_URL=http://localhost:6333`
- `QDRANT_COMPOSE_FILE=docker-compose.qdrant.yml`
- `SEMANTIC_ENRICHMENT_BASE_URL=http://ai:8002/v1`
- `SEMANTIC_ENRICHMENT_MODEL=chat`
- `SEMANTIC_EMBEDDING_BASE_URL=http://ai:8001/v1`
- `VLLM_SUMMARIZATION_BASE_URL=http://ai:8002/v1`  # compatibility shim only
- `VLLM_EMBEDDING_BASE_URL=http://ai:8001/v1`  # compatibility shim only
- `OPENAI_API_BASE=http://localhost:8001/v1`  # legacy fallback only
- `OPENAI_API_KEY=vllm-local`
- `VOYAGE_API_KEY`

## CLI Examples

```bash
# Validate only
python scripts/cli/mcp_cli.py setup semantic --dry-run

# Strict mode
python scripts/cli/mcp_cli.py setup semantic --strict

# JSON output for CI
python scripts/cli/mcp_cli.py setup semantic --json

# Select profile
python scripts/cli/mcp_cli.py setup semantic --profile commercial_high
```

## Verify Services

```bash
curl http://localhost:6333/collections
curl http://ai:8002/v1/models   # oss_high enrichment proxy
curl http://ai:8001/v1/models   # oss_high embedding endpoint
```

## What Preflight Proves

`setup semantic` and `mcp-index index check-semantic` now perform a semantic
preflight for the active profile that stays read-only with respect to summaries
and vectors:

- an enrichment chat smoke sends a redacted OpenAI-compatible chat request to
  the selected enrichment endpoint using the configured chat model
- an embedding smoke verifies the returned vector dimension matches the active
  profile
- a Qdrant collection check verifies collection existence, namespace identity,
  vector dimension, and distance metric without creating or mutating the
  collection
- API-key reporting remains metadata-only: env-var name plus presence boolean,
  never the secret value
- when any check fails, the command emits a structured blocker, semantic vector
  writes remain fail-closed until remediation is complete, and the phase stays
  read-only with respect to summaries and vectors

## Default `oss_high` Layout

- Enrichment uses `${SEMANTIC_ENRICHMENT_BASE_URL:http://ai:8002/v1}` with
  `${SEMANTIC_ENRICHMENT_MODEL:chat}`.
- Embeddings use `${SEMANTIC_EMBEDDING_BASE_URL:http://ai:8001/v1}` with
  `Qwen/Qwen3-Embedding-8B`.
- Legacy `VLLM_SUMMARIZATION_BASE_URL` and `VLLM_EMBEDDING_BASE_URL` remain
  accepted as compatibility shims when the newer `SEMANTIC_*` vars are unset.
- `uv sync --locked` installs the default OpenAI-compatible client stack; no extra
  semantic install is required just to reach the local enrichment or embedding
  endpoints.

## Readiness Notes

- `get_status` exposes lexical readiness separately from semantic readiness.
- `search_code(semantic=true)` refuses with semantic readiness metadata when
  summaries, vectors, or profile compatibility are missing.
- Semantic search remains experimental and provider-aware; do not treat a
  lexically ready repository as semantically query-ready unless the semantic
  readiness surface reports `ready`.

## Full Reindex Pipeline

In semantic mode, a full `reindex` now runs the build in a fixed order:

1. lexical/chunk persistence
2. authoritative summary generation for the targeted chunks/files
3. semantic vector writes

The semantic vector stage is strict. If authoritative summaries are missing for
targeted chunks, or if semantic preflight says the active profile cannot write
vectors, semantic vector writes are skipped and semantic readiness stays
not-ready even when lexical indexing completed successfully.

`reindex` reports the semantic stage additively. Operators should expect to see
whether summaries were written, whether semantic vectors were written, and
whether the semantic stage was blocked before any vector write or failed after
lexical persistence.

Manual summary tools stay separate from the full-sync contract:

- `write_summaries` is an explicit summary-only operation. It can populate
  authoritative summaries, but it does not claim semantic vector success.
- `summarize_sample` is a diagnostic/sample tool for inspecting summary output
  and does not satisfy the full-sync semantic build contract by itself.

## Incremental Mutation Contract

Incremental mutation follows the same ordered semantic contract as full sync:

1. lexical/chunk persistence
2. authoritative summary generation or summary reuse when the stored semantic
   fingerprint still matches
3. strict semantic vector writes

Changed chunks invalidate stale semantic evidence before re-embedding. That
includes authoritative summaries when chunk content or the summary contract
changes, plus vector linkages for stale chunk, subchunk, and file-summary
entries.

Deletes remove both authoritative summaries and semantic vectors for the
affected file. Renames may preserve authoritative chunk summaries only when the
stored profile and prompt fingerprints still match, but the file-summary vector
is rotated through the same summary-first rebuild path so path-sensitive
semantic context does not go stale.

Watcher-triggered repair uses the same summary-first mutation contract as
direct incremental sync. This phase is limited to mutation durability and
watcher repair; it does not change semantic query routing and does not claim
dogfood rebuild evidence.

## Troubleshooting

- Qdrant unreachable
  - run `docker compose -f docker-compose.qdrant.yml up -d qdrant`
  - ensure port `6333` is free
- OpenAI-compatible endpoint unreachable
  - check the selected profile's enrichment or embedding host/port
  - verify `SEMANTIC_ENRICHMENT_BASE_URL` and `SEMANTIC_EMBEDDING_BASE_URL`
- Wrong chat model or blocked semantic writes
  - verify `SEMANTIC_ENRICHMENT_MODEL` matches a model served by the enrichment endpoint
  - rerun `setup semantic --json` to inspect the structured blocker and remediation
- Voyage provider failing
  - verify `VOYAGE_API_KEY`
- Preflight output
  - `setup semantic --json` reports resolved enrichment and embedding endpoints separately
  - preflight reports collection validation, vector dimension checks, and whether it can write semantic vectors
  - API-key reporting is metadata-only: env-var name plus presence boolean, never the secret value
