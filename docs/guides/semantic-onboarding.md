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
- Voyage and/or OpenAI-compatible embedding endpoints (vLLM)

## Quick Start

```bash
python scripts/cli/mcp_cli.py setup semantic
```

The command performs preflight checks and, by default, starts local Qdrant if it is not reachable.

## Where Settings Live

Configuration precedence:

1. CLI flags (`setup semantic --qdrant-url ...`)
2. Environment variables (`.env`)
3. `code-index-mcp.profiles.yaml`
4. `SEMANTIC_PROFILES_JSON`
5. Built-in defaults

> **Tip**: For multi-profile setups, set `base_url` directly in
> `code-index-mcp.profiles.yaml` rather than via `OPENAI_API_BASE`. The YAML value
> takes precedence for profile URLs and avoids accidentally routing all profiles to the
> same endpoint.

## Key Environment Variables

- `SEMANTIC_SEARCH_ENABLED=true`
- `SEMANTIC_AUTOSTART_QDRANT=true`
- `SEMANTIC_STRICT_MODE=false`
- `SEMANTIC_PREFLIGHT_TIMEOUT_SECONDS=10`
- `QDRANT_URL=http://localhost:6333`
- `QDRANT_COMPOSE_FILE=docker-compose.qdrant.yml`
- `OPENAI_API_BASE=http://localhost:8001/v1`  # fallback only; prefer profiles.yaml base_url
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
curl http://ai:8001/v1/models   # oss_high vLLM (adjust hostname to your setup)
```

## Readiness Notes

- `get_status` exposes lexical readiness separately from semantic readiness.
- `search_code(semantic=true)` refuses with semantic readiness metadata when
  summaries, vectors, or profile compatibility are missing.
- Semantic search remains experimental and provider-aware; do not treat a
  lexically ready repository as semantically query-ready unless the semantic
  readiness surface reports `ready`.

## Troubleshooting

- Qdrant unreachable
  - run `docker compose -f docker-compose.qdrant.yml up -d qdrant`
  - ensure port `6333` is free
- OpenAI-compatible endpoint unreachable
  - check vLLM process/container binding and host/port
  - verify `OPENAI_API_BASE`
- Voyage provider failing
  - verify `VOYAGE_API_KEY`
