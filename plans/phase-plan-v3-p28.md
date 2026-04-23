# P28: MCP Tool Handoff & Fail-Closed Query Behavior

> Plan doc produced by `codex-plan-phase specs/phase-plans-v3.md P28` on 2026-04-23.
> Source roadmap `specs/phase-plans-v3.md` is staged in this worktree (`git status --short` shows `A  specs/phase-plans-v3.md`).

## Context

P28 consumes the P27 readiness contract and should not execute until P27's readiness
schema is final and its targeted tests pass. The current P27 working tree introduces
`RepositoryReadinessState`, `RepositoryReadiness.to_dict()`, `ReadinessClassifier`,
`RepoResolver.classify()`, and `_classify_ctx()` in `mcp_server/cli/tool_handlers.py`.

The current gap is that query handlers only short-circuit `unsupported_worktree`.
`search_code` and `symbol_lookup` can still dispatch against missing, empty, stale,
wrong-branch, building, or unregistered indexes and then return ordinary `[]` or
`not_found` responses. At the same time, `_SERVER_INSTRUCTIONS`, tool descriptions,
`AGENTS.md`, README, and slash-command docs still encourage unconditional MCP-first
search and treat a zero-result index response as the only safe fallback signal.

P28 freezes one user-facing rule: indexed search is authoritative only when repository
readiness is `ready`. When readiness is not ready, query tools return a structured
`index_unavailable` response with `safe_fallback: "native_search"` and do not call the
dispatcher. Ready indexes that simply have no matching results remain ordinary no-match
responses and must be distinguishable from unavailable indexes.

External phase dependency: P27 must complete IF-0-P27-1 through IF-0-P27-6 before any
P28 implementation lane starts.

## Interface Freeze Gates

- [ ] IF-0-P28-1 - Query readiness gate: after path sandbox checks and before any
      dispatcher call, `handle_search_code` and `handle_symbol_lookup` classify the
      target repository; if `RepositoryReadiness.ready` is `False`, they return
      `index_unavailable` and do not call `dispatcher.search()` or `dispatcher.lookup()`.
- [ ] IF-0-P28-2 - Unavailable-query response contract: non-ready query responses use
      JSON with `error: "Index unavailable"`, `code: "index_unavailable"`,
      `tool`, `safe_fallback: "native_search"`, `readiness:
      RepositoryReadiness.to_dict()`, `message`, `remediation`, and the original `query`
      or `symbol`. They never return a bare `[]` or `result: "not_found"`.
- [ ] IF-0-P28-3 - Ready no-match contract: ready query responses that have no matches
      keep the existing no-match semantics (`results: []` for search and
      `result: "not_found"` for symbols) and include readiness metadata showing
      `state: "ready"` so callers can distinguish no matches from unavailable indexes.
- [ ] IF-0-P28-4 - STDIO handoff contract: `_SERVER_INSTRUCTIONS` and `search_code` /
      `symbol_lookup` tool descriptions say to use indexed search only when readiness is
      `ready`; `index_unavailable` means use native search and optionally run `reindex`
      according to the readiness remediation.
- [ ] IF-0-P28-5 - Documentation handoff contract: `AGENTS.md`, `README.md`, and the
      `.claude/commands` quick references use the same readiness vocabulary, remove
      unconditional "always use MCP first" wording, and document `safe_fallback:
      "native_search"`.
- [ ] IF-0-P28-6 - Readiness vocabulary contract: P28 reuses P27
      `RepositoryReadinessState` values for all query fail-closed decisions; new
      production code does not introduce a second readiness enum or parallel state names.

## Lane Index & Dependencies

- SL-0 - Query fail-closed response contract; Depends on: P27; Blocks: SL-1, SL-5; Parallel-safe: no
- SL-1 - STDIO instructions and tool descriptions; Depends on: SL-0; Blocks: SL-5; Parallel-safe: yes
- SL-2 - AGENTS readiness handoff; Depends on: P27; Blocks: SL-5; Parallel-safe: yes
- SL-3 - README readiness handoff; Depends on: P27; Blocks: SL-5; Parallel-safe: yes
- SL-4 - Slash-command readiness handoff; Depends on: P27; Blocks: SL-5; Parallel-safe: yes
- SL-5 - P28 contract audit; Depends on: SL-0, SL-1, SL-2, SL-3, SL-4; Blocks: P33, P34; Parallel-safe: no

Lane DAG:

```text
P27
 ├─> SL-0 ─> SL-1 ─┐
 ├─> SL-2 ─────────┤
 ├─> SL-3 ─────────┼─> SL-5
 └─> SL-4 ─────────┘
```

