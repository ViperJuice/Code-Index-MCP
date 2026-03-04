# Artifact Persistence and Recovery

This guide describes how index persistence works with artifact push/pull/recover,
how default-branch updates are applied, and how to validate the behavior.

## Lifecycle Overview

1. Local index build creates lexical and semantic assets (`code_index.db`, vector payloads).
2. `mcp_cli.py artifact push` packages and uploads the artifact (full and optionally delta metadata).
3. Teammates or fresh clones run `mcp_cli.py artifact pull --latest` to hydrate local indexes.
4. On branch/commit targeting, `mcp_cli.py artifact recover --branch ... --commit ...` resolves and restores matching artifact state.
5. On default branch changes, delta chains can be resolved and applied from last full artifact.

## Commands

```bash
# Upload local indexes
uv run python scripts/cli/mcp_cli.py artifact push --validate

# Pull latest compatible artifact
uv run python scripts/cli/mcp_cli.py artifact pull --latest

# Recover by branch and/or commit
uv run python scripts/cli/mcp_cli.py artifact recover --branch main --commit <sha>
```

## What Gets Persisted

- Lexical index (SQLite / FTS)
- Semantic payloads and profile metadata
- Artifact metadata (`artifact-metadata.json`, manifest payloads)
- Optional delta manifests for commit-to-commit transitions

## Default Branch Update Behavior

When `main` advances:

1. Resolver finds the newest target commit.
2. If full artifact exists for target commit, hydrate directly.
3. Otherwise, resolve chain `[full_base, delta_1..delta_n]`.
4. Apply deltas in order and verify checksums.

## Validation Checklist

- Push succeeds and artifact is visible in backend.
- Pull recreates local index and query results are non-empty.
- Recover by commit restores historical state.
- Delta apply rejects invalid manifest/checksum mismatches.

## Automated Tests

- `tests/test_artifact_lifecycle.py`
  - Commit artifact create/extract roundtrip
  - Delta create/apply correctness
  - Delta chain resolution for default branch progression
