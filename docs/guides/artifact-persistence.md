# Artifact Persistence and Recovery

This guide describes how index persistence works with artifact push/pull/recover,
how default-branch updates are applied, and how to reconcile local branch/worktree
drift without adding a complicated remote delta-download protocol.

## Lifecycle Overview

1. Local index build creates lexical and semantic assets (`code_index.db`, metadata, and any semantic sidecar data).
2. `mcp-index artifact push` packages and uploads a full snapshot artifact.
3. Teammates or fresh clones run `mcp-index artifact pull --latest` to hydrate local indexes from that full snapshot.
4. The CLI reports the restored artifact commit and compares it to local `HEAD`.
5. If your branch or working tree has drifted, use local incremental reindexing to reconcile only changed files.
6. On branch/commit targeting, `mcp-index artifact recover --branch ... --commit ...` resolves and restores matching artifact state.

## Commands

```bash
# Upload local indexes
mcp-index artifact push --validate

# Pull latest compatible artifact
mcp-index artifact pull --latest

# Check whether the restored artifact matches local HEAD/worktree drift
mcp-index artifact sync

# Recover by branch and/or commit
mcp-index artifact recover --branch main --commit <sha>
```

## What Gets Persisted

- Lexical index (SQLite / FTS)
- Semantic payloads and profile metadata
- Artifact metadata (`artifact-metadata.json`, manifest payloads)

## Recommended Remote/Local Split

- **Remote transport:** full GitHub artifact snapshot only.
- **Local efficiency:** incremental reindex after restore based on git diff and
  watcher-driven file changes.

This keeps the GitHub path simple while still avoiding full local rebuilds for
normal development.

## Why Not Partial Remote Downloads?

The current compressed artifact for this repository is only a few dozen megabytes,
which is small enough that full artifact download remains simpler than designing
and maintaining a remote delta fetch/apply protocol.

That means:

- GitHub stores and serves whole artifacts.
- Local machines handle the optimization by reconciling drift after restore.
- Remote partial artifact download is only worth revisiting if artifact size or
  pull frequency grows enough to justify the operational complexity.

## Default Branch Update Behavior

When `main` advances:

1. Pull the newest compatible full artifact.
2. Read the restored artifact commit and compare it to local `HEAD`.
3. If `HEAD` matches, start using the restored index immediately.
4. If `HEAD` differs, run `mcp-index artifact sync` to let local incremental
   reconciliation handle added, modified, deleted, and renamed files when the
   drift volume is small enough.
5. If drift is very large, prefer a local rebuild instead of forcing incremental catch-up.

## Branch Switching Strategy

The recommended branch workflow is:

1. Use the latest `main` artifact as the base snapshot.
2. Switch branches locally.
3. Diff the restored artifact commit to your current `HEAD`.
4. Reconcile those changes locally with incremental indexing.
5. Let the watcher keep the index current after that point.

This avoids per-branch remote artifact complexity while still making frequent
branch switching cheap enough for normal development.

## Validation Checklist

- Push succeeds and a GitHub artifact is visible remotely.
- Pull recreates local index and reports the restored artifact commit.
- Sync reports whether local `HEAD` or working tree differs from the restored artifact.
- Recover by commit restores historical state.
- Local incremental reconciliation handles added, modified, deleted, and renamed files.

## Automated Tests

- `tests/test_artifact_commands.py`
  - Pull/recover/sync restore reporting
  - Local restore verification
- `tests/test_incremental_indexer.py`
  - Added/modified/deleted file reconciliation
  - Split semantic chunk cleanup
- `tests/test_watcher.py`
  - Ongoing file watcher updates after restore
