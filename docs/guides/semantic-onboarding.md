# Semantic Onboarding (Docker-First)

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
- `VOYAGE_API_KEY` (or `VOYAGE_AI_API_KEY`)

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

## Troubleshooting

- Qdrant unreachable
  - run `docker compose -f docker-compose.qdrant.yml up -d qdrant`
  - ensure port `6333` is free
- OpenAI-compatible endpoint unreachable
  - check vLLM process/container binding and host/port
  - verify `OPENAI_API_BASE`
- Voyage provider failing
  - verify `VOYAGE_API_KEY` or `VOYAGE_AI_API_KEY`
