# Python client API status

- Phase plan: `plans/phase-plan-v9-PYCLIENT.md`
- Supported import path: `mcp_server.client`
- Supported local API names: `IndexItClient`, `open_client`,
  `ClientSearchOptions`, `search_code`, `symbol_lookup`, `reindex`,
  `get_status`
- Package identity: distribution name remains `index-it-mcp`; import package
  remains `mcp_server`
- Source-filter scope: `source_type="friction"` with `friction_categories`,
  `source_type="history"` with `history_labels` and `history_repos`, plus
  `include_source_metadata`
- Readiness contract: non-ready repos return typed `index_unavailable` data
  with `safe_fallback="native_search"` instead of querying stale indexes
- Wrapper compatibility: MCP `search_code` and FastAPI `/search` use the same
  local search service for dispatcher-backed searches
- Stability note: beta local API only; MCP tools remain the preferred LLM
  surface
- Non-goals: no remote service client, no MCP tool removal, no package rename,
  no FRICTION/HISTORY schema changes
- Verification commands:
  - `uv run pytest tests/test_python_client_contract.py tests/test_python_client_search.py tests/test_python_client_sources.py tests/test_python_client_indexing.py tests/test_python_client_mcp_wrapper.py tests/test_friction_tool_handlers.py tests/test_history_tool_handlers.py tests/test_gateway.py tests/docs/test_pyclient_api_contract.py tests/docs/test_pyclient_public_docs.py -q --no-cov`
  - `uv run pytest tests/smoke/test_mcpbase_stdio_smoke.py tests/smoke/test_secondary_tool_readiness_smoke.py -q --no-cov`
  - `make agent-full`
  - `phase-loop validate-roadmap specs/phase-plans-v9.md`
