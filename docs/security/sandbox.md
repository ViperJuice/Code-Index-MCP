# Plugin Sandbox Architecture

> **Beta status**: This page targets `1.2.0-rc6`. Default sandbox behavior is
> documented alongside language support in [../SUPPORT_MATRIX.md](../SUPPORT_MATRIX.md).

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

## Availability States (P24)

Sandboxing remains default-on. `PluginFactory.get_plugin_availability()` and the
MCP `list_plugins` tool expose the detailed capability state for every factory
language:

- `enabled`: the language has a hardened sandbox module and required extras are present.
- `unsupported`: the language is registry-only or otherwise lacks a hardened sandbox module.
- `missing_extra`: the plugin depends on an optional extra that is not installed.
- `disabled`: reserved for administratively disabled capabilities.
- `load_error`: an unexpected construction failure that should be investigated.

Registry-only languages such as Ruby or JSON are skipped quietly in default
sandbox mode and are visible as `unsupported`, not as startup/runtime failures.
They can be loaded through generic parsing only when an operator explicitly opts
out with `MCP_PLUGIN_SANDBOX_DISABLE=1`.

Known optional dependency misses are normalized. For example, Java static
analysis requires `javalang`; install it with:

```bash
uv sync --locked --extra java
```

Sandbox worker import and construction failures return structured details with
`state`, `language`, `required_extras`, and `remediation` where known. C# is
available through both `c_sharp` and `csharp` aliases.

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

## Memory limit default (P20)

As of P20, the `CapabilitySet.mem_mb` default was raised from **512 MiB to 2048 MiB**
(`mcp_server/sandbox/capabilities.py`). The previous 512 MiB limit caused spurious
worker OOM kills when plugins loaded large embedding models (in particular, OpenBLAS
triggered by `numpy` import during the semantic-indexing pipeline). The new default
allows the Voyage AI embedding worker to initialise without requiring operators to set
a per-plugin memory override.

## Default-on migration (P18)

> See [docs/operations/p18-upgrade.md](../operations/p18-upgrade.md) for the full operator migration procedure.

As of P18, plugin sandboxing is **enabled by default**. Previously `MCP_PLUGIN_SANDBOX_ENABLED=1` was required to activate it; now sandboxing runs unless explicitly opted out.

### Opting out

Set `MCP_PLUGIN_SANDBOX_DISABLE=1` to run plugins unsandboxed. Only do this if every loaded plugin is fully trusted.

```bash
export MCP_PLUGIN_SANDBOX_DISABLE=1  # NOT recommended; removes defense-in-depth
```

### Migration checklist

- **If you previously ran with `MCP_PLUGIN_SANDBOX_ENABLED=1`**: no action required — sandbox remains on.
- **If you previously ran without that env var**: you were running unsandboxed. Expect subprocess and network calls from plugins to fail unless capabilities are declared. Audit plugin capability needs and either grant them or set `MCP_PLUGIN_SANDBOX_DISABLE=1` while you migrate.
- **Go plugin users**: ensure `subprocess` capability is granted (it was already required for `go test`).