## Lanes

### SL-0 - Query Fail-Closed Response Contract

- **Scope**: Make `search_code` and `symbol_lookup` fail closed for every non-ready P27 readiness state while preserving ordinary no-match behavior for ready indexes.
- **Owned files**: `mcp_server/cli/tool_handlers.py`, `tests/test_tool_readiness_fail_closed.py`, `tests/test_tool_handlers_readiness.py`
- **Interfaces provided**: `_index_unavailable_response(readiness, tool, *, query=None, symbol=None) -> list[types.TextContent]`; query response schema from IF-0-P28-2; ready no-match schema from IF-0-P28-3
- **Interfaces consumed**: P27 `RepositoryReadiness`, `RepositoryReadinessState`, `RepositoryReadiness.to_dict()`, `_classify_ctx()`, `_ensure_response()`, `_allowed_roots()`, `_path_within_allowed()`, existing dispatcher protocol methods
- **Parallel-safe**: no
- **Tasks**:
  - test: Add `tests/test_tool_readiness_fail_closed.py` with parametrized `search_code` and `symbol_lookup` cases for `unregistered_repository`, `missing_index`, `index_empty`, `stale_commit`, `wrong_branch`, `index_building`, and `unsupported_worktree`.
  - test: Assert every non-ready query case returns `code == "index_unavailable"`, `safe_fallback == "native_search"`, the original `readiness.state`, and does not call the dispatcher.
  - test: Assert ready search misses still return `results: []` and ready symbol misses still return `result: "not_found"` with readiness metadata, not `index_unavailable`.
  - test: Update P27 handler tests in `tests/test_tool_handlers_readiness.py` so search/symbol unsupported-worktree expectations match P28 while `reindex` remains a mutation-path response.
  - impl: Replace the query-only `_unsupported_worktree_response()` path with a generic `_index_unavailable_response()` path for all non-ready readiness states.
  - impl: Keep path sandbox failures as `path_outside_allowed_roots`; readiness checks run only after the sandbox accepts path-shaped `repository` values.
  - impl: Gate `dispatcher.search()` and `dispatcher.lookup()` behind `readiness.ready is True` when `_classify_ctx()` returns a readiness result.
  - impl: Include ready readiness metadata on no-match responses without changing successful hit payloads unless needed for consistency.
  - verify: `uv run pytest tests/test_tool_readiness_fail_closed.py tests/test_tool_handlers_readiness.py -v --no-cov`

### SL-1 - STDIO Instructions And Tool Descriptions

- **Scope**: Update the MCP server's model-facing instructions and query tool descriptions to advertise readiness-gated indexed search instead of unconditional MCP-first search.
- **Owned files**: `mcp_server/cli/stdio_runner.py`, `tests/test_stdio_tool_descriptions.py`
- **Interfaces provided**: IF-0-P28-4 `_SERVER_INSTRUCTIONS`; readiness-aware `search_code` and `symbol_lookup` descriptions; `_LocalRepoResolver.classify(path)` for single-repo STDIO fallback readiness when `_repo_resolver` is unavailable
- **Interfaces consumed**: SL-0 `index_unavailable` response schema; P27 `ReadinessClassifier.classify_registered()` and `RepositoryReadinessState`; existing `_build_tool_list()` tool names and schemas
- **Parallel-safe**: yes
- **Tasks**:
  - test: Add `tests/test_stdio_tool_descriptions.py` asserting `_SERVER_INSTRUCTIONS`, `search_code.description`, and `symbol_lookup.description` contain `readiness`, `ready`, `index_unavailable`, `native_search`, and `reindex`.
  - test: Assert the query tool descriptions no longer contain unconditional phrases such as `[USE BEFORE GREP]`, `ALWAYS use`, or fallback instructions tied only to `0 results` / `not_found`.
  - test: Assert existing repository input schemas remain present and optional for query tools.
  - impl: Rewrite `_SERVER_INSTRUCTIONS` to instruct clients to check `get_status` repository readiness or honor query `index_unavailable` before trusting indexed search.
  - impl: Rewrite `search_code` and `symbol_lookup` descriptions to say indexed search is authoritative only for readiness `ready`; otherwise use native search and follow readiness remediation.
  - impl: Add `_LocalRepoResolver.classify()` using `_local_ctx.registry_entry` and `ReadinessClassifier.classify_registered()` so legacy single-repo STDIO mode still exposes readiness to SL-0 query gates.
  - verify: `uv run pytest tests/test_stdio_tool_descriptions.py tests/docs/test_p6b_sl3.py tests/docs/test_p7_schema_alignment.py -v --no-cov`

