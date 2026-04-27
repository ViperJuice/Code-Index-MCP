# Artifact Persistence and Recovery

This guide describes how index persistence works with artifact push/pull/recover,
how default-branch updates are applied, and how to reconcile local branch/worktree
drift without adding a complicated remote delta-download protocol.

## Lifecycle Overview

1. Local index build creates lexical and semantic assets under `.mcp-index/` (`current.db`, `.index_metadata.json`, and `vector_index.qdrant`).
2. `mcp-index artifact push` packages a full snapshot artifact and publishes it
   either through GitHub Actions artifacts or through a SHA-keyed GitHub
   Release asset set.
3. Teammates or fresh clones run `mcp-index preflight` first to see whether they are behind remote or missing local runtime state.
4. `mcp-index artifact pull --latest` hydrates local indexes from the full snapshot when needed.
5. MCP reads the restored local runtime files directly from disk (`.mcp-index/current.db`, `.mcp-index/.index_metadata.json`, `.mcp-index/vector_index.qdrant`).
6. The CLI reports the restored artifact commit and compares it to local `HEAD`.
7. If your branch or working tree has drifted, use local incremental reindexing to reconcile only changed files.
8. On branch/commit targeting, `mcp-index artifact recover --branch ... --commit ...` resolves and restores matching artifact state.

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

# Explicit unsafe recovery override; prints rejected validation reasons
mcp-index artifact recover --branch main --commit <sha> --unsafe-allow-mismatched-artifact
```

## What Gets Persisted

- Lexical index (SQLite / FTS)
- Semantic payloads and profile metadata
- Artifact metadata (`artifact-metadata.json`, manifest payloads)

These files are expected to exist locally for MCP runtime use, but they are
distributed through GitHub artifacts or GitHub Release assets rather than
committed to normal git history.

`.mcp-index/current.db` is canonical. Root-level `code_index.db` is accepted only
as a legacy archive member after artifact metadata has validated successfully,
and it is installed as `.mcp-index/current.db`.

The canonical published baseline includes two semantic profiles in separate
collections inside `vector_index.qdrant`:

- `commercial_high` -> `code_index__commercial_high__v1`
- `oss_high` -> `code_index__oss_high__v1`

That lets teammates pull one artifact and choose either the proprietary or OSS
semantic profile without rebuilding the whole repository.

## Remote Publication Modes

- **Runtime direct publish:** `publish_on_reindex()` creates or repairs a
  SHA-keyed release, uploads the archive plus `artifact-metadata.json`,
  checksum sidecar, and optional attestation sidecar, verifies those assets,
  then moves `index-latest`.
- **GitHub Actions artifacts:** CI uploads a repo-scoped `.mcp-index/`
  snapshot archive plus packaged `artifact-metadata.json` for validation and
  recovery compatibility. This path mirrors the direct-publish metadata
  contract, but it does not move release pointers.
- **Local-only fallback:** when remote publication is unavailable, local
  `.mcp-index/` state remains the runtime source of truth.

## Operator Path Selection

- **Local-only build or repair:** use `mcp-index artifact push --validate`,
  `pull`, `sync`, or `recover` against local `.mcp-index/` state when you are
  reconciling a workstation or a fresh clone.
- **CI snapshot upload:** use the GitHub Actions upload path for validation and
  short-lived recovery artifacts. The supported manual dispatch surface is
  validation of an existing uploaded artifact, not release promotion or cleanup
  management.
- **Runtime publish-on-reindex:** rely on the watcher/runtime direct-publish
  path when you need the durable SHA-keyed release asset set and `index-latest`
  pointer movement.

## Recommended Remote/Local Split

- **Remote transport:** GitHub Release assets for runtime direct publish, with
  GitHub Actions artifacts still supported for CI and recovery compatibility.
- **Canonical semantic storage:** file-backed `vector_index.qdrant` built in CI.
- **Local efficiency:** incremental reindex after restore based on git diff and
  watcher-driven file changes.
- **Provider safety:** `auto` routes only to implemented providers. S3, GCS, and
  Azure are documented placeholders and cannot be selected in production until
  implemented.

This keeps the GitHub path simple while still avoiding full local rebuilds for
normal development.

## Same-Machine Multi-Repo Workflow

For open source users running multiple repositories on one machine, the
recommended model is local-first:

- register each checkout once with `mcp-index repository register <path>`
- use `mcp-index repository list -v` to inspect repo-level readiness and semantic profiles
- each repository keeps its own local runtime/index files
- the shared registry tracks which repos are ready, stale, or missing local state
- `mcp-index artifact workspace-status` reports readiness across registered repos
- `mcp-index artifact publish-workspace` records per-repo prepared artifact
  state plus metadata/validation fields
- `mcp-index artifact fetch-workspace` hydrates registered repositories from
  validated artifacts and reports commit, branch, checksum, schema_version,
  semantic_profile_hash, and semantic_profiles
- `mcp-index artifact reconcile-workspace` refreshes that readiness after restores or rebuilds
- normal CI acceptance uses a deterministic local GitHub/CLI mock for this
  workspace lifecycle instead of live publication

Typical flow:

```bash
mcp-index repository register /path/to/repo-a
mcp-index repository register /path/to/repo-b
mcp-index repository list -v
mcp-index artifact workspace-status
mcp-index artifact publish-workspace
mcp-index artifact fetch-workspace
mcp-index artifact reconcile-workspace
```

This avoids turning multi-repo usage into a GitHub-artifact-per-repo system,
which helps keep the tool practical for open source developers who do not want
ongoing infrastructure costs.

## MRE2E Accepted Deployment Shape

MRE2E freezes the supported acceptance shape for multi-repo hydration:

- many unrelated repositories on one machine;
- one registered worktree per git common directory;
- tracked/default branch indexing only;
- local-first workspace commands as the operator surface:
  `workspace-status`, `publish-workspace`, `fetch-workspace`,
  `reconcile-workspace`;
- deterministic local GitHub/CLI mock coverage in CI for
  `register -> index -> publish -> hydrate -> reconcile -> query`;
- optional live-operator validation only when a human explicitly needs to prove
  real GitHub artifact transport behavior.

This phase is still beta. Normal CI does not require live GitHub publication,
and rollout posture for broader production adoption remains deferred to
`MRREADY`.

## MRREADY Rollout Gate

MRREADY turns the multi-repo lifecycle into a rollout gate rather than another
artifact feature:

- `mcp-index repository list -v`, `mcp-index repository status`, and
  `mcp-index artifact workspace-status` are the canonical operator views.
- Those surfaces report rollout statuses such as `ready`, `local_only`,
  `publish_failed`, `wrong_branch`, `stale_commit`, `missing_index`, and
  `partial_index_failure`.
- Query tools remain separate. A non-ready repository still returns
  `index_unavailable` with `safe_fallback: "native_search"` until readiness is
  back to `ready`.
- The current verdict is `controlled rollout only`, not broad multi-repo
  deployment, because the beta boundary still applies to multi-repo and STDIO.

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

Downloads fail closed by default. Wrong `repo_id`, wrong `tracked_branch`, stale
commit, unknown schema, missing metadata, checksum mismatch, and semantic profile
mismatch block extraction or install unless the caller explicitly supplies
`allow_unsafe=True` through the API or
`--unsafe-allow-mismatched-artifact` through the CLI. Unsafe installs report the
rejected reasons.

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

- Push succeeds and the remote SHA-keyed release contains the archive,
  `artifact-metadata.json`, checksum sidecar, and optional attestation sidecar.
- `index-latest` points only at a fully populated SHA release.
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
