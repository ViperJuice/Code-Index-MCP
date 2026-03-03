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
2. Checks embedding provider readiness for selected/default profile.
3. Checks Qdrant reachability.
4. If Qdrant is down and autostart is enabled, starts Qdrant via Docker Compose.
5. Prints actionable status and next steps.

### Exit Semantics

- Non-strict mode: command can succeed with warnings.
- Strict mode: command fails when preflight is not fully ready.
