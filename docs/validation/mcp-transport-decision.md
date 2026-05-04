# MCPTRANSPORT decision

## Current v8 decision

Remote MCP transport is deferred in v8. The supported MCP client transport in
this repository remains `mcp-index stdio`.

`mcp-index serve` and `mcp_server.gateway:app` remain the FastAPI
admin/debug HTTP surface for diagnostics, scripting, health, metrics, and
manual operations. They are not this repository's MCP Streamable HTTP
transport.

## Why v8 defers remote MCP

- The existing FastAPI gateway is an admin/debug surface, not a dedicated MCP
  transport lifecycle.
- Reusing the admin gateway as if it were Streamable HTTP would blur route
  ownership and misstate the supported client contract.
- `MCPAUTH` should not design remote MCP authorization until there is an
  actual remote MCP transport to protect.

## Minimum prerequisites for a future remote MCP phase

- Add a distinct Streamable HTTP endpoint with separate routing and lifecycle
  from the existing admin/debug gateway.
- Add transport-specific tests and client smokes that prove the endpoint works
  as MCP rather than as the admin REST API.
- Keep admin/debug route coverage passing while the new remote transport is
  introduced alongside it.
- Move remote authorization design into `MCPAUTH` only after the dedicated
  transport exists.

## Downstream implication

`MCPAUTH` should document the current state as "no remote MCP auth is
implemented" unless a later roadmap phase adds a dedicated remote MCP
transport first.