### SL-2 - AGENTS Readiness Handoff

- **Scope**: Align the repository's agent instructions with the P28 readiness-first search contract.
- **Owned files**: `AGENTS.md`, `tests/docs/test_p28_agents_handoff.py`
- **Interfaces provided**: AGENTS MCP search strategy that uses indexed search only for readiness `ready` and names `index_unavailable` / `native_search`
- **Interfaces consumed**: IF-0-P28-1 through IF-0-P28-5; P27 readiness states and multi-repo support model
- **Parallel-safe**: yes
- **Tasks**:
  - test: Add docs tests proving `AGENTS.md` mentions `ready`, `index_unavailable`, `safe_fallback`, `native_search`, and `reindex` in the MCP search strategy section.
  - test: Assert `AGENTS.md` no longer contains unconditional "ALWAYS USE MCP TOOLS FIRST", "Fall back to Grep ONLY if this returns 0 results", or equivalent not-found-only fallback language.
  - impl: Update the MCP search strategy to require checking `get_status` readiness or honoring `index_unavailable` before relying on indexed results.
  - impl: Preserve the high-level preference for MCP search when readiness is `ready`, but state that native `rg`/file tools are the safe fallback when readiness is non-ready or MCP tools are unavailable.
  - impl: Update multi-repo notes that currently imply all worktrees of the same repo share one usable index; point to the P27 unsupported-worktree contract instead.
  - verify: `uv run pytest tests/docs/test_p28_agents_handoff.py tests/docs/test_p7_markdown_alignment.py -v --no-cov`

### SL-3 - README Readiness Handoff

- **Scope**: Update customer-facing README guidance so LLM users and operators understand readiness-gated MCP search and fail-closed query responses.
- **Owned files**: `README.md`, `tests/docs/test_p28_readme_handoff.py`
- **Interfaces provided**: README usage guidance for `get_status` readiness, `index_unavailable`, `safe_fallback: "native_search"`, and `reindex` remediation
- **Interfaces consumed**: IF-0-P28-1 through IF-0-P28-5; P27 readiness states; existing README beta and MCP-primary framing tests
- **Parallel-safe**: yes
- **Tasks**:
  - test: Add README docs tests requiring readiness-gated wording near the Project Status / MCP usage sections and the multi-repo query examples.
  - test: Assert README no longer says LLMs should "always use these first" without the readiness qualifier.
  - test: Assert README documents the difference between a ready no-match response and `index_unavailable`.
  - impl: Update the Project Status primary-surface line to say MCP tools are the primary LLM surface when repository readiness is `ready`.
  - impl: Update "Using Against Many Repos" to say same-repo multiple worktrees are unsupported for v3 and non-ready query responses provide `safe_fallback: "native_search"`.
  - impl: Update the tool-call example prose to tell clients to call `get_status` or handle `index_unavailable` before treating index results as authoritative.
  - verify: `uv run pytest tests/docs/test_p28_readme_handoff.py tests/docs/test_p8_customer_docs_alignment.py -v --no-cov`

### SL-4 - Slash-Command Readiness Handoff

- **Scope**: Update the custom slash-command quick references so they no longer teach unconditional MCP-first behavior.
- **Owned files**: `.claude/commands/mcp-tools.md`, `.claude/commands/search-code.md`, `.claude/commands/find-symbol.md`, `.claude/commands/verify-mcp.md`, `tests/docs/test_p28_slash_commands_handoff.py`
- **Interfaces provided**: slash-command docs that require readiness `ready` for indexed search and treat `index_unavailable` as a native-search fallback signal
- **Interfaces consumed**: IF-0-P28-1 through IF-0-P28-5; existing command names and examples
- **Parallel-safe**: yes
- **Tasks**:
  - test: Add command-doc tests requiring `ready`, `index_unavailable`, `safe_fallback`, and `native_search` across the four command docs.
  - test: Assert the command docs no longer contain "Never use grep", "MCP-First: Enabled", or fallback-only-on-zero-result language.
  - impl: Update `/mcp-tools` search strategy and performance comparison to be readiness-scoped, not unconditional.
  - impl: Update `/search-code` and `/find-symbol` to say native `rg` / file search is expected when readiness is non-ready or `index_unavailable` is returned.
  - impl: Update `/verify-mcp` expected output to include repository readiness and make MCP-first conditional on `ready`.
  - verify: `uv run pytest tests/docs/test_p28_slash_commands_handoff.py -v --no-cov`

