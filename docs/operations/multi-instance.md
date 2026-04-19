# Multi-Instance Operations Runbook

This document covers running two or more `Code-Index-MCP` server processes against the
same registry file on the same host — and what to do when a process crashes while holding
a lock.

> **Scope**: Two MCP server processes on the **same host** sharing a single
> `repository_registry.json` file are fully supported.  Cross-host multi-instance (NFS,
> distributed filesystems, shared network mounts) is **not in scope** for P17 and is not
> safe with the file-based flock protocol described here.

---

## 1. File-locking protocol

`RepositoryRegistry.save()` uses a POSIX advisory exclusive lock before every write.

| Detail | Value |
|---|---|
| Lock file | `<registry_path>.lock` (sibling of `registry.json`) |
| Lock type | `fcntl.LOCK_EX` (blocking exclusive) |
| File mode | `0o600` (owner read/write only) |
| Unlock | `fcntl.LOCK_UN` in a `finally` block — always released |

**Write protocol (read-merge-write)**

1. `open(lock_path, O_CREAT|O_RDWR, 0o600)` → obtain the lock fd.
2. `fcntl.flock(fd, LOCK_EX)` — blocks until no other process holds LOCK_EX.
3. Read the on-disk JSON (catches writes from concurrent processes since our last read).
4. Merge: `{**on_disk, **in_memory}` — our new entries win; concurrent entries are preserved.
5. Write to `.tmp`, then `rename()` into the final path (atomic on Linux).
6. `fcntl.flock(fd, LOCK_UN)` + `close(fd)` — always in the `finally` block.

This prevents the lost-write hazard: if two processes call `save()` simultaneously, both
updates are preserved in the merged file.

---

## 2. Singleton reset semantics

`reset_process_singletons()` (`mcp_server/cli/bootstrap.py`) is called at the top of
`initialize_stateless_services()` before any service is constructed.  It nulls nine
module-level singletons:

| Module | Attribute nulled |
|---|---|
| `mcp_server.metrics.prometheus_exporter` | `_exporter` |
| `mcp_server.gateway` | `_repo_registry` |
| `mcp_server.plugin_system.loader` | `_loader` |
| `mcp_server.plugin_system.discovery` | `_discovery` |
| `mcp_server.plugin_system.config` | `_config_manager` |
| `mcp_server.plugins.memory_aware_manager` | `_manager_instance` |
| `mcp_server.storage.multi_repo_manager` | `_manager_instance` |
| `mcp_server.dispatcher.cross_repo_coordinator` | `_coordinator_instance` |
| `mcp_server.plugins.repository_plugin_loader` | `_loader_instance` |

**Why this matters for multi-instance**: each process initializes fresh managers from
its own environment.  There is no shared in-memory state between processes; the only
shared state is the `registry.json` file (serialized via flock) and the SQLite index
files (one per repository, opened independently).

---

## 3. Disaster recovery — process crash while holding the lock

POSIX advisory flocks (`fcntl.flock`) are automatically released by the kernel when the
file descriptor is closed or the process exits, including abnormal termination (SIGKILL,
OOM kill, crash).

**Recovery procedure**

1. **Do nothing** — the OS cleans up the flock.  The next call to `save()` from any
   surviving process will successfully acquire `LOCK_EX` and proceed.
2. Verify the lock is gone: `flock --exclusive --nonblock <registry_path>.lock echo ok`
   should succeed immediately after the crashed process exits.
3. If the registry JSON is corrupt (crash mid-write to the `.tmp` file before the
   `rename`), the `.tmp` file will be present alongside `registry.json`.  In this case:
   - The `.tmp` file is incomplete and should be removed: `rm <registry_path>.tmp`
   - The original `registry.json` is intact (rename is atomic; the tmp was never moved).
4. Restart the server process normally.

**The `.lock` file itself**: it is safe to `rm` the `.lock` file after confirming no
process holds it.  The next `save()` will recreate it via `O_CREAT`.

---

## 4. Boundary conditions

| Scenario | Supported? | Notes |
|---|---|---|
| Two processes, same host, same `registry.json` | Yes | flock serializes writes; reads are merge-safe |
| Same process, re-init via `initialize_stateless_services` | Yes | `reset_process_singletons` ensures clean slate |
| Process restart on ENOSPC | Yes | Store enters read-only mode; reads continue; see `docs/operations/` for disk-full recovery |
| Cross-host NFS share | **No** | NFS advisory locks are unreliable; not supported in P17 |
| Distributed store (etcd/Redis) | **No** | Out of scope; file-based registry only |

---

## See also

- `mcp_server/storage/repository_registry.py` — `save()` implementation
- `mcp_server/cli/bootstrap.py` — `reset_process_singletons()`, `initialize_stateless_services()`
- `docs/operations/known-test-debt.md` — residual test failures and resolution paths
- `ARCHITECTURE.md` — Concurrency & Multi-Instance Safety section
