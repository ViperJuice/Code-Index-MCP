# CLI Setup Reference

## Command Group

`python scripts/cli/mcp_cli.py setup`

## Semantic Setup

`python scripts/cli/mcp_cli.py setup semantic`

### Options

- `--autostart-qdrant/--no-autostart-qdrant` (default: enabled)
- `--strict/--no-strict`
- `--qdrant-url <url>`
- `--openai-api-base <url>`
- `--profile <profile_id>`
- `--timeout <seconds>`
- `--dry-run`
- `--json`

### Behavior

1. Validates semantic profile configuration.
2. Resolves the selected/default profile's embedding and enrichment metadata.
3. Checks embedding provider readiness for the selected/default profile.
4. Reports redacted API-key env-var names and presence for both enrichment and embedding.
5. Checks Qdrant reachability.
6. If Qdrant is down and autostart is enabled, starts Qdrant via Docker Compose.
7. Prints actionable status and next steps.

For the default `oss_high` profile, the docs contract is:

- enrichment defaults to `SEMANTIC_ENRICHMENT_BASE_URL=http://ai:8002/v1`
  with `SEMANTIC_ENRICHMENT_MODEL=chat`
- embeddings default to `SEMANTIC_EMBEDDING_BASE_URL=http://ai:8001/v1`
  with `Qwen/Qwen3-Embedding-8B`
- `VLLM_SUMMARIZATION_BASE_URL` and `VLLM_EMBEDDING_BASE_URL` are compatibility shims only

### Exit Semantics

- Non-strict mode: command can succeed with warnings.
- Strict mode: command fails when preflight is not fully ready.
