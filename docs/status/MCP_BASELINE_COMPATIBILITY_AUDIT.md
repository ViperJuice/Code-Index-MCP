# MCP Baseline Compatibility Audit

Last verified in MCPBASE against the current v8 roadmap baseline.

## Frozen Baseline

- MCP spec revision target: `2025-11-25`
- Official Python MCP SDK observed in this repo's locked environment: `mcp==1.27.0`
  sourced from `uv.lock` and confirmed at runtime during the MCPBASE smoke
- Primary MCP surface: `python -m mcp_server.cli.stdio_runner`
- Secondary HTTP surface: `mcp-index serve` starts the FastAPI admin/debug
  gateway and is not the repo's MCP Streamable HTTP transport

## Stable Public Tool Names

- `symbol_lookup`
- `search_code`
- `get_status`
- `list_plugins`
- `reindex`
- `write_summaries`
- `summarize_sample`
- `handshake`

## Preserved No-Argument Tool Calls

- `get_status({})`
- `list_plugins({})`

MCPBASE freezes those empty-object call shapes so downstream phases do not
silently introduce required inputs for them.

## Confirmed Smoke Coverage

The MCPBASE official Python SDK smoke proves that an MCP client can:

- complete `initialize`
- call `tools/list`
- call `get_status({})`
- call `list_plugins({})`
- perform representative ready-repo calls for `symbol_lookup` and
  `search_code`

The smoke is compatibility evidence only. It does not claim any new metadata,
result-schema, task, or transport migration.

## Explicit Deferrals

The following work remains downstream-only in the v8 roadmap:

- `MCPMETA`: richer tool metadata
- `MCPSTRUCT`: structured result and output-schema work
- `MCPTASKS`: task envelopes and task-oriented flows
- `MCPTRANSPORT`: any remote MCP transport, including Streamable HTTP
- `MCPAUTH`: transport/auth hardening beyond the current handshake baseline

## No-Migration Statement

MCPBASE intentionally does not change:

- MCP tool metadata fields beyond the current `name`, `description`, and
  `inputSchema`
- result-shape migration to new output schemas or `structuredContent`
- task wiring
- FastAPI endpoint surface or any claim that it already implements remote MCP
  transport
