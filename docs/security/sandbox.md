# Plugin Sandbox Architecture

## Overview

The plugin sandbox (SL-1) isolates plugin execution from the host process via a dedicated worker process communicating over JSON-line IPC. This document describes the sandbox boundary, capability model, and threat profile.

## IPC Protocol

The sandbox uses a **JSON-line message envelope** over stdin/stdout:

```
Worker ◄─── stdin (JSON lines, 30s timeout) ◄─── Host
Worker ──► stdout (JSON lines, 16 MiB max per line) ──► Host
```

**Message Shape**:
```json
{
  "request_id": "uuid-or-counter",
  "method": "invoke_plugin_method",
  "args": { "symbol": "MyClass", ... },
  "capabilities": { "filesystem": false, "network": false, ... }
}
```

**Response Shape**:
```json
{
  "request_id": "same-as-request",
  "result": { "matches": [...] },
  "error": null
}
```

## Capability Set

The `CapabilitySet` dataclass defines which operations are allowed:

- **filesystem**: read/write file system (default: false)
- **network**: make HTTP/TCP calls (default: false)
- **subprocess**: spawn child processes (default: false — even plugins needing subprocesses must declare explicitly)
- **env_read**: read environment variables (default: false)
- **sqlite**: access to the SQLite store (default: true — the plugin is responsible for safe queries)

The host constructs a `SandboxedPlugin` adapter wrapping each real plugin instance with per-plugin capability declarations.

## Worker Lifecycle

1. **Startup**: Host spawns worker as a subprocess, passing `--plugin-name <name>` and `--capabilities <json>`.
2. **Steady state**: Host sends requests over stdin; worker reads and processes; worker writes responses to stdout.
3. **Timeout**: If no response in 30 seconds, the worker is force-killed and the request returns an error.
4. **Shutdown**: Host sends a `shutdown` signal (or closes stdin) and waits for graceful exit.

## Threat Model

**What the sandbox blocks**:
- File system escape (plugins cannot access files outside their declared read-only roots)
- Network access (no sockets, no HTTP clients unless explicitly enabled)
- Arbitrary subprocess spawning (unless `subprocess` capability is granted — Go plugin may need this)
- Environment variable leakage (unless `env_read` capability is granted)
- Direct SQLite write access (plugins get a read-only connection or a transaction-wrapped write path)

**What the sandbox does NOT block**:
- CPU-based DoS (a runaway plugin loop will burn CPU until the 30s timeout)
- Memory DoS (a plugin allocating unbounded memory is not constrained; RSS limits may be enforced at the OS level)
- Plugin-to-plugin communication (if two plugins share a backend, one can interfere with the other)

**Threat assumptions**:
- Plugins are not intentionally adversarial (sandboxing is defense-in-depth, not a hard security boundary)
- The host process is trusted
- The Go plugin (which needs subprocess access for `go test` execution) is first-party or heavily audited
