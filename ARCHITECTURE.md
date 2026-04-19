# Architecture Overview

This file documents high-level architectural decisions for Code-Index-MCP.  It is
extended as significant design decisions are made.  For phase-level implementation
details see `specs/phase-plans-v1.md`.

---

## Concurrency & Multi-Instance Safety (P17)

Added in P17 — Durability & Multi-Instance Safety.

### Registry flock protocol

`RepositoryRegistry.save()` uses a **POSIX advisory exclusive lock** to serialize
concurrent writers.

- Lock file: `<registry_path>.lock` (sibling of `registry.json`), mode `0o600`.
- Lock type: `fcntl.LOCK_EX` (blocking) — writers queue; no write is dropped.
- Read-merge-write: each writer re-reads the on-disk JSON after acquiring the lock,
  merges its in-memory entries over the disk state, then writes atomically via
  `rename()`.  This prevents the lost-write hazard when two processes save concurrently.
- The flock is released by the kernel on process exit (including crash), so there is no
  permanent lock-file cleanup needed after an abnormal termination.
- Boundary: this protocol is safe for **same-host** processes only.  NFS/cross-host
  advisory locks are not reliable and are not supported.

See `docs/operations/multi-instance.md` for the full operator runbook.

### Singleton reset rule

`reset_process_singletons()` (`mcp_server/cli/bootstrap.py`) is invoked at the
**top** of `initialize_stateless_services()` before any manager is constructed.  It
nulls nine module-level singletons so that re-initialization in the same Python process
(test teardown, hot-reload, fork) yields fresh, independent managers rather than
inheriting stale state from a previous initialization cycle.

This is the authoritative reset point — callers must not null these attributes
individually; they must call `initialize_stateless_services()`.

### Ref-poller edge-case semantics

`RefPoller` (`mcp_server/watcher/ref_poller.py`) detects three edge cases that signal
a branch has diverged non-incrementally from the last-indexed state:

1. **Detached HEAD** — current commit cannot be resolved to a branch tip.
2. **Force-push** — commit hash changed without a fast-forward relationship.
3. **Branch rename** — the tracked branch no longer exists.

In all three cases the poller calls `enqueue_full_rescan(repo_id)` on the
`GitIndexManager`, discarding the incremental checkpoint and re-indexing the repository
from scratch.  This is conservative but correct: incremental indexing on a rewritten
history would produce inconsistent symbol tables.

### ENOSPC → read-only store

When a SQLite `commit()` raises `OSError(ENOSPC)`, `SQLiteStore`
(`mcp_server/storage/sqlite_store.py`) transitions to **read-only mode**:

- All subsequent write operations raise `TransientArtifactError("store is read-only after ENOSPC")`.
- The `mcp_storage_readonly_total` Prometheus counter is incremented.
- Read operations continue to succeed — the server keeps serving search queries.
- Recovery requires freeing disk space and restarting the server process (the read-only
  flag is in-memory; there is no automatic recovery without a restart).
