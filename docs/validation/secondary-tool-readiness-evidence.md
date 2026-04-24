> **Historical artifact — as-of 2026-04-18, may not reflect current behavior**

# TOOLRDY Secondary Tool Readiness Evidence

Generated: 2026-04-24T05:54:00Z
Repo commit: 8d08545
Phase plan: `plans/phase-plan-v4-toolrdy.md`

## Contract Summary

TOOLRDY hardens secondary tools so they fail closed against non-ready
repository scopes before mutating index state or constructing summarization
workers.

For `reindex`, non-ready repository states return:

- `results: []`
- `code: <readiness.code>`
- `tool: "reindex"`
- `readiness: readiness.to_dict()`
- `remediation: <readiness.remediation>`
- `mutation_performed: false`

For `write_summaries` and `summarize_sample`, non-ready repository states
return:

- `results: []`
- `code: <readiness.code>`
- `tool: "write_summaries"` or `tool: "summarize_sample"`
- `readiness: readiness.to_dict()`
- `remediation: <readiness.remediation>`
- `persisted: false`

These mutation and summarization refusals intentionally do not include
`safe_fallback: "native_search"`. Native search fallback remains a query-tool
contract for `search_code` and `symbol_lookup`, not a mutation or
summarization instruction.

Covered readiness states:

- `unregistered_repository`
- `missing_index`
- `index_empty`
- `stale_commit`
- `wrong_branch`
- `index_building`
- `unsupported_worktree`

Explicit path scope remains bounded by `MCP_ALLOWED_ROOTS`.
`path_outside_allowed_roots` and `conflicting_path_and_repository` keep
precedence before secondary readiness refusals.

## Implementation Evidence

- `mcp_server/cli/tool_handlers.py` now uses a secondary-tool readiness refusal
  helper for `reindex`, `write_summaries`, and `summarize_sample`.
- `reindex` rejects non-ready readiness states before dispatcher mutation or
  FTS rebuild, and records durable file rows for ready handler-driven reindex
  paths before rebuilding lexical rows.
- `summarize_sample(paths=...)` checks every explicit path against
  `MCP_ALLOWED_ROOTS`, requires one ready repository scope, and rejects
  mismatched path/repository scope with `conflicting_path_and_repository`.
- `mcp_server/cli/stdio_runner.py` descriptions for `reindex`,
  `write_summaries`, and `summarize_sample` now describe readiness gating and
  structured readiness refusals without native-search fallback language.

## Verification

Passed:

```bash
uv run pytest tests/test_tool_readiness_fail_closed.py tests/test_repository_readiness.py tests/test_git_index_manager.py -v --no-cov
```

Result: 61 passed.

Passed:

```bash
uv run pytest tests/test_handler_path_sandbox.py tests/integration/test_multi_repo_server.py -v --no-cov
```

Result: 32 passed.

Passed:

```bash
uv run pytest tests/test_stdio_tool_descriptions.py tests/docs/test_p6b_sl3.py tests/docs/test_p7_schema_alignment.py -v --no-cov
```

Result: 13 passed.

Passed:

```bash
uv run pytest tests/test_multi_repo_failure_matrix.py tests/smoke/test_secondary_tool_readiness_smoke.py -v --no-cov
```

Result: 9 passed.

Passed:

```bash
uv run pytest tests/test_tool_readiness_fail_closed.py tests/test_repository_readiness.py tests/test_git_index_manager.py tests/test_handler_path_sandbox.py tests/integration/test_multi_repo_server.py tests/test_multi_repo_failure_matrix.py tests/smoke -v --no-cov
```

Result: 108 passed.

Passed:

```bash
make alpha-production-matrix
```

Result: 93 passed.

## GACLOSE Handoff

No non-ready state remains intentionally allowed for `reindex`,
`write_summaries`, or `summarize_sample`.

GACLOSE can consume this artifact as evidence that secondary mutation and
summarization tools now refuse unsafe repository scopes, that explicit path
scope stays inside `MCP_ALLOWED_ROOTS`, and that ready registered repositories
can still reindex, search, and persist durable SQLite `files` rows.
