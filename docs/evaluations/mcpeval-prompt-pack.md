# MCPEVAL Prompt Pack

This prompt pack is the repo-owned read-only evaluation corpus for the v8
`MCPEVAL` closeout. Every prompt assumes the server is running over the primary
STDIO MCP surface, uses no secrets, and targets stable answers or answer
constraints that can be verified against fixture-backed local repos.

## Prompt 1

**Prompt**

What MCP protocol revision does this server target, and what transport is the
primary supported MCP client path?

**Expected answer constraints**

- Must name MCP `2025-11-25`.
- Must identify STDIO as the primary supported MCP transport.
- Must not describe the FastAPI gateway as Streamable HTTP MCP.

## Prompt 2

**Prompt**

Run `get_status` and summarize the server posture for a ready local repository.

**Expected answer constraints**

- Must describe the result as a ready-path status or healthy-path status check.
- Must mention version `1.2.0`.
- Must not confuse readiness status with query success or failure.

## Prompt 3

**Prompt**

Use `search_code` against a ready repository to find the unique token
`p33_alpha_unique_token`. What file should appear in the answer?

**Expected answer constraints**

- Must mention `alpha.py`.
- Must treat the answer as a ready-path indexed result.
- Must not claim `index_unavailable`.

## Prompt 4

**Prompt**

Use `symbol_lookup` against a ready repository to find `P33AlphaWidget`. Where
is it defined?

**Expected answer constraints**

- Must mention `alpha.py`.
- Must identify the symbol name `P33AlphaWidget`.
- Must describe the answer as a symbol-definition result, not a text-search hit.

## Prompt 5

**Prompt**

Query a same-repo linked worktree with `search_code`. What should the failure
shape tell the client to do?

**Expected answer constraints**

- Must mention `index_unavailable`.
- Must mention `safe_fallback: "native_search"`.
- Must identify the readiness state as unsupported worktree or
  `unsupported_worktree`.

## Prompt 6

**Prompt**

What is the difference between a ready no-match result and a non-ready query
result for `search_code` or `symbol_lookup`?

**Expected answer constraints**

- Must distinguish ready no-match payloads from fail-closed readiness refusals.
- Must mention `results: []` and/or `result: "not_found"` for ready misses.
- Must mention `index_unavailable` for non-ready repositories.

## Prompt 7

**Prompt**

How should a client scope queries when two unrelated repositories are
registered with one server?

**Expected answer constraints**

- Must mention the optional `repository` argument.
- Must describe repository scoping by registered repo name or allowed path.
- Must not imply that sibling worktrees are automatically supported.

## Prompt 8

**Prompt**

If a user requests `semantic: true` before semantic readiness is fully built,
what answer posture should the client expect?

**Expected answer constraints**

- Must describe an explicit semantic refusal or readiness-gated response.
- Must mention `semantic_not_ready` or another semantic-specific refusal path.
- Must not claim lexical fallback silently replaces the refused semantic query.

## Prompt 9

**Prompt**

What is the documented task-oriented path for `reindex`?

**Expected answer constraints**

- Must mention including a `task` object in `tools/call`.
- Must mention `tasks/get` and `tasks/result`.
- May mention `tasks/list` or `tasks/cancel`, but must keep the answer
  read-only and documentation-based.

## Prompt 10

**Prompt**

Can this repository's FastAPI gateway be registered today as the repo's
Streamable HTTP MCP transport?

**Expected answer constraints**

- Must answer no or explicitly state that remote MCP transport is deferred.
- Must state that FastAPI is the admin/debug HTTP surface.
- Must mention Streamable HTTP as deferred or unsupported in the current v8
  posture.

## Prompt 11

**Prompt**

What does `MCP_CLIENT_SECRET` protect, and what does it not protect?

**Expected answer constraints**

- Must identify it as a local STDIO handshake guard.
- Must state that it is not remote MCP authorization.
- Must keep the answer redacted and documentation-based.
