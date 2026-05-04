# MCPAUTH boundary

## Supported auth surfaces

`MCP_CLIENT_SECRET` is a local STDIO handshake guard for `mcp-index stdio`.
Clients satisfy that local STDIO handshake guard by calling the `handshake`
tool before other gated STDIO tool calls.

The FastAPI gateway uses separate admin/debug bearer token authentication for
routes such as `/metrics` and other protected admin/debug endpoints.

no remote MCP authorization is implemented while remote MCP transport remains
deferred.

## Secret-handling expectations

- The STDIO `handshake` tool must not log raw secret values.
- HTTP 4xx and 5xx responses must redact `MCP_CLIENT_SECRET=` values alongside
  existing bearer, JWT, and GitHub token redaction.
- Auth failures stay fail-closed without widening the supported auth story
  beyond the current local STDIO plus admin/debug HTTP split.

## Evidence

- `tests/test_handshake.py`
- `tests/test_mcpauth_stdio_contract.py`
- `tests/test_secret_redaction.py`
- `tests/security/test_metrics_auth.py`
- `tests/security/test_route_auth_coverage.py`
- `tests/security/test_mcpauth_boundary.py`
- `tests/docs/test_mcpauth_surface_alignment.py`