### SL-5 - P28 Contract Audit

- **Scope**: Run the P28 reducer checks across query behavior, tool descriptions, and documentation surfaces.
- **Owned files**: (none)
- **Interfaces provided**: completed IF-0-P28-1 through IF-0-P28-6 evidence for P33 release-gate planning
- **Interfaces consumed**: SL-0 query response tests; SL-1 STDIO tests; SL-2 through SL-4 docs findings; roadmap exit criteria from `specs/phase-plans-v3.md`
- **Parallel-safe**: no
- **Tasks**:
  - test: Run all P28 targeted tests after implementation lanes land.
  - verify: `uv run pytest tests/test_tool_readiness_fail_closed.py tests/test_tool_handlers_readiness.py tests/test_stdio_tool_descriptions.py -v --no-cov`
  - verify: `uv run pytest tests/docs/test_p28_agents_handoff.py tests/docs/test_p28_readme_handoff.py tests/docs/test_p28_slash_commands_handoff.py -v --no-cov`
  - verify: `uv run pytest tests/docs/test_p6b_sl3.py tests/docs/test_p7_schema_alignment.py tests/docs/test_p7_markdown_alignment.py tests/docs/test_p8_customer_docs_alignment.py -v --no-cov`
  - verify: `rg -n "ALWAYS use|ALWAYS USE|USE BEFORE GREP|Fall back.*ONLY.*(0 results|not_found)|Never use grep|Never use.*file searching|MCP-First: Enabled" mcp_server/cli/stdio_runner.py AGENTS.md README.md .claude/commands`
  - impl: If the grep finds intentional historical wording outside P28-owned active instructions, narrow the assertion to active model-facing sections instead of weakening the P28 contract.

## Verification

Required P28 targeted checks:

```bash
uv run pytest tests/test_tool_readiness_fail_closed.py tests/test_tool_handlers_readiness.py tests/test_stdio_tool_descriptions.py -v --no-cov
uv run pytest tests/docs/test_p28_agents_handoff.py tests/docs/test_p28_readme_handoff.py tests/docs/test_p28_slash_commands_handoff.py -v --no-cov
```

Compatibility checks around existing docs and tool schema contracts:

```bash
uv run pytest tests/docs/test_p6b_sl3.py tests/docs/test_p7_schema_alignment.py tests/docs/test_p7_markdown_alignment.py tests/docs/test_p8_customer_docs_alignment.py -v --no-cov
```

Contract search:

```bash
rg -n "index_unavailable|safe_fallback|native_search|RepositoryReadiness|readiness" \
  mcp_server/cli/tool_handlers.py mcp_server/cli/stdio_runner.py AGENTS.md README.md .claude/commands tests

rg -n "ALWAYS use|ALWAYS USE|USE BEFORE GREP|Fall back.*ONLY.*(0 results|not_found)|Never use grep|Never use.*file searching|MCP-First: Enabled" \
  mcp_server/cli/stdio_runner.py AGENTS.md README.md .claude/commands
```

The second `rg` command should return no active model-facing instruction hits after P28.

Whole-phase optional regression after targeted checks pass:

```bash
uv run pytest tests/test_repository_readiness.py tests/test_repo_resolver.py tests/test_health_surface.py tests/test_tool_handlers_readiness.py -v --no-cov
make test
```

## Acceptance Criteria

- [ ] `search_code` and `symbol_lookup` classify repository readiness before dispatcher calls.
- [ ] Non-ready readiness states return `code: "index_unavailable"` with `safe_fallback: "native_search"`.
- [ ] Missing, stale, wrong-branch, unsupported-worktree, unregistered, empty-index, and index-building states do not produce plain `[]` or `not_found`.
- [ ] Empty ready search results remain distinguishable from unavailable indexes through readiness metadata.
- [ ] Ready symbol misses remain distinguishable from unavailable indexes through readiness metadata.
- [ ] Query path sandbox errors still return `path_outside_allowed_roots` instead of being converted to `index_unavailable`.
- [ ] `_SERVER_INSTRUCTIONS` and query tool descriptions no longer contain unconditional MCP-first language.
- [ ] `AGENTS.md`, `README.md`, and `.claude/commands` instruct models to use indexed search only when readiness is `ready`.
- [ ] Docs name `index_unavailable`, `safe_fallback: "native_search"`, and `reindex` remediation.
- [ ] Tests assert unavailable indexes do not produce plain `[]` or `not_found`.
- [ ] P28 does not change search ranking, reranking, language support, artifact behavior, or automatic indexing policy.
