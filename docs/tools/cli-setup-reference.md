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
3. Sends an enrichment chat smoke using the configured chat model.
4. Sends an embedding smoke and checks vector dimension against the active profile.
5. Validates Qdrant collection existence, namespace identity, vector dimension, and distance metric.
4. Reports redacted API-key env-var names and presence for both enrichment and embedding.
6. Checks Qdrant reachability.
7. If Qdrant is down and autostart is enabled, starts Qdrant via Docker Compose.
8. Prints actionable status, a structured blocker when semantic vector writes are blocked, and next steps.

For the default `oss_high` profile, the docs contract is:

- enrichment defaults to `SEMANTIC_ENRICHMENT_BASE_URL=http://ai:8002/v1`
  with `SEMANTIC_ENRICHMENT_MODEL=chat`
- embeddings default to `SEMANTIC_EMBEDDING_BASE_URL=http://ai:8001/v1`
  with `Qwen/Qwen3-Embedding-8B`
- `VLLM_SUMMARIZATION_BASE_URL` and `VLLM_EMBEDDING_BASE_URL` are compatibility shims only

### Exit Semantics

- Non-strict mode: command can succeed with warnings.
- Strict mode: command fails when the structured blocker says semantic vector writes are not allowed.

## `mcp-index index check-semantic`

`mcp-index index check-semantic`

This command renders the same active-profile semantic preflight contract as
`setup semantic` without running a full index. It reports:

- enrichment chat smoke status
- embedding vector dimension validation
- Qdrant collection validation
- metadata-only API-key presence
- the structured blocker and whether the active profile can write semantic vectors
